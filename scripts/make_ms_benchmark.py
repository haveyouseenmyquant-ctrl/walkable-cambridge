"""Freeze the 40-photo held-out Market Square set for market_square_realism / market_square_photo_match (run ONCE).

    .venv/bin/python -I scripts/make_ms_benchmark.py

Zone: within 90 m of 52.2053N, 0.1190E. Candidates: perspective Mapillary photos (SfM pose) from the cached listing
(data/raw/mapillary_list.json) whose camera is inside the zone and within 4 m of an OSM walkable-way sample, with the
same pose/FOV limits as make_benchmark.py. 40 are spread over position and heading (farthest-point sampling in
(x, y, 12 cos h, 12 sin h)), at most one per sequence per 15 m. Photos of the 200-photo benchmark may be chosen too
(they are already held out). Writes data/benchmark/market_square.json (views, same format as benchmark.json),
photos into data/benchmark/photos_ms/, and data/benchmark/heldout_ms.json (images + same-sequence frames within 15 m),
which every world builder must exclude in addition to heldout.json.
"""
import json
import math
import os
import sys

import numpy as np
from pyproj import Proj, Transformer
from scipy.spatial import cKDTree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_benchmark as MB  # noqa: E402

ROOT = MB.ROOT
OUT = os.path.join(ROOT, "data/benchmark")
CENTRE = (0.1190, 52.2053)
R = 90.0
N_VIEWS = 40


def main():
    if os.path.exists(os.path.join(OUT, "market_square.json")) and "--force" not in sys.argv:
        sys.exit("already frozen (data/benchmark/market_square.json)")
    tg = json.load(open(os.path.join(ROOT, "data/derived/osm_targets.json")))
    wtree = cKDTree(np.array([[s[0], s[1]] for s in tg["walk"]["samples"]]))
    tf = Transformer.from_crs(4326, 27700, always_xy=True)
    bng = Proj("EPSG:27700")
    c0 = tf.transform(*CENTRE)
    cand = []
    for im in json.load(open(os.path.join(ROOT, "data/raw/mapillary_list.json"))):
        if im.get("is_pano") or im.get("camera_type") not in (None, "perspective") or not im.get("computed_geometry"):
            continue
        if im.get("computed_compass_angle") is None or not im.get("thumb_1024_url"):
            continue
        lo, la = im["computed_geometry"]["coordinates"]
        e, n = tf.transform(lo, la)
        if math.hypot(e - c0[0], n - c0[1]) > R or wtree.query([e, n])[0] > 4.0:
            continue
        hd, pt = MB.pose(im)
        conv = bng.get_factors(lo, la).meridian_convergence
        w, h = im.get("width") or 4, im.get("height") or 3
        f = (im.get("camera_parameters") or [None])[0]
        hfov = math.degrees(2 * math.atan(w / (2 * f * max(w, h)))) if f else 70.0
        if not (30 <= hfov <= 110) or abs(pt) > 25:
            continue
        cand.append(dict(id=im["id"], e=e, n=n, heading=(hd - conv) % 360, pitch=pt, hfov=hfov, w=w, h=h,
                         seq=im.get("sequence"), captured_at=im.get("captured_at"),
                         creator=(im.get("creator") or {}).get("username"), url=im["thumb_1024_url"]))
    print("candidates", len(cand), file=sys.stderr)
    F = np.array([[c["e"], c["n"], 12 * math.cos(math.radians(c["heading"])), 12 * math.sin(math.radians(c["heading"]))] for c in cand])
    chosen = [int(np.argmin(((F[:, :2] - c0) ** 2).sum(1)))]
    dmin = np.sqrt(((F - F[chosen[0]]) ** 2).sum(1))
    while len(chosen) < N_VIEWS and dmin.max() > 0:
        i = int(np.argmax(dmin))
        if all(not (cand[j]["seq"] == cand[i]["seq"] and np.hypot(*(F[i, :2] - F[j, :2])) < 15) for j in chosen):
            chosen.append(i)
            dmin = np.minimum(dmin, np.sqrt(((F - F[i]) ** 2).sum(1)))
        else:
            dmin[i] = 0
    os.makedirs(os.path.join(OUT, "photos_ms"), exist_ok=True)
    man = json.load(open(os.path.join(ROOT, "site/manifest.json")))["origin"]
    views = []
    for i in chosen:
        c = cand[i]
        p = os.path.join(OUT, "photos_ms", f"{c['id']}.jpg")
        if not os.path.exists(p):
            open(p, "wb").write(MB.get(c["url"]))
        views.append(dict(id=c["id"], x=round(c["e"] - man["e0"], 2), y=round(c["n"] - man["n0"], 2),
                          e=round(c["e"], 2), n=round(c["n"], 2), heading=round(c["heading"], 2), pitch=round(c["pitch"], 2),
                          hfov=round(c["hfov"], 2), w=c["w"], h=c["h"], seq=c["seq"], captured_at=c["captured_at"],
                          creator=c["creator"], licence="CC-BY-SA 4.0", source=f"https://www.mapillary.com/app/?pKey={c['id']}",
                          dist_centre_m=round(float(np.hypot(c["e"] - c0[0], c["n"] - c0[1])), 1)))
    views.sort(key=lambda v: v["dist_centre_m"])
    json.dump(views, open(os.path.join(OUT, "market_square.json"), "w"), indent=1)
    held = {"images": [v["id"] for v in views], "sequence_near": [[v["seq"], v["e"], v["n"], 15] for v in views]}
    json.dump(held, open(os.path.join(OUT, "heldout_ms.json"), "w"))
    print(json.dumps({"views": len(views), "candidates": len(cand)}))


if __name__ == "__main__":
    main()
