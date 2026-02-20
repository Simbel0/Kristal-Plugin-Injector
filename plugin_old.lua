MainMenu = Kristal.States["Menu"]

MainMenu.onKeyPressed = Utils.override(MainMenu.onKeyPressed, function(orig, self, key, is_repeat)
	print(self, key, is_repeat)
	if self.state == "MAINMENU" then
		if Input.ctrl() and key == "p" then
			self:setState("plugins")
		end
	end
	orig(self, key, is_repeat)
end)

MainMenu.draw = Utils.override(MainMenu.draw, function(orig, self)
	orig(self)

	love.graphics.setFont(self.small_font)
    love.graphics.setColor(1, 1, 1, 0.5)
	love.graphics.printf("[Ctrl+P]: Plugins", 0, SCREEN_HEIGHT-16, SCREEN_WIDTH, "right")
end)