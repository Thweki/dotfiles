#!/usr/bin/env bash

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOME_DIR="${HOME}"
SOURCE_HOME="${REPO_DIR}/home"
BACKUP_ROOT="${HOME_DIR}/.dotfiles-backup/$(date +%Y%m%d-%H%M%S)"
DRY_RUN=0
NO_BACKUP=0

usage() {
  cat <<'EOF'
用法:
  ./install.sh [--dry-run] [--no-backup]

参数:
  --dry-run    仅显示将要执行的动作，不实际修改文件
  --no-backup  覆盖已有文件时不创建备份
  -h, --help   显示帮助
EOF
}

log_action() {
  printf '%-8s %s\n' "$1" "$2"
}

run_cmd() {
  if [ "$DRY_RUN" -eq 1 ]; then
    log_action "dry-run" "$*"
    return 0
  fi
  "$@"
}

parse_args() {
  while [ "$#" -gt 0 ]; do
    case "$1" in
      --dry-run) DRY_RUN=1 ;;
      --no-backup) NO_BACKUP=1 ;;
      -h|--help)
        usage
        exit 0
        ;;
      *)
        printf '未知参数: %s\n' "$1" >&2
        usage >&2
        exit 1
        ;;
    esac
    shift
  done
}

backup_if_exists() {
  local target="$1"
  if [ ! -e "$target" ] && [ ! -L "$target" ]; then
    return 0
  fi

  if [ "$NO_BACKUP" -eq 1 ]; then
    log_action "remove" "$target"
    run_cmd rm -rf "$target"
    return 0
  fi

  local rel
  case "$target" in
    "${HOME_DIR}/"*) rel="${target#"${HOME_DIR}/"}" ;;
    /*) rel="external/${target#/}" ;;
    *) printf 'Backup target must be absolute: %s\n' "$target" >&2; return 1 ;;
  esac
  local backup_path="${BACKUP_ROOT}/${rel}"
  log_action "backup" "${target} -> ${backup_path}"

  if [ "$DRY_RUN" -eq 1 ]; then
    return 0
  fi

  mkdir -p "$(dirname "$backup_path")"
  mv "$target" "$backup_path"
}

install_path() {
  local rel="$1"
  local src="${SOURCE_HOME}/${rel}"
  local dst="${HOME_DIR}/${rel}"

  backup_if_exists "$dst"
  log_action "install" "$dst"

  if [ "$DRY_RUN" -eq 1 ]; then
    return 0
  fi

  mkdir -p "$(dirname "$dst")"
  cp -a "$src" "$dst"
}

select_firefox_profile() {
  local profile_ini="$1"
  local firefox_root="$2"
  awk -v root="$firefox_root" '
    function finish_section() {
      if (in_profile && def && path != "" && !profile_found) {
        profile_path=path
        profile_relative=relative
        profile_found=1
      }
    }
    { sub(/\r$/, "") }
    /^\[/ {
      finish_section()
      in_profile=($0 ~ /^\[Profile[^]]*\]$/)
      in_install=($0 ~ /^\[Install[^]]*\]$/)
      path=""
      def=0
      relative="1"
      next
    }
    {
      separator=index($0, "=")
      if (!separator) next
      key=substr($0, 1, separator-1)
      value=substr($0, separator+1)
      if (in_install && key == "Default" && value != "" && install_path == "")
        install_path=value
      if (in_profile && key == "Path") path=value
      if (in_profile && key == "IsRelative") relative=value
      if (in_profile && key == "Default") def=(value == "1")
    }
    END {
      finish_section()
      if (install_path != "") {
        path=install_path
        relative=(substr(path, 1, 1) == "/" ? "0" : "1")
      } else if (profile_found) {
        path=profile_path
        relative=profile_relative
      } else exit

      if (relative == "0" && substr(path, 1, 1) == "/") print path
      else if (relative == "1" && substr(path, 1, 1) != "/") print root "/" path
    }
  ' "$profile_ini"
}

install_firefox_profile() {
  local firefox_root="${HOME_DIR}/.config/mozilla/firefox"
  local template_root="${SOURCE_HOME}/.config/mozilla/firefox/profile-template"

  if [ ! -d "$firefox_root" ]; then
    log_action "skip" "firefox profile not found at ${firefox_root}"
    return 0
  fi

  local profile_ini="${firefox_root}/profiles.ini"
  if [ ! -f "$profile_ini" ]; then
    log_action "skip" "firefox profiles.ini not found"
    return 0
  fi

  local target_profile
  target_profile="$(select_firefox_profile "$profile_ini" "$firefox_root")"
  if [ -z "$target_profile" ]; then
    log_action "skip" "firefox default profile not found"
    return 0
  fi

  # Resolve existing directories before constructing backup paths, including ../ paths.
  if ! target_profile="$(cd -- "$target_profile" 2>/dev/null && pwd -P)"; then
    log_action "skip" "firefox profile directory not found"
    return 0
  fi

  if [ ! -w "$target_profile" ] ||
    { { [ -e "${target_profile}/chrome" ] || [ -L "${target_profile}/chrome" ]; } &&
      { [ ! -d "${target_profile}/chrome" ] || [ ! -w "${target_profile}/chrome" ]; }; }; then
    log_action "skip" "invalid firefox profile destination: ${target_profile}"
    return 0
  fi

  local destination
  for destination in user.js chrome/userChrome.css chrome/userContent.css; do
    if [ -e "${target_profile}/${destination}" ] && [ ! -f "${target_profile}/${destination}" ]; then
      log_action "skip" "invalid firefox file destination: ${target_profile}/${destination}"
      return 0
    fi
  done

  log_action "install" "firefox profile -> ${target_profile}"

  backup_if_exists "${target_profile}/user.js"
  backup_if_exists "${target_profile}/chrome/userChrome.css"
  backup_if_exists "${target_profile}/chrome/userContent.css"

  if [ "$DRY_RUN" -eq 1 ]; then
    return 0
  fi

  mkdir -p "${target_profile}/chrome"
  cp -a "${template_root}/user.js" "${target_profile}/user.js"
  cp -a "${template_root}/chrome/userChrome.css" "${target_profile}/chrome/userChrome.css"
  cp -a "${template_root}/chrome/userContent.css" "${target_profile}/chrome/userContent.css"
}

main() {
  parse_args "$@"

  if [ "$DRY_RUN" -eq 0 ] && [ "$NO_BACKUP" -eq 0 ]; then
    mkdir -p "$BACKUP_ROOT"
  fi

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

  backup_if_exists "${HOME_DIR}/.local/share/fcitx5/themes/everforest"
  log_action "install" "${HOME_DIR}/.local/share/fcitx5/themes/everforest"
  if [ "$DRY_RUN" -eq 0 ]; then
    mkdir -p "${HOME_DIR}/.local/share/fcitx5/themes"
    cp -a "${SOURCE_HOME}/.local/share/fcitx5/themes/everforest" "${HOME_DIR}/.local/share/fcitx5/themes/everforest"
  fi

  install_firefox_profile

  printf '\nDone.\n'
  if [ "$NO_BACKUP" -eq 0 ]; then
    printf 'Backups are in %s\n' "$BACKUP_ROOT"
  fi
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  main "$@"
fi
