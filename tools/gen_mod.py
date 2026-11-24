#!/usr/bin/env python3
"""Generates the Fortress Mode project files that Content Editor would otherwise write.

Usage: gen_mod.py <path to a burnproj from any Game Mode project> <its mod name> <its mod GUID>
Option keys must match assets/scar/winconditions/fortress_mode.scar.
"""
import hashlib
import struct
import sys
import uuid
import zlib
from pathlib import Path
from xml.sax.saxutils import escape

MOD_NAME = "fortress_mode"
MOD_GUID = uuid.UUID("7f3c2a14-9b6e-4d21-8c5a-3e1f60b7d942")
ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
WINCOND = ASSETS / "scar" / "winconditions"
LOCDB = ASSETS / "locdb"

TITLE = ("Fortress Mode", "堡垒模式")
DESCRIPTION = (
    "Co-op against the AI behind tough walls. Enemy AIs take turns sending siege waves and launch regular "
    "all-out attacks, while your units and defenses are far sturdier. Every value is set in the lobby, "
    "next to all the standard game options.",
    "和朋友一起守城打 AI。敌方 AI 轮流派出攻城波次，还会定期全军总攻；你的单位和防御建筑则耐打得多。"
    "所有数值都在房间设置里调整，标准模式的选项全部保留。",
)
# The lobby options of the official standard mode. A WinCondition cannot inherit them, so they are
# declared again here, with the keys, text IDs and defaults read from Data.sga scar\winconditions\standard_mode.bin.
OFFICIAL_SECTIONS = [
    ("section_inner_win_conditions", 11162694, True, [
        ("bool", "option_win_condition_conquest", 11162695, 0, 11169855, True),
        ("bool", "option_win_condition_religious", 11162696, 0, 11169856, True),
        ("bool", "option_win_condition_wonder", 11162697, 0, 11169857, True),
        ("bool", "option_win_condition_regicide", 11261399, 0, 11218487, False),
    ]),
    ("section_starting_conditions", 11162698, False, [
        ("bool", "option_score", 11217778, 11217780, 11217781, False),
        ("enum", "option_resources", 11162699, 0, 11184041, "resources_standard", [
            ("resources_standard", 11183007, 40560), ("resources_high", 11183008, 40561),
            ("resources_very_high", 11183009, 11184042), ("resources_max", 11217750, 11217751)]),
        ("enum", "option_start_age", 11182993, 0, 11184044, "option_start_age_1", [
            ("option_start_age_1", 11162701, 11183854), ("option_start_age_2", 11162702, 11183855),
            ("option_start_age_3", 11162703, 11183856), ("option_start_age_4", 11162704, 11183857)]),
        ("enum", "option_fow", 11183006, 0, 11184045, "option_fow_conceal", [
            ("option_fow_conceal", 11162705, 11183858), ("option_fow_explore", 11162706, 11183859),
            ("option_fow_reveal", 11162707, 11183860)]),
        ("bool", "reveal_fow_on_elimination", 11217779, 11217782, 11217782, False),
    ]),
]
SECTION_KEY = "section_fortress"
SECTION_NAME = ("Fortress Settings", "堡垒设置")

