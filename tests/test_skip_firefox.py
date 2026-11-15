"""Isolated --skip-firefox integration tests; no real package tools or home."""

from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[1]
BASH = shutil.which("bash")


def snapshot(root):
    return {
        str(path.relative_to(root)): (
            ("link", str(path.readlink())) if path.is_symlink()
            else ("directory",) if path.is_dir()
            else ("file", path.read_bytes())
        )
        for path in root.rglob("*")
    }


class SkipFirefoxTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="skip-firefox-")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.home = self.root / "user home"
        self.profile = self.home / ".config/mozilla/firefox/personal.default"
        (self.profile / "chrome").mkdir(parents=True)
        (self.profile.parent / "profiles.ini").write_text(
            "[InstallTest]\nDefault=personal.default\n"
        )
        for rel in ("user.js", "chrome/userChrome.css", "chrome/userContent.css"):
            (self.profile / rel).write_text("personal content: " + rel)
        (self.profile / "bookmarks.html").write_text("keep bookmarks")
        self.bin = self.root / "bin"
        self.bin.mkdir()
        # Only these commands can be reached; host sudo/pacman are inaccessible.
        for command in ("bash", "dirname", "date", "cat", "awk", "mkdir",
                        "mv", "cp", "rm", "grep"):
            (self.bin / command).symlink_to(shutil.which(command))
        self.env = {"HOME": str(self.home), "PATH": str(self.bin)}

    def run_script(self, script, *args):
        result = subprocess.run(
            [BASH, str(script), *args], env=self.env, cwd=self.root,
            capture_output=True, text=True, timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout

    def assert_desktop_installed(self):
        for rel in (".xprofile", ".config/kitty/kitty.conf",
                    ".local/share/fcitx5/themes/everforest/theme.conf"):
            self.assertEqual((self.home / rel).read_bytes(),
                             (REPO / "home" / rel).read_bytes())

    def test_skip_preserves_firefox_and_installs_desktop(self):
        before = snapshot(self.profile.parent)
        output = self.run_script(REPO / "install.sh", "--skip-firefox")
        self.assertEqual(snapshot(self.profile.parent), before)
        self.assert_desktop_installed()
        self.assertIn("skip", output)
        self.assertIn("--skip-firefox", output)
        self.assertFalse(list((self.home / ".dotfiles-backup").rglob("user.js")))

    def test_skip_with_no_backup_preserves_symlink_and_referent(self):
        external = self.root / "personal preferences"
        external.write_text("external preferences")
        (self.profile / "user.js").unlink()
        (self.profile / "user.js").symlink_to(external)
        before = snapshot(self.profile.parent)
        self.run_script(REPO / "install.sh", "--no-backup", "--skip-firefox")
        self.assertEqual(snapshot(self.profile.parent), before)
        self.assertEqual(external.read_text(), "external preferences")
        self.assertFalse((self.home / ".dotfiles-backup").exists())
        self.assert_desktop_installed()

    def test_skip_dry_run_leaves_home_unchanged(self):
        before = snapshot(self.home)
        for extra in ((), ("--no-backup",)):
            with self.subTest(extra=extra):
                output = self.run_script(REPO / "install.sh", "--skip-firefox",
                                         "--dry-run", *extra)
                self.assertEqual(snapshot(self.home), before)
                self.assertNotIn("firefox profile ->", output)

    def test_skip_without_firefox_does_not_create_it(self):
        shutil.rmtree(self.profile.parent)
        self.run_script(REPO / "install.sh", "--skip-firefox")
        self.assertFalse(self.profile.parent.exists())
        self.assert_desktop_installed()

    def test_default_still_installs_and_backs_up_firefox(self):
        original = (self.profile / "user.js").read_bytes()
        self.run_script(REPO / "install.sh")
        template = REPO / "home/.config/mozilla/firefox/profile-template"
        for rel in ("user.js", "chrome/userChrome.css", "chrome/userContent.css"):
            self.assertEqual((self.profile / rel).read_bytes(),
                             (template / rel).read_bytes())
        backups = list((self.home / ".dotfiles-backup").rglob("user.js"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_bytes(), original)
        self.assertEqual((self.profile / "bookmarks.html").read_text(), "keep bookmarks")

    def test_bootstrap_forwards_skip_and_keeps_package_installation(self):
        repo = self.root / "repo copy"
        repo.mkdir()
        for name in ("install.sh", "packages-arch.txt"):
            shutil.copy2(REPO / name, repo / name)
        (repo / "home").symlink_to(REPO / "home", target_is_directory=True)
        marker = self.root / "arch-release"
        marker.touch()
        bootstrap = repo / "bootstrap-arch.sh"
        # Substitute only the OS marker in a disposable copy to simulate Arch.
        bootstrap.write_text((REPO / "bootstrap-arch.sh").read_text().replace(
            "/etc/arch-release", str(marker)))
        calls = self.root / "package-calls"
        self.env["CALL_LOG"] = str(calls)
        for name, body in (
            ("sudo", 'exec "$@"\n'),
            ("pacman", 'printf "%s\\n" "$@" > "$CALL_LOG"\n'),
        ):
            stub = self.bin / name
            stub.write_text(f"#!{BASH}\nset -eu\n{body}")
            stub.chmod(0o755)
        before = snapshot(self.profile.parent)
        self.run_script(bootstrap, "--skip-firefox", "--no-backup")
        self.assertEqual(snapshot(self.profile.parent), before)
        self.assert_desktop_installed()
        self.assertFalse((self.home / ".dotfiles-backup").exists())
        self.assertEqual(calls.read_text().splitlines(),
                         ["-S", "--needed", *(REPO / "packages-arch.txt").read_text().splitlines()])

    def test_help_lists_option_in_both_entry_points(self):
        for name in ("install.sh", "bootstrap-arch.sh"):
            with self.subTest(script=name):
                self.assertIn("--skip-firefox", self.run_script(REPO / name, "--help"))


if __name__ == "__main__":
    unittest.main()
