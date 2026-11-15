"""Count external path operations while exercising real copies in temporary homes."""

import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[1]


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


class InstallerProcessTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="installer-processes-")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.repo = self.root / "repo with spaces"
        self.repo.mkdir()
        shutil.copy2(REPO / "install.sh", self.repo / "install.sh")
        shutil.copytree(REPO / "home", self.repo / "home")
        self.home = self.root / "home with spaces"
        self.home.mkdir()
        bin_dir = self.root / "bin"
        bin_dir.mkdir()
        self.calls = self.root / "dirname-calls"
        wrapper = bin_dir / "dirname"
        wrapper.write_text(
            '#!/bin/sh\nprintf "call\\n" >> "$DIRNAME_LOG"\n'
            f'exec {shlex.quote(shutil.which("dirname"))} "$@"\n'
        )
        wrapper.chmod(0o755)
        self.env = dict(HOME=str(self.home), PATH=f"{bin_dir}:{os.defpath}",
                        DIRNAME_LOG=str(self.calls), LC_ALL="C")

    def install(self, *args):
        result = subprocess.run(
            ["bash", str(self.repo / "install.sh"), *args], cwd=self.root,
            env=self.env, capture_output=True, text=True, timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def assert_no_per_target_dirname(self):
        # Repository discovery may use dirname once; deployment should use none.
        calls = self.calls.read_text().splitlines() if self.calls.exists() else []
        self.assertLessEqual(len(calls), 1, f"dirname launched {len(calls)} times")

    def assert_payload(self):
        for source in (self.repo / "home").rglob("*"):
            if source.is_file() and "profile-template" not in source.parts:
                target = self.home / source.relative_to(self.repo / "home")
                self.assertEqual(target.read_bytes(), source.read_bytes())
                self.assertEqual(target.stat().st_mode, source.stat().st_mode)

    def populate(self):
        shutil.copytree(self.repo / "home", self.home, dirs_exist_ok=True)
        self.external = self.root / "external"
        self.external.write_text("keep outside home\n")
        (self.home / ".xprofile").unlink()
        (self.home / ".xprofile").symlink_to(self.external)
        (self.home / ".config/i3/stale").write_text("old config\n")
        self.profile = self.home / ".config/mozilla/firefox/chosen profile"
        (self.profile / "chrome").mkdir(parents=True)
        (self.profile.parent / "profiles.ini").write_text(
            "[InstallTest]\nDefault=chosen profile\n"
        )
        self.firefox_files = ("user.js", "chrome/userChrome.css", "chrome/userContent.css")
        for relative in self.firefox_files:
            (self.profile / relative).write_text("old " + relative)

    def test_fresh_install_avoids_per_target_processes(self):
        self.install()
        self.assert_payload()
        self.assert_no_per_target_dirname()

    def test_populated_install_preserves_backups_and_firefox(self):
        self.populate()
        self.install()
        self.assert_payload()
        backup, = (self.home / ".dotfiles-backup").iterdir()
        self.assertEqual(os.readlink(backup / ".xprofile"), str(self.external))
        self.assertEqual(self.external.read_text(), "keep outside home\n")
        self.assertEqual((backup / ".config/i3/stale").read_text(), "old config\n")
        self.assertFalse((self.home / ".config/i3/stale").exists())
        template = self.repo / "home/.config/mozilla/firefox/profile-template"
        for relative in self.firefox_files:
            self.assertEqual((self.profile / relative).read_bytes(),
                             (template / relative).read_bytes())
            self.assertEqual((backup / self.profile.relative_to(self.home) / relative)
                             .read_text(), "old " + relative)
        self.assert_no_per_target_dirname()

    def test_no_backup_replaces_without_touching_symlink_referent(self):
        self.populate()
        self.install("--no-backup")
        self.assert_payload()
        self.assertFalse((self.home / ".dotfiles-backup").exists())
        self.assertFalse((self.home / ".config/i3/stale").exists())
        self.assertEqual(self.external.read_text(), "keep outside home\n")
        self.assert_no_per_target_dirname()

    def test_dry_run_leaves_home_unchanged(self):
        self.populate()
        before = snapshot(self.home)
        self.install("--dry-run")
        self.assertEqual(snapshot(self.home), before)
        self.assert_no_per_target_dirname()


if __name__ == "__main__":
    unittest.main()
