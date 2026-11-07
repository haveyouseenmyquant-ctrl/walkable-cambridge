#!/usr/bin/env python3
"""Trees from OSM (natural=tree nodes, tree_row ways) and the EA LiDAR canopy, written per tile.

  .venv/bin/python -I scripts/trees.py [--out site]     (run after build.py; edits manifest.json in place)

Canopy height model = first-return DSM - DTM (1 m, EA NLP 2023). Vegetation = CHM > 3 m, outside OSM buildings
(+1 m) and water, where the laser penetrates (first return - last return > 0.5 m, 5x5 mean): that drops roofs,
walls and vans. Tree tops = local maxima of the smoothed CHM (window grows with height); each top's crown is its
watershed-like share of the vegetation mask (nearest top within 10 m), crown radius = sqrt(area / pi).
OSM trees win: LiDAR tops within an OSM tree's crown are dropped; OSM trees take height / crown from tags, else
from the CHM around them.
Output: <out>/trees/<tile>.bin, float32 records [x, y, z_ground, height, crown_r, seed] (collision frame, FORMAT.md);
manifest tiles get "trees": "trees/<tile>.bin" and "ntrees".
"""
import json, os, sys
import numpy as np
import rasterio
from rasterio.features import rasterize
from scipy.ndimage import gaussian_filter, maximum_filter, uniform_filter, distance_transform_edt, binary_dilation
from shapely.geometry import mapping

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build as B   # OSM helpers (load_osm, way_area, coords, E0, N0, EXT, TILE)

ROOT = B.ROOT
OUT = B.OUT
L = os.path.join(ROOT, "data/lidar")


