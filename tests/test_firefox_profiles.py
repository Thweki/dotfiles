"""Isolated Firefox installer regressions: python3 -B -m unittest discover -s tests -v."""

import os
from pathlib import Path
import subprocess
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[1]
TEMPLATE = REPO / "home/.config/mozilla/firefox/profile-template"
PROFILE_FILES = ("user.js", "chrome/userChrome.css", "chrome/userContent.css")


class FirefoxProfilesTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="firefox-profiles-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.home = self.root / "home"
        self.firefox = self.home / ".config/mozilla/firefox"
        self.firefox.mkdir(parents=True)
        self.ini = self.firefox / "profiles.ini"
        self.backups = self.home / "backups"

    def bash(self, command, *args):
        return subprocess.run(
            ["bash", "-c", 'source "$1"; shift; ' + command,
             "test-firefox", str(REPO / "install.sh"), *map(str, args)],
            env={**os.environ, "HOME": str(self.home)},
            check=True, capture_output=True, text=True,
        ).stdout

    def write_ini(self, contents):
        self.ini.write_bytes(contents.encode())

    def select(self):
        # Check the entire stdout, including its final newline: exactly one path.
        return self.bash('select_firefox_profile "$1" "$2"', self.ini, self.firefox)

    def install(self, dry_run=False, no_backup=False):
        return self.bash(
            'BACKUP_ROOT="$1"; DRY_RUN="$2"; NO_BACKUP="$3"; install_firefox_profile',
            self.backups, int(dry_run), int(no_backup),
        )

    def profile(self, path="chosen"):
        target = self.firefox / path
        target.mkdir(parents=True)
        return target

    def seed_files(self, target):
        for relative in PROFILE_FILES:
            path = target / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("original " + relative)

    def assert_installed(self, target):
        for relative in PROFILE_FILES:
            self.assertEqual((target / relative).read_bytes(),
                             (TEMPLATE / relative).read_bytes())

    def assert_original(self, target):
        for relative in PROFILE_FILES:
            self.assertEqual((target / relative).read_text(), "original " + relative)

    def test_default_section_finalized_at_next_profile(self):
        self.write_ini("[Profile0]\nPath=chosen\nDefault=1\n"
                       "[Profile1]\nPath=other\n")
        self.assertEqual(self.select(), f"{self.firefox}/chosen\n")

    def test_default_section_finalized_at_eof(self):
        self.write_ini("[Profile0]\nDefault=1\nIsRelative=1\nPath=chosen")
        self.assertEqual(self.select(), f"{self.firefox}/chosen\n")

    def test_default_before_general_section_prints_once(self):
        self.write_ini("[Profile0]\nPath=chosen\nDefault=1\n"
                       "[General]\nStartWithLastProfile=1\n")
        self.assertEqual(self.select(), f"{self.firefox}/chosen\n")

    def test_multiple_defaults_print_only_first(self):
        self.write_ini("[Profile0]\nPath=chosen\nDefault=1\n"
                       "[Profile1]\nPath=other\nDefault=1\n")
        self.assertEqual(self.select(), f"{self.firefox}/chosen\n")

    def test_install_default_takes_precedence_in_either_order(self):
        profile = "[Profile0]\nPath=fallback\nDefault=1\n"
        install = "[InstallABC]\nDefault=chosen\n[InstallDEF]\nDefault=other\n"
        for contents in (profile + install, install + profile):
            with self.subTest(contents=contents):
                self.write_ini(contents)
                self.assertEqual(self.select(), f"{self.firefox}/chosen\n")

    def test_empty_install_default_allows_profile_fallback(self):
        self.write_ini("[InstallABC]\nDefault=\n"
                       "[Profile0]\nPath=chosen\nDefault=1\n")
        self.assertEqual(self.select(), f"{self.firefox}/chosen\n")

    def test_crlf_and_path_with_spaces_and_equals(self):
        self.write_ini("[Profile0]\r\nPath=chosen = profile\r\n"
                       "IsRelative=1\r\nDefault=1\r\n")
        self.assertEqual(self.select(), f"{self.firefox}/chosen = profile\n")

    def test_no_default_produces_no_output_or_changes(self):
        target = self.profile()
        self.seed_files(target)
        self.write_ini("[Profile0]\nPath=chosen\n")
        self.assertEqual(self.select(), "")
        self.assertIn("skip", self.install())
        self.assert_original(target)
        self.assertFalse(self.backups.exists())

    def test_absolute_external_profile_and_backups(self):
        target = self.root / "external = profile"
        self.seed_files(target)
        self.write_ini(f"[Profile0]\nPath={target}\nIsRelative=0\nDefault=1\n")
        self.assertEqual(self.select(), f"{target}\n")
        self.install()
        self.assert_installed(target)
        self.assert_original(self.backups / "external" / target.relative_to("/"))
        self.assertFalse((self.firefox / str(target).lstrip("/")).exists())

    def test_absolute_install_default(self):
        target = self.root / "external install"
        target.mkdir()
        self.write_ini(f"[InstallABC]\nDefault={target}\n")
        self.assertEqual(self.select(), f"{target}\n")
        self.install()
        self.assert_installed(target)

    def test_relative_profile_installs_with_home_relative_backups(self):
        target = self.profile()
        self.seed_files(target)
        self.write_ini("[Profile0]\nPath=chosen\nIsRelative=1\nDefault=1\n")
        self.install()
        self.assert_installed(target)
        self.assert_original(self.backups / target.relative_to(self.home))

    def test_parent_relative_external_profile_backup_stays_in_backup_root(self):
        target = self.root / "external"
        self.seed_files(target)
        relative = os.path.relpath(target, self.firefox)
        self.write_ini(f"[Profile0]\nPath={relative}\nIsRelative=1\nDefault=1\n")
        self.install()
        self.assert_installed(target)
        self.assert_original(self.backups / "external" / target.relative_to("/"))
        self.assertEqual(len(list(self.backups.rglob("user.js"))), 1)

    def test_symlink_to_external_profile_resolves_for_backup(self):
        target = self.root / "external"
        self.seed_files(target)
        (self.firefox / "chosen").symlink_to(target, target_is_directory=True)
        self.write_ini("[InstallABC]\nDefault=chosen\n")
        self.install()
        self.assert_installed(target)
        self.assert_original(self.backups / "external" / target.relative_to("/"))
        self.assertTrue((self.firefox / "chosen").is_symlink())

    def test_inconsistent_path_flags_are_rejected(self):
        target = self.profile()
        self.seed_files(target)
        for path, relative in ((str(target), "1"), ("chosen", "0"), ("chosen", "2")):
            with self.subTest(path=path, relative=relative):
                self.write_ini(f"[Profile0]\nPath={path}\nIsRelative={relative}\nDefault=1\n")
                self.assertEqual(self.select(), "")
                self.assertIn("skip", self.install())
                self.assert_original(target)
                self.assertFalse(self.backups.exists())

    def test_missing_profile_is_not_created_even_in_dry_run(self):
        for default in ("missing", str(self.root / "missing external")):
            for dry_run in (False, True):
                with self.subTest(default=default, dry_run=dry_run):
                    self.write_ini(f"[InstallABC]\nDefault={default}\n")
                    output = self.install(dry_run=dry_run)
                    self.assertIn("skip", output)
                    self.assertNotIn("firefox profile ->", output)
                    self.assertFalse((self.firefox / default).exists())
                    self.assertFalse(self.backups.exists())

    def test_profile_file_is_rejected(self):
        target = self.firefox / "chosen"
        target.write_text("keep")
        self.write_ini("[InstallABC]\nDefault=chosen\n")
        self.assertIn("skip", self.install())
        self.assertEqual(target.read_text(), "keep")
        self.assertFalse(self.backups.exists())

    def test_invalid_chrome_destination_does_not_backup_user_js(self):
        target = self.profile()
        (target / "user.js").write_text("keep")
        self.write_ini("[InstallABC]\nDefault=chosen\n")
        chrome = target / "chrome"
        for kind in ("file", "dangling symlink"):
            with self.subTest(kind=kind):
                if kind == "file":
                    chrome.write_text("keep chrome")
                else:
                    chrome.symlink_to(target / "missing")
                self.assertIn("skip", self.install())
                self.assertEqual((target / "user.js").read_text(), "keep")
                self.assertFalse(self.backups.exists())
                chrome.unlink()

    def test_directory_in_place_of_file_is_rejected_before_any_backup(self):
        for relative in PROFILE_FILES:
            with self.subTest(relative=relative):
                target = self.profile(relative.replace("/", "-"))
                self.seed_files(target)
                destination = target / relative
                destination.unlink()
                destination.mkdir()
                self.write_ini(f"[InstallABC]\nDefault={target.name}\n")
                self.assertIn("skip", self.install())
                self.assertTrue(destination.is_dir())
                for other in set(PROFILE_FILES) - {relative}:
                    self.assertEqual((target / other).read_text(), "original " + other)
                self.assertFalse(self.backups.exists())

    @unittest.skipIf(os.geteuid() == 0, "root bypasses directory write permissions")
    def test_unwritable_destinations_are_rejected(self):
        target = self.profile()
        self.seed_files(target)
        self.write_ini("[InstallABC]\nDefault=chosen\n")
        for directory in (target, target / "chrome"):
            with self.subTest(directory=directory):
                directory.chmod(0o555)
                try:
                    self.assertIn("skip", self.install())
                    self.assert_original(target)
                    self.assertFalse(self.backups.exists())
                finally:
                    directory.chmod(0o755)

    def test_external_profile_dry_run_and_no_backup(self):
        target = self.root / "external"
        self.seed_files(target)
        self.write_ini(f"[InstallABC]\nDefault={target}\n")
        self.install(dry_run=True)
        self.assert_original(target)
        self.assertFalse(self.backups.exists())
        self.install(no_backup=True)
        self.assert_installed(target)
        self.assertFalse(self.backups.exists())


if __name__ == "__main__":
    unittest.main()
