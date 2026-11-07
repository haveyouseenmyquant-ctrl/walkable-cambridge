"""Build the frozen, held-out 200-photo benchmark for photo_match_score (run ONCE; never re-run to change it).

    MAPILLARY_TOKEN=MLY|... .venv/bin/python -I scripts/make_benchmark.py

1. Lists every Mapillary image in the study area (Graph API, 0.002 deg cells).
2. Keeps perspective (non-panorama) photos with a computed pose, inside the study area and within 4 m of an OSM
   walkable-way sample (data/derived/osm_targets.json).
3. Spreads 200 evenly over the walkable network: farthest-point sampling over the candidates, seeded at the one
   nearest Great St Mary's, at most one photo per Mapillary sequence per 50 m.
4. Downloads the 1024 px thumbnails to data/benchmark/photos/<id>.jpg and writes data/benchmark/benchmark.json
   (pose in the world frame + credit) and data/benchmark/heldout.json (image and sequence ids the world builders
   must never use: these images, and any image of the same sequence within 15 m of one).
Photos: Mapillary contributors, CC-BY-SA 4.0.
"""
import json
import math
import os
import sys
import time
import urllib.parse
import urllib.request

import numpy as np
from pyproj import Proj, Transformer
from scipy.spatial import cKDTree
from shapely import wkt
from shapely.geometry import Point

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data/benchmark")
S, W, N, E = 52.1975, 0.1080, 52.2125, 0.1330
GSM = (0.1183, 52.2052)
N_VIEWS = 200
FIELDS = "id,computed_geometry,computed_compass_angle,computed_rotation,camera_type,camera_parameters,is_pano,width,height,captured_at,sequence,creator,thumb_1024_url"


def token():
    t = os.environ.get("MAPILLARY_TOKEN")
    p = os.path.join(ROOT, "data/mapillary_token")
    if not t and os.path.exists(p):
        t = open(p).read().strip()
    if not t:
        sys.exit("set MAPILLARY_TOKEN or write data/mapillary_token")
    return t


def get(url):
    for i in range(5):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "walkable-cambridge"}), timeout=60) as r:
                return r.read()
        except Exception as e:  # rate limits / timeouts: back off
            print("retry", i, e, file=sys.stderr)
            time.sleep(5 * (i + 1))
    raise RuntimeError(url)


def list_images(tok):
    cache = os.path.join(ROOT, "data/raw/mapillary_list.json")
    if os.path.exists(cache):
        return json.load(open(cache))
    imgs, step = {}, 0.002
    for la in np.arange(S, N, step):
        for lo in np.arange(W, E, step):
            bbox = f"{lo:.4f},{la:.4f},{min(lo + step, E):.4f},{min(la + step, N):.4f}"
            q = urllib.parse.urlencode({"access_token": tok, "fields": FIELDS, "bbox": bbox, "limit": 2000})
            d = json.loads(get("https://graph.mapillary.com/images?" + q))["data"]
            for im in d:
                imgs[im["id"]] = im
            print(bbox, len(d), len(imgs), file=sys.stderr)
    os.makedirs(os.path.dirname(cache), exist_ok=True)
    json.dump(list(imgs.values()), open(cache, "w"))
    return list(imgs.values())


def rodrigues(r):
    r = np.asarray(r, float)
    th = np.linalg.norm(r)
    if th < 1e-12:
        return np.eye(3)
    k = r / th
    K = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    return np.eye(3) + math.sin(th) * K + (1 - math.cos(th)) * K @ K


def pose(im):
    """(true heading deg, pitch deg). OpenSfM: world (ENU) -> camera rotation; camera looks along +z."""
    if im.get("computed_rotation"):
        d = rodrigues(im["computed_rotation"]).T @ np.array([0, 0, 1.0])
        return math.degrees(math.atan2(d[0], d[1])) % 360, math.degrees(math.asin(max(-1, min(1, d[2]))))
    return im["computed_compass_angle"] % 360, 0.0


