#!/usr/bin/env sh

set -eu

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"

run_once() {
  proc_name="$1"
  shift

  if pgrep -x "$proc_name" >/dev/null 2>&1; then
    return 0
  fi

  "$@" >/dev/null 2>&1 &
}

if command -v dex >/dev/null 2>&1; then
  run_once dex dex --autostart --environment i3
fi

if command -v nm-applet >/dev/null 2>&1; then
  run_once nm-applet nm-applet
fi

if command -v fcitx5 >/dev/null 2>&1; then
  run_once fcitx5 fcitx5 -d
fi

if command -v dunst >/dev/null 2>&1; then
  run_once dunst dunst
fi

if command -v xss-lock >/dev/null 2>&1 && command -v i3lock >/dev/null 2>&1; then
  run_once xss-lock "$SCRIPT_DIR/lock.sh" --daemon
fi

if command -v vmware-user-suid-wrapper >/dev/null 2>&1; then
  run_once vmware-user-suid-wrapper vmware-user-suid-wrapper
fi

"$SCRIPT_DIR/theme.sh"

if command -v xrandr >/dev/null 2>&1; then
  xrandr --output Virtual-1 --auto >/dev/null 2>&1 || true
fi
