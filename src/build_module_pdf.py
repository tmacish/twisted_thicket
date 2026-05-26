#!/usr/bin/env python3
"""
build_module_pdf.py
TSR 1st-Edition-style module PDF for The Twisted Thicket.
Personal use only.
"""

import re, io
from pathlib import Path
from PIL import Image as PILImage, ImageEnhance

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer,
    Image as RLImage, PageBreak, Table, TableStyle,
    KeepTogether, NextPageTemplate, CondPageBreak,
)
from reportlab.platypus.flowables import Flowable
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE   = Path('/home/tjmcdon/RPG/Code/the_twisted_thicket')
FONTS  = BASE / 'fonts'
IMAGES = BASE / 'images'
OUTPUT = BASE / 'the_twisted_thicket_module.pdf'

# ---------------------------------------------------------------------------
# Page geometry  (US Letter)
# ---------------------------------------------------------------------------
PW, PH = letter          # 612 x 792 pt
ML  = 0.72 * inch
MR  = 0.72 * inch
MT  = 0.88 * inch        # leaves room for running header
MB  = 0.70 * inch
GAP = 0.22 * inch
CW  = (PW - ML - MR - GAP) / 2   # ~3.31 in per column
CH  = PH - MT - MB                # column height

# ---------------------------------------------------------------------------
# Colour palette  (TSR 1E orange-cover style)
# ---------------------------------------------------------------------------
TSR_ORANGE    = colors.Color(0.820, 0.370, 0.098)
TSR_ORANGE_DK = colors.Color(0.520, 0.210, 0.038)
CREAM         = colors.Color(0.940, 0.922, 0.868)
BACK_CREAM    = colors.Color(0.878, 0.845, 0.780)
DARK_INK      = colors.Color(0.065, 0.048, 0.022)
BOX_BG        = colors.Color(0.872, 0.850, 0.790)
BOX_BORDER    = colors.Color(0.230, 0.140, 0.042)
RULE_COL      = colors.Color(0.200, 0.120, 0.025)
GOLD          = colors.Color(0.980, 0.900, 0.620)
GOLD_DIM      = colors.Color(0.870, 0.760, 0.430)

# ---------------------------------------------------------------------------
# Fonts
# ---------------------------------------------------------------------------
def register_fonts():
    pdfmetrics.registerFont(TTFont('IMFell',      str(FONTS / 'IMFell.ttf')))
    pdfmetrics.registerFont(TTFont('IMFellI',     str(FONTS / 'IMFell-Italic.ttf')))
    pdfmetrics.registerFont(TTFont('Cinzel',      str(FONTS / 'Cinzel.ttf')))
    pdfmetrics.registerFont(TTFont('Blackletter', str(FONTS / 'Blackletter.ttf')))
    pdfmetrics.registerFontFamily('IMFell',
        normal='IMFell', italic='IMFellI', bold='Cinzel', boldItalic='IMFellI')

