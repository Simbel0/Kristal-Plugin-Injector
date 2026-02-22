--- Hook for the Plugin Loader for Kristal 0.8.1 and below
---
--- This file hooks into the Main Menu of Kristal prior to version 0.9.0
--- The Loader expects the main menu to have a state machine, which is something older versions don't have
--- That's a problem, as most standalone releases to my knowledge runs on 0.8.1 or older.
--- So this file hooks into them to force them to work with the PluginOptionsHandler object anyway

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