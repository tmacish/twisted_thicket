#!/usr/bin/env python3
"""
Generate the Twisted Thicket hex map poster as an SVG.
Output is written to stdout; redirect to the appropriate maps/ file.

Usage:
    python3 src/generate_hex_map.py --mode dm     > maps/hex_map_dm.svg
    python3 src/generate_hex_map.py --mode player > maps/hex_map_player.svg

Player mode shows only locations A and B (the known starting area).
DM mode shows all locations A–H with full legend.
"""

import argparse
import math

W, H = 2400, 1700
margin_x = 150
margin_y = 225

r = 75
sq3 = math.sqrt(3)
col_spacing = r * sq3
row_spacing = r * 1.5
odd_x_offset = r * sq3 / 2

COLS = 12
ROWS = 9

COLORS = {
    'mountain':     '#9a8878',
    'northern_rise':'#b0a090',
    'forest':       '#3a6b2a',
    'deep_forest':  '#2a5520',
    'dark_forest':  '#1e3f18',
    'forest_edge':  '#4a7235',
    'corrupted':    '#2e1812',
    'rocky':        '#7a6a58',
    'glade':        '#7ac858',
    'logging':      '#8a7050',
    'ravine':       '#5c4a38',
    'grass':        '#b8c875',
    'road':         '#d4c285',
}

# Per-hex terrain overrides; default terrain is computed by row in get_terrain()
special = {
    (4,0):'mountain', (5,0):'mountain', (6,0):'northern_rise',
    (7,0):'mountain', (8,0):'mountain',
    (5,1):'dark_forest', (6,1):'dark_forest', (7,1):'dark_forest',
    (4,2):'dark_forest', (5,2):'corrupted', (6,2):'dark_forest', (7,2):'dark_forest',
    (3,3):'deep_forest', (4,3):'glade', (5,3):'deep_forest',
    (8,3):'deep_forest', (9,3):'rocky', (10,3):'deep_forest',
    (3,4):'ravine', (4,4):'deep_forest', (6,4):'logging',
    (2,5):'forest_edge', (3,5):'ravine', (4,5):'deep_forest',
    (1,6):'forest_edge', (2,6):'forest_edge', (3,6):'grass', (4,6):'grass',
    (0,7):'grass', (1,7):'road', (2,7):'grass', (3,7):'grass', (4,7):'grass',
    (0,8):'grass', (1,8):'road', (2,8):'grass', (3,8):'grass', (4,8):'grass', (5,8):'grass',
}


def get_terrain(col, row):
    if (col, row) in special:
        return special[(col, row)]
    if row == 0:
        return 'mountain'
    if row <= 5:
        return 'forest'
    if row <= 7:
        return 'forest_edge'
    return 'grass'


def hex_center(col, row):
    cx = margin_x + col * col_spacing + (odd_x_offset if row % 2 == 1 else 0)
    cy = margin_y + row * row_spacing
    return cx, cy


def hex_pts(cx, cy):
    pts = []
    for i in range(6):
        a = math.radians(30 + 60 * i)
        pts.append(f"{cx + r * math.cos(a):.1f},{cy + r * math.sin(a):.1f}")
    return ' '.join(pts)


locations = {
    'A': {'pos':(1,7), 'label':'Road to Town',                'color':'#b8900a'},
    'B': {'pos':(2,6), 'label':'Forest Edge Camp',             'color':'#3a7a10'},
    'C': {'pos':(3,5), 'label':'Ravine Wagon Wreck',           'color':'#7a4810'},
    'D': {'pos':(6,4), 'label':'Logging Camp',                 'color':'#8a5a18'},
    'E': {'pos':(4,3), 'label':'Dust Pool Glade',              'color':'#20901a'},
    'F': {'pos':(5,2), 'label':'Thorn-Choked Hollow',          'color':'#8a1010'},
    'G': {'pos':(9,3), 'label':'Riddle Cave of the Ash Tongue','color':'#5a4a8a'},
    'H': {'pos':(6,0), 'label':'Northern Rise',                'color':'#506070'},
}

label_dy = {'A':52, 'B':-52, 'C':52, 'D':52, 'E':-52, 'F':-52, 'G':52, 'H':-52}

PLAYER_LOCATIONS = {'A', 'B'}