# key, English name, Chinese name, English tooltip, Chinese tooltip, default item, items
OPTIONS = [
    ("option_unit_health", "Human Unit Health", "玩家单位血量",
     "Health multiplier for human players' military units.", "真人玩家军事单位的血量倍率。",
     "unit_hp_200",
     [("unit_hp_100", "x1"), ("unit_hp_150", "x1.5"), ("unit_hp_200", "x2"),
      ("unit_hp_300", "x3"), ("unit_hp_400", "x4"), ("unit_hp_500", "x5")]),
    ("option_defense_health", "Human Defense Health", "玩家防御建筑血量",
     "Health multiplier for human players' walls, gates, towers, outposts and keeps.",
     "真人玩家城墙、城门、哨塔和城堡的血量倍率。",
     "defense_hp_400",
     [("defense_hp_100", "x1"), ("defense_hp_200", "x2"), ("defense_hp_300", "x3"),
      ("defense_hp_400", "x4"), ("defense_hp_500", "x5"), ("defense_hp_800", "x8"),
      ("defense_hp_1000", "x10")]),
    ("option_trebuchet", "Disable Trebuchets", "禁用巨型投石机",
     "Who cannot build trebuchets.", "哪些玩家不能建造巨型投石机。",
     "trebuchet_ai",
     [("trebuchet_off", ("Nobody", "不禁用")), ("trebuchet_ai", ("AI only", "仅 AI")),
      ("trebuchet_humans", ("Humans only", "仅真人玩家")), ("trebuchet_all", ("Everyone", "所有玩家"))]),
    ("option_human_pop", "Human Population Cap", "玩家人口上限",
     "Maximum population for human players.", "真人玩家的人口上限。",
     "human_pop_300",
     [("human_pop_200", "200"), ("human_pop_250", "250"), ("human_pop_300", "300"),
      ("human_pop_400", "400"), ("human_pop_500", "500")]),
    ("option_ai_pop", "AI Population Cap", "AI 人口上限",
     "Maximum population for AI players.", "AI 玩家的人口上限。",
     "ai_pop_200",
     [("ai_pop_100", "100"), ("ai_pop_150", "150"), ("ai_pop_200", "200"),
      ("ai_pop_250", "250"), ("ai_pop_300", "300")]),
    ("option_ai_production", "AI Unit Production Speed", "AI 造兵速度",
     "Unit production speed multiplier for AI players' buildings.", "AI 玩家建筑的单位生产速度倍率。",
     "ai_production_200",
     [("ai_production_100", "x1"), ("ai_production_125", "x1.25"), ("ai_production_150", "x1.5"),
      ("ai_production_200", "x2"), ("ai_production_300", "x3")]),
    ("option_minerals", "Gold and Stone Deposits", "金矿石矿储量",
     "Multiplies how much every gold and stone deposit on the map holds.", "地图上所有金矿和石矿的储量倍率。",
     "minerals_200",
     [("minerals_100", ("x1 (standard)", "×1（原版）")), ("minerals_150", "×1.5"), ("minerals_200", "×2"),
      ("minerals_300", "×3"), ("minerals_500", "×5")]),
    ("option_start_villagers", "Starting Villagers", "初始村民",
     "Villagers every player starts with.", "所有玩家（含 AI）开局时的村民数量。",
     "start_villagers_16",
     [("start_villagers_6", ("6 (standard)", "6（原版）")), ("start_villagers_10", "10"), ("start_villagers_16", "16"),
      ("start_villagers_20", "20"), ("start_villagers_30", "30")]),
    ("option_assault_interval", "AI All-Out Attack", "AI 定期总攻",
     "From minute 8 on, how often one enemy AI with a standing main town center sends its whole land army.", "从第 8 分钟开始，每隔这段时间，随机一家主城镇中心还在的敌方 AI 派出全部陆军。",
     "assault_2",
     [("assault_off", ("Off", "关")), ("assault_1", ("1 min", "1 分钟")), ("assault_2", ("2 min", "2 分钟")),
      ("assault_3", ("3 min", "3 分钟")), ("assault_5", ("5 min", "5 分钟")), ("assault_10", ("10 min", "10 分钟"))]),
    ("option_survive_time", "Survival Victory", "存活胜利",
     "Humans win if they are still alive after this long.", "坚持到这个时间，真人一方获胜。",
     "survive_60",
     [("survive_off", ("Off", "关")), ("survive_5", ("5 min (test)", "5 分钟（测试）")), ("survive_30", ("30 min", "30 分钟")),
      ("survive_45", ("45 min", "45 分钟")), ("survive_60", ("60 min", "60 分钟")),
      ("survive_90", ("90 min", "90 分钟")), ("survive_120", ("120 min", "120 分钟"))]),
    ("option_wave_size", "Attack Wave Size", "攻城波次规模",
     "Units in each attack wave. One AI attacks at a time, spawning near its town center.",
     "每波攻城的单位数量。AI 轮流出兵，从自己的城镇中心附近出发。",
     "wave_size_100",
     [("wave_size_0", ("Off", "关")), ("wave_size_50", "50"), ("wave_size_100", "100"),
      ("wave_size_150", "150"), ("wave_size_200", "200")]),
    ("option_wave_first", "First Wave", "首波时间",
     "When the first attack wave starts.", "第一波攻城开始的时间。",
     "wave_first_10",
     [("wave_first_1", ("1 min (test)", "1 分钟（测试）")), ("wave_first_5", ("5 min", "5 分钟")), ("wave_first_10", ("10 min", "10 分钟")),
      ("wave_first_15", ("15 min", "15 分钟")), ("wave_first_20", ("20 min", "20 分钟"))]),
    ("option_wave_interval", "Wave Interval", "波次间隔",
     "Time between attack waves.", "两波攻城之间的间隔。",
     "wave_interval_1",
     [("wave_interval_1", ("1 min", "1 分钟")), ("wave_interval_2", ("2 min", "2 分钟")), ("wave_interval_5", ("5 min", "5 分钟")), ("wave_interval_8", ("8 min", "8 分钟")),
      ("wave_interval_10", ("10 min", "10 分钟")), ("wave_interval_15", ("15 min", "15 分钟"))]),
]


