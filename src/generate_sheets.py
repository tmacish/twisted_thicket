#!/usr/bin/env python3
"""
AD&D 2e Character Sheet Generator — The Twisted Thicket
Authentic 1980s TSR aesthetic: parchment, fantasy fonts, red-and-brown borders.

Usage:
    python3 generate_sheets.py           # all characters -> sheets/
    python3 generate_sheets.py 01        # single character (by number prefix)

Requires: pip install reportlab
Fonts downloaded automatically to fonts/ on first run.
"""

import re
import os
import sys
import urllib.request
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ROOT            = Path(__file__).parent.parent   # the_twisted_thicket/ project root
CHAR_DIR        = ROOT / "characters"
FONTS_DIR       = ROOT / "fonts"
OUTPUT_DIR      = ROOT / "sheets"
BACKGROUNDS_DIR = ROOT / "handouts" / "player_backgrounds"

# ---------------------------------------------------------------------------
# Colour palette  (R, G, B  in  0.0–1.0)
# ---------------------------------------------------------------------------

C_PARCHMENT     = (0.961, 0.922, 0.788)   # aged cream
C_PARCHMENT_SHD = (0.886, 0.839, 0.694)   # slightly darker cream
C_INK           = (0.082, 0.039, 0.008)   # near-black
C_BORDER        = (0.400, 0.145, 0.035)   # dark saddle-brown
C_HEADING       = (0.530, 0.000, 0.020)   # dark blood-red
C_RULE          = (0.600, 0.440, 0.180)   # golden rule lines
C_SHADED_ROW    = (0.918, 0.875, 0.745)   # alternating row tint

# ---------------------------------------------------------------------------
# Font management
# ---------------------------------------------------------------------------

BASE = "https://raw.githubusercontent.com/google/fonts/main/ofl"

FONT_URLS = {
    # Cinzel (variable font — registers fine as-is; bold = same file at larger size)
    "Cinzel.ttf":
        f"{BASE}/cinzel/Cinzel%5Bwght%5D.ttf",
    # IM Fell English (actual filenames in the repo are abbreviated)
    "IMFell.ttf":
        f"{BASE}/imfellenglish/IMFeENrm28P.ttf",
    "IMFell-Italic.ttf":
        f"{BASE}/imfellenglish/IMFeENit28P.ttf",
    # UnifrakturMaguntia blackletter
    "Blackletter.ttf":
        f"{BASE}/unifrakturmaguntia/UnifrakturMaguntia-Book.ttf",
}

FONT_NAMES = {
    "Cinzel.ttf":        ("Cinzel", "Cinzel-Bold"),   # register same file under both names
    "IMFell.ttf":        ("IMFell",),
    "IMFell-Italic.ttf": ("IMFell-Italic",),
    "Blackletter.ttf":   ("Blackletter",),
}

_registered: set[str] = set()


def ensure_fonts() -> None:
    FONTS_DIR.mkdir(exist_ok=True)
    for fname, url in FONT_URLS.items():
        dest = FONTS_DIR / fname
        if dest.exists():
            continue
        print(f"  Downloading {fname} ...", end=" ", flush=True)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=20) as r:
                dest.write_bytes(r.read())
            print("ok")
        except Exception as exc:
            print(f"failed ({exc})")


def register_fonts() -> None:
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    for fname, regnames in FONT_NAMES.items():
        fpath = FONTS_DIR / fname
        if not fpath.exists():
            continue
        for regname in regnames:
            try:
                pdfmetrics.registerFont(TTFont(regname, str(fpath)))
                _registered.add(regname)
            except Exception:
                pass


def F(preferred: str, fallback: str) -> str:
    return preferred if preferred in _registered else fallback


def body() -> str:   return F("IMFell",       "Times-Roman")
def italic() -> str: return F("IMFell-Italic","Times-Italic")
def head() -> str:   return F("Cinzel-Bold",  "Times-Bold")
def bl() -> str:     return F("Blackletter",  "Times-BoldItalic")

# ---------------------------------------------------------------------------
# Markdown parser
# ---------------------------------------------------------------------------

def _clean(s: str) -> str:
    """Strip common markdown markup from a string."""
    s = re.sub(r'\*\*(.+?)\*\*', r'\1', s)
    s = re.sub(r'\*(.+?)\*',     r'\1', s)
    s = re.sub(r'`(.+?)`',       r'\1', s)
    return s.strip()


