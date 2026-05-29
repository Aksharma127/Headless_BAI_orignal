#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SRC_DIR="${1:-$ROOT_DIR/chromium-main/src/out/Default}"
DEST_DIR="${2:-$ROOT_DIR/bai-final-year/runtime/chromium}"

if [[ ! -x "$SRC_DIR/chrome" ]]; then
  echo "Custom Chromium binary not found or not executable: $SRC_DIR/chrome" >&2
  exit 1
fi

rm -rf "$DEST_DIR"
mkdir -p "$DEST_DIR"

cp "$SRC_DIR/chrome" "$DEST_DIR/"

find "$SRC_DIR" -maxdepth 1 -type f \
  \( -name "*.so" -o -name "*.pak" -o -name "*.bin" -o -name "*.dat" \) \
  -exec cp {} "$DEST_DIR/" \;

for directory in locales resources swiftshader; do
  if [[ -d "$SRC_DIR/$directory" ]]; then
    cp -a "$SRC_DIR/$directory" "$DEST_DIR/"
  fi
done

chmod +x "$DEST_DIR/chrome"

echo "Packaged custom Chromium runtime into $DEST_DIR"
du -sh "$DEST_DIR"
