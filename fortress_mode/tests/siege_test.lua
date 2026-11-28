-- Focused test for siege retargeting: idle, gone or stuck squads get a new target. Run: lua tests/siege_test.lua assets/scar/winconditions/fortress_mode.scar
-- Unknown engine calls are stubbed as no-ops; the script's locals are exposed through _T.
local path = arg[1]
local log = { attacks = { }, debug = { } }
setmetatable(_G, { __index = function(_, name)
	if name:match("^[A-Z]") then return function() end end
end })
function Misc_IsDevMode() return true end
function import() end
function print(s) table.insert(log.debug, s) end
local now = 0
function World_GetGameTime() return now end
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
function Squad_GetID(s) return s.id end
local by_id = { }
function Entity_IsValid(id) return by_id[id] ~= nil and not by_id[id].dead end
function Entity_FromID(id) return by_id[id] end
function Entity_GetHealth(e) return e.health or 100 end
function EGroup_ForEach(g, f) for i, e in ipairs(g.list) do f(g, i, e) end end
local buildings = { }
local function index_buildings() by_id = { } for _, b in ipairs(buildings) do by_id[b.id] = b end end
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
function Cmd_AttackMove(sg, pos)
	local ids = { }
	for _, s in ipairs(sg.squads) do table.insert(ids, s.id) end
	table.insert(log.attacks, { squads = ids, move_to = pos.x })
end
function Cmd_Attack(sg, eg)
	local ids = { }
	for _, s in ipairs(sg.squads) do table.insert(ids, s.id) end
	table.insert(log.attacks, { squads = ids, target = eg.list[1].id })
end

local source = io.open(path):read("a")
local chunk = assert(load(source .. "\n_T = { OrderSiegeSquads = OrderSiegeSquads }", "@" .. path))
chunk()

local failed = 0
local function check(name, ok)
	print = io.write
	io.write((ok and "PASS " or "FAIL ") .. name .. "\n")
	if not ok then failed = failed + 1 end
end
local human = { id = 1, index = 1 }
local function force(squads) local g = sgroup("siege"); g.squads = squads; return { attacker = { id = 3, index = 3 }, target = human, siege = g } end
local function reset(b) log.attacks = { }; buildings = b; index_buildings() end
local function P(x) return { x = x, y = 0, z = 0 } end
local function pass(f) log.attacks = { }; _T.OrderSiegeSquads(f) end

