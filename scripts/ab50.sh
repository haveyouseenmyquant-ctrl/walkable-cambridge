#!/bin/bash
# A/B check of a viewer option on the 50 judge views (photo_match only, local site/).
#   scripts/ab50.sh <label> "<url query, e.g. look=v2&trees>" [workers=3]
# Renders to /tmp/wc_ab_<label>, scores to /tmp/wc_ab_<label>.json and prints the mean.
set -euo pipefail
cd "$(dirname "$0")/.."
B=data/benchmark; L=$1; Q=$2; W=${3:-3}; R=/tmp/wc_ab_$L
rm -rf "$R"; mkdir -p "$R"
for k in $(seq 0 $((W - 1))); do
  IDS=$(.venv/bin/python -I -c "import json; v=json.load(open('$B/judge_views.json')); v=v['ids'] if isinstance(v,dict) else v; print(','.join(str(x) for x in v[$k::$W]))")
  WC_QUERY="$Q" node scripts/photo_render.mjs site $B/benchmark.json "$R" --only "$IDS" 2>/dev/null &
done
wait
.venv/bin/python -I scripts/photo_score.py $B/photos "$R" --out /tmp/wc_ab_$L.json | tail -n1
