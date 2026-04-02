# 安装后检查

以下步骤适用于新机器首次部署完成后。

## 1. 重新登录图形会话

- 退出当前 `i3` 会话并重新登录
- 或者直接重启机器

这样可以确保：

- `.xprofile` 生效
- GTK / Qt 主题环境变量生效
- `xss-lock`、`dunst`、`fcitx5` 等自启动完整拉起

## 2. 检查输入法

- 确认 `fcitx5` 已启动
- 确认候选框主题是 Everforest
- 确认字号正常
- 确认 `Ctrl+Space` 能切换输入法

如果没有生效，可以执行：

```bash
pkill fcitx5
fcitx5 -d
```

## 3. 检查 i3 桌面

- 检查 `i3bar` 配色是否正确
- 检查 `rofi` 是否能通过 `Super+d` 打开
- 检查 `dunst` 通知样式
- 检查 `Super+Shift+x` 是否能触发锁屏

## 4. 检查终端与主题

- 打开 `kitty`
- 确认 Everforest 配色生效
- 确认光标拖尾动画正常

## 5. 检查 Firefox

- 完全退出并重新打开 Firefox
- 确认工具栏、标签栏、地址栏样式已生效

## 6. 检查 Neovim

首次打开 `nvim` 后执行：

```vim
:Lazy sync
```

如果主题插件或其他插件未安装完成，重开一次 `nvim`。

## 7. 检查字体

至少确认这些字体已经可用：

- `CaskaydiaCove Nerd Font`
- `FiraCode Nerd Font`

检查命令：

```bash
fc-list | rg 'Caskaydia|FiraCode'
```

