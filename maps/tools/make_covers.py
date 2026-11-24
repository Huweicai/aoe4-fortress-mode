"""Draws the Mod Hub cover and thumbnail of each map from its real layout.

Run: python3 maps/tools/make_covers.py <library dir>
The library dir is scar/terrainlayout/library extracted from Data.sga (tools/sga.py). Needs lua, Pillow and the macOS
Hiragino Sans GB font. Writes maps/<map>/publish/cover.png and maps/<map>/publish/mod.png.
"""
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[2]
WIDTH, HEIGHT = 1920, 1080
FONT_PATH = "/System/Library/Fonts/Hiragino Sans GB.ttc"
FONT_REGULAR, FONT_BOLD = 0, 1

BACKGROUND = (16, 18, 24)
TEXT = (244, 236, 222)
MUTED = (186, 176, 164)
GOLD = (236, 196, 120)
TERRAIN = {
    ".": (112, 138, 78),
    "h": (132, 150, 86),
    "T": (52, 84, 46),
    "#": (96, 86, 80),
    "~": (46, 92, 140),
    "G": (230, 190, 60),
    "S": (176, 176, 184),
}
DEFENDER = (80, 150, 255)
ATTACKER = (225, 60, 50)

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
    "fortress_pass": {
        "seed": 2,
        "title": "隘口要塞",
        "title_en": "FORTRESS  PASS",
        "tagline": "每人一座盆地、一个隘口，山脊小路互相支援",
        "tagline_en": "A walled basin and one narrow pass each, with a ridge path between",
        "points": [
            ("一人一口", "One pass each", "每座盆地只有一个窄口"),
            ("山脊小路", "Ridge path", "两座盆地之间有小路互通"),
            ("后方资源", "Safe resources", "盆地后方有额外的金矿和石矿"),
        ],
    },
}


def font(size, weight=FONT_BOLD):
    return ImageFont.truetype(FONT_PATH, size, index=weight)


def layout(map_name, library, seed):
    script = ROOT / "maps" / map_name / f"{map_name}.lua"
    preview = ROOT / "maps" / "tests" / "preview.lua"
    output = subprocess.run(["lua", str(preview), str(script), library, "640", TEAMS, str(seed)],
                            check=True, capture_output=True, text=True).stdout
    return [line for line in output.splitlines()[1:] if line]


def draw_layout(rows, size):
    cells = len(rows)
    scale = 8
    image = Image.new("RGB", (cells * scale, cells * scale))
    draw = ImageDraw.Draw(image)
    starts, resources = [], []
    for r, line in enumerate(rows):
        for c, char in enumerate(line):
            if char.isdigit():
                starts.append((r, c, char))
                char = "."
            elif char in "GS":
                resources.append((r, c, char))
                char = "."
            draw.rectangle([c * scale, r * scale, (c + 1) * scale, (r + 1) * scale], fill=TERRAIN.get(char, TERRAIN["."]))
    # Soften the coarse squares a little, as the game blends them too.
    image = image.filter(ImageFilter.GaussianBlur(1)).resize((size, size), Image.LANCZOS)
    draw = ImageDraw.Draw(image)
    cell = size / cells
    for r, c, kind in resources:
        x, y, radius = (c + 0.5) * cell, (r + 0.5) * cell, cell * 0.7
        draw.ellipse([x - radius, y - radius, x + radius, y + radius], fill=TERRAIN[kind], outline=(40, 34, 20), width=3)
    for r, c, player in starts:
        x, y = (c + 0.5) * cell, (r + 0.5) * cell
        color = DEFENDER if player in DEFENDERS else ATTACKER
        radius = cell * 1.6
        draw.ellipse([x - radius, y - radius, x + radius, y + radius], fill=color, outline=(255, 255, 255), width=4)
        draw.text((x, y), "守" if player in DEFENDERS else "攻", font=font(int(radius * 0.9)), fill=(255, 255, 255), anchor="mm")
    return image


def cover(map_name, info, rows):
    canvas = Image.new("RGB", (WIDTH, HEIGHT), BACKGROUND)
    map_size = 920
    map_image = draw_layout(rows, map_size)
    shadow = Image.new("RGBA", (map_size + 80, map_size + 80), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle([40, 40, map_size + 40, map_size + 40], radius=24, fill=(0, 0, 0, 200))
    canvas.paste(shadow.filter(ImageFilter.GaussianBlur(24)), (40, 40), shadow.filter(ImageFilter.GaussianBlur(24)))
    mask = Image.new("L", (map_size, map_size), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, map_size, map_size], radius=24, fill=255)
    canvas.paste(map_image, (80, 80), mask)

    draw = ImageDraw.Draw(canvas)
    x = 1080
    draw.text((x, 120), info["title"], font=font(120), fill=TEXT)
    draw.text((x + 4, 270), info["title_en"], font=font(46), fill=GOLD)
    draw.line([(x, 345), (x + 720, 345)], fill=GOLD, width=2)
    draw.text((x, 372), info["tagline"], font=font(34, FONT_REGULAR), fill=TEXT)
    draw.text((x, 424), info["tagline_en"], font=fitted(draw, info["tagline_en"], 26, 760), fill=MUTED)
    y = 520
    for title, title_en, body in info["points"]:
        draw.rectangle([x, y + 6, x + 8, y + 86], fill=GOLD)
        draw.text((x + 32, y), title, font=font(40), fill=TEXT)
        draw.text((x + 32 + draw.textlength(title, font=font(40)) + 20, y + 12), title_en, font=font(26), fill=GOLD)
        draw.text((x + 32, y + 56), body, font=font(28, FONT_REGULAR), fill=MUTED)
        y += 120
    legend = ((DEFENDER, "守方 Defenders"), (ATTACKER, "攻方 Attackers"), (TERRAIN["~"], "深水 Deep water"),
              (TERRAIN["#"], "山 Cliffs"), (TERRAIN["G"], "金矿 Gold"), (TERRAIN["S"], "石矿 Stone"))
    present = set("".join(rows))
    legend = [item for item in legend if item[0] not in (TERRAIN["~"], TERRAIN["#"]) or
              (item[0] == TERRAIN["~"] and "~" in present) or (item[0] == TERRAIN["#"] and "#" in present)]
    for index, (color, label) in enumerate(legend):
        lx, ly = 1080 + (index % 3) * 260, 880 + (index // 3) * 44
        draw.ellipse([lx, ly, lx + 26, ly + 26], fill=color)
        draw.text((lx + 38, ly + 13), label, font=font(22, FONT_REGULAR), fill=MUTED, anchor="lm")
    draw.text((1080, 990), "为《堡垒模式》设计 · Made for Fortress Mode", font=font(24, FONT_REGULAR), fill=MUTED)
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


if __name__ == "__main__":
    main()
