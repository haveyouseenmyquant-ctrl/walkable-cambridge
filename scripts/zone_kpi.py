"""facade_geometry_match_pct and painted_detail_pct for the zone being worked on (Market Square).

    .venv/bin/python -I scripts/zone_kpi.py [site_dir]

Walls: data/annotations/market_square/walls.json (street-facing walls within 90 m of 52.2053N 0.1190E).
- facade_geometry_match_pct: per wall, agreement between the annotation (data/annotations/market_square/way_*.json,
  made from non-held-out photos) and the 3D elements the build actually emitted (site/zone/zone.json "walls"):
  mean over [window, door, shopfront, dormer] (storeys not yet counted separately) of min(model, annot) / max(model, annot) (1 if both 0).
  Walls without an annotation count as 0. KPI = length-weighted mean x 100.
- painted_detail_pct (lower is better): wall area (length x height) whose windows/doors exist only as a photo
  texture: walls carrying a photo-baked facade quad (site/facades/*.bin) and no modelled facade skin, divided by the
  total wall area, x 100.
"""
import glob
import json
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "site")
A = os.path.join(ROOT, "data/annotations/market_square")
TYPES = ("window", "door", "shopfront", "dormer")


def main():
    walls = json.load(open(os.path.join(A, "walls.json")))["walls"]
    ann = {}
    for f in glob.glob(os.path.join(A, "way_*.json")):
        try:
            for w in json.load(open(f)).get("walls", []):
                ann[w["id"]] = w
        except Exception:
            pass
    zp = os.path.join(SITE, "zone/zone.json")
    gp = os.path.join(ROOT, "data/derived/facade_geometry.json")   # per wall, written by zone_build.py with the build
    model = {}
    if os.path.exists(zp) and os.path.exists(gp):
        for w in json.load(open(gp))["walls"]:
            model[w["id"]] = dict(counts=w.get("elements", {}), skin=w.get("tris", 0) > 0)
    quads = []
    for f in glob.glob(os.path.join(SITE, "facades/*.bin")):
        q = np.fromfile(f, "<f4").reshape(-1, 4, 5)
        quads.append(q[:, :, :2].astype(float).mean(1))
    Q = np.concatenate(quads) if quads else np.zeros((0, 2))
    num = den = painted = area = 0.0
    for w in walls:
        L, H = w["length"], max(w["height"], 0)
        p0, p1 = np.array(w["p0"]), np.array(w["p1"])
        d = (p1 - p0) / L
        a = ann.get(w["id"])
        m = model.get(w["id"])
        score = 0.0
        if a and m:
            ac = {t: sum(1 for e in a.get("elements", []) if e.get("type") == t) for t in TYPES}
            mc = m.get("counts", {})
            parts = [(ac[t], mc.get(t, 0)) for t in TYPES]
            score = float(np.mean([1.0 if x == y == 0 else min(x, y) / max(x, y) for x, y in parts]))
        num += score * L; den += L
        area += L * H
        if not (m and m.get("skin")) and len(Q):
            v = Q - p0
            along, off = v[:, 0] * d[0] + v[:, 1] * d[1], np.abs(v[:, 0] * d[1] - v[:, 1] * d[0])
            if np.any((along > 0) & (along < L) & (off < 0.6)):
                painted += L * H
    print(json.dumps({"facade_geometry_match_pct": round(100 * num / max(den, 1e-9), 2),
                      "painted_detail_pct": round(100 * painted / max(area, 1e-9), 2)}))


if __name__ == "__main__":
    main()