def main():
    first = rasterio.open(os.path.join(L, "nlp2023_first_return_dsm_1m.tif"))
    tf = first.transform
    F = first.read(1).astype(np.float32)
    LAST = rasterio.open(os.path.join(L, "nlp2023_dsm_1m.tif")).read(1).astype(np.float32)
    DTM = rasterio.open(os.path.join(L, "dtm_1m.tif")).read(1).astype(np.float32)
    ok = (F > -100) & (DTM > -100) & (LAST > -100)
    chm = np.where(ok, F - DTM, 0).clip(0, 60)
    pen = uniform_filter(np.where(ok, F - LAST, 0).clip(0, 10), 5)

    nodes, ways, rels, pnodes = B.load_osm()
    blds, water, osm_trees = [], [], []
    for w in ways.values():
        t = w.get("tags", {})
        if "building" in t and t["building"] != "no":
            g = B.way_area(w, nodes)
            if g is not None: blds.append(g)
        if t.get("natural") == "water" or t.get("waterway") == "riverbank":
            g = B.way_area(w, nodes)
            if g is not None: water.append(g)
        if t.get("natural") == "tree_row":   # one tree every 8 m along the row
            c = B.coords(w, nodes)
            if c and len(c) >= 2:
                from shapely.geometry import LineString
                ln = LineString(c)
                for d in np.arange(0, ln.length + 0.1, 8.0):
                    p = ln.interpolate(d); osm_trees.append((p.x, p.y, {}))
    for e in pnodes:
        if e["tags"].get("natural") == "tree":
            E, N = nodes[e["id"]]
            osm_trees.append((E, N, e["tags"]))
    shp = F.shape
    mask_b = rasterize([(mapping(g.buffer(1.0)), 1) for g in blds], out_shape=shp, transform=tf, dtype=np.uint8) > 0
    mask_w = rasterize([(mapping(g), 1) for g in water], out_shape=shp, transform=tf, dtype=np.uint8) > 0 if water else np.zeros(shp, bool)
    mask_b3 = binary_dilation(mask_b, iterations=2)   # eaves / mixed edge pixels give false canopy next to walls
    veg = (chm > 3.0) & ~mask_b3 & ~mask_w & (pen > 0.8) & ok
    print("vegetation px", int(veg.sum()), "osm trees", len(osm_trees), flush=True)

    # tree tops: local maxima of the smoothed CHM; window 5 px for < 10 m, 7 px for taller trees
    s = gaussian_filter(np.where(veg, chm, 0), 1.0)
    top5 = (s == maximum_filter(s, 5)) & veg & (s < 15)
    top7 = (s == maximum_filter(s, 7)) & veg & (s >= 15)
    ty, tx = np.nonzero(top5 | top7)
    # crowns: each vegetation px goes to the nearest top (within 10 m)
    lab = np.zeros(shp, np.int32)
    lab[ty, tx] = np.arange(1, len(ty) + 1)
    dist, (iy, ix) = distance_transform_edt(lab == 0, return_indices=True)
    own = np.where(veg & (dist <= 10), lab[iy, ix], 0)
    area = np.bincount(own.ravel(), minlength=len(ty) + 1)[1:]
    E = tf.c + (tx + 0.5) * tf.a; N = tf.f + (ty + 0.5) * tf.e
    H = chm[ty, tx]; R = np.sqrt(np.maximum(area, 1) / np.pi).clip(1.2, 10)
    keep = (area >= 10) & (pen[ty, tx] > 3.0)   # true canopy: the laser goes deep into it
    lid = np.stack([E, N, H, R], 1)[keep]
    print("lidar tops", len(lid), flush=True)

    def chm_at(e, n, r):
        c = int((e - tf.c) / tf.a); rr = int((n - tf.f) / tf.e); k = max(1, int(r))
        win = chm[max(rr - k, 0):rr + k + 1, max(c - k, 0):c + k + 1]
        vw = veg[max(rr - k, 0):rr + k + 1, max(c - k, 0):c + k + 1]
        return float(win[vw].max()) if vw.any() else None

    def num(v):
        try: return float(str(v).split()[0].replace("m", ""))
        except Exception: return None

    trees = []
    from scipy.spatial import cKDTree
    kd = cKDTree(lid[:, :2]) if len(lid) else None
    drop = np.zeros(len(lid), bool)
    for e, n, t in osm_trees:
        h = num(t.get("height")) or chm_at(e, n, 3) or 7.0
        h = float(np.clip(h, 3, 35))
        r = (num(t.get("diameter_crown")) or 0) / 2
        near = kd.query_ball_point([e, n], max(r, 3.0)) if kd is not None else []
        if not r:
            r = float(np.median(lid[near, 3])) if near else max(1.5, h * 0.3)
        drop[near] = True
        trees.append((e, n, h, float(np.clip(r, 1.2, 10))))
    trees += [tuple(x) for x in lid[~drop]]
    trees = np.array(trees, np.float32)
    # ground height and per-tile files
    rows = ((trees[:, 1] - tf.f) / tf.e).astype(int).clip(0, shp[0] - 1)
    cols = ((trees[:, 0] - tf.c) / tf.a).astype(int).clip(0, shp[1] - 1)
    zg = DTM[rows, cols]
    x = trees[:, 0] - B.E0; y = trees[:, 1] - B.N0
    seed = np.random.default_rng(7).random(len(trees)).astype(np.float32)
    rec = np.stack([x, y, zg, trees[:, 2], trees[:, 3], seed], 1).astype(np.float32)
    man_p = os.path.join(OUT, "manifest.json")
    man = json.load(open(man_p))
    os.makedirs(os.path.join(OUT, "trees"), exist_ok=True)
    total = 0
    for tile in man["tiles"]:
        x0, y0, x1, y1 = tile["bounds"]
        sel = (x >= x0) & (x < x1) & (y >= y0) & (y < y1) & (zg > -100)
        tile.pop("trees", None); tile.pop("ntrees", None)
        if sel.any():
            p = "trees/%s.bin" % tile["id"]
            rec[sel].tofile(os.path.join(OUT, p))
            tile["trees"], tile["ntrees"] = p, int(sel.sum()); total += int(sel.sum())
    json.dump(man, open(man_p, "w"), separators=(",", ":"))
    print("trees written", total, "(osm", len(osm_trees), ")", flush=True)


if __name__ == "__main__":
    main()
