"""City-wide baseline facades (session 35): real 3D facade geometry from the parametric parts library on every
street-facing wall of every OSM building in the world, not only the Market Square zone.

  .venv/bin/python -I scripts/city_facades.py

Walls: OSM building edges >= 2 m that face a walkable way (as scripts/zone_walls.py: an OSM walk sample within 3 m of
a point 2-25 m out along the outward normal, no other footprint in between). Skipped: walls the zone build already
covers (data/annotations/market_square/walls.json), bespoke buildings (scripts/zone_bespoke_*.py BUILDS), detailed
landmark models (manifest landmarks), market stall canopies (building=roof) and duplicate overlapping footprints.
Per wall the layout is the wall's annotation if one exists (data/annotations/ring1/way_<id>.json, same schema and the
same facade_parts.wall_facade code path as the zone; session 36), else scripts/facade_styles.py layout(wall) (style
from OSM tags), else facade_parts.default_layout. colour_hint: the median colour of the wall's rectified photo pieces in the old photo
facade atlases (site/facades, non-held-out Mapillary): photos give only the material colour, all detail is geometry.
Writes
  site/cityfac/<tile id>.glb    one node per building "f:<osm_id>", compact quantized GLB like the zone
  site/cityfac/index.json       {tiles: {tile id: {glb, tris}}, stats}
  data/derived/facade_geometry_city.json   per wall: id, dist from the square, element counts, areas (ring KPIs)
"""
import io
import json
import math
import os
import sys
import time

import numpy as np
import rasterio
from PIL import Image
from pyproj import Transformer
from scipy.spatial import cKDTree
from shapely import STRtree, linestrings
from shapely.geometry import Point

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build as B  # noqa: E402
import facade_parts as F  # noqa: E402
import zone_build as Z  # noqa: E402

try:
    import facade_styles as S  # noqa: E402
except Exception as e:   # optional
    print("facade_styles unavailable:", repr(e), file=sys.stderr)
    S = None

ROOT = B.ROOT
OUT = os.path.join(ROOT, "site/cityfac")
SQUARE = (0.1190, 52.2053)
ANN_DIRS = [os.path.join(ROOT, "data/annotations/ring1")]
RING1_R = 400.0   # ring 1: city walls (outside the zone) within this many metres of the square
TYPES = ("window", "door", "shopfront", "dormer")


def geometry_match(rows, ann):
    """zone_kpi.py's facade_geometry_match_pct over these rows: per wall, mean over TYPES of min/max(annotated, emitted)
    counts (1 if both 0); unannotated walls score 0; length-weighted, x 100."""
    num = den = 0.0
    for r in rows:
        a = ann.get(r["id"])
        sc = 0.0
        if a is not None:
            ac = {t: sum(1 for e in a.get("elements", []) if e.get("type") == t) for t in TYPES}
            mc = r["elements"]
            sc = float(np.mean([1.0 if ac[t] == mc.get(t, 0) == 0 else min(ac[t], mc.get(t, 0)) / max(ac[t], mc.get(t, 0))
                                for t in TYPES]))
        num += sc * r["length"]; den += r["length"]
    return round(100 * num / max(den, 1e-9), 2)


def buildings(nodes, ways, rels):
    out = []
    for w in ways.values():
        t = w.get("tags", {})
        if "building" in t:
            g = B.way_area(w, nodes)
            if g is not None and not g.is_empty:
                out.append(("way/%d" % w["id"], t, g))
    for r in rels:
        t = r.get("tags", {})
        if "building" in t:
            try:
                g = B.rel_area(r, ways, nodes)
            except Exception:
                g = None
            if g is not None and not g.is_empty:
                out.append(("relation/%d" % r["id"], t, g))
    res = []
    for oid, t, g in out:
        for p in B.polys_of(g):
            if abs(p.centroid.x - B.E0) < B.EXT and abs(p.centroid.y - B.N0) < B.EXT:
                res.append((oid, t, p))
    return res


