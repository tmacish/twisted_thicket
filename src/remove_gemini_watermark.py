"""
Remove the Gemini sparkle watermark from generated images.

The watermark is a small 4-pointed star in the bottom-right corner.
Strategy: sample the background color from just inside the corner (avoiding
the sparkle) and fill the corner patch with that sampled color.

Usage:
    python3 src/remove_gemini_watermark.py                  # all PNGs in handouts/
    python3 src/remove_gemini_watermark.py handouts/kaida.png handouts/session_intro_seal.png
"""

import sys
import glob
from pathlib import Path
from PIL import Image
import numpy as np

# Gemini sparkle is inset ~33-80px from the bottom-right corner (on 1024px images).
# Cover the whole zone with margin; sample background from just outside it.
PATCH_SIZE = 92   # px from corner to cover
SAMPLE_SIZE = 20  # px wide strip to sample background color from


def remove_watermark(path: Path) -> None:
    img = Image.open(path).convert("RGBA")
    arr = np.array(img, dtype=np.float64)
    h, w = arr.shape[:2]

    # Sample background from the strip just outside the patch on each side,
    # then fill the patch with the mean of those surrounding pixels.
    top_strip = arr[h - PATCH_SIZE - SAMPLE_SIZE : h - PATCH_SIZE,
                    w - PATCH_SIZE - SAMPLE_SIZE : w]
    left_strip = arr[h - PATCH_SIZE : h,
                     w - PATCH_SIZE - SAMPLE_SIZE : w - PATCH_SIZE]
    bg_color = np.concatenate([
        top_strip.reshape(-1, 4),
        left_strip.reshape(-1, 4),
    ]).mean(axis=0)

    # Fill the corner patch
    arr[h - PATCH_SIZE:h, w - PATCH_SIZE:w] = bg_color

    result = Image.fromarray(arr.astype(np.uint8), "RGBA")
    if img.mode != "RGBA":
        result = result.convert(img.mode)
    result.save(path)
    print(f"  patched: {path}")


def main():
    if len(sys.argv) > 1:
        targets = [Path(p) for p in sys.argv[1:]]
    else:
        targets = [
            p for p in Path("handouts").glob("*.png")
            if p.is_file()
        ]

    if not targets:
        print("No PNG files found.")
        return

    for path in sorted(targets):
        remove_watermark(path)


if __name__ == "__main__":
    main()
