#!/usr/bin/env python3
"""
Player handout generator for The Twisted Thicket.
Produces parchment-document PNG images in the preread1.png scroll aesthetic.

Usage:
    python3 generate_handouts.py          # all handouts
    python3 generate_handouts.py manifest # single handout by keyword

Requires: pip install Pillow
"""

import sys
import math
import random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT      = Path(__file__).parent
FONTS_DIR = ROOT / "fonts"
OUT_DIR   = ROOT / "handouts"

# ---------------------------------------------------------------------------
# Palette — warm parchment, dark ink, sepia brown, blood red
# ---------------------------------------------------------------------------
BG           = (15,  8,  2)        # near-black background
PARCH        = (196,161,104)       # parchment base
PARCH_LIGHT  = (222,192,138)       # lighter parchment center
PARCH_DARK   = (148,112, 62)       # dark edges / aged areas
INK          = ( 28, 12,  2)       # near-black ink
BROWN        = ( 96, 34,  8)       # medium sepia brown
RED          = (125,  0, 10)       # blood red (for rubrics)
GOLD_RULE    = (148,108, 42)       # golden rule lines
BARK         = ( 92, 56, 18)       # bark brown
BARK_DARK    = ( 52, 28,  6)       # dark bark
STONE        = ( 82, 68, 48)       # carved stone base
STONE_LIGHT  = (120,104, 80)       # raised stone surface
STONE_CARVE  = (220,200,164)       # carved-out letter color

# ---------------------------------------------------------------------------
# Font helpers
# ---------------------------------------------------------------------------
def fnt(name: str, size: int) -> ImageFont.FreeTypeFont:
    paths = {
        'bl':   FONTS_DIR / 'Blackletter.ttf',
        'body': FONTS_DIR / 'IMFell.ttf',
        'ital': FONTS_DIR / 'IMFell-Italic.ttf',
        'head': FONTS_DIR / 'Cinzel.ttf',
    }
    try:
        return ImageFont.truetype(str(paths.get(name, paths['body'])), size)
    except OSError:
        return ImageFont.load_default()

def tw(draw, text, font):
    """Text width."""
    return draw.textbbox((0, 0), text, font=font)[2]

def th(draw, text, font):
    """Text height."""
    b = draw.textbbox((0, 0), text, font=font)
    return b[3] - b[1]

def wrap(draw, text, font, max_w):
    """Word-wrap to max_w pixels. Returns list of lines."""
    lines, cur = [], ""
    for word in text.split():
        test = (cur + " " + word).strip()
        if tw(draw, test, font) <= max_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines or [""]

# ---------------------------------------------------------------------------
# Texture generators
# ---------------------------------------------------------------------------
def parchment_texture(w, h, seed=0, variation=20):
    rng = random.Random(seed)
    img = Image.new('RGB', (w, h))
    px  = img.load()
    br, bg, bb = PARCH
    for y in range(h):
        row_bias = rng.randint(-8, 8)
        for x in range(w):
            n = rng.randint(-variation, variation) + row_bias
            px[x, y] = (
                max(0, min(255, br + n)),
                max(0, min(255, bg + n - 5)),
                max(0, min(255, bb + n - 12)),
            )
    return img.filter(ImageFilter.GaussianBlur(0.9))


