"""Ring encounters, centre outwards (session 41): greedy cover of the OSM walkable samples within --radius m of the
Market Square centre by encounter zones placed on walkable samples, so every sample lies within 60 m of one.
Hand-placed encounters in site/app/game/encounters.json are kept; generated ones ("gen": true) are replaced.
  .venv/bin/python -I scripts/gen_encounters.py [--radius 300] [--spacing 60]"""
import argparse, json, math, os
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ap = argparse.ArgumentParser()
ap.add_argument("--radius", type=float, default=300)
ap.add_argument("--spacing", type=float, default=60)
ap.add_argument("--dry", action="store_true")
a = ap.parse_args()

F = os.path.join(ROOT, "site/app/game/encounters.json")
enc = [e for e in json.load(open(F)) if not e.get("gen")]
o = json.load(open(os.path.join(ROOT, "site/manifest.json")))["origin"]
s = np.array([p[:2] for p in json.load(open(os.path.join(ROOT, "data/derived/osm_targets.json")))["walk"]["samples"]], float)
s -= [o["e0"], o["n0"]]
C = np.array([-103.0, 57.0])          # Market Square centre in the world frame
s = s[np.hypot(*(s - C).T) <= a.radius]
cov = np.zeros(len(s), bool)
for e in enc:
    cov |= np.hypot(s[:, 0] - e["x"], s[:, 1] - e["y"]) <= 60 + e.get("r", 0)

# mob mixes by setting: the river side (west, the Backs/Cam) gets wraiths and wisps, the rest the town mobs
TOWN = [["gargoyle", "ink_imp"], ["automaton", "soot_sprite"], ["statue", "bell_bats"], ["ink_imp", "crest_griffin"],
        ["bicycle_golem", "wisp"], ["soot_sprite", "gargoyle"], ["crest_griffin", "automaton"], ["bell_bats", "ink_imp"]]
RIVER = [["river_wraith", "wisp"], ["punt_revenant", "bog_hag"], ["river_wraith", "punt_revenant"], ["bog_hag", "wisp"]]
R = 5
out, k = [], 0
while not cov.all():
    # next uncovered sample nearest the centre: grows rings outwards
    i = np.flatnonzero(~cov)
    j = i[np.argmin(np.hypot(*(s[i] - C).T))]
    # move the zone up to spacing/2 outwards along the street so it covers more new samples
    d = np.hypot(*(s - s[j]).T)
    near = np.flatnonzero((d <= a.spacing / 2) & ~cov)
    best, bestn = j, -1
    for c in near[:: max(1, len(near) // 30)]:
        n = int(((np.hypot(*(s - s[c]).T) <= 60 + R) & ~cov).sum())
        if n > bestn: best, bestn = c, n
    x, y = s[best]
    cov |= np.hypot(*(s - s[best]).T) <= 60 + R
    dist = math.hypot(x - C[0], y - C[1])
    pool = RIVER if x < -330 else TOWN
    out.append({"id": "gen-%03d" % k, "name": "Ring %d" % (1 + int(dist // 150)), "x": round(float(x), 1), "y": round(float(y), 1),
                "r": R, "mobs": pool[k % len(pool)], "gen": True})
    k += 1
if not a.dry:
    json.dump(enc + out, open(F, "w"), indent=0)
print(json.dumps({"hand": len(enc), "generated": len(out), "radius": a.radius}))
