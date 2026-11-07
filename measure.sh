#!/bin/bash
# Prints one JSON object of KPI readings. Measures the published site if SITE_URL exists
# (one line: the GitHub Pages URL), otherwise the local build in site/.
# Rules: FORMAT.md. Targets (denominators) come from the fixed OSM extract via scripts/osm_targets.py.
cd "$(dirname "$0")"
PY=.venv/bin/python
[ -f data/derived/osm_targets.json ] || $PY -I scripts/osm_targets.py >/dev/null 2>&1
SRC=site
[ -s SITE_URL ] && SRC=$(head -n1 SITE_URL | tr -d '[:space:]')
exec $PY -I scripts/kpi.py "$SRC" 2>/dev/null
