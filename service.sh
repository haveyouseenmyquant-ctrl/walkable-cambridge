#!/bin/bash
# Hourly checks of the published site:
#  - headless Chrome (swiftshader): load_seconds, site_errors over the moves test + a 60 s scripted walk
#  - Chrome on the Mac's GPU (ANGLE Metal, a 1920x1080 window: headless throttles rAF): fps_median over a 60 s walk
#  - benchmark: if data/benchmark/benchmark.json exists and the live build has no cached score, render + score it
# The runs take longer than measure.sh may take, so measure.sh reads data/derived/browser_kpi.json (if under 3 h old)
# and data/benchmark/scores/<build_hash>.json.
cd "$(dirname "$0")"
LAST=0
while true; do
  SRC=site
  [ -s SITE_URL ] && SRC=$(head -n1 SITE_URL | tr -d '[:space:]')
  # session 31: the Market Square benchmark (main KPI) first, every 10 min check for a new live build;
  # the browser checks hourly, then the 200-view benchmark
  # session 42 (Gaspard): game KPIs + gameplay_judged for each new live hash. The tests run on local site/, which
  # equals the live build after publish.sh; only run when the hashes agree so the cache is keyed to the live build.
  # session 55: prefer data/derived/live_site (publish.sh's APFS-clone snapshot of the published build), so sessions
  # editing site/ no longer block the live build's game scores
  LH=$(.venv/bin/python -I scripts/build_hash.py "$SRC" 2>/dev/null)
  GS=site
  [ -d data/derived/live_site ] && [ "$(.venv/bin/python -I scripts/build_hash.py data/derived/live_site 2>/dev/null)" = "$LH" ] && GS=data/derived/live_site
  SH=$(.venv/bin/python -I scripts/build_hash.py $GS 2>/dev/null)
  if [ -n "$LH" ] && [ "$LH" = "$SH" ]; then
    [ -s data/benchmark/scores/${LH}_game.json ] || WC_SITE=$GS scripts/game_kpi.sh 2>&1 | tail -n1
    [ -x scripts/gameplay_kpi.sh ] && [ ! -s data/benchmark/scores/${LH}_gameplay.json ] && WC_SITE=$GS scripts/gameplay_kpi.sh 2>&1 | tail -n1
  fi
  [ -f data/benchmark/market_square.json ] && scripts/ms_bench.sh "$SRC" 2>&1 | tail -n2
  if [ $(( $(date +%s) - LAST )) -lt 3300 ]; then
    [ -f data/benchmark/benchmark.json ] && scripts/bench.sh "$SRC" 2>&1 | tail -n2
    sleep 600; continue
  fi
  LAST=$(date +%s)
  OUT=$(node scripts/browser_test.mjs "$SRC" --no-moves 2>/tmp/wc_browser_test.err | tail -n1)
  FPS=$(WC_GPU=1 node scripts/browser_test.mjs "$SRC" 2>/tmp/wc_browser_gpu.err | tail -n1)
  if echo "$OUT" | grep -q load_seconds; then
    F=$(echo "$FPS" | .venv/bin/python -I -c 'import json,sys
try: print(json.dumps({"fps_median": json.loads(sys.stdin.read())["fps_median"]}))
except Exception: print("{}")')
    R=$(.venv/bin/python -I -c 'import json,sys; a=json.loads(sys.argv[1]); a.update(json.loads(sys.argv[2])); print(json.dumps(a))' "$OUT" "$F")
    echo "{\"ts\": $(date +%s), \"src\": \"$SRC\", \"result\": $R}" > data/derived/browser_kpi.json
    echo "$(date -u +%FT%TZ) $R"
  else
    echo "$(date -u +%FT%TZ) browser test failed: $(tail -n3 /tmp/wc_browser_test.err)"
  fi
  [ -f data/benchmark/benchmark.json ] && scripts/bench.sh "$SRC" 2>&1 | tail -n2
  sleep 600
done
