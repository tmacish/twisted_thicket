#!/bin/bash
# Upscales new_player_map.png to 2400x1920 using GIMP cubic interpolation.
# Output written to images/new_player_map_2400.png (original is not overwritten).

INPUT="/home/tjmcdon/RPG/Code/the_twisted_thicket/images/new_player_map.png"
OUTPUT="/home/tjmcdon/RPG/Code/the_twisted_thicket/images/new_player_map_2400.png"

gimp -i -b "(let* \
  ((image (car (gimp-file-load RUN-NONINTERACTIVE \"${INPUT}\" \"${INPUT}\"))))  \
  (gimp-image-scale-full image 2400 1920 INTERPOLATION-CUBIC) \
  (gimp-image-flatten image) \
  (file-png-save RUN-NONINTERACTIVE image \
    (car (gimp-image-get-active-drawable image)) \
    \"${OUTPUT}\" \"${OUTPUT}\" \
    0 6 1 1 1 1 1))" \
  -b "(gimp-quit 0)"

echo "Done: ${OUTPUT}"
