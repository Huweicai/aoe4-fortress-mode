"""Fills a Generated Map project made in the Content Editor with this repo's layout script, lobby texts and cover.

Run: python3 maps/tools/install_project.py <map>   e.g. fortress_bridge
The editor project must exist on the Windows machine as Documents\\<map> (New Mod > Generated Map > Basic).
The first run copies the editor's project files into maps/<map>/ and moves the layout script to where the editor
wants it; every run then writes the lobby texts and pushes the script, texts and cover back.
"""
import csv
import io
import re
import subprocess
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HOST = ["-o", "HostKeyAlias=192.168.31.208"]
REMOTE = "tion@192.168.31.87"

# The name shown in the lobby and the Mod Hub; written here rather than taken from the editor, where it is typed by hand.
TITLES = {
    "fortress_h": "H 型要塞 · Fortress H",
    "fortress_bridge": "长桥要塞 · Fortress Bridge",
    "fortress_hill": "山顶要塞 · Fortress Hill",
    "fortress_pass": "隘口要塞 · Fortress Pass",
}
# Tags under the map in the lobby, from map_gen\map_gen_ui_characteristic, as the official maps use them.
CHARACTERISTICS = {
    "fortress_h": ["choke_point", "limited_naval", "more_gold", "more_stone"],
    "fortress_bridge": ["choke_point", "lanes", "limited_naval"],
    "fortress_hill": ["choke_point", "limited_naval", "more_gold", "more_stone"],
    "fortress_pass": ["choke_point", "limited_naval", "more_gold", "more_stone"],
}
PLAYSTYLE_TAGS = ["casual"]
# Mod description, two lobby notes and the lobby description, each in Chinese then English.
TEXTS = {
    "fortress_h": (
        "背靠背守住 H 的横梁：上下是深湖，左右各一座陆桥，AI 从两侧压上来。为《堡垒模式》设计，也可当普通团队图。 / Hold the crossbar of an H back to back: deep lakes above and below, one land bridge at each end, attackers from both sides. Made for Fortress Mode; works as any team game.",
        "人少的一队守横梁，人多的一队从两侧进攻 / The smaller team holds the crossbar; the larger one attacks from both sides",
        "真人放同一队，AI 放另一队 / Put humans on one team and AIs on the other",
        "背靠背守住 H 的横梁。横梁上下是深湖，可以捕鱼，左右各有一座陆桥。攻方分在左右两条竖边，同时压过来。 / Hold the crossbar of an H back to back. Deep lakes above and below are good for fishing, and each end has one land bridge. The attackers are split between the two uprights and come from both sides.",
    ),
    "fortress_bridge": (
        "两队各守一岸，中间只有一座窄长的陆桥，两侧全是深水。为《堡垒模式》设计，也可当普通团队图。 / Two teams on opposite shores, joined only by one long, narrow land bridge with deep water on both sides. Made for Fortress Mode; works as any team game.",
        "1 号位所在的队伍在左岸，其他队伍在右岸 / The first player's team takes the left shore, everyone else the right",
        "真人放同一队并占 1 号位，AI 放另一队 / Put humans on one team, with you in slot 1, and AIs on the other",
        "两边各守一岸，中间只有一座约 48 米宽的陆桥，两侧是深水，停在一侧的战舰能打到大半座桥。两岸都有浅滩和鱼群。 / One shore each and a single land bridge about 48 m wide between, with deep water on both sides; a warship on one side covers most of it. Both shores have shallows and fish.",
    ),
    "fortress_hill": (
        "大家一起守护城河围着的中央小山，每位守方一对相邻的陆桥。为《堡垒模式》设计，也可当普通团队图。 / Hold the moated hill in the middle together, with a pair of close land bridges for each defender. Made for Fortress Mode; works as any team game.",
        "人少的一队守中央小山，人多的一队从四周进攻 / The smaller team holds the hill; the larger one attacks from all around",
        "真人放同一队，AI 放另一队 / Put humans on one team and AIs on the other",
        "守方聚在中央一座平缓的小山上，四周是护城河，每人一对相邻的陆桥。攻方分布在地图四角。 / The defenders start together on a gentle hill ringed by a moat, with a pair of close land bridges each. The attackers start in the corners.",
    ),
    "fortress_pass": (
        "每人一座护城河围着的盆地和一座陆桥，盆地之间有小桥互通。为《堡垒模式》设计，也可当普通团队图。 / A moated basin and one land bridge for each defender, with small bridges between basins. Made for Fortress Mode; works as any team game.",
        "人少的一队守北边的盆地，人多的一队从南边进攻 / The smaller team holds the basins in the north; the larger one attacks from the south",
        "真人放同一队，AI 放另一队 / Put humans on one team and AIs on the other",
        "守方每人一座被护城河围住的盆地，只有一座陆桥通向外面，盆地之间有小桥。攻方在南边的开阔地上。 / Each defender holds a basin ringed by a moat with a single land bridge out, and small bridges link the basins. The attackers start on the open plain to the south.",
    ),
}
PROJECT_FILES = ["{m}.aoe4mod", "assets/mod.rdo", "assets/_default.burnproj", "assets/attrib/{m}.xml",
                 "assets/attrib/instances/map_gen/map_gen_layout/{m}.xml", "assets/locdb/{m}_en.csv"]


