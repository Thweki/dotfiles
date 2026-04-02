---@type LazySpec
return {

  -- == 添加插件示例 ==

  "andweeb/presence.nvim",
  {
    "ray-x/lsp_signature.nvim",
    event = "BufRead",
    config = function() require("lsp_signature").setup() end,
  },

  -- == 覆盖插件示例 ==

  -- 自定义 alpha 选项
  {
    "goolord/alpha-nvim",
    opts = function(_, opts)
      -- 自定义仪表盘头部
      opts.section.header.val = {
        " █████  ███████ ████████ ██████   ██████",
        "██   ██ ██         ██    ██   ██ ██    ██",
        "███████ ███████    ██    ██████  ██    ██",
        "██   ██      ██    ██    ██   ██ ██    ██",
        "██   ██ ███████    ██    ██   ██  ██████",
        " ",
        "    ███    ██ ██    ██ ██ ███    ███",
        "    ████   ██ ██    ██ ██ ████  ████",
        "    ██ ██  ██ ██    ██ ██ ██ ████ ██",
        "    ██  ██ ██  ██  ██  ██ ██  ██  ██",
        "    ██   ████   ████   ██ ██      ██",
      }
      return opts
    end,
  },

  -- 您可以按如下方式禁用默认插件：
  { "max397574/better-escape.nvim", enabled = false },

  -- 您还可以轻松自定义插件的额外设置，这些设置在插件的 setup 调用之外
  {
    "L3MON4D3/LuaSnip",
    config = function(plugin, opts)
      require "astronvim.plugins.configs.luasnip"(plugin, opts) -- 包含调用 setup 的默认 astronvim 配置
      -- 添加更多自定义 luasnip 配置，例如文件类型扩展或自定义片段
      local luasnip = require "luasnip"
      luasnip.filetype_extend("javascript", { "javascriptreact" })
    end,
  },

  {
    "windwp/nvim-autopairs",
    config = function(plugin, opts)
      require "astronvim.plugins.configs.nvim-autopairs"(plugin, opts) -- 包含调用 setup 的默认 astronvim 配置
      -- 添加更多自定义 autopairs 配置，例如自定义规则
      local npairs = require "nvim-autopairs"
      local Rule = require "nvim-autopairs.rule"
      local cond = require "nvim-autopairs.conds"
      npairs.add_rules(
        {
          Rule("$", "$", { "tex", "latex" })
            -- 如果下一个字符是 % 则不添加配对
            :with_pair(cond.not_after_regex "%%")
            -- 如果前一个字符是 xxx 则不添加配对
            :with_pair(cond.not_before_regex("xxx", 3))
            -- 重复字符时不要右移
            :with_move(cond.none())
            -- 如果下一个字符是 xx 则不删除
            :with_del(cond.not_after_regex "xx")
            -- 当按 <cr> 时禁用添加新行
            :with_cr(cond.none()),
        },
        -- 禁用 .vim 文件，但对其他文件类型有效
        Rule("a", "a", "-vim")
      )
    end,
  },
  {
    "j-hui/fidget.nvim",
    opts = {},
  },

  {
    "keaising/im-select.nvim",
    config = function() require("im_select").setup {} end,
  },
  {
    "anurag3301/nvim-platformio.lua",
    -- cmd = { 'Pioinit', 'Piorun', 'Piocmdh', 'Piocmdf', 'Piolib', 'Piomon', 'Piodebug', 'Piodb' },

    -- optional: cond used to enable/disable platformio
    -- based on existance of platformio.ini file and .pio folder in cwd.
    -- You can enable platformio plugin, using :Pioinit command
    cond = function()
      -- local platformioRootDir = vim.fs.root(vim.fn.getcwd(), { 'platformio.ini' }) -- cwd and parents
      local platformioRootDir = (vim.fn.filereadable "platformio.ini" == 1) and vim.fn.getcwd() or nil
      if platformioRootDir and vim.fs.find(".pio", { path = platformioRootDir, type = "directory" })[1] then
        -- if platformio.ini file and .pio folder exist in cwd, enable plugin to install plugin (if not istalled) and load it.
        vim.g.platformioRootDir = platformioRootDir
      elseif (vim.uv or vim.loop).fs_stat(vim.fn.stdpath "data" .. "/lazy/nvim-platformio.lua") == nil then
        -- if nvim-platformio not installed, enable plugin to install it first time
        vim.g.platformioRootDir = vim.fn.getcwd()
      else -- if nvim-platformio.lua installed but disabled, create Pioinit command
        vim.api.nvim_create_user_command("Pioinit", function() --available only if no platformio.ini and .pio in cwd
          vim.api.nvim_create_autocmd("User", {
            pattern = { "LazyRestore", "LazyLoad" },
            once = true,
            callback = function(args)
              if args.match == "LazyRestore" then
                require("lazy").load { plugins = { "nvim-platformio.lua" } }
              elseif args.match == "LazyLoad" then
                vim.notify("PlatformIO loaded", vim.log.levels.INFO, { title = "PlatformIO" })
                vim.cmd "Pioinit"
              end
            end,
          })
          vim.g.platformioRootDir = vim.fn.getcwd()
          require("lazy").restore { plguins = { "nvim-platformio.lua" }, show = false }
        end, {})
      end
      return vim.g.platformioRootDir ~= nil
    end,

    -- Dependencies are lazy-loaded by default unless specified otherwise.
    dependencies = {
      { "akinsho/toggleterm.nvim" },
      { "nvim-telescope/telescope.nvim" },
      { "nvim-telescope/telescope-ui-select.nvim" },
      { "nvim-lua/plenary.nvim" },
      { "folke/which-key.nvim" },
    },
  },
}
