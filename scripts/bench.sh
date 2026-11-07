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
[ -f "$OUT" ] && [ -f $B/scores/${HASH}_judge.json ] && [ -f $B/scores/${HASH}_quality.json ] && { head -c 300 "$OUT"; echo; exit 0; }
R=/tmp/wc_renders_$HASH
mkdir -p $B/scores $B/renders
if [ ! -f "$OUT" ]; then
  [ "$(ls "$R" 2>/dev/null | wc -l)" -ge 200 ] || { rm -rf "$R"; node scripts/photo_render.mjs "$SRC" $B/benchmark.json "$R"; }
  .venv/bin/python -I scripts/photo_score.py $B/photos "$R" --out "$OUT"
fi
# judged_realism (50 blind A/B views) and visual_quality (30 views, rubric): Claude vision judge, scripts/judge.py
[ -d "$R" ] || R=$B/renders/latest
[ -f $B/scores/${HASH}_judge.json ] || .venv/bin/python -I scripts/judge.py "$HASH" "$R" --only realism
[ -f $B/scores/${HASH}_quality.json ] || .venv/bin/python -I scripts/judge.py "$HASH" "$R" --only quality
[ "$R" = $B/renders/latest ] && exit 0
# keep a small copy of the renders for the journal's side-by-sides (overwritten each build)
rm -rf $B/renders/latest && mkdir -p $B/renders/latest && cp "$R"/*.png $B/renders/latest/ && rm -rf "$R"
