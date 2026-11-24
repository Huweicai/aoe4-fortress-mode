"""Draws the mod thumbnail (assets/mod.png) and the Mod Hub gallery images (publish/*.png).

Run with: python3 tools/make_cover.py  (needs Pillow and the macOS Hiragino Sans GB font)
"""
import math
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
WIDTH, HEIGHT = 1920, 1080
FONT_PATH = "/System/Library/Fonts/Hiragino Sans GB.ttc"
FONT_REGULAR, FONT_BOLD = 0, 1

SKY_TOP = (14, 18, 34)
SKY_HORIZON = (122, 52, 34)
STONE = (24, 24, 30)
STONE_EDGE = (58, 54, 60)
EMBER = (255, 138, 60)
GOLD = (236, 196, 120)
TEXT = (244, 236, 222)
MUTED = (186, 176, 164)
ENEMY = (120, 20, 18)


def font(size, weight=FONT_BOLD):
    return ImageFont.truetype(FONT_PATH, size, index=weight)


def vertical_gradient(top, bottom, horizon_y):
    image = Image.new("RGB", (WIDTH, HEIGHT))
    draw = ImageDraw.Draw(image)
    for y in range(HEIGHT):
        t = min(1.0, y / horizon_y) ** 1.6
        color = tuple(round(a + (b - a) * t) for a, b in zip(top, bottom))
        draw.line([(0, y), (WIDTH, y)], fill=color)
    return image


def add_glow(image, center, radius, color, strength):
    glow = Image.new("RGB", image.size, (0, 0, 0))
    ImageDraw.Draw(glow).ellipse([center[0] - radius, center[1] - radius, center[0] + radius, center[1] + radius], fill=color)
    glow = glow.filter(ImageFilter.GaussianBlur(radius / 2))
    return Image.blend(image, Image.composite(glow, image, glow.convert("L")), strength)


def draw_embers(draw, rng, count, area):
    for _ in range(count):
        x, y = rng.uniform(area[0], area[2]), rng.uniform(area[1], area[3])
        size = rng.uniform(1.5, 4.5)
        alpha = rng.randint(90, 230)
        draw.ellipse([x - size, y - size, x + size, y + size], fill=EMBER + (alpha,))


def crenellations(x0, x1, top, merlon, gap):
    points = []
    x = x0
    while x < x1:
        right = min(x + merlon, x1)
        points += [(x, top), (right, top), (right, top + merlon * 0.7)]
        x = right + gap
        points += [(min(x, x1), top + merlon * 0.7)]
    return points


def draw_fortress(draw, ground):
    wall_top = ground - 230
    # Curtain wall with merlons, running off the left edge.
    wall = [(-10, ground)] + [(-10, wall_top)] + crenellations(-10, 1010, wall_top - 40, 44, 30) + [(1010, wall_top), (1010, ground)]
    draw.polygon(wall, fill=STONE)
    # Towers.
    for left, width, height in ((80, 190, 380), (560, 210, 420), (930, 170, 340)):
        top = ground - height
        tower = [(left, ground), (left, top)] + crenellations(left, left + width, top - 46, 40, 26) + [(left + width, top), (left + width, ground)]
        draw.polygon(tower, fill=STONE)
        draw.line([(left, top), (left, ground)], fill=STONE_EDGE, width=3)
        for row in range(3):
            window_y = top + 60 + row * 95
            cx = left + width / 2
            draw.rounded_rectangle([cx - 13, window_y, cx + 13, window_y + 46], radius=12, fill=EMBER)
    # Banner.
    # On the left tower, clear of the title block.
    pole_x, pole_top = 175, ground - 500
    draw.line([(pole_x, ground - 380), (pole_x, pole_top)], fill=STONE, width=8)
    draw.polygon([(pole_x, pole_top), (pole_x + 120, pole_top + 30), (pole_x, pole_top + 62)], fill=GOLD)


def draw_army(draw, rng, ground):
    # Ranks of spears closing in from the right, smaller towards the horizon.
    for rank in range(9):
        depth = rank / 8
        y = ground - 40 - depth * 150
        scale = 1.0 - depth * 0.55
        spacing = 30 * scale
        x = 1180 + depth * 160
        while x < WIDTH + 40:
            body_height = 70 * scale
            draw.rectangle([x - 7 * scale, y - body_height, x + 7 * scale, y], fill=ENEMY)
            draw.ellipse([x - 9 * scale, y - body_height - 18 * scale, x + 9 * scale, y - body_height], fill=ENEMY)
            spear_x = x + 12 * scale
            draw.line([(spear_x, y - 10 * scale), (spear_x, y - body_height - 70 * scale)], fill=ENEMY, width=max(2, round(3 * scale)))
            draw.polygon([(spear_x - 5 * scale, y - body_height - 70 * scale), (spear_x + 5 * scale, y - body_height - 70 * scale), (spear_x, y - body_height - 92 * scale)], fill=(170, 40, 30))
            x += spacing + rng.uniform(0, 10 * scale)
    # A battering ram leading the charge.
    ram_x, ram_y = 1150, ground - 20
    draw.polygon([(ram_x, ram_y), (ram_x + 210, ram_y), (ram_x + 180, ram_y - 110), (ram_x + 30, ram_y - 110)], fill=(70, 18, 16))
    draw.rectangle([ram_x - 70, ram_y - 70, ram_x + 40, ram_y - 50], fill=(90, 24, 20))
    for wheel in (ram_x + 40, ram_x + 170):
        draw.ellipse([wheel - 26, ram_y - 26, wheel + 26, ram_y + 26], fill=(40, 12, 12))


