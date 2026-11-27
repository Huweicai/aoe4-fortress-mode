-- Fortress Hill: the smaller team starts together on a gentle hill in the middle of the map, ringed by a moat.
-- Each defender brings one pair of close land bridges over the moat, so every player has two nearby gaps to hold;
-- the pairs go left, right, top and bottom in turn. The other team starts around the edge of the map.
--
--        A        A        A
--      ~~~~~~~~~~~~~~~~~~~~~~~~~~~~
--      ~                          ~
--      =   bridges  P1  P2 bridges=      = : land bridge, two close together per defender
--      =                          =
--      ~                          ~
--      ~~~~~~~~~~~~~~~~~~~~~~~~~~~~
--        A        A        A

-- Tuning. One coarse square is METERS_PER_SQUARE wide.
local METERS_PER_SQUARE = 16
-- The plateau is a square this share of the map wide.
local PLATEAU_SHARE = 0.6
-- The moat is deep water: mountains made the camera jump, and forest or cliffs leave a walkable strip where they
-- meet water. A gentle hill rather than a plateau, since a plateau's cliffs would leave no shore for docks.
local RIM_THICKNESS = 3
local RAMP_WIDTH = 4
-- Squares between the two bridges of a pair, centre to centre.
local RAMP_SPACING = 7
local PLATEAU = tt_hills_gentle_rolling
local RAMP = tt_plains
-- One fishing spot every this many squares around the moat.
local FISH_SPACING = 3
local FOREST_CHANCE = 0.03
local HILL_CHANCE = 0.05

terrainLayoutResult = {}
gridHeight, gridWidth, gridSize = SetCustomCoarseGrid(METERS_PER_SQUARE)
playerStarts = worldPlayerCount

local plains = tt_plains
local rock = tt_ocean
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

-- The plateau, rim included.
local middle = math.ceil(gridSize / 2)
local half = math.floor(gridSize * PLATEAU_SHARE / 2)
local top, bottom, left, right = middle - half, middle + half, middle - half, middle + half
for row = top, bottom do
	for col = left, right do
		local on_rim = row < top + RIM_THICKNESS or row > bottom - RIM_THICKNESS or col < left + RIM_THICKNESS or col > right - RIM_THICKNESS
		Set(row, col, on_rim and rock or PLATEAU)
	end
end

-- A shore on the inner edge of the moat and fish around its middle; the bridges are cut through both afterwards.
for row = top, bottom do
	for col = left, right do
		local depth = math.min(row - top, bottom - row, col - left, right - col)
		if depth == RIM_THICKNESS - 1 then
			Set(row, col, shore)
		elseif depth == math.floor(RIM_THICKNESS / 2) and (row + col) % FISH_SPACING == 0 then
			Set(row, col, fish)
		end
	end
end

-- One pair of bridges per defender, on the sides in turn. A side that gets a second pair shifts both apart.
local sides = { "left", "right", "top", "bottom" }
-- Rows grow downwards, so top is a negative sine.
local SIDE_ANGLES = { left = math.pi, right = 0, top = -math.pi / 2, bottom = math.pi / 2 }
local pairs_per_side = { }
for index = 1, #defenders do
	local side = sides[(index - 1) % #sides + 1]
	pairs_per_side[side] = (pairs_per_side[side] or 0) + 1
end

local function CutRamp(side, along)
	for offset = 0, RAMP_WIDTH - 1 do
		local at = along + offset
		for depth = 0, RIM_THICKNESS - 1 do
			if side == "left" then
				Set(at, left + depth, RAMP)
			elseif side == "right" then
				Set(at, right - depth, RAMP)
			elseif side == "top" then
				Set(top + depth, at, RAMP)
			else
				Set(bottom - depth, at, RAMP)
			end
		end
	end
end

local inner = (bottom - top + 1) - 2 * RIM_THICKNESS
for side, count in pairs(pairs_per_side) do
	for pair = 1, count do
		-- Centre of this pair along the side, then one ramp either side of it.
		local centre = top + RIM_THICKNESS + math.floor(inner * (pair - 0.5) / count)
		CutRamp(side, centre - math.ceil(RAMP_SPACING / 2) - math.floor(RAMP_WIDTH / 2))
		CutRamp(side, centre + math.ceil(RAMP_SPACING / 2) - math.floor(RAMP_WIDTH / 2))
	end
end

-- Cover off the plateau, kept a few squares clear of the rim.
for row = 1, gridSize do
	for col = 1, gridSize do
		local near_plateau = row >= top - 3 and row <= bottom + 3 and col >= left - 3 and col <= right + 3
		if not near_plateau then
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

-- Defenders together in the middle: alone in the centre, otherwise a little towards their own ramps.
local cluster = math.max(3, math.floor(inner / 5))
for index, player in ipairs(defenders) do
	if #defenders == 1 then
		PlaceStart(player, middle, middle)
	else
		-- Each defender sits on the side of their own ramps; a second lap of sides moves in closer.
		local angle = SIDE_ANGLES[sides[(index - 1) % #sides + 1]]
		local distance = cluster / (1 + math.floor((index - 1) / #sides))
		PlaceStart(player, middle + Round(math.sin(angle) * distance, 0), middle + Round(math.cos(angle) * distance, 0))
	end
end

-- Attackers spread around the edge of the map.
local edge = math.max(2, math.floor(gridSize * 0.08))
local reach = middle - edge
for index, player in ipairs(attackers) do
	local angle = math.pi / 4 + 2 * math.pi * (index - 1) / math.max(1, #attackers)
	-- On a square ring rather than a circle, so diagonal starts go into the corners, away from the moat.
	local stretch = reach / math.max(math.abs(math.sin(angle)), math.abs(math.cos(angle)))
	local row = middle + Round(math.sin(angle) * stretch, 0)
	local col = middle + Round(math.cos(angle) * stretch, 0)
	PlaceStart(player, math.max(2, math.min(gridSize - 1, row)), math.max(2, math.min(gridSize - 1, col)))
end

-- Extra gold and stone on the plateau, in the corners away from the ramps.
local near = RIM_THICKNESS + 1
Set(top + near, left + near, tt_gold_large)
Set(bottom - near, right - near, tt_gold_large)
Set(top + near, right - near, tt_stone_large)
Set(bottom - near, left + near, tt_stone_large)

-- A sacred site near the middle of the map, at least SACRED_CLEARANCE squares from every start.
local SACRED_CLEARANCE = 4
local function NearStart(row, col)
	for r = row - SACRED_CLEARANCE + 1, row + SACRED_CLEARANCE - 1 do
		for c = col - SACRED_CLEARANCE + 1, col + SACRED_CLEARANCE - 1 do
			if r >= 1 and r <= gridSize and c >= 1 and c <= gridSize and terrainLayoutResult[r][c].playerIndex ~= nil then
				return true
			end
		end
	end
	return false
end
-- With no such spot, as with four defenders round the middle, the centre itself is still a few squares clear.
local sacred_row = middle
for _, offset in ipairs({ 0, -4, 4, -6, 6 }) do
	if not NearStart(middle + offset, middle) then
		sacred_row = middle + offset
		break
	end
end
Set(sacred_row, middle, tt_holy_site)
