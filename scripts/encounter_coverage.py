"""encounter_coverage_pct: share of the OSM walkable samples (every 5 m, data/derived/osm_targets.json) that lie within
60 m of an encounter zone's edge (site/app/game/encounters.json: {x, y, r} in the world frame = BNG - manifest origin).
  .venv/bin/python -I scripts/encounter_coverage.py [site_dir | live_url]   -> {"encounter_coverage_pct": n}
A URL (the live GitHub Pages build) is read over HTTP; no encounters file there -> 0."""
import json, os, sys, urllib.request
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
site = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "site")

def load(rel):
    if site.startswith("http"):
        with urllib.request.urlopen(site.rstrip("/") + "/" + rel, timeout=15) as r:
            return json.loads(r.read())
    return json.load(open(os.path.join(site, rel)))


try:
    enc = load("app/game/encounters.json")
except Exception:
    print(json.dumps({"encounter_coverage_pct": 0})); sys.exit()
enc = enc.get("encounters", enc) if isinstance(enc, dict) else enc
o = load("manifest.json")["origin"]
s = np.array([p[:2] for p in json.load(open(os.path.join(ROOT, "data/derived/osm_targets.json")))["walk"]["samples"]], float)
s -= [o["e0"], o["n0"]]
hit = np.zeros(len(s), bool)
for e in enc:
    hit |= np.hypot(s[:, 0] - e["x"], s[:, 1] - e["y"]) <= 60 + float(e.get("r", 0))
print(json.dumps({"encounter_coverage_pct": round(100.0 * hit.mean(), 2)}))
