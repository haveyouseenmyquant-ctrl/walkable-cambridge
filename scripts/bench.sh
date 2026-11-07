#!/bin/bash
# Render the frozen benchmark from a build and score it; caches data/benchmark/scores/<build_hash>.json.
#   scripts/bench.sh [site_dir_or_url]   (default: SITE_URL if present, else site/)
# build_hash = sha256 of the build's manifest.json (unique per build: it carries the build timestamp).
set -euo pipefail
cd "$(dirname "$0")/.."
B=data/benchmark
[ -f $B/benchmark.json ] || { echo "no frozen benchmark yet (scripts/make_benchmark.py)" >&2; exit 1; }
SRC=${1:-site}; [ $# -eq 0 ] && [ -s SITE_URL ] && SRC=$(head -n1 SITE_URL | tr -d '[:space:]')
HASH=$(.venv/bin/python -I scripts/build_hash.py "$SRC")
OUT=$B/scores/$HASH.json
[ -f "$OUT" ] && { cat "$OUT" | head -c 300; echo; exit 0; }
R=/tmp/wc_renders_$HASH; rm -rf "$R"
node scripts/photo_render.mjs "$SRC" $B/benchmark.json "$R"
mkdir -p $B/scores $B/renders
.venv/bin/python -I scripts/photo_score.py $B/photos "$R" --out "$OUT"
# keep a small copy of the renders for the journal's side-by-sides (overwritten each build)
rm -rf $B/renders/latest && mkdir -p $B/renders/latest && cp "$R"/*.png $B/renders/latest/ && rm -rf "$R"