# ---------------------------------------------------------------------------
# Paragraph styles
# ---------------------------------------------------------------------------
def build_styles():
    S = {}
    def mk(name, **kw):
        base = kw.pop('parent', None)
        st = ParagraphStyle(name, parent=S.get(base))
        for k, v in kw.items():
            setattr(st, k, v)
        S[name] = st
        return st

    mk('body',  fontName='IMFell', fontSize=9.4, leading=13.2,
       textColor=DARK_INK, alignment=TA_JUSTIFY,
       spaceBefore=3, spaceAfter=2, firstLineIndent=11)
    mk('body0', parent='body', firstLineIndent=0)   # first para in section
    mk('ra',    fontName='IMFellI', fontSize=9, leading=12.8,
       textColor=DARK_INK, alignment=TA_JUSTIFY,
       firstLineIndent=0, spaceBefore=1, spaceAfter=1,
       leftIndent=5, rightIndent=5)
    mk('h1',    fontName='Cinzel', fontSize=14, leading=17,
       textColor=DARK_INK, alignment=TA_CENTER,
       spaceBefore=12, spaceAfter=6, firstLineIndent=0)
    mk('h2',    fontName='Cinzel', fontSize=11, leading=13.5,
       textColor=DARK_INK, alignment=TA_LEFT,
       spaceBefore=9, spaceAfter=3, firstLineIndent=0)
    mk('h3',    fontName='Cinzel', fontSize=9.4, leading=12,
       textColor=DARK_INK, alignment=TA_LEFT,
       spaceBefore=6, spaceAfter=2, firstLineIndent=0)
    mk('bullet',fontName='IMFell', fontSize=9.4, leading=12.8,
       textColor=DARK_INK, alignment=TA_JUSTIFY,
       firstLineIndent=0, leftIndent=13, spaceBefore=1, spaceAfter=1)
    mk('tc',    fontName='IMFell', fontSize=8.4, leading=11,
       textColor=DARK_INK, firstLineIndent=0)
    mk('th',    fontName='Cinzel', fontSize=7.8, leading=10,
       textColor=DARK_INK, alignment=TA_CENTER, firstLineIndent=0)
    mk('cap',   fontName='IMFellI', fontSize=7.8, leading=10,
       textColor=DARK_INK, alignment=TA_CENTER, firstLineIndent=0,
       spaceBefore=2, spaceAfter=2)
    return S

# ---------------------------------------------------------------------------
# Custom flowables
# ---------------------------------------------------------------------------

class ReadAloudBox(Flowable):
    PAD = 6
    def __init__(self, paras, w):
        super().__init__()
        self._paras = paras
        self._w = w

    def wrap(self, aW, aH):
        w = min(self._w, aW)
        iw = w - 2 * self.PAD
        h = 2 * self.PAD + 2
        for p in self._paras:
            _, ph = p.wrap(iw, 9999)
            h += ph + p.style.spaceBefore + p.style.spaceAfter
        self.__rw, self.__rh = w, h
        return w, h

    def draw(self):
        c, w, h = self.canv, self.__rw, self.__rh
        c.setFillColor(BOX_BG);  c.setStrokeColor(BOX_BORDER)
        c.setLineWidth(0.8);     c.rect(0, 0, w, h, fill=1, stroke=1)
        c.setLineWidth(0.25)
        c.line(3, h-4, w-3, h-4);  c.line(3, 3, w-3, 3)
        y = h - self.PAD
        iw = w - 2 * self.PAD
        for p in self._paras:
            _, ph = p.wrapOn(c, iw, 9999)
            y -= ph + p.style.spaceBefore
            p.drawOn(c, self.PAD, y)
            y -= p.style.spaceAfter


class SecRule(Flowable):
    def __init__(self, w, thick=0.6, double=True):
        super().__init__()
        self._w = w; self.thick = thick; self.double = double
    def wrap(self, aW, aH):
        self.__rw = min(self._w, aW)
        return self.__rw, 7
    def draw(self):
        c = self.canv; w = self.__rw
        c.setStrokeColor(RULE_COL)
        c.setLineWidth(self.thick); c.line(0, 4, w, 4)
        if self.double:
            c.setLineWidth(0.25); c.line(0, 1.5, w, 1.5)


# ---------------------------------------------------------------------------
# Inline markdown to ReportLab XML
# ---------------------------------------------------------------------------
_ESC = str.maketrans({'&': '&amp;', '<': '&lt;', '>': '&gt;'})

def mdi(text):
    t = text.translate(_ESC)
    t = re.sub(r'\*\*\*(.*?)\*\*\*', r'<font name="Cinzel" size="8.5"><i>\1</i></font>', t)
    t = re.sub(r'\*\*(.*?)\*\*',     r'<font name="Cinzel" size="8.8">\1</font>', t)
    t = re.sub(r'\*((?!\s)[^*\n]+?(?<!\s))\*', r'<i>\1</i>', t)
    t = re.sub(r'`([^`]+)`', r'<font name="Courier" size="8">\1</font>', t)
    return t


