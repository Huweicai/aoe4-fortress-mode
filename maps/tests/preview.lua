-- Prints a map layout as ASCII. Run: lua maps/tests/preview.lua <layout.lua> <library dir> <map size m> <teams, e.g. 1,1,2,2,2,2> [seed]
-- The library dir is scar/terrainlayout/library extracted from Data.sga (tools/sga.py).
local layout, library, size, team_list, seed = arg[1], arg[2], tonumber(arg[3]), arg[4], tonumber(arg[5] or 1)
setmetatable(_G, { __index = function(_, name) if name:match("^tt_") then return name end end })
math.randomseed(seed)
worldTerrainWidth, worldTerrainHeight = size, size
playerTeams = { }
for team in team_list:gmatch("%d+") do table.insert(playerTeams, tonumber(team)) end
worldPlayerCount = #playerTeams
function worldGetRandom() return math.random() end
function Round(x, digits) local m = 10 ^ (digits or 0); return math.floor(x * m + 0.5) / m end
local real_print = print
print = function() end
for _, file in ipairs({ "map_setup.lua", "player_starts.lua", "template_functions.lua" }) do dofile(library .. "/" .. file) end
if SetUpGrid == nil then
	function SetUpGrid(n, terrain, grid)
		for r = 1, n do grid[r] = { } for c = 1, n do grid[r][c] = { terrainType = terrain } end end
		return grid
	end
end
dofile(layout)
print = real_print
local glyph = { tt_plains = ".", tt_impasse_mountains = "#", tt_impasse_trees_plains = "T", tt_hills_low_rolling = "h", tt_gold_large = "G", tt_stone_large = "S", tt_lake_deep = "~", tt_ocean = "~", tt_ocean_shore = "s", tt_lake_medium_fish_single_precise = "f", tt_plateau_low = ",", tt_hills_low_rolling = "h" }
print(string.format("grid %dx%d, %d m per square", gridSize, gridSize, math.floor(size / gridSize)))
for r = 1, gridSize do
	local line = { }
	for c = 1, gridSize do
		local cell = terrainLayoutResult[r][c]
		line[c] = cell.playerIndex and tostring(cell.playerIndex + 1) or glyph[cell.terrainType] or "?"
	end
	print(table.concat(line))
end
