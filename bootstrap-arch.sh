#!/usr/bin/env bash

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACKAGE_FILE="${REPO_DIR}/packages-arch.txt"

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

"${REPO_DIR}/install.sh"
