"""Run bootstrap in temporary directories with no root or real package tools."""

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[1]
BASH = shutil.which("bash")


class BootstrapTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="bootstrap-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / "repo"
        self.bin = self.root / "bin"
        self.home = self.root / "home"
        for directory in (self.repo, self.bin, self.home):
            directory.mkdir()
        self.bootstrap = self.repo / "bootstrap-arch.sh"
        shutil.copy2(REPO / "bootstrap-arch.sh", self.bootstrap)
        (self.repo / "packages-arch.txt").write_text(
            "# Test packages\n\nalpha\n  # Ignored comment\nbeta\n"
        )
        self.calls = self.root / "calls"
        self.env = dict(os.environ, HOME=str(self.home), PATH=str(self.bin),
                        CALL_LOG=str(self.calls))
        # Restrict PATH so a missing stub can never reach the host's sudo/pacman.
        for command in ("bash", "dirname", "grep", "cat", "date", "awk"):
            (self.bin / command).symlink_to(shutil.which(command))
        self.write_script(self.bin / "sudo",
                          'printf "sudo %s\\n" "$*" >> "$CALL_LOG"\n"$@"\n')
        self.write_script(self.bin / "pacman",
                          'printf "pacman %s\\n" "$*" >> "$CALL_LOG"\n'
                          'exit "${PACMAN_STATUS:-0}"\n')
        self.write_script(self.repo / "install.sh",
                          'printf "install.sh %s\\n" "$*" >> "$CALL_LOG"\n')

    def write_script(self, path, body):
        path.write_text(f"#!{BASH}\nset -eu\n{body}")
        path.chmod(0o755)

    def run_bootstrap(self, *args):
        return subprocess.run([BASH, str(self.bootstrap), *args], env=self.env,
                              text=True, capture_output=True, timeout=10)

    def call_lines(self):
        return self.calls.read_text().splitlines() if self.calls.exists() else []

    def simulate_arch(self):
        # Replace only the OS marker path in this isolated copy. Production
        # keeps its real platform check; tests need neither Arch nor root.
        marker = self.root / "arch-release"
        marker.touch()
        self.bootstrap.write_text(self.bootstrap.read_text().replace(
            "/etc/arch-release", str(marker)))

    def test_dry_run_previews_packages_and_forwards_installer_flags(self):
        for args in (("--dry-run",), ("--dry-run", "--no-backup"),
                     ("--no-backup", "--dry-run")):
            with self.subTest(args=args):
                self.calls.unlink(missing_ok=True)
                result = self.run_bootstrap(*args)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("dry-run  sudo pacman -S --needed alpha beta",
                              result.stdout)
                self.assertEqual(self.call_lines(), ["install.sh " + " ".join(args)])

    def test_dry_run_does_not_require_package_tools(self):
        (self.bin / "sudo").unlink()
        (self.bin / "pacman").unlink()
        result = self.run_bootstrap("--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("sudo pacman -S --needed alpha beta", result.stdout)
        self.assertEqual(self.call_lines(), ["install.sh --dry-run"])

    def test_normal_run_installs_packages_before_installer(self):
        self.simulate_arch()
        result = self.run_bootstrap("--no-backup")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.call_lines(), [
            "sudo pacman -S --needed alpha beta",
            "pacman -S --needed alpha beta",
            "install.sh --no-backup",
        ])

    def test_package_failure_stops_before_installer(self):
        self.simulate_arch()
        self.env["PACMAN_STATUS"] = "37"
        result = self.run_bootstrap()
        self.assertEqual(result.returncode, 37, result.stderr)
        self.assertEqual(self.call_lines(), [
            "sudo pacman -S --needed alpha beta",
            "pacman -S --needed alpha beta",
        ])

    def test_dry_run_with_real_installer_preserves_home(self):
        shutil.copy2(REPO / "install.sh", self.repo / "install.sh")
        (self.repo / "home").symlink_to(REPO / "home", target_is_directory=True)
        (self.home / ".xprofile").write_text("existing configuration\n")
        (self.home / ".gtkrc-2.0").symlink_to(".xprofile")
        profile_root = self.home / ".config/mozilla/firefox"
        profile = profile_root / "test.default"
        (profile / "chrome").mkdir(parents=True)
        (profile_root / "profiles.ini").write_text(
            "[InstallTest]\nDefault=test.default\n")
        for name in ("user.js", "chrome/userChrome.css", "chrome/userContent.css"):
            (profile / name).write_text("existing Firefox configuration\n")

        def snapshot():
            return {str(path.relative_to(self.home)): (
                path.lstat().st_mode, path.lstat().st_mtime_ns,
                os.readlink(path) if path.is_symlink() else
                path.read_bytes() if path.is_file() else None,
            ) for path in (self.home, *self.home.rglob("*"))}

        before = snapshot()
        for args in (("--dry-run",), ("--dry-run", "--no-backup")):
            with self.subTest(args=args):
                result = self.run_bootstrap(*args)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("sudo pacman -S --needed alpha beta", result.stdout)
                self.assertIn("install", result.stdout)
                self.assertIn("firefox profile ->", result.stdout)
                self.assertEqual(self.call_lines(), [])
                self.assertEqual(snapshot(), before)


if __name__ == "__main__":
    unittest.main()
