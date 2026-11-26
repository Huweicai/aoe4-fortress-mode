-- Fortress H: the smaller team holds the crossbar of an H, back to back; the other team starts on the two uprights
-- and attacks from both sides. Deep water fills the H above and below the crossbar, and each end of the crossbar
-- meets its upright through one short, narrow neck.
--
--   +------+~~~~~~~~~~~~~~~~+------+
--   |      |~~~~ water ~~~~~|      |
--   |  A1  |  shore, fishing |  A2  |
--   |      =  P1        P2  =      |   = : narrow neck, one per side
--   |  A3  |  shore, fishing |  A4  |
--   |      |~~~~ water ~~~~~|      |
--   +------+~~~~~~~~~~~~~~~~+------+

-- Tuning. One coarse square is METERS_PER_SQUARE wide.
local METERS_PER_SQUARE = 16
-- Width of each upright, as a share of the map; the crossbar takes what is left between the necks.
local UPRIGHT_SHARE = 0.22
-- Height of the crossbar, as a share of the map.
local CROSSBAR_SHARE = 0.42
-- Each neck is a land bridge across deep water. Water leaves no strip to sneak along, as forest and cliffs do at
-- the shore, cannot be chopped open and keeps the ground flat for the camera.
local NECK_LENGTH = 3
local NECK_WIDTH = 8
-- One fishing spot every this many squares along each shore of the crossbar.
local FISH_SPACING = 3
local FOREST_CHANCE = 0.03
local HILL_CHANCE = 0.05

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

-- The defenders are the smallest team; on a tie, the team of the first player.
teamsList, playersPerTeam = SetUpTeams()
local teams = { }
local team_order = { }
for index = 1, #playerTeams do
	local team = playerTeams[index]
	if teams[team] == nil then
		teams[team] = { }
		table.insert(team_order, team)
	end
	table.insert(teams[team], index)
end
local defender_team = team_order[1]
for _, team in ipairs(team_order) do
	if #teams[team] < #teams[defender_team] then
		defender_team = team
	end
end
local defenders = teams[defender_team]
local attackers = { }
for index = 1, #playerTeams do
	if playerTeams[index] ~= defender_team then
		table.insert(attackers, index)
	end
end

-- Columns: left upright, left neck, crossbar, right neck, right upright.
local upright = math.max(5, math.floor(gridSize * UPRIGHT_SHARE))
local left_neck_first = upright + 1
local left_neck_last = upright + NECK_LENGTH
local right_neck_last = gridSize - upright
local right_neck_first = right_neck_last - NECK_LENGTH + 1
local crossbar_first = left_neck_last + 1
local crossbar_last = right_neck_first - 1

-- Rows: water, crossbar, water.
local middle = math.ceil(gridSize / 2)
local crossbar_rows = math.max(6, math.floor(gridSize * CROSSBAR_SHARE))
local crossbar_top = middle - math.floor(crossbar_rows / 2)
local crossbar_bottom = crossbar_top + crossbar_rows - 1

-- Water between the uprights, except for the crossbar.
for row = 1, gridSize do
	if row < crossbar_top or row > crossbar_bottom then
		for col = left_neck_first, right_neck_last do
			Set(row, col, water)
		end
	end
end

-- A shore along the crossbar only, so the shallows never link the uprights to the crossbar past the necks.
for col = crossbar_first, crossbar_last do
	Set(crossbar_top - 1, col, shore)
	Set(crossbar_bottom + 1, col, shore)
	if (col - crossbar_first) % FISH_SPACING == 1 then
		Set(crossbar_top - 3, col, fish)
		Set(crossbar_bottom + 3, col, fish)
	end
end

-- Each neck is water across the crossbar but for a land bridge in the middle.
local gap_first = middle - math.floor((NECK_WIDTH - 1) / 2)
local gap_last = gap_first + NECK_WIDTH - 1
for _, neck in ipairs({ { left_neck_first, left_neck_last }, { right_neck_first, right_neck_last } }) do
	for col = neck[1], neck[2] do
		for row = crossbar_top, crossbar_bottom do
			if row < gap_first or row > gap_last then
				Set(row, col, water)
			end
		end
	end
end

-- Cover on the uprights, kept clear of the necks.
for row = 1, gridSize do
	for _, range in ipairs({ { 1, upright }, { right_neck_last + 1, gridSize } }) do
		for col = range[1], range[2] do
			local near_neck = math.abs(row - middle) <= 3 and (col >= upright - 2 and col <= right_neck_last + 3)
			if not near_neck then
				local roll = worldGetRandom()
				if roll < FOREST_CHANCE then
					Set(row, col, tt_impasse_trees_plains)
				elseif roll < FOREST_CHANCE + HILL_CHANCE then
					Set(row, col, tt_hills_low_rolling)
				end
			end
		end
	end
end

-- Starts take a player index from 0, as on the setup screen.
local function PlaceStart(player, row, col)
	Set(row, col, start)
	terrainLayoutResult[row][col].playerIndex = player - 1
end

-- Defenders spread along the crossbar, the first one nearest the left neck.
local crossbar_width = crossbar_last - crossbar_first + 1
for index, player in ipairs(defenders) do
	local col = crossbar_first + math.floor(crossbar_width * (index - 0.5) / #defenders)
	PlaceStart(player, middle, col)
end

-- Attackers alternate between the uprights, spread from top to bottom on each.
local sides = { { col = math.ceil(upright / 2), players = { } }, { col = gridSize - math.floor(upright / 2), players = { } } }
for index, player in ipairs(attackers) do
	table.insert(sides[(index - 1) % 2 + 1].players, player)
end
for _, side in ipairs(sides) do
	for index, player in ipairs(side.players) do
		local row = math.floor(gridSize * (index - 0.5) / #side.players + 0.5)
		PlaceStart(player, math.max(2, math.min(gridSize - 1, row)), side.col)
	end
end

-- Extra gold and stone near both ends of the crossbar, one pair per defender, a square off the shore.
Set(crossbar_top + 2, crossbar_first + 1, tt_gold_large)
Set(crossbar_bottom - 2, crossbar_first + 1, tt_stone_large)
Set(crossbar_top + 2, crossbar_last - 1, tt_gold_large)
Set(crossbar_bottom - 2, crossbar_last - 1, tt_stone_large)
