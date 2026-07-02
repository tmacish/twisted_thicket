#!/usr/bin/env python3
import sys
import os
from PIL import Image

def collate_images(top_path, bottom_path, output_path="collated_output.png"):
    # Expand user paths (like ~/) if passed
    top_path = os.path.expanduser(top_path)
    bottom_path = os.path.expanduser(bottom_path)

    # Open the source images
    try:
        img_top = Image.open(top_path)
        img_bottom = Image.open(bottom_path)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return

    # Configuration for the dark wooden separator line
    separator_h = 4
    sep_color = (43, 26, 14) # Hex #2b1a0e in RGB

    # Calculate final dimensions
    w1, h1 = img_top.size
    w2, h2 = img_bottom.size
    
    final_w = max(w1, w2)
    final_h = h1 + separator_h + h2

    # Create the new black canvas
    canvas = Image.new("RGB", (final_w, final_h), color=(0, 0, 0))

    # Center and paste the Top Image (People)
    off_x1 = (final_w - w1) // 2
    canvas.paste(img_top, (off_x1, 0))

    # Create and paste the Separator line
    sep_line = Image.new("RGB", (final_w, separator_h), color=sep_color)
    canvas.paste(sep_line, (0, h1))

    # Center and paste the Bottom Image (Scroll)
    off_x2 = (final_w - w2) // 2
    canvas.paste(img_bottom, (off_x2, h1 + separator_h))

    # Save the final masterpiece
    canvas.save(output_path)
    print(f"Successfully collated! Saved to: {os.path.abspath(output_path)}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 collate.py <path_to_top_image> <path_to_bottom_image>")
        sys.exit(1)
        
    collate_images(sys.argv[1], sys.argv[2])