def parse_character(md_path: Path) -> dict:
    text = md_path.read_text(encoding="utf-8")
    char: dict = {"source": md_path.name}

    # H1: "Name, Race Class Level"
    m = re.match(r'#\s+(.+?),\s+(.+?)\s+(\d+)', text)
    if m:
        char["name"]  = m.group(1).strip()
        raw_cls       = m.group(2).strip()
        char["level"] = m.group(3).strip()
    else:
        char["name"], raw_cls, char["level"] = md_path.stem, "Unknown", "?"

    # Split race from class string (e.g. "Dwarf Fighter", "Human Paladin")
    race_m = re.match(r'(Human|Dwarf|Elf|Half.?Elf|Gnome|Halfling|Half.?Orc)\s+(.*)', raw_cls)
    if race_m:
        char["race"]  = race_m.group(1)
        char["class"] = race_m.group(2)
    else:
        char["race"]  = "Human"
        char["class"] = raw_cls

    # Opening italic description
    m = re.search(r'\n\*([^*].+?)\*\n', text, re.DOTALL)
    char["description"] = _clean(m.group(1)) if m else ""

    # Alignment
    aln_pat = (r'Lawful Good|Lawful Neutral|Lawful Evil|'
               r'Neutral Good|True Neutral|Neutral Evil|'
               r'Chaotic Good|Chaotic Neutral|Chaotic Evil')
    m = re.search(aln_pat, text)
    char["alignment"] = m.group(0) if m else ""

    # Ability scores table
    char["abilities"] = []
    sec = re.search(r'## Ability Scores\n\n(.+?)\n\n---', text, re.DOTALL)
    if sec:
        for row in re.finditer(
            r'^\|\s*([^|]+?)\s*\|\s*(\d+[/\d]*)\s*\|\s*([^|]*?)\s*\|',
            sec.group(1), re.MULTILINE
        ):
            name = row.group(1).strip()
            if name and name.lower() not in ("ability", "---"):
                char["abilities"].append({
                    "name":  name,
                    "score": row.group(2).strip(),
                    "notes": row.group(3).strip(),
                })

    # Combat statistics (key–value pairs before the Weapons table)
    char["combat"] = {}
    sec = re.search(r'## Combat Statistics\n\n(.+?)(?=\n\*\*Weapons|\n---|\n## )',
                    text, re.DOTALL)
    if sec:
        for kv in re.finditer(r'\*\*(.+?):\*\*\s*(.+)', sec.group(1)):
            key = kv.group(1).strip()
            val = re.sub(r'\s*\(.*?\)', '', kv.group(2)).strip()
            val = re.sub(r'\s*\*.*', '', val).strip()
            char["combat"][key] = val

    # Weapons table
    char["weapons"] = []
    sec = re.search(
        r'\| Weapon \|.+?\n\|[-| ]+\n((?:\|.+\n)+)', text
    )
    if sec:
        for row in re.finditer(r'^\|(.+?)\|(.+?)\|(.+?)\|(.+?)\|',
                               sec.group(1), re.MULTILINE):
            name = row.group(1).strip()
            if name and "---" not in name:
                char["weapons"].append({
                    "name":   name,
                    "to_hit": row.group(2).strip(),
                    "damage": row.group(3).strip(),
                    "notes":  row.group(4).strip(),
                })

    # Saving throws
    char["saves"] = []
    sec = re.search(r'\| Save \| Target \|\n\|[-| ]+\n((?:\|.+\n)+)', text)
    if sec:
        for row in re.finditer(r'^\|\s*(.+?)\s*\|\s*(\d+)\s*\|',
                               sec.group(1), re.MULTILINE):
            char["saves"].append({
                "name":   row.group(1).strip(),
                "target": row.group(2).strip(),
            })

    # Thief skills (Kaida only, but detect generically)
    char["thief_skills"] = []
    sec = re.search(r'## Thief Skills\n\n(.+?)(?=\n---|\n## )', text, re.DOTALL)
    if sec:
        for row in re.finditer(
            r'^\|\s*([^|]+?)\s*\|[^|]+\|[^|]+\|\s*(\d+%)\s*\|',
            sec.group(1), re.MULTILINE
        ):
            skill = row.group(1).strip()
            total = row.group(2).strip()
            if skill and skill.lower() not in ("skill", "---"):
                char["thief_skills"].append({"name": skill, "total": total})

    # Class-specific abilities (Bard, Ranger, Druid, Paladin, Cleric, Dwarf, Half-Elf)
    char["class_abilities"] = []
    for sec_m in re.finditer(
        r'## ((?:Bard|Ranger|Druid|Paladin|Cleric|Dwarf|Half.?Elf)\s+Abilities)\n\n(.+?)(?=\n---|\n## |\Z)',
        text, re.DOTALL
    ):
        title = sec_m.group(1).strip()
        sec_text = sec_m.group(2)
        items = []
        # Bullet format: "- **Name:** desc"
        for item in re.finditer(r'^-\s*\*\*([^*\n]+?):\*\*\s*(.+)', sec_text, re.MULTILINE):
            desc = _clean(item.group(2)).strip()
            if desc:
                items.append({"name": item.group(1).strip(), "desc": desc})
        # Paragraph format: "**Name:** desc\n\n**Next:** ..." (fallback if no bullets found)
        if not items:
            for item in re.finditer(
                r'\*\*([^*\n]+?):\*\*\s*(.+?)(?=\n\n\*\*|\Z)', sec_text, re.DOTALL
            ):
                desc = re.sub(r'\n', ' ', _clean(item.group(2)))
                desc = re.sub(r'\s+', ' ', desc).strip()
                if desc:
                    items.append({"name": item.group(1).strip(), "desc": desc})
        if items:
            char["class_abilities"].append({"title": title, "items": items})

    # Spells memorised
    char["spells"] = {}
    sec = re.search(r'## Spells Memoris[e|é]d\n\n(.+?)(?=\n---|\n## )', text, re.DOTALL)
    if sec:
        for blk in re.finditer(
            r'\*\*(\d+)(?:st|nd|rd|th) Level \((\d+) slots?\).*?\*\*[:\n]+((?:-[^\n]+\n?)+)',
            sec.group(1)
        ):
            lv    = int(blk.group(1))
            slots = blk.group(2)
            names = []
            for line in re.findall(r'^-\s*(.+)', blk.group(3), re.MULTILINE):
                m2 = re.match(r'([^*(×]+)', line)
                if m2:
                    names.append(m2.group(1).strip().rstrip(':').strip())
            char["spells"][lv] = {"slots": slots, "spells": names}

    # Turning Undead table (Cleric / Paladin)
    char["turning_undead"] = []
    sec = re.search(r'## Turning Undead\n\n(.+?)(?=\n---|\n## |\Z)', text, re.DOTALL)
    if sec:
        for row in re.finditer(
            r'^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|',
            sec.group(1), re.MULTILINE
        ):
            name   = row.group(1).strip()
            result = row.group(2).strip()
            if name and 'Undead' not in name and '---' not in name:
                char["turning_undead"].append({"type": name, "result": result})

    # Languages
    char["languages"] = []
    sec = re.search(r'## Languages\n\n(.+?)(?=\n---|\n## |\Z)', text, re.DOTALL)
    if sec:
        raw = _clean(sec.group(1).strip())
        char["languages"] = [l.strip() for l in re.split(r',', raw) if l.strip()]

    # Equipment block
    sec = re.search(r'## Equipment\n\n(.+?)(?=\n---|\n## )', text, re.DOTALL)
    char["equipment"] = _clean(sec.group(1)) if sec else ""

    # Magic items
    char["magic_items"] = []
    sec = re.search(r'## Magic Items\n\n(.+?)(?=\n---|\n## )', text, re.DOTALL)
    if sec:
        for item in re.finditer(
            r'\*\*(.+?)\*\*:?\s*(.+?)(?=\n\n\*\*|\Z)', sec.group(1), re.DOTALL
        ):
            desc = re.sub(r'\n', ' ', _clean(item.group(2)))
            desc = re.sub(r'\s+', ' ', desc).strip()
            char["magic_items"].append({"name": item.group(1).strip(), "desc": desc})

    # Personality bullets
    char["personality"] = []
    sec = re.search(r'## Personality\n\n(.+?)(?=\n---|\n## |\Z)', text, re.DOTALL)
    if sec:
        for b in re.findall(r'^-\s*(.+)', sec.group(1), re.MULTILINE):
            char["personality"].append(_clean(b))

    # Proficiencies
    char["proficiencies"] = {"weapon": [], "nonweapon": [], "bonus": ""}
    sec = re.search(r'## Proficiencies\n\n(.+?)(?=\n---|\n## |\Z)', text, re.DOTALL)
    if sec:
        m = re.search(r'\*\*Weapon Proficiencies:\*\*\s*(.+)', sec.group(1))
        if m:
            char["proficiencies"]["weapon"] = [p.strip() for p in m.group(1).split(',') if p.strip()]
        m = re.search(r'\*\*Non-Weapon Proficiencies \(Bonus\):\*\*\s*(.+)', sec.group(1))
        if m:
            char["proficiencies"]["bonus"] = _clean(m.group(1))
        nwp_m = re.search(r'\| Proficiency \|.+?\n\|[-| ]+\n((?:\|.+\n)+)', sec.group(1))
        if nwp_m:
            for row in re.finditer(
                r'^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*(\d+%?)\s*\|',
                nwp_m.group(1), re.MULTILINE
            ):
                name = row.group(1).strip()
                if name and '---' not in name:
                    char["proficiencies"]["nonweapon"].append({
                        "name":   name,
                        "ability": row.group(2).strip(),
                        "check":  row.group(3).strip(),
                    })

    return char

# ---------------------------------------------------------------------------
# Drawing helpers
# ---------------------------------------------------------------------------

def _sf(c, col):  c.setFillColorRGB(*col)
def _ss(c, col):  c.setStrokeColorRGB(*col)


def draw_parchment(c, W, H):
    _sf(c, C_PARCHMENT)
    c.rect(0, 0, W, H, fill=1, stroke=0)
    # Light vignette strips at edges
    _sf(c, C_PARCHMENT_SHD)
    for i in range(5):
        alpha_like = 0.15 - i * 0.025
        # Simulate with thin shaded rects
        _sf(c, (C_PARCHMENT_SHD[0], C_PARCHMENT_SHD[1] - i*0.01, C_PARCHMENT_SHD[2]))
        c.rect(0,           i * 8, W, 8, fill=1, stroke=0)
        c.rect(0, H - (i+1)*8, W, 8, fill=1, stroke=0)
    _sf(c, C_PARCHMENT)


def draw_border(c, x, y, w, h, lw=1.5, gap=3):
    """Double-rule border box."""
    _ss(c, C_BORDER)
    c.setLineWidth(lw)
    c.rect(x, y, w, h, stroke=1, fill=0)
    c.setLineWidth(0.4)
    c.rect(x + gap, y + gap, w - 2*gap, h - 2*gap, stroke=1, fill=0)


def draw_diamond(c, cx, cy, half=5):
    """Filled diamond ornament."""
    _sf(c, C_BORDER)
    p = c.beginPath()
    p.moveTo(cx, cy + half)
    p.lineTo(cx + half, cy)
    p.lineTo(cx, cy - half)
    p.lineTo(cx - half, cy)
    p.close()
    c.drawPath(p, fill=1, stroke=0)


