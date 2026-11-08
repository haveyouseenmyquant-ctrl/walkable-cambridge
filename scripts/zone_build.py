"""Market Square zone: real 3D facade geometry from the parametric parts library (session 30).

  .venv/bin/python -I scripts/zone_build.py [--ann-dir DIR ...]

Reads data/annotations/market_square/walls.json and the per-building annotations way_<id>.json (SCHEMA.md); walls
without an annotation get facade_parts.default_layout (flagged in the stats). Writes
  site/zone/market_square.glb    one node per building "f:<osm_id>" (+ scripts/zone_props.py build() nodes, if any)
  site/zone/zone.json            {glb, centre, radius, stats}
  data/derived/facade_geometry.json   per wall: id, annotated, element counts, areas (facade KPIs)
"""
import glob
import importlib
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build as B  # noqa: E402
import facade_parts as F  # noqa: E402

ROOT = B.ROOT
ZONE = "market_square"
ANN_DIR = os.path.join(ROOT, "data/annotations", ZONE)
GAMMA = float(os.environ.get("ZONE_GAMMA", "1.0"))   # colour hex -> vertex colour exponent (build.py uses raw values)


def load_annotations(dirs):
    walls = {}
    for d in dirs:
        for f in sorted(glob.glob(os.path.join(d, "way_*.json")) + glob.glob(os.path.join(d, "relation_*.json"))):
            try:
                a = json.load(open(f))
            except (OSError, ValueError) as e:
                print("skip annotation", f, e, file=sys.stderr)
                continue
            for w in a.get("walls", []):
                if "id" in w:
                    walls[w["id"]] = w
    return walls


def corner_extents(walls):
    """Skin x-extent per wall: extended by the skin depth at convex corners shared with the next/previous listed
    wall of the same building, shortened at concave ones (so neighbouring skins meet in a mitre)."""
    ext = {w["id"]: [0.0, w["length"]] for w in walls}
    ends = {}
    for w in walls:
        ends.setdefault((w["osm_id"], tuple(np.round(w["p0"], 1))), []).append(("start", w))
    for a in walls:
        for kind, b in ends.get((a["osm_id"], tuple(np.round(a["p1"], 1))), []):
            if b is a:
                continue
            da = np.subtract(a["p1"], a["p0"]) / max(a["length"], 1e-6)
            db = np.subtract(b["p1"], b["p0"]) / max(b["length"], 1e-6)
            cr = da[0] * db[1] - da[1] * db[0]   # outside on the right => footprint CCW => left turn = convex
            if abs(cr) < 0.2:
                continue
            d = F.SKIN if cr > 0 else -F.SKIN
            ext[a["id"]][1] += d
            ext[b["id"]][0] -= d
    return ext


def to_collision(w, T, N):
    p0 = np.asarray(w["p0"], float)
    d = (np.asarray(w["p1"], float) - p0) / w["length"]
    n = np.array([d[1], -d[0]])   # outward = right of p0 -> p1
    X = p0[0] + T[..., 0] * d[0] + T[..., 1] * n[0]
    Y = p0[1] + T[..., 0] * d[1] + T[..., 1] * n[1]
    Z = w["ground_z"] + T[..., 2]
    P = np.stack([X, Y, Z], -1)
    Nw = np.stack([N[:, 0] * d[0] + N[:, 1] * n[0], N[:, 0] * d[1] + N[:, 1] * n[1], N[:, 2]], -1)
    return P, Nw


def orient(P, Nw):
    """Make every triangle counter-clockwise seen from its intended normal; returns P and unit face normals."""
    g = np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0])
    flip = (g * Nw).sum(1) < 0
    P = P.copy()
    P[flip] = P[flip][:, ::-1]
    g[flip] = -g[flip]
    ln = np.linalg.norm(g, axis=1)
    keep = ln > 1e-9
    return P[keep], g[keep] / ln[keep, None], keep


def gl_mesh(name, P, nrm, col):
    k = len(P)
    pos = B.to_gl(P.reshape(-1, 3))
    nr = B.to_gl(np.repeat(nrm, 3, 0))
    cl = np.repeat(col, 3, 0)
    return (name, pos, nr, cl, np.arange(k * 3))


