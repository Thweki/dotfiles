#!/usr/bin/env bash

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACKAGE_FILE="${REPO_DIR}/packages-arch.txt"
INSTALL_ARGS=()

usage() {
  cat <<'EOF'
用法:
  ./bootstrap-arch.sh [--dry-run] [--no-backup]

参数:
  --dry-run    安装依赖后，以演练模式执行 install.sh
  --no-backup  调用 install.sh 时不创建备份
  -h, --help   显示帮助
EOF
}

parse_args() {
  while [ "$#" -gt 0 ]; do
    case "$1" in
      --dry-run|--no-backup) INSTALL_ARGS+=("$1") ;;
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

  mapfile -t packages < <(grep -vE '^\s*(#|$)' "$PACKAGE_FILE")

  if [ "${#packages[@]}" -gt 0 ]; then
    sudo pacman -S --needed "${packages[@]}"
  fi

  "${REPO_DIR}/install.sh" "${INSTALL_ARGS[@]}"
}

main "$@"
