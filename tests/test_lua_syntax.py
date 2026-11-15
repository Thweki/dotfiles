"""Checker regressions; real parser tests require the same lua5.1 package as CI."""

from contextlib import redirect_stderr, redirect_stdout
import io
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from scripts.check_lua import check_lua


class LuaSyntaxTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="dotfiles lua ")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.enterContext(redirect_stdout(io.StringIO()))
        self.stderr = self.enterContext(redirect_stderr(io.StringIO()))

    def write_lua(self, name, content):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    def test_recurses_and_preserves_paths_with_spaces(self):
        files = [
            self.write_lua("init.lua", "return {}"),
            self.write_lua("lua/plugins/new plugin.lua", "return {}"),
        ]
        self.write_lua("README.md", "not Lua")
        with patch("scripts.check_lua.subprocess.run") as run:
            run.return_value = subprocess.CompletedProcess([], 0)
            self.assertEqual(check_lua(self.root), 0)
        self.assertEqual(
            [call.args[0] for call in run.call_args_list],
            [["luac5.1", "-p", str(path)] for path in files],
        )

    def test_parser_failure_fails_check(self):
        self.write_lua("init.lua", "return {")
        with patch("scripts.check_lua.subprocess.run") as run:
            run.return_value = subprocess.CompletedProcess([], 1)
            self.assertEqual(check_lua(self.root), 1)

    def test_missing_compiler_fails_check(self):
        self.write_lua("init.lua", "return {}")
        with patch("scripts.check_lua.subprocess.run", side_effect=FileNotFoundError):
            self.assertEqual(check_lua(self.root), 1)
        self.assertIn("luac5.1 is required", self.stderr.getvalue())

    def test_empty_or_missing_tree_fails_check(self):
        with patch("scripts.check_lua.subprocess.run") as run:
            self.assertEqual(check_lua(self.root), 1)
            self.assertEqual(check_lua(self.root / "missing"), 1)
        run.assert_not_called()

    @unittest.skipUnless(shutil.which("luac5.1"), "luac5.1 is not installed")
    def test_real_parser_rejects_nested_syntax_error(self):
        self.write_lua("init.lua", "return {}")
        self.write_lua("lua/plugins/broken plugin.lua", "return {")
        self.assertEqual(check_lua(self.root), 1)

    @unittest.skipUnless(shutil.which("luac5.1"), "luac5.1 is not installed")
    def test_real_parser_does_not_execute_code_or_emit_bytecode(self):
        marker = self.root / "executed"
        self.write_lua("init.lua", f'io.open("{marker}", "w"):close()\nerror("executed")')
        # luac writes bytecode in its working directory unless parse-only is used.
        original_run = subprocess.run
        with patch(
            "scripts.check_lua.subprocess.run",
            side_effect=lambda *args, **kwargs: original_run(*args, cwd=self.root, **kwargs),
        ):
            self.assertEqual(check_lua(self.root), 0)
        self.assertEqual(sorted(p.name for p in self.root.iterdir()), ["init.lua"])


if __name__ == "__main__":
    unittest.main()
