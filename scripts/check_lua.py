"""Parse Neovim's Lua 5.1 configuration without executing it or loading plugins."""

from pathlib import Path
import subprocess
import sys


def check_lua(root):
    files = sorted(root.rglob("*.lua"))
    if not files:
        print(f"No Lua files found in {root}", file=sys.stderr)
        return 1

    for path in files:
        try:
            result = subprocess.run(["luac5.1", "-p", str(path)], check=False)
        except FileNotFoundError:
            print("luac5.1 is required; install the lua5.1 package.", file=sys.stderr)
            return 1
        if result.returncode:
            return 1
    print(f"PASS Lua 5.1 syntax: {len(files)} files")
    return 0


if __name__ == "__main__":
    sys.exit(check_lua(Path(__file__).resolve().parents[1] / "home/.config/nvim"))
