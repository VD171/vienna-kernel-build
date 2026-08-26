#!/usr/bin/env bash
# Build a flashable boot.img for the Motorola Edge 60 Neo (vienna) from a GKI Image.gz,
# then give it an AVB footer sized for the real partition.
#
# Needs: mkbootimg and avbtool (both from AOSP, pip install avbtool works too).
#
#   ./make-boot.sh Image.gz vbmeta_stock.img out/
#
# Produces out/boot-new.img (footered, ready for `fastboot flash boot`) and prints the
# next step. Pair it with patch-vbmeta.py, which is the part that actually unlocks the
# preflash check. Read ../flash-recipe/README.md before running any of this.
set -euo pipefail

IMAGE_GZ=${1:?usage: make-boot.sh <Image.gz> <vbmeta_stock.img> <outdir>}
VBMETA_STOCK=${2:?missing vbmeta_stock.img}
OUT=${3:-out}

# vienna: boot partition is 64 MiB. Verified with `fastboot getvar partition-size:boot`.
PART_SIZE=67108864
# Header v4 is what this device ships. Anything else is refused.
HEADER_VERSION=4

mkdir -p "$OUT"
RAW="$OUT/boot-raw.img"
FINAL="$OUT/boot-new.img"

echo "==> mkbootimg (header v4)"
mkbootimg --header_version "$HEADER_VERSION" --kernel "$IMAGE_GZ" --output "$RAW"

echo "==> stock boot salt (reused so the descriptor keeps its exact layout)"
SALT=$(python3 "$(dirname "$0")/patch-vbmeta.py" --print-salt "$VBMETA_STOCK")
echo "    salt: ${SALT:0:24}..."

cp "$RAW" "$FINAL"
echo "==> avbtool add_hash_footer (partition_size=$PART_SIZE)"
avbtool add_hash_footer \
  --image "$FINAL" \
  --partition_name boot \
  --partition_size "$PART_SIZE" \
  --salt "$SALT"

echo
echo "wrote $FINAL ($(stat -c%s "$FINAL") bytes)"
echo
echo "next, build the patched vbmeta from the image WITHOUT the footer:"
echo "  python3 patch-vbmeta.py $VBMETA_STOCK $RAW $OUT/vbmeta-new.img"
echo
echo "then, on the device (unlocked bootloader):"
echo "  fastboot flash vbmeta $OUT/vbmeta-new.img"
echo "  fastboot flash boot   $FINAL"
