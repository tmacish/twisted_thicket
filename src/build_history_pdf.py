#!/usr/bin/env python3
"""
build_history_pdf.py
Renders the in-world chronicle "The Long War Below and the Battle of Blackmoor:
 A True Account" (manuscript/appendices/history_behind_the_thicket.md) as a TSR-styled
PDF, matching the look of build_module_pdf.py: same fonts, palette, two-column
parchment interior, and ornamental rules.

The printed handout strips the markdown title block (re-set on the cover) and
the out-of-fiction referee note at the foot of the source file.
Personal use only.
"""

import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer,
    Table, TableStyle, PageBreak, NextPageTemplate, CondPageBreak,
)
from reportlab.platypus.flowables import Flowable
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE   = Path('/home/tjmcdon/RPG/Code/the_twisted_thicket')
FONTS  = BASE / 'fonts'
SRC_MD = BASE / 'manuscript' / 'appendices' / 'history_behind_the_thicket.md'
OUTPUT = BASE / 'history_behind_the_thicket.pdf'

# ---------------------------------------------------------------------------
# Page geometry  (US Letter)
# ---------------------------------------------------------------------------
PW, PH = letter
ML  = 0.72 * inch
MR  = 0.72 * inch
MT  = 0.88 * inch
MB  = 0.70 * inch
GAP = 0.22 * inch
CW  = (PW - ML - MR - GAP) / 2
CH  = PH - MT - MB

# ---------------------------------------------------------------------------
# Colour palette  (shared with build_module_pdf.py)
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

    mk('body',  fontName='IMFell', fontSize=9.6, leading=13.6,
       textColor=DARK_INK, alignment=TA_JUSTIFY,
       spaceBefore=3, spaceAfter=2, firstLineIndent=11)
    mk('body0', parent='body', firstLineIndent=0)
    # Bracketed scribe interjections: italic, faintly inset
    mk('scribe', fontName='IMFellI', fontSize=9.2, leading=13,
       textColor=colors.Color(0.30, 0.20, 0.07), alignment=TA_JUSTIFY,
       firstLineIndent=0, leftIndent=10, rightIndent=4,
       spaceBefore=3, spaceAfter=3)
    mk('h1',    fontName='Cinzel', fontSize=14, leading=17,
       textColor=DARK_INK, alignment=TA_CENTER,
       spaceBefore=12, spaceAfter=6, firstLineIndent=0)
    mk('h2',    fontName='Cinzel', fontSize=11, leading=13.5,
       textColor=DARK_INK, alignment=TA_LEFT,
       spaceBefore=9, spaceAfter=3, firstLineIndent=0)
    mk('h3',    fontName='Cinzel', fontSize=9.4, leading=12,
       textColor=DARK_INK, alignment=TA_LEFT,
       spaceBefore=6, spaceAfter=2, firstLineIndent=0)
    mk('subtitle', fontName='IMFellI', fontSize=9.6, leading=13,
       textColor=colors.Color(0.30, 0.20, 0.07), alignment=TA_CENTER,
       firstLineIndent=0, spaceBefore=2, spaceAfter=4)
    mk('bullet',fontName='IMFell', fontSize=9.4, leading=12.8,
       textColor=DARK_INK, alignment=TA_JUSTIFY,
       firstLineIndent=0, leftIndent=13, spaceBefore=1, spaceAfter=1)
    mk('tc',    fontName='IMFell', fontSize=8.4, leading=11,
       textColor=DARK_INK, firstLineIndent=0)
    mk('th',    fontName='Cinzel', fontSize=7.8, leading=10,
       textColor=DARK_INK, alignment=TA_CENTER, firstLineIndent=0)
    return S