def main():
    if os.path.exists(os.path.join(OUT, "benchmark.json")) and "--force" not in sys.argv:
        sys.exit("benchmark already frozen (data/benchmark/benchmark.json)")
    tok = token()
    tg = json.load(open(os.path.join(ROOT, "data/derived/osm_targets.json")))
    area = wkt.loads(tg["area_bng_wkt"])
    walk = np.array([[s[0], s[1]] for s in tg["walk"]["samples"]])
    wtree = cKDTree(walk)
    tf = Transformer.from_crs(4326, 27700, always_xy=True)
    bng = Proj("EPSG:27700")
    cand = []
    for im in list_images(tok):
        if im.get("is_pano") or im.get("camera_type") not in (None, "perspective") or not im.get("computed_geometry"):
            continue
        if im.get("computed_compass_angle") is None or not im.get("thumb_1024_url"):
            continue
        lo, la = im["computed_geometry"]["coordinates"]
        e, n = tf.transform(lo, la)
        if not area.contains(Point(e, n)) or wtree.query([e, n])[0] > 4.0:
            continue
        hd, pt = pose(im)
        conv = bng.get_factors(lo, la).meridian_convergence   # grid north is this many deg east of true north
        w, h = im.get("width") or 4, im.get("height") or 3
        f = (im.get("camera_parameters") or [None])[0]
        hfov = math.degrees(2 * math.atan(w / (2 * f * max(w, h)))) if f else 70.0
        if not (30 <= hfov <= 110) or abs(pt) > 25:
            continue
        cand.append(dict(id=im["id"], e=e, n=n, heading=(hd - conv) % 360, pitch=pt, hfov=hfov, w=w, h=h,
                         seq=im.get("sequence"), captured_at=im.get("captured_at"),
                         creator=(im.get("creator") or {}).get("username"), url=im["thumb_1024_url"]))
    print("candidates", len(cand), file=sys.stderr)
    P = np.array([[c["e"], c["n"]] for c in cand])
    g = tf.transform(*GSM)
    chosen = [int(np.argmin(((P - g) ** 2).sum(1)))]
    dmin = np.sqrt(((P - P[chosen[0]]) ** 2).sum(1))
    while len(chosen) < N_VIEWS and dmin.max() > 0:
        i = int(np.argmax(dmin))
        ok = all(not (cand[j]["seq"] == cand[i]["seq"] and np.hypot(*(P[i] - P[j])) < 50) for j in chosen)
        if ok:
            chosen.append(i)
            dmin = np.minimum(dmin, np.sqrt(((P - P[i]) ** 2).sum(1)))
        else:
            dmin[i] = 0
    os.makedirs(os.path.join(OUT, "photos"), exist_ok=True)
    man = json.load(open(os.path.join(ROOT, "site/manifest.json")))["origin"]
    views = []
    for i in chosen:
        c = cand[i]
        open(os.path.join(OUT, "photos", f"{c['id']}.jpg"), "wb").write(get(c["url"]))
        views.append(dict(id=c["id"], x=round(c["e"] - man["e0"], 2), y=round(c["n"] - man["n0"], 2),
                          e=round(c["e"], 2), n=round(c["n"], 2), heading=round(c["heading"], 2), pitch=round(c["pitch"], 2),
                          hfov=round(c["hfov"], 2), w=c["w"], h=c["h"], seq=c["seq"], captured_at=c["captured_at"],
                          creator=c["creator"], licence="CC-BY-SA 4.0", source=f"https://www.mapillary.com/app/?pKey={c['id']}",
                          dist_gsm_m=round(float(np.hypot(c["e"] - g[0], c["n"] - g[1])), 1)))
    views.sort(key=lambda v: v["dist_gsm_m"])
    json.dump(views, open(os.path.join(OUT, "benchmark.json"), "w"), indent=1)
    held = {"images": [v["id"] for v in views], "sequence_near": [[v["seq"], v["e"], v["n"], 15] for v in views]}
    json.dump(held, open(os.path.join(OUT, "heldout.json"), "w"))
    print(json.dumps({"views": len(views), "candidates": len(cand)}))


if __name__ == "__main__":
    main()
