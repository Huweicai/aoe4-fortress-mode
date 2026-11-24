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
assert(load(io.open(path):read("a") .. "\n_T = { GrantUpgrades = GrantUpgrades, BuffWeapons = BuffWeapons, HUMAN_FREE_UPGRADES = HUMAN_FREE_UPGRADES, HUMAN_TREBUCHET_WEAPONS = HUMAN_TREBUCHET_WEAPONS, HUMAN_TREBUCHET_MODIFIERS = HUMAN_TREBUCHET_MODIFIERS }", "@" .. path))()

local failed = 0
local function check(name, ok) io.write((ok and "PASS " or "FAIL ") .. name .. "\n"); if not ok then failed = failed + 1 end end

_T.GrantUpgrades(7, _T.HUMAN_FREE_UPGRADES)
check("both armor techs granted to that player", #log.upgrades == 2 and log.upgrades[1].p == 7 and log.upgrades[1].u == "upg:upgrade_melee_armor_i" and log.upgrades[2].u == "upg:upgrade_ranged_armor_i")
log.upgrades = { }
_T.GrantUpgrades(7, { "missing_upgrade", "upgrade_melee_armor_i" })
check("an unknown upgrade is skipped, the rest still granted", #log.upgrades == 1)

_T.BuffWeapons(7, _T.HUMAN_TREBUCHET_WEAPONS, _T.HUMAN_TREBUCHET_MODIFIERS)
local by = { }
for _, a in ipairs(log.applied) do by[a.m.bp] = by[a.m.bp] or { }; by[a.m.bp][a.m.kind] = a.m.factor; assert(a.p == 7) end
local cw = by["wpn:weapon_trebuchet_4_counterweight"]
check("counterweight: damage x3, range x1.2, reload x2/3", cw and cw.damage_weapon_modifier == 3 and cw.range_weapon_modifier == 1.2 and math.abs(cw.reload_weapon_modifier - 2 / 3) < 1e-9)
check("greek fire trebuchet buffed too", by["wpn:weapon_trebuchet_4_greek_fire"] ~= nil)
check("a rejected modifier does not stop the others", cw.weapon_wind_down_modifier == nil and cw.damage_weapon_modifier == 3)
check("a missing weapon is skipped", by["wpn:weapon_trebuchet_4_grenade_jin"] == nil)
check("weapon type modifiers, as a player modifier", log.modifiers[1].target == "MAT_WeaponType")
io.write(failed == 0 and "ALL OK\n" or ("FAILED " .. failed .. "\n"))
os.exit(failed == 0 and 0 or 1)