def draw_page_border(c, W, H, M):
    """Full-page ornate double border with corner diamonds."""
    bx, by = M, M
    bw, bh = W - 2*M, H - 2*M

    _ss(c, C_BORDER)
    c.setLineWidth(2.0)
    c.rect(bx, by, bw, bh, stroke=1, fill=0)
    c.setLineWidth(0.6)
    c.rect(bx + 5, by + 5, bw - 10, bh - 10, stroke=1, fill=0)

    for dx, dy in ((bx, by), (bx+bw, by), (bx, by+bh), (bx+bw, by+bh)):
        draw_diamond(c, dx, dy, half=6)


def h_rule(c, x, y, w, double=False):
    _ss(c, C_RULE)
    c.setLineWidth(0.8)
    c.line(x, y, x + w, w + y - w)  # y only, horizontal
    c.line(x, y, x + w, y)
    if double:
        c.setLineWidth(0.3)
        c.line(x, y + 2, x + w, y + 2)


def section_bar(c, label, x, y, w, font_size=7):
    """Red header bar for a section."""
    bar_h = font_size + 6
    _sf(c, C_HEADING)
    c.rect(x + 2, y, w - 4, bar_h, fill=1, stroke=0)
    _sf(c, C_PARCHMENT)
    c.setFont(head(), font_size)
    c.drawCentredString(x + w / 2, y + 3.5, label.upper())
    return bar_h


def word_wrap(text: str, c, font: str, size: float, max_w: float) -> list[str]:
    lines, cur = [], ""
    for word in text.split():
        test = (cur + " " + word).strip()
        if c.stringWidth(test, font, size) <= max_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def clip_str(s: str, c, font: str, size: float, max_w: float) -> str:
    if c.stringWidth(s, font, size) <= max_w:
        return s
    while s and c.stringWidth(s + "...", font, size) > max_w:
        s = s[:-1]
    return s + "..."

# ---------------------------------------------------------------------------
# Section renderers  (each returns updated y after drawing)
# ---------------------------------------------------------------------------

def render_abilities(c, char, x, y, w) -> float:
    ROW_H = 15
    ab = char["abilities"]
    inner_h = ROW_H * len(ab) + 4
    bar_h = section_bar(c, "Ability Scores", x, y - 12, w)
    box_h = bar_h + 12 + inner_h
    draw_border(c, x, y - box_h, w, box_h, lw=1, gap=2)

    # Re-draw bar inside border
    section_bar(c, "Ability Scores", x, y - bar_h - 2, w)

    ry = y - bar_h - 2 - 10

    # Fixed left-justified columns: name | score box | notes
    NAME_W   = 80   # ability name column width
    SCORE_X  = x + NAME_W + 8   # left edge of score box
    SCORE_W  = 24
    NOTES_X  = SCORE_X + SCORE_W + 6
    NOTES_W  = w - (NOTES_X - x) - 6

    # Column headers
    _sf(c, C_INK)
    c.setFont(head(), 6.5)
    c.drawString(x + 5, ry, "Ability")
    c.drawCentredString(SCORE_X + SCORE_W / 2, ry, "Score")
    c.drawString(NOTES_X, ry, "Notes")
    _ss(c, C_RULE);  c.setLineWidth(0.5)
    c.line(x + 4, ry - 2, x + w - 4, ry - 2)
    ry -= ROW_H - 2

    for i, ab_row in enumerate(char["abilities"]):
        # Alternate shading
        if i % 2 == 1:
            _sf(c, C_SHADED_ROW)
            c.rect(x + 4, ry - 3, w - 8, ROW_H - 1, fill=1, stroke=0)

        _sf(c, C_INK)
        c.setFont(body(), 8)
        c.drawString(x + 5, ry, clip_str(ab_row["name"], c, body(), 8, NAME_W - 4))

        # Score in a small box
        _ss(c, C_BORDER);  c.setLineWidth(0.6)
        c.rect(SCORE_X, ry - 2, SCORE_W, 11, stroke=1, fill=0)
        _sf(c, C_HEADING)
        c.setFont(head(), 8.5)
        c.drawCentredString(SCORE_X + SCORE_W / 2, ry + 1, ab_row["score"])

        # Notes left-justified after score box
        notes = clip_str(ab_row["notes"], c, italic(), 6.5, NOTES_W)
        _sf(c, C_INK)
        c.setFont(italic(), 6.5)
        c.drawString(NOTES_X, ry, notes)

        ry -= ROW_H

    return y - box_h - 5


def render_saves(c, char, x, y, w) -> float:
    ROW_H = 13
    saves = char["saves"]
    if not saves:
        return y
    inner_h = ROW_H * len(saves) + 4
    bar_h = 13
    box_h = bar_h + 14 + inner_h
    draw_border(c, x, y - box_h, w, box_h, lw=1, gap=2)
    section_bar(c, "Saving Throws", x, y - bar_h - 2, w, font_size=7)

    ry = y - bar_h - 2 - 10
    for i, sv in enumerate(saves):
        if i % 2 == 1:
            _sf(c, C_SHADED_ROW)
            c.rect(x + 4, ry - 3, w - 8, ROW_H, fill=1, stroke=0)
        _sf(c, C_INK)
        c.setFont(body(), 7.5)
        c.drawString(x + 5, ry, sv["name"])

        tx = x + w - 22
        _ss(c, C_BORDER);  c.setLineWidth(0.6)
        c.rect(tx, ry - 2, 18, 11, stroke=1, fill=0)
        _sf(c, C_HEADING)
        c.setFont(head(), 8)
        c.drawCentredString(tx + 9, ry + 1, sv["target"])

        ry -= ROW_H

    return y - box_h - 5


def render_proficiencies(c, char, x, y, w) -> float:
    profs = char.get("proficiencies", {})
    wp    = profs.get("weapon", [])
    nwp   = profs.get("nonweapon", [])
    bonus = profs.get("bonus", "")
    if not wp and not nwp:
        return y

    FONT_SZ = 6.5
    LEADING  = 8.5
    ROW_H    = 10
    bar_h    = 13

    # Height: weapon line(s) + optional bonus line + NWP header row + NWP rows
    wp_text   = "WP: " + ", ".join(wp) if wp else ""
    wp_lines  = word_wrap(wp_text, c, body(), FONT_SZ, w - 10) if wp_text else []
    bonus_lines = word_wrap("Bonus: " + bonus, c, italic(), FONT_SZ, w - 10) if bonus else []
    nwp_rows  = len(nwp)
    header_h  = ROW_H if nwp else 0
    inner_h   = (len(wp_lines) * LEADING + (2 if wp_lines else 0) +
                 len(bonus_lines) * LEADING + (2 if bonus_lines else 0) +
                 header_h + ROW_H * nwp_rows + 4)
    box_h = bar_h + 14 + inner_h

    draw_border(c, x, y - box_h, w, box_h, lw=1, gap=2)
    section_bar(c, "Proficiencies", x, y - bar_h - 2, w, font_size=7)

    ry = y - bar_h - 2 - 10

    # Weapon proficiency line
    for i, line in enumerate(wp_lines):
        _sf(c, C_HEADING if i == 0 else C_INK)
        c.setFont(head() if i == 0 else body(), FONT_SZ)
        c.drawString(x + 5, ry, line)
        ry -= LEADING
    if wp_lines:
        ry -= 2

    # Bonus proficiencies (ranger tracking etc.)
    for i, line in enumerate(bonus_lines):
        _sf(c, C_INK)
        c.setFont(italic(), FONT_SZ)
        c.drawString(x + 5, ry, line)
        ry -= LEADING
    if bonus_lines:
        ry -= 2

    # NWP table
    if nwp:
        _sf(c, C_INK);  c.setFont(head(), 5.5)
        c.drawString(x + 5, ry, "NON-WEAPON PROFICIENCY")
        c.drawCentredString(x + w - 12, ry, "d%")
        _ss(c, C_RULE);  c.setLineWidth(0.4)
        c.line(x + 4, ry - 2, x + w - 4, ry - 2)
        ry -= ROW_H

        for i, prof in enumerate(nwp):
            if i % 2 == 1:
                _sf(c, C_SHADED_ROW)
                c.rect(x + 4, ry - 2, w - 8, ROW_H, fill=1, stroke=0)
            _sf(c, C_INK);  c.setFont(body(), FONT_SZ)
            c.drawString(x + 5, ry, clip_str(prof["name"], c, body(), FONT_SZ, w - 28))
            _sf(c, C_HEADING);  c.setFont(head(), 7)
            c.drawCentredString(x + w - 12, ry, prof["check"])
            ry -= ROW_H

    return y - box_h - 5