# ---------------------------------------------------------------------------
# Markdown file parser
# ---------------------------------------------------------------------------
def parse_file(path, styles):
    return parse_text(Path(path).read_text(encoding='utf-8'), styles)


def parse_text(text, styles):
    lines  = text.split('\n')
    out    = []
    i      = 0
    fresh  = True   # first para after heading gets no indent

    def add(f): out.append(f)

    while i < len(lines):
        ln = lines[i]

        # blank
        if not ln.strip():
            i += 1; continue

        # H1
        if re.match(r'^# [^#]', ln):
            add(Spacer(1, 5))
            add(Paragraph(mdi(ln[2:].strip()), styles['h1']))
            add(SecRule(CW, thick=1.0))
            add(Spacer(1, 3))
            fresh = True; i += 1; continue

        # H2
        if re.match(r'^## [^#]', ln):
            add(Spacer(1, 3))
            add(Paragraph(mdi(ln[3:].strip()), styles['h2']))
            add(SecRule(CW, thick=0.5, double=False))
            add(Spacer(1, 2))
            fresh = True; i += 1; continue

        # H3
        if re.match(r'^### [^#]', ln):
            add(Paragraph(mdi(ln[4:].strip()), styles['h3']))
            fresh = True; i += 1; continue

        # H4+
        if re.match(r'^#{4,}', ln):
            txt = re.sub(r'^#+\s*', '', ln)
            add(Paragraph('<font name="Cinzel" size="9">' + mdi(txt) + '</font>',
                          styles['body0']))
            fresh = True; i += 1; continue

        # HR
        if ln.strip() in ('---', '***', '___'):
            add(SecRule(CW, thick=0.4, double=True))
            add(Spacer(1, 3))
            i += 1; continue

        # Blockquote (read-aloud)
        if ln.startswith('>'):
            bq = []
            while i < len(lines) and lines[i].startswith('>'):
                bq.append(lines[i].lstrip('> ').rstrip())
                i += 1
            paras, cur = [], []
            for bl in bq:
                if not bl.strip():
                    if cur: paras.append(' '.join(cur)); cur = []
                else:
                    cur.append(bl)
            if cur: paras.append(' '.join(cur))
            rp = [Paragraph(mdi(p), styles['ra']) for p in paras if p.strip()]
            if rp:
                add(Spacer(1, 3))
                add(ReadAloudBox(rp, CW))
                add(Spacer(1, 3))
            fresh = True; continue

        # Table
        if ln.startswith('|'):
            rows = []
            while i < len(lines) and lines[i].startswith('|'):
                rows.append(lines[i]); i += 1
            tdata = []
            hdr = True
            for row in rows:
                if re.match(r'^\|[-: |]+\|$', row.strip()): continue
                cells = [c.strip() for c in row.strip().strip('|').split('|')]
                st = styles['th'] if hdr else styles['tc']
                tdata.append([Paragraph(mdi(c), st) for c in cells])
                hdr = False
            if tdata:
                nc = max(len(r) for r in tdata)
                cw = CW / nc
                t = Table(tdata, colWidths=[cw]*nc)
                t.setStyle(TableStyle([
                    ('BACKGROUND',  (0,0), (-1,0),  BOX_BG),
                    ('LINEBELOW',   (0,0), (-1,0),  0.5, RULE_COL),
                    ('ROWBACKGROUNDS',(0,1),(-1,-1),[CREAM, BOX_BG]),
                    ('GRID',        (0,0), (-1,-1), 0.25,
                     colors.Color(0.55, 0.42, 0.28)),
                    ('LEFTPADDING', (0,0), (-1,-1), 3),
                    ('RIGHTPADDING',(0,0), (-1,-1), 3),
                    ('TOPPADDING',  (0,0), (-1,-1), 2),
                    ('BOTTOMPADDING',(0,0),(-1,-1), 2),
                    ('VALIGN',      (0,0), (-1,-1), 'TOP'),
                ]))
                add(Spacer(1,3)); add(t); add(Spacer(1,3))
            fresh = True; continue

        # Unordered list
        if re.match(r'^[-*+] ', ln):
            while i < len(lines) and re.match(r'^[-*+] ', lines[i]):
                add(Paragraph('• ' + mdi(lines[i][2:].strip()),
                               styles['bullet']))
                i += 1
            fresh = True; continue

        # Ordered list
        if re.match(r'^\d+\. ', ln):
            n = 1
            while i < len(lines) and re.match(r'^\d+\. ', lines[i]):
                txt = re.sub(r'^\d+\. ', '', lines[i]).strip()
                add(Paragraph(f'<font name="Cinzel" size="8">{n}.</font> '
                               + mdi(txt), styles['bullet']))
                n += 1; i += 1
            fresh = True; continue

        # Regular paragraph — collect continuation lines
        pl = [ln.rstrip()]; i += 1
        while i < len(lines):
            nx = lines[i]
            if (not nx.strip() or nx.startswith('#') or nx.startswith('|')
                    or nx.startswith('>') or re.match(r'^[-*+] ', nx)
                    or re.match(r'^\d+\.', nx) or nx.strip() in ('---','***','___')):
                break
            pl.append(nx.rstrip()); i += 1
        pt_text = ' '.join(pl).strip()
        if pt_text:
            st = styles['body0'] if fresh else styles['body']
            add(Paragraph(mdi(pt_text), st))
            fresh = False

    return out


