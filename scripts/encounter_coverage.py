"""encounter_coverage_pct: share of the OSM walkable samples (every 5 m, data/derived/osm_targets.json) that lie within
60 m of an encounter zone's edge (site/app/game/encounters.json: {x, y, r} in the world frame = BNG - manifest origin).
  .venv/bin/python -I scripts/encounter_coverage.py [site_dir]   -> {"encounter_coverage_pct": n}"""
import json, os, sys
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
site = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "site")
f = os.path.join(site, "app/game/encounters.json")
if not os.path.exists(f):
    print("{}"); sys.exit()
enc = json.load(open(f))
enc = enc.get("encounters", enc) if isinstance(enc, dict) else enc
o = json.load(open(os.path.join(site, "manifest.json")))["origin"]
s = np.array([p[:2] for p in json.load(open(os.path.join(ROOT, "data/derived/osm_targets.json")))["walk"]["samples"]], float)
s -= [o["e0"], o["n0"]]
hit = np.zeros(len(s), bool)
for e in enc:
    hit |= np.hypot(s[:, 0] - e["x"], s[:, 1] - e["y"]) <= 60 + float(e.get("r", 0))
print(json.dumps({"encounter_coverage_pct": round(100.0 * hit.mean(), 2)}))
