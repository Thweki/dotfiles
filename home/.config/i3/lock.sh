#!/usr/bin/env sh

set -eu

daemon_mode=0
if [ "${1:-}" = "--daemon" ]; then
  daemon_mode=1
fi

lock_cmd=
if command -v i3lock >/dev/null 2>&1; then
  lock_cmd="i3lock --nofork -c 2d353b"
fi

if [ "$daemon_mode" -eq 1 ]; then
  if [ -n "$lock_cmd" ] && command -v xss-lock >/dev/null 2>&1; then
    exec sh -c "xss-lock --transfer-sleep-lock -- $lock_cmd"
  fi
  exit 0
fi

if [ -n "$lock_cmd" ]; then
  exec sh -c "$lock_cmd"
fi

exit 0
