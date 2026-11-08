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
# roof_match_pct needs the GLBs on disk: computed from site/ when it is the same build as SRC
[ -f $B/scores/${HASH}_roof.json ] || { [ "$(.venv/bin/python -I scripts/build_hash.py site)" = "$HASH" ] && .venv/bin/python -I scripts/roof_match.py site || true; }
[ -f "$OUT" ] && [ -f $B/scores/${HASH}_judge.json ] && [ -f $B/scores/${HASH}_quality.json ] && { head -c 300 "$OUT"; echo; exit 0; }
R=/tmp/wc_renders_$HASH
mkdir -p $B/scores $B/renders
if [ ! -f "$OUT" ]; then
  # 4 parallel swiftshader workers (~8 min total); views already in $R are skipped, so a worker that crashed
  # (e.g. while the machine was busy with an A/B run) is simply re-run for its missing views, up to 3 rounds
  W=${BENCH_WORKERS:-4}
  for round in 1 2 3; do
    [ "$(ls "$R" 2>/dev/null | wc -l)" -ge 200 ] && break
    for k in $(seq 0 $((W - 1))); do
      IDS=$(.venv/bin/python -I -c "import json,sys; v=json.load(open('$B/benchmark.json')); v=v['views'] if isinstance(v,dict) else v; print(','.join(str(x['id']) for x in v[$k::$W]))")
      node scripts/photo_render.mjs "$SRC" $B/benchmark.json "$R" --only "$IDS" 2>>/tmp/wc_bench_render.err &
    done
    wait
  done
  [ "$(ls "$R" | wc -l)" -ge 200 ] || { echo "renders incomplete ($(ls "$R" | wc -l)/200)" >&2; exit 1; }
  # session 44: the live build can change while rendering (a publish mid-run); never cache mixed renders
  [ "$(.venv/bin/python -I scripts/build_hash.py "$SRC")" = "$HASH" ] || { rm -rf "$R"; echo "build changed during render" >&2; exit 1; }
  .venv/bin/python -I scripts/photo_score.py $B/photos "$R" --out "$OUT"
fi
# judged_realism (50 blind A/B views) and visual_quality (30 views, rubric): Claude vision judge, scripts/judge.py
[ -d "$R" ] || R=$B/renders/latest
[ -f $B/scores/${HASH}_judge.json ] || .venv/bin/python -I scripts/judge.py "$HASH" "$R" --only realism
[ -f $B/scores/${HASH}_quality.json ] || .venv/bin/python -I scripts/judge.py "$HASH" "$R" --only quality
[ "$R" = $B/renders/latest ] && exit 0
# keep a small copy of the renders for the journal's side-by-sides (overwritten each build)
rm -rf $B/renders/latest && mkdir -p $B/renders/latest && cp "$R"/*.png $B/renders/latest/ && rm -rf "$R"