def photo_colours():
    """Median colour per photo-facade quad: (x, y) quad centres in the collision frame, (n, 3) colours 0..1."""
    xy, col = [], []
    d = os.path.join(ROOT, "site/facades")
    for f in sorted(os.listdir(d)):
        if not f.endswith(".bin") or not os.path.exists(os.path.join(d, f[:-4] + ".webp")):
            continue
        a = np.fromfile(os.path.join(d, f), "<f4").reshape(-1, 4, 5)
        im = np.asarray(Image.open(os.path.join(d, f[:-4] + ".webp")).convert("RGBA"))
        h, w = im.shape[:2]
        for q in a:
            u0, u1 = q[:, 3].min(), q[:, 3].max()
            v0, v1 = q[:, 4].min(), q[:, 4].max()
            c0, c1 = int(u0 * w), max(int(u1 * w), int(u0 * w) + 1)
            r0, r1 = int((1 - v1) * h), max(int((1 - v0) * h), int((1 - v1) * h) + 1)
            px = im[r0:r1, c0:c1].reshape(-1, 4)
            px = px[px[:, 3] > 128, :3]
            if len(px) < 20:
                continue
            # wall colour, not glass: the brighter half of the pixels
            lum = px.mean(1)
            px = px[lum >= np.median(lum)]
            xy.append(q[:, :2].mean(0)); col.append(np.median(px, 0) / 255)
    return np.array(xy), np.array(col)


def hexc(c):
    return "#%02x%02x%02x" % tuple(int(round(min(max(v, 0), 1) * 255)) for v in c)


