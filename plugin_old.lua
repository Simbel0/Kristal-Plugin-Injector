--- Hook for the Plugin Loader for Kristal 0.8.1 and below
---
--- This file hooks into the Main Menu of Kristal prior to version 0.9.0
--- The Loader expects the main menu to have a state machine, which is something older versions don't have
--- That's a problem, as most standalone releases to my knowledge runs on 0.8.1 or older.
--- So this file hooks into them to force them to work with the PluginOptionsHandler object anyway
INJECTED_PLUGINLOADER = true

local MainMenu = Kristal.States["Menu"]

MainMenu.onKeyPressed = Utils.override(MainMenu.onKeyPressed, function(orig, self, key, is_repeat)
	if self.state == "OPTIONS" then
		if Input.ctrl() and key == "p" then
			self:setState("plugins")
		end
	elseif self.state == "plugins" then
		self.PluginOptions:onKeyPressed(key, is_repeat)
		if key == "f2" then
			love.system.openURL("file://"..love.filesystem.getSaveDirectory().."/mods")
		end
		return
	end
	orig(self, key, is_repeat)
end)

MainMenu.onStateChange = Utils.override(MainMenu.onStateChange, function(orig, self, old_state, new_state)
	if new_state == "plugins" then
		self.PluginOptions:onEnter(old_state)
	elseif old_state == "plugins" then
		self.PluginOptions:onLeave()
		self.selected_option = 1
		self.heart_target_x = 152
        self.heart_target_y = 129 + self.options_target_y
	end
	orig(self, old_state, new_state)
end)

MainMenu.update = Utils.override(MainMenu.update, function(orig, self)
	if self.state == "plugins" then
		self.PluginOptions:update()
	end
	orig(self)
end)

MainMenu.draw = Utils.override(MainMenu.draw, function(orig, self)
	orig(self)
	if self.state == "plugins" then
		self.PluginOptions:draw()
	end

	if self.state == "OPTIONS" then
		love.graphics.setFont(self.small_font)
    	love.graphics.setColor(1, 1, 1, 0.5)
		love.graphics.printf("[Ctrl+P]: Plugins", 0, SCREEN_HEIGHT-16, SCREEN_WIDTH, "right")
	elseif self.state == "plugins" then
		love.graphics.setFont(self.small_font)
    	love.graphics.setColor(1, 1, 1, 0.5)
		love.graphics.printf("[F2]: Open Plugins Folder", 0, SCREEN_HEIGHT-16, SCREEN_WIDTH, "right")
	end
end)

--- We also need to add those three functions as the plugin loader uses them.

---@see http://lua-users.org/wiki/SortedIteration
---@private
local function __genOrderedIndex(t)
    local ordered_index = {}
    for key in pairs(t) do
        table.insert(ordered_index, key)
    end
    table.sort(ordered_index)
    return ordered_index
end

-- Equivalent of the next function, but returns the keys in the alphabetic
-- order. We use a temporary ordered key table that is stored in the
-- table being iterated.
---@generic K
---@generic V
---@param table table<K,V>
---@param index? K
---@return K|nil
---@return V|nil
---@see http://lua-users.org/wiki/SortedIteration
Utils.hook(Utils, "orderedNext", function(_, table, index)
    local key = nil
    if index == nil then
        -- the first time, generate the index
        table.__ordidx = __genOrderedIndex(table)
        key = table.__ordidx[1]
    else
        -- fetch the next value
        for i = 1, #table.__ordidx do
            if table.__ordidx[i] == index then
                key = table.__ordidx[i+1]
            end
        end
    end

    if key then
        return key, table[key]
    end

    -- no more value to return, cleanup
    table.__ordidx = nil
end)

-- Equivalent of the pairs() function on tables. Allows to iterate
-- in order
---@generic K
---@generic V
---@param t table<K, V> The table to iterate
---@return fun(table: table<K,V>, index?: K):K,V next
---@return table<K, V> t
---@return nil
---@see http://lua-users.org/wiki/SortedIteration
Utils.hook(Utils, "orderedPairs", function(_, t)
    return Utils.orderedNext, t, nil
end)

-- Have a non-zero chance of blowing up as Mod.info.lib_order probably started to exist for a good reason
Utils.hook(Kristal, "iterLibraries", function()
    local index = 0

    local keys = {}
    for k,v in pairs(Mod.libs) do
    	table.insert(keys, k)
    end

    return function()
        index = index + 1

        if index <= #keys then
            local lib_id = keys[index]

            return lib_id, Mod.libs[lib_id]
        end
    end
end)

