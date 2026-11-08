#!/bin/bash
# Prints one JSON object of KPI readings. Measures the published site if SITE_URL exists
# (one line: the GitHub Pages URL), otherwise the local build in site/.
# Rules: FORMAT.md. Targets (denominators) come from the fixed OSM extract via scripts/osm_targets.py.
# load_seconds / site_errors come from service.sh's hourly headless-Chrome run (60 s walk), if under 3 h old.
cd "$(dirname "$0")"
PY=.venv/bin/python
[ -f data/derived/osm_targets.json ] || $PY -I scripts/osm_targets.py >/dev/null 2>&1
SRC=site
[ -s SITE_URL ] && SRC=$(head -n1 SITE_URL | tr -d '[:space:]')
export BUILD_HASH=$($PY -I scripts/build_hash.py "$SRC" 2>/dev/null)
# kpi.py reads every tile (~25-50 s); its result depends only on the build, so cache it per build hash.
KC=data/derived/kpi_cache_$BUILD_HASH.json
if [ -n "$BUILD_HASH" ] && [ -s "$KC" ]; then cat "$KC"; else
  K=$($PY -I scripts/kpi.py "$SRC" 2>/dev/null); echo "$K"
  [ -n "$BUILD_HASH" ] && echo "$K" | grep -q walkable_coverage_pct && echo "$K" > "$KC"
fi | $PY -I -c '
import json, os, sys, time
out = json.loads(sys.stdin.read())
p = "data/derived/browser_kpi.json"
if os.path.exists(p):
    b = json.load(open(p))
    if time.time() - b["ts"] < 3 * 3600:
        out.update(b["result"])
# photo_match_score / judged_realism / visual_quality: cached per build hash by scripts/bench.sh (benchmark renders + DINOv2)
# roof_match_pct: cached per build hash by scripts/roof_match.py (reads every GLB; run by publish.sh and bench.sh)
h = os.environ.get("BUILD_HASH", "")
for k, suf in (("photo_match_score", ""), ("judged_realism", "_judge"), ("visual_quality", "_quality"), ("roof_match_pct", "_roof")):
    f = "data/benchmark/scores/%s%s.json" % (h, suf)
    if h and os.path.exists(f):
        out[k] = json.load(open(f))[k]
print(json.dumps(out))'
