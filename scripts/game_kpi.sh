#!/bin/bash
# Game KPIs for the local build (= the live one after publish.sh), cached per build hash for measure.sh:
#   data/benchmark/scores/<hash>_game.json  {mob_types, bosses, equipment_effects, playable_classes, playtest_pass_pct, boss_ttk_spread_pct}
# mob_types counts regular mob types that pass the automated combat test (spawn, attack, take damage, die);
# equipment_effects counts items whose effect test passes. playable_classes / playtest_pass_pct / boss_ttk_spread_pct
# come from the headless route bot (scripts/playtest.mjs: 5 runs per class over a fixed 5-encounter route + the Bellwarden).
cd "$(dirname "$0")/.."
H=$(.venv/bin/python -I scripts/build_hash.py site)
OUT=data/benchmark/scores/${H}_game.json
[ -s "$OUT" ] && [ "$1" != "-f" ] && { cat "$OUT"; exit 0; }
M=$(node scripts/test_mobs.mjs site 2>/tmp/wc_test_mobs.err | tail -n1)
I=$(node scripts/test_items.mjs site 2>/tmp/wc_test_items.err | tail -n1)
P=$(node scripts/playtest.mjs site 2>/tmp/wc_playtest.err | tail -n1)
.venv/bin/python -I -c '
import json, sys
out = {}
try:
    m = json.loads(sys.argv[1]); out["mob_types"] = m["mob_types_ok"]; out["bosses"] = m["bosses_ok"]
except Exception: pass
try: out["equipment_effects"] = json.loads(sys.argv[2])["equipment_effects"]
except Exception: pass
try:
    p = json.loads(sys.argv[3])
    for k in ("playable_classes", "playtest_pass_pct", "boss_ttk_spread_pct", "boss_ttk_median_s"):
        if p.get(k) is not None: out[k] = p[k]
except Exception: pass
print(json.dumps(out))' "$M" "$I" "$P" | tee "$OUT.tmp"
grep -q '[0-9]' "$OUT.tmp" && mv "$OUT.tmp" "$OUT" || rm -f "$OUT.tmp"
