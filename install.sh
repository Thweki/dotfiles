#!/usr/bin/env bash

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOME_DIR="${HOME}"
SOURCE_HOME="${REPO_DIR}/home"
BACKUP_ROOT="${HOME_DIR}/.dotfiles-backup/$(date +%Y%m%d-%H%M%S)"

backup_if_exists() {
  local target="$1"
  if [ -e "$target" ] || [ -L "$target" ]; then
    local rel="${target#${HOME_DIR}/}"
    local backup_path="${BACKUP_ROOT}/${rel}"
    mkdir -p "$(dirname "$backup_path")"
    mv "$target" "$backup_path"
    printf 'backup  %s -> %s\n' "$target" "$backup_path"
  fi
}

install_path() {
  local rel="$1"
  local src="${SOURCE_HOME}/${rel}"
  local dst="${HOME_DIR}/${rel}"

  backup_if_exists "$dst"
  mkdir -p "$(dirname "$dst")"
  cp -a "$src" "$dst"
  printf 'install  %s\n' "$dst"
}

copy_tree_contents() {
  local src_dir="$1"
  local dst_dir="$2"
  mkdir -p "$dst_dir"
  cp -a "${src_dir}/." "$dst_dir/"
}

install_firefox_profile() {
  local firefox_root="${HOME_DIR}/.config/mozilla/firefox"
  local template_root="${SOURCE_HOME}/.config/mozilla/firefox/profile-template"

  if [ ! -d "$firefox_root" ]; then
    printf 'skip     firefox profile not found at %s\n' "$firefox_root"
    return 0
  fi

  local profile_ini="${firefox_root}/profiles.ini"
  if [ ! -f "$profile_ini" ]; then
    printf 'skip     firefox profiles.ini not found\n'
    return 0
  fi

  local profile_path
  profile_path="$(
    awk -F= '
      /^\[Install/ { in_install=1; next }
      /^\[/ { in_install=0 }
      in_install && $1 == "Default" { print $2; exit }
    ' "$profile_ini"
  )"

  if [ -z "${profile_path}" ]; then
    profile_path="$(
      awk -F= '
        /^\[Profile/ { in_profile=1; path=""; def=0; next }
        /^\[/ { if (in_profile && def && path) { print path; exit } in_profile=0 }
        in_profile && $1 == "Path" { path=$2 }
        in_profile && $1 == "Default" && $2 == "1" { def=1 }
        END { if (in_profile && def && path) print path }
      ' "$profile_ini"
    )"
  fi

  if [ -z "${profile_path}" ]; then
    printf 'skip     firefox default profile not found\n'
    return 0
  fi

  local target_profile="${firefox_root}/${profile_path}"
  mkdir -p "${target_profile}/chrome"

  backup_if_exists "${target_profile}/user.js"
  backup_if_exists "${target_profile}/chrome/userChrome.css"
  backup_if_exists "${target_profile}/chrome/userContent.css"

  cp -a "${template_root}/user.js" "${target_profile}/user.js"
  cp -a "${template_root}/chrome/userChrome.css" "${target_profile}/chrome/userChrome.css"
  cp -a "${template_root}/chrome/userContent.css" "${target_profile}/chrome/userContent.css"
  printf 'install  firefox profile -> %s\n' "$target_profile"
}

main() {
  mkdir -p "$BACKUP_ROOT"

  install_path ".xprofile"
  install_path ".gtkrc-2.0"

  local config_dirs=(
    ".config/i3"
    ".config/kitty"
    ".config/rofi"
    ".config/dunst"
    ".config/fcitx5"
    ".config/gtk-3.0"
    ".config/gtk-4.0"
    ".config/Kvantum"
    ".config/qt5ct"
    ".config/qt6ct"
    ".config/nvim"
  )

  local rel
  for rel in "${config_dirs[@]}"; do
    install_path "$rel"
  done

  mkdir -p "${HOME_DIR}/.local/share/fcitx5/themes"
  backup_if_exists "${HOME_DIR}/.local/share/fcitx5/themes/everforest"
  cp -a "${SOURCE_HOME}/.local/share/fcitx5/themes/everforest" "${HOME_DIR}/.local/share/fcitx5/themes/everforest"
  printf 'install  %s\n' "${HOME_DIR}/.local/share/fcitx5/themes/everforest"

  install_firefox_profile

  printf '\nDone.\n'
  printf 'Backups are in %s\n' "$BACKUP_ROOT"
}

main "$@"

