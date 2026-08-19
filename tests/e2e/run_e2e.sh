#!/usr/bin/env bash
# Run the end-to-end bulk upload test suite.
#
# Prerequisites:
#   - Docker containers running:  cd deployment && docker-compose up -d
#   - OR local dev server:        make dev  (in one terminal)
#   - At least one MP3 file in ./data/uploads/
#
# Environment overrides:
#   RAGPIPE_API_BASE=http://localhost:3000/api/v1
#   QDRANT_BASE=http://localhost:6333
#   RAGPIPE_AUDIO_COLLECTION=audio_v1

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"

echo ""
echo "══════════════════════════════════════════════════════════"
echo "  Music RAG — Bulk Upload End-to-End Test"
echo "  Proving: CSV upload → audio pipeline → Qdrant vectors"
echo "══════════════════════════════════════════════════════════"
echo ""
echo "  API base  : ${RAGPIPE_API_BASE:-http://localhost:8000/api/v1}"
echo "  Qdrant    : ${QDRANT_BASE:-http://localhost:6333}"
echo "  Collection: ${RAGPIPE_AUDIO_COLLECTION:-audio_v1}"
echo ""

# Quick pre-flight checks
check_endpoint() {
    local url="$1"
    local label="$2"
    if curl -sf "$url" > /dev/null 2>&1; then
        echo "  ✓ $label reachable"
    else
        echo "  ✗ $label NOT reachable at $url"
        echo "    Start the service and retry."
        exit 1
    fi
}

echo "Pre-flight checks:"
check_endpoint "${RAGPIPE_API_BASE:-http://localhost:8000/api/v1}/health" "API server"
check_endpoint "${QDRANT_BASE:-http://localhost:6333}/collections"         "Qdrant"

# Check for audio files
MP3_COUNT=$(find "$PROJECT_ROOT/data/uploads" -name "*.mp3" 2>/dev/null | wc -l || echo 0)
if [ "$MP3_COUNT" -eq 0 ]; then
    echo ""
    echo "  ✗ No MP3 files found in data/uploads/"
    echo "    Upload at least one audio file via POST /api/v1/media/upload first."
    exit 1
fi
echo "  ✓ Audio files in data/uploads/: $MP3_COUNT"

echo ""
echo "Running test..."
echo ""

"$PROJECT_ROOT/venv/bin/python" -m pytest \
    tests/e2e/test_bulk_upload_e2e.py \
    -v \
    -s \
    --timeout=300 \
    -m e2e \
    "$@"
