#!/usr/bin/env python3
"""
Generate Ringstown town map as SVG.
Building locations are randomized each run unless --seed is specified.
Stone walls form the town perimeter with corner towers and two gates.

Usage:
    python3 src/generate_ringstown.py > maps/ringstown.svg
    python3 src/generate_ringstown.py --seed 42 > maps/ringstown.svg
"""

import argparse
import math
import random


def x(text):
    """Escape text for safe inclusion in XML/SVG."""
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

W, H = 2400, 1800
SQ3 = math.sqrt(3)

R = 62          # hex circumradius, pointy-top
TOWN_R = 5      # wall ring (distance from center)
GRID_R = 7      # render this many rings total (TOWN_R + 2 exterior rings)

MAP_CX = 840    # town center x (offset left to leave legend room)
MAP_CY = 950    # town center y


# ---------------------------------------------------------------------------
# Axial coordinate helpers (pointy-top hexes)
# ---------------------------------------------------------------------------

def axial_to_pixel(q, s):
    px = MAP_CX + R * (SQ3 * q + SQ3 / 2 * s)
    py = MAP_CY + R * 1.5 * s
    return px, py


def axial_dist(q, s):
    return (abs(q) + abs(q + s) + abs(s)) // 2


def hex_poly(cx, cy, radius=None):
    if radius is None:
        radius = R
    pts = []
    for i in range(6):
        a = math.radians(30 + 60 * i)
        pts.append(f"{cx + radius * math.cos(a):.1f},{cy + radius * math.sin(a):.1f}")
    return ' '.join(pts)


# ---------------------------------------------------------------------------
# Town layout constants
# ---------------------------------------------------------------------------

# Six corner towers of the wall ring
TOWERS = {(5, 0), (0, 5), (-5, 5), (-5, 0), (0, -5), (5, -5)}

# Gate hexes: two at south (toward Critwall road), one at north (toward Thicket)
SOUTH_GATE = frozenset({(0, 5), (-1, 5)})
NORTH_GATE = frozenset({(0, -5)})
ALL_GATES   = SOUTH_GATE | NORTH_GATE

# Fixed building positions (not randomised)
TOWN_SQUARE   = (0, 0)   # always at centre
GATEHOUSE_HEX = (0, 4)   # Elnara's Post, just inside the south gate


# ---------------------------------------------------------------------------
# Colors
# ---------------------------------------------------------------------------

COLORS = {
    'exterior_far':  '#2a5520',
    'exterior_near': '#4a7235',
    'wall':          '#7a7060',
    'tower':         '#504838',
    'gate':          '#a09060',
    'street':        '#c8b888',
    'square':        '#c8b060',
    # building type keys
    'inn':           '#c87830',
    'tavern':        '#a03020',
    'alchemist':     '#7040a0',
    'smithy':        '#586878',
    'armory':        '#884040',
    'stable':        '#b08840',
    'temple':        '#c0a018',
    'garrison':      '#385068',
    'well':          '#3870a8',
    'market':        '#78a028',
    'herbalist':     '#308040',
    'warehouse':     '#907860',
    'gatehouse':     '#285888',
}


# ---------------------------------------------------------------------------
# Building definitions
# (type, label_line1, label_line2, full_name, color_key)
# ---------------------------------------------------------------------------

BUILDINGS = [
    ('inn',       "Plume's",    'Rest',       "The Plume's Rest",       'inn'),
    ('tavern',    'Scalded',    'Goblin',     'The Scalded Goblin',     'tavern'),
    ('tavern',    'Black',      'Feather',    'The Black Feather',      'tavern'),
    ('alchemist', "Thingiz-",   "zard's",     "Thingizzard's Sundries", 'alchemist'),
    ('smithy',    'Hammer &',   'Thorn',      'Hammer & Thorn Smithy',  'smithy'),
    ('smithy',    'Anvil',      'Ring',       'The Anvil Ring',         'smithy'),
    ('armory',    'White Plume','Armory',     'White Plume Armory',     'armory'),
    ('stable',    "Brindle's",  'Stable',     "Brindle's Stable",       'stable'),
    ('temple',    'St.',        'Cuthbert',   'Shrine of St. Cuthbert', 'temple'),
    ('garrison',  'Shield',     'Post',       'The Shield Post',        'garrison'),
    ('well',      'Town',       'Well',       'The Town Well',          'well'),
    ('market',    'Ring',       'Market',     'Ring Square Market',     'market'),
    ('herbalist', 'Moss &',     'Root',       'Moss & Root Herbals',    'herbalist'),
    ('warehouse', "Chandler's", 'Whs.',       "Chandler's Warehouse",   'warehouse'),
]

FIXED_BUILDINGS = {
    TOWN_SQUARE:    ('square',    'Ring',     'Square', 'Ring Square',   'square'),
    GATEHOUSE_HEX:  ('gatehouse', "Elnara's", 'Post',   "Elnara's Post", 'gatehouse'),
}


# ---------------------------------------------------------------------------
# SVG generation
# ---------------------------------------------------------------------------

