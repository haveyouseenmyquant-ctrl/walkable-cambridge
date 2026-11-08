"""roof_match_pct: share of OSM buildings whose modelled roof surface is within 0.75 m RMSE of the LiDAR surface.

  .venv/bin/python -I scripts/roof_match.py [site_dir] [--verbose] [--worst N]

For each target building (data/derived/osm_targets.json) the render mesh (glTF node b:<osm_id> in its tile GLB, the
mesh the viewer draws) is rasterised top-down onto the 1 m LiDAR grid: per cell the highest mesh surface over the
cell centre (cells with no mesh surface get the DTM, i.e. the model shows ground there). Compared with the EA DSM on
the cells whose centres lie inside the OSM footprint shrunk by 0.5 m (so 1 m pixels that mix wall top and street are
left out; small footprints with no such cell use the unshrunk footprint). Comparing absolute heights is the same as
comparing (model - DTM) with (DSM - DTM). A building counts if RMSE <= 0.75 m; buildings without LiDAR cells are left
out of the denominator. Reading every GLB takes too long for measure.sh, so the result is cached per build hash in
data/benchmark/scores/<hash>_roof.json (publish.sh / service.sh run it), and measure.sh reads that cache.
"""
import json
import os
import struct
import subprocess
import sys

import numpy as np
import rasterio
from rasterio.features import geometry_mask
from rasterio.windows import from_bounds
from shapely.geometry import shape

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.argv = [a for a in sys.argv]
import kpi as K  # noqa: E402

ROOT = K.ROOT
TOL = 0.75
VERBOSE = "--verbose" in sys.argv
WORST = int(sys.argv[sys.argv.index("--worst") + 1]) if "--worst" in sys.argv else 0
args = [a for a in sys.argv[1:] if not a.startswith("--") and not a.isdigit()]
SITE = args[0] if args else os.path.join(ROOT, "site")
CTYPE = {5121: "u1", 5123: "<u2", 5125: "<u4", 5126: "<f4"}
NCOMP = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}


def read_glb(path):
    b = open(path, "rb").read()
    clen, _ = struct.unpack("<II", b[12:20])
    js = json.loads(b[20:20 + clen])
    o = 20 + clen
    blen, _ = struct.unpack("<II", b[o:o + 8])
    return js, b[o + 8:o + 8 + blen]


def accessor(js, bin_, i):
    a = js["accessors"][i]
    bv = js["bufferViews"][a["bufferView"]]
    dt = np.dtype(CTYPE[a["componentType"]])
    nc = NCOMP[a["type"]]
    off = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
    stride = bv.get("byteStride", 0)
    if stride and stride != nc * dt.itemsize:
        raw = np.frombuffer(bin_, np.uint8, a["count"] * stride, off).reshape(a["count"], stride)
        return raw[:, :nc * dt.itemsize].copy().view(dt).reshape(a["count"], nc)
    return np.frombuffer(bin_, dt, a["count"] * nc, off).reshape(a["count"], nc)


def mesh_tris(js, bin_, node, e0, n0):
    """Triangles of a node's mesh in BNG (E, N, height)."""
    t = np.array(node.get("translation") or [0, 0, 0], float)
    out = []
    for prim in js["meshes"][node["mesh"]].get("primitives", []):
        if prim.get("mode", 4) != 4:
            continue
        P = accessor(js, bin_, prim["attributes"]["POSITION"]).astype(np.float64) + t
        idx = accessor(js, bin_, prim["indices"]).ravel().astype(np.int64) if "indices" in prim else np.arange(len(P))
        V = np.stack([P[:, 0] + e0, -P[:, 2] + n0, P[:, 1]], 1)
        out.append(V[idx.reshape(-1, 3)])
    return np.concatenate(out) if out else np.zeros((0, 3, 3))


