"""Package-list failures must stop bootstrap before any installation."""

from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[1]
BASH = shutil.which("bash")


class BootstrapPackageListTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="bootstrap-packages-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / "repo with spaces"
        self.bin = self.root / "bin"
        self.home = self.root / "home"
        for directory in (self.repo, self.bin, self.home):
            directory.mkdir()
        marker = self.root / "arch-release"
        marker.touch()
        self.bootstrap = self.repo / "bootstrap-arch.sh"
        # Change only the OS marker in a disposable copy; no Arch/root needed.
        self.bootstrap.write_text((REPO / "bootstrap-arch.sh").read_text().replace(
            "/etc/arch-release", str(marker)))
        self.packages = self.repo / "packages-arch.txt"
        self.packages.write_text("alpha\nbeta\n")
        self.calls = self.root / "calls"
        self.env = dict(HOME=str(self.home), PATH=str(self.bin),
                        CALL_LOG=str(self.calls), LC_ALL="C")
        # A missing stub cannot fall back to a real package manager or installer.
        for command in ("bash", "dirname", "grep"):
            (self.bin / command).symlink_to(shutil.which(command))
        self.write_script(self.bin / "sudo",
                          'printf "sudo\\n" >> "$CALL_LOG"\n"$@"\n')
        self.write_script(self.bin / "pacman",
                          'printf "pacman\\n" >> "$CALL_LOG"\n'
                          'printf "<%s>\\n" "$@" >> "$CALL_LOG"\n')
        self.write_script(self.repo / "install.sh",
                          'printf "install\\n" >> "$CALL_LOG"\n')

    def write_script(self, path, body):
        path.write_text(f"#!{BASH}\nset -eu\n{body}")
        path.chmod(0o755)

    def run_bootstrap(self):
        return subprocess.run([BASH, str(self.bootstrap)], cwd=self.root,
                              env=self.env, capture_output=True, text=True,
                              timeout=10)

    def call_lines(self):
        return self.calls.read_text().splitlines() if self.calls.exists() else []

    def assert_stopped(self, result):
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(result.stderr)
        self.assertEqual(self.call_lines(), [])

    def test_missing_package_list_stops_installation(self):
        self.packages.unlink()
        self.assert_stopped(self.run_bootstrap())

    def test_directory_package_list_stops_installation(self):
        self.packages.unlink()
        self.packages.mkdir()
        self.assert_stopped(self.run_bootstrap())

    def test_read_failure_after_partial_output_stops_installation(self):
        # Deterministic I/O failure, even when tests run as root. Partial output
        # must never become an incomplete pacman invocation.
        (self.bin / "grep").unlink()
        self.write_script(self.bin / "grep",
                          'printf "alpha\\n"\n'
                          'printf "simulated read failure\\n" >&2\nexit 2\n')
        result = self.run_bootstrap()
        self.assert_stopped(result)
        self.assertEqual(result.returncode, 2)

    def test_empty_package_list_still_runs_installer(self):
        self.packages.write_text("")
        result = self.run_bootstrap()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.call_lines(), ["install"])

    def test_only_comments_and_whitespace_still_runs_installer(self):
        self.packages.write_text("# comment\n\n \t\n  # indented comment\n")
        result = self.run_bootstrap()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.call_lines(), ["install"])

    def test_last_package_without_newline_is_passed_as_one_argument(self):
        self.packages.write_text("# comment\nalpha\n\n \t# comment\nbeta")
        result = self.run_bootstrap()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.call_lines(), [
            "sudo", "pacman", "<-S>", "<--needed>", "<alpha>", "<beta>",
            "install",
        ])


if __name__ == "__main__":
    unittest.main()
