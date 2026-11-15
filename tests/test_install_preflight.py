"""Reject incomplete installer payloads before touching an existing home."""

from contextlib import contextmanager
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[1]
FILES = (
    ".xprofile", ".gtkrc-2.0",
    ".config/mozilla/firefox/profile-template/user.js",
    ".config/mozilla/firefox/profile-template/chrome/userChrome.css",
    ".config/mozilla/firefox/profile-template/chrome/userContent.css",
)
DIRECTORIES = tuple(".config/" + name for name in (
    "i3", "kitty", "rofi", "dunst", "fcitx5", "gtk-3.0", "gtk-4.0",
    "Kvantum", "qt5ct", "qt6ct", "nvim",
)) + (".local/share/fcitx5/themes/everforest",)


def snapshot(root):
    return {
        str(path.relative_to(root)): (
            path.lstat().st_mode, path.lstat().st_mtime_ns,
            os.readlink(path) if path.is_symlink() else
            path.read_bytes() if path.is_file() else None,
        )
        for path in (root, *root.rglob("*"))
    }


@contextmanager
def fixture():
    with tempfile.TemporaryDirectory(prefix="dotfiles-preflight-") as temporary:
        root = Path(temporary)
        repo = root / "repo with spaces"
        repo.mkdir()
        shutil.copy2(REPO / "install.sh", repo / "install.sh")
        shutil.copytree(REPO / "home", repo / "home")
        home = root / "home with spaces"
        home.mkdir()
        (home / ".xprofile").write_text("original xprofile\n")
        (home / ".gtkrc-2.0").symlink_to("missing-target")
        for relative in DIRECTORIES:
            target = home / relative
            target.mkdir(parents=True)
            (target / "keep").write_text("original directory\n")
        profile = home / ".config/mozilla/firefox/chosen"
        (profile / "chrome").mkdir(parents=True)
        (profile.parent / "profiles.ini").write_text("[InstallTest]\nDefault=chosen\n")
        for relative in ("user.js", "chrome/userChrome.css", "chrome/userContent.css"):
            (profile / relative).write_text("original Firefox\n")
        yield repo, home


def install(repo, home, *args):
    return subprocess.run(
        ["bash", str(repo / "install.sh"), *args],
        cwd=repo.parent,
        env={"HOME": str(home), "PATH": os.defpath, "LC_ALL": "C.UTF-8"},
        capture_output=True, text=True, timeout=10,
    )


class InstallerPreflightTests(unittest.TestCase):
    def check_rejected(self, relative, args, replacement=None):
        with fixture() as (repo, home):
            source = repo / "home" / relative
            was_directory = source.is_dir()
            if was_directory:
                shutil.rmtree(source)
            else:
                source.unlink()
            if replacement == "wrong-type":
                if was_directory:
                    source.write_text("not a directory\n")
                else:
                    source.mkdir()
            elif replacement == "dangling-link":
                source.symlink_to("missing-source")
            before = snapshot(home)
            result = install(repo, home, *args)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(snapshot(home), before, "installer modified home")
            self.assertIn(str(source), result.stderr)

    def test_missing_sources_preserve_home_with_and_without_backups(self):
        for relative in FILES + DIRECTORIES:
            for args in ((), ("--no-backup",)):
                with self.subTest(source=relative, args=args):
                    self.check_rejected(relative, args)

    def test_wrong_source_types_preserve_home(self):
        for relative in (FILES[0], FILES[-1], DIRECTORIES[0], DIRECTORIES[-1]):
            for args in ((), ("--no-backup",)):
                with self.subTest(source=relative, args=args):
                    self.check_rejected(relative, args, "wrong-type")

    def test_dangling_sources_preserve_home(self):
        for relative in (FILES[0], DIRECTORIES[0]):
            with self.subTest(source=relative):
                self.check_rejected(relative, ("--no-backup",), "dangling-link")

    def test_dry_run_reports_incomplete_payload_without_writes(self):
        for args in (("--dry-run",), ("--dry-run", "--no-backup")):
            with self.subTest(args=args):
                self.check_rejected(DIRECTORIES[-1], args)

    def test_complete_payload_still_installs(self):
        for args in ((), ("--no-backup",)):
            with self.subTest(args=args), fixture() as (repo, home):
                result = install(repo, home, *args)
                self.assertEqual(result.returncode, 0, result.stderr)
                for relative in (".xprofile", ".config/i3/config",
                                 ".local/share/fcitx5/themes/everforest/theme.conf"):
                    self.assertTrue((home / relative).read_bytes() ==
                                    (repo / "home" / relative).read_bytes())
                self.assertEqual((home / ".dotfiles-backup").exists(), not args)


if __name__ == "__main__":
    unittest.main()