def scp(source, target):
    subprocess.run(["scp", "-q", *HOST, source, target], check=True)


def fetch_project(name, project):
    for pattern in PROJECT_FILES:
        rel = pattern.format(m=name)
        local = project / rel
        if not local.exists():
            local.parent.mkdir(parents=True, exist_ok=True)
            scp(f"{REMOTE}:Documents/{name}/{rel}", str(local))
    script = project / "assets" / "scar" / "terrainlayout" / f"{name}.lua"
    if not script.exists():
        script.parent.mkdir(parents=True, exist_ok=True)
        (project / f"{name}.lua").rename(script)


def mod_guid(project, name):
    text = (project / "assets" / "attrib" / f"{name}.xml").read_text(encoding="utf-8-sig")
    return text.split('guid="', 1)[1].split('"', 1)[0]


def write_texts(project, name, guid):
    title = TITLES[name]
    description, note1, note2, long_text = TEXTS[name]
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\r\n")
    writer.writerow(["ID", "Pipeline", "PipelineStage", "Notes", "TranslationNotes", "Tags", "Text"])
    for row in (("1", "Mod name.", title), ("2", "Mod description.", description), ("3", "Map name.", title),
                ("4", "Lobby note.", note1), ("5", "Lobby note.", note2), ("6", "Lobby description.", long_text)):
        writer.writerow([row[0], "", "", row[1], "", "", row[2]])
    with open(project / "assets" / "locdb" / f"{name}_en.csv", "w", encoding="utf-8-sig", newline="") as target:
        target.write(out.getvalue())

    layout = project / "assets" / "attrib" / "instances" / "map_gen" / "map_gen_layout" / f"{name}.xml"
    with open(layout, encoding="utf-8", newline="") as source:
        text = source.read()
    # The template's own notes and description, wherever the editor put other attributes on the tag.
    for tag, old, key in (("note", "11166241", 4), ("note", "11166242", 5), ("display_description_long", "11183792", 6)):
        text = re.sub(rf'<locstring name="{tag}" value="{old}"', f'<locstring name="{tag}" value="{key}" mod="{guid}"', text)
    newline = "\r\n" if "\r\n" in text else "\n"

    def fill(list_name, item_name, tags):
        items = "".join(
            f'\t\t\t\t<instance_reference name="{item_name}" value="map_gen\\map_gen_ui_characteristic\\{tag}" '
            f'List.ItemID="{zlib.crc32(f"{name}/{list_name}/{tag}".encode()) - 2**31}" />{newline}' for tag in tags)
        return re.sub(rf'(<list name="{list_name}">){re.escape(newline)}.*?(\t\t\t</list>)',
                      lambda m: m.group(1) + newline + items + m.group(2), text, count=1, flags=re.S)

    text = fill("characteristics", "characteristic", CHARACTERISTICS[name])
    text = fill("playstyle_tags", "playstyle_tags", PLAYSTYLE_TAGS)
    # The lobby icon: our own instead of the template's wrench. The editor burns ui\images into game textures.
    text = text.replace('value="map_gen_layout\\default_mod_icon"', f'value="map_gen_layout\\{name}_icon"')
    with open(layout, "w", encoding="utf-8", newline="") as target:
        target.write(text)


def push(project, name):
    pairs = [(f"assets/scar/terrainlayout/{name}.lua", f"assets/scar/terrainlayout/"),
             (f"assets/locdb/{name}_en.csv", "assets/locdb/"),
             (f"assets/attrib/instances/map_gen/map_gen_layout/{name}.xml", "assets/attrib/instances/map_gen/map_gen_layout/"),
             ("assets/mod.png", "assets/"),
             (f"assets/ui/images/map_gen_layout/{name}_icon.png", "assets/ui/images/map_gen_layout/")]
    subprocess.run(["ssh", *HOST, REMOTE, f"mkdir Documents\\{name}\\assets\\ui\\images\\map_gen_layout"],
                   capture_output=True)
    for local, remote_dir in pairs:
        scp(str(project / local), f"{REMOTE}:Documents/{name}/{remote_dir}")


def main():
    name = sys.argv[1]
    project = ROOT / "maps" / name
    fetch_project(name, project)
    write_texts(project, name, mod_guid(project, name))
    (project / "assets" / "mod.png").write_bytes((project / "publish" / "mod.png").read_bytes())
    icon = project / "assets" / "ui" / "images" / "map_gen_layout" / f"{name}_icon.png"
    icon.parent.mkdir(parents=True, exist_ok=True)
    icon.write_bytes((project / "publish" / "icon.png").read_bytes())
    push(project, name)
    print(f"{name}: installed")


if __name__ == "__main__":
    main()