# ---------------------------------------------------------------------------
# Custom flowables (shared with build_module_pdf.py)
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
# Markdown parser  (adapted from build_module_pdf.py)
# A whole-line bracketed paragraph "[ ... ]" renders in the scribe style.
# ---------------------------------------------------------------------------
def parse_text(text, styles):
    lines  = text.split('\n')
    out    = []
    i      = 0
    fresh  = True

    def add(f): out.append(f)

    while i < len(lines):
        ln = lines[i]

        if not ln.strip():
            i += 1; continue

        if re.match(r'^# [^#]', ln):
            add(Spacer(1, 5))
            add(Paragraph(mdi(ln[2:].strip()), styles['h1']))
            add(SecRule(CW, thick=1.0))
            add(Spacer(1, 3))
            fresh = True; i += 1; continue

        if re.match(r'^## [^#]', ln):
            add(Spacer(1, 3))
            add(Paragraph(mdi(ln[3:].strip()), styles['h2']))
            add(SecRule(CW, thick=0.5, double=False))
            add(Spacer(1, 2))
            fresh = True; i += 1; continue

        if re.match(r'^### [^#]', ln):
            add(Paragraph(mdi(ln[4:].strip()), styles['h3']))
            fresh = True; i += 1; continue

        if re.match(r'^#{4,}', ln):
            txt = re.sub(r'^#+\s*', '', ln)
            add(Paragraph('<font name="Cinzel" size="9">' + mdi(txt) + '</font>',
                          styles['body0']))
            fresh = True; i += 1; continue

        if ln.strip() in ('---', '***', '___'):
            add(SecRule(CW, thick=0.4, double=True))
            add(Spacer(1, 3))
            i += 1; continue

        if ln.startswith('>'):
            bq = []
            while i < len(lines) and lines[i].startswith('>'):
                bq.append(lines[i].lstrip('> ').rstrip()); i += 1
            paras, cur = [], []
            for bl in bq:
                if not bl.strip():
                    if cur: paras.append(' '.join(cur)); cur = []
                else:
                    cur.append(bl)
            if cur: paras.append(' '.join(cur))
            rp = [Paragraph(mdi(p), styles['body']) for p in paras if p.strip()]
            if rp:
                add(Spacer(1, 3)); add(ReadAloudBox(rp, CW)); add(Spacer(1, 3))
            fresh = True; continue

        if ln.startswith('|'):
            rows = []
            while i < len(lines) and lines[i].startswith('|'):
                rows.append(lines[i]); i += 1
            tdata = []; hdr = True
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

        if re.match(r'^[-*+] ', ln):
            while i < len(lines) and re.match(r'^[-*+] ', lines[i]):
                add(Paragraph('• ' + mdi(lines[i][2:].strip()), styles['bullet']))
                i += 1
            fresh = True; continue

        if re.match(r'^\d+\. ', ln):
            n = 1
            while i < len(lines) and re.match(r'^\d+\. ', lines[i]):
                txt = re.sub(r'^\d+\. ', '', lines[i]).strip()
                add(Paragraph(f'<font name="Cinzel" size="8">{n}.</font> ' + mdi(txt),
                              styles['bullet']))
                n += 1; i += 1
            fresh = True; continue

        # Regular paragraph (collect continuation lines)
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
            # whole-paragraph scribe note: [ ... ]
            if pt_text.startswith('[') and pt_text.endswith(']'):
                add(Paragraph(mdi(pt_text), styles['scribe']))
                fresh = True
            else:
                st = styles['body0'] if fresh else styles['body']
                add(Paragraph(mdi(pt_text), st))
                fresh = False

    return out


# ---------------------------------------------------------------------------
# Source loading: split off the title block; drop the trailing referee note.
# ---------------------------------------------------------------------------
def load_source():
    raw = SRC_MD.read_text(encoding='utf-8')
    lines = raw.split('\n')

    title, subtitle = '', ''
    for ln in lines:
        if not title and ln.startswith('# '):
            title = ln[2:].strip()
            continue
        if title and not subtitle and ln.strip().startswith('*'):
            subtitle = ln.strip().strip('*').strip()
            break

    # Body starts at the first "## " heading (the Preface).
    start = 0
    for idx, ln in enumerate(lines):
        if ln.startswith('## '):
            start = idx; break
    body_lines = lines[start:]

    # Drop the out-of-fiction referee note at the foot of the file.
    body = '\n'.join(body_lines)
    cut = body.find('*[Referee note')
    if cut != -1:
        body = body[:cut].rstrip()
        # trailing horizontal rule left dangling above the note
        body = re.sub(r'\n-{3,}\s*$', '', body).rstrip()

    return title, subtitle, body


# ---------------------------------------------------------------------------
# Canvas helpers
# ---------------------------------------------------------------------------
def _fit(canvas, text, font, size, maxw):
    while size > 6 and canvas.stringWidth(text, font, size) > maxw:
        size -= 0.5
    return size

def _wrap_draw(canvas, text, font, size, x, y, maxw, leading, align='left'):
    words = text.split()
    line = ''
    for w in words:
        test = (line + ' ' + w).strip()
        if canvas.stringWidth(test, font, size) > maxw and line:
            _draw_line(canvas, line, font, size, x, y, maxw, align)
            y -= leading; line = w
        else:
            line = test
    if line:
        _draw_line(canvas, line, font, size, x, y, maxw, align)
        y -= leading
    return y