# ---------------------------------------------------------------------------
# Blueprint map
# ---------------------------------------------------------------------------
def make_blueprint(src, dst):
    img = PILImage.open(src).convert('RGBA')
    bg  = PILImage.new('RGBA', img.size, (255,255,255,255))
    bg.paste(img, mask=img.split()[3])
    rgb = ImageEnhance.Contrast(bg.convert('RGB')).enhance(1.4)
    r, g, b = rgb.split()
    bp = PILImage.merge('RGB', (
        r.point(lambda v: int(v*0.16 + 6)),
        g.point(lambda v: int(v*0.36 + 20)),
        b.point(lambda v: int(v*0.60 + 95)),
    ))
    bp.save(dst, 'PNG')


# ---------------------------------------------------------------------------
# Page callbacks
# ---------------------------------------------------------------------------

def cb_interior(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(CREAM)
    canvas.rect(0, 0, PW, PH, fill=1, stroke=0)
    # Running header
    canvas.setFont('Cinzel', 7.4)
    canvas.setFillColor(DARK_INK)
    canvas.drawString(ML, PH - 0.52*inch, 'TTT-1  •  THE TWISTED THICKET')
    canvas.setFont('IMFell', 7.4)
    canvas.drawRightString(PW - MR, PH - 0.52*inch, str(doc.page))
    canvas.setStrokeColor(RULE_COL)
    canvas.setLineWidth(0.8); canvas.line(ML, PH-0.59*inch, PW-MR, PH-0.59*inch)
    canvas.setLineWidth(0.25); canvas.line(ML, PH-0.62*inch, PW-MR, PH-0.62*inch)
    # Footer
    canvas.setLineWidth(0.5)
    canvas.line(ML, MB - 0.10*inch, PW-MR, MB - 0.10*inch)
    canvas.setFont('IMFellI', 6.2)
    canvas.setFillColor(colors.Color(0.35, 0.22, 0.08))
    canvas.drawCentredString(PW/2, MB - 0.25*inch, 'For Personal Use Only')
    canvas.restoreState()


def cb_map(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(CREAM)
    canvas.rect(0, 0, PW, PH, fill=1, stroke=0)
    canvas.setFont('Cinzel', 7.4)
    canvas.setFillColor(DARK_INK)
    canvas.drawCentredString(PW/2, PH - 0.50*inch, 'TTT-1  •  THE TWISTED THICKET')
    canvas.setFont('IMFell', 7.4)
    canvas.drawRightString(PW - MR, PH - 0.50*inch, str(doc.page))
    canvas.setStrokeColor(RULE_COL)
    canvas.setLineWidth(0.5); canvas.line(ML, PH-0.57*inch, PW-MR, PH-0.57*inch)
    canvas.restoreState()


def cb_cover(canvas, doc):
    canvas.saveState()

    # Orange fill
    canvas.setFillColor(TSR_ORANGE)
    canvas.rect(0, 0, PW, PH, fill=1, stroke=0)

    # Outer double border
    canvas.setStrokeColor(DARK_INK)
    canvas.setLineWidth(2.8)
    canvas.rect(0.24*inch, 0.24*inch, PW-0.48*inch, PH-0.48*inch, fill=0, stroke=1)
    canvas.setLineWidth(0.7)
    canvas.rect(0.33*inch, 0.33*inch, PW-0.66*inch, PH-0.66*inch, fill=0, stroke=1)

    # Top banner
    bh = 0.58*inch
    by = PH - 0.33*inch - bh
    canvas.setFillColor(DARK_INK)
    canvas.rect(0.33*inch, by, PW-0.66*inch, bh, fill=1, stroke=0)
    canvas.setFillColor(colors.white)
    canvas.setFont('Cinzel', 9.2)
    canvas.drawCentredString(PW/2, by + 0.35*inch, 'ADVANCED DUNGEONS & DRAGONS')
    canvas.setFont('IMFellI', 7.2)
    canvas.drawCentredString(PW/2, by + 0.16*inch, 'Role Playing Game Supplement')
    canvas.setFont('Cinzel', 7.8)
    canvas.drawString(0.44*inch, by + 0.25*inch, 'MODULE TTT-1')

    # Artwork frame
    ax = 0.44*inch;  aw = PW - 0.88*inch
    ay = by - 0.12*inch - 3.55*inch;  ah = 3.55*inch
    canvas.setFillColor(DARK_INK)
    canvas.rect(ax-3, ay-3, aw+6, ah+6, fill=1, stroke=0)
    canvas.drawImage(str(IMAGES/'twistedthicket.png'),
                     ax, ay, width=aw, height=ah,
                     preserveAspectRatio=True, anchor='c', mask='auto')

    # Title block background
    tb_y = ay - 0.20*inch - 1.52*inch;  tb_h = 1.52*inch
    canvas.setFillColor(TSR_ORANGE_DK)
    canvas.rect(0.33*inch, tb_y, PW-0.66*inch, tb_h, fill=1, stroke=0)

    # Gold rules
    canvas.setStrokeColor(GOLD)
    canvas.setLineWidth(1.6)
    canvas.line(0.46*inch, tb_y+tb_h-0.08*inch, PW-0.46*inch, tb_y+tb_h-0.08*inch)
    canvas.setLineWidth(0.4)
    canvas.line(0.46*inch, tb_y+tb_h-0.15*inch, PW-0.46*inch, tb_y+tb_h-0.15*inch)

    # Title
    canvas.setFillColor(GOLD)
    canvas.setFont('Blackletter', 33)
    canvas.drawCentredString(PW/2, tb_y + 0.92*inch, 'The Twisted Thicket')

    # Subtitle
    canvas.setFont('Cinzel', 9)
    canvas.setFillColor(GOLD_DIM)
    canvas.drawCentredString(PW/2, tb_y + 0.65*inch,
                             'An Adventure for 4-6 Characters, Levels 5-7')

    # Gold rules below subtitle
    canvas.setStrokeColor(GOLD)
    canvas.setLineWidth(0.4)
    canvas.line(0.46*inch, tb_y+0.50*inch, PW-0.46*inch, tb_y+0.50*inch)
    canvas.setLineWidth(1.6)
    canvas.line(0.46*inch, tb_y+0.43*inch, PW-0.46*inch, tb_y+0.43*inch)

    # Tagline
    canvas.setFont('IMFellI', 8.2)
    canvas.setFillColor(colors.Color(0.82, 0.72, 0.48))
    canvas.drawCentredString(PW/2, tb_y + 0.22*inch,
                             'OSRIC Compatible  —  A Prelude to White Plume Mountain')

    # Bottom bar
    bb_h = 0.48*inch
    canvas.setFillColor(DARK_INK)
    canvas.rect(0.33*inch, 0.33*inch, PW-0.66*inch, bb_h, fill=1, stroke=0)
    canvas.setFont('Cinzel', 11.5)
    canvas.setFillColor(colors.white)
    canvas.drawString(0.52*inch, 0.33*inch + 0.18*inch, 'TSR')
    canvas.setFont('IMFell', 7.5)
    canvas.drawString(0.52*inch + 0.44*inch, 0.33*inch + 0.18*inch, 'Games')
    canvas.setFont('IMFellI', 6.8)
    canvas.setFillColor(colors.Color(0.65, 0.65, 0.65))
    canvas.drawCentredString(PW/2, 0.33*inch + 0.18*inch,
                             'For Personal Use Only — Not for Distribution')

    canvas.restoreState()


def cb_back(canvas, doc):
    canvas.saveState()

    canvas.setFillColor(BACK_CREAM)
    canvas.rect(0, 0, PW, PH, fill=1, stroke=0)

    # Border
    canvas.setStrokeColor(DARK_INK)
    canvas.setLineWidth(2.8)
    canvas.rect(0.28*inch, 0.28*inch, PW-0.56*inch, PH-0.56*inch, fill=0, stroke=1)
    canvas.setLineWidth(0.6)
    canvas.rect(0.36*inch, 0.36*inch, PW-0.72*inch, PH-0.72*inch, fill=0, stroke=1)

    # Top panel
    tp_h = 1.30*inch
    tp_y = PH - 0.36*inch - tp_h
    canvas.setFillColor(TSR_ORANGE_DK)
    canvas.rect(0.36*inch, tp_y, PW-0.72*inch, tp_h, fill=1, stroke=0)
    canvas.setFillColor(GOLD)
    canvas.setFont('Blackletter', 24)
    canvas.drawCentredString(PW/2, tp_y + 0.76*inch, 'The Twisted Thicket')
    canvas.setFont('Cinzel', 7.8)
    canvas.setFillColor(GOLD_DIM)
    canvas.drawCentredString(PW/2, tp_y + 0.50*inch,
                             'MODULE TTT-1   •   LEVELS 5-7   •   4-6 PLAYERS')
    canvas.drawCentredString(PW/2, tp_y + 0.30*inch, 'OSRIC COMPATIBLE')

    # Town image
    iy  = tp_y - 0.08*inch - 2.20*inch
    ix  = 0.50*inch;  iw = PW - 1.00*inch;  ih = 2.20*inch
    canvas.setFillColor(DARK_INK)
    canvas.rect(ix-2, iy-2, iw+4, ih+4, fill=1, stroke=0)
    canvas.drawImage(str(IMAGES/'ringstown.png'),
                     ix, iy, width=iw, height=ih,
                     preserveAspectRatio=True, anchor='c', mask='auto')

    # Description text
    desc = (
        "North of the settled roadlands, agents of an ancient evil have been smuggling a "
        "refined magical stimulant through the Twisted Thicket. When a cargo wagon "
        "overturned in a ravine, an adult owlbear devoured the contents and was "
        "transformed. It now tears through the forest in bouts of ecstatic fury, "
        "trailing cold white sparks, while those who sample the dust experience "
        "terrible strength, obsession, and flashes of a hostile and alien intelligence.",
        "",
        "The characters are hired to enter the Thicket, stop the killings, and recover "
        "or destroy any contraband. Their investigation leads through seven connected "
        "locations: a wrecked smuggler's wagon, a damaged logging camp, a corrupted "
        "woodland pool, a thorn-choked hollow, and finally a cave that opens onto "
        "something much larger than a single forest.",
        "",
        "This module is designed as a compact single-session outdoor adventure and as a "
        "prologue to White Plume Mountain. It includes a complete wandering encounter "
        "table and full sequel hooks.",
    )
    dx = 0.52*inch;  dw = PW - 1.04*inch
    dy = iy - 0.22*inch
    canvas.setFont('IMFell', 8.5)
    canvas.setFillColor(DARK_INK)
    for para in desc:
        if not para:
            dy -= 7; continue
        words = para.split()
        line = ''
        for w in words:
            test = (line + ' ' + w).strip()
            if canvas.stringWidth(test, 'IMFell', 8.5) > dw:
                canvas.drawString(dx, dy, line); dy -= 12.5; line = w
            else:
                line = test
        if line:
            canvas.drawString(dx, dy, line); dy -= 12.5

    # Info strip
    is_y = 1.06*inch
    canvas.setFillColor(TSR_ORANGE)
    canvas.rect(0.50*inch, is_y, PW-1.00*inch, 0.58*inch, fill=1, stroke=0)
    canvas.setFont('IMFell', 8.2)
    canvas.setFillColor(DARK_INK)
    canvas.drawString(0.65*inch, is_y+0.36*inch,
                      'For use with the OSRIC rules system (AD&D 1st Edition compatible)')
    canvas.drawString(0.65*inch, is_y+0.17*inch,
                      'Suitable for 4-6 players  •  Characters of levels 5-7')

    # Bottom bar
    canvas.setFillColor(DARK_INK)
    canvas.rect(0.36*inch, 0.36*inch, PW-0.72*inch, 0.50*inch, fill=1, stroke=0)
    canvas.setFont('Cinzel', 10)
    canvas.setFillColor(colors.white)
    canvas.drawString(0.52*inch, 0.52*inch, 'TSR  Games')
    canvas.setFont('IMFellI', 6.8)
    canvas.setFillColor(colors.Color(0.62, 0.62, 0.62))
    canvas.drawCentredString(PW/2, 0.52*inch, 'For Personal Use Only — Not for Distribution')

    canvas.restoreState()


# ---------------------------------------------------------------------------
# Content order
# ---------------------------------------------------------------------------
CONTENT = [
    ('manuscript/00_overview.md',                          'chapter'),
    ('manuscript/01_referee_notes.md',                     'chapter'),
    ('manuscript/00b_session_intro.md',                    'chapter'),
    ('manuscript/00c_the_north_gate.md',                   'chapter'),
    ('manuscript/02_white_plume_dust.md',                  'chapter'),
    ('manuscript/07_ringstown.md',                         'chapter'),
    ('manuscript/03_npcs.md',                              'chapter'),
    ('manuscript/04_wandering_encounters.md',              'chapter'),
    ('manuscript/areas/01_forest_edge_road.md',            'area'),
    ('manuscript/areas/02_ravine_wagon_wreck.md',          'area'),
    ('manuscript/areas/03_logging_camp.md',                'area'),
    ('manuscript/areas/04_dust_pool_glade.md',             'area'),
    ('manuscript/areas/05_thorn_choked_hollow.md',         'area'),
    ('manuscript/areas/06_game_trails.md',                 'area'),
    ('manuscript/areas/07_riddle_cave_of_the_ash_tongue.md','area'),
    ('manuscript/05_conclusion.md',                        'chapter'),
    ('manuscript/08_rumors.md',                            'appendix'),
]


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------
def build():
    register_fonts()
    S = build_styles()

    # Blueprint map
    bp_path = '/tmp/ttt_blueprint.png'
    make_blueprint(str(IMAGES/'twistedthicketdmmap.png'), bp_path)

    # Frames
    tiny = Frame(0, 0, 1, 1, leftPadding=0, rightPadding=0,
                 topPadding=0, bottomPadding=0)
    col1 = Frame(ML,          MB, CW, CH,
                 leftPadding=2, rightPadding=2,
                 topPadding=0, bottomPadding=0, id='c1')
    col2 = Frame(ML+CW+GAP,   MB, CW, CH,
                 leftPadding=2, rightPadding=2,
                 topPadding=0, bottomPadding=0, id='c2')
    mfh  = PH - 0.65*inch - MB
    mapf = Frame(ML, MB, PW-ML-MR, mfh,
                 leftPadding=0, rightPadding=0,
                 topPadding=0, bottomPadding=0)

    doc = BaseDocTemplate(str(OUTPUT), pagesize=letter, allowSplitting=1,
                          title='The Twisted Thicket (Module TTT-1)',
                          author='Personal Use Only',
                          subject='OSRIC Compatible Adventure, Levels 5-7')
    doc.addPageTemplates([
        PageTemplate(id='cover',    frames=[tiny],       onPage=cb_cover),
        PageTemplate(id='back',     frames=[tiny],       onPage=cb_back),
        PageTemplate(id='interior', frames=[col1, col2], onPage=cb_interior),
        PageTemplate(id='map',      frames=[mapf],       onPage=cb_map),
    ])

    story = []

    # --- Cover ---
    story.append(Spacer(1, 0.5))

    # --- Player map ---
    story.append(NextPageTemplate('map'))
    story.append(PageBreak())
    story.append(Paragraph("PLAYER'S MAP OF THE TWISTED THICKET", S['h2']))
    story.append(Spacer(1, 5))
    story.append(RLImage(str(IMAGES/'thicketplaymap.png'),
                         width=PW-ML-MR, height=mfh-0.38*inch,
                         kind='proportional'))
    story.append(Paragraph(
        'Distribute to players at session start. Shows roads, forest edge, and Ringstown only.',
        S['cap']))

    # --- Interior content ---
    story.append(NextPageTemplate('interior'))
    story.append(PageBreak())

    for idx, (rel, ftype) in enumerate(CONTENT):
        fp = BASE / rel
        if not fp.exists():
            continue
        if idx > 0:
            story.append(CondPageBreak(1.6*inch))
        story.extend(parse_file(fp, S))
        story.append(Spacer(1, 8))

    # --- Ringstown tactical map ---
    story.append(NextPageTemplate('map'))
    story.append(PageBreak())
    story.append(Paragraph('MAP OF RINGSTOWN (TACTICAL)', S['h2']))
    story.append(Spacer(1, 5))
    story.append(RLImage(str(IMAGES/'ringstown-tactical.png'),
                         width=PW-ML-MR, height=mfh-0.38*inch,
                         kind='proportional'))
    story.append(Paragraph(
        'Referee use. Shows all named buildings and key locations within Ringstown.',
        S['cap']))

    # --- DM map (blueprint) ---
    story.append(PageBreak())
    story.append(Paragraph("DUNGEON MASTER'S MAP OF THE TWISTED THICKET", S['h2']))
    story.append(Spacer(1, 5))
    story.append(RLImage(bp_path,
                         width=PW-ML-MR, height=mfh-0.38*inch,
                         kind='proportional'))
    story.append(Paragraph(
        'For Dungeon Master use only. All seven area locations keyed. Do not show to players.',
        S['cap']))

    # --- Back cover ---
    story.append(NextPageTemplate('back'))
    story.append(PageBreak())
    story.append(Spacer(1, 0.5))

    doc.build(story)
    print(f'Done: {OUTPUT}  ({OUTPUT.stat().st_size // 1024} KB)')


if __name__ == '__main__':
    build()
