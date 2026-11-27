"""Draws the Mod Hub cover and thumbnail of each map from its real layout.

Run: python3 maps/tools/make_covers.py <library dir>
The library dir is scar/terrainlayout/library extracted from Data.sga (tools/sga.py). Needs lua, Pillow and the macOS
Hiragino Sans GB font. Writes maps/<map>/publish/cover.png and maps/<map>/publish/mod.png.
"""
import random
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import map_art

ROOT = Path(__file__).resolve().parents[2]
GOLD = map_art.GOLD
WIDTH, HEIGHT = 1920, 1080
FONT_PATH = "/System/Library/Fonts/Hiragino Sans GB.ttc"
FONT_REGULAR, FONT_BOLD = 0, 1

TEXT = (244, 236, 222)
MUTED = (176, 170, 158)

# Each map is drawn for the match it is made for: two defenders against four attackers.
TEAMS = "1,1,2,2,2,2"
DEFENDERS = {"1", "2"}
MAPS = {
    "fortress_h": {
        "seed": 4,
        "title": "H 型要塞",
        "title_en": "FORTRESS  H",
        "tagline": "背靠背守住 H 的横梁，AI 从两侧压上来",
        "tagline_en": "Hold the crossbar back to back while the AI comes from both sides",
        "points": [
            ("两个窄口", "Two narrow necks", "左右各一个，一人守一边"),
            ("湖泊环绕", "Lakes all round", "横梁上下都是深湖，可以捕鱼"),
            ("资源充足", "Rich crossbar", "两端各有额外的金矿和石矿"),
        ],
    },
    "fortress_bridge": {
        "seed": 3,
        "title": "长桥要塞",
        "title_en": "FORTRESS  BRIDGE",
        "tagline": "两边各守一岸，中间只有一座窄长的陆桥",
        "tagline_en": "One shore each, and a single long, narrow land bridge between",
        "points": [
            ("唯一通道", "One way across", "32 米宽的陆桥，战舰能从侧面轰到整座桥"),
            ("隔岸对峙", "Face to face", "两队分在左右两岸"),
            ("湖里有鱼", "Fishing", "两岸都有浅滩和鱼群"),
        ],
    },
    "fortress_hill": {
        "seed": 5,
        "title": "山顶要塞",
        "title_en": "FORTRESS  HILL",
        "tagline": "大家一起守中央小山，每人两座相邻的陆桥",
        "tagline_en": "Hold the moated hill together, two close bridges for each defender",
        "points": [
            ("一人两口", "Two bridges each", "每位守方一对相邻的陆桥"),
            ("聚在一起", "Together", "守方出生点都在小山中央"),
            ("四面来敌", "Attacked from all sides", "攻方分布在地图四周"),
        ],
    },
    "fortress_pass": {
        "seed": 2,
        "title": "隘口要塞",
        "title_en": "FORTRESS  PASS",
        "tagline": "每人一座盆地、一座陆桥，水道小桥互相支援",
        "tagline_en": "A moated basin and one land bridge each, with a small bridge between",
        "points": [
            ("一人一桥", "One bridge each", "每座盆地只有一座陆桥"),
            ("水道小桥", "Linked basins", "两座盆地之间有小桥互通"),
            ("后方资源", "Safe resources", "盆地后方有额外的金矿和石矿"),
        ],
    },
}


def font(size, weight=FONT_BOLD):
    return ImageFont.truetype(FONT_PATH, size, index=weight)


def layout(map_name, library, seed):
    # Maps that already have their editor project keep the script where the editor wants it.
    script = ROOT / "maps" / map_name / "assets" / "scar" / "terrainlayout" / f"{map_name}.lua"
    if not script.exists():
        script = ROOT / "maps" / map_name / f"{map_name}.lua"
    preview = ROOT / "maps" / "tests" / "preview.lua"
    output = subprocess.run(["lua", str(preview), str(script), library, "640", TEAMS, str(seed)],
                            check=True, capture_output=True, text=True).stdout
    return [line for line in output.splitlines()[1:] if line]


def cover(map_name, info, rows):
    """The map in the game's own icon style on the left, the pitch on the right, all in navy and gold."""
    canvas = map_art._cloth(WIDTH, random.Random(1)).crop((0, 0, WIDTH, HEIGHT))
    map_size = 920
    map_image = map_art.draw_map(rows, map_size, DEFENDERS)
    frame = ImageDraw.Draw(canvas)
    frame.rectangle([66, 66, 80 + map_size + 14, 80 + map_size + 14], outline=GOLD, width=3)
    canvas.paste(map_image, (80, 80))

    draw = ImageDraw.Draw(canvas)
    x = 1080
    draw.text((x, 120), info["title"], font=font(120), fill=TEXT)
    draw.text((x + 4, 270), info["title_en"], font=font(46), fill=GOLD)
    draw.line([(x, 345), (x + 720, 345)], fill=GOLD, width=2)
    draw.text((x, 372), info["tagline"], font=font(34, FONT_REGULAR), fill=TEXT)
    draw.text((x, 424), info["tagline_en"], font=fitted(draw, info["tagline_en"], 26, 760), fill=MUTED)
    y = 520
    for title, title_en, body in info["points"]:
        draw.rectangle([x, y + 6, x + 6, y + 86], fill=GOLD)
        draw.text((x + 32, y), title, font=font(40), fill=TEXT)
        draw.text((x + 32 + draw.textlength(title, font=font(40)) + 20, y + 12), title_en, font=font(26), fill=GOLD)
        draw.text((x + 32, y + 56), body, font=font(28, FONT_REGULAR), fill=MUTED)
        y += 120
    for index, (colour, label) in enumerate(((map_art.DEFENDER, "守方 Defenders"), (map_art.ATTACKER, "攻方 Attackers"))):
        lx = 1080 + index * 300
        draw.polygon([(lx, 890), (lx + 30, 900), (lx, 910)], fill=colour, outline=GOLD)
        draw.line([(lx, 884), (lx, 922)], fill=GOLD, width=3)
        draw.text((lx + 44, 902), label, font=font(24, FONT_REGULAR), fill=MUTED, anchor="lm")
    draw.text((1080, 980), "为《堡垒模式》设计 · Made for Fortress Mode", font=font(24, FONT_REGULAR), fill=MUTED)
    return canvas


def fitted(draw, text, size, width):
    while size > 14 and draw.textlength(text, font=font(size, FONT_REGULAR)) > width:
        size -= 1
    return font(size, FONT_REGULAR)


def main():
    library = sys.argv[1]
    for map_name, info in MAPS.items():
        rows = layout(map_name, library, info["seed"])
        publish = ROOT / "maps" / map_name / "publish"
        publish.mkdir(exist_ok=True)
        image = cover(map_name, info, rows)
        image.save(publish / "cover.png", optimize=True)
        image.save(publish / "mod.png", optimize=True)
        map_art.draw_map(rows, 512, DEFENDERS).save(publish / "icon.png", optimize=True)


if __name__ == "__main__":
    main()
