if not vim.g.neovide then return {} end

-- vim.o.guifont = "JetBrainsMono Nerd Font Mono:h12"
vim.o.guifont = "JetBrainsMono Nerd Font Mono:h11.5"
vim.g.neovide_transparency = 1.0
vim.g.transparency = 1.0
vim.g.neovide_refresh_rate = 60
vim.g.neovide_refresh_rate_idle = 5
vim.g.neovide_hide_mouse_when_typing = true
vim.g.neovide_cursor_antialiasing = true
vim.g.neovide_cursor_vfx_mode = "pixiedust"
vim.g.neovide_cursor_vfx_particle_density = 70.0

local function set_ime(args)
  if args.event:match "Enter$" then
    vim.g.neovide_input_ime = true
  else
    vim.g.neovide_input_ime = false
  end
end

local ime_input = vim.api.nvim_create_augroup("ime_input", { clear = true })

vim.api.nvim_create_autocmd({ "InsertEnter", "InsertLeave" }, {
  group = ime_input,
  pattern = "*",
  callback = set_ime,
})

vim.api.nvim_create_autocmd({ "CmdlineEnter", "CmdlineLeave" }, {
  group = ime_input,
  pattern = "[/\\?]",
  callback = set_ime,
})

---@param scale_factor number
---@return number
local function clamp_scale_factor(scale_factor)
  return math.max(math.min(scale_factor, vim.g.neovide_max_scale_factor), vim.g.neovide_min_scale_factor)
end

---@param scale_factor number
---@param clamp? boolean
local function set_scale_factor(scale_factor, clamp)
  vim.g.neovide_scale_factor = clamp and clamp_scale_factor(scale_factor) or scale_factor
end

local function reset_scale_factor() vim.g.neovide_scale_factor = vim.g.neovide_initial_scale_factor end

---@param increment number
---@param clamp? boolean
local function change_scale_factor(increment, clamp) set_scale_factor(vim.g.neovide_scale_factor + increment, clamp) end

---@type LazySpec
return {
  "AstroNvim/astrocore",
  ---@type AstroCoreOpts
  opts = {
    options = {
      g = {
        neovide_increment_scale_factor = vim.g.neovide_increment_scale_factor or 0.1,
        neovide_min_scale_factor = vim.g.neovide_min_scale_factor or 0.7,
        neovide_max_scale_factor = vim.g.neovide_max_scale_factor or 2.0,
        neovide_initial_scale_factor = vim.g.neovide_scale_factor or 1,
        neovide_scale_factor = vim.g.neovide_scale_factor or 1,
      },
    },
    commands = {
      NeovideSetScaleFactor = {
        function(event)
          local scale_factor, option = tonumber(event.fargs[1]), event.fargs[2]

          if not scale_factor then
            vim.notify(
              "Error: scale factor argument is nil or not a valid number.",
              vim.log.levels.ERROR,
              { title = "Recipe: neovide" }
            )
            return
          end

          set_scale_factor(scale_factor, option ~= "force")
        end,
        nargs = "+",
        desc = "Set Neovide scale factor",
      },
      NeovideResetScaleFactor = {
        reset_scale_factor,
        desc = "Reset Neovide scale factor",
      },
    },
    mappings = {
      n = {
        ["<C-=>"] = {
          function() change_scale_factor(vim.g.neovide_increment_scale_factor * vim.v.count1, true) end,
          desc = "Increase Neovide scale factor",
        },
        ["<C-->"] = {
          function() change_scale_factor(-vim.g.neovide_increment_scale_factor * vim.v.count1, true) end,
          desc = "Decrease Neovide scale factor",
        },
        ["<C-0>"] = { reset_scale_factor, desc = "Reset Neovide scale factor" },
      },
    },
  },
}