class Strings:
    """Assigns localization IDs in first-use order."""

    def __init__(self):
        self.rows = []

    def add(self, english, chinese=None):
        self.rows.append((english, english if chinese is None else chinese))
        return len(self.rows)


def stable_id(*parts):
    digest = hashlib.sha256("/".join(map(str, parts)).encode()).digest()
    return struct.unpack("<Q", digest[:8])[0]


def mod_parts():
    return struct.unpack("<IIII", MOD_GUID.bytes_le)


def loc_property(name, loc_key, owner, path, official=False):
    part0, part1, part2, part3 = (0, 0, 0, 0) if official else mod_parts()
    loc_id = stable_id(path, name)
    return f"""<DataProperty Name="{name}" Type="Object">
<DataValue Name="util::ReflectLocString">{loc_id}</DataValue>
<DataObject Name="" Type="util::ReflectLocString" Id="{loc_id}" OwnerId="{owner}">
<DataProperty Name="m_modPart2" Type="UInt32" Value="{part2}"/>
<DataProperty Name="m_modPart3" Type="UInt32" Value="{part3}"/>
<DataProperty Name="m_modPart0" Type="UInt32" Value="{part0}"/>
<DataProperty Name="m_modPart1" Type="UInt32" Value="{part1}"/>
<DataProperty Name="m_locStringKey" Type="Int32" Value="{loc_key}"/>
</DataObject>
</DataProperty>"""


def enum_item(item, default_key, owner, strings):
    key, label = item
    english, chinese = (label, label) if isinstance(label, str) else label
    item_id = stable_id("item", key)
    loc_key = strings.add(english, chinese)
    is_default = "true" if key == default_key else "false"
    return item_id, f"""<DataObject Name="" Type="WinCondition::OptionEnumItemUIDescriptor" Id="{item_id}" OwnerId="{owner}">
<DataProperty Name="m_key" Type="String" Value="{key}"/>
{loc_property("m_feSummaryName", loc_key, item_id, key)}
{loc_property("m_feName", loc_key, item_id, key)}
<DataProperty Name="m_isDefaultValue" Type="Bool" Value="{is_default}"/>
<DataProperty Name="m_devOnly" Type="Bool" Value="false"/>
</DataObject>"""


def enum_option(option, owner, strings):
    key, en_name, zh_name, en_tip, zh_tip, default_key, items = option
    option_id = stable_id("option", key)
    built = [enum_item(item, default_key, option_id, strings) for item in items]
    values = "\n".join(f'<DataValue Name="WinCondition::OptionEnumItemUIDescriptor">{i}</DataValue>' for i, _ in built)
    bodies = "\n".join(body for _, body in built)
    name_key = strings.add(en_name, zh_name)
    tip_key = strings.add(en_tip, zh_tip)
    return option_id, f"""<DataObject Name="" Type="WinCondition::EnumerationOptionUIDescriptor" Id="{option_id}" OwnerId="{owner}">
<DataProperty Name="#BaseTypes" Type="String" Value="WinCondition::OptionUIDescriptor#0|"/>
<DataProperty Name="m_key" Type="String" Value="{key}"/>
<DataProperty Name="m_enumItems" Type="Object">
{values}
{bodies}
</DataProperty>
{loc_property("m_feSummaryName", name_key, option_id, key)}
{loc_property("m_feDescriptionTooltip", tip_key, option_id, key)}
{loc_property("m_feName", name_key, option_id, key)}
</DataObject>"""