-- wall at 300 in front of a keep at 500
reset({ { id = 10, owner = 1, type = "building", pos = P(500) }, { id = 20, owner = 1, type = "wall", pos = P(300) } })
local f = force({ { id = 1, idle = false, pos = P(100) } }); f.building_id = 10
pass(f); check("busy and moving siege keeps its order", #log.attacks == 0)
f.siege.squads[1].pos = P(200); now = 10; pass(f); check("still moving: no order", #log.attacks == 0)
now = 40; pass(f); check("stopped for 30 s without hurting its target: sent at what is closest", #log.attacks == 1 and log.attacks[1].target == 20)
now = 50; by_id[20].health = 90; pass(f); now = 60; by_id[20].health = 80; pass(f); now = 90; by_id[20].health = 70; pass(f)
check("standing still but hurting its target is left alone", #log.attacks == 0)

-- unreachable target: busy forever, never idle
reset({ { id = 10, owner = 1, type = "building", pos = P(300) }, { id = 11, owner = 1, type = "building", pos = P(600) } })
now = 0
local u = force({ { id = 1, idle = false, pos = P(250) } }); u.building_id = 10
pass(u); now = 30; pass(u)
check("stuck on an unreachable target: sent elsewhere", #log.attacks == 1 and log.attacks[1].target == 11)
now = 60; pass(u); now = 90; pass(u)
check("stuck again: the first target is still avoided", #log.attacks == 1 and log.attacks[1].target ~= 10 or #log.attacks == 0)
now = 300; u.siege_tracks[1].since = 0; pass(u)
check("after a while the avoided target may be tried again", #log.attacks == 1)

-- a ram stuck behind a forest goes for the building the infantry reached rather than the nearest one
reset({ { id = 10, owner = 1, type = "building", pos = P(300) }, { id = 11, owner = 1, type = "building", pos = P(320) }, { id = 12, owner = 1, type = "building", pos = P(700) } })
now = 0
local fo = force({ { id = 1, idle = false, pos = P(250) } }); fo.building_id = 12
fo.siege_tracks = { [1] = { avoid = { }, target_id = 10 } }
pass(fo); now = 30; pass(fo)
check("stuck: follows the infantry's target first", #log.attacks == 1 and log.attacks[1].target == 12)
now = 60; pass(fo)
check("stuck on that too: falls back to the nearest one not avoided", #log.attacks == 1 and log.attacks[1].target == 11)
now = 90; pass(fo)
check("every target avoided: attack-moves with the infantry", #log.attacks == 1 and log.attacks[1].move_to == 700)

-- idle and gone targets
reset({ { id = 10, owner = 1, type = "building", pos = P(500) }, { id = 20, owner = 1, type = "wall", pos = P(300) } })
now = 0
local i = force({ { id = 1, idle = true, pos = P(290) }, { id = 2, idle = false, pos = P(290) } }); i.building_id = 10
pass(i); check("idle squad reordered, busy one left alone", #log.attacks == 1 and #log.attacks[1].squads == 1 and log.attacks[1].squads[1] == 1)
i.siege.squads[1].idle = false; by_id[10].dead = true; pass(i)
check("target gone: the busy squad is reordered too", #log.attacks == 1 and #log.attacks[1].squads == 1 and log.attacks[1].squads[1] == 2)
local g = force({ { id = 1, idle = true, pos = P(290) }, { id = 2, idle = true, pos = P(291) } })
pass(g); check("one order per squad, never a formation", #log.attacks == 2 and #log.attacks[1].squads == 1 and #log.attacks[2].squads == 1)
reset({ { id = 10, owner = 1, type = "building", pos = P(300) }, { id = 11, owner = 1, type = "building", pos = P(340) } })
local crowd = { } for k = 1, 5 do crowd[k] = { id = k, idle = true, pos = P(250) } end
pass(force(crowd)); local per = { } for _, a in ipairs(log.attacks) do per[a.target] = (per[a.target] or 0) + 1 end
check("at most 3 squads per building, the rest go to the next one", per[10] == 3 and per[11] == 2)
local busy = force({ { id = 1, idle = false, pos = P(250) }, { id = 2, idle = false, pos = P(250) }, { id = 3, idle = false, pos = P(250) }, { id = 4, idle = true, pos = P(250) } })
busy.siege_tracks = { [1] = { avoid = { }, target_id = 10, since = 0 }, [2] = { avoid = { }, target_id = 10, since = 0 }, [3] = { avoid = { }, target_id = 10, since = 0 } }
pass(busy); check("squads still on a building count towards its 3", #log.attacks == 1 and log.attacks[1].target == 11)
reset({ { id = 10, owner = 1, type = "building", pos = P(500) }, { id = 20, owner = 1, type = "wall", pos = P(300) } })
local d = force({ { id = 1, idle = true, pos = P(290) }, { id = 2, idle = true, pos = P(495) } })
pass(d); local t = { } for _, a in ipairs(log.attacks) do t[a.target] = a.squads[1] end
check("each squad goes for what is closest to it", #log.attacks == 2 and t[20] == 1 and t[10] == 2)
local gone = force({ { id = 1, idle = true, pos = P(290) } }); pass(gone); gone.siege.squads = { }; pass(gone)
check("tracks of dead squads are dropped", next(gone.siege_tracks) == nil)

reset({ { id = 10, owner = 1, type = "building", pos = P(500) }, no_wall_type = true })
pass(force({ { id = 1, idle = true, pos = P(290) } })); check("an unknown wall type falls back to buildings", #log.attacks == 1 and log.attacks[1].target == 10)
reset({ { id = 10, owner = 2, type = "building", pos = P(500) } })
pass(force({ { id = 1, idle = true, pos = P(290) } })); check("nothing of the target human left: no crash", true)
reset({ })
pass(force({ })); check("empty siege group: no order", #log.attacks == 0)

-- cost: a whole wave needing new targets at once must stay cheap in a single tick
do
	local many = { }
	for k = 1, 200 do many[k] = { id = 1000 + k, owner = 1, type = "building", pos = P(300 + k) } end
	reset(many)
	local calls = 0
	local real = Entity_GetPosition
	Entity_GetPosition = function(e) calls = calls + 1; return real(e) end
	local wave = { } for k = 1, 20 do wave[k] = { id = k, idle = true, pos = P(250) } end
	pass(force(wave))
	Entity_GetPosition = real
	check("a whole wave at once: at most 8 new orders this pass", #log.attacks == 8)
	check("building positions read once per pass, not once per squad", calls <= 200)
end

io.write(failed == 0 and "ALL OK\n" or ("FAILED " .. failed .. "\n"))
os.exit(failed == 0 and 0 or 1)