def render_combat(c, char, x, y, w) -> float:
    FIELDS = [
        ("Hit Points",          "HP"),
        ("Hit Die",             "Hit Die"),
        ("Armour Class",        "AC"),
        ("THAC0",               "THAC0"),
        ("Attacks per Round",   "Attacks/Rd"),
        ("Backstab",            "Backstab"),
        ("Movement",            "Movement"),
        ("Experience Points",   "XP"),
        ("Age",                 "Age"),
        ("Deity",               "Deity"),
    ]
    ROW_H = 14
    rows = [(label, char["combat"].get(key, "")) for key, label in FIELDS
            if key in char["combat"]]
    if not rows:
        return y
    bar_h = 13
    box_h = bar_h + 14 + ROW_H * len(rows) + 4
    draw_border(c, x, y - box_h, w, box_h, lw=1, gap=2)
    section_bar(c, "Combat Statistics", x, y - bar_h - 2, w, font_size=7)

    ry = y - bar_h - 2 - 10
    for label, val in rows:
        _sf(c, C_INK)
        c.setFont(head(), 7)
        label_w = c.stringWidth(label + ": ", head(), 7)
        c.drawString(x + 5, ry, label + ":")
        _sf(c, C_HEADING)
        c.setFont(body(), 8)
        c.drawString(x + 5 + label_w + 1, ry, val)
        ry -= ROW_H

    return y - box_h - 5


def render_weapons(c, char, x, y, w) -> float:
    weapons = char["weapons"]
    if not weapons:
        return y
    ROW_H = 11
    bar_h = 13
    box_h = bar_h + 14 + 10 + ROW_H * len(weapons) + 4
    draw_border(c, x, y - box_h, w, box_h, lw=1, gap=2)
    section_bar(c, "Weapons & Attacks", x, y - bar_h - 2, w, font_size=7)

    ry = y - bar_h - 2 - 10

    # Column proportions
    c1x = x + 5
    c2x = x + w * 0.45
    c3x = x + w * 0.60
    c4x = x + w * 0.73

    _sf(c, C_INK);  c.setFont(head(), 6)
    c.drawString(c1x, ry, "WEAPON")
    c.drawString(c2x, ry, "+HIT")
    c.drawString(c3x, ry, "DAMAGE")
    c.drawString(c4x, ry, "NOTES")
    _ss(c, C_RULE);  c.setLineWidth(0.5)
    c.line(x + 4, ry - 2, x + w - 4, ry - 2)
    ry -= ROW_H

    for i, wp in enumerate(weapons):
        if i % 2 == 1:
            _sf(c, C_SHADED_ROW)
            c.rect(x + 4, ry - 2, w - 8, ROW_H, fill=1, stroke=0)
        _sf(c, C_INK);  c.setFont(body(), 7)
        c.drawString(c1x, ry, clip_str(wp["name"],   c, body(), 7, c2x - c1x - 3))
        c.drawString(c2x, ry, clip_str(wp["to_hit"], c, body(), 7, c3x - c2x - 3))
        c.drawString(c3x, ry, clip_str(wp["damage"], c, body(), 7, c4x - c3x - 3))
        c.drawString(c4x, ry, clip_str(wp["notes"],  c, body(), 7, x + w - 4 - c4x))
        ry -= ROW_H

    return y - box_h - 5


def render_thief_skills(c, char, x, y, w) -> float:
    skills = char.get("thief_skills", [])
    if not skills:
        return y
    ROW_H = 11
    bar_h = 13
    # Two columns of skills
    mid = (len(skills) + 1) // 2
    col_rows = max(mid, len(skills) - mid)
    box_h = bar_h + 16 + ROW_H * col_rows + 4
    draw_border(c, x, y - box_h, w, box_h, lw=1, gap=2)
    section_bar(c, "Thief Skills", x, y - bar_h - 2, w, font_size=7)

    ry = y - bar_h - 2 - 10
    half_w = (w - 12) / 2

    for i, sk in enumerate(skills):
        col = 0 if i < mid else 1
        row = i if col == 0 else i - mid
        rx = x + 5 + col * (half_w + 6)
        ry_row = ry - row * ROW_H

        _sf(c, C_INK);  c.setFont(body(), 7)
        c.drawString(rx, ry_row, sk["name"])
        _sf(c, C_HEADING);  c.setFont(head(), 7.5)
        tw = c.stringWidth(sk["total"], head(), 7.5)
        c.drawString(rx + half_w - tw - 2, ry_row, sk["total"])

    return y - box_h - 5


def render_class_abilities(c, char, x, y, w, max_h=180) -> float:
    sections = char.get("class_abilities", [])
    if not sections:
        return y
    FONT_SZ = 6.5
    LEADING  = 8.5
    bar_h    = 13

    # content entries: ("section"|"name"|"body", text)
    content: list[tuple[str, str]] = []
    for sec in sections:
        if len(sections) > 1:
            content.append(("section", sec["title"]))
        for item in sec["items"]:
            content.append(("name", item["name"] + ":"))
            for line in word_wrap(item["desc"], c, body(), FONT_SZ, w - 18):
                content.append(("body", "  " + line))
            content.append(("body", ""))

    box_h = min(bar_h + 16 + len(content) * LEADING + 4, max_h)
    draw_border(c, x, y - box_h, w, box_h, lw=1, gap=2)
    bar_label = "Abilities" if len(sections) > 1 else sections[0]["title"]
    section_bar(c, bar_label, x, y - bar_h - 2, w, font_size=7)

    ry = y - bar_h - 2 - 10
    stop_y = y - box_h + LEADING

    for kind, line in content:
        if ry < stop_y:
            break
        if kind == "body" and not line.strip():
            ry -= LEADING * 0.35
            continue
        if kind == "section":
            _sf(c, C_BORDER)
            c.setFont(head(), 6)
            c.drawString(x + 5, ry, line.upper())
            ry -= LEADING
        elif kind == "name":
            _sf(c, C_HEADING)
            c.setFont(head(), FONT_SZ)
            c.drawString(x + 5, ry, line)
            ry -= LEADING
        else:
            _sf(c, C_INK)
            c.setFont(body(), FONT_SZ)
            c.drawString(x + 5, ry, line)
            ry -= LEADING

    return y - box_h - 5


def render_turning_undead(c, char, x, y, w) -> float:
    rows = char.get("turning_undead", [])
    if not rows:
        return y
    ROW_H = 11
    bar_h = 13
    mid = (len(rows) + 1) // 2
    col_rows = max(mid, len(rows) - mid)
    box_h = bar_h + 14 + ROW_H * (col_rows + 1) + 4
    draw_border(c, x, y - box_h, w, box_h, lw=1, gap=2)
    section_bar(c, "Turn Undead", x, y - bar_h - 2, w, font_size=7)

    ry      = y - bar_h - 2 - 10
    half_w  = (w - 12) / 2
    res_off = half_w * 0.70

    _sf(c, C_INK);  c.setFont(head(), 5.5)
    c.drawString(x + 5,                           ry, "UNDEAD TYPE")
    c.drawString(x + 5 + res_off,                 ry, "RESULT")
    c.drawString(x + 5 + half_w + 6,              ry, "UNDEAD TYPE")
    c.drawString(x + 5 + half_w + 6 + res_off,    ry, "RESULT")
    _ss(c, C_RULE);  c.setLineWidth(0.4)
    c.line(x + 4, ry - 2, x + w - 4, ry - 2)
    ry -= ROW_H

    for i, entry in enumerate(rows):
        col = 0 if i < mid else 1
        row = i if col == 0 else i - mid
        rx      = x + 5 + col * (half_w + 6)
        ry_row  = ry - row * ROW_H
        _sf(c, C_INK);  c.setFont(body(), 7)
        c.drawString(rx, ry_row, entry["type"])
        _sf(c, C_HEADING);  c.setFont(head(), 7.5)
        c.drawString(rx + res_off, ry_row, entry["result"])

    return y - box_h - 5