def build_svg(seed=None):
    rng = random.Random(seed)
    o = []

    # --- Enumerate all hexes ---
    hexes = {}
    for q in range(-GRID_R, GRID_R + 1):
        for s in range(-GRID_R, GRID_R + 1):
            if abs(q + s) > GRID_R:
                continue
            d = axial_dist(q, s)
            if d < TOWN_R:
                hexes[(q, s)] = 'interior'
            elif d == TOWN_R:
                if (q, s) in TOWERS:
                    hexes[(q, s)] = 'tower'
                elif (q, s) in ALL_GATES:
                    hexes[(q, s)] = 'gate'
                else:
                    hexes[(q, s)] = 'wall'
            elif d == TOWN_R + 1:
                hexes[(q, s)] = 'exterior_near'
            else:
                hexes[(q, s)] = 'exterior_far'

    # --- Random building placement ---
    interior = [
        hx for hx, t in hexes.items()
        if t == 'interior' and hx not in FIXED_BUILDINGS
    ]
    rng.shuffle(interior)

    placement = dict(FIXED_BUILDINGS)
    for i, bld in enumerate(BUILDINGS):
        if i < len(interior):
            placement[interior[i]] = bld
    for hx in interior[len(BUILDINGS):]:
        placement[hx] = ('street', '', '', '', 'street')

    # --- SVG header ---
    o.append('<?xml version="1.0" encoding="UTF-8"?>')
    o.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="24in" height="18in" viewBox="0 0 {W} {H}">')
    o.append('  <defs>')
    o.append('    <filter id="ds"><feDropShadow dx="1" dy="1" stdDeviation="2" flood-opacity="0.4"/></filter>')
    o.append('  </defs>')

    # Background + border
    o.append(f'  <rect width="{W}" height="{H}" fill="#f4e8c8"/>')
    o.append(f'  <rect x="15" y="15" width="{W-30}" height="{H-30}" fill="none" stroke="#7a5a20" stroke-width="8" rx="6"/>')
    o.append(f'  <rect x="25" y="25" width="{W-50}" height="{H-50}" fill="none" stroke="#c8a860" stroke-width="2" rx="4"/>')

    # Title
    o.append(f'  <text x="{W//2}" y="90" text-anchor="middle" font-family="Georgia,serif" font-size="70" font-weight="bold" fill="#2a1508" letter-spacing="6">RINGSTOWN</text>')
    o.append(f'  <text x="{W//2}" y="130" text-anchor="middle" font-family="Georgia,serif" font-size="24" font-style="italic" fill="#5a3818">Frontier Town · Shield Lands · The Twisted Thicket</text>')
    o.append(f'  <line x1="80" y1="150" x2="{W-80}" y2="150" stroke="#7a5a20" stroke-width="2"/>')

    # --- Draw hexes ---
    draw_order = ['exterior_far', 'exterior_near', 'wall', 'tower', 'gate', 'interior']

    for t in draw_order:
        for hx, ht in hexes.items():
            if ht != t:
                continue
            q, s = hx
            cx, cy = axial_to_pixel(q, s)
            pts = hex_poly(cx, cy)

            # Fill colour
            if t == 'interior' and hx in placement:
                bld = placement[hx]
                fill = COLORS.get(bld[4], COLORS['street'])
            elif t == 'interior':
                fill = COLORS['street']
            else:
                fill = COLORS[t]

            stroke_c = '#1a0e04' if t not in ('exterior_far', 'exterior_near') else '#1a3010'
            stroke_w = '2.0' if t in ('wall', 'tower') else '1.0'
            o.append(f'  <polygon points="{pts}" fill="{fill}" stroke="{stroke_c}" stroke-width="{stroke_w}"/>')

            # Inner ring on towers to suggest battlements
            if t == 'tower':
                ipts = hex_poly(cx, cy, R * 0.58)
                o.append(f'  <polygon points="{ipts}" fill="none" stroke="#302820" stroke-width="1.5" stroke-dasharray="4,2"/>')

            # Gate label
            if t == 'gate':
                lbl = 'S.Gate' if (q, s) in SOUTH_GATE else 'N.Gate'
                o.append(f'  <text x="{cx:.1f}" y="{cy+4:.1f}" text-anchor="middle" font-family="Georgia,serif" font-size="8" fill="#3a2808">{lbl}</text>')

    # --- Building labels ---
    for hx, bld in placement.items():
        if bld[4] == 'street':
            continue
        q, s = hx
        cx, cy = axial_to_pixel(q, s)
        l1, l2 = bld[1], bld[2]
        # Dark text with white stroke so it reads on any fill
        style = 'font-family="Georgia,serif" font-size="9.5" font-weight="bold" stroke="white" stroke-width="2.5" paint-order="stroke" fill="#1a0800"'
        if l2:
            o.append(f'  <text x="{cx:.1f}" y="{cy-2:.1f}" text-anchor="middle" {style}>{x(l1)}</text>')
            o.append(f'  <text x="{cx:.1f}" y="{cy+10:.1f}" text-anchor="middle" {style}>{x(l2)}</text>')
        else:
            o.append(f'  <text x="{cx:.1f}" y="{cy+4:.1f}" text-anchor="middle" {style}>{x(l1)}</text>')

    # --- Road label below south gate ---
    sg_list = sorted(SOUTH_GATE)
    sx = sum(axial_to_pixel(q, s)[0] for q, s in sg_list) / len(sg_list)
    sy = max(axial_to_pixel(q, s)[1] for q, s in sg_list) + R + 40
    o.append(f'  <text x="{sx:.0f}" y="{sy:.0f}" text-anchor="middle" font-family="Georgia,serif" font-size="18" font-style="italic" fill="#5a3818">↓ Road to Critwall</text>')

    # North gate label
    nx, ny = axial_to_pixel(0, -TOWN_R)
    o.append(f'  <text x="{nx:.0f}" y="{ny - R - 20:.0f}" text-anchor="middle" font-family="Georgia,serif" font-size="18" font-style="italic" fill="#5a3818">↑ The Twisted Thicket</text>')

    # --- Legend panel ---
    lx0, ly0 = 1720, 200
    legend_entries = [
        ('wall',    COLORS['wall'],    'Stone Wall'),
        ('tower',   COLORS['tower'],   'Wall Tower'),
        ('gate',    COLORS['gate'],    'Town Gate'),
        ('street',  COLORS['street'],  'Street / Open Ground'),
        ('square',  COLORS['square'],  'Ring Square'),
    ]
    seen_names = {e[2] for e in legend_entries}
    for bld in list(FIXED_BUILDINGS.values()) + BUILDINGS:
        name = bld[3]
        if name not in seen_names:
            seen_names.add(name)
            legend_entries.append((bld[0], COLORS[bld[4]], name))

    panel_h = 44 + len(legend_entries) * 30 + 16
    o.append(f'  <rect x="{lx0-12}" y="{ly0-12}" width="624" height="{panel_h}" fill="#ede0b5" stroke="#7a5a20" stroke-width="2" rx="5"/>')
    o.append(f'  <text x="{lx0+300}" y="{ly0+20}" text-anchor="middle" font-family="Georgia,serif" font-size="22" font-weight="bold" fill="#2a1508">MAP KEY</text>')
    for i, (_, color, label) in enumerate(legend_entries):
        iy = ly0 + 44 + i * 30
        o.append(f'  <rect x="{lx0}" y="{iy-2}" width="24" height="18" fill="{color}" stroke="#2a1508" stroke-width="1"/>')
        o.append(f'  <text x="{lx0+34}" y="{iy+12}" font-family="Georgia,serif" font-size="16" fill="#2a1508">{x(label)}</text>')

    # --- Compass rose ---
    crx, cry = W - 155, H - 160
    crr = 55
    for deg, lbl, north in [(0, 'N', True), (90, 'E', False), (180, 'S', False), (270, 'W', False)]:
        a = math.radians(deg - 90)
        tx  = crx + (crr - 8)  * math.cos(a);  ty  = cry + (crr - 8)  * math.sin(a)
        bx  = crx - 12         * math.cos(a);  by  = cry - 12         * math.sin(a)
        lxp = crx + 9 * math.cos(a + math.pi / 2); lyp = cry + 9 * math.sin(a + math.pi / 2)
        rxp = crx + 9 * math.cos(a - math.pi / 2); ryp = cry + 9 * math.sin(a - math.pi / 2)
        fill = '#8a1010' if north else '#f4e8c8'
        o.append(f'  <polygon points="{tx:.1f},{ty:.1f} {lxp:.1f},{lyp:.1f} {bx:.1f},{by:.1f} {rxp:.1f},{ryp:.1f}" fill="{fill}" stroke="#2a1508" stroke-width="1.5"/>')
        lx = crx + (crr + 16) * math.cos(a)
        ly = cry + (crr + 16) * math.sin(a) + 6
        o.append(f'  <text x="{lx:.1f}" y="{ly:.1f}" text-anchor="middle" font-family="Georgia,serif" font-size="18" font-weight="bold" fill="#2a1508">{lbl}</text>')
    o.append(f'  <circle cx="{crx}" cy="{cry}" r="6" fill="#2a1508"/>')
    o.append(f'  <text x="{crx}" y="{cry - crr - 22}" text-anchor="middle" font-family="Georgia,serif" font-size="13" font-style="italic" fill="#5a3818">White Plume Mtn.</text>')

    # --- Footer ---
    seed_note = f'Seed: {seed}' if seed is not None else 'Layout randomised each run  ·  use --seed N for reproducible output'
    o.append(f'  <text x="{W//2}" y="{H-28}" text-anchor="middle" font-family="Georgia,serif" font-size="14" font-style="italic" fill="#7a5a30">RINGSTOWN  ·  {seed_note}</text>')

    o.append('</svg>')
    return '\n'.join(o)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate Ringstown town map SVG.')
    parser.add_argument('--seed', type=int, default=None,
                        help='Random seed for a reproducible layout (omit for random)')
    args = parser.parse_args()
    print(build_svg(args.seed))
