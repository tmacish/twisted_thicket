#!/usr/bin/env python3
"""
Generate progressive reveal versions of the player map.
Each stage reveals one additional area. Print and swap at the table.

Output: images/reveal/
    stage_00_start.png        -- southern road only, thicket covered
    stage_01_area1.png        -- + Forest Edge Road (entrance)
    stage_02_area2.png        -- + Ravine Wagon Wreck
    stage_03_area3.png        -- + Logging Camp
    stage_04_area4.png        -- + Dust Pool Glade
    stage_05_area5.png        -- + Thorn-Choked Hollow
    stage_06_area6.png        -- + Game Trails
    stage_07_area7.png        -- + Riddle Cave (full map)
"""

import os
from PIL import Image, ImageDraw, ImageFilter

MAP_PATH = os.path.join(os.path.dirname(__file__), "..", "images", "new_player_map_2400.png")
OUT_DIR  = os.path.join(os.path.dirname(__file__), "..", "images", "reveal")

W, H = 2400, 1920

# Overlay colour: near-black with faint warm tint so it reads as shadow, not void.
# Fully opaque for clean printing.
SHADOW = (12, 8, 5, 255)


def ellipse_points(cx, cy, rx, ry, steps=64):
    """Return a polygon approximating an ellipse, for organic-looking reveals."""
    import math
    return [
        (int(cx + rx * math.cos(2 * math.pi * i / steps)),
         int(cy + ry * math.sin(2 * math.pi * i / steps)))
        for i in range(steps)
    ]


# Each entry is a list of (polygon_points) that get punched out of the overlay.
# Cumulative: each stage includes all prior stages' reveals.
# White Plume Mountain (upper-right) and the southern approach are always visible.

ALWAYS_CLEAR = [
    # Southern road / meadow -- the approach before the tree line
    [(0, 1680), (2400, 1680), (2400, 1920), (0, 1920)],
    # White Plume Mountain only -- just the volcano, not the cave entrance
    [(2150, 0), (2400, 0), (2400, 1920), (2150, 1920)],
]

AREA_REVEALS = [
    # Stage 1: Forest Edge Road -- the trail fork just inside the tree line
    [ellipse_points(1150, 1560, 320, 240)],

    # Stage 2: Ravine Wagon Wreck -- lower right, the stream ravine
    [ellipse_points(1500, 1320, 480, 360)],

    # Stage 3: Logging Camp -- upper left, ruins and K-marks
    [ellipse_points(330, 390, 350, 300)],

    # Stage 4: Dust Pool Glade -- the glowing pool at center
    [ellipse_points(900, 980, 450, 400)],

    # Stage 5: Thorn-Choked Hollow -- upper center mass
    [ellipse_points(700, 300, 600, 300),
     ellipse_points(400, 450, 320, 260)],

    # Stage 6: Game Trails zone -- broad eastern corridor, Blackrazor oak
    [ellipse_points(1350, 780, 580, 500)],

    # Stage 7: Riddle Cave -- right side, cave approach and face-entrance
    [ellipse_points(1720, 1000, 400, 380),
     ellipse_points(1200, 400, 420, 360)],  # upper center remainder
]

STAGE_NAMES = [
    "stage_00_start",
    "stage_01_area1_forest_edge",
    "stage_02_area2_ravine",
    "stage_03_area3_logging_camp",
    "stage_04_area4_dust_pool",
    "stage_05_area5_hollow",
    "stage_06_area6_game_trails",
    "stage_07_area7_riddle_cave",
]


def build_overlay(revealed_polys):
    """Create RGBA overlay: SHADOW everywhere except revealed + always-clear polys."""
    overlay = Image.new("RGBA", (W, H), SHADOW)
    draw = ImageDraw.Draw(overlay)
    for poly in ALWAYS_CLEAR + revealed_polys:
        draw.polygon(poly, fill=(0, 0, 0, 0))
    # Soft edge on reveals so boundaries look organic on print
    overlay = overlay.filter(ImageFilter.GaussianBlur(radius=18))
    # Re-stamp always-clear as fully transparent so road/mountain are crisp
    draw2 = ImageDraw.Draw(overlay)
    for poly in ALWAYS_CLEAR:
        draw2.polygon(poly, fill=(0, 0, 0, 0))
    return overlay


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    base = Image.open(MAP_PATH).convert("RGBA")

    cumulative_reveals = []

    for i, name in enumerate(STAGE_NAMES):
        if i > 0:
            cumulative_reveals.extend(AREA_REVEALS[i - 1])

        overlay = build_overlay(list(cumulative_reveals))
        result = Image.alpha_composite(base, overlay).convert("RGB")
        out_path = os.path.join(OUT_DIR, f"{name}.png")
        result.save(out_path, "PNG", optimize=True)
        print(f"  {name}.png")

    print(f"\nDone. {len(STAGE_NAMES)} files in images/reveal/")


if __name__ == "__main__":
    main()