--- From here, it's just me trying to make the Chaos Plugin work on Frozen Heart

--- Creates an alert bubble (tiny !) above this character.
---@param duration?     number  The number of frames to show the bubble for. (Defaults to `20`)
---@param options?      table   A table defining additional properties to control the bubble.
---|"play_sound"    # Whether the alert sound will be played. (Defaults to `true`)
---|"sprite"        # The sprite to use for the alert bubble. (Defaults to `"effects/alert"`)
---|"offset_x"      # The x-offset of the icon.
---|"offset_y"      # The y-offset of the icon.
---|"layer"         # The layer to put the icon on. (Defaults to `100`)
---|"callback"      # A callback that is run when the alert finishes.
---@return Sprite
Utils.hook(Character, "alert", function(_, self, duration, options)
    options = options or {}
    if options["play_sound"] == nil or options["play_sound"] then
        Assets.stopAndPlaySound("alert")
    end
    local sprite_to_use = options["sprite"] or "effects/alert"
    self.alert_timer = duration and duration * 30 or 20
    if self.alert_icon then self.alert_icon:remove() end
    self.alert_icon = Sprite(sprite_to_use, (self.width / 2) + (options["offset_x"] or 0), options["offset_y"] or 0)
    self.alert_icon:setOrigin(0.5, 1)
    self.alert_icon.layer = options["layer"] or 100
    self:addChild(self.alert_icon)
    self.alert_callback = options["callback"]
    return self.alert_icon
end)

Utils.hook(ChaserEnemy, "onAlerted", function(_, self)
    if self.physics.move_target and self.physics.move_target.after then
        self.physics.move_target:after()
    end
    self.physics.move_target = nil

    if self.physics.move_path and self.physics.move_path.after then
        self.physics.move_path:after()
    end
    self.physics.move_path = nil
end)

-- Same as love.graphics.print(), but has the align parameter after the y param
-- Available align options: "left", "center" and "right"
-- If using align as a table, you can spcify the key "align" for the alignment and "line_offset" for the new line spacing.
Utils.hook(Draw, "printAlign", function(_, text, x, y, align, r, sx, sy, ox, oy, kx, ky)
    local new_line_space = 0
    local new_line_space_height = love.graphics.getFont():getHeight()
    if type(align) == "table" then
        if align["line_offset"] then
            new_line_space_height = new_line_space_height + align["line_offset"]
        end
        if align["align"] then
            align = align["align"]
        end
    end

    for line in string.gmatch(text, "([^\n]+)") do
        local font = love.graphics.getFont()
        local line_width = font:getWidth(line)

        local offset_x = 0
        if align == "center" then
            offset_x = (line_width / 2) * (sx or 1)
        elseif align == "right" then
            offset_x = line_width * (sx or 1)
        end

        love.graphics.print(
            line,
            x - offset_x,
            y + new_line_space,
            r,
            sx, sy, ox, oy, kx, ky
        )

        new_line_space = new_line_space + new_line_space_height * (sy or 1)
    end
end)

---@param loop boolean
Utils.hook(Music, "setLooping", function(_, self, loop)
    self.looping = loop
    if self.source then
        self.source:setLooping(loop)
    end
end)

-- lol, lmao even
-- Does NOT handle every possible case
ClassUtils = Utils
FileSystemUtils = Utils
HookSystem = Utils
StringUtils = Utils
TiledUtils = Utils

MathUtils = Utils.copy(Utils, true)
MathUtils.randomInt = love.math.random

TableUtils = Utils.copy(Utils, true)
TableUtils.removeValue = Utils.removeFromTable
TableUtils.contains = Utils.containsValue
TableUtils.mergeMany = Utils.mergeMultiple
TableUtils.flip = Utils.flipTable
TableUtils.rotate = Utils.rotateTable
TableUtils.some = function(tbl, func)
    for i = 1, #tbl do
        if func(tbl[i]) then
            return true
        end
    end
    return false
end

ColorUtils = Utils.copy(Utils, true)
ColorUtils.HSLToRGB = Utils.hslToRgb
ColorUtils.RGBToHSL = Utils.rgbToHsl
ColorUtils.HSVToRGB = Utils.hsvToRgb
ColorUtils.hexToRGB = Utils.hexToRgb
ColorUtils.RGBToHex = Utils.rgbToHex