def bark_texture(w, h, seed=5):
    rng = random.Random(seed)
    img = Image.new('RGB', (w, h))
    px  = img.load()
    br, bg, bb = BARK
    for y in range(h):
        # Long horizontal grain streaks
        row_noise = rng.randint(-20, 20)
        for x in range(w):
            grain = rng.randint(-12, 12)
            px[x, y] = (
                max(0, min(255, br + grain + row_noise // 2)),
                max(0, min(255, bg + grain + row_noise // 3)),
                max(0, min(255, bb + grain + row_noise // 4)),
            )
    # Add vertical crack lines
    for _ in range(rng.randint(8, 14)):
        cx = rng.randint(0, w)
        for y in range(0, h, rng.randint(2, 5)):
            if rng.random() > 0.3:
                px[max(0, min(w-1, cx + rng.randint(-1,1))), y] = BARK_DARK
    return img.filter(ImageFilter.GaussianBlur(0.5))


def stone_texture(w, h, seed=9):
    rng = random.Random(seed)
    img = Image.new('RGB', (w, h))
    px  = img.load()
    sr, sg, sb = STONE
    for y in range(h):
        for x in range(w):
            n = rng.randint(-15, 15)
            px[x, y] = (
                max(0, min(255, sr + n)),
                max(0, min(255, sg + n)),
                max(0, min(255, sb + n - 3)),
            )
    return img.filter(ImageFilter.GaussianBlur(0.7))


def add_vignette(img, strength=0.5):
    w, h = img.size
    ov   = Image.new('RGB', (w, h), (0, 0, 0))
    mask = Image.new('L',   (w, h), 0)
    d    = ImageDraw.Draw(mask)
    steps = 90
    for i in range(steps):
        v = int(255 * ((steps - i) / steps) ** 1.9 * strength)
        d.rectangle([i, i, w-i-1, h-i-1], outline=v)
    img.paste(ov, mask=mask)
    return img


def add_scroll_curl(img, curl_h=70):
    """Darken top and bottom edges to simulate scroll curl."""
    w, h = img.size
    px   = img.load()
    for y in range(curl_h):
        t = 1.0 - (y / curl_h) ** 0.6
        for x in range(w):
            r, g, b = px[x, y]
            px[x, y] = (int(r*(1-t)), int(g*(1-t)), int(b*(1-t)))
        # Bottom mirror
        r, g, b = px[x, h-1-y]
        for x in range(w):
            r, g, b = px[x, h-1-y]
            px[x, h-1-y] = (int(r*(1-t)), int(g*(1-t)), int(b*(1-t)))
    return img


def add_age_spots(img, count=25, seed=17):
    rng = random.Random(seed)
    w, h = img.size
    d    = ImageDraw.Draw(img)
    for _ in range(count):
        x, y = rng.randint(5, w-5), rng.randint(5, h-5)
        sz   = rng.randint(1, 5)
        dk   = rng.randint(15, 50)
        col  = tuple(max(0, c - dk) for c in PARCH)
        d.ellipse([x, y, x+sz, y+sz], fill=col)
    return img


def add_water_stain(img, n=4, seed=31):
    rng = random.Random(seed)
    w, h = img.size
    d    = ImageDraw.Draw(img)
    for _ in range(n):
        x  = rng.randint(w//5, 4*w//5)
        y  = rng.randint(h//4, 3*h//4)
        rw = rng.randint(50, 180)
        rh = rng.randint(25, 90)
        col = tuple(max(0, c - rng.randint(18, 35)) for c in PARCH)
        for expand in range(4):
            d.ellipse([x-rw+expand*3, y-rh+expand*2,
                       x+rw-expand*3, y+rh-expand*2], outline=col)
    return img

# ---------------------------------------------------------------------------
# Decorative drawing
# ---------------------------------------------------------------------------
def draw_weapon_icons(draw, cx, y, size=46, spacing=80):
    """Draw four weapon silhouettes (sword, hammer, trident, spear) centered at cx."""

    def icon_sword(d, x, y, s):
        d.line([(x, y-s//2-4), (x, y+s//2)], fill=BROWN, width=2)
        d.line([(x-s//4, y+s//8), (x+s//4, y+s//8)], fill=BROWN, width=3)
        d.ellipse([x-3, y+s//2-2, x+3, y+s//2+5], fill=BROWN)
        d.polygon([(x, y-s//2-10), (x-3, y-s//2-2), (x+3, y-s//2-2)], fill=BROWN)

    def icon_hammer(d, x, y, s):
        d.line([(x, y-s//4), (x, y+s//2)], fill=BROWN, width=2)
        d.rectangle([x-s//4, y-s//2, x+s//4, y-s//4], fill=BROWN)

    def icon_trident(d, x, y, s):
        d.line([(x, y-s//8), (x, y+s//2)], fill=BROWN, width=2)
        for tx in [-s//5, 0, s//5]:
            d.line([(x+tx, y+s//8), (x+tx, y-s//2)], fill=BROWN, width=2)
            d.polygon([(x+tx, y-s//2-6), (x+tx-3, y-s//2+2),
                       (x+tx+3, y-s//2+2)], fill=BROWN)

    def icon_spear(d, x, y, s):
        d.line([(x, y-s//3), (x, y+s//2)], fill=BROWN, width=2)
        d.polygon([(x, y-s//2-6), (x-5, y-s//3+2), (x+5, y-s//3+2)], fill=BROWN)

    icons = [icon_sword, icon_hammer, icon_trident, icon_spear]
    positions = [cx + spacing * (i - 1.5) for i in range(4)]
    for fn, px in zip(icons, positions):
        fn(draw, int(px), y + size // 2, size)

    rule_y = y + size + 10
    lx = int(positions[0] - spacing // 2)
    rx = int(positions[-1] + spacing // 2)
    draw.line([(lx, rule_y),     (rx, rule_y)],     fill=GOLD_RULE, width=1)
    draw.line([(lx, rule_y + 4), (rx, rule_y + 4)], fill=GOLD_RULE, width=1)
    return rule_y + 8


def draw_rule(draw, x1, y, x2):
    draw.line([(x1, y),   (x2, y)],   fill=GOLD_RULE, width=1)
    draw.line([(x1, y+3), (x2, y+3)], fill=GOLD_RULE, width=1)
    return y + 7


def draw_paragraph(draw, text, x, y, max_w, font, lh, bottom_y,
                   dropcap=True, color=INK):
    """Render a paragraph with optional drop cap. Returns new y."""
    if not text.strip():
        return y + lh // 2

    if dropcap and text[0].isalpha():
        cap_letter = text[0]
        rest       = text[1:]
        cap_lines  = 3
        cap_sz     = lh * cap_lines - 6
        cap_font   = fnt('bl', cap_sz)
        cap_bb     = draw.textbbox((0, 0), cap_letter, font=cap_font)
        cap_w      = cap_bb[2] - cap_bb[0]
        cap_h      = cap_bb[3] - cap_bb[1]

        draw.text((x, y - 2), cap_letter, font=cap_font, fill=BROWN)

        # Text beside cap
        side_w    = max_w - cap_w - 8
        side_x    = x + cap_w + 8
        side_lines = wrap(draw, rest, font, side_w)
        beside_n  = cap_lines  # render this many lines beside cap

        ry = y
        for i, line in enumerate(side_lines):
            if i >= beside_n:
                # Switch to full width for remainder
                remainder = " ".join(side_lines[i:])
                ry = max(ry, y + cap_h + 4)
                for full_line in wrap(draw, remainder, font, max_w):
                    if ry + lh > bottom_y: return ry
                    draw.text((x, ry), full_line, font=font, fill=color)
                    ry += lh
                return ry
            if ry + lh > bottom_y: return ry
            draw.text((side_x, ry), line, font=font, fill=color)
            ry += lh
        ry = max(ry, y + cap_h + 4)
        return ry

    # No drop cap — plain wrapped text
    for line in wrap(draw, text, font, max_w):
        if y + lh > bottom_y: break
        draw.text((x, y), line, font=font, fill=color)
        y += lh
    return y

# ---------------------------------------------------------------------------
# Scroll canvas factory
# ---------------------------------------------------------------------------
def make_scroll_canvas(width=900, height=1200, seed=42):
    """
    Returns (composite_img, content_rect).
    content_rect = (x1, y1, x2, y2) — usable area inside the scroll.
    """
    bg = Image.new('RGB', (width, height), BG)
    d  = ImageDraw.Draw(bg)

    MX, MY = 48, 60   # margin: left/right, top/bottom

    PW = width  - 2 * MX
    PH = height - 2 * MY

    # Parchment slab
    p = parchment_texture(PW, PH, seed=seed)
    p = add_vignette(p, strength=0.42)
    p = add_scroll_curl(p, curl_h=80)
    p = add_age_spots(p, seed=seed+3)

    bg.paste(p, (MX, MY))

    # Scroll rods (dark cylinders at top and bottom)
    rod_col = (28, 12, 3)
    hl_col  = (60, 36, 16)
    d.rectangle([MX, MY-10,  MX+PW, MY+26],             fill=rod_col)
    d.line(     [MX, MY-8,   MX+PW, MY-8],              fill=hl_col, width=3)
    d.rectangle([MX, MY+PH-26, MX+PW, MY+PH+10],        fill=rod_col)
    d.line(     [MX, MY+PH+8,  MX+PW, MY+PH+8],         fill=hl_col, width=3)

    # Parchment outline
    d.rectangle([MX, MY, MX+PW, MY+PH], outline=(36, 16, 4), width=2)

    # Content area (inside parchment, with inner margins)
    PAD_X = 62
    PAD_Y = 92
    content = (MX+PAD_X, MY+PAD_Y, MX+PW-PAD_X, MY+PH-PAD_Y)
    return bg, content


# ---------------------------------------------------------------------------
# Handout 1 — Wagon Manifest (Area 2)
# ---------------------------------------------------------------------------
def make_manifest():
    img, (x1, y1, x2, y2) = make_scroll_canvas(900, 870, seed=10)
    d  = ImageDraw.Draw(img)
    cw = x2 - x1

    add_water_stain(img, n=3, seed=22)

    y = y1

    # Weapon icons
    y = draw_weapon_icons(d, (x1+x2)//2, y) + 14

    # Letterhead
    hf = fnt('head', 28)
    line1 = "BLINK TINDERFLIP"
    d.text(((x1+x2-tw(d, line1, hf))//2, y), line1, font=hf, fill=BROWN)
    y += th(d, line1, hf) + 4
    sf = fnt('ital', 20)
    line2 = "Freight & Carriage  —  Critwall to Ringstown"
    d.text(((x1+x2-tw(d, line2, sf))//2, y), line2, font=sf, fill=INK)
    y += th(d, line2, sf) + 8
    y = draw_rule(d, x1, y, x2) + 10

    # "CONSIGNMENT MANIFEST"
    mf = fnt('head', 19)
    label = "CONSIGNMENT MANIFEST"
    d.text(((x1+x2-tw(d, label, mf))//2, y), label, font=mf, fill=RED)
    y += th(d, label, mf) + 14

    # Blink's mark (stylised T in circle)
    mark_x, mark_y = (x1+x2)//2, y + 28
    d.ellipse([mark_x-26, mark_y-26, mark_x+26, mark_y+26], outline=BROWN, width=2)
    tf = fnt('head', 30)
    d.text((mark_x - tw(d, "T", tf)//2, mark_y - th(d, "T", tf)//2 - 2),
           "T", font=tf, fill=BROWN)
    y += 68

    y = draw_rule(d, x1, y, x2) + 14

    # Coach entries
    entries = [
        ("COACH A", [
            "Wave — sealed cask, handle with care.",
        ]),
        ("COACH B", [
            "W. — wrapped head, iron band.",
            "BR — wrapped, do not unwrap.",
        ]),
    ]
    ef = fnt('ital', 26)
    lf = fnt('body', 26)
    lh = th(d, "Xg", lf) + 8

    for coach_label, items in entries:
        d.text((x1, y), coach_label + ":", font=ef, fill=RED)
        y += lh + 2
        for item in items:
            d.text((x1 + 28, y), item, font=lf, fill=INK)
            y += lh
        y += 10
        y = draw_rule(d, x1, y, x2) + 12

    # Addressee
    y += 10
    af = fnt('ital', 23)
    d.text((x1, y), "Addressed to:", font=af, fill=BROWN)
    y += th(d, "X", af) + 4
    nf = fnt('body', 28)
    d.text((x1 + 28, y), "E. Forger, Ringstown", font=nf, fill=INK)
    y += th(d, "X", nf) + 14

    # Signature line
    y = draw_rule(d, x1, y, x1 + cw // 2) + 8
    d.text((x1, y), "Authorised by:", font=af, fill=BROWN)

    img.save(OUT_DIR / "area2_wagon_manifest.png")
    print("  area2_wagon_manifest.png")


# ---------------------------------------------------------------------------
# Handout 2 — Coded Ledger Page (Area 2)
# ---------------------------------------------------------------------------
def make_coded_ledger():
    img, (x1, y1, x2, y2) = make_scroll_canvas(900, 980, seed=77)
    d  = ImageDraw.Draw(img)
    cw = x2 - x1

    add_water_stain(img, n=6, seed=88)
    add_age_spots(img, count=40, seed=55)

    y = y1 + 10

    # Header
    hf = fnt('head', 20)
    label = "CONSIGNMENT LOG"
    d.text(((x1+x2-tw(d, label, hf))//2, y), label, font=hf, fill=BROWN)
    y += th(d, label, hf) + 6
    y = draw_rule(d, x1, y, x2) + 14

    cf = fnt('ital', 26)
    sf = fnt('body', 26)
    lh = th(d, "Xg", sf) + 10

    def entry(lbl, value, color_label=BROWN, color_val=INK, strike=False):
        nonlocal y
        d.text((x1, y), lbl, font=cf, fill=color_label)
        vx = x1 + tw(d, lbl, cf) + 10
        d.text((vx, y), value, font=sf, fill=color_val)
        if strike:
            my = y + lh // 2
            d.line([(x1, my), (x2, my)], fill=BROWN, width=2)
        y += lh

    entry("Date:",     "[17th Lamptide, Third Moon]",  BROWN, INK)
    entry("Contact:",  "K",                             BROWN, RED)
    entry("Quantity:", "8 (eight) tubes. conf.",         BROWN, INK)
    entry("Seal:",     "wax / bladder-skin / full",      BROWN, INK)
    entry("Dest.:",    "[the camp] / north road",        BROWN, INK)
    entry("Coach:",    "B. Tinderflip freight line",     BROWN, INK)
    y += 6
    y = draw_rule(d, x1, y, x2) + 10

    # Crossed-out older entry
    d.text((x1, y), "Prev. run:", font=cf, fill=PARCH_DARK)
    d.text((x1 + tw(d, "Prev. run:", cf) + 10, y),
           "6 t. / dest. S. [?]", font=sf, fill=PARCH_DARK)
    my = y + lh // 2 - 2
    d.line([(x1, my), (x2 - 40, my)], fill=BROWN, width=2)
    y += lh + 6

    nf = fnt('ital', 20)
    d.text((x1, y), "* rendezvous: one day after delivery.", font=nf, fill=BROWN)
    y += th(d, "X", nf) + 4
    d.text((x1, y), "* if K not present — leave with foreman.", font=nf, fill=BROWN)
    y += th(d, "X", nf) + 4

    # Ink smudge over part of last line
    smudge = Image.new('RGB', (200, 40), tuple(c - 22 for c in PARCH))
    smudge = smudge.filter(ImageFilter.GaussianBlur(8))
    img.paste(smudge, (x1 + cw // 3, y - lh * 2))

    img.save(OUT_DIR / "area2_coded_ledger.png")
    print("  area2_coded_ledger.png")


# ---------------------------------------------------------------------------
# Handout 3 — The Operative's Note (Area 6, found with Orn)
# ---------------------------------------------------------------------------
def make_orn_note():
    img, (x1, y1, x2, y2) = make_scroll_canvas(900, 1100, seed=33)
    d  = ImageDraw.Draw(img)
    cw = x2 - x1

    y = y1

    y = draw_weapon_icons(d, (x1+x2)//2, y) + 18

    hf = fnt('head', 18)
    label = "FOR THE ATTENTION OF THE RECEIVING PARTY"
    d.text(((x1+x2-tw(d, label, hf))//2, y), label, font=hf, fill=RED)
    y += th(d, label, hf) + 8
    y = draw_rule(d, x1, y, x2) + 18

    bf  = fnt('ital', 28)
    lh  = th(d, "Xg", bf) + 8

    paragraphs = [
        ("The second cache has been relocated. The original staging point "
         "— the camp supply shed — was compromised. "
         "These three tubes are the remainder."),
        ("The balance of the shipment moved north ahead of schedule. "
         "Find the cave and follow the markers."),
        ("Do not use the obsidian method of entry. That key is spent."),
    ]

    for para in paragraphs:
        y = draw_paragraph(d, para, x1, y, cw, bf, lh, y2,
                           dropcap=False, color=INK)
        y += lh // 2 + 6

    y += 14
    y = draw_rule(d, x1 + cw // 3, y, x1 + 2 * cw // 3) + 16

    # Wax seal — thumb only, no design
    seal_x = (x1 + x2) // 2
    seal_y = y + 30
    d.ellipse([seal_x-28, seal_y-28, seal_x+28, seal_y+28],
              fill=tuple(c - 30 for c in PARCH), outline=BROWN, width=2)
    for r in range(4, 18, 4):
        d.ellipse([seal_x-r, seal_y-r, seal_x+r, seal_y+r], outline=BROWN, width=1)
    ff = fnt('body', 13)
    note = "(no seal mark — pressed thumb only)"
    d.text(((x1+x2-tw(d, note, ff))//2, seal_y+34), note, font=ff, fill=PARCH_DARK)

    img.save(OUT_DIR / "area6_orn_note.png")
    print("  area6_orn_note.png")


# ---------------------------------------------------------------------------
# Handout 4 — The Ash Tongue Riddle (Area 7) — stone rubbing style
# ---------------------------------------------------------------------------
def make_ash_tongue_riddle():
    W, H = 920, 760
    # Stone background (dark, carved look)
    img = stone_texture(W, H, seed=19)
    img = add_vignette(img, strength=0.6)

    # Lighten center panel slightly
    d    = ImageDraw.Draw(img)
    cx, cy = W // 2, H // 2
    for r in range(120, 0, -1):
        alpha = int(12 * (1 - r / 120))
        d.ellipse([cx-r*3, cy-r*2, cx+r*3, cy+r*2],
                  outline=tuple(min(255, c + alpha) for c in STONE_LIGHT))

    # Outer border (double rule, carved look)
    d.rectangle([20, 20, W-20, H-20], outline=STONE_LIGHT, width=2)
    d.rectangle([28, 28, W-28, H-28], outline=STONE_LIGHT, width=1)

    # "OLD FLAN" header
    hf = fnt('head', 17)
    header = "—  Inscription Above the Ash Tongue Face  —"
    d.text(((W - tw(d, header, hf))//2, 40), header, font=hf, fill=STONE_CARVE)

    d.line([(60, 70), (W-60, 70)], fill=STONE_LIGHT, width=1)

    # The riddle — carved letter look (light on dark stone)
    rf  = fnt('ital', 38)
    lines = [
        "When white breath wears a mortal face,",
        "Seek not the height but hollow place.",
        "Turn the eye and still the tongue,",
        "There lies the path for old and young.",
    ]
    lh  = th(d, "Xg", rf) + 18
    ry  = 104

    for line in lines:
        lw = tw(d, line, rf)
        lx = (W - lw) // 2
        d.text((lx+2, ry+2), line, font=rf, fill=STONE)        # shadow
        d.text((lx,   ry),   line, font=rf, fill=STONE_CARVE)  # carved
        ry += lh

    ry += 14
    d.line([(60, ry), (W-60, ry)], fill=STONE_LIGHT, width=1)
    ry += 16

    # Scholar's gloss notes
    nf  = fnt('ital', 17)
    notes = [
        '"White breath wears a mortal face" — the plume of White Plume Mountain, visible at dusk.',
        '"Turn the eye and still the tongue" — the stone mechanism. Clockwise. Then hold silence.',
    ]
    for note in notes:
        lines_w = wrap(d, note, nf, W - 120)
        for ln in lines_w:
            d.text(((W - tw(d, ln, nf)) // 2, ry), ln, font=nf, fill=STONE_LIGHT)
            ry += th(d, ln, nf) + 6

    # Bottom rune-like marks
    rune_y = H - 56
    for i, glyph in enumerate(["|", "<|>", "|||", "<|>", "|"]):
        rx = W // 2 + (i - 2) * 48
        gf = fnt('head', 19)
        d.text((rx - tw(d, glyph, gf)//2, rune_y), glyph, font=gf, fill=STONE_LIGHT)

    img.save(OUT_DIR / "area7_ash_tongue_riddle.png")
    print("  area7_ash_tongue_riddle.png")


# ---------------------------------------------------------------------------
# Handout 5 — Bark Map to White Plume Mountain (Area 7)
# ---------------------------------------------------------------------------
def make_bark_map():
    W, H = 1050, 780
    # Bark texture base
    img = bark_texture(W, H, seed=3)
    img = add_vignette(img, strength=0.5)
    d   = ImageDraw.Draw(img)

    # Irregular torn border (rough outer edges suggesting cut bark)
    rng = random.Random(42)
    for side in range(4):
        for _ in range(80):
            if side == 0:  # top
                x = rng.randint(0, W); y = rng.randint(0, 12)
            elif side == 1:  # bottom
                x = rng.randint(0, W); y = rng.randint(H-12, H)
            elif side == 2:  # left
                x = rng.randint(0, 12); y = rng.randint(0, H)
            else:  # right
                x = rng.randint(W-12, W); y = rng.randint(0, H)
            d.ellipse([x-4, y-4, x+4, y+4], fill=BG)

    # Title
    tf  = fnt('bl', 26)
    title = "Route North"
    d.text(((W - tw(d, title, tf))//2, 18), title, font=tf, fill=(220,190,130))

    d.line([(60, 52), (W-60, 52)], fill=(140,100,40), width=1)
    d.line([(60, 55), (W-60, 55)], fill=(140,100,40), width=1)

    # Map elements — coordinate system
    # Start: bottom-center(ish), end: top-center (mountain)
    # Path winds N with branches and landmarks

    CREAM = (218, 188, 130)
    DARKINK = (40, 22, 6)

    lf  = fnt('ital', 18)
    lfs = fnt('ital', 15)
    lf2 = fnt('body', 16)

    def label(text, x, y, font=None, angle=0, color=CREAM):
        f = font or lf
        if angle != 0:
            # Render to temp image then rotate
            tw_ = tw(d, text, f) + 4
            th_ = th(d, text, f) + 4
            tmp = Image.new('RGBA', (tw_, th_), (0,0,0,0))
            td  = ImageDraw.Draw(tmp)
            td.text((2, 2), text, font=f, fill=color)
            tmp = tmp.rotate(angle, expand=True)
            img.paste(tmp, (int(x), int(y)), tmp)
        else:
            d.text((x, y), text, font=f, fill=color)

    def dot(x, y, r=5, col=None):
        c = col or (180, 140, 60)
        d.ellipse([x-r, y-r, x+r, y+r], fill=c, outline=DARKINK, width=1)

    def path_segment(pts, w=3):
        for i in range(len(pts)-1):
            d.line([pts[i], pts[i+1]], fill=(160, 120, 55), width=w)

    # ---- The route ----
    # Layout (W=1050, H=780):
    # South start: (~525, 700)
    # Iron-red spring: (~480, 580)
    # Dead ash fork: (~520, 440)
    #   East branch (correct): (~620, 360)
    #   West branch (wrong, fades): (~400, 380)
    # Entry stone: (~640, 250)
    # Sulphur vent / WPM entry: (~660, 130)
    # Mountain peak: (~660, 60)

    # Draw "south" label at start
    start = (525, 700)
    label("(start — the cave)", start[0]-70, start[1]+8, lfs)

    # Main path south to north
    main_path = [
        start,
        (510, 650), (500, 610), (485, 580),   # to spring
        (495, 545), (505, 510), (515, 475),    # after spring
        (520, 440),                             # fork
        (560, 415), (595, 390), (625, 365),    # east branch (correct)
        (638, 330), (645, 295), (648, 255),    # to entry stone
        (652, 220), (658, 185), (660, 150),    # to vent
        (660, 115), (660, 78),                 # to peak
    ]
    path_segment(main_path, w=3)

    # Wrong branch (fades, thinner)
    wrong_branch = [
        (520, 440), (490, 420), (460, 405), (420, 395), (395, 388),
    ]
    for i in range(len(wrong_branch)-1):
        alpha = int(160 * (1 - i / len(wrong_branch)))
        col = (alpha, int(alpha * 0.75), int(alpha * 0.34))
        d.line([wrong_branch[i], wrong_branch[i+1]], fill=col, width=2)

    # ---- Landmarks ----

    # 1. Iron-red spring (~485, 580)
    sx, sy = 485, 577
    dot(sx, sy, r=6, col=(160, 60, 30))
    # Spring symbol: wavy lines
    for wy in range(sy-4, sy+6, 3):
        for wx in range(sx-8, sx+8, 4):
            d.ellipse([wx, wy, wx+2, wy+2], fill=(160,60,30))
    label("the iron-red spring", sx - 130, sy - 8, lfs)

    # 2. Dead ash fork (~520, 440)
    fx, fy = 520, 440
    dot(fx, fy, r=5)
    # Fork symbol: Y shape
    d.line([(fx, fy-10), (fx, fy)],   fill=CREAM, width=2)
    d.line([(fx, fy), (fx-12, fy+10)], fill=(140,100,40), width=2)
    d.line([(fx, fy), (fx+15, fy+10)], fill=CREAM, width=2)
    label("dead ash — fork", fx - 128, fy - 18, lfs)
    label("→ take east", fx + 22, fy - 6, lfs, color=(200, 180, 100))
    # Wrong-branch label
    label("(wrong — fades)", 388, 395, lfs, color=(100,80,50))

    # 3. Entry stone (~648, 252)
    ex, ey = 648, 252
    dot(ex, ey, r=6)
    # Stone symbol: small upright rectangle
    d.rectangle([ex-5, ey-10, ex+5, ey+2], outline=CREAM, width=1)
    # K facing sunrise
    kf = fnt('bl', 14)
    d.text((ex-4, ey-10), "K", font=kf, fill=CREAM)
    label("entry stone — K faces sunrise", ex + 14, ey - 8, lfs)

    # 4. Sulphur vent (~660, 148)
    vx, vy = 660, 148
    dot(vx, vy, r=5, col=(130,160,30))
    # Vent: upward lines (smoke)
    for i in range(3):
        wx = vx - 6 + i * 6
        d.line([(wx, vy-2), (wx + rng.randint(-3,3), vy-14)],
               fill=(130,160,30), width=1)
    label("sulphur vent", vx + 12, vy - 8, lfs, color=(160,190,60))
    label("(no smoke from outside)", vx + 12, vy + 6, lfs, color=(130,160,30))

    # 5. Mountain at top
    mx, my = 660, 68
    # Triangle for peak
    d.polygon([(mx, my-28), (mx-30, my+12), (mx+30, my+12)], outline=CREAM, width=2)
    # Snow cap
    d.polygon([(mx, my-28), (mx-12, my-10), (mx+12, my-10)], fill=CREAM)
    mf = fnt('head', 13)
    label("WHITE PLUME MOUNTAIN", mx - 70, my + 16, mf, color=(210,200,170))

    # ---- Hours labels on path ----
    hour_labels = [
        ((498, 617), "~2 hrs"),
        ((515, 492), "~1.5 hrs"),
        ((590, 382), "~2 hrs"),
        ((648, 200), "~1.5 hrs"),
        ((660, 120), "~1 hr"),
    ]
    hf2 = fnt('ital', 14)
    for (hx, hy), htxt in hour_labels:
        label(htxt, hx + 6, hy, hf2, color=(160,140,90))

    # North arrow
    na_x, na_y = 90, 100
    d.polygon([(na_x, na_y-22), (na_x-8, na_y+8), (na_x, na_y+2),
               (na_x+8, na_y+8)], fill=CREAM, outline=DARKINK)
    nf = fnt('head', 14)
    label("N", na_x - 5, na_y - 40, nf, color=CREAM)
    d.line([(na_x, na_y-22), (na_x, na_y+8)], fill=CREAM, width=1)

    # ---- Annotation notes in multiple "hands" ----
    note1 = "third vent from east — confirmed safe"
    label(note1, vx - 210, vy - 32, fnt('ital', 14), color=(170,200,100))

    note2 = "spring runs red in dry season — still drinkable"
    label(note2, 290, 598, fnt('body', 14), color=(190,160,90))

    note3 = "entry stone: K carved 4 ft, faces east at equinox."
    label(note3, 670, 262, fnt('ital', 14), color=CREAM)

    # Scale note
    d.line([(W-220, H-50), (W-100, H-50)], fill=CREAM, width=1)
    d.line([(W-220, H-44), (W-220, H-56)], fill=CREAM, width=1)
    d.line([(W-100, H-44), (W-100, H-56)], fill=CREAM, width=1)
    label("≈ half-day travel", W-218, H-46, fnt('ital', 11))

    img.save(OUT_DIR / "area7_bark_map.png")
    print("  area7_bark_map.png")


# ---------------------------------------------------------------------------
# Handout 6 — Gnome Warning on Bark Strip (Area 7)
# ---------------------------------------------------------------------------
def make_gnome_warning():
    # Landscape bark strip
    W, H = 1000, 460
    img  = bark_texture(W, H, seed=7)
    img  = add_vignette(img, strength=0.52)
    add_age_spots(img, count=30, seed=61)

    d    = ImageDraw.Draw(img)

    rng = random.Random(14)
    for _ in range(240):
        x = rng.randint(0, W)
        for y_edge in [rng.randint(0, 12), rng.randint(H-12, H)]:
            d.ellipse([x-5, y_edge-5, x+5, y_edge+5], fill=BG)

    hf  = fnt('ital', 16)
    d.text((36, 18), "[written in careful Gnomish]", font=hf, fill=(148,124,72))

    d.line([(36, 42), (W-36, 42)], fill=(120,90,35), width=1)

    gf  = fnt('ital', 22)
    lh  = th(d, "Xg", gf) + 7

    text = (
        "The third vent from the east leads to the gathering chamber. "
        "The gathering chamber is not safe when the smoke is white above. "
        "Wait for the smoke to turn grey before entering from below. "
        "The gathering chamber floor is uneven and the gnomes who know "
        "the path are not always there. If you hear hammering below, "
        "do not call out — let it stop on its own."
    )

    MAX_W = W - 90
    lines = wrap(d, text, gf, MAX_W)
    ry    = 56

    for line in lines:
        wobble = rng.randint(-2, 2)
        d.text((44, ry + wobble), line, font=gf, fill=(218, 190, 124))
        ry += lh
        if ry > H - 54:
            break

    # Gnome handprint (berry-red)
    hp_x, hp_y = W - 68, H - 72
    d.ellipse([hp_x-15, hp_y-20, hp_x+15, hp_y+20],
              fill=(160, 58, 58), outline=(118, 38, 38), width=1)
    for i in range(5):
        angle = -60 + i * 30
        fx = hp_x + int(18 * math.cos(math.radians(angle)))
        fy = hp_y - 22 + int(6 * math.sin(math.radians(angle)))
        d.ellipse([fx-4, fy-6, fx+4, fy+6], fill=(160,58,58))

    cf = fnt('ital', 14)
    note = "(translation by Nib — or any gnome of the mountain lineage)"
    d.text(((W - tw(d, note, cf))//2, H - 26), note, font=cf, fill=(130,110,60))

    img.save(OUT_DIR / "area7_gnome_warning.png")
    print("  area7_gnome_warning.png")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
HANDOUTS = {
    "manifest": make_manifest,
    "ledger":   make_coded_ledger,
    "note":     make_orn_note,
    "riddle":   make_ash_tongue_riddle,
    "map":      make_bark_map,
    "gnome":    make_gnome_warning,
}

def main():
    try:
        from PIL import Image  # noqa: F401
    except ImportError:
        import os
        os.system(f"{sys.executable} -m pip install Pillow")

    OUT_DIR.mkdir(exist_ok=True)

    keys = sys.argv[1:] if len(sys.argv) > 1 else list(HANDOUTS)
    print("Generating handouts...")
    for key in keys:
        if key in HANDOUTS:
            HANDOUTS[key]()
        else:
            # Fuzzy match
            matches = [k for k in HANDOUTS if key.lower() in k]
            if matches:
                HANDOUTS[matches[0]]()
            else:
                print(f"  Unknown handout: {key}. Options: {list(HANDOUTS)}")

    print(f"\nSaved to {OUT_DIR}/")


if __name__ == "__main__":
    main()
