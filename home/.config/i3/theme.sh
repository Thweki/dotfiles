#!/usr/bin/env sh

set -eu

BG="#2d353b"

if command -v xsetroot >/dev/null 2>&1; then
  xsetroot -solid "$BG" >/dev/null 2>&1 || true
  exit 0
fi

if command -v hsetroot >/dev/null 2>&1; then
  hsetroot -solid "$BG" >/dev/null 2>&1 || true
  exit 0
fi

if command -v feh >/dev/null 2>&1; then
  feh --bg-fill "$HOME/.config/i3/background.png" >/dev/null 2>&1 || true
  exit 0
fi

exit 0