def main():
    t0 = time.time()
    args = sys.argv[1:]
    dirs = [ANN_DIR] + [args[i + 1] for i, a in enumerate(args) if a == "--ann-dir"]
    W = json.load(open(os.path.join(ANN_DIR, "walls.json")))["walls"]
    ann = load_annotations(dirs)
    ext = corner_extents(W)
    man = json.load(open(os.path.join(ROOT, "site/manifest.json")))
    landmark = {l["osm_id"]: l["id"] for l in man.get("landmarks", []) if l.get("detailed") and l.get("osm_id")}
    by_b, rows, skipped = {}, [], []
    tot_area = tot_detail = 0.0
    for w in W:
        L, H = w["length"], w["eave_z"] - w["ground_z"]
        a = ann.get(w["id"])
        if a is None and w["osm_id"] in landmark:
            # detailed landmark render model (build.py build_landmarks) already has 3D buttresses/piers/windows that a
            # generic skin would clash with; only annotated walls of landmarks get a skin
            skipped.append({"id": w["id"], "reason": "landmark:" + landmark[w["osm_id"]]})
            continue
        lay = a if a is not None else F.default_layout(w)
        x0s, x1s = ext[w["id"]]
        P = F.wall_facade(L, H, lay, x0s, x1s)
        T, N, C = P.arrays()
        if not len(T):
            continue
        Pw, Nw = to_collision(w, T, N)
        Pw, nrm, keep = orient(Pw, Nw)
        col = np.clip(C[keep], 0, 1) ** GAMMA
        by_b.setdefault(w["osm_id"], []).append((Pw, nrm, col))
        area = L * H
        tot_area += area
        tot_detail += min(P.detail_area, area)
        rows.append({"id": w["id"], "osm_id": w["osm_id"], "annotated": a is not None, "length": round(L, 2),
                     "height": round(H, 2), "area": round(area, 2), "detail_area": round(min(P.detail_area, area), 2),
                     "elements": dict(sorted(P.counts.items())), "tris": int(len(Pw))})
    meshes = []
    for oid, parts in by_b.items():
        meshes.append(gl_mesh("f:" + oid, *(np.concatenate(x) for x in zip(*parts))))
    nprops = 0
    if os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), "zone_props.py")):
        try:
            zp = importlib.import_module("zone_props")
            for pr in zp.build() if hasattr(zp, "build") else []:
                T = np.asarray(pr["tris"], float).reshape(-1, 3, 3)
                if not len(T):
                    continue
                g = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
                ln = np.linalg.norm(g, axis=1)
                ok = ln > 1e-9
                col = np.broadcast_to(np.asarray(pr["col"], float), (len(T), 3))[ok]
                meshes.append(gl_mesh(pr["name"], T[ok], g[ok] / ln[ok, None], col))
                nprops += int(ok.sum())
        except Exception as e:   # props are optional; never break the facade build
            print("zone_props failed:", repr(e), file=sys.stderr)
    out = os.path.join(ROOT, "site/zone")
    os.makedirs(out, exist_ok=True)
    B.write_glb(os.path.join(out, ZONE + ".glb"), meshes)
    ntris = sum(len(m[4]) // 3 for m in meshes)
    allp = np.array([w["p0"] for w in W] + [w["p1"] for w in W])
    centre = ((allp.min(0) + allp.max(0)) / 2).round(1).tolist()
    stats = {"walls_annotated": sum(r["annotated"] for r in rows), "walls_total": len(W), "walls_built": len(rows),
             "walls_unannotated": [r["id"] for r in rows if not r["annotated"]],
             "walls_skipped": skipped,
             "tris": ntris, "facade_tris": ntris - nprops, "prop_tris": nprops,
             "facade_area_m2": round(tot_area, 1), "modelled_detail_area_m2": round(tot_detail, 1)}
    json.dump({"glb": "zone/" + ZONE + ".glb", "centre": centre, "radius": 140, "stats": stats},
              open(os.path.join(out, "zone.json"), "w"), indent=1)
    os.makedirs(os.path.join(ROOT, "data/derived"), exist_ok=True)
    json.dump({"zone": ZONE, "built": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "walls": rows,
               "skipped": skipped,
               "stats": {k: v for k, v in stats.items() if k not in ("walls_unannotated", "walls_skipped")}},
              open(os.path.join(ROOT, "data/derived/facade_geometry.json"), "w"), indent=1)
    s = {k: v for k, v in stats.items() if k not in ("walls_unannotated", "walls_skipped")}
    s["walls_skipped"] = len(skipped)
    print(f"zone {ZONE}: {len(meshes)} nodes, {s}, {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
