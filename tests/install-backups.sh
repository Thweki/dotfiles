#!/usr/bin/env bash

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEST_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/dotfiles-backups.XXXXXX")"
trap 'rm -rf "$TEST_ROOT"' EXIT

fail() {
  printf 'FAIL: %s\n' "$*" >&2
  exit 1
}

# Exercise the actual installer with tiny source fixtures and a frozen clock.
FIXTURE_REPO="${TEST_ROOT}/fixture repo"
mkdir -p "$FIXTURE_REPO/home" "$TEST_ROOT/bin"
cp "$REPO_DIR/install.sh" "$FIXTURE_REPO/install.sh"
cat > "$TEST_ROOT/bin/date" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' '20000101-000000'
EOF
chmod +x "$TEST_ROOT/bin/date"
export PATH="$TEST_ROOT/bin:$PATH"

printf 'installed xprofile\n' > "$FIXTURE_REPO/home/.xprofile"
printf 'installed gtkrc\n' > "$FIXTURE_REPO/home/.gtkrc-2.0"
for rel in \
  .config/i3 .config/kitty .config/rofi .config/dunst .config/fcitx5 \
  .config/gtk-3.0 .config/gtk-4.0 .config/Kvantum .config/qt5ct \
  .config/qt6ct .config/nvim .local/share/fcitx5/themes/everforest; do
  mkdir -p "$FIXTURE_REPO/home/$rel"
  printf 'installed directory\n' > "$FIXTURE_REPO/home/$rel/config"
done

seed_home() {
  mkdir -p "$1/.config/i3/nested"
  printf 'original xprofile\n' > "$1/.xprofile"
  printf 'original directory\n' > "$1/.config/i3/nested/original"
}

run_install() {
  local target_home="$1"
  shift
  HOME="$target_home" bash "$FIXTURE_REPO/install.sh" "$@" > "$TEST_ROOT/install.log" 2>&1 || {
    cat "$TEST_ROOT/install.log" >&2
    fail 'installer failed'
  }
}

COLLISION_HOME="$TEST_ROOT/collision home"
seed_home "$COLLISION_HOME"
cp -a "$COLLISION_HOME" "$TEST_ROOT/original"

# A backup made by the old timestamp-only installer must also stay untouched.
LEGACY_ROOT="$COLLISION_HOME/.dotfiles-backup/20000101-000000"
mkdir -p "$LEGACY_ROOT/.config/i3"
printf 'legacy xprofile\n' > "$LEGACY_ROOT/.xprofile"
printf 'legacy directory\n' > "$LEGACY_ROOT/.config/i3/legacy"
cp -a "$LEGACY_ROOT" "$TEST_ROOT/legacy"

run_install "$COLLISION_HOME"
FIRST_ROOT="$(sed -n 's/^Backups are in //p' "$TEST_ROOT/install.log")"
[ -d "$FIRST_ROOT" ] || fail 'first backup directory missing'
[ "$FIRST_ROOT" != "$LEGACY_ROOT" ] || fail 'legacy backup directory reused'
cmp "$TEST_ROOT/original/.xprofile" "$FIRST_ROOT/.xprofile" || fail 'original file lost'
diff -r "$TEST_ROOT/original/.config/i3" "$FIRST_ROOT/.config/i3" || fail 'original directory layout lost'
cp -a "$FIRST_ROOT" "$TEST_ROOT/first backup"

run_install "$COLLISION_HOME"
SECOND_ROOT="$(sed -n 's/^Backups are in //p' "$TEST_ROOT/install.log")"
[ -d "$SECOND_ROOT" ] || fail 'second backup directory missing'
[ "$FIRST_ROOT" != "$SECOND_ROOT" ] || fail 'same-second backup directory reused'
case "$SECOND_ROOT" in
  "$COLLISION_HOME/.dotfiles-backup/20000101-000000."*) ;;
  *) fail 'backup directory not under the timestamped backup root' ;;
esac
diff -r "$TEST_ROOT/first backup" "$FIRST_ROOT" || fail 'first backup changed on rerun'
diff -r "$TEST_ROOT/legacy" "$LEGACY_ROOT" || fail 'legacy backup changed'
cmp "$FIXTURE_REPO/home/.xprofile" "$SECOND_ROOT/.xprofile" || fail 'second file backup incorrect'
diff -r "$FIXTURE_REPO/home/.config/i3" "$SECOND_ROOT/.config/i3" || fail 'second directory backup nested or incorrect'
cmp "$FIXTURE_REPO/home/.xprofile" "$COLLISION_HOME/.xprofile" || fail 'file replacement install changed'
diff -r "$FIXTURE_REPO/home/.config/i3" "$COLLISION_HOME/.config/i3" || fail 'directory replacement install changed'
printf 'PASS: same-second file and directory backups preserve both runs and legacy backups\n'

DRY_HOME="$TEST_ROOT/dry home"
seed_home "$DRY_HOME"
cp -a "$DRY_HOME" "$TEST_ROOT/dry expected"
run_install "$DRY_HOME" --dry-run
diff -r "$TEST_ROOT/dry expected" "$DRY_HOME" || fail 'dry-run wrote to HOME'
[ ! -e "$DRY_HOME/.dotfiles-backup" ] || fail 'dry-run created a backup directory'

cp -a "$COLLISION_HOME" "$TEST_ROOT/collision expected"
run_install "$COLLISION_HOME" --dry-run
diff -r "$TEST_ROOT/collision expected" "$COLLISION_HOME" || fail 'dry-run changed existing backups or installed files'
printf 'PASS: dry-run makes no writes with or without existing backups\n'

NO_BACKUP_HOME="$TEST_ROOT/no backup home"
seed_home "$NO_BACKUP_HOME"
run_install "$NO_BACKUP_HOME" --no-backup
[ ! -e "$NO_BACKUP_HOME/.dotfiles-backup" ] || fail '--no-backup created a backup directory'
cmp "$FIXTURE_REPO/home/.xprofile" "$NO_BACKUP_HOME/.xprofile" || fail '--no-backup file replacement failed'
diff -r "$FIXTURE_REPO/home/.config/i3" "$NO_BACKUP_HOME/.config/i3" || fail '--no-backup directory replacement failed'
printf 'PASS: --no-backup still replaces files and directories without backups\n'
