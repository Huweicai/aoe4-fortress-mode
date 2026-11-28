-- Hidden human buffs: free armor upgrades and trebuchet weapon modifiers.
-- Run: lua tests/buffs_test.lua assets/scar/winconditions/fortress_mode.scar
local path = arg[1]
local log = { upgrades = { }, modifiers = { }, applied = { } }
setmetatable(_G, { __index = function(_, name) if name:match("^[A-Z]") then return function() end end end })
function import() end
function print() end
MAT_WeaponType, MUT_Multiplication = "MAT_WeaponType", "MUT_Multiplication"
function BP_GetUpgradeBlueprint(name) if name:find("missing") then error("no such upgrade") end return "upg:" .. name end
function Player_CompleteUpgrade(p, u) table.insert(log.upgrades, { p = p, u = u }) end
function BP_GetWeaponBlueprint(name) if name:find("_jin") then error("not in this game") end return "wpn:" .. name end
function Modifier_Create(target, kind, mut, exclusive, factor, bp)
	if kind == "weapon_wind_down_modifier" then error("unknown modifier") end
	local m = { target = target, kind = kind, factor = factor, bp = bp }
	table.insert(log.modifiers, m)
	return m
end
function Modifier_ApplyToPlayer(m, p) table.insert(log.applied, { m = m, p = p }) end
assert(load(io.open(path):read("a") .. "\n_T = { SetMaximumHealth = SetMaximumHealth, BuildSiegeUnits = BuildSiegeUnits, AnnounceWave = AnnounceWave, ReadNumber = ReadNumber, BoostMonkHealing = BoostMonkHealing, GrantUpgrades = GrantUpgrades, BuffWeapons = BuffWeapons, HUMAN_FREE_UPGRADES = HUMAN_FREE_UPGRADES, HUMAN_TREBUCHET_WEAPONS = HUMAN_TREBUCHET_WEAPONS, HUMAN_TREBUCHET_MODIFIERS = HUMAN_TREBUCHET_MODIFIERS }", "@" .. path))()

local failed = 0
local function check(name, ok) io.write((ok and "PASS " or "FAIL ") .. name .. "\n"); if not ok then failed = failed + 1 end end

