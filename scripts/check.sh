#!/usr/bin/env bash

set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

shell_files=(home/.xprofile)
while IFS= read -r -d '' file; do
  shell_files+=("$file")
done < <(find . -name .git -prune -o -type f -name '*.sh' -print0)

dialect() {
  if [[ "$1" == home/.xprofile ]]; then
    printf 'sh\n'
    return
  fi
  local shebang
  IFS= read -r shebang < "$1"
  case "$shebang" in
    '#!'*bash*) printf 'bash\n' ;;
    '#!'*sh*) printf 'sh\n' ;;
    *) printf 'Unknown shell dialect: %s\n' "$1" >&2; return 1 ;;
  esac
}

syntax() {
  local file shell
  for file in "${shell_files[@]}"; do
    shell="$(dialect "$file")"
    "$shell" -n "$file"
    printf 'PASS syntax (%s): %s\n' "$shell" "$file"
  done
}

payload() {
  local file directory
  local helpers=(
    home/.config/i3/autostart.sh home/.config/i3/lock.sh
    home/.config/i3/status.sh home/.config/i3/theme.sh
    home/.config/i3/toggle-scratchpad-note.sh
  )
  local files=(
    README.md post-install.md packages-arch.txt packages-arch-aur.txt
    install.sh bootstrap-arch.sh home/.xprofile home/.gtkrc-2.0
    home/.config/i3/config home/.config/kitty/kitty.conf
    home/.config/rofi/config.rasi home/.config/dunst/dunstrc
    home/.config/fcitx5/config home/.config/fcitx5/profile
    home/.config/gtk-3.0/settings.ini home/.config/gtk-3.0/gtk.css
    home/.config/gtk-4.0/settings.ini home/.config/gtk-4.0/gtk.css
    home/.config/Kvantum/kvantum.kvconfig
    home/.config/Kvantum/Everforest/Everforest.kvconfig
    home/.config/qt5ct/qt5ct.conf home/.config/qt6ct/qt6ct.conf
    home/.config/nvim/init.lua home/.config/nvim/lua/lazy_setup.lua
    home/.local/share/fcitx5/themes/everforest/theme.conf
    home/.config/mozilla/firefox/profile-template/user.js
    home/.config/mozilla/firefox/profile-template/chrome/userChrome.css
    home/.config/mozilla/firefox/profile-template/chrome/userContent.css
  )
  for file in "${files[@]}" "${helpers[@]}"; do
    if [[ ! -s "$file" ]]; then
      printf 'Missing or empty payload file: %s\n' "$file" >&2
      return 1
    fi
  done
  for directory in i3 kitty rofi dunst fcitx5 gtk-3.0 gtk-4.0 Kvantum qt5ct qt6ct nvim; do
    test -d "home/.config/$directory"
  done
  for file in install.sh bootstrap-arch.sh "${helpers[@]}"; do
    if [[ ! -x "$file" ]]; then
      printf 'Payload script is not executable: %s\n' "$file" >&2
      return 1
    fi
  done
  printf 'PASS payload files, directories, and executable permissions\n'
}

lint() {
  if ! command -v shellcheck >/dev/null 2>&1; then
    printf 'SKIP ShellCheck: shellcheck is not installed (CI installs it).\n'
    return
  fi
  local file shell
  for file in "${shell_files[@]}"; do
    shell="$(dialect "$file")"
    shellcheck --severity=warning --shell="$shell" "$file"
    printf 'PASS ShellCheck (%s): %s\n' "$shell" "$file"
  done
}

tests() {
  python3 -B -m unittest discover -s tests -v
}

case "${1:-all}" in
  syntax) syntax ;;
  payload) payload ;;
  lint) lint ;;
  tests) tests ;;
  all) syntax; payload; lint; tests ;;
  *) printf 'Usage: bash scripts/check.sh [all|syntax|payload|lint|tests]\n' >&2; exit 2 ;;
esac
