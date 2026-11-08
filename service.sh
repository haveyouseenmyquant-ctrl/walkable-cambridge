#!/bin/bash
# Hourly checks of the published site:
#  - headless Chrome (swiftshader): load_seconds, site_errors over the moves test + a 60 s scripted walk
#  - Chrome on the Mac's GPU (ANGLE Metal, a 1920x1080 window: headless throttles rAF): fps_median over a 60 s walk
#  - benchmark: if data/benchmark/benchmark.json exists and the live build has no cached score, render + score it
# The runs take longer than measure.sh may take, so measure.sh reads data/derived/browser_kpi.json (if under 3 h old)
# and data/benchmark/scores/<build_hash>.json.
cd "$(dirname "$0")"
while true; do
  SRC=site
  [ -s SITE_URL ] && SRC=$(head -n1 SITE_URL | tr -d '[:space:]')
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
  [ -f data/benchmark/market_square.json ] && scripts/ms_bench.sh "$SRC" 2>&1 | tail -n2
  sleep 3600
done
