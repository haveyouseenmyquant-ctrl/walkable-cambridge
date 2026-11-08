#!/bin/bash
# A/B photo_match on the benchmark views within a distance of Great St Mary's (any site dir or URL).
#   scripts/abring.sh <label> <site_dir_or_url> <max_dist_m> [workers=4] ["<url query>"]
# Renders to /tmp/wc_ab_<label>, scores to /tmp/wc_ab_<label>.json and prints the mean.
set -euo pipefail
cd "$(dirname "$0")/.."
B=data/benchmark; L=$1; S=$2; D=$3; W=${4:-4}; Q=${5:-}; R=/tmp/wc_ab_$L
rm -rf "$R"; mkdir -p "$R"
for k in $(seq 0 $((W - 1))); do
  IDS=$(.venv/bin/python -I -c "import json; v=[x['id'] for x in json.load(open('$B/benchmark.json')) if x['dist_gsm_m'] <= $D]; print(','.join(v[$k::$W]))")
  WC_QUERY="$Q" node scripts/photo_render.mjs "$S" $B/benchmark.json "$R" --only "$IDS" 2>/dev/null &
done
wait
.venv/bin/python -I scripts/photo_score.py $B/photos "$R" --out /tmp/wc_ab_$L.json | tail -n1