def render_spells(c, char, x, y, w) -> float:
    spells = char.get("spells", {})
    if not spells:
        return y
    LEVEL_H = 12
    SPELL_H = 10
    bar_h = 13
    total_lines = sum(1 + len(d["spells"]) for d in spells.values())
    box_h = bar_h + 16 + LEVEL_H * len(spells) + SPELL_H * total_lines + 8
    box_h = min(box_h, 200)

    draw_border(c, x, y - box_h, w, box_h, lw=1, gap=2)
    section_bar(c, "Spells Memorised", x, y - bar_h - 2, w, font_size=7)

    ORDINALS = {1:"1st", 2:"2nd", 3:"3rd", 4:"4th", 5:"5th", 6:"6th"}
    ry = y - bar_h - 2 - LEVEL_H - 2
    stop_y = y - box_h + SPELL_H

    for lv, data in sorted(spells.items()):
        if ry < stop_y:
            break
        lv_label = f"{ORDINALS.get(lv, str(lv)+'th')} Level  ({data['slots']} slots)"
        _sf(c, C_BORDER)
        c.rect(x + 4, ry - 1, w - 8, LEVEL_H, fill=1, stroke=0)
        _sf(c, C_PARCHMENT);  c.setFont(head(), 6.5)
        c.drawString(x + 8, ry + 3, lv_label)
        ry -= LEVEL_H + 2

        spell_list = data["spells"]
        mid = (len(spell_list) + 1) // 2
        col_w = (w - 14) / 2
        col_top = ry

        for i, name in enumerate(spell_list):
            if ry < stop_y:
                break
            col = 0 if i < mid else 1
            row = i if col == 0 else i - mid
            rx = x + 6 + col * col_w
            r_y = col_top - row * SPELL_H
            _sf(c, C_INK);  c.setFont(body(), 7)
            c.drawString(rx, r_y, "- " + name)

        rows_drawn = max(mid, len(spell_list) - mid)
        ry = col_top - rows_drawn * SPELL_H - 3

    return y - box_h - 5


def render_languages(c, char, x, y, w) -> float:
    langs = char.get("languages", [])
    if not langs:
        return y
    FONT_SZ = 6.5
    LEADING  = 8.5
    bar_h    = 13
    text = ", ".join(langs)
    lines = word_wrap(text, c, body(), FONT_SZ, w - 10)
    box_h = bar_h + 14 + len(lines) * LEADING + 4
    draw_border(c, x, y - box_h, w, box_h, lw=1, gap=2)
    section_bar(c, "Languages", x, y - bar_h - 2, w, font_size=7)
    ry = y - bar_h - 2 - 10
    for line in lines:
        _sf(c, C_INK)
        c.setFont(body(), FONT_SZ)
        c.drawString(x + 5, ry, line)
        ry -= LEADING
    return y - box_h - 5


# ---------------------------------------------------------------------------
# Ability modifiers quick-reference
# ---------------------------------------------------------------------------

def _dex_reaction_adj(score: int) -> int:
    if score <= 3:  return -3
    if score == 4:  return -2
    if score == 5:  return -1
    if score <= 15: return 0
    if score == 16: return +1
    if score == 17: return +2
    if score == 18: return +2
    return +3


def extract_key_mods(char: dict) -> list[tuple[str, str]]:
    """Pull combat-relevant modifiers from ability notes for at-a-glance display."""
    result = []
    for ab in char.get("abilities", []):
        name  = ab["name"]
        score = ab.get("score", "10")
        notes = _clean(ab.get("notes", ""))

        if name == "Strength":
            parts = []
            m = re.search(r'([+-]\d+)\s+to\s+hit', notes, re.I)
            if m and int(m.group(1)) != 0: parts.append(f"Hit {m.group(1)}")
            m = re.search(r'([+-]\d+)\s+damage', notes, re.I)
            if m and int(m.group(1)) != 0: parts.append(f"Dmg {m.group(1)}")
            if parts: result.append(("STR", "  ".join(parts)))

        elif name == "Dexterity":
            try:   dex = int(str(score).split('/')[0])
            except ValueError: dex = 10
            parts = []
            react = _dex_reaction_adj(dex)
            if react != 0: parts.append(f"Init {react:+d}")
            m = re.search(r'([+-]\d+)\s+missile', notes, re.I)
            if m: parts.append(f"Miss {m.group(1)}")
            m = re.search(r'([+-]\d+)\s*AC|AC\s*([+-]\d+)', notes, re.I)
            if m:
                val = m.group(1) or m.group(2)
                parts.append(f"AC {val}")
            if parts: result.append(("DEX", "  ".join(parts)))

        elif name == "Constitution":
            m = re.search(r'([+-]\d+)\s+hp', notes, re.I)
            if m: result.append(("CON", f"HP/die {m.group(1)}"))

        elif name == "Wisdom":
            m = re.search(r'([+-]\d+)\s+magical\s+def', notes, re.I)
            if m: result.append(("WIS", f"Magic Def {m.group(1)}"))

        elif name == "Charisma":
            m = re.search(r'[Rr]eaction\s*([+-]\d+)|([+-]\d+)\s*[Rr]eaction', notes)
            if m:
                val = m.group(1) or m.group(2)
                result.append(("CHA", f"Reaction {val}"))

    return result


def render_ability_mods(c, char, x, y, w) -> float:
    mods = extract_key_mods(char)
    if not mods:
        return y
    FONT_SZ = 7
    LEADING = 10
    bar_h   = 13
    LABEL_W = 28
    box_h = bar_h + 12 + len(mods) * LEADING + 4
    draw_border(c, x, y - box_h, w, box_h, lw=1, gap=2)
    section_bar(c, "Ability Modifiers", x, y - bar_h - 2, w, font_size=7)
    ry = y - bar_h - 2 - 10
    for ability, mod_text in mods:
        _sf(c, C_HEADING);  c.setFont(head(), FONT_SZ)
        c.drawString(x + 5, ry, ability + ":")
        _sf(c, C_INK);  c.setFont(body(), FONT_SZ)
        c.drawString(x + 5 + LABEL_W, ry, mod_text)
        ry -= LEADING
    return y - box_h - 5


def render_current_hp(c, char, x, y, w) -> float:
    max_hp = char.get("combat", {}).get("Hit Points", "")
    bar_h  = 13
    cell_h = 18
    box_h  = bar_h + 10 + cell_h + 14
    draw_border(c, x, y - box_h, w, box_h, lw=1, gap=2)
    section_bar(c, "Current Hit Points", x, y - bar_h - 2, w, font_size=7)

    ry   = y - bar_h - 2 - 8
    half = (w - 14) / 2

    for i, (label, val) in enumerate([("MAX", max_hp), ("CURRENT", "")]):
        cell_x = x + 5 + i * (half + 2)
        _ss(c, C_BORDER);  c.setLineWidth(0.8)
        c.rect(cell_x, ry - cell_h, half - 2, cell_h, stroke=1, fill=0)
        if val:
            _sf(c, C_HEADING);  c.setFont(head(), 11)
            c.drawCentredString(cell_x + (half - 2) / 2, ry - 13, val)
        _sf(c, C_INK);  c.setFont(body(), 5.5)
        c.drawCentredString(cell_x + (half - 2) / 2, ry - cell_h - 6, label)

    return y - box_h - 5


