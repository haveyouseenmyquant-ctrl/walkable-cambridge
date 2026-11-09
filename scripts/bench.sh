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
# roof_match_pct needs the GLBs on disk: computed from site/ when it is the same build as SRC
[ -f $B/scores/${HASH}_roof.json ] || { [ "$(.venv/bin/python -I scripts/build_hash.py site)" = "$HASH" ] && .venv/bin/python -I scripts/roof_match.py site || true; }
[ -f $B/scores/${HASH}_judge.json ] && [ -f $B/scores/${HASH}_quality.json ] && { head -c 200 $B/scores/${HASH}_judge.json; echo; exit 0; }
R=/tmp/wc_renders_$HASH
mkdir -p $B/scores $B/renders
# session 58: photo_match_score is retired (Gaspard, 8 Nov), so only the views the two judges use are rendered:
# judge_views (50) + quality_views (30), about 75 unique instead of 200. Abort between rounds if the live build changed.
IDS_ALL=$(.venv/bin/python -I -c "import json; a=json.load(open('$B/judge_views.json'))+json.load(open('$B/quality_views.json')); print(' '.join(sorted(set(map(str,a)))))")
NEED=$(echo $IDS_ALL | wc -w | tr -d ' ')
have() { local n=0; for i in $IDS_ALL; do [ -f "$R/$i.png" ] && n=$((n+1)); done; echo $n; }
if [ ! -f $B/scores/${HASH}_judge.json ] || [ ! -f $B/scores/${HASH}_quality.json ]; then
  W=${BENCH_WORKERS:-4}
  for round in 1 2 3; do
    [ "$(have)" -ge "$NEED" ] && break
    [ "$(.venv/bin/python -I scripts/build_hash.py "$SRC")" = "$HASH" ] || { rm -rf "$R"; echo "build changed during render" >&2; exit 1; }
    for k in $(seq 0 $((W - 1))); do
      IDS=$(echo $IDS_ALL | tr ' ' '\n' | awk -v k=$k -v w=$W 'NR%w==k' | paste -sd, -)
      node scripts/photo_render.mjs "$SRC" $B/benchmark.json "$R" --only "$IDS" 2>>/tmp/wc_bench_render.err &
    done
    wait
  done
  [ "$(have)" -ge "$NEED" ] || { echo "renders incomplete ($(have)/$NEED)" >&2; exit 1; }
  [ "$(.venv/bin/python -I scripts/build_hash.py "$SRC")" = "$HASH" ] || { rm -rf "$R"; echo "build changed during render" >&2; exit 1; }
fi
# judged_realism (50 blind A/B views) and visual_quality (30 views, rubric): Claude vision judge, scripts/judge.py
[ -d "$R" ] || R=$B/renders/latest
[ -f $B/scores/${HASH}_judge.json ] || .venv/bin/python -I scripts/judge.py "$HASH" "$R" --only realism
[ -f $B/scores/${HASH}_quality.json ] || .venv/bin/python -I scripts/judge.py "$HASH" "$R" --only quality
[ "$R" = $B/renders/latest ] && exit 0
# keep a small copy of the renders for the journal's side-by-sides (overwritten each build)
rm -rf $B/renders/latest && mkdir -p $B/renders/latest && cp "$R"/*.png $B/renders/latest/ && rm -rf "$R"
