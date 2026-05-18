#!/bin/bash
# Upscales all images/area*.png to 2x their original resolution using GIMP cubic interpolation.
# Preserves each image's original aspect ratio — no squishing.
# Output files written to images/vtt/ with the same filename.
# Run this any time new area maps are added — already-upscaled files are skipped.

IMAGES_DIR="/home/tjmcdon/RPG/Code/the_twisted_thicket/images"
OUTPUT_DIR="${IMAGES_DIR}/vtt"

mkdir -p "${OUTPUT_DIR}"

shopt -s nullglob
MAPS=("${IMAGES_DIR}"/area*.png)

if [ ${#MAPS[@]} -eq 0 ]; then
  echo "No area*.png files found in ${IMAGES_DIR}"
  exit 1
fi

for INPUT in "${MAPS[@]}"; do
  FILENAME=$(basename "${INPUT}")
  OUTPUT="${OUTPUT_DIR}/${FILENAME}"

  if [ -f "${OUTPUT}" ]; then
    echo "SKIP (already exists): ${FILENAME}"
    continue
  fi

  # Calculate 2x dimensions preserving aspect ratio
  W=$(identify -format '%w' "${INPUT}")
  H=$(identify -format '%h' "${INPUT}")
  NEW_W=$((W * 2))
  NEW_H=$((H * 2))

  echo "Upscaling: ${FILENAME} (${W}x${H} -> ${NEW_W}x${NEW_H})"

  gimp -i -b "(let* \
    ((image (car (gimp-file-load RUN-NONINTERACTIVE \"${INPUT}\" \"${INPUT}\")))) \
    (gimp-image-scale-full image ${NEW_W} ${NEW_H} INTERPOLATION-CUBIC) \
    (gimp-image-flatten image) \
    (file-png-save RUN-NONINTERACTIVE image \
      (car (gimp-image-get-active-drawable image)) \
      \"${OUTPUT}\" \"${OUTPUT}\" \
      0 6 1 1 1 1 1))" \
    -b "(gimp-quit 0)" 2>/dev/null

  if [ -f "${OUTPUT}" ]; then
    echo "  Done: $(identify -format '%wx%h' "${OUTPUT}")"
  else
    echo "  FAILED: ${FILENAME}"
  fi
done

echo ""
echo "VTT maps written to: ${OUTPUT_DIR}"
