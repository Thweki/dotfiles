"""Validate HOME before installer mutations; never write to unsafe test paths."""

import os
from pathlib import Path
import subprocess
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[1]
MODES = ((), ("--no-backup",), ("--dry-run",), ("--dry-run", "--no-backup"))


class InstallerHomeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="dotfiles-home-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.home = self.root / "home with spaces"
        self.home.mkdir()
        (self.home / ".xprofile").write_text("original xprofile\n")
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.mutations = self.root / "mutations"
        # Unsafe HOME cases must remain harmless even against the old installer.
        for command in ("mkdir", "mv", "rm", "cp"):
            stub = self.bin / command
            stub.write_text(
                '#!/bin/sh\nprintf "%s\\n" "$0" >> "$MUTATION_LOG"\nexit 97\n'
            )
            stub.chmod(0o755)

    def install(self, home, args=(), block_mutations=True):
        env = {"PATH": os.defpath, "LC_ALL": "C", "MUTATION_LOG": str(self.mutations)}
        if home is not None:
            env["HOME"] = str(home)
        if block_mutations:
            env["PATH"] = str(self.bin) + os.pathsep + env["PATH"]
        return subprocess.run(
            ["bash", str(REPO / "install.sh"), *args],
            cwd=self.root, env=env, capture_output=True, text=True, timeout=10,
        )

    def assert_rejected(self, home):
        for args in MODES:
            with self.subTest(home=home, args=args):
                self.mutations.unlink(missing_ok=True)
                result = self.install(home, args)
                self.assertFalse(self.mutations.exists(), "attempted a filesystem mutation")
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("Invalid HOME", result.stderr)

    def test_unset_empty_and_relative_home_are_rejected(self):
        for home in (None, "", ".", self.home.name, "-invalid"):
            self.assert_rejected(home)

    def test_root_and_root_aliases_are_rejected(self):
        root_link = self.root / "root link"
        root_link.symlink_to("/", target_is_directory=True)
        for home in ("/", "//", "/./", "/tmp/..", root_link, str(root_link) + "/.."):
            self.assert_rejected(home)

    def test_missing_home_file_and_dangling_link_are_rejected(self):
        missing = self.root / "missing"
        dangling = self.root / "dangling"
        dangling.symlink_to(missing, target_is_directory=True)
        for home in (missing, self.home / ".xprofile", dangling):
            self.assert_rejected(home)

    def test_help_does_not_require_home(self):
        result = self.install(None, ("--help",))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--dry-run", result.stdout)
        self.assertFalse(self.mutations.exists())

    def test_valid_homes_support_install_backup_and_preview(self):
        for spelling in ("absolute", "symlink", "trailing-slash", "parent-component"):
            for args in MODES:
                with self.subTest(spelling=spelling, args=args):
                    home = self.root / (spelling + " home-" + str(len(args)) + "-" + "_".join(args))
                    home.mkdir()
                    (home / ".xprofile").write_text("original xprofile\n")
                    alias = str(home)
                    if spelling == "symlink":
                        link = self.root / (home.name + " link")
                        link.symlink_to(home, target_is_directory=True)
                        alias = str(link)
                    elif spelling == "trailing-slash":
                        alias += "/"
                    elif spelling == "parent-component":
                        alias = str(self.home) + "/../" + home.name
                    result = self.install(alias, args, block_mutations=False)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    if "--dry-run" in args:
                        self.assertEqual(list(home.iterdir()), [home / ".xprofile"])
                        self.assertEqual((home / ".xprofile").read_text(), "original xprofile\n")
                        continue
                    for relative in (".xprofile", ".config/i3/config",
                                     ".local/share/fcitx5/themes/everforest/theme.conf"):
                        self.assertEqual((home / relative).read_bytes(),
                                         (REPO / "home" / relative).read_bytes())
                    backups = list((home / ".dotfiles-backup").glob("*/.xprofile"))
                    if "--no-backup" in args:
                        self.assertFalse((home / ".dotfiles-backup").exists())
                    else:
                        self.assertEqual(len(backups), 1)
                        self.assertEqual(backups[0].read_text(), "original xprofile\n")


if __name__ == "__main__":
    unittest.main()