def render_thac0_matrix(c, char, x, y, w) -> float:
    thac0_raw = char.get("combat", {}).get("THAC0", "")
    m_t   = re.match(r'(\d+)', str(thac0_raw))
    thac0 = int(m_t.group(1)) if m_t else None

    ACS     = list(range(10, -6, -1))   # AC 10 down to -5
    n       = len(ACS)
    bar_h   = 13
    row_h   = 12
    label_w = 34
    col_w   = (w - label_w - 10) / n
    box_h   = bar_h + 8 + row_h * 2 + 8

    draw_border(c, x, y - box_h, w, box_h, lw=1, gap=2)
    lbl = "To Hit Matrix" + (f"  (THAC0 {thac0})" if thac0 else "")
    section_bar(c, lbl, x, y - bar_h - 2, w, font_size=7)

    ry      = y - bar_h - 2 - 5
    cell_x0 = x + label_w

    # Row 1: AC header cells (shaded)
    _sf(c, C_INK);  c.setFont(head(), 6)
    c.drawString(x + 5, ry + 2, "AC")
    for i, ac in enumerate(ACS):
        cx = cell_x0 + i * col_w
        _sf(c, C_PARCHMENT_SHD)
        c.rect(cx, ry - 2, col_w - 1, row_h, fill=1, stroke=0)
        _ss(c, C_RULE);  c.setLineWidth(0.3)
        c.rect(cx, ry - 2, col_w - 1, row_h, stroke=1, fill=0)
        _sf(c, C_BORDER);  c.setFont(head(), 6)
        c.drawCentredString(cx + (col_w - 1) / 2, ry + 2, str(ac))
    ry -= row_h + 3

    # Row 2: roll needed
    _sf(c, C_INK);  c.setFont(head(), 6)
    c.drawString(x + 5, ry, "Need")
    for i, ac in enumerate(ACS):
        cx = cell_x0 + i * col_w
        if thac0 is not None:
            roll = thac0 - ac
            if roll <= 1:   roll_str, hard = "1",   False
            elif roll > 20: roll_str, hard = "--",  True
            else:           roll_str, hard = str(roll), roll >= 17
        else:
            roll_str, hard = "", False
        _sf(c, C_HEADING if hard else C_INK)
        c.setFont(head() if hard else body(), 6.5)
        c.drawCentredString(cx + (col_w - 1) / 2, ry, roll_str)

    return y - box_h - 5


def render_equipment(c, char, x, y, w, max_h=120) -> float:
    text = char.get("equipment", "")
    if not text:
        return y
    FONT_SZ = 7
    LEADING  = 9
    bar_h    = 10
    # Build wrapped lines
    lines = []
    for raw in text.split("\n"):
        raw = raw.strip()
        if not raw:
            continue
        # Bold category label handling: "Worn: ..." → "Worn: ..."
        m = re.match(r'\*\*(.+?):\*\*\s*(.*)', raw)
        if m:
            raw = m.group(1) + ": " + m.group(2)
        lines.extend(word_wrap(raw, c, body(), FONT_SZ, w - 12))

    box_h = min(bar_h + 16 + len(lines) * LEADING + 4, max_h)
    draw_border(c, x, y - box_h, w, box_h, lw=1, gap=2)
    section_bar(c, "Equipment", x, y - bar_h - 2, w, font_size=7)

    ry = y - bar_h - 2 - 10
    stop_y = y - box_h + LEADING

    for line in lines:
        if ry < stop_y:
            break
        # Category labels in bold-ish color
        _sf(c, C_HEADING if re.match(r'(Worn|Pack|Coin):', line) else C_INK)
        c.setFont(body(), FONT_SZ)
        c.drawString(x + 5, ry, line)
        ry -= LEADING

    return y - box_h - 5


def render_magic_items(c, char, x, y, w, max_h=150) -> float:
    items = char.get("magic_items", [])
    if not items:
        return y
    FONT_SZ = 6.5
    LEADING  = 8.5
    bar_h    = 10

    # Build line list: (bold?, text)
    content: list[tuple[bool, str]] = []
    for item in items:
        content.append((True, item["name"] + ":"))
        for line in word_wrap(item["desc"], c, body(), FONT_SZ, w - 18):
            content.append((False, "  " + line))
        content.append((False, ""))  # gap

    box_h = min(bar_h + 16 + len(content) * LEADING + 4, max_h)
    draw_border(c, x, y - box_h, w, box_h, lw=1, gap=2)
    section_bar(c, "Magic Items", x, y - bar_h - 2, w, font_size=7)

    ry = y - bar_h - 2 - 10
    stop_y = y - box_h + LEADING

    for bold, line in content:
        if ry < stop_y:
            break
        if not line.strip():
            ry -= LEADING * 0.35
            continue
        _sf(c, C_HEADING if bold else C_INK)
        c.setFont(head() if bold else body(), FONT_SZ)
        c.drawString(x + 5, ry, line)
        ry -= LEADING

    return y - box_h - 5


def render_personality(c, char, x, y, w, max_h=90) -> float:
    bullets = char.get("personality", [])[:3]
    if not bullets:
        return y
    FONT_SZ = 6.5
    LEADING  = 8.5
    bar_h    = 10

    lines: list[str] = []
    for b in bullets:
        lines.extend(word_wrap("- " + b, c, italic(), FONT_SZ, w - 12))

    box_h = min(bar_h + 16 + len(lines) * LEADING + 4, max_h)
    draw_border(c, x, y - box_h, w, box_h, lw=1, gap=2)
    section_bar(c, "Personality", x, y - bar_h - 2, w, font_size=7)

    ry = y - bar_h - 2 - 10
    stop_y = y - box_h + LEADING

    for line in lines:
        if ry < stop_y:
            break
        _sf(c, C_INK);  c.setFont(italic(), FONT_SZ)
        c.drawString(x + 5, ry, line)
        ry -= LEADING

    return y - box_h - 5

# ---------------------------------------------------------------------------
# Full page composition
# ---------------------------------------------------------------------------

MARGIN = 32


