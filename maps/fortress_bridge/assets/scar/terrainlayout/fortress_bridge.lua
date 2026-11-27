-- Fortress Bridge: two teams on the uprights of an H, joined only by its crossbar, a long and narrow land bridge
-- with deep water on both sides. The first team starts on the left upright, everyone else on the right one.
--
--   +------+~~~~~~~~~~~~~~~~+------+
--   |  A1  |~~~~ water ~~~~~|  B1  |
--   |      |                |      |
--   |  A2  ==================  B2  |   = : the bridge, the only way across
--   |      |                |      |
--   |  A3  |~~~~ water ~~~~~|  B3  |
--   +------+~~~~~~~~~~~~~~~~+------+

-- Tuning. One coarse square is METERS_PER_SQUARE wide, so the bridge is about 3 * 16 = 48 m wide: a warship on one
-- side, the baochuan's cannons reaching 36 m, covers most of it. Two squares came out flooded once the engine
-- smoothed the shores.
local METERS_PER_SQUARE = 16
-- Width of each upright, as a share of the map; the bridge spans what is left.
local UPRIGHT_SHARE = 0.24
local BRIDGE_WIDTH = 3
-- One fishing spot every this many squares down each shore.
local FISH_SPACING = 3

terrainLayoutResult = {}
gridHeight, gridWidth, gridSize = SetCustomCoarseGrid(METERS_PER_SQUARE)
playerStarts = worldPlayerCount

local plains = tt_plains
-- Deep water and its shore as the official lake maps lay them out; fish sit a little way off the shore.
local water = tt_ocean
local shore = tt_ocean_shore
local fish = tt_lake_medium_fish_single_precise
local start = tt_player_start_classic_plains

terrainLayoutResult = SetUpGrid(gridSize, plains, terrainLayoutResult)

local function Set(row, col, terrain)
	if row >= 1 and row <= gridSize and col >= 1 and col <= gridSize then
		terrainLayoutResult[row][col].terrainType = terrain
	end
end

-- The team of the first player takes the left upright; every other team the right one.
teamsList, playersPerTeam = SetUpTeams()
local left_team = playerTeams[1]
local sides = { { players = { } }, { players = { } } }
for index = 1, #playerTeams do
	table.insert(sides[playerTeams[index] == left_team and 1 or 2].players, index)
end

-- Columns: left upright, water and bridge, right upright.
local upright = math.max(5, math.floor(gridSize * UPRIGHT_SHARE))
local water_first = upright + 1
local water_last = gridSize - upright
local middle = math.ceil(gridSize / 2)
local bridge_first = middle - math.floor((BRIDGE_WIDTH - 1) / 2)
local bridge_last = bridge_first + BRIDGE_WIDTH - 1

for row = 1, gridSize do
	if row < bridge_first or row > bridge_last then
		for col = water_first, water_last do
			Set(row, col, water)
		end
	end
end

-- A shore down the inner edge of each upright and fish further out, both kept off the bridge.
for row = 1, gridSize do
	if row < bridge_first - 1 or row > bridge_last + 1 then
		Set(row, water_first, shore)
		Set(row, water_last, shore)
		if row % FISH_SPACING == 1 then
			Set(row, water_first + 2, fish)
			Set(row, water_last - 2, fish)
		end
	end
end

-- Starts take a player index from 0, as on the setup screen.
local function PlaceStart(player, row, col)
	Set(row, col, start)
	terrainLayoutResult[row][col].playerIndex = player - 1
end

sides[1].col = math.ceil(upright / 2)
sides[2].col = gridSize - math.floor(upright / 2)
for _, side in ipairs(sides) do
	for index, player in ipairs(side.players) do
		local row = math.floor(gridSize * (index - 0.5) / #side.players + 0.5)
		PlaceStart(player, math.max(2, math.min(gridSize - 1, row)), side.col)
	end
end

-- Extra gold and stone at the back of each upright, against the map edge.
Set(2, 2, tt_gold_large)
Set(gridSize - 1, 2, tt_stone_large)
Set(2, gridSize - 1, tt_gold_large)
Set(gridSize - 1, gridSize - 1, tt_stone_large)

-- A sacred site in the middle of the bridge, for both sides to fight over.
Set(middle, middle, tt_holy_site)