def official_loc(name, loc_key, owner, path):
    return loc_property(name, loc_key, owner, path, official=True)


def official_bool(option, owner):
    _, key, name_key, summary_key, tooltip_key, default = option
    option_id = stable_id("option", key)
    return option_id, "BooleanOptionUIDescriptor", f"""<DataObject Name="" Type="WinCondition::BooleanOptionUIDescriptor" Id="{option_id}" OwnerId="{owner}">
<DataProperty Name="#BaseTypes" Type="String" Value="WinCondition::OptionUIDescriptor#0|"/>
<DataProperty Name="m_key" Type="String" Value="{key}"/>
<DataProperty Name="m_defaultValue" Type="Bool" Value="{"true" if default else "false"}"/>
{official_loc("m_feSummaryName", summary_key, option_id, key)}
{official_loc("m_feDescriptionTooltip", tooltip_key, option_id, key)}
{official_loc("m_feName", name_key, option_id, key)}
</DataObject>"""


def official_enum(option, owner):
    _, key, name_key, summary_key, tooltip_key, default_key, items = option
    option_id = stable_id("option", key)
    values, bodies = [], []
    for item_key, item_name, item_summary in items:
        item_id = stable_id("item", item_key)
        values.append(f'<DataValue Name="WinCondition::OptionEnumItemUIDescriptor">{item_id}</DataValue>')
        bodies.append(f"""<DataObject Name="" Type="WinCondition::OptionEnumItemUIDescriptor" Id="{item_id}" OwnerId="{option_id}">
<DataProperty Name="m_key" Type="String" Value="{item_key}"/>
{official_loc("m_feSummaryName", item_summary, item_id, item_key)}
{official_loc("m_feName", item_name, item_id, item_key)}
<DataProperty Name="m_isDefaultValue" Type="Bool" Value="{"true" if item_key == default_key else "false"}"/>
<DataProperty Name="m_devOnly" Type="Bool" Value="false"/>
</DataObject>""")
    newline = "\n"
    return option_id, "EnumerationOptionUIDescriptor", f"""<DataObject Name="" Type="WinCondition::EnumerationOptionUIDescriptor" Id="{option_id}" OwnerId="{owner}">
<DataProperty Name="#BaseTypes" Type="String" Value="WinCondition::OptionUIDescriptor#0|"/>
<DataProperty Name="m_key" Type="String" Value="{key}"/>
<DataProperty Name="m_enumItems" Type="Object">
{newline.join(values)}
{newline.join(bodies)}
</DataProperty>
{official_loc("m_feSummaryName", summary_key, option_id, key)}
{official_loc("m_feDescriptionTooltip", tooltip_key, option_id, key)}
{official_loc("m_feName", name_key, option_id, key)}
</DataObject>"""


def official_section(section, owner):
    key, name_key, featured, options = section
    section_id = stable_id("section", key)
    built = [(official_bool if option[0] == "bool" else official_enum)(option, section_id) for option in options]
    values = "\n".join(f'<DataValue Name="WinCondition::{kind}">{i}</DataValue>' for i, kind, _ in built)
    bodies = "\n".join(body for _, _, body in built)
    return section_id, f"""<DataObject Name="" Type="WinCondition::OptionSectionUIDescriptor" Id="{section_id}" OwnerId="{owner}">
<DataProperty Name="m_featured" Type="Bool" Value="{"true" if featured else "false"}"/>
<DataProperty Name="m_key" Type="String" Value="{key}"/>
<DataProperty Name="m_options" Type="Object">
{values}
{bodies}
</DataProperty>
{official_loc("m_feName", name_key, section_id, key)}
</DataObject>"""


