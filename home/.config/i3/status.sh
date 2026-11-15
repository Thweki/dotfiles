#!/usr/bin/env bash

set -euo pipefail

volume() {
  if command -v pactl >/dev/null 2>&1; then
    local mute level _
    read -r _ mute _ <<< "$(pactl get-sink-mute @DEFAULT_SINK@ 2>/dev/null)"
    read -r _ _ _ _ level _ <<< "$(pactl get-sink-volume @DEFAULT_SINK@ 2>/dev/null)"
    level="${level//%/}"
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
