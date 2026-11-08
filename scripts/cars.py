#!/usr/bin/env python3
"""Parked cars where OSM maps on-street parking (session 25). Run after street_objects.py (and again after it).

  .venv/bin/python -I scripts/cars.py [--out site] [--occ 0.8] [--lots]

Sources:
- road ways tagged parking:<side>=lane|street_side|half_on_kerb|on_kerb (or the older parking:lane:<side>=parallel|
  diagonal|perpendicular), side in left/right/both, orientation from parking:<side>:orientation;
- amenity=parking areas tagged parking=lane|street_side|layby (cars along the long axis of the area);
- with --lots also parking=surface areas (rows of perpendicular bays), off by default.
Cars stand in a row along the kerb, centre max(road_half - 1.2, 3.75) m from the way for parallel bays (a car's
half-length more for diagonal/perpendicular), every 6 m (parallel), 2.6 m
(perpendicular) or 3 m (diagonal), with occupancy --occ, never within 8 m of a road junction.
Output: appended to <out>/objects/<tile>.bin as type 13 records [x, y, z_ground, 13, heading, seed, 1] (heading =
direction of the car's long axis, radians, collision frame); earlier type 13 records are replaced, so it can rerun.
Not counted by street_objects_pct (no OSM node targets).
"""
import json, os, sys
from collections import Counter
import numpy as np
import rasterio
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build as B

CAR = 13
ON = {"lane", "street_side", "half_on_kerb", "on_kerb", "parallel", "diagonal", "perpendicular", "on_street", "yes"}
PITCH = {"parallel": 6.0, "perpendicular": 2.6, "diagonal": 3.0}
JUNC = 8.0
LANE = 2.75
OCC = float(sys.argv[sys.argv.index("--occ") + 1]) if "--occ" in sys.argv else 0.8


def side_spec(t, side):
    """(orientation, kerb_shift) if the way has parking on that side, else None."""
    for s in (side, "both"):
        v = t.get("parking:%s" % s)
        if v in ON:
            o = t.get("parking:%s:orientation" % s, "parallel")
            return (o if o in PITCH else "parallel"), (0.9 if v in ("half_on_kerb", "on_kerb") else 0.0)
        v = t.get("parking:lane:%s" % s)
        if v in PITCH:
            return v, (0.9 if t.get("parking:lane:%s:%s" % (s, v)) in ("half_on_kerb", "on_kerb") else 0.0)
    return None


