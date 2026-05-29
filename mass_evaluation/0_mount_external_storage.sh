#!/bin/bash
# 🔌 STEP 0: Mount External Storage
# Mount your external drive containing 100+ website samples to the corpus/ directory
# Usage: ./0_mount_external_storage.sh

set -e

CORPUS_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/corpus"
MOUNT_POINT="${1:-.}"  # Default to current directory if no argument provided

echo "🔌 External Storage Mount Script"
echo "================================"
echo "Corpus Path: $CORPUS_PATH"
echo "Mount Point: $MOUNT_POINT"
echo ""

# TODO: Add your mount logic here
# Example:
# sudo mount -t cifs //network/share/websites $CORPUS_PATH -o username=user,password=pass
# OR
# ln -s /path/to/external/drive/* $CORPUS_PATH/

echo "✅ Mount configuration ready."
echo "   Ensure your corpus files are accessible at: $CORPUS_PATH"
