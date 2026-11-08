#!/bin/bash
# Game KPIs for the local build (= the live one after publish.sh), cached per build hash for measure.sh:
#   data/benchmark/scores/<hash>_game.json  {mob_types, bosses, equipment_effects}
# mob_types counts regular mob types that pass the automated combat test (spawn, attack, take damage, die);
# equipment_effects counts items whose effect test passes. playable_classes / playtest_pass_pct need the headless
# route bot (not written yet), so they are not reported.
cd "$(dirname "$0")/.."
H=$(.venv/bin/python -I scripts/build_hash.py site)
OUT=data/benchmark/scores/${H}_game.json
[ -s "$OUT" ] && [ "$1" != "-f" ] && { cat "$OUT"; exit 0; }
M=$(node scripts/test_mobs.mjs site 2>/tmp/wc_test_mobs.err | tail -n1)
I=$(node scripts/test_items.mjs site 2>/tmp/wc_test_items.err | tail -n1)
.venv/bin/python -I -c '
import json, sys
out = {}
try:
    m = json.loads(sys.argv[1]); out["mob_types"] = m["mob_types_ok"]; out["bosses"] = m["bosses_ok"]
except Exception: pass
try: out["equipment_effects"] = json.loads(sys.argv[2])["equipment_effects"]
except Exception: pass
print(json.dumps(out))' "$M" "$I" | tee "$OUT.tmp"
grep -q '[0-9]' "$OUT.tmp" && mv "$OUT.tmp" "$OUT" || rm -f "$OUT.tmp"