def _draw_line(canvas, line, font, size, x, y, maxw, align):
    canvas.setFont(font, size)
    if align == 'center':
        canvas.drawCentredString(x + maxw/2, y, line)
    else:
        canvas.drawString(x, y, line)


# ---------------------------------------------------------------------------
# Page callbacks
# ---------------------------------------------------------------------------
HEADER = "THE HISTORY BEHIND THE TWISTED THICKET"

def cb_interior(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(CREAM)
    canvas.rect(0, 0, PW, PH, fill=1, stroke=0)
    canvas.setFont('Cinzel', 7.4)
    canvas.setFillColor(DARK_INK)
    canvas.drawString(ML, PH - 0.52*inch, HEADER)
    canvas.setFont('IMFell', 7.4)
    canvas.drawRightString(PW - MR, PH - 0.52*inch, str(doc.page))
    canvas.setStrokeColor(RULE_COL)
    canvas.setLineWidth(0.8); canvas.line(ML, PH-0.59*inch, PW-MR, PH-0.59*inch)
    canvas.setLineWidth(0.25); canvas.line(ML, PH-0.62*inch, PW-MR, PH-0.62*inch)
    canvas.setLineWidth(0.5)
    canvas.line(ML, MB - 0.10*inch, PW-MR, MB - 0.10*inch)
    canvas.setFont('IMFellI', 6.2)
    canvas.setFillColor(colors.Color(0.35, 0.22, 0.08))
    canvas.drawCentredString(PW/2, MB - 0.25*inch, 'For Personal Use Only')
    canvas.restoreState()


def cb_cover(canvas, doc):
    canvas.saveState()

    # Parchment field
    canvas.setFillColor(BACK_CREAM)
    canvas.rect(0, 0, PW, PH, fill=1, stroke=0)

    # Double ink border
    canvas.setStrokeColor(DARK_INK)
    canvas.setLineWidth(2.8)
    canvas.rect(0.30*inch, 0.30*inch, PW-0.60*inch, PH-0.60*inch, fill=0, stroke=1)
    canvas.setLineWidth(0.7)
    canvas.rect(0.40*inch, 0.40*inch, PW-0.80*inch, PH-0.80*inch, fill=0, stroke=1)

    cx = PW/2
    inner_w = PW - 1.30*inch
    left = 0.65*inch

    # Kicker
    canvas.setFont('Cinzel', 9)
    canvas.setFillColor(TSR_ORANGE_DK)
    canvas.drawCentredString(cx, PH - 1.50*inch, 'A LOREMASTER’S TRUE HISTORY')

    # Ornamental rule
    def orn(y):
        canvas.setStrokeColor(RULE_COL)
        canvas.setLineWidth(1.4); canvas.line(left, y, PW-left, y)
        canvas.setLineWidth(0.3); canvas.line(left, y-3, PW-left, y-3)
    orn(PH - 1.72*inch)

    # Title (two lines, Blackletter, fit to width)
    line1 = 'The Long War Below and the Battle of Blackmoor'
    line2 = 'A True Account'
    s1 = _fit(canvas, line1, 'Blackletter', 34, inner_w)
    s2 = _fit(canvas, line2, 'Blackletter', 26, inner_w)
    canvas.setFillColor(DARK_INK)
    canvas.setFont('Blackletter', s1)
    canvas.drawCentredString(cx, PH - 2.55*inch, line1)
    canvas.setFont('Blackletter', s2)
    canvas.drawCentredString(cx, PH - 3.30*inch, line2)

    orn(PH - 3.65*inch)

    # Subtitle (wrapped italic)
    sub = doc.history_subtitle or ''
    y = PH - 4.05*inch
    y = _wrap_draw(canvas, sub, 'IMFellI', 11, left, y, inner_w, 16, align='center')

    # Attribution block
    canvas.setFillColor(colors.Color(0.30, 0.20, 0.07))
    canvas.setFont('Cinzel', 9.5)
    canvas.drawCentredString(cx, PH - 5.70*inch, 'Dictated by  SILVANIUS  the Lorekeeper')
    canvas.setFont('IMFellI', 9.5)
    canvas.drawCentredString(cx, PH - 5.95*inch, 'in his last season')
    canvas.setFont('Cinzel', 9.5)
    canvas.drawCentredString(cx, PH - 6.30*inch, 'Set down by the hand of  TAMSIN REED,  his apprentice')

    # Device: a small diamond knot
    dy = PH - 7.05*inch
    canvas.setStrokeColor(RULE_COL); canvas.setFillColor(TSR_ORANGE_DK)
    canvas.setLineWidth(0.8)
    canvas.line(cx-46, dy, cx-10, dy)
    canvas.line(cx+10, dy, cx+46, dy)
    canvas.translate(cx, dy); canvas.rotate(45)
    canvas.rect(-4.5, -4.5, 9, 9, fill=1, stroke=1)
    canvas.rotate(-45); canvas.translate(-cx, -dy)

    # Bottom bar
    canvas.setFillColor(DARK_INK)
    canvas.rect(0.40*inch, 0.40*inch, PW-0.80*inch, 0.46*inch, fill=1, stroke=0)
    canvas.setFont('IMFellI', 8)
    canvas.setFillColor(colors.Color(0.86, 0.84, 0.78))
    canvas.drawCentredString(cx, 0.40*inch + 0.16*inch,
                             '“Do not let them sing it the easy way.”')

    canvas.restoreState()


def cb_back(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(BACK_CREAM)
    canvas.rect(0, 0, PW, PH, fill=1, stroke=0)
    canvas.setStrokeColor(DARK_INK)
    canvas.setLineWidth(2.8)
    canvas.rect(0.30*inch, 0.30*inch, PW-0.60*inch, PH-0.60*inch, fill=0, stroke=1)
    canvas.setLineWidth(0.7)
    canvas.rect(0.40*inch, 0.40*inch, PW-0.80*inch, PH-0.80*inch, fill=0, stroke=1)

    cx = PW/2
    left = 0.95*inch
    inner_w = PW - 1.90*inch

    canvas.setFillColor(colors.Color(0.30, 0.20, 0.07))
    canvas.setFont('IMFellI', 11)
    epitaph = (
        'I have kept his letters, and his notes, and this. I am young, and I will '
        'carry it a long time. If it has reached you, then it outran the easy song, '
        'which is all he ever wanted.'
    )
    y = PH/2 + 0.7*inch
    y = _wrap_draw(canvas, epitaph, 'IMFellI', 11, left, y, inner_w, 17, align='center')

    canvas.setStrokeColor(RULE_COL)
    canvas.setLineWidth(0.4); canvas.line(left, y-6, PW-left, y-6)

    canvas.setFont('Cinzel', 9)
    canvas.setFillColor(DARK_INK)
    canvas.drawCentredString(cx, y - 0.40*inch, '—  TAMSIN REED')

    canvas.setFont('IMFellI', 6.8)
    canvas.setFillColor(colors.Color(0.40, 0.27, 0.10))
    canvas.drawCentredString(cx, 0.62*inch, 'For Personal Use Only — Not for Distribution')
    canvas.restoreState()


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------
def build():
    register_fonts()
    S = build_styles()
    title, subtitle, body = load_source()

    tiny = Frame(0, 0, 1, 1, leftPadding=0, rightPadding=0,
                 topPadding=0, bottomPadding=0)
    col1 = Frame(ML, MB, CW, CH, leftPadding=2, rightPadding=2,
                 topPadding=0, bottomPadding=0, id='c1')
    col2 = Frame(ML+CW+GAP, MB, CW, CH, leftPadding=2, rightPadding=2,
                 topPadding=0, bottomPadding=0, id='c2')

    doc = BaseDocTemplate(str(OUTPUT), pagesize=letter, allowSplitting=1,
                          title=title or 'A History of the Twisted Thicket',
                          author='Personal Use Only',
                          subject='In-world chronicle, companion to Module TTT-1')
    doc.history_subtitle = subtitle
    doc.addPageTemplates([
        PageTemplate(id='cover',    frames=[tiny],       onPage=cb_cover),
        PageTemplate(id='back',     frames=[tiny],       onPage=cb_back),
        PageTemplate(id='interior', frames=[col1, col2], onPage=cb_interior),
    ])

    story = []

    # Cover
    story.append(Spacer(1, 0.5))

    # Interior: the chronicle body only. The title lives on the cover and is
    # deliberately not repeated here.
    story.append(NextPageTemplate('interior'))
    story.append(PageBreak())
    story.append(Spacer(1, 4))
    story.extend(parse_text(body, S))

    # Back cover
    story.append(NextPageTemplate('back'))
    story.append(PageBreak())
    story.append(Spacer(1, 0.5))

    doc.build(story)
    print(f'Done: {OUTPUT}  ({OUTPUT.stat().st_size // 1024} KB)')


if __name__ == '__main__':
    build()