def main():
    t0 = time.time()
    tf = Transformer.from_crs(4326, 27700, always_xy=True)
    sx, sy = tf.transform(*SQUARE)
    nodes, ways, rels, _ = B.load_osm()
    blds = buildings(nodes, ways, rels)
    geoms = [g for _, _, g in blds]
    tree = STRtree(geoms)
    tg = json.load(open(os.path.join(ROOT, "data/derived/osm_targets.json")))
    wt = cKDTree(np.array([[s[0], s[1]] for s in tg["walk"]["samples"]]))
    dtm = rasterio.open(os.path.join(ROOT, "data/lidar/dtm_1m.tif")); dsm = rasterio.open(os.path.join(ROOT, "data/lidar/dsm_1m.tif"))
    DT, DS = dtm.read(1), dsm.read(1)

    def samp(R, A, P):
        r, c = rasterio.transform.rowcol(R.transform, P[:, 0], P[:, 1])
        r = np.clip(np.asarray(r), 0, A.shape[0] - 1); c = np.clip(np.asarray(c), 0, A.shape[1] - 1)
        return A[r, c].astype(float)

    zone_ids = {w["id"] for w in json.load(open(os.path.join(ROOT, "data/annotations/market_square/walls.json")))["walls"]}
    bespoke = set(Z.load_bespoke())
    man = json.load(open(os.path.join(ROOT, "site/manifest.json")))
    landmark = {l["osm_id"] for l in man.get("landmarks", []) if l.get("detailed") and l.get("osm_id")}
    skip_b = bespoke | landmark | Z.PROP_BUILDINGS
    ann = Z.load_annotations([d for d in ANN_DIRS if os.path.isdir(d)])

    # ---- candidate edges
    E = []   # (bi, k, a, b)
    for bi, (oid, t, g) in enumerate(blds):
        if oid in skip_b or t.get("building") == "roof":
            continue
        ring = list(g.exterior.coords)
        if not g.exterior.is_ccw:
            ring = ring[::-1]
        for k in range(len(ring) - 1):
            a, b = np.array(ring[k]), np.array(ring[k + 1])
            if np.linalg.norm(b - a) >= 2 and "%s:%d" % (oid, k) not in zone_ids:
                E.append((bi, k, a, b))
    A = np.array([e[2] for e in E]); Bp = np.array([e[3] for e in E])
    L = np.linalg.norm(Bp - A, axis=1)
    D = (Bp - A) / L[:, None]
    Nrm = np.stack([D[:, 1], -D[:, 0]], 1)
    M = (A + Bp) / 2
    hit = np.full(len(E), -1.0)
    for s in (25, 20, 14, 9, 5, 2):   # nearest probe distance with a walk sample within 3 m
        d, _ = wt.query(M + Nrm * s)
        hit[d < 3] = s
    cand = np.nonzero(hit > 0)[0]
    segs = linestrings(np.stack([M[cand] + Nrm[cand] * 0.3, M[cand] + Nrm[cand] * hit[cand, None]], 1))
    si, gi = tree.query(segs, predicate="intersects")
    own = np.array([E[i][0] for i in cand])
    blocked = np.zeros(len(cand), bool)
    blocked[si[gi != own[si]]] = True
    keep = cand[~blocked]
    print(f"{len(blds)} footprints, {len(E)} edges, {len(cand)} near walks, {len(keep)} street-facing", file=sys.stderr)

    gz = samp(dtm, DT, M[keep] + Nrm[keep] * 1.5)
    ez = []
    for i in keep:
        ins = np.array([A[i] + D[i] * L[i] * f - Nrm[i] * s for f in (0.2, 0.4, 0.6, 0.8) for s in (1, 1.75, 2.5)])
        ez.append(float(np.median(samp(dsm, DS, ins))))
    W = []
    for j, i in enumerate(keep):
        bi, k, a, b = E[i]
        oid, t, g = blds[bi]
        if ez[j] - gz[j] < 2.2:
            continue
        W.append(dict(id="%s:%d" % (oid, k), osm_id=oid, tags=t, length=round(float(L[i]), 2),
                      p0=[round(a[0] - B.E0, 2), round(a[1] - B.N0, 2)], p1=[round(b[0] - B.E0, 2), round(b[1] - B.N0, 2)],
                      ground_z=round(float(gz[j]), 2), eave_z=round(ez[j], 2), height=round(ez[j] - float(gz[j]), 2),
                      dist_centre=round(math.hypot(M[i][0] - sx, M[i][1] - sy), 1)))

    # ---- annotated walls clipped by a low eave (session 37): where the OSM footprint sits in front of the LiDAR facade the
    # 1-2.5 m inset DSM samples hit the street, so the eave comes out too low and wall_facade clips the annotation. Walk the
    # DSM inward (median along the wall per inset) and take the first inset height that clears the annotation's top.
    for w in W:
        a = ann.get(w["id"])
        if a is None:
            continue
        top = max([e.get("z", 0) + e.get("h", 0) for e in a.get("elements", []) if e.get("type") == "window"]
                  + [e.get("z1", 0) for e in a.get("elements", [])] + [a.get("cornice_z") or 0, 0])
        if top <= w["height"]:
            continue
        p0 = np.add(w["p0"], [B.E0, B.N0]); d = np.subtract(w["p1"], w["p0"]) / w["length"]; nrm = np.array([d[1], -d[0]])
        prof = [float(np.median(samp(dsm, DS, np.array([p0 + d * w["length"] * f - nrm * s for f in (0.2, 0.35, 0.5, 0.65, 0.8)]))))
                - w["ground_z"] for s in (1, 1.5, 2, 2.5, 3, 4, 5, 6)]
        fit = [h for h in prof if h >= top - 0.2]
        hn = fit[0] if fit else max(prof)
        if hn > w["height"] + 0.3:
            print("eave fix", w["id"], w["height"], "->", round(hn, 2), "annotation top", top, file=sys.stderr)
            w["height"] = round(hn, 2); w["eave_z"] = round(w["ground_z"] + hn, 2); w["eave_fixed"] = True

    # ---- duplicates (overlapping footprints): parallel walls of different buildings with midpoints < 1.2 m apart
    mids = np.array([np.add(w["p0"], w["p1"]) / 2 for w in W])
    dirs = np.array([np.subtract(w["p1"], w["p0"]) / w["length"] for w in W])
    drop = set()
    for i, j in sorted(cKDTree(mids).query_pairs(1.2)):
        a, b = W[i], W[j]
        if a["osm_id"] == b["osm_id"] or float(dirs[i] @ dirs[j]) < 0.95 or i in drop or j in drop:
            continue
        # keep the annotated wall, then the one with an address (as zone_build.duplicate_walls)
        ra = (a["id"] in ann, "addr:housenumber" in a["tags"]); rb = (b["id"] in ann, "addr:housenumber" in b["tags"])
        drop.add(i if rb > ra else j)
    W = [w for i, w in enumerate(W) if i not in drop]

    # ---- colour hints from the photo facade atlases
    pxy, pcol = photo_colours()
    if len(pxy):
        pt = cKDTree(pxy)
        for w in W:
            m = np.add(w["p0"], w["p1"]) / 2
            idx = pt.query_ball_point(m, max(2.0, w["length"] / 2))
            if idx:
                w["colour_hint"] = hexc(np.median(pcol[idx], 0))

    # ring-1 wall list for annotators (data/annotations/ring1/walls.json, the frame annotations refer to)
    os.makedirs(ANN_DIRS[0], exist_ok=True)
    json.dump({"centre": list(SQUARE), "radius": RING1_R,
               "walls": [{k: v for k, v in w.items() if k != "colour_hint"} for w in W if w["dist_centre"] <= RING1_R]},
              open(os.path.join(ANN_DIRS[0], "walls.json"), "w"), indent=1)
    ext = Z.corner_extents(W)
    by_tile, rows = {}, []
    nstyle = 0
    for w in W:
        Lw, H = w["length"], w["eave_z"] - w["ground_z"]
        lay = ann.get(w["id"])
        if lay is None and S is not None:
            try:
                lay = S.layout(w); nstyle += 1
            except Exception as e:
                print("style failed", w["id"], repr(e), file=sys.stderr)
        if lay is None:
            lay = F.default_layout(w)
            if w.get("colour_hint"):
                lay["wall_colour"] = w["colour_hint"]
            if S is not None:
                S.apply_override(lay, w["osm_id"])   # photo-read material/colour (data/annotations/colours)
        x0s, x1s = ext[w["id"]]
        P = F.wall_facade(Lw, H, lay, x0s, x1s)
        T, N, C = P.arrays()
        Mt = P.mats()
        if not len(T):
            continue
        Pw, Nw = Z.to_collision(w, T, N)
        Pw, nrm, kp = Z.orient(Pw, Nw)
        m = np.add(w["p0"], w["p1"]) / 2
        tx, ty = int((m[0] + B.EXT) // B.TILE), int((m[1] + B.EXT) // B.TILE)
        tid = f"t_{tx}_{ty}"
        by_tile.setdefault(tid, {}).setdefault(w["osm_id"], []).append((Pw, nrm, np.clip(C[kp], 0, 1), Mt[kp]))
        area = Lw * H
        rows.append({"id": w["id"], "osm_id": w["osm_id"], "dist_centre": w["dist_centre"], "length": Lw,
                     "height": round(H, 2), "area": round(area, 2), "detail_area": round(min(P.detail_area, area), 2),
                     "elements": dict(sorted(P.counts.items())), "tris": int(len(Pw)), "tile": tid,
                     "colour_hint": w.get("colour_hint"), "annotated": w["id"] in ann,
                     "street": w["tags"].get("addr:street")})
    os.makedirs(OUT, exist_ok=True)
    for f in os.listdir(OUT):
        if f.endswith(".glb"):
            os.remove(os.path.join(OUT, f))
    index = {}
    for tid, bb in sorted(by_tile.items()):
        meshes = [Z.gl_mesh("f:" + oid, *(np.concatenate(x) for x in zip(*parts))) for oid, parts in bb.items()]
        Z.write_compact_glb(os.path.join(OUT, tid + ".glb"), meshes)
        index[tid] = {"glb": "cityfac/%s.glb" % tid, "tris": int(sum(len(m[4]) // 3 for m in meshes))}
    ring1 = [r for r in rows if r["dist_centre"] <= RING1_R]
    kp = [r for r in ring1 if r["street"] == "King's Parade"]
    built = {r["id"] for r in rows}
    stats = {"walls": len(rows), "buildings": len({r["osm_id"] for r in rows}), "styled": nstyle,
             "annotations": len(ann), "walls_annotated": sum(r["annotated"] for r in rows),
             "buildings_annotated": len({r["osm_id"] for r in rows if r["annotated"]}),
             "annotations_unmatched": sorted(k for k in ann if k not in built),
             "ring1_walls": len(ring1), "ring1_walls_annotated": sum(r["annotated"] for r in ring1),
             "ring1_facade_geometry_match_pct": geometry_match(ring1, ann),
             "kings_parade_walls": len(kp), "kings_parade_walls_annotated": sum(r["annotated"] for r in kp),
             "kings_parade_facade_geometry_match_pct": geometry_match(kp, ann),
             "colour_hints": sum(1 for r in rows if r["colour_hint"]),
             "colour_override_buildings": len({r["osm_id"] for r in rows if S is not None and not r["annotated"]
                                               and S.colour_override(r["osm_id"])}), "duplicates_dropped": len(drop),
             "tris": sum(v["tris"] for v in index.values()), "facade_area_m2": round(sum(r["area"] for r in rows)),
             "bytes": sum(os.path.getsize(os.path.join(ROOT, "site", v["glb"])) for v in index.values())}
    json.dump({"tiles": index, "stats": stats}, open(os.path.join(OUT, "index.json"), "w"), indent=1)
    json.dump({"built": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "walls": rows, "stats": stats},
              open(os.path.join(ROOT, "data/derived/facade_geometry_city.json"), "w"))
    print(json.dumps(stats), f"{time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
