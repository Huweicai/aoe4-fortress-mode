-- Fortress Pass: the smaller team holds walled basins in the north, each with one narrow gap; the other team starts on
-- the open plain to the south. Made for Fortress Mode (two humans against AIs), but plays as any team game.
--
--   north edge
--   +----------+---+----------+
--   |  basin 1 | r |  basin 2 |   r: ridge between basins, with a narrow path so neighbours can help each other
--   |   (P1)   | = |   (P2)   |
--   +====  ====+===+====  ====+   mountain wall; each basin has one narrow gap
--   |      open plain         |
--   |   A1    A2    A3   A4   |   attackers spread along the south
--   +-------------------------+

-- Tuning. One coarse square is METERS_PER_SQUARE wide, so a gap of GAP_SQUARES is about 2 * 16 = 32 m.
local METERS_PER_SQUARE = 16
local GAP_SQUARES = 2
local RIDGE_PATH_SQUARES = 1
local WALL_THICKNESS = 3
local RIDGE_THICKNESS = 3
-- Share of the map height taken by the basins.
local BASIN_DEPTH = 0.42
-- Attackers start this far up from the south edge, as a share of the map height.
local ATTACKER_ROW_FROM_SOUTH = 0.14
local FOREST_CHANCE = 0.03
local HILL_CHANCE = 0.06

terrainLayoutResult = {}
gridHeight, gridWidth, gridSize = SetCustomCoarseGrid(METERS_PER_SQUARE)
playerStarts = worldPlayerCount

local plains = tt_plains
local wall = tt_impasse_mountains
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

-- Basins side by side across the north, separated by ridges.
local basin_count = math.max(1, #defenders)
local basin_rows = math.max(8, math.floor(gridSize * BASIN_DEPTH))
local wall_first = basin_rows + 1
local wall_last = basin_rows + WALL_THICKNESS
local basin_width = (gridSize - (basin_count - 1) * RIDGE_THICKNESS) / basin_count

local basins = { }
for index = 1, basin_count do
	local first = math.floor((index - 1) * (basin_width + RIDGE_THICKNESS)) + 1
	local last = math.floor(first + basin_width - 1)
	basins[index] = { first = first, last = last, centre = math.floor((first + last) / 2) }
end

-- The wall across the map, with one gap below the middle of each basin.
for row = wall_first, wall_last do
	for col = 1, gridSize do
		Set(row, col, wall)
	end
end
for _, basin in ipairs(basins) do
	local gap_first = basin.centre - math.floor((GAP_SQUARES - 1) / 2)
	for row = wall_first, wall_last do
		for col = gap_first, gap_first + GAP_SQUARES - 1 do
			Set(row, col, plains)
		end
	end
end

-- Ridges between basins, each with a narrow path halfway down.
local path_row = math.floor(basin_rows / 2)
for index = 1, basin_count - 1 do
	local first = basins[index].last + 1
	for col = first, first + RIDGE_THICKNESS - 1 do
		for row = 1, basin_rows do
			if row < path_row or row >= path_row + RIDGE_PATH_SQUARES then
				Set(row, col, wall)
			end
		end
	end
end

-- Some cover on the plain, kept clear of the gaps and the attacker starts.
local attacker_row = gridSize - math.max(2, math.floor(gridSize * ATTACKER_ROW_FROM_SOUTH))
for row = wall_last + 3, gridSize do
	for col = 1, gridSize do
		if math.abs(row - attacker_row) > 3 then
			local roll = worldGetRandom()
			if roll < FOREST_CHANCE then
				Set(row, col, tt_impasse_trees_plains)
			elseif roll < FOREST_CHANCE + HILL_CHANCE then
				Set(row, col, tt_hills_low_rolling)
			end
		end
	end
end

-- Starts take a player index from 0, as on the setup screen.
local function PlaceStart(player, row, col)
	Set(row, col, start)
	terrainLayoutResult[row][col].playerIndex = player - 1
end

local defender_row = math.floor(basin_rows * 0.55)
for index, player in ipairs(defenders) do
	PlaceStart(player, defender_row, basins[index].centre)
end

for index, player in ipairs(attackers) do
	local col = math.floor(gridSize * (index - 0.5) / #attackers + 0.5)
	PlaceStart(player, attacker_row, math.max(2, math.min(gridSize - 1, col)))
end

-- Extra gold and stone at the back of each basin, so defenders need not leave early.
for _, basin in ipairs(basins) do
	Set(2, basin.first + 1, tt_gold_large)
	Set(2, basin.last - 1, tt_stone_large)
end
