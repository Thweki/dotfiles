#!/usr/bin/env bash

set -euo pipefail

class_name="scratchpad-term"
title_name="scratchpad-note"
session_name="scratchpad"

tree_objects() {
  i3-msg -t get_tree | sed 's/},{/},\n{/g'
}

window_exists() {
  tree_objects | grep -F "\"class\":\"${class_name}\"" >/dev/null 2>&1
}

window_visible() {
  tree_objects | grep -F "\"class\":\"${class_name}\"" | grep -Fv '"output":"__i3"' >/dev/null 2>&1
}

show_window() {
  i3-msg "scratchpad show" >/dev/null
}

hide_window() {
  i3-msg "[class=\"^${class_name}\$\"] move scratchpad" >/dev/null
}

spawn_window() {
  kitty --class "${class_name}" --title "${title_name}" tmux new-session -A -s "${session_name}" >/dev/null 2>&1 &
  for _ in $(seq 1 30); do
    if window_exists; then
      break
    fi
    sleep 0.1
  done
  show_window
}

if ! window_exists; then
  spawn_window
elif window_visible; then
  hide_window
else
  show_window
fi
