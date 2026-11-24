-- Focused test for idle-siege retargeting. Run: lua tests/siege_test.lua assets/scar/winconditions/fortress_mode.scar
-- Unknown engine calls are stubbed as no-ops; the script's locals are exposed through _T.
local path = arg[1]
local log = { attacks = { }, debug = { } }
setmetatable(_G, { __index = function(_, name)
	if name:match("^[A-Z]") then return function() end end
end })
function Misc_IsDevMode() return true end
function import() end
function print(s) table.insert(log.debug, s) end
function World_GetGameTime() return 0 end
function AI_IsAIPlayer(id) return id >= 3 end
function Player_ObserveRelationship(a, b) return 1 end
R_ENEMY = 1
function World_DistancePointToPoint(a, b) return math.abs(a.x - b.x) end
function Entity_GetPosition(e) return e.pos end
function Entity_GetID(e) return e.id end
local function sgroup(name) return { name = name, squads = { } } end
local sgroups = { }
function SGroup_CreateIfNotFound(n) sgroups[n] = sgroups[n] or sgroup(n); return sgroups[n] end
function SGroup_Clear(g) g.squads = { } end
function SGroup_Add(g, s) table.insert(g.squads, s) end
function SGroup_CountSpawned(g) return #g.squads end
function SGroup_ForEach(g, f) for i, s in ipairs(g.squads) do f(g, i, s) end end
function Squad_IsIdle(s) return s.idle end
function Squad_GetPosition(s) return s.pos end
local buildings = { }
function Player_GetEntitiesFromType(id, t)
	if t == "wall" and buildings.no_wall_type then error("unknown type") end
	local g = { list = { } }
	for _, b in ipairs(buildings) do if b.owner == id and b.type == t then table.insert(g.list, b) end end
	return g
end
function EGroup_CountSpawned(g) return g.list and #g.list or 0 end
function EGroup_GetClosestEntity(g, pos)
	local best
	for _, b in ipairs(g.list) do if not best or math.abs(b.pos.x - pos.x) < math.abs(best.pos.x - pos.x) then best = b end end
	return best
end
function EGroup_CreateIfNotFound() return { list = { } } end
function EGroup_Clear(g) g.list = { } end
function EGroup_Add(g, e) table.insert(g.list, e) end
function Cmd_Attack(sg, eg)
	local ids = { }
	for _, s in ipairs(sg.squads) do table.insert(ids, s.id) end
	table.insert(log.attacks, { squads = ids, target = eg.list[1].id })
end

local source = io.open(path):read("a")
local chunk = assert(load(source .. "\n_T = { OrderIdleSiege = OrderIdleSiege }", "@" .. path))
chunk()

local failed = 0
local function check(name, ok)
	print = io.write
	io.write((ok and "PASS " or "FAIL ") .. name .. "\n")
	if not ok then failed = failed + 1 end
end
local human = { id = 1, index = 1 }
local function force(squads) local g = sgroup("siege"); g.squads = squads; return { attacker = { id = 3, index = 3 }, target = human, siege = g } end
local function reset(b) log.attacks = { }; buildings = b end
local function P(x) return { x = x, y = 0, z = 0 } end

reset({ { id = 10, owner = 1, type = "building", pos = P(500) }, { id = 20, owner = 1, type = "wall", pos = P(300) } })
_T.OrderIdleSiege(force({ { id = 1, idle = false, pos = P(290) } }))
check("busy siege gets no order", #log.attacks == 0)

reset(buildings)
_T.OrderIdleSiege(force({ { id = 1, idle = true, pos = P(290) }, { id = 2, idle = false, pos = P(290) } }))
check("idle ram outside the wall attacks the wall", #log.attacks == 1 and log.attacks[1].target == 20 and #log.attacks[1].squads == 1 and log.attacks[1].squads[1] == 1)

reset(buildings)
_T.OrderIdleSiege(force({ { id = 1, idle = true, pos = P(290) }, { id = 2, idle = true, pos = P(495) } }))
local t = { } for _, a in ipairs(log.attacks) do t[a.target] = a.squads[1] end
check("each idle squad goes for what is closest to it", #log.attacks == 2 and t[20] == 1 and t[10] == 2)

reset(buildings)
_T.OrderIdleSiege(force({ { id = 1, idle = true, pos = P(290) }, { id = 2, idle = true, pos = P(291) } }))
check("squads with the same target share one order", #log.attacks == 1 and #log.attacks[1].squads == 2)

reset({ { id = 10, owner = 1, type = "building", pos = P(500) }, no_wall_type = true })
_T.OrderIdleSiege(force({ { id = 1, idle = true, pos = P(290) } }))
check("an unknown wall type falls back to buildings", #log.attacks == 1 and log.attacks[1].target == 10)

reset({ { id = 10, owner = 2, type = "building", pos = P(500) } })
_T.OrderIdleSiege(force({ { id = 1, idle = true, pos = P(290) } }))
check("nothing of the target human left: no crash", true)

reset({ })
_T.OrderIdleSiege(force({ }))
check("empty siege group: no order", #log.attacks == 0)

io.write(failed == 0 and "ALL OK\n" or ("FAILED " .. failed .. "\n"))
os.exit(failed == 0 and 0 or 1)