def build_svg(visible_locations):
    active = {k: v for k, v in locations.items() if k in visible_locations}
    o = []

    o.append('<?xml version="1.0" encoding="UTF-8"?>')
    o.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="36in" height="25.5in" viewBox="0 0 {W} {H}">')
    o.append('  <defs>')
    o.append('    <filter id="ds"><feDropShadow dx="2" dy="2" stdDeviation="3" flood-opacity="0.5"/></filter>')
    o.append('  </defs>')

    # Background and border
    o.append(f'  <rect width="{W}" height="{H}" fill="#f4e8c8"/>')
    o.append(f'  <rect x="15" y="15" width="{W-30}" height="{H-30}" fill="none" stroke="#7a5a20" stroke-width="8" rx="6"/>')
    o.append(f'  <rect x="25" y="25" width="{W-50}" height="{H-50}" fill="none" stroke="#c8a860" stroke-width="2" rx="4"/>')

    # Title
    o.append(f'  <text x="{W//2}" y="100" text-anchor="middle" font-family="Georgia,serif" font-size="62" font-weight="bold" fill="#2a1508" letter-spacing="4">THE TWISTED THICKET</text>')
    o.append(f'  <line x1="80" y1="125" x2="{W-80}" y2="125" stroke="#7a5a20" stroke-width="2"/>')

    # Hex grid
    for row in range(ROWS):
        for col in range(COLS):
            cx, cy = hex_center(col, row)
            t = get_terrain(col, row)
            c = COLORS[t]
            p = hex_pts(cx, cy)
            o.append(f'  <polygon points="{p}" fill="{c}" stroke="#1a0e04" stroke-width="1.2"/>')

    # Coordinate labels (faint, for editing reference)
    for row in range(ROWS):
        for col in range(COLS):
            cx, cy = hex_center(col, row)
            o.append(f'  <text x="{cx:.1f}" y="{cy+4:.1f}" text-anchor="middle" font-family="Georgia,serif" font-size="10" fill="#00000030">{col},{row}</text>')

    # Location marker circles
    for letter, info in active.items():
        col, row = info['pos']
        cx, cy = hex_center(col, row)
        lc = info['color']
        o.append(f'  <circle cx="{cx:.1f}" cy="{cy:.1f}" r="30" fill="{lc}" stroke="#f4e8c8" stroke-width="3.5" filter="url(#ds)"/>')
        o.append(f'  <text x="{cx:.1f}" y="{cy+11:.1f}" text-anchor="middle" font-family="Georgia,serif" font-size="28" font-weight="bold" fill="white">{letter}</text>')

    # Location name labels beside markers
    for letter, info in active.items():
        col, row = info['pos']
        cx, cy = hex_center(col, row)
        lx = cx
        ly = cy + label_dy[letter]
        words = info['label'].split()
        mid = len(words) // 2
        lines = [' '.join(words[:mid]), ' '.join(words[mid:])] if len(words) > 2 else [info['label']]
        for li, line in enumerate(lines):
            lyi = ly + li * 20
            o.append(f'  <text x="{lx:.1f}" y="{lyi:.1f}" text-anchor="middle" font-family="Georgia,serif" font-size="16" font-weight="bold" stroke="#f4e8c8" stroke-width="4" paint-order="stroke" fill="{info["color"]}">{line}</text>')

    # Legend panel — terrain key
    lx0 = 1790
    ly0 = 225
    terrain_items = [
        ('mountain',     'Mountain / High Ground'),
        ('northern_rise','Northern Rise (White Plume Mtn)'),
        ('forest',       'Forest'),
        ('deep_forest',  'Deep Forest'),
        ('dark_forest',  'Dense Thicket'),
        ('corrupted',    'Corrupted Ground'),
        ('rocky',        'Rocky Outcrop'),
        ('glade',        'Glade / Clearing'),
        ('logging',      'Logged / Cleared'),
        ('ravine',       'Ravine'),
        ('grass',        'Open Grassland'),
        ('road',         'Road / Track'),
    ]
    t_panel_h = 44 + len(terrain_items) * 33 + 16
    o.append(f'  <rect x="{lx0-12}" y="{ly0-12}" width="570" height="{t_panel_h}" fill="#ede0b5" stroke="#7a5a20" stroke-width="2" rx="5"/>')
    o.append(f'  <text x="{lx0+271}" y="{ly0+20}" text-anchor="middle" font-family="Georgia,serif" font-size="22" font-weight="bold" fill="#2a1508">TERRAIN KEY</text>')
    for i, (tk, tlabel) in enumerate(terrain_items):
        iy = ly0 + 44 + i * 33
        tc = COLORS[tk]
        o.append(f'  <rect x="{lx0}" y="{iy-2}" width="26" height="20" fill="{tc}" stroke="#2a1508" stroke-width="1"/>')
        o.append(f'  <text x="{lx0+38}" y="{iy+14}" font-family="Georgia,serif" font-size="18" fill="#2a1508">{tlabel}</text>')

    # Legend panel — location key (only visible locations)
    lky0 = ly0 + t_panel_h + 24
    loc_panel_h = 44 + len(active) * 36 + 16
    o.append(f'  <rect x="{lx0-12}" y="{lky0-12}" width="570" height="{loc_panel_h}" fill="#ede0b5" stroke="#7a5a20" stroke-width="2" rx="5"/>')
    o.append(f'  <text x="{lx0+271}" y="{lky0+20}" text-anchor="middle" font-family="Georgia,serif" font-size="22" font-weight="bold" fill="#2a1508">LOCATIONS</text>')
    for i, (letter, info) in enumerate(active.items()):
        iy = lky0 + 44 + i * 36
        lc = info['color']
        o.append(f'  <circle cx="{lx0+14}" cy="{iy+9}" r="14" fill="{lc}" stroke="#2a1508" stroke-width="1"/>')
        o.append(f'  <text x="{lx0+14}" y="{iy+14}" text-anchor="middle" font-family="Georgia,serif" font-size="15" font-weight="bold" fill="white">{letter}</text>')
        o.append(f'  <text x="{lx0+40}" y="{iy+15}" font-family="Georgia,serif" font-size="18" fill="#2a1508">{info["label"]}</text>')

    # Compass rose
    crx, cry = W - 180, H - 175
    crr = 65
    for deg, lbl, north in [(0,'N',True),(90,'E',False),(180,'S',False),(270,'W',False)]:
        a = math.radians(deg - 90)
        tx = crx + (crr - 8) * math.cos(a)
        ty = cry + (crr - 8) * math.sin(a)
        bx = crx - 14 * math.cos(a)
        by = cry - 14 * math.sin(a)
        lxp = crx + 10 * math.cos(a + math.pi/2)
        lyp = cry + 10 * math.sin(a + math.pi/2)
        rxp = crx + 10 * math.cos(a - math.pi/2)
        ryp = cry + 10 * math.sin(a - math.pi/2)
        fill = '#8a1010' if north else '#f4e8c8'
        o.append(f'  <polygon points="{tx:.1f},{ty:.1f} {lxp:.1f},{lyp:.1f} {bx:.1f},{by:.1f} {rxp:.1f},{ryp:.1f}" fill="{fill}" stroke="#2a1508" stroke-width="1.5"/>')
        lx = crx + (crr + 18) * math.cos(a)
        ly = cry + (crr + 18) * math.sin(a) + 7
        o.append(f'  <text x="{lx:.1f}" y="{ly:.1f}" text-anchor="middle" font-family="Georgia,serif" font-size="22" font-weight="bold" fill="#2a1508">{lbl}</text>')
    o.append(f'  <circle cx="{crx}" cy="{cry}" r="7" fill="#2a1508"/>')

    # Scale bar
    scx, scy = 100, H - 80
    scw = 280
    segs = 6
    sw = scw // segs
    o.append(f'  <text x="{scx+scw//2}" y="{scy-20}" text-anchor="middle" font-family="Georgia,serif" font-size="17" fill="#2a1508">1 hex ≈ ½ mile</text>')
    o.append(f'  <line x1="{scx}" y1="{scy}" x2="{scx+scw}" y2="{scy}" stroke="#2a1508" stroke-width="2.5"/>')
    for s in range(segs):
        sf = '#2a1508' if s % 2 == 0 else '#f4e8c8'
        o.append(f'  <rect x="{scx+s*sw}" y="{scy-4}" width="{sw}" height="8" fill="{sf}" stroke="#2a1508" stroke-width="1"/>')
    o.append(f'  <line x1="{scx}" y1="{scy-8}" x2="{scx}" y2="{scy+8}" stroke="#2a1508" stroke-width="2"/>')
    o.append(f'  <line x1="{scx+scw}" y1="{scy-8}" x2="{scx+scw}" y2="{scy+8}" stroke="#2a1508" stroke-width="2"/>')
    o.append(f'  <text x="{scx}" y="{scy+24}" text-anchor="middle" font-family="Georgia,serif" font-size="15" fill="#2a1508">0</text>')
    o.append(f'  <text x="{scx+scw//2}" y="{scy+24}" text-anchor="middle" font-family="Georgia,serif" font-size="15" fill="#2a1508">1.5</text>')
    o.append(f'  <text x="{scx+scw}" y="{scy+24}" text-anchor="middle" font-family="Georgia,serif" font-size="15" fill="#2a1508">3 mi</text>')

    # Footer
    o.append(f'  <text x="{W//2}" y="{H-28}" text-anchor="middle" font-family="Georgia,serif" font-size="15" font-style="italic" fill="#7a5a30">PLACEHOLDER MAP · The Twisted Thicket · Commissioned art to replace this draft</text>')

    o.append('</svg>')
    return '\n'.join(o)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate Twisted Thicket hex map SVG.')
    parser.add_argument(
        '--mode',
        choices=['dm', 'player'],
        default='dm',
        help='dm: all locations shown; player: only A and B shown (default: dm)',
    )
    args = parser.parse_args()
    visible = set(locations.keys()) if args.mode == 'dm' else PLAYER_LOCATIONS
    print(build_svg(visible))
