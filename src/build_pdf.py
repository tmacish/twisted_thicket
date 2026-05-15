#!/usr/bin/env python3
"""
Build a print-ready PDF of the full adventure module from manuscript markdown files.
Outputs to .old/the_twisted_thicket.pdf

Usage:
    python3 src/build_pdf.py
"""

import os
import subprocess
import sys
import tempfile
import markdown as md_lib

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MANUSCRIPT_FILES = [
    'manuscript/00_overview.md',
    'manuscript/00b_session_intro.md',
    'manuscript/00c_the_north_gate.md',
    'manuscript/01_referee_notes.md',
    'manuscript/02_white_plume_dust.md',
    'manuscript/03_npcs.md',
    'manuscript/04_wandering_encounters.md',
    'manuscript/areas/01_forest_edge_road.md',
    'manuscript/areas/02_ravine_wagon_wreck.md',
    'manuscript/areas/03_logging_camp.md',
    'manuscript/areas/04_dust_pool_glade.md',
    'manuscript/areas/05_thorn_choked_hollow.md',
    'manuscript/areas/06_game_trails.md',
    'manuscript/areas/07_riddle_cave_of_the_ash_tongue.md',
    'manuscript/05_conclusion.md',
    'manuscript/06_hex_map.md',
    'manuscript/07_ringstown.md',
    'manuscript/08_rumors.md',
]

CSS = """
@page {
  size: letter;
  margin: 0.75in 0.8in;
}

* { box-sizing: border-box; }

body {
  font-family: Georgia, "Times New Roman", serif;
  font-size: 13.5px;
  color: #1f1b16;
  background: #fffdf8;
  line-height: 1.45;
  margin: 0;
  padding: 0;
}

h1 {
  font-size: 26px;
  text-align: center;
  color: #3b2412;
  border-bottom: 2px solid #8b6b3f;
  padding-bottom: 0.25em;
  margin-top: 0;
  margin-bottom: 0.5em;
  letter-spacing: 0.03em;
  page-break-before: auto;
}

h2 {
  font-size: 18px;
  color: #3b2412;
  border-bottom: 1px solid #c8b79a;
  padding-bottom: 0.15em;
  margin-top: 1.4em;
  margin-bottom: 0.4em;
  page-break-after: avoid;
}

h3 {
  font-size: 15px;
  color: #3b2412;
  margin-top: 1.1em;
  margin-bottom: 0.3em;
  page-break-after: avoid;
}

h4 {
  font-size: 13.5px;
  color: #3b2412;
  margin-top: 0.9em;
  margin-bottom: 0.25em;
  page-break-after: avoid;
}

p { margin: 0.4em 0 0.6em; }

ul, ol {
  margin: 0.3em 0 0.6em;
  padding-left: 1.5em;
}

li { margin-bottom: 0.2em; }

blockquote {
  margin: 0.75em 0;
  padding: 0.6em 0.85em;
  background: #f4efe4;
  border-left: 4px solid #8b6b3f;
  font-style: italic;
  color: #2a1e0e;
  page-break-inside: avoid;
}

blockquote p { margin: 0; }

table {
  width: 100%;
  border-collapse: collapse;
  margin: 0.7em 0 1em;
  font-size: 13px;
  page-break-inside: avoid;
}

th, td {
  border: 1px solid #cdbb9e;
  padding: 0.4em 0.55em;
  vertical-align: top;
}

th {
  background: #efe6d6;
  text-align: left;
  font-weight: bold;
}

tr:nth-child(even) td { background: #faf6f0; }

hr {
  border: none;
  border-top: 1px solid #c8b79a;
  margin: 1.2em 0;
}

strong { color: #2a1508; }

.section-break {
  border-top: 2px solid #8b6b3f;
  margin: 1.8em 0;
  page-break-after: avoid;
}

/* Stat block styling: paragraphs inside an h3-led section that follow
   the NPC/monster pattern get a light box treatment via sibling CSS.
   We achieve this by wrapping each manuscript section in a div. */
.manuscript-section {
  margin-bottom: 1.2em;
}

.manuscript-section.is-area {
  page-break-inside: avoid;
}
"""

SECTION_LABELS = {
    'manuscript/areas/01_forest_edge_road.md': 'is-area',
    'manuscript/areas/02_ravine_wagon_wreck.md': 'is-area',
    'manuscript/areas/03_logging_camp.md': 'is-area',
    'manuscript/areas/04_dust_pool_glade.md': 'is-area',
    'manuscript/areas/05_thorn_choked_hollow.md': 'is-area',
    'manuscript/areas/06_game_trails.md': 'is-area',
    'manuscript/areas/07_riddle_cave_of_the_ash_tongue.md': 'is-area',
}


def build_html():
    converter = md_lib.Markdown(extensions=['tables', 'nl2br'])
    sections = []

    for filepath in MANUSCRIPT_FILES:
        abs_path = os.path.join(REPO_ROOT, filepath)
        with open(abs_path, encoding='utf-8') as f:
            raw = f.read()
        html = converter.convert(raw)
        converter.reset()
        extra_class = SECTION_LABELS.get(filepath, '')
        classes = f'manuscript-section {extra_class}'.strip()
        sections.append(f'<div class="{classes}">\n{html}\n</div>')

    body = '\n'.join(sections)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>The Twisted Thicket</title>
<style>
{CSS}
</style>
</head>
<body>
{body}
</body>
</html>"""


def main():
    out_dir = os.path.join(REPO_ROOT, '.old')
    os.makedirs(out_dir, exist_ok=True)

    html = build_html()

    with tempfile.NamedTemporaryFile(
        suffix='.html', delete=False, mode='w', encoding='utf-8', dir=out_dir
    ) as f:
        f.write(html)
        tmp_html = f.name

    out_pdf = os.path.join(out_dir, 'the_twisted_thicket.pdf')

    cmd = [
        'google-chrome',
        '--headless=new',
        '--disable-gpu',
        '--no-sandbox',
        '--disable-dev-shm-usage',
        '--run-all-compositor-stages-before-draw',
        '--virtual-time-budget=5000',
        f'--print-to-pdf={out_pdf}',
        '--print-to-pdf-no-header',
        f'file://{tmp_html}',
    ]

    print('Rendering PDF via Chrome headless…')
    result = subprocess.run(cmd, capture_output=True, text=True)
    os.unlink(tmp_html)

    if result.returncode != 0:
        print(f'Chrome error:\n{result.stderr}', file=sys.stderr)
        sys.exit(1)

    size_kb = os.path.getsize(out_pdf) // 1024
    print(f'PDF written to {out_pdf} ({size_kb} KB)')


if __name__ == '__main__':
    main()