def main():
    nodes, ways, _, _ = B.load_osm()
    rng = np.random.default_rng(25)
    rw = [w for w in ways.values() if w.get("tags", {}).get("highway") in B.ROAD_HALF]
    use = Counter(n for w in rw for n in set(w["nodes"]))
    inner = {n for w in rw for n in w["nodes"][1:-1]}
    junc = [Point(nodes[n]) for n, c in use.items() if n in nodes and (c >= 3 or (c == 2 and n in inner))]
    jz = unary_union([p.buffer(JUNC) for p in junc])
    cars = []   # (E, N, heading)

    def row(ln, orient, start_off=0.0):
        pitch = PITCH[orient]
        d = start_off + pitch / 2
        while d <= ln.length - pitch / 2 + 1e-6:
            a, b = ln.interpolate(max(d - 0.5, 0)), ln.interpolate(min(d + 0.5, ln.length))
            h = float(np.arctan2(b.y - a.y, b.x - a.x))
            if orient == "perpendicular": h += np.pi / 2
            elif orient == "diagonal": h += np.pi / 4
            p = ln.interpolate(d)
            if rng.random() < OCC:
                cars.append((p.x, p.y, h + (np.pi if rng.random() < 0.5 else 0.0) * (orient == "parallel")))
            d += pitch

    n_way = n_area = 0
    for w in rw:
        t = w["tags"]
        if t.get("area") == "yes":
            continue
        c = [nodes[n] for n in w["nodes"] if n in nodes]
        if len(c) < 2:
            continue
        half = B.road_half(t)
        for side in ("left", "right"):
            sp = side_spec(t, side)
            if not sp:
                continue
            orient, shift = sp
            # car centre from the way's centreline: just inside the kerb of the modelled carriageway (build.py
            # road_half, widened for parked sides since session 26), with at least one 2.75 m traffic lane beside it
            depth = 1.0 if orient == "parallel" else (2.3 if orient == "perpendicular" else 1.9)
            off = max(half - depth - 0.2, LANE + depth) + shift   # depth: half the car across the row
            ln = LineString(c).parallel_offset(off, side, join_style=2)
            for g in getattr(ln, "geoms", [ln]):
                g = g.difference(jz)
                for p in getattr(g, "geoms", [g]):
                    if p.length > PITCH[orient]:
                        row(p, orient); n_way += 1
    lots = "--lots" in sys.argv
    for w in ways.values():
        t = w.get("tags", {})
        if t.get("amenity") != "parking" or t.get("parking") not in ({"lane", "street_side", "layby"} | ({"surface"} if lots else set())):
            continue
        c = [nodes[n] for n in w["nodes"] if n in nodes]
        if len(c) < 4 or w["nodes"][0] != w["nodes"][-1]:
            continue
        poly = Polygon(c)
        if not poly.is_valid or poly.area < 8:
            continue
        r = list(poly.minimum_rotated_rectangle.exterior.coords)
        e0, e1 = np.subtract(r[1], r[0]), np.subtract(r[2], r[1])
        L, W = np.hypot(*e0), np.hypot(*e1)
        if L < W:
            e0, e1, L, W = e1, e0, W, L
            r0 = np.array(r[1])
        else:
            r0 = np.array(r[0])
        u, v = e0 / L, e1 / W
        if W < 4.0:   # a strip: one row, parallel if narrow
            orient = "parallel" if W < 3.2 else "perpendicular"
            mid = r0 + v * W / 2
            row(LineString([mid, mid + u * L]), orient); n_area += 1
        else:          # a lot: rows of perpendicular bays 5 m deep, every other pair of rows an aisle
            k = 0
            for y in np.arange(2.5, W - 2.4, 5.0):
                if k % 3 == 2:
                    k += 1; continue
                mid = r0 + v * y
                ln = LineString([mid, mid + u * L])
                seg = ln.intersection(poly.buffer(-1.0))
                for g in getattr(seg, "geoms", [seg]):
                    if g.length > 2.6 and g.geom_type == "LineString":
                        row(g, "perpendicular")
                k += 1
            n_area += 1
    dtm = rasterio.open(os.path.join(B.ROOT, "data/lidar/dtm_1m.tif"))
    D = dtm.read(1); tf = dtm.transform
    rec = []
    for E, N, h in cars:
        r, c = int((N - tf.f) / tf.e), int((E - tf.c) / tf.a)
        if 0 <= r < D.shape[0] and 0 <= c < D.shape[1]:
            rec.append((E - B.E0, N - B.N0, float(D[r, c]), CAR, h, rng.random(), 1))
    rec = np.array(rec, np.float32).reshape(-1, 7)
    man_p = os.path.join(B.OUT, "manifest.json")
    man = json.load(open(man_p))
    os.makedirs(os.path.join(B.OUT, "objects"), exist_ok=True)
    total = 0
    for tile in man["tiles"]:
        x0, y0, x1, y1 = tile["bounds"]
        old = np.zeros((0, 7), np.float32)
        if tile.get("objects"):
            old = np.fromfile(os.path.join(B.OUT, tile["objects"]), np.float32).reshape(-1, 7)
            old = old[old[:, 3] != CAR]
        sel = (rec[:, 0] >= x0) & (rec[:, 0] < x1) & (rec[:, 1] >= y0) & (rec[:, 1] < y1)
        a = np.concatenate([old, rec[sel]])
        if len(a):
            p = "objects/%s.bin" % tile["id"]
            a.tofile(os.path.join(B.OUT, p))
            tile["objects"], tile["nobjects"] = p, int(len(a)); total += int(sel.sum())
    json.dump(man, open(man_p, "w"), separators=(",", ":"))
    print("parked cars: %d (%d way sides/rows, %d parking areas), occupancy %.2f" % (total, n_way, n_area, OCC))


if __name__ == "__main__":
    main()