_T.GrantUpgrades(7, _T.HUMAN_FREE_UPGRADES)
check("both armor techs granted to that player", #log.upgrades == 2 and log.upgrades[1].p == 7 and log.upgrades[1].u == "upg:upgrade_melee_armor_i" and log.upgrades[2].u == "upg:upgrade_ranged_armor_i")
log.upgrades = { }
_T.GrantUpgrades(7, { "missing_upgrade", "upgrade_melee_armor_i" })
check("an unknown upgrade is skipped, the rest still granted", #log.upgrades == 1)

-- In the game a player id is an engine object, not a number, so the tests pass a table.
local PLAYER = setmetatable({ }, { __tostring = function() return "Player7" end })
local ok, err = pcall(_T.BuffWeapons, PLAYER, _T.HUMAN_TREBUCHET_WEAPONS, _T.HUMAN_TREBUCHET_MODIFIERS)
check("player id that is not a number does not break it", ok)
local by = { }
for _, a in ipairs(log.applied) do by[a.m.bp] = by[a.m.bp] or { }; by[a.m.bp][a.m.kind] = a.m.factor; assert(a.p == PLAYER) end
local cw = by["wpn:weapon_trebuchet_4_counterweight"]
check("counterweight: damage x3, range x1.2, reload x2/3", cw and cw.damage_weapon_modifier == 3 and cw.range_weapon_modifier == 1.2 and math.abs(cw.reload_weapon_modifier - 2 / 3) < 1e-9)
check("greek fire trebuchet buffed too", by["wpn:weapon_trebuchet_4_greek_fire"] ~= nil)
check("a rejected modifier does not stop the others", cw.weapon_wind_down_modifier == nil and cw.damage_weapon_modifier == 3)
check("a missing weapon is skipped", by["wpn:weapon_trebuchet_4_grenade_jin"] == nil)
check("weapon type modifiers, as a player modifier", log.modifiers[1].target == "MAT_WeaponType")

-- monk healing
local rates = { }
function Player_GetStateModelFloat(p, key) assert(key == "monk_heal_rate"); return rates[p] end
function Player_SetStateModelFloat(p, key, v) assert(key == "monk_heal_rate"); rates[p] = v end
local human = { id = 7, index = 1 }
rates[7] = 7; _T.BoostMonkHealing(human); check("monk healing 7 -> 105", rates[7] == 105)
_T.BoostMonkHealing(human); check("not boosted twice", rates[7] == 105)
rates[7] = 110; _T.BoostMonkHealing(human); check("a tech raising it on top is left alone", rates[7] == 110)
rates[7] = 10; _T.BoostMonkHealing(human); check("a tech setting it lower is boosted again", rates[7] == 150)
rates[8] = nil; _T.BoostMonkHealing({ id = 8, index = 2 }); check("no property: nothing set", rates[8] == nil)

-- numeric options read from their keys
local function section(key, chosen, items) local e = { } for i, k in ipairs(items) do e[k] = i end return { [key] = { enum_items = e, enum_value = e[chosen] } } end
check("70 s wave interval", _T.ReadNumber(section("o", "wave_every_70", { "wave_every_30", "wave_every_70" }), "o", "wave_every", 1, 60) == 70)
check("x1.75 health", _T.ReadNumber(section("o", "unit_hp_175", { "unit_hp_100", "unit_hp_175" }), "o", "unit_hp", 100, 2) == 1.75)
check("off is 0", _T.ReadNumber(section("o", "assault_every_off", { "assault_every_off", "assault_every_60" }), "o", "assault_every", 1, 120) == 0)
check("old key falls back", _T.ReadNumber(section("o", "wave_interval_1", { "wave_interval_1" }), "o", "wave_every", 1, 60) == 60)
check("missing option falls back", _T.ReadNumber({ }, "o", "wave_every", 1, 60) == 60)
-- wave announcement
do
	local blips, cues = { }, { }
	ECV_Queue, ECV_Title = "queue", "title"
	function UI_CreateMinimapBlipOnPosFrom(sender, pos, life, template) table.insert(blips, { sender = sender, pos = pos, life = life, template = template }) end
	function UI_CreateEventCue(title, desc, template, icon, sound, visibility, life) table.insert(cues, { title = title, visibility = visibility, sound = sound, life = life }) end
	function Loc_Empty() return "" end
	local ai = { id = "AI3" }
	_T.AnnounceWave(ai, { x = 5 }, "敌军来袭 · Enemy wave incoming")
	check("wave: blip in the attacker's colour where it spawns", #blips == 1 and blips[1].sender == "AI3" and blips[1].pos.x == 5 and blips[1].life > 0)
	check("wave: cue in the side queue with a sound, not mid-screen", #cues == 1 and cues[1].visibility == "queue" and cues[1].sound ~= "" and cues[1].title:find("Enemy wave", 1, true))
end

-- siege of the first wave: half the rams come as bombards
do
	local no_bombard = false
	function Cardinal_ConvertTypeToSquadBlueprint(types) if types[1] == "scar_bombard" and no_bombard then return nil end return types[1] end
	local function count(units) local c = { } for _, u in ipairs(units) do c[u.sbp] = (c[u.sbp] or 0) + u.numSquads end return c end
	local c = count(_T.BuildSiegeUnits(1))
	check("first wave: 1 ram and 2 bombards instead of 2 and 1", c.scar_ram == 1 and c.scar_bombard == 2)
	no_bombard = true
	c = count(_T.BuildSiegeUnits(1))
	check("a civ without bombards keeps all its rams", c.scar_ram == 2 and c.scar_bombard == nil)
end

-- human monks
do
	MUT_Set = "MUT_Set"
	local made = { }
	function Modifier_Create(target, kind, mut, exclusive, value, bp) local m = { kind = kind, mut = mut, value = value, bp = bp }; table.insert(made, m); return m end
	local applied = { }
	function Modifier_ApplyToPlayer(m, p) table.insert(applied, { m = m, p = p }) end
	_T.SetMaximumHealth({ "monk_eng", "monk_chi" }, "P1", 1000)
	check("monks: health set to 1000, not multiplied", #applied == 2 and made[1].kind == "health_maximum_modifier" and made[1].mut == "MUT_Set" and made[1].value == 1000 and applied[1].p == "P1")
end

io.write(failed == 0 and "ALL OK\n" or ("FAILED " .. failed .. "\n"))
os.exit(failed == 0 and 0 or 1)