def draw_sheet(char: dict, c):
    from reportlab.lib.pagesizes import LETTER
    W, H = LETTER

    draw_parchment(c, W, H)
    draw_page_border(c, W, H, MARGIN)

    IW = W - 2 * MARGIN   # inner width
    LX = MARGIN + 7       # left content edge

    TOP = H - MARGIN - 8  # top of usable content area

    # ---- TOP GAME TITLE BAR ----
    _sf(c, C_BORDER)
    c.rect(LX, TOP - 14, IW - 14, 14, fill=1, stroke=0)
    _sf(c, C_PARCHMENT)
    c.setFont(head(), 6.5)
    c.drawCentredString(W / 2, TOP - 10.5,
        "THE TWISTED THICKET    *    AD&D 2ND EDITION    *    CHARACTER RECORD SHEET")

    # ---- CHARACTER NAME (blackletter, large) ----
    name_y = TOP - 14
    _sf(c, C_PARCHMENT_SHD)
    c.rect(LX, name_y - 26, IW - 14, 26, fill=1, stroke=0)
    _ss(c, C_BORDER);  c.setLineWidth(0.8)
    c.rect(LX, name_y - 26, IW - 14, 26, stroke=1, fill=0)
    draw_diamond(c, LX + 14, name_y - 13, half=5)
    draw_diamond(c, LX + IW - 28, name_y - 13, half=5)

    _sf(c, C_INK)
    c.setFont(head(), 20)
    c.drawCentredString(W / 2, name_y - 20, char.get("name", "Unknown"))

    # ---- INFO BAR: class / race / level / alignment ----
    info_y = name_y - 26
    _sf(c, C_HEADING)
    c.rect(LX, info_y - 13, IW - 14, 13, fill=1, stroke=0)
    _sf(c, C_PARCHMENT)
    c.setFont(head(), 7)
    parts = []
    if char.get("class"):     parts.append(f"Class: {char['class']}")
    parts.append(f"Race: {char.get('race', 'Human')}")
    if char.get("level"):     parts.append(f"Level: {char['level']}")
    if char.get("alignment"): parts.append(f"Alignment: {char['alignment']}")
    c.drawCentredString(W / 2, info_y - 10, "  |  ".join(parts))

    current_y = info_y - 13 - 6

    # ---- TWO-COLUMN LAYOUT ----
    col_w  = (IW - 14 - 8) // 2
    LEFT_W = col_w
    RIGHT_W = col_w
    RIGHT_X = LX + LEFT_W + 8

    left_y  = current_y
    right_y = current_y

    left_y  = render_abilities(c, char, LX,     left_y,  LEFT_W)
    left_y -= 3
    left_y  = render_saves(c, char, LX,         left_y,  LEFT_W)
    if char.get("proficiencies", {}).get("weapon") or char.get("proficiencies", {}).get("nonweapon"):
        left_y -= 3
        left_y = render_proficiencies(c, char, LX, left_y, LEFT_W)
    if char.get("languages"):
        left_y -= 3
        left_y = render_languages(c, char, LX, left_y, LEFT_W)

    right_y = render_combat(c, char, RIGHT_X,   right_y, RIGHT_W)
    right_y -= 3
    right_y = render_current_hp(c, char, RIGHT_X, right_y, RIGHT_W)
    if extract_key_mods(char):
        right_y -= 3
        right_y = render_ability_mods(c, char, RIGHT_X, right_y, RIGHT_W)
    right_y -= 3
    right_y = render_weapons(c, char, RIGHT_X,  right_y, RIGHT_W)
    if char.get("thief_skills"):
        right_y -= 3
        right_y = render_thief_skills(c, char, RIGHT_X, right_y, RIGHT_W)
    if char.get("turning_undead"):
        right_y -= 3
        right_y = render_turning_undead(c, char, RIGHT_X, right_y, RIGHT_W)

    bottom_y = min(left_y, right_y) - 6
    FULL_W = IW - 14

    # THAC0 matrix (full width)
    bottom_y = render_thac0_matrix(c, char, LX, bottom_y, FULL_W)
    bottom_y -= 4

    # Spells (casters only)
    if char.get("spells"):
        bottom_y = render_spells(c, char, LX, bottom_y, FULL_W)
        bottom_y -= 4

    # Equipment
    bottom_y = render_equipment(c, char, LX, bottom_y, FULL_W)
    bottom_y -= 4

    # Magic items + personality side by side if space allows
    remaining = bottom_y - (MARGIN + 14)
    if remaining > 36:
        mi_w   = FULL_W * 0.60
        pers_w = FULL_W * 0.37
        pers_x = LX + mi_w + 7

        render_magic_items( c, char, LX,     bottom_y, mi_w,   max_h=remaining)
        render_personality( c, char, pers_x, bottom_y, pers_w, max_h=remaining)

    # ---- FOOTER ----
    _sf(c, C_BORDER)
    c.setFont(body(), 5.5)
    c.drawCentredString(W / 2, MARGIN + 4,
        f"The Twisted Thicket  *  {char.get('name','')}  "
        f"*  {char.get('class','')} {char.get('level','')}")

# ---------------------------------------------------------------------------
# Background sheet — parser
# ---------------------------------------------------------------------------

def parse_background(md_path: Path) -> dict:
    text = md_path.read_text(encoding="utf-8")
    bg: dict = {"source": md_path.name}

    # H1: character name
    m = re.match(r'#\s+(.+)', text)
    bg["name"] = m.group(1).strip() if m else md_path.stem

    # H3: "Race Class — Your Background"
    m = re.search(r'###\s+(.+?)\s*—\s*Your Background', text)
    bg["subtitle"] = m.group(1).strip() if m else ""

    # Split on horizontal rules to get content blocks
    blocks = re.split(r'\n---\n', text)
    sections: list[dict] = []
    intro_set = False

    for block in blocks:
        block = block.strip()
        if not block:
            continue
        if block.startswith('#'):
            continue  # title block

        # Section with a ### heading?
        m = re.match(r'###\s+(.+?)\n+([\s\S]+)', block)
        if m:
            heading = m.group(1).strip()
            content = m.group(2).strip()
            sections.append({"heading": heading, "content": content})
        elif not intro_set:
            bg["intro"] = block
            intro_set = True

    bg["sections"] = sections
    return bg


# ---------------------------------------------------------------------------
# Background sheet — renderers
# ---------------------------------------------------------------------------

def _render_prose_block(c, text: str, x: float, y: float, w: float,
                        font_size: float = 7.5, leading: float = 9.5,
                        use_italic: bool = False) -> float:
    """Render flowing prose inside an already-drawn box. Returns new y."""
    fnt = italic() if use_italic else body()
    stop_y = y - 600  # hard floor; caller constrains box_h
    for para in text.split('\n\n'):
        para = _clean(para.strip())
        if not para:
            y -= leading * 0.5
            continue
        for line in word_wrap(para, c, fnt, font_size, w - 12):
            if y < stop_y:
                break
            _sf(c, C_INK)
            c.setFont(fnt, font_size)
            c.drawString(x + 6, y, line)
            y -= leading
        y -= leading * 0.4   # paragraph gap
    return y


def render_bg_section(c, heading: str, content: str,
                      x: float, y: float, w: float,
                      bottom_limit: float) -> float:
    """Draw one prose section with a header bar. Returns y after the box."""
    FONT_SZ = 7.5
    LEADING  = 9.5
    bar_h    = 10

    # Estimate line count
    all_lines: list[str] = []
    for para in content.split('\n\n'):
        para = _clean(para.strip())
        if para:
            all_lines.extend(word_wrap(para, c, body(), FONT_SZ, w - 12))
            all_lines.append('')
    while all_lines and not all_lines[-1]:
        all_lines.pop()

    if not all_lines:
        return y

    raw_h = bar_h + 14 + len(all_lines) * LEADING + 4
    available = y - bottom_limit
    box_h = min(raw_h, available - 4)
    if box_h < bar_h + 18:
        return y  # not enough room

    draw_border(c, x, y - box_h, w, box_h, lw=1, gap=2)
    section_bar(c, heading, x, y - bar_h - 2, w, font_size=7)

    ry = y - bar_h - 2 - 10
    stop_ry = y - box_h + LEADING

    for line in all_lines:
        if ry < stop_ry:
            break
        if not line:
            ry -= LEADING * 0.4
            continue
        _sf(c, C_INK)
        c.setFont(body(), FONT_SZ)
        c.drawString(x + 6, ry, line)
        ry -= LEADING

    return y - box_h - 5


