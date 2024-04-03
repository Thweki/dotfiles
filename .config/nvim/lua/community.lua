-- AstroCommunity: import any community modules here
-- We import this file in `lazy_setup.lua` before the `plugins/` folder.
-- This guarantees that the specs are processed before any user plugins.

---@type LazySpec
return {
  "AstroNvim/astrocommunity",
  { import = "astrocommunity.pack.lua" },
  { import = "astrocommunity.pack.bash" },
  { import = "astrocommunity.pack.go" },
  { import = "astrocommunity.pack.json" },
  { import = "astrocommunity.pack.html-css" },
  { import = "astrocommunity.pack.markdown" },
  { import = "astrocommunity.pack.php" },
  { import = "astrocommunity.pack.python-ruff" },
  { import = "astrocommunity.pack.toml" },
  { import = "astrocommunity.pack.rust" },
  { import = "astrocommunity.pack.typescript-all-in-one" },
  { import = "astrocommunity.pack.vue" },
  { import = "astrocommunity.pack.sql" },
  { import = "astrocommunity.pack.yaml" },
  ---------------------------------------
  { import = "astrocommunity.colorscheme.rose-pine" },
  ---------------------------------------
  { import = "astrocommunity.color.headlines-nvim" },
  ---------------------------------------
  { import = "astrocommunity.code-runner.sniprun" },
  { import = "astrocommunity.code-runner.compiler-nvim" },
  ---------------------------------------
  { import = "astrocommunity.diagnostics.trouble-nvim" },
  ---------------------------------------
  { import = "astrocommunity.editing-support.conform-nvim" },
  { import = "astrocommunity.editing-support.refactoring-nvim" },
  { import = "astrocommunity.editing-support.nvim-regexplainer" },
  -- { import = "astrocommunity.editing-support.rainbow-delimiters-nvim" },
  ---------------------------------------
  { import = "astrocommunity.lsp.lsp-signature-nvim" },
  { import = "astrocommunity.lsp.ts-error-translator-nvim" },
  ---------------------------------------
  { import = "astrocommunity.markdown-and-latex.glow-nvim" },
  ---------------------------------------
  { import = "astrocommunity.motion.flash-nvim" },
  ---------------------------------------
  { import = "astrocommunity.scrolling.neoscroll-nvim" },
}