def win_condition_rdo(strings):
    root = stable_id("wincondition")
    ui = stable_id("ui")
    section = stable_id("section")
    enum_name = escape("FamilyManagerEnum<FamilyManager::FamilyType::TYP_StartingCondition,StdTraits>")
    enum_attr = enum_name.replace('"', "&quot;")
    starting = stable_id("starting")
    precache = stable_id("precache")

    title_key = strings.add(*TITLE)
    tooltip_key = strings.add(*DESCRIPTION)
    section_key = strings.add(*SECTION_NAME)
    built = [enum_option(option, section, strings) for option in OPTIONS]
    values = "\n".join(f'<DataValue Name="WinCondition::EnumerationOptionUIDescriptor">{i}</DataValue>' for i, _ in built)
    bodies = "\n".join(body for _, body in built)
    official = [official_section(section, ui) for section in OFFICIAL_SECTIONS]
    official_values = "\n".join(f'<DataValue Name="WinCondition::OptionSectionUIDescriptor">{i}</DataValue>' for i, _ in official)
    official_bodies = "\n".join(body for _, body in official)

    return f"""<DataWarehouse>
<DataObject Name="" Type="WinCondition" Id="{root}">
<DataProperty Name="m_maxTeams" Type="Int32" Value="-1"/>
<DataProperty Name="m_startingCondition" Type="Object">
<DataValue Name="{enum_attr}">{starting}</DataValue>
<DataObject Name="" Type="{enum_attr}" Id="{starting}" OwnerId="{root}">
<DataProperty Name="m_enumName" Type="String" Value=""/>
</DataObject>
</DataProperty>
<DataProperty Name="m_gameModeType" Type="String" Value=""/>
<DataProperty Name="m_scarWinConditionFile" Type="String" Value="winconditions\\{MOD_NAME}"/>
<DataProperty Name="m_feAllowSelectingStartingLocations" Type="Bool" Value="true"/>
<DataProperty Name="m_playerUpgrades" Type="Object"/>
<DataProperty Name="m_feIcon" Type="String" Value="images\\multiplayer\\gamemode_swords"/>
<DataProperty Name="m_scarMissionFile" Type="String" Value=""/>
<DataProperty Name="m_feImageSelected" Type="String" Value="images\\illustrations\\create_game\\game_mode_standard_selected"/>
{loc_property("m_feDescriptionTooltip", tooltip_key, root, "root")}
<DataProperty Name="m_startingBuildingReplacements" Type="Object"/>
{loc_property("m_feName", title_key, root, "root")}
<DataProperty Name="m_tuningModGUID" Type="String" Value=""/>
<DataProperty Name="m_optionsUIDescriptor" Type="Object">
<DataValue Name="WinCondition::OptionsUIDescriptor">{ui}</DataValue>
<DataObject Name="" Type="WinCondition::OptionsUIDescriptor" Id="{ui}" OwnerId="{root}">
<DataProperty Name="m_optionSections" Type="Object">
{official_values}
<DataValue Name="WinCondition::OptionSectionUIDescriptor">{section}</DataValue>
{official_bodies}
<DataObject Name="" Type="WinCondition::OptionSectionUIDescriptor" Id="{section}" OwnerId="{ui}">
<DataProperty Name="m_featured" Type="Bool" Value="false"/>
<DataProperty Name="m_key" Type="String" Value="{SECTION_KEY}"/>
<DataProperty Name="m_options" Type="Object">
{values}
{bodies}
</DataProperty>
{loc_property("m_feName", section_key, section, "section")}
</DataObject>
</DataProperty>
</DataObject>
</DataProperty>
<DataProperty Name="m_precacheList" Type="Object">
<DataValue Name="PrecacheList">{precache}</DataValue>
<DataObject Name="" Type="PrecacheList" Id="{precache}" OwnerId="{root}">
<DataProperty Name="m_precacheItems" Type="Object"/>
</DataObject>
</DataProperty>
<DataProperty Name="m_name" Type="String" Value="{MOD_NAME}"/>
<DataProperty Name="m_objectiveUnitTypes" Type="Object"/>
<DataProperty Name="m_devOnly" Type="Bool" Value="false"/>
<DataProperty Name="m_egroupNamePrefixDestroyList" Type="String"/>
<DataProperty Name="m_permittedInventoryItemCategories" Type="String"/>
<DataProperty Name="m_feImageUnselected" Type="String" Value="images\\illustrations\\create_game\\game_mode_standard_unselected"/>
</DataObject>
</DataWarehouse>
"""


