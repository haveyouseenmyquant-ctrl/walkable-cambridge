"""Connector repair: link enclosed walkable pockets to the reachable network.

Some OSM walkways sit in courts or on islands whose access (a door, a gate arch, a culvert) is not mapped,
so the extruded world seals them off. This reads the walk grid and missed samples written by
`kpi.py --verbose` and, for each unreachable pocket, adds a short straight connector (BNG line) from the
missed sample nearest to reachable ground to that ground. build.py cuts a ground-floor passage along each
connector through the buildings it crosses and paves it where it crosses water.
Connectors accumulate in data/derived/connectors.json (committed). Usage: kpi.py site --verbose; connectors.py
"""
import json, os, sys
import numpy as np
from scipy import ndimage

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data/derived/connectors.json")
MAX_LEN = 30.0   # longest connector (m)

d = np.load(os.path.join(ROOT, "data/derived/walk_grid.npz"))
F, R = d["free"], d["reach"]
gx0, gy0, c = float(d["gx0"]), float(d["gy0"]), float(d["cell"])
H, W = F.shape
misses = json.load(open(os.path.join(ROOT, "data/derived/walk_misses.json")))
dist, (ij, ii) = ndimage.distance_transform_edt(~R, return_indices=True)
lab, _ = ndimage.label(F & ~R)

groups = {}
for x, y, way, _ in misses:
    i, j = int((x - gx0) / c), int((y - gy0) / c)
    r = 2
    win = lab[max(j - r, 0):j + r + 1, max(i - r, 0):i + r + 1]
    comp = int(win.max()) if win.max() > 0 else None
    key = ("c", comp) if comp else ("p", way, round(x), round(y))
    dd = dist[j, i] * c
    if key not in groups or dd < groups[key][0]:
        groups[key] = (dd, x, y, way, gx0 + (ii[j, i] + 0.5) * c, gy0 + (ij[j, i] + 0.5) * c)

old = json.load(open(OUT))["connectors"] if os.path.exists(OUT) else []
seen = {tuple(o.get("from", o["line"][0])) for o in old}
new = []
for dd, x, y, way, tx, ty in groups.values():
    if dd > MAX_LEN or (round(x, 2), round(y, 2)) in seen:
        continue
    v = np.array([tx - x, ty - y]); n = np.linalg.norm(v)
    if n < 1e-6:
        continue
    e = np.array([tx, ty]) + v / n * 1.5   # run 1.5 m into the reachable ground and 1.5 m into the pocket
    b = np.array([x, y]) - v / n * 1.5
    new.append({"way": way, "from": [round(x, 2), round(y, 2)], "line": [[round(float(b[0]), 2), round(float(b[1]), 2)], [round(float(e[0]), 2), round(float(e[1]), 2)]],
                "len": round(float(n) + 3, 1)})
json.dump({"note": __doc__.strip().splitlines()[0], "connectors": old + new}, open(OUT, "w"), indent=0)
print(f"{len(groups)} pockets, {len(new)} new connectors, {len(old) + len(new)} total", file=sys.stderr)
