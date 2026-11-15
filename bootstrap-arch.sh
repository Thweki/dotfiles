#!/usr/bin/env bash

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACKAGE_FILE="${REPO_DIR}/packages-arch.txt"
INSTALL_ARGS=()
DRY_RUN=0

usage() {
  cat <<'EOF'
用法:
  ./bootstrap-arch.sh [--dry-run] [--no-backup]

参数:
  --dry-run    预览依赖安装与文件部署，不执行 sudo/pacman，不修改系统或文件
  --no-backup  调用 install.sh 时不创建备份
  -h, --help   显示帮助
EOF
}

parse_args() {
  while [ "$#" -gt 0 ]; do
    case "$1" in
      --dry-run) DRY_RUN=1; INSTALL_ARGS+=("$1") ;;
      --no-backup) INSTALL_ARGS+=("$1") ;;
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

main() {
  parse_args "$@"

  if [ "$DRY_RUN" -eq 0 ]; then
    if [ ! -f /etc/arch-release ]; then
      printf '当前系统不是 Arch Linux，停止执行。\n' >&2
      exit 1
    fi

    if ! command -v sudo >/dev/null 2>&1; then
      printf '未找到 sudo，无法安装依赖。\n' >&2
      exit 1
    fi

    if ! command -v pacman >/dev/null 2>&1; then
      printf '未找到 pacman，无法安装依赖。\n' >&2
      exit 1
    fi
  fi

  mapfile -t packages < <(grep -vE '^\s*(#|$)' "$PACKAGE_FILE")

  if [ "${#packages[@]}" -gt 0 ]; then
    if [ "$DRY_RUN" -eq 1 ]; then
      printf 'dry-run  sudo pacman -S --needed'
      printf ' %q' "${packages[@]}"
      printf '\n'
    else
      sudo pacman -S --needed "${packages[@]}"
    fi
  fi

  "${REPO_DIR}/install.sh" "${INSTALL_ARGS[@]}"
}

main "$@"
