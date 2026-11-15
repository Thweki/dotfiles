#!/usr/bin/env python3
"""Exercise i3 audio bindings without an i3 session or an audio server."""

import os
from pathlib import Path
import re
import shlex
import shutil
import signal
import subprocess
import tempfile
import time


ROOT = Path(__file__).resolve().parents[1]
CONFIG = (ROOT / "home/.config/i3/config").read_text()
STATUS = ROOT / "home/.config/i3/status.sh"
BINDINGS = {
    "XF86AudioRaiseVolume": "set-sink-volume @DEFAULT_SINK@ +5%",
    "XF86AudioLowerVolume": "set-sink-volume @DEFAULT_SINK@ -5%",
    "XF86AudioMute": "set-sink-mute @DEFAULT_SINK@ toggle",
    "XF86AudioMicMute": "set-source-mute @DEFAULT_SOURCE@ toggle",
}


def write_command(directory, name, body):
    path = directory / name
    path.write_text("#!/usr/bin/env bash\nset -euo pipefail\n" + body)
    path.chmod(0o755)


def wait_for_output(process, output, minimum_lines):
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        assert process.poll() is None, (
            f"status process exited after an audio binding: {process.returncode}"
        )
        if len(output.read_text().splitlines()) >= minimum_lines:
            return
        time.sleep(0.01)
    raise AssertionError("status process stopped producing output")


def main():
    variables = dict(re.findall(r"^set (\$\w+) (.+)$", CONFIG, re.MULTILINE))
    status_path = re.search(r"^\s*status_command (.+)$", CONFIG, re.MULTILINE)
    assert status_path, "missing status_command"

    with tempfile.TemporaryDirectory(prefix="status-volume-keys-") as temporary:
        directory = Path(temporary)
        output = directory / "status.log"
        actions = directory / "audio.log"
        write_command(directory, "pactl", """
case "$1" in
  get-sink-mute) printf 'Mute: no\\n' ;;
  get-sink-volume) printf 'Volume: front-left: 32768 / 50%% / -18.06 dB\\n' ;;
  set-sink-volume|set-sink-mute|set-source-mute) printf '%s\\n' "$*" >> "$AUDIO_LOG" ;;
  *) exit 1 ;;
esac
""")
        # Scope the configured pkill to our child; never signal desktop processes.
        write_command(directory, "pkill", """
[[ $# -eq 3 && $1 == -USR1 && $2 == -f && $3 == "$STATUS_PATH" ]]
kill -USR1 "$STATUS_PID"
""")
        # Shorten only the poll interval so every binding can verify fresh output.
        write_command(directory, "sleep", f"exec {shlex.quote(shutil.which('sleep'))} 0.05\n")
        environment = dict(os.environ, PATH=f"{directory}:{os.environ['PATH']}",
                           AUDIO_LOG=str(actions), STATUS_PATH=status_path[1])
        with output.open("w") as log:
            process = subprocess.Popen(["bash", str(STATUS)], env=environment,
                                       stdout=log, stderr=log, start_new_session=True)
            try:
                environment["STATUS_PID"] = str(process.pid)
                wait_for_output(process, output, 1)
                for key, expected_action in BINDINGS.items():
                    match = re.search(
                        rf"^bindsym {key} exec --no-startup-id (.+)$", CONFIG, re.MULTILINE
                    )
                    assert match, f"missing binding: {key}"
                    command = re.sub(r"\$\w+", lambda match: variables[match[0]], match[1])
                    subprocess.run(["bash", "-c", command], env=environment,
                                   check=True, timeout=3)
                    assert actions.read_text().splitlines()[-1] == expected_action, key
                    # Require continued output after the binding has completed.
                    lines = len(output.read_text().splitlines())
                    wait_for_output(process, output, lines + 2)
                    print(f"PASS: {key} leaves status alive and updating")
            finally:
                # Reap the child and its sleep even if the regression kills Bash.
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                process.wait(timeout=3)


if __name__ == "__main__":
    main()
