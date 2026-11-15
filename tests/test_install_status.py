"""Installer status integration tests; all configuration lives in temporary homes."""

import os
from pathlib import Path
import shutil
import stat
import subprocess
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[1]


def snapshot(root):
    """Include empty directories, links, modes and mtimes, but not read atimes."""
    result = {}
    for path in [root, *root.rglob("*")]:
        info = path.lstat()
        if path.is_symlink():
            content = os.readlink(path)
        elif stat.S_ISREG(info.st_mode):
            content = path.read_bytes()
        else:
            content = None
        result[str(path.relative_to(root))] = (
            info.st_mode, info.st_mtime_ns, content
        )
    return result


class InstallStatusTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="dotfiles status ")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo = self.root / "repo with spaces"
        self.repo.mkdir()
        shutil.copy2(REPO / "install.sh", self.repo / "install.sh")
        shutil.copytree(REPO / "home", self.repo / "home", symlinks=True)
        self.home = self.root / "home with spaces"
        self.home.mkdir()

    def run_installer(self, *args, env=None):
        return subprocess.run(
            ["/bin/bash", str(self.repo / "install.sh"), *args],
            cwd=self.root,
            env={**os.environ, "HOME": str(self.home), "LC_ALL": "C", **(env or {})},
            capture_output=True, text=True, timeout=10,
        )

    def status(self, expected, *args, env=None):
        before = snapshot(self.root)
        result = self.run_installer("--status", *args, env=env)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        self.assertEqual(snapshot(self.root), before, "status changed the filesystem")
        self.assertNotIn("Backups are in", result.stdout)
        self.assertNotIn("Done.", result.stdout)
        return result

    def assert_status(self, result, state, rel):
        self.assertIn(f"{state:<8} {self.home / rel}\n", result.stdout)

    def install(self):
        result = self.run_installer("--no-backup")
        self.assertEqual(result.returncode, 0, result.stderr)

    def firefox_profile(self):
        firefox = self.home / ".config/mozilla/firefox"
        profile = firefox / "test.default"
        profile.mkdir(parents=True)
        (firefox / "profiles.ini").write_text("[InstallTEST]\nDefault=test.default\n")
        return profile

    def test_empty_home_lists_every_target_without_writes(self):
        result = self.status(1)
        self.assertEqual(sum(line.startswith("missing ") for line in result.stdout.splitlines()), 14)
        self.assert_status(result, "missing", ".xprofile")
        self.assert_status(result, "missing", ".local/share/fcitx5/themes/everforest")
        self.assertIn("skip", result.stdout)

    def test_fresh_install_matches_including_firefox_and_binary_theme(self):
        self.firefox_profile()
        self.install()
        result = self.status(0)
        self.assertEqual(len(result.stdout.splitlines()), 17)
        self.assertTrue(all(line.startswith("same ") for line in result.stdout.splitlines()))

    def test_changed_content_is_reported_without_disclosing_it(self):
        self.install()
        marker = "PRIVATE_FIXTURE_VALUE_NOT_FOR_STATUS_OUTPUT"
        (self.home / ".xprofile").write_text(marker)
        result = self.status(1)
        self.assert_status(result, "different", ".xprofile")
        self.assert_status(result, "same", ".config/i3")
        self.assertNotIn(marker, result.stdout + result.stderr)

    def test_directory_extra_missing_nested_and_binary_files(self):
        self.install()
        extra = self.home / ".config/i3/local-only"
        extra.mkdir()
        (extra / "custom").write_text("local data")
        (self.home / ".config/kitty/kitty.conf").unlink()
        (self.home / ".config/nvim/lua/polish.lua").write_text("-- custom\n")
        (self.home / ".local/share/fcitx5/themes/everforest/arrow.png").write_bytes(b"\x00changed")
        result = self.status(1)
        for rel in (".config/i3", ".config/kitty", ".config/nvim", ".local/share/fcitx5/themes/everforest"):
            self.assert_status(result, "different", rel)

    def test_target_type_conflicts_and_fifo_do_not_hang(self):
        self.install()
        (self.home / ".xprofile").unlink()
        (self.home / ".xprofile").mkdir()
        shutil.copy2(self.repo / "home/.xprofile", self.home / ".xprofile/.xprofile")
        shutil.rmtree(self.home / ".config/i3")
        (self.home / ".config/i3").write_text("file instead of directory")
        (self.home / ".gtkrc-2.0").unlink()
        os.mkfifo(self.home / ".gtkrc-2.0")
        result = self.status(1)
        for rel in (".xprofile", ".config/i3", ".gtkrc-2.0"):
            self.assert_status(result, "different", rel)

    def test_root_symlinks_are_replacements_even_with_identical_referents(self):
        self.install()
        for rel in (".xprofile", ".config/i3"):
            target = self.home / rel
            outside = self.root / target.name
            target.rename(outside)
            target.symlink_to(outside)
        (self.home / ".gtkrc-2.0").unlink()
        (self.home / ".gtkrc-2.0").symlink_to(self.root / "missing")
        result = self.status(1)
        for rel in (".xprofile", ".config/i3", ".gtkrc-2.0"):
            self.assert_status(result, "different", rel)

    def test_nested_symlinks_compare_link_text_without_following(self):
        source_link = self.repo / "home/.config/i3/link"
        source_link.symlink_to("missing-one")
        self.install()
        self.status(0)
        target_link = self.home / ".config/i3/link"
        target_link.unlink()
        target_link.symlink_to("missing-two")
        self.assert_status(self.status(1), "different", ".config/i3")

    def test_firefox_checks_only_managed_files(self):
        profile = self.firefox_profile()
        self.install()
        (profile / "prefs.js").write_text("unmanaged fixture")
        self.status(0)
        (profile / "user.js").write_text("changed preferences")
        (profile / "chrome/userContent.css").unlink()
        result = self.status(1)
        prefix = ".config/mozilla/firefox/test.default/"
        self.assert_status(result, "different", prefix + "user.js")
        self.assert_status(result, "same", prefix + "chrome/userChrome.css")
        self.assert_status(result, "missing", prefix + "chrome/userContent.css")

    def test_status_stays_read_only_with_other_flags_in_either_order(self):
        self.install()
        (self.home / ".xprofile").write_text("local fixture")
        for args in (("--dry-run",), ("--no-backup",), ("--no-backup", "--dry-run")):
            with self.subTest(args=args):
                self.status(1, *args)
                before = snapshot(self.root)
                result = self.run_installer(*args, "--status")
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertEqual(snapshot(self.root), before)

    def test_missing_source_is_error_even_when_target_is_missing(self):
        (self.repo / "home/.xprofile").unlink()
        self.assert_status(self.status(2), "error", ".xprofile")

    def test_diff_failure_takes_precedence_over_differences(self):
        (self.home / ".xprofile").write_text("fixture")
        bin_dir = self.root / "bin"
        bin_dir.mkdir()
        diff = bin_dir / "diff"
        diff.write_text("#!/bin/sh\necho PRIVATE_DIFF_DIAGNOSTIC >&2\nexit 2\n")
        diff.chmod(0o755)
        result = self.status(2, env={"PATH": f"{bin_dir}:{os.environ['PATH']}"})
        self.assert_status(result, "error", ".xprofile")
        self.assert_status(result, "missing", ".gtkrc-2.0")
        self.assertNotIn("PRIVATE_DIFF_DIAGNOSTIC", result.stdout + result.stderr)

    def test_missing_diff_has_clear_error_and_no_writes(self):
        bin_dir = self.root / "bin"
        bin_dir.mkdir()
        for command in ("dirname", "date"):
            (bin_dir / command).symlink_to(shutil.which(command))
        result = self.status(2, env={"PATH": str(bin_dir)})
        self.assertIn("Status requires GNU diff", result.stderr)

    def test_help_documents_status(self):
        result = self.run_installer("--help")
        self.assertEqual(result.returncode, 0)
        self.assertIn("--status", result.stdout)


if __name__ == "__main__":
    unittest.main()
