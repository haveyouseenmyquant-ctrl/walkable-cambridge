#!/usr/bin/env python3
"""Street furniture from OSM nodes, written per tile (run after build.py; edits manifest.json in place).

  .venv/bin/python -I scripts/street_objects.py [--out site]

Object types (TYPES below; the same list defines street_objects_pct in kpi.py, with natural=tree counted against
the trees layer). Each object stands at its mapped position on the DTM. Benches, bike stands and signs face along
the nearest walkable/road way (heading = that segment's direction, radians, collision frame).
Output: <out>/objects/<tile>.bin, float32 records [x, y, z_ground, type, heading, seed, n] where n = capacity in
bike stands (bicycle_parking: capacity / 2, 1..12) else 1. Manifest tiles get "objects" / "nobjects".
"""
import json, os, sys
import numpy as np
import rasterio
from shapely.geometry import LineString, Point
from shapely.strtree import STRtree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build as B

TYPES = {   # type id: (name, predicate on tags)
    1: ("street_lamp", lambda t: t.get("highway") == "street_lamp"),
    2: ("bench", lambda t: t.get("amenity") == "bench" or t.get("leisure") == "picnic_table"),
    3: ("bollard", lambda t: t.get("barrier") in ("bollard", "rising_kerb")),
    4: ("waste_basket", lambda t: t.get("amenity") in ("waste_basket", "waste_disposal", "recycling")),
    5: ("bicycle_parking", lambda t: t.get("amenity") == "bicycle_parking"),
    6: ("post_box", lambda t: t.get("amenity") == "post_box"),
    7: ("telephone", lambda t: t.get("amenity") == "telephone" or t.get("man_made") == "telephone_box"),
    8: ("bus_stop", lambda t: t.get("highway") == "bus_stop"),
    9: ("sign", lambda t: t.get("highway") in ("traffic_sign", "milestone") or t.get("tourism") == "information"
        and t.get("information") in ("board", "map", "guidepost") or "advertising" in t),
    10: ("statue", lambda t: t.get("historic") in ("memorial", "monument")
         and t.get("memorial") not in ("plaque", "blue_plaque") or t.get("tourism") == "artwork"
         and t.get("artwork_type") in ("statue", "sculpture", "bust", None)),
    11: ("fountain", lambda t: t.get("amenity") in ("fountain", "drinking_water")),
    12: ("clock", lambda t: t.get("amenity") == "clock" and t.get("support") in ("pole", "ground", None)),
}
LAT0, LAT1, LON0, LON1 = 52.1975, 52.2125, 0.1080, 0.1330


def classify(t):
    for k, (_, f) in TYPES.items():
        if f(t):
            return k
    return 0


def objects_in_area(nodes_ll=None):
    """[(E, N, type, tags)] for every OSM node of a TYPES type inside the study area (shared with kpi.py)."""
    els = json.load(open(B.RAW))["elements"]
    from pyproj import Transformer
    tr = Transformer.from_crs(4326, 27700, always_xy=True)
    out = []
    for e in els:
        if e["type"] != "node" or not e.get("tags"):
            continue
        if not (LAT0 <= e["lat"] <= LAT1 and LON0 <= e["lon"] <= LON1):
            continue
        k = classify(e["tags"])
        if k:
            E, N = tr.transform(e["lon"], e["lat"])
            out.append((E, N, k, e["tags"]))
    return out


def main():
    objs = objects_in_area()
    dtm = rasterio.open(os.path.join(B.ROOT, "data/lidar/dtm_1m.tif"))
    D = dtm.read(1); tf = dtm.transform
    nodes, ways, _, _ = B.load_osm()
    lines = []
    for w in ways.values():
        t = w.get("tags", {})
        if "highway" in t and t["highway"] not in ("bus_stop", "platform"):
            c = B.coords(w, nodes)
            if c and len(c) >= 2:
                lines.append(LineString(c))
    tree = STRtree(lines)
    rng = np.random.default_rng(3)
    rec = []
    for E, N, k, t in objs:
        p = Point(E, N)
        i = tree.nearest(p)
        ln = lines[i]
        d = ln.project(p)
        a, b = ln.interpolate(max(d - 1, 0)), ln.interpolate(min(d + 1, ln.length))
        head = float(np.arctan2(b.y - a.y, b.x - a.x))
        # local frame: +x along the way, the way on local +y (benches, signs and bus stops face +y)
        side = np.sign((b.x - a.x) * (N - a.y) - (b.y - a.y) * (E - a.x)) or 1.0
        if k in (2, 9, 8):
            head += np.pi if side > 0 else 0.0
        if "direction" in t:
            try: head = -np.radians(float(t["direction"]))   # facing (local +y) = compass bearing
            except ValueError: pass
        n = 1
        if k == 5:
            try: n = int(t.get("capacity", "4")) // 2
            except ValueError: n = 2
            n = int(np.clip(n, 1, 12))
        r, c = int((N - tf.f) / tf.e), int((E - tf.c) / tf.a)
        zg = float(D[r, c]) if 0 <= r < D.shape[0] and 0 <= c < D.shape[1] else -9999
        rec.append((E - B.E0, N - B.N0, zg, k, head, rng.random(), n))
    rec = np.array(rec, np.float32)
    man_p = os.path.join(B.OUT, "manifest.json")
    man = json.load(open(man_p))
    os.makedirs(os.path.join(B.OUT, "objects"), exist_ok=True)
    total = 0
    for tile in man["tiles"]:
        x0, y0, x1, y1 = tile["bounds"]
        sel = (rec[:, 0] >= x0) & (rec[:, 0] < x1) & (rec[:, 1] >= y0) & (rec[:, 1] < y1) & (rec[:, 2] > -100)
        tile.pop("objects", None); tile.pop("nobjects", None)
        if sel.any():
            p = "objects/%s.bin" % tile["id"]
            rec[sel].tofile(os.path.join(B.OUT, p))
            tile["objects"], tile["nobjects"] = p, int(sel.sum()); total += int(sel.sum())
    # viewer defaults (URL params override): a layer counts towards street_objects_pct only if drawn by default
    man["layers"] = {"trees": True, "objects": True}
    json.dump(man, open(man_p, "w"), separators=(",", ":"))
    tg = [[E, N, k] for E, N, k, _ in objs]   # KPI targets: these + OSM natural=tree nodes in the study area
    els = json.load(open(B.RAW))["elements"]
    from pyproj import Transformer
    tr = Transformer.from_crs(4326, 27700, always_xy=True)
    for e in els:
        if e["type"] == "node" and e.get("tags", {}).get("natural") == "tree" and LAT0 <= e["lat"] <= LAT1 and LON0 <= e["lon"] <= LON1:
            tg.append(list(tr.transform(e["lon"], e["lat"])) + [0])
    json.dump(tg, open(os.path.join(B.ROOT, "data/derived/street_object_targets.json"), "w"))
    print("street object targets", len(tg))
    from collections import Counter
    print("objects written", total, dict(Counter(TYPES[int(k)][0] for k in rec[:, 3])), flush=True)


if __name__ == "__main__":
    main()
