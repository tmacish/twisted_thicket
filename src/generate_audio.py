#!/usr/bin/env python3
"""
Generate chapter-by-chapter MP3 audio files from The Twisted Thicket manuscript.
Reads markdown source files directly, strips formatting, and synthesises with edge-tts.

Output: audio/ directory at repo root.
Voice: en-US-ChristopherNeural
"""

import asyncio
import os
import re
import sys

import edge_tts

MANUSCRIPT = os.path.join(os.path.dirname(__file__), "..", "manuscript")
AUDIO_DIR  = os.path.join(os.path.dirname(__file__), "..", "audio")
VOICE      = "en-US-ChristopherNeural"

# Each chapter: (output_slug, display_title, [relative paths from MANUSCRIPT])
CHAPTERS = [
    ("01_overview_and_referees_notes", "Overview and Referee's Notes", [
        "00_overview.md",
        "01_referee_notes.md",
        "02_white_plume_dust.md",
    ]),
    ("02_session_introduction_and_npcs", "Session Introduction and NPCs", [
        "00b_session_intro.md",
        "00c_the_north_gate.md",
        "03_npcs.md",
    ]),
    ("03_area_1_forest_edge_road",           "Area 1: Forest Edge Road",              ["areas/01_forest_edge_road.md"]),
    ("04_area_2_ravine_wagon_wreck",          "Area 2: Ravine Wagon Wreck",            ["areas/02_ravine_wagon_wreck.md"]),
    ("05_area_3_logging_camp",               "Area 3: Logging Camp",                  ["areas/03_logging_camp.md"]),
    ("06_area_4_dust_pool_glade",            "Area 4: Dust Pool Glade",               ["areas/04_dust_pool_glade.md"]),
    ("07_area_5_thorn_choked_hollow",        "Area 5: Thorn-Choked Hollow",           ["areas/05_thorn_choked_hollow.md"]),
    ("08_area_6_game_trails",               "Area 6: Game Trails",                   ["areas/06_game_trails.md"]),
    ("09_area_7_riddle_cave",               "Area 7: Riddle Cave of the Ash Tongue", ["areas/07_riddle_cave_of_the_ash_tongue.md"]),
    ("10_conclusion",                        "Conclusion",                            ["05_conclusion.md"]),
]

# Table separator row: lines like |---|---| or |:--:|---|
_TABLE_SEP_RE = re.compile(r"^\s*\|[-:| ]+\|\s*$")

# Table data row: | cell | cell | ... |
_TABLE_ROW_RE = re.compile(r"^\s*\|(.+)\|\s*$")

# Heading: # Title or ## Title
_HEADING_RE = re.compile(r"^#{1,6}\s+(.+)$")

# Blockquote marker: > text
_BLOCKQUOTE_RE = re.compile(r"^>\s?(.*)$")

# Horizontal rule
_HRULE_RE = re.compile(r"^\s*---+\s*$")

# Double-hyphen used as em-dash substitute
_DOUBLE_HYPHEN_RE = re.compile(r"\s*--\s*")

# Bold and italic markers
_BOLD_RE   = re.compile(r"\*\*(.+?)\*\*")
_ITALIC_RE = re.compile(r"\*(.+?)\*")

# Backticks
_CODE_RE = re.compile(r"`(.+?)`")

# Multiple blank lines
_MULTI_BLANK_RE = re.compile(r"\n{3,}")

# Comma with extra whitespace around it (used as em-dash substitute in source)
_COMMA_SPACE_RE = re.compile(r",\s{2,}")


def _convert_table_row(line: str) -> str:
    """Convert '| 1 | Some text here |' to '1: Some text here.'"""
    cells = [c.strip() for c in line.strip().strip("|").split("|")]
    cells = [c for c in cells if c]
    if not cells:
        return ""
    if len(cells) == 1:
        return cells[0]
    # First cell is usually a die result or column header
    return f"{cells[0]}: {'. '.join(cells[1:])}"


def clean_markdown(raw: str) -> str:
    lines = raw.replace("\r\n", "\n").split("\n")
    out = []
    for line in lines:
        # Skip horizontal rules
        if _HRULE_RE.match(line):
            continue
        # Skip table separator rows
        if _TABLE_SEP_RE.match(line):
            continue
        # Convert table data rows
        if _TABLE_ROW_RE.match(line):
            converted = _convert_table_row(line)
            if converted:
                out.append(converted)
            continue
        # Strip heading markers, keep text
        m = _HEADING_RE.match(line)
        if m:
            out.append(m.group(1))
            continue
        # Strip blockquote markers, keep text
        m = _BLOCKQUOTE_RE.match(line)
        if m:
            out.append(m.group(1))
            continue
        out.append(line)

    text = "\n".join(out)

    # Inline substitutions
    text = _DOUBLE_HYPHEN_RE.sub(", ", text)
    text = _BOLD_RE.sub(r"\1", text)
    text = _ITALIC_RE.sub(r"\1", text)
    text = _CODE_RE.sub(r"\1", text)

    # Normalise spacing
    text = _COMMA_SPACE_RE.sub(", ", text)
    text = re.sub(r"[ \t]+", " ", text)           # collapse spaces/tabs on a line
    text = re.sub(r"(?m) +$", "", text)           # strip trailing spaces
    text = _MULTI_BLANK_RE.sub("\n\n", text)

    return text.strip()


def build_chapter_text(file_list: list[str]) -> str:
    parts = []
    for rel_path in file_list:
        full_path = os.path.join(MANUSCRIPT, rel_path)
        if not os.path.exists(full_path):
            print(f"  WARNING: not found: {full_path}", file=sys.stderr)
            continue
        with open(full_path, encoding="utf-8") as f:
            raw = f.read()
        parts.append(clean_markdown(raw))
    return "\n\n".join(parts)


async def synthesize(text: str, output_path: str) -> None:
    communicate = edge_tts.Communicate(text, VOICE)
    await communicate.save(output_path)
    size_kb = os.path.getsize(output_path) // 1024
    print(f"  saved {os.path.basename(output_path)} ({size_kb} KB)")


async def main() -> None:
    os.makedirs(AUDIO_DIR, exist_ok=True)

    for slug, title, files in CHAPTERS:
        print(f"\n{title}")
        text = build_chapter_text(files)
        if not text:
            print("  WARNING: empty, skipping.")
            continue
        output_path = os.path.join(AUDIO_DIR, f"{slug}.mp3")
        await synthesize(text, output_path)

    print("\nDone.")


if __name__ == "__main__":
    asyncio.run(main())