def main():
    man = json.load(open(os.path.join(SITE, "manifest.json")))
    e0, n0 = man["origin"]["e0"], man["origin"]["n0"]
    tg = json.load(open(K.TARGETS))
    targets = {b["osm_id"]: b for b in tg["buildings"] if b.get("footprint")}
    tiles = {t["id"]: t for t in man["tiles"]}
    by_tile = {}
    for b in man.get("buildings", []):
        if b.get("osm_id") in targets:
            by_tile.setdefault(b.get("tile"), []).append(b)
    K.CELL = 1.0
    res, n_nolidar, n_missing = {}, 0, 0
    dtm = rasterio.open(os.path.join(K.LIDAR_DIR, "dtm_1m.tif"))
    dsm = rasterio.open(os.path.join(K.LIDAR_DIR, "dsm_1m.tif"))
    assert dtm.transform == dsm.transform and dtm.transform.a == 1.0
    seen = set()
    for tid, blist in by_tile.items():
        t = tiles.get(tid)
        if not t or not t.get("glb") or not os.path.exists(os.path.join(SITE, t["glb"])):
            continue
        js, bin_ = read_glb(os.path.join(SITE, t["glb"]))
        byname = {n.get("name"): n for n in js["nodes"] if n.get("name")}
        for b in blist:
            oid = b["osm_id"]
            n = byname.get(b.get("node") or "b:" + oid)
            if not n or "mesh" not in n:
                continue
            seen.add(oid)
            fp = targets[oid]["footprint"]
            g = shape(fp)
            x0, y0, x1, y1 = g.bounds
            win = from_bounds(x0 - 1, y0 - 1, x1 + 1, y1 + 1, dtm.transform).round_offsets().round_lengths()
            if win.width < 1 or win.height < 1:
                n_nolidar += 1
                continue
            A = dtm.read(1, window=win, masked=True)
            S = dsm.read(1, window=win, masked=True)
            wt = dtm.window_transform(win)
            gs = g.buffer(-0.5)
            m = geometry_mask([gs], A.shape, wt, invert=True) if not gs.is_empty else np.zeros(A.shape, bool)
            if m.sum() == 0:
                m = geometry_mask([fp], A.shape, wt, invert=True)
            m &= ~np.ma.getmaskarray(A) & ~np.ma.getmaskarray(S)
            if m.sum() == 0:
                n_nolidar += 1
                continue
            H, W = A.shape
            gx0, gy_top = wt.c, wt.f
            gy0 = gy_top - H   # south edge; raster rows go south, grid rows (cj) go north
            P = mesh_tris(js, bin_, n, e0, n0)
            top = np.full(H * W, -np.inf)
            if len(P):
                li, z = K.raster_cells(P, gx0, gy0, W, H)
                np.maximum.at(top, li, z)
            top = top.reshape(H, W)[::-1]          # to raster row order
            top = np.where(np.isfinite(top), top, A.data)
            d = (top - S.data)[m]
            res[oid] = {"rmse": float(np.sqrt(np.mean(d * d))), "n": int(m.sum()), "bias": float(np.mean(d))}
    n_missing = len(targets) - len(seen)
    ok = sum(1 for r in res.values() if r["rmse"] <= TOL)
    out = {"roof_match_pct": round(100.0 * ok / max(1, len(res)), 2), "n": len(res), "ok": ok,
           "no_lidar": n_nolidar, "not_in_build": n_missing,
           "median_rmse": round(float(np.median([r["rmse"] for r in res.values()])), 3)}
    if VERBOSE or WORST:
        out["buildings"] = res
    try:
        h = subprocess.run([sys.executable, "-I", os.path.join(ROOT, "scripts/build_hash.py"), SITE],
                           capture_output=True, text=True, check=True).stdout.strip()
        d = os.path.join(ROOT, "data/benchmark/scores")
        json.dump({**out, "buildings": res, "build": h}, open(os.path.join(d, f"{h}_roof.json"), "w"))
    except Exception as e:
        print("cache write failed:", e, file=sys.stderr)
    if WORST:
        for oid, r in sorted(res.items(), key=lambda kv: -kv[1]["rmse"])[:WORST]:
            print(oid, r, file=sys.stderr)
    print(json.dumps({k: v for k, v in out.items() if k != "buildings"}))


if __name__ == "__main__":
    main()
