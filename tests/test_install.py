"""Exercise the real installer only inside disposable homes and repo copies."""

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[1]
PROFILE_FILES = ("user.js", "chrome/userChrome.css", "chrome/userContent.css")


def snapshot(root):
    return {
        str(path.relative_to(root)): (
            path.lstat().st_mode,
            path.lstat().st_mtime_ns,
            os.readlink(path) if path.is_symlink() else
            path.read_bytes() if path.is_file() else None,
        )
        for path in (root, *root.rglob("*"))
    }


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="dotfiles-install-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / "repo with spaces"
        self.repo.mkdir()
        shutil.copy2(REPO / "install.sh", self.repo / "install.sh")
        shutil.copytree(REPO / "home", self.repo / "home")
        self.home = self.root / "home with spaces"
        self.home.mkdir()
        self.env = {"HOME": str(self.home), "PATH": os.defpath, "LC_ALL": "C.UTF-8"}

    def install(self, *args):
        return subprocess.run(
            ["bash", str(self.repo / "install.sh"), *args],
            cwd=self.root, env=self.env, capture_output=True, text=True, timeout=10,
        )

    def assert_success(self, result):
        self.assertEqual(result.returncode, 0, result.stderr)

    def assert_payload(self):
        for source in (self.repo / "home").rglob("*"):
            if source.is_file() and "profile-template" not in source.parts:
                target = self.home / source.relative_to(self.repo / "home")
                self.assertEqual(target.read_bytes(), source.read_bytes())
                self.assertEqual(target.stat().st_mode, source.stat().st_mode)

    def test_help_and_invalid_arguments_leave_home_unchanged(self):
        before = snapshot(self.home)
        for args, expected in ((("--help",), 0), (("--invalid",), 1)):
            with self.subTest(args=args):
                result = self.install(*args)
                self.assertEqual(result.returncode, expected, result.stderr)
                self.assertEqual(snapshot(self.home), before)

    def test_dry_run_preserves_empty_and_populated_home(self):
        for populated in (False, True):
            if populated:
                (self.home / ".xprofile").write_text("original\n")
                (self.home / ".gtkrc-2.0").symlink_to("missing")
                config = self.home / ".config/i3"
                config.mkdir(parents=True)
                (config / "keep").write_text("keep\n")
                profile = self.home / ".config/mozilla/firefox/chosen"
                (profile / "chrome").mkdir(parents=True)
                (profile.parent / "profiles.ini").write_text(
                    "[InstallTest]\nDefault=chosen\n")
                for relative in PROFILE_FILES:
                    (profile / relative).write_text("original Firefox\n")
            before = snapshot(self.home)
            for args in (("--dry-run",), ("--dry-run", "--no-backup")):
                with self.subTest(populated=populated, args=args):
                    result = self.install(*args)
                    self.assert_success(result)
                    self.assertIn("install", result.stdout)
                    self.assertEqual(snapshot(self.home), before)

    def test_fresh_install_from_other_working_directory_and_spaced_paths(self):
        self.assert_success(self.install())
        self.assert_payload()
        self.assertFalse((self.home / ".config/mozilla").exists())

    def test_backup_preserves_file_directory_and_symlinks(self):
        (self.home / ".xprofile").write_text("original\n")
        (self.home / ".gtkrc-2.0").symlink_to("missing")
        config = self.home / ".config"
        (config / "i3").mkdir(parents=True)
        (config / "i3/keep").write_text("old i3\n")
        external = self.root / "external"
        external.mkdir()
        (external / "keep").write_text("outside\n")
        (config / "kitty").symlink_to(external, target_is_directory=True)
        self.assert_success(self.install())
        backups = list((self.home / ".dotfiles-backup").iterdir())
        self.assertEqual(len(backups), 1)
        backup = backups[0]
        self.assertEqual((backup / ".xprofile").read_text(), "original\n")
        self.assertEqual(os.readlink(backup / ".gtkrc-2.0"), "missing")
        self.assertEqual((backup / ".config/i3/keep").read_text(), "old i3\n")
        self.assertEqual(os.readlink(backup / ".config/kitty"), str(external))
        self.assertEqual((external / "keep").read_text(), "outside\n")
        self.assert_payload()

    def test_no_backup_replaces_stale_directory_and_preserves_symlink_target(self):
        config = self.home / ".config"
        (config / "i3").mkdir(parents=True)
        (config / "i3/stale").write_text("stale\n")
        external = self.root / "external"
        external.write_text("outside\n")
        (self.home / ".xprofile").symlink_to(external)
        self.assert_success(self.install("--no-backup"))
        self.assertFalse((config / "i3/stale").exists())
        self.assertFalse((self.home / ".dotfiles-backup").exists())
        self.assertEqual(external.read_text(), "outside\n")
        self.assert_payload()

    def test_firefox_install_default_copies_and_backs_up_only_selected_profile(self):
        firefox = self.home / ".config/mozilla/firefox"
        chosen = firefox / "chosen"
        other = firefox / "other"
        for profile in (chosen, other):
            (profile / "chrome").mkdir(parents=True)
            for relative in PROFILE_FILES:
                (profile / relative).write_text("original " + relative)
        (firefox / "profiles.ini").write_text(
            "[InstallTest]\nDefault=chosen\n[Profile0]\nPath=other\nDefault=1\n")
        before_other = snapshot(other)
        self.assert_success(self.install())
        backup = next((self.home / ".dotfiles-backup").iterdir())
        for relative in PROFILE_FILES:
            self.assertEqual((chosen / relative).read_bytes(),
                             (REPO / "home/.config/mozilla/firefox/profile-template" /
                              relative).read_bytes())
            self.assertEqual((backup / chosen.relative_to(self.home) / relative).read_text(),
                             "original " + relative)
        self.assertEqual(snapshot(other), before_other)


if __name__ == "__main__":
    unittest.main()
