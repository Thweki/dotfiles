# dotfiles

这是我的个人桌面与开发环境配置仓库，主要用于在新机器上快速恢复一致的使用体验。

## 包含内容

- `i3`、`kitty`、`rofi`、`dunst`
- `fcitx5` 以及本地 Everforest 主题
- `gtk-3.0`、`gtk-4.0`、`qt5ct`、`qt6ct`、`Kvantum`
- Firefox 样式模板
- AstroNvim 配置
- `.xprofile`、`.gtkrc-2.0`

## 使用方式

```bash
git clone <你的仓库地址> ~/dotfiles
cd ~/dotfiles
./install.sh
```

演练模式：

```bash
./install.sh --dry-run
```

如果是 Arch Linux 新机器，建议直接执行：

```bash
git clone <你的仓库地址> ~/dotfiles
cd ~/dotfiles
./bootstrap-arch.sh
```

如果你想先演练部署动作：

```bash
./bootstrap-arch.sh --dry-run
```

## `install.sh` 会做什么

- 创建缺失目录
- 将已有配置备份到 `~/.dotfiles-backup/<时间戳>/`
- 将仓库中的配置复制到 `$HOME`
- 自动检测 Firefox 默认 profile，并安装 `user.js`、`userChrome.css`、`userContent.css`

支持参数：

- `--dry-run`：只打印将要执行的动作
- `--no-backup`：覆盖已有文件时不创建备份

## `bootstrap-arch.sh` 会做什么

- 检查当前系统是否为 Arch Linux
- 使用 `pacman` 安装 [packages-arch.txt](/home/thweki/dotfiles/packages-arch.txt) 中列出的依赖
- 安装完成后自动执行 `install.sh`

支持将 `--dry-run` 和 `--no-backup` 透传给 `install.sh`。

## Arch Linux 依赖

依赖列表见：

- [packages-arch.txt](/home/thweki/dotfiles/packages-arch.txt)：必须包
- [packages-arch-aur.txt](/home/thweki/dotfiles/packages-arch-aur.txt)：可选包与 AUR 包
- [post-install.md](/home/thweki/dotfiles/post-install.md)：安装后手工步骤

## 安装完成后

安装后的详细检查项见 [post-install.md](/home/thweki/dotfiles/post-install.md)。

## CI

仓库内置了 GitHub Actions 检查：

- `bash -n` 校验脚本语法
- 检查关键文件和目录是否存在
