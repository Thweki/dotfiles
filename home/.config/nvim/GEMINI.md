# Project Overview

This directory contains a personalized configuration for AstroNvim, a popular Neovim distribution. The configuration is written in Lua and uses `lazy.nvim` for plugin management. The setup is highly customized with a variety of plugins for UI enhancements, LSP features, and language support.

## Key Technologies

*   **Neovim**: The underlying text editor.
*   **AstroNvim**: The Neovim distribution that provides the framework for this configuration.
*   **Lua**: The language used for configuration.
*   **lazy.nvim**: The plugin manager.

## Building and Running

To use this configuration, you need to have Neovim installed. Then, you can clone this repository to your Neovim configuration directory (`~/.config/nvim` on Linux and macOS, `~/AppData/Local/nvim` on Windows).

```bash
git clone <repository_url> ~/.config/nvim
```

After cloning, open Neovim, and `lazy.nvim` will automatically install the configured plugins.

## Development Conventions

The configuration is structured to separate concerns:

*   `init.lua`: The entry point that bootstraps `lazy.nvim`.
*   `lua/lazy_setup.lua`: Configures `lazy.nvim` and loads the plugins.
*   `lua/community.lua`: Imports plugins from the AstroNvim community repository.
*   `lua/plugins/`: Contains individual plugin configurations.
*   `lua/polish.lua`: For user-specific customizations.

The user has configured a variety of plugins, including:

*   **UI**: `astroui` with the `rose-pine` colorscheme, `nvim-colorizer.lua`, and a custom dashboard.
*   **LSP**: `astrolsp` with auto-formatting on save, and `mason.nvim` to manage LSP servers.
*   **Treesitter**: For advanced syntax highlighting.
*   **Neovide**: Specific settings for the Neovide GUI.
*   **Custom Plugins**: `presence.nvim` and `lsp_signature.nvim`.