def draw_background_sheet(bg: dict, c, char: dict | None = None) -> None:
    from reportlab.lib.pagesizes import LETTER
    W, H = LETTER

    draw_parchment(c, W, H)
    draw_page_border(c, W, H, MARGIN)

    IW  = W - 2 * MARGIN
    LX  = MARGIN + 7
    TOP = H - MARGIN - 8

    # ---- DETACHABLE MARKER ----
    _ss(c, C_RULE)
    c.setLineWidth(0.4)
    c.setDash([3, 3], 0)
    c.line(LX, TOP - 3, LX + IW - 14, TOP - 3)
    c.setDash()
    _sf(c, C_RULE)
    c.setFont(body(), 5.5)
    c.drawCentredString(W / 2, TOP - 8.5,
        "- - - - - - -  PLAYER HANDOUT  /  DETACH AND KEEP  - - - - - - -")

    # ---- HEADER BAR ----
    _sf(c, C_BORDER)
    c.rect(LX, TOP - 24, IW - 14, 13, fill=1, stroke=0)
    _sf(c, C_PARCHMENT)
    c.setFont(head(), 6.5)
    c.drawCentredString(W / 2, TOP - 20,
        "THE TWISTED THICKET    *    PLAYER BACKGROUND    *    THE TWISTED THICKET")

    # ---- CHARACTER NAME ----
    name_y = TOP - 24
    _sf(c, C_PARCHMENT_SHD)
    c.rect(LX, name_y - 26, IW - 14, 26, fill=1, stroke=0)
    _ss(c, C_BORDER)
    c.setLineWidth(0.8)
    c.rect(LX, name_y - 26, IW - 14, 26, stroke=1, fill=0)
    draw_diamond(c, LX + 14,       name_y - 13, half=5)
    draw_diamond(c, LX + IW - 28,  name_y - 13, half=5)
    _sf(c, C_INK)
    c.setFont(head(), 20)
    c.drawCentredString(W / 2, name_y - 20, bg.get("name", ""))

    # ---- SUBTITLE BAR ----
    sub_y = name_y - 26
    _sf(c, C_HEADING)
    c.rect(LX, sub_y - 13, IW - 14, 13, fill=1, stroke=0)
    _sf(c, C_PARCHMENT)
    c.setFont(head(), 7)
    c.drawCentredString(W / 2, sub_y - 10, bg.get("subtitle", ""))

    current_y = sub_y - 13 - 8
    FULL_W    = IW - 14
    BOTTOM    = MARGIN + 16

    # ---- INTRO (italic, borderless) ----
    intro = bg.get("intro", "")
    if intro:
        FONT_SZ = 7.5
        LEADING  = 9.5
        _sf(c, C_PARCHMENT_SHD)
        # draw a thin tinted band behind the intro
        intro_lines: list[str] = []
        for para in intro.split('\n\n'):
            para = _clean(para.strip())
            if para:
                intro_lines.extend(word_wrap(para, c, italic(), FONT_SZ, FULL_W - 12))
                intro_lines.append('')
        while intro_lines and not intro_lines[-1]:
            intro_lines.pop()

        band_h = len(intro_lines) * LEADING + 10
        c.rect(LX, current_y - band_h, FULL_W, band_h, fill=1, stroke=0)
        _ss(c, C_RULE)
        c.setLineWidth(0.4)
        c.rect(LX, current_y - band_h, FULL_W, band_h, stroke=1, fill=0)

        iy = current_y - 6
        for line in intro_lines:
            if not line:
                iy -= LEADING * 0.4
                continue
            _sf(c, C_INK)
            c.setFont(italic(), FONT_SZ)
            c.drawString(LX + 6, iy, line)
            iy -= LEADING

        current_y = current_y - band_h - 8

    # ---- SECTIONS ----
    for section in bg.get("sections", []):
        if current_y < BOTTOM + 30:
            break
        current_y = render_bg_section(
            c, section["heading"], section["content"],
            LX, current_y, FULL_W, BOTTOM
        )
        current_y -= 4

    # ---- CLASS ABILITIES (Bard, Ranger, etc.) ----
    if char and char.get("class_abilities") and current_y > BOTTOM + 30:
        remaining = current_y - BOTTOM - 16
        current_y = render_class_abilities(c, char, LX, current_y, FULL_W, max_h=remaining)

    # ---- FOOTER ----
    _sf(c, C_BORDER)
    c.setFont(body(), 5.5)
    c.drawCentredString(W / 2, MARGIN + 4,
        f"The Twisted Thicket  *  {bg.get('name', '')}  *  Player Background")


# ---------------------------------------------------------------------------
# Blank character sheet template
# ---------------------------------------------------------------------------

BLANK_CHAR: dict = {
    "name":        "___________________________",
    "class":       "_________________",
    "race":        "___________",
    "level":       "__",
    "alignment":   "___________________",
    "description": "",
    "abilities": [
        {"name": "Strength",     "score": "__", "notes": ""},
        {"name": "Dexterity",    "score": "__", "notes": ""},
        {"name": "Constitution", "score": "__", "notes": ""},
        {"name": "Intelligence", "score": "__", "notes": ""},
        {"name": "Wisdom",       "score": "__", "notes": ""},
        {"name": "Charisma",     "score": "__", "notes": ""},
    ],
    "combat": {
        "Hit Points":        "___",
        "Hit Die":           "___",
        "Armour Class":      "___",
        "THAC0":             "___",
        "Attacks per Round": "___",
        "Movement":          "___",
        "Experience Points": "________ / ________",
        "Age":               "___",
    },
    "weapons": [
        {"name": "____________________", "to_hit": "___", "damage": "______", "notes": ""},
        {"name": "____________________", "to_hit": "___", "damage": "______", "notes": ""},
        {"name": "____________________", "to_hit": "___", "damage": "______", "notes": ""},
    ],
    "saves": [
        {"name": "Death / Poison", "target": "__"},
        {"name": "Wands",          "target": "__"},
        {"name": "Paralyzation",   "target": "__"},
        {"name": "Breath Weapon",  "target": "__"},
        {"name": "Spells",         "target": "__"},
    ],
    "thief_skills":    [],
    "class_abilities": [],
    "turning_undead":  [],
    "spells":          {},
    "languages":       [],
    "equipment":       "Worn: _______________________________________________\nPack: _______________________________________________\nCoin: _______________________",
    "magic_items":     [],
    "personality":     [],
    "proficiencies": {
        "weapon":    ["_____________", "_____________", "_____________"],
        "nonweapon": [
            {"name": "____________________", "ability": "_______", "check": "___%"},
            {"name": "____________________", "ability": "_______", "check": "___%"},
            {"name": "____________________", "ability": "_______", "check": "___%"},
            {"name": "____________________", "ability": "_______", "check": "___%"},
        ],
        "bonus": "",
    },
}

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def _find_background(char_stem: str) -> Path | None:
    """Return the matching background md for a character file stem, or None."""
    prefix = char_stem[:2]
    matches = list(BACKGROUNDS_DIR.glob(f"{prefix}_*background*.md"))
    return matches[0] if matches else None


def generate_sheet(md_path: Path, out_dir: Path) -> None:
    from reportlab.pdfgen import canvas as cv
    from reportlab.lib.pagesizes import LETTER
    char = parse_character(md_path)
    out  = out_dir / f"{md_path.stem}_sheet.pdf"
    c = cv.Canvas(str(out), pagesize=LETTER)
    c.setTitle(f"{char.get('name','Character')} — The Twisted Thicket")
    draw_sheet(char, c)

    bg_path = _find_background(md_path.stem)
    if bg_path:
        c.showPage()
        draw_background_sheet(parse_background(bg_path), c, char=char)

    c.save()
    print(f"  {out.name}"  + (" (+background)" if bg_path else ""))


def main():
    # Ensure reportlab
    try:
        import reportlab  # noqa: F401
    except ImportError:
        print("Installing reportlab...")
        os.system(f"{sys.executable} -m pip install reportlab")

    print("AD&D 2e Sheet Generator — The Twisted Thicket")
    print("-" * 46)
    print("Checking fonts...")
    ensure_fonts()
    register_fonts()
    if _registered:
        print(f"  Loaded: {', '.join(sorted(_registered))}")
    else:
        print("  No custom fonts; using built-in Times.")

    OUTPUT_DIR.mkdir(exist_ok=True)

    # Determine targets
    args = sys.argv[1:]

    if args and args[0] == "blank":
        from reportlab.pdfgen import canvas as cv
        from reportlab.lib.pagesizes import LETTER
        out = OUTPUT_DIR / "blank_sheet.pdf"
        c = cv.Canvas(str(out), pagesize=LETTER)
        c.setTitle("Blank Character Sheet - The Twisted Thicket")
        draw_sheet(BLANK_CHAR, c)
        c.save()
        print(f"\n  {out.name}")
        print(f"\nSheets saved to {OUTPUT_DIR}/")
        return

    if args:
        prefix = args[0].zfill(2)
        files = sorted(CHAR_DIR.glob(f"{prefix}_*.md"))
    else:
        files = sorted(f for f in CHAR_DIR.glob("[0-9][0-9]_*.md")
                       if not f.stem.startswith("00"))

    if not files:
        print(f"No character files found in {CHAR_DIR}")
        sys.exit(1)

    print(f"\nGenerating {len(files)} sheet(s)...")
    for f in files:
        generate_sheet(f, OUTPUT_DIR)

    print(f"\nSheets saved to {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