def mod_rdo(name_key, description_key):
    root = stable_id("mod")
    return f"""<DataWarehouse>
<DataObject Name="{MOD_NAME}" Type="Mod" Id="{root}" Version="1">
{loc_property("m_description", description_key, root, "mod")}
{loc_property("m_name", name_key, root, "mod")}
</DataObject>
</DataWarehouse>
"""


def csv_field(text):
    return '"' + text.replace('"', '""') + '"' if ("," in text or '"' in text) else text


def write_text(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def write_locale(strings):
    english = ["﻿ID,Pipeline,PipelineStage,Notes,TranslationNotes,Tags,Text"]
    chinese = ["﻿ID,SourceText,TranslatedText"]
    for index, (en, zh) in enumerate(strings.rows, start=1):
        english.append(f"{index},,,,,,{csv_field(en)}")
        chinese.append(f"{index},{csv_field(en)},{csv_field(zh)}")
    write_text(LOCDB / f"{MOD_NAME}_en.csv", "\n".join(english) + "\n")
    write_text(LOCDB / f"{MOD_NAME}_zh-hans.csv", "\n".join(chinese) + "\n")
    write_text(LOCDB / f"{MOD_NAME}.locdb", """﻿<?xml version="1.0" encoding="utf-8"?>
<Metadata xmlns:i="http://www.w3.org/2001/XMLSchema-instance" xmlns="Localization">
	<CustomDictionary xmlns:d2p1="http://schemas.microsoft.com/2003/10/Serialization/Arrays" />
	<CustomFields />
	<Locales>
		<Locale>
			<DisplayName>English</DisplayName>
			<EngineName i:nil="true" />
			<Name>en</Name>
		</Locale>
		<Locale>
			<DisplayName>Chinese (Simplified)</DisplayName>
			<EngineName i:nil="true" />
			<Name>zh-Hans</Name>
		</Locale>
	</Locales>
	<Pipelines />
	<Scans />
	<StorageLocations>
		<StorageLocation>
			<DisplayName>Default</DisplayName>
			<RelativePath>.</RelativePath>
			<SerializeCustomFields>true</SerializeCustomFields>
		</StorageLocation>
	</StorageLocations>
	<Tags />
	<Version>2</Version>
</Metadata>
""")


def write_png(path, width=1920, height=1080):
    row = b"\x00" + bytes((58, 66, 74, 255)) * width
    raw = zlib.compress(row * height, 9)

    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data))

    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", raw) + chunk(b"IEND", b""))


def main():
    burnproj_template, template_name, template_guid = Path(sys.argv[1]), sys.argv[2], uuid.UUID(sys.argv[3])
    strings = Strings()
    name_key = strings.add(*TITLE)
    description_key = strings.add(*DESCRIPTION)
    write_text(WINCOND / f"{MOD_NAME}.rdo", win_condition_rdo(strings))
    write_text(ASSETS / "mod.rdo", mod_rdo(name_key, description_key))
    write_locale(strings)
    # The real thumbnail comes from tools/make_cover.py; this only covers a fresh checkout.
    if not (ASSETS / "mod.png").exists():
        write_png(ASSETS / "mod.png")
    write_text(ASSETS / "_default.burnproj", burnproj_template.read_text(encoding="utf-8").replace(template_name, MOD_NAME).replace(template_guid.hex, MOD_GUID.hex))
    write_text(ROOT / f"{MOD_NAME}.aoe4mod", f"""﻿<?xml version="1.0" encoding="utf-8"?>
<Mod xmlns:i="http://www.w3.org/2001/XMLSchema-instance" xmlns="http://schemas.datacontract.org/2004/07/Essence.Editor.Modding">
	<DataGenericPath>assets</DataGenericPath>
	<DataIntermediatePath>cache</DataIntermediatePath>
	<ID>{MOD_GUID}</ID>
	<LocDBPath>locdb\\{MOD_NAME}.locdb</LocDBPath>
	<Type>Extension</Type>
</Mod>
""")


if __name__ == "__main__":
    main()
