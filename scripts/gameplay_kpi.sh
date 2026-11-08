#!/bin/bash
# gameplay_judged KPI for the local build, cached per build hash: data/benchmark/scores/<hash>_gameplay.json
# Records a fixed 60 s scripted combat clip per class (scripts/gameplay_clip.mjs: 12 frames + event log), then a Claude
# judge scores each clip 0-10 on a fixed 7-item rubric (scripts/gameplay_judge.py); KPI = mean over classes x 10.
#   scripts/gameplay_kpi.sh [-f]
cd "$(dirname "$0")/.."
H=$(.venv/bin/python -I scripts/build_hash.py site)
OUT=data/benchmark/scores/${H}_gameplay.json
[ -s "$OUT" ] && [ "$1" != "-f" ] && { cat "$OUT"; exit 0; }
TMP=$(mktemp -d /tmp/wc_gameplay.XXXXXX)
trap 'rm -rf "$TMP"' EXIT
node scripts/gameplay_clip.mjs site "$TMP" 2>/tmp/wc_gameplay_clip.err | tail -n1 >&2
.venv/bin/python -I scripts/gameplay_judge.py "$TMP" --hash "$H" -f
