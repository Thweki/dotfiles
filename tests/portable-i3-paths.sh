#!/usr/bin/env bash

set -euo pipefail

REPO_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
TEST_ROOT="$(mktemp -d)"
trap 'rm -rf -- "$TEST_ROOT"' EXIT

fail() {
  printf 'FAIL: %s\n' "$*" >&2
  exit 1
}

# No desktop programs or process signals may escape these tests.
STUB_BIN="$TEST_ROOT/bin"
mkdir -p "$STUB_BIN"
ln -s /bin/sh "$STUB_BIN/sh"
ln -s "$(command -v dirname)" "$STUB_BIN/dirname"
cat > "$STUB_BIN/pgrep" <<'EOF'
#!/bin/sh
exit 1
EOF
cat > "$STUB_BIN/record" <<'EOF'
#!/bin/sh
printf '%s\n' "$@" > "$TEST_LOG/${0##*/}"
EOF
chmod +x "$STUB_BIN/pgrep" "$STUB_BIN/record"
for program in xss-lock i3lock xsetroot pkill; do
  ln -s record "$STUB_BIN/$program"
done

check_launch() {
  local helper="$1" command="$2"
  [[ -n "$command" && "$command" != *$'\n'* ]] || fail "missing or duplicate $helper command"
  rm -f -- "$TEST_LOG/launch"
  HOME="$test_home" PATH="$STUB_BIN" /bin/sh -c "$command"
  [[ "$(cat "$TEST_LOG/launch")" == "$i3_dir/$helper" ]] || fail "$helper launch path"
}

check_home() {
  local label="$1" test_home="$2" i3_dir
  i3_dir="$test_home/.config/i3"
  export TEST_LOG="$TEST_ROOT/log-$label"
  mkdir -p "$test_home" "$TEST_LOG"

  # Exercise the real installer, confined to a fresh temporary HOME.
  HOME="$test_home" bash "$REPO_DIR/install.sh" --no-backup > "$TEST_LOG/install"

  # Source with the installed script's $0 so we can wait for run_once's child.
  # HOME and cwd deliberately differ from the helper directory: siblings must
  # resolve from the script, even when the installed tree is moved.
  (
    cd /
    HOME="$TEST_ROOT/unused-home" PATH="$STUB_BIN" CDPATH=/tmp \
      /bin/sh -c '. "$0"; wait' "$i3_dir/autostart.sh"
  )
  printf '%s\n' --transfer-sleep-lock -- i3lock --nofork -c 2d353b | \
    diff -u - "$TEST_LOG/xss-lock"
  printf '%s\n' -solid '#2d353b' | diff -u - "$TEST_LOG/xsetroot"

  # Replace installed entry points with recorders; executing config commands
  # through /bin/sh checks tilde expansion and word boundaries without i3/X11.
  for helper in autostart.sh toggle-scratchpad-note.sh lock.sh status.sh; do
    cat > "$i3_dir/$helper" <<'EOF'
#!/bin/sh
[ "$#" -eq 0 ] || exit 1
printf '%s\n' "$0" > "$TEST_LOG/launch"
EOF
  done

  local config="$i3_dir/config"
  check_launch autostart.sh "$(sed -n 's/^exec_always --no-startup-id //p' "$config")"
  check_launch toggle-scratchpad-note.sh "$(sed -n 's/^bindsym \$mod+t exec --no-startup-id //p' "$config")"
  check_launch lock.sh "$(sed -n 's/^bindsym \$mod+Shift+x exec --no-startup-id //p' "$config")"
  check_launch status.sh "$(sed -n 's/^[[:space:]]*status_command //p' "$config")"

  # Inspect pkill's arguments using a stub; never signal a real process.
  local refresh
  refresh="$(sed -n 's/^set \$refresh_i3status //p' "$config")"
  [[ -n "$refresh" ]] || fail 'missing status lookup'
  HOME="$test_home" PATH="$STUB_BIN" /bin/sh -c "$refresh"
  printf '%s\n' -USR1 -f "$i3_dir/status.sh" | diff -u - "$TEST_LOG/pkill"
  printf 'PASS: %s\n' "$label"
}

# Model the original default home without writing into a real user's home.
check_home default-home "$TEST_ROOT/default/home/thweki"
check_home alternate-home "$TEST_ROOT/alternate/home/alice"
check_home home-with-spaces "$TEST_ROOT/home with spaces"
