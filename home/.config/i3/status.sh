#!/usr/bin/env bash

set -euo pipefail

volume() {
  if command -v pactl >/dev/null 2>&1; then
    local mute level
    mute="$(pactl get-sink-mute @DEFAULT_SINK@ 2>/dev/null | awk '{print $2}')"
    level="$(pactl get-sink-volume @DEFAULT_SINK@ 2>/dev/null | awk 'NR==1 {gsub(/%/, "", $5); print $5}')"
    if [ -n "${level:-}" ]; then
      if [ "$mute" = "yes" ]; then
        printf 'VOL muted'
      else
        printf 'VOL %s%%' "$level"
      fi
      return
    fi
  fi
  printf 'VOL n/a'
}

host() {
  uname -n 2>/dev/null || printf 'host'
}

while true; do
  printf '%s | %s | %s\n' "$(volume)" "$(host)" "$(date '+%Y-%m-%d %H:%M')"
  sleep 5
done