def text_with_shadow(draw, position, text, text_font, fill, shadow=(0, 0, 0, 200), offset=4, anchor="la"):
    x, y = position
    draw.text((x + offset, y + offset), text, font=text_font, fill=shadow, anchor=anchor)
    draw.text((x, y), text, font=text_font, fill=fill, anchor=anchor)


def scene(seed=7):
    rng = random.Random(seed)
    ground = 930
    image = vertical_gradient(SKY_TOP, SKY_HORIZON, ground)
    image = add_glow(image, (1520, ground - 40), 520, (255, 110, 50), 0.55)
    image = add_glow(image, (640, ground - 200), 420, (255, 140, 70), 0.25)
    canvas = image.convert("RGBA")
    draw = ImageDraw.Draw(canvas, "RGBA")
    for _ in range(140):
        x, y = rng.uniform(0, WIDTH), rng.uniform(0, ground * 0.45)
        draw.point((x, y), fill=(255, 255, 255, rng.randint(60, 180)))
    draw_army(draw, rng, ground)
    draw.rectangle([0, ground, WIDTH, HEIGHT], fill=(16, 14, 18))
    draw_fortress(draw, ground)
    draw_embers(draw, rng, 160, (900, 300, WIDTH, ground))
    return canvas.convert("RGB")


def cover():
    canvas = scene().convert("RGBA")
    shade = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    ImageDraw.Draw(shade).rectangle([0, 0, WIDTH, 420], fill=(8, 8, 14, 170))
    canvas = Image.alpha_composite(canvas, shade.filter(ImageFilter.GaussianBlur(60))).convert("RGB")
    draw = ImageDraw.Draw(canvas, "RGBA")
    text_with_shadow(draw, (WIDTH / 2, 70), "堡垒模式", font(178), TEXT, anchor="ma")
    text_with_shadow(draw, (WIDTH / 2, 268), "F O R T R E S S   M O D E", font(54), GOLD, anchor="ma", offset=3)
    draw.line([(WIDTH / 2 - 330, 350), (WIDTH / 2 + 330, 350)], fill=GOLD + (180,), width=2)
    text_with_shadow(draw, (WIDTH / 2, 372), "守住城墙，扛住 AI 一波接一波的攻城", font(42, FONT_REGULAR), MUTED, anchor="ma", offset=2)
    text_with_shadow(draw, (WIDTH / 2, 428), "Hold the walls against endless AI siege waves", font(34, FONT_REGULAR), MUTED, anchor="ma", offset=2)
    return canvas


FEATURES = [
    ("坚城", "Stronger defenders",
     "玩家单位血量 ×2，城墙、箭塔、城堡 ×4", "Your units ×2 health; walls, towers and keeps ×4"),
    ("攻城波次", "Siege waves",
     "每波 100 步兵，冲车和手推炮一波比一波多", "100 infantry a wave, with more rams and bombards each time"),
    ("定期总攻", "All-out attacks",
     "每 2 分钟随机一家 AI 全军压上", "Every 2 minutes one AI sends its whole army"),
    ("更凶的 AI", "Fiercer AI",
     "AI 造兵 ×2，主城被攻破就不再出增援", "AI trains ×2 faster; no more waves once its capital falls"),
    ("更大的规模", "Bigger games",
     "人口 300 / AI 200，开局 16 村民，金矿石矿 ×2", "300 / 200 population, 16 villagers, ×2 gold and stone"),
    ("存活胜利", "Survival victory",
     "坚持 60 分钟即获胜；所有标准选项照常保留", "Survive 60 minutes to win; every standard option is kept"),
]


CARD_TEXT_WIDTH = 720


def fitted(draw, text, size, width):
    while size > 16 and draw.textlength(text, font=font(size, FONT_REGULAR)) > width:
        size -= 1
    return font(size, FONT_REGULAR)


def features_card():
    canvas = scene(seed=11).convert("RGBA")
    canvas = Image.alpha_composite(canvas, Image.new("RGBA", canvas.size, (6, 6, 12, 205))).convert("RGB")
    draw = ImageDraw.Draw(canvas, "RGBA")
    text_with_shadow(draw, (WIDTH / 2, 60), "堡垒模式  ·  Fortress Mode", font(76), TEXT, anchor="ma")
    text_with_shadow(draw, (WIDTH / 2, 160), "所有数值都可以在房间设置里调整  ·  Every value can be changed in the lobby", font(32, FONT_REGULAR), GOLD, anchor="ma", offset=2)
    column_x = (130, 1000)
    top, row_height = 260, 250
    for index, (title_cn, title_en, body_cn, body_en) in enumerate(FEATURES):
        x = column_x[index % 2]
        y = top + (index // 2) * row_height
        draw.rounded_rectangle([x, y, x + 790, y + 210], radius=18, fill=(255, 255, 255, 14), outline=GOLD + (90,), width=2)
        draw.rectangle([x, y + 24, x + 8, y + 186], fill=EMBER)
        draw.text((x + 40, y + 24), title_cn, font=font(46), fill=TEXT)
        draw.text((x + 40 + draw.textlength(title_cn, font=font(46)) + 24, y + 40), title_en, font=font(30), fill=GOLD)
        draw.text((x + 40, y + 100), body_cn, font=fitted(draw, body_cn, 30, CARD_TEXT_WIDTH), fill=TEXT)
        draw.text((x + 40, y + 148), body_en, font=fitted(draw, body_en, 26, CARD_TEXT_WIDTH), fill=MUTED)
    return canvas


def main():
    publish = ROOT / "publish"
    publish.mkdir(exist_ok=True)
    image = cover()
    image.save(ROOT / "assets" / "mod.png", optimize=True)
    image.save(publish / "cover.png", optimize=True)
    features_card().save(publish / "features.png", optimize=True)


if __name__ == "__main__":
    main()
