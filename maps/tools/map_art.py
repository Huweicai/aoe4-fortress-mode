"""Draws a map layout in the style of the game's own map icons: gold line art on a dark navy cloth.

The layout is the ASCII grid printed by maps/tests/preview.lua:
  . plains   h hills   T forest   # cliffs   ~ deep water   , plateau   G gold   S stone   digits player starts
"""
import math
import random

import numpy as np

from PIL import Image, ImageChops, ImageDraw, ImageFilter

NAVY = (14, 22, 40)
NAVY_LIGHT = (24, 36, 62)
GOLD = (222, 178, 92)
GOLD_DARK = (150, 112, 52)
WATER = (36, 78, 128)
WATER_DEEP = (22, 50, 92)
STONE = (168, 170, 176)
DEFENDER = (92, 170, 255)
ATTACKER = (232, 72, 60)

# Drawn this many times larger, then scaled down, for smooth lines.
SUPERSAMPLE = 3


def _cloth(size, rng):
    """Dark navy with a woven texture and a soft vignette."""
    base = Image.new("RGB", (size, size), NAVY)
    noise = Image.effect_noise((size, size), 18).convert("L")
    weave = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(weave)
    step = max(3, size // 220)
    for x in range(0, size, step):
        draw.line([(x, 0), (x, size)], fill=10)
    for y in range(0, size, step):
        draw.line([(0, y), (size, y)], fill=10)
    texture = ImageChops.add(noise.point(lambda v: v // 6), weave)
    lighter = Image.new("RGB", (size, size), NAVY_LIGHT)
    base = Image.composite(lighter, base, texture.point(lambda v: min(255, v * 4)))
    vignette = Image.new("L", (size, size), 0)
    ImageDraw.Draw(vignette).ellipse([-size * 0.2, -size * 0.2, size * 1.2, size * 1.2], fill=255)
    vignette = vignette.filter(ImageFilter.GaussianBlur(size // 8))
    dark = Image.new("RGB", (size, size), (6, 10, 20))
    base = Image.composite(base, dark, vignette)
    # The faint survey lines across every official icon.
    draw = ImageDraw.Draw(base, "RGBA")
    for _ in range(5):
        x0, x1 = rng.uniform(-0.2, 1.2) * size, rng.uniform(-0.2, 1.2) * size
        draw.line([(x0, 0), (x1, size)], fill=GOLD + (34,), width=max(1, size // 900))
    return base


def _mask(rows, chars, size, smooth):
    cells = len(rows)
    cell = size / cells
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    for r, line in enumerate(rows):
        for c, char in enumerate(line):
            if char in chars:
                draw.rectangle([c * cell - 1, r * cell - 1, (c + 1) * cell + 1, (r + 1) * cell + 1], fill=255)
    if smooth:
        mask = mask.filter(ImageFilter.GaussianBlur(cell * smooth)).point(lambda v: 255 if v > 128 else 0)
    return mask


def _organic(mask, cell, rng, wobble=0.9):
    """Wobbles the edges of a blocky mask so shores look drawn by hand."""
    size = mask.size[0]
    # Low-frequency noise: random values on a coarse grid, smoothly scaled up.
    coarse = max(4, int(size / cell / 1.5))
    grid = np.array([[rng.random() for _ in range(coarse)] for _ in range(coarse)]) * 255
    noise = np.asarray(Image.fromarray(grid.astype(np.uint8)).resize((size, size), Image.BICUBIC), float)
    noise = (noise - noise.mean()) / (noise.std() + 1e-6)
    soft = np.asarray(mask.filter(ImageFilter.GaussianBlur(cell * 0.45)), float) / 255
    return Image.fromarray(((soft + noise * 0.1 * wobble) > 0.5).astype(np.uint8) * 255)


def _outline(mask, width):
    grown = mask.filter(ImageFilter.MaxFilter(width | 1))
    return ImageChops.subtract(grown, mask)


def _cells(rows, chars):
    for r, line in enumerate(rows):
        for c, char in enumerate(line):
            if char in chars:
                yield r, c


def _gold_layer(image, mask, colour=GOLD, alpha=255):
    layer = Image.new("RGB", image.size, colour)
    image.paste(layer, (0, 0), mask.point(lambda v: v * alpha // 255))


def _water(image, rows, cell, rng):
    mask = _mask(rows, "~sf", image.size[0], 0)
    if not mask.getbbox():
        return
    mask = _organic(mask, cell, rng)
    depth = mask.filter(ImageFilter.GaussianBlur(cell * 1.2))
    water = Image.composite(Image.new("RGB", image.size, WATER_DEEP), Image.new("RGB", image.size, WATER), depth)
    image.paste(water, (0, 0), mask)
    # A thick gold shore and a thin line a little way out, as on the official lake icons.
    _gold_layer(image, _outline(mask, int(cell * 0.32)))
    ring = _outline(mask.filter(ImageFilter.MaxFilter(int(cell * 0.6) | 1)), max(3, int(cell * 0.08)))
    _gold_layer(image, ring, alpha=120)
    draw = ImageDraw.Draw(image, "RGBA")
    for r, c in _cells(rows, "~sf"):
        if rng.random() < 0.18:
            x, y = (c + rng.random()) * cell, (r + rng.random()) * cell
            for k in range(3):
                yy = y + k * cell * 0.16
                points = [(x + t * cell * 0.12, yy + math.sin(t * 1.6) * cell * 0.05) for t in range(6)]
                draw.line(points, fill=GOLD + (110,), width=max(2, int(cell * 0.04)))


def _fish(image, rows, cell):
    draw = ImageDraw.Draw(image)
    line = max(2, int(cell * 0.06))
    for r, c in _cells(rows, "f"):
        x, y = (c + 0.5) * cell, (r + 0.5) * cell
        draw.ellipse([x - cell * 0.35, y - cell * 0.15, x + cell * 0.2, y + cell * 0.15], outline=GOLD, width=line)
        draw.polygon([(x + cell * 0.2, y), (x + cell * 0.45, y - cell * 0.18), (x + cell * 0.45, y + cell * 0.18)], outline=GOLD)


def _peak(draw, x, y, height, width, line):
    left, top, right = (x - width / 2, y), (x, y - height), (x + width / 2, y)
    draw.line([left, top, right], fill=GOLD, width=line, joint="curve")
    # Hatching on the shaded side.
    for k in range(1, 5):
        t = k / 5
        sx, sy = x + width / 2 * t, y - height * (1 - t)
        draw.line([(sx, sy), (sx - width * 0.18, sy + height * 0.22)], fill=GOLD_DARK, width=max(1, line // 2))


def _mountains(image, rows, cell, rng):
    """Overlapping hand-drawn peaks, back rows first so the front ones hide them."""
    draw = ImageDraw.Draw(image)
    line = max(3, int(cell * 0.09))
    peaks = []
    for r, c in _cells(rows, "#"):
        for _ in range(2):
            if rng.random() < 0.6:
                peaks.append(((r + rng.uniform(0.5, 1.1)) * cell, (c + rng.uniform(0.1, 0.9)) * cell))
    for y, x in sorted(peaks):
        height, width = cell * rng.uniform(1.0, 1.6), cell * rng.uniform(0.9, 1.3)
        draw.polygon([(x - width / 2, y), (x, y - height), (x + width / 2, y)], fill=NAVY)
        _peak(draw, x, y, height, width, line)


def _plateau(image, rows, cell):
    mask = _mask(rows, ",GSH0123456789", image.size[0], 0.2)
    rim = _mask(rows, "#h", image.size[0], 0.0)
    plateau_area = ImageChops.multiply(mask, ImageChops.invert(rim))
    if not _mask(rows, ",", image.size[0], 0).getbbox():
        return
    lighter = Image.new("RGB", image.size, NAVY_LIGHT)
    image.paste(lighter, (0, 0), plateau_area.point(lambda v: v * 120 // 255))


def _hills(image, rows, cell, rng):
    draw = ImageDraw.Draw(image)
    line = max(2, int(cell * 0.05))
    for r, c in _cells(rows, "h"):
        x, y = (c + 0.5) * cell, (r + 0.6) * cell
        w = cell * rng.uniform(0.7, 1.0)
        draw.arc([x - w / 2, y - cell * 0.35, x + w / 2, y + cell * 0.35], 200, 340, fill=GOLD, width=line)
        for k in range(3):
            hx = x + w * (0.05 + k * 0.1)
            draw.line([(hx, y - cell * 0.08), (hx + cell * 0.08, y + cell * 0.06)], fill=GOLD_DARK, width=max(1, line // 2))


def _trees(image, rows, cell, rng):
    draw = ImageDraw.Draw(image)
    line = max(3, int(cell * 0.07))
    for r, c in _cells(rows, "T"):
        x, y = (c + rng.uniform(0.25, 0.75)) * cell, (r + rng.uniform(0.25, 0.75)) * cell
        radius = cell * rng.uniform(0.32, 0.46)
        draw.ellipse([x - radius, y - radius * 1.2, x + radius, y + radius * 0.4], outline=GOLD, width=line)
        draw.line([(x, y + radius * 0.4), (x, y + radius * 1.2)], fill=GOLD, width=line)


def _grass(image, rows, cell, rng):
    draw = ImageDraw.Draw(image, "RGBA")
    line = max(1, int(cell * 0.035))
    for r, c in _cells(rows, ".,"):
        if rng.random() < 0.08:
            x, y = (c + rng.random()) * cell, (r + rng.random()) * cell
            for dx in (-0.08, 0, 0.08):
                draw.line([(x + dx * cell, y), (x + dx * cell * 1.6, y - cell * 0.12)], fill=GOLD + (150,), width=line)


def _gold(draw, x, y, cell):
    """Three stacked gold bars, as on the official icons."""
    bar_w, bar_h = cell * 0.42, cell * 0.22
    for bx, by in ((-0.5, 0), (0.5, 0), (0, -1)):
        cx, cy = x + bx * bar_w * 1.02, y + by * bar_h * 1.05
        poly = [(cx - bar_w / 2, cy + bar_h / 2), (cx + bar_w / 2, cy + bar_h / 2),
                (cx + bar_w * 0.35, cy - bar_h / 2), (cx - bar_w * 0.35, cy - bar_h / 2)]
        draw.polygon(poly, fill=(236, 186, 60), outline=(120, 84, 20))


def _shrine(draw, x, y, cell):
    """A sacred site: a stepped gold platform with a pole and pennant, as on the official icons."""
    line = max(2, int(cell * 0.07))
    w = cell * 1.1
    for k, width in enumerate((1.0, 0.75, 0.5)):
        top = y + cell * 0.3 - k * cell * 0.18
        draw.rectangle([x - w * width / 2, top - cell * 0.16, x + w * width / 2, top], outline=GOLD, width=line)
    pole_top = y - cell * 1.1
    draw.line([(x, y - cell * 0.24), (x, pole_top)], fill=GOLD, width=line)
    draw.polygon([(x, pole_top), (x + cell * 0.45, pole_top + cell * 0.14), (x, pole_top + cell * 0.28)], fill=GOLD)
    for angle in range(0, 360, 45):
        dx, dy = math.cos(math.radians(angle)), math.sin(math.radians(angle))
        draw.line([(x + dx * cell * 0.25, pole_top - cell * 0.1 + dy * cell * 0.25),
                   (x + dx * cell * 0.42, pole_top - cell * 0.1 + dy * cell * 0.42)], fill=GOLD, width=max(1, line // 2))


def _stone(draw, x, y, cell):
    r = cell * 0.42
    blob = [(x - r, y + r * 0.4), (x - r * 0.7, y - r * 0.3), (x - r * 0.1, y - r * 0.7), (x + r * 0.6, y - r * 0.45),
            (x + r, y + r * 0.2), (x + r * 0.5, y + r * 0.55), (x - r * 0.4, y + r * 0.6)]
    draw.polygon(blob, fill=STONE, outline=(90, 92, 100))
    draw.line([(x - r * 0.2, y - r * 0.2), (x + r * 0.3, y + r * 0.1)], fill=(120, 122, 130), width=max(1, int(cell * 0.05)))


def _keep(draw, x, y, cell, colour):
    """A small gold keep with a coloured banner: the colour tells defenders from attackers."""
    w, h = cell * 1.1, cell * 0.8
    line = max(2, int(cell * 0.07))
    base = [x - w / 2, y - h / 2, x + w / 2, y + h / 2]
    draw.rectangle(base, fill=NAVY, outline=GOLD, width=line)
    for k in range(4):
        mx = x - w / 2 + k * w / 3.0
        draw.rectangle([mx - w * 0.08, y - h / 2 - h * 0.22, mx + w * 0.08, y - h / 2], fill=GOLD)
    draw.rectangle([x - w * 0.12, y, x + w * 0.12, y + h / 2], fill=GOLD)
    pole = x + w * 0.05
    draw.line([(pole, y - h / 2), (pole, y - h * 1.55)], fill=GOLD, width=line)
    draw.polygon([(pole, y - h * 1.55), (pole + w * 0.6, y - h * 1.35), (pole, y - h * 1.15)], fill=colour, outline=GOLD)


def draw_map(rows, size, defenders, seed=7):
    """Returns a square RGB image of the layout, size pixels wide."""
    rng = random.Random(seed)
    big = size * SUPERSAMPLE
    cell = big / len(rows)
    image = _cloth(big, rng)
    _plateau(image, rows, cell)
    _grass(image, rows, cell, rng)
    _water(image, rows, cell, rng)
    _mountains(image, rows, cell, rng)
    _fish(image, rows, cell)
    _hills(image, rows, cell, rng)
    _trees(image, rows, cell, rng)
    draw = ImageDraw.Draw(image)
    for r, c in _cells(rows, "G"):
        _gold(draw, (c + 0.5) * cell, (r + 0.6) * cell, cell * 1.6)
    for r, c in _cells(rows, "S"):
        _stone(draw, (c + 0.5) * cell, (r + 0.5) * cell, cell * 1.6)
    for r, c in _cells(rows, "H"):
        _shrine(draw, (c + 0.5) * cell, (r + 0.5) * cell, cell * 1.6)
    for r, c in _cells(rows, "0123456789"):
        colour = DEFENDER if rows[r][c] in defenders else ATTACKER
        _keep(draw, (c + 0.5) * cell, (r + 0.5) * cell, cell * 1.7, colour)
    return image.resize((size, size), Image.LANCZOS)
