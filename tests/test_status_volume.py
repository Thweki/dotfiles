#!/usr/bin/env python3
"""Run the real status loop with isolated audio, clock, and sleep commands."""

import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
STATUS = ROOT / "home/.config/i3/status.sh"
BASH = shutil.which("bash")
AWK = shutil.which("awk")


class StatusVolumeTests(unittest.TestCase):
    def run_status(self, frames, *, missing_pactl=False, audio_exit=0):
        with tempfile.TemporaryDirectory(prefix="status-volume-") as temporary:
            directory = Path(temporary)
            tick = directory / "tick"
            tick.write_text("1\n")
            calls = directory / "calls"
            calls.touch()

            def command(name, body):
                path = directory / name
                path.write_text(f"#!{BASH}\nset -eu\n" + body)
                path.chmod(0o755)

            # Forward awk so the original script still renders correctly; the
            # process-count assertion must detect the optimization independently.
            command("awk", 'printf "awk\\n" >> "$CALLS"\n'
                    f'exec {shlex.quote(AWK)} "$@"\n')
            if not missing_pactl:
                body = 'printf "%s\\n" "$*" >> "$CALLS"\n'
                body += 'case "$1:$(< "$TICK")" in\n'
                for index, (mute, volume) in enumerate(frames, 1):
                    for operation, output in (("get-sink-mute", mute),
                                              ("get-sink-volume", volume)):
                        body += (f"  {operation}:{index}) printf '%s' "
                                 f"{shlex.quote(output)} ;;\n")
                body += f"  *) exit 99 ;;\nesac\nexit {audio_exit}\n"
                command("pactl", body)
            command("uname", '[[ "$*" == -n ]]\nprintf "test-host\\n"\n')
            command("date", '[[ "$*" == "+%Y-%m-%d %H:%M" ]]\n'
                    'printf "2026-11-15 12:34\\n"\n')
            # End the otherwise infinite loop after a deterministic number of
            # updates, without waiting or leaving background processes behind.
            command("sleep", '[[ "$*" == 5 ]]\ntick=$(< "$TICK")\n'
                    f'(( tick < {len(frames)} )) || exit 42\n'
                    'printf "%s\\n" "$((tick + 1))" > "$TICK"\n')
            result = subprocess.run(
                [BASH, str(STATUS)], text=True, capture_output=True, timeout=5,
                env=dict(os.environ, PATH=str(directory), TICK=str(tick),
                         CALLS=str(calls)),
            )
            self.assertEqual(result.returncode, 42, result.stderr)
            self.assertEqual(result.stderr, "")
            return result.stdout.splitlines(), calls.read_text().splitlines()

    def assert_lines(self, lines, volumes):
        self.assertEqual(lines, [
            f"VOL {volume} | test-host | 2026-11-15 12:34"
            for volume in volumes
        ])

    def test_volume_and_mute_refresh_on_every_poll(self):
        frames = [
            ("Mute: no\n", "Volume: front-left: 32768 / 50% / -18.06 dB,"
             " front-right: 65536 / 100% / 0.00 dB\n        balance 0.50\n"),
            ("Mute: yes\n", "Volume: mono: 0 / 0% / -inf dB\n"),
            ("Mute: no\n", "\tVolume:  mono:  81920  /  125%  /  5.81 dB\n"),
        ]
        lines, calls = self.run_status(frames)
        self.assert_lines(lines, ["50%", "muted", "125%"])
        self.assertEqual([call for call in calls if call != "awk"], [
            "get-sink-mute @DEFAULT_SINK@",
            "get-sink-volume @DEFAULT_SINK@",
        ] * 3)

    def test_polling_does_not_spawn_awk(self):
        frames = [("Mute: no\n", "Volume: mono: 32768 / 50% / -18.06 dB\n")] * 3
        lines, calls = self.run_status(frames)
        self.assert_lines(lines, ["50%"] * 3)
        self.assertNotIn("awk", calls, "volume parsing should use Bash builtins")

    def test_missing_pactl(self):
        lines, calls = self.run_status([("", "")] * 2, missing_pactl=True)
        self.assert_lines(lines, ["n/a"] * 2)
        self.assertEqual(calls, [])

    def test_empty_or_failed_audio_output(self):
        for audio_exit in (0, 1):
            with self.subTest(audio_exit=audio_exit):
                lines, _ = self.run_status([("", "")] * 2, audio_exit=audio_exit)
                self.assert_lines(lines, ["n/a"] * 2)

    def test_zero_volume_and_missing_level(self):
        lines, _ = self.run_status([
            ("Mute: no\n", "Volume: mono: 0 / 0% / -inf dB\n"),
            ("Mute: yes\n", "Volume:\n"),
        ])
        self.assert_lines(lines, ["0%", "n/a"])


if __name__ == "__main__":
    unittest.main()
