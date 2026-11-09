#!/bin/bash
# Market Square KPIs for a build: render the 40 frozen held-out views (data/benchmark/market_square.json), then
#   market_square_realism     = blind Claude judge (judge.py --only market) -> scores/<hash>_msjudge.json
#   scripts/ms_bench.sh [site_dir_or_url]
set -euo pipefail
cd "$(dirname "$0")/.."
B=data/benchmark
SRC=${1:-site}; [ $# -eq 0 ] && [ -s SITE_URL ] && SRC=$(head -n1 SITE_URL | tr -d '[:space:]')
HASH=$(.venv/bin/python -I scripts/build_hash.py "$SRC")
[ -f $B/scores/${HASH}_msjudge.json ] && exit 0
R=/tmp/wc_ms_renders_$HASH
mkdir -p "$R" $B/scores
for round in 1 2; do
  [ "$(ls "$R" | wc -l)" -ge 40 ] && break
  for k in 0 1 2 3; do
    IDS=$(.venv/bin/python -I -c "import json; v=json.load(open('$B/market_square.json')); print(','.join(x['id'] for x in v[$k::4]))")
    node scripts/photo_render.mjs "$SRC" $B/market_square.json "$R" --only "$IDS" 2>>/tmp/wc_ms_render.err &
  done
  wait
done
[ "$(ls "$R" | wc -l)" -ge 38 ] || { echo "ms renders incomplete ($(ls "$R" | wc -l)/40)" >&2; exit 1; }
# session 58: market_square_photo_match (DINOv2) is retired; only the judge runs. Never cache a mixed build.
[ "$(.venv/bin/python -I scripts/build_hash.py "$SRC")" = "$HASH" ] || { rm -rf "$R"; echo "build changed during ms render" >&2; exit 1; }
[ -f $B/scores/${HASH}_msjudge.json ] || .venv/bin/python -I scripts/judge.py "$HASH" "$R" --only market
rm -rf $B/renders/ms_latest && mkdir -p $B/renders/ms_latest && cp "$R"/*.png $B/renders/ms_latest/ && rm -rf "$R"
