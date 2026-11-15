"""Run bootstrap in temporary directories with no root or real package tools."""

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
        self.env = dict(HOME=str(self.home), PATH=str(self.bin),
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

    def test_help_and_invalid_arguments_do_not_run_commands(self):
        for args, expected in ((("--help",), 0), (("--invalid",), 1)):
            with self.subTest(args=args):
                result = self.run_bootstrap(*args)
                self.assertEqual(result.returncode, expected, result.stderr)
                self.assertEqual(self.call_lines(), [])

    def test_unsupported_platform_does_not_run_commands(self):
        self.bootstrap.write_text(self.bootstrap.read_text().replace(
            "/etc/arch-release", str(self.root / "missing-arch-release")))
        result = self.run_bootstrap()
        self.assertEqual(result.returncode, 1)
        self.assertEqual(self.call_lines(), [])

    def test_missing_package_tools_stop_before_installer(self):
        self.simulate_arch()
        for command in ("sudo", "pacman"):
            with self.subTest(command=command):
                tool = self.bin / command
                contents = tool.read_text()
                tool.unlink()
                try:
                    result = self.run_bootstrap()
                    self.assertEqual(result.returncode, 1)
                    self.assertIn(command, result.stderr)
                    self.assertEqual(self.call_lines(), [])
                finally:
                    tool.write_text(contents)
                    tool.chmod(0o755)

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


if __name__ == "__main__":
    unittest.main()
