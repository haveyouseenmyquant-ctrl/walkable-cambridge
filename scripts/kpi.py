"""KPI harness for Walkable Cambridge. Prints one JSON object of KPI readings.

Reads the build exactly as the browser does (manifest.json, collision/*.col, tiles/*.glb) from
a local directory or a URL, and compares it with the fixed OSM targets in data/derived/osm_targets.json.
Rules are documented in FORMAT.md.

Usage: .venv/bin/python -I scripts/kpi.py [site_dir_or_url] [--verbose]
"""
import json
import math
import os
import struct
import sys
import time
import urllib.request

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGETS = os.path.join(ROOT, "data/derived/osm_targets.json")
LANDMARKS = os.path.join(ROOT, "landmarks/landmarks.json")
LIDAR_DIR = os.path.join(ROOT, "data/lidar")
CACHE = os.path.join(ROOT, "data/derived/lidar_building_stats.json")

CELL = 0.5          # walk grid resolution (m)
MARGIN = 100.0      # grid margin around study area so detours just outside still connect (m)
STEP_H = 0.45       # max height difference between neighbouring cells (m)
BODY_LO, BODY_HI = 0.35, 1.8
MAX_TILT_COS = math.cos(math.radians(50))
SNAP = 1.0          # tolerance from OSM sample point to reachable cell (m)
HEIGHT_TOL = 2.0

VERBOSE = "--verbose" in sys.argv
args = [a for a in sys.argv[1:] if not a.startswith("--")]
SRC = args[0] if args else os.path.join(ROOT, "site")
REMOTE = SRC.startswith("http://") or SRC.startswith("https://")


def log(*a):
    if VERBOSE:
        print(*a, file=sys.stderr)


_CACHE = {}
FAILED = []  # remote fetches that failed after retries (e.g. Pages mid-deploy): the result is then not cached


def fetch(rel, rng=None):
    if (rel, rng) in _CACHE:
        return _CACHE.pop((rel, rng))
    if REMOTE:
        req = urllib.request.Request(SRC.rstrip("/") + "/" + rel, headers={"User-Agent": "walkable-cambridge-kpi"})
        if rng:
            req.add_header("Range", "bytes=%d-%d" % rng)
        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=20) as r:
                    data = r.read()
                    if rng and r.status == 200:  # server ignored the range
                        data = data[rng[0]:rng[1] + 1]
                    return data
            except Exception as e:
                err = e
                time.sleep(1 + 2 * attempt)
        log("fetch failed", rel, err)
        FAILED.append(rel)
        return None
    p = os.path.join(SRC, rel)
    if not os.path.isfile(p):
        return None
    with open(p, "rb") as f:
        if rng:
            f.seek(rng[0])
            return f.read(rng[1] - rng[0] + 1)
        return f.read()


def glb_json(rel):
    head = fetch(rel, (0, 19))
    if not head or len(head) < 20 or head[:4] != b"glTF":
        return None
    clen, ctype = struct.unpack("<II", head[12:20])
    if ctype != 0x4E4F534A:
        return None
    body = fetch(rel, (20, 20 + clen - 1))
    try:
        return json.loads(body.decode("utf-8"))
    except Exception:
        return None


def read_col(buf):
    if not buf or buf[:4] != b"WCOL":
        return None
    _ver, nv, nt = struct.unpack("<III", buf[4:16])
    o = 16
    v = np.frombuffer(buf, "<f4", nv * 3, o).reshape(-1, 3).astype(np.float64); o += nv * 12
    t = np.frombuffer(buf, "<u4", nt * 3, o).reshape(-1, 3); o += nt * 12
    kind = np.frombuffer(buf, "u1", nt, o); o += nt
    surf = np.frombuffer(buf, "u1", nt, o)
    return v, t, kind, surf


def raster_cells(P, gx0, gy0, W, H):
    """Rasterise triangles P (n,3,3) by their XY projection onto grid cell centres.
    Returns (linear cell index, interpolated z) for every covered cell centre."""
    x0 = np.floor((P[:, :, 0].min(1) - gx0) / CELL - 0.5).astype(np.int64)
    y0 = np.floor((P[:, :, 1].min(1) - gy0) / CELL - 0.5).astype(np.int64)
    x1 = np.ceil((P[:, :, 0].max(1) - gx0) / CELL - 0.5).astype(np.int64)
    y1 = np.ceil((P[:, :, 1].max(1) - gy0) / CELL - 0.5).astype(np.int64)
    bw = 2 ** np.ceil(np.log2(np.maximum(1, x1 - x0 + 1))).astype(np.int64)
    bh = 2 ** np.ceil(np.log2(np.maximum(1, y1 - y0 + 1))).astype(np.int64)
    out_l, out_z = [], []
    for w, h in set(zip(bw.tolist(), bh.tolist())):
        idx = np.nonzero((bw == w) & (bh == h))[0]
        oi, oj = np.meshgrid(np.arange(w), np.arange(h))
        oi, oj = oi.ravel(), oj.ravel()
        chunk = max(1, 3_000_000 // len(oi))
        for s in range(0, len(idx), chunk):
            sel = idx[s:s + chunk]
            ci = x0[sel, None] + oi[None, :]
            cj = y0[sel, None] + oj[None, :]
            px = gx0 + (ci + 0.5) * CELL
            py = gy0 + (cj + 0.5) * CELL
            A, B, C = P[sel, 0, None, :], P[sel, 1, None, :], P[sel, 2, None, :]
            d = (B[..., 0] - A[..., 0]) * (C[..., 1] - A[..., 1]) - (C[..., 0] - A[..., 0]) * (B[..., 1] - A[..., 1])
            with np.errstate(all="ignore"):
                l1 = ((px - A[..., 0]) * (C[..., 1] - A[..., 1]) - (C[..., 0] - A[..., 0]) * (py - A[..., 1])) / d
                l2 = ((B[..., 0] - A[..., 0]) * (py - A[..., 1]) - (px - A[..., 0]) * (B[..., 1] - A[..., 1])) / d
                eps = 1e-9
                m = (np.abs(d) > 1e-12) & (l1 >= -eps) & (l2 >= -eps) & (l1 + l2 <= 1 + eps)
                m &= (ci >= 0) & (ci < W) & (cj >= 0) & (cj < H)
                z = A[..., 2] + l1 * (B[..., 2] - A[..., 2]) + l2 * (C[..., 2] - A[..., 2])
            out_l.append((cj * W + ci)[m])
            out_z.append(z[m])
    if not out_l:
        return np.zeros(0, np.int64), np.zeros(0)
    return np.concatenate(out_l), np.concatenate(out_z)


def clip_slab(P, zlo, zhi):
    """Clip triangles P (n,3,3) to zlo[i] <= z <= zhi[i]; returns triangles (m,3,3)."""
    out = []
    for tri, lo, hi in zip(P, zlo, zhi):
        if tri[:, 2].max() < lo or tri[:, 2].min() > hi:
            continue
        poly = list(tri)
        for plane, keep_above in ((lo, True), (hi, False)):
            res = []
            for k in range(len(poly)):
                a, b = poly[k], poly[(k + 1) % len(poly)]
                ia = (a[2] >= plane) if keep_above else (a[2] <= plane)
                ib = (b[2] >= plane) if keep_above else (b[2] <= plane)
                if ia:
                    res.append(a)
                if ia != ib:
                    t = (plane - a[2]) / (b[2] - a[2])
                    res.append(a + t * (b - a))
            poly = res
            if len(poly) < 3:
                break
        for k in range(1, len(poly) - 1):
            out.append((poly[0], poly[k], poly[k + 1]))
    return np.array(out, dtype=np.float64).reshape(-1, 3, 3)


def edge_cells(P, spacing, gx0, gy0, W, H):
    """Cells crossed by the XY projection of the edges of triangles P (n,3,3)."""
    out = []
    for k in range(3):
        A, B = P[:, k, :2], P[:, (k + 1) % 3, :2]
        n = np.maximum(1, np.ceil(np.linalg.norm(B - A, axis=1) / spacing)).astype(np.int64)
        for nn in np.unique(n):
            sel = n == nn
            t = np.linspace(0, 1, nn + 1)[None, :, None]
            pts = (A[sel, None] + t * (B[sel, None] - A[sel, None])).reshape(-1, 2)
            ci = np.floor((pts[:, 0] - gx0) / CELL).astype(np.int64)
            cj = np.floor((pts[:, 1] - gy0) / CELL).astype(np.int64)
            inb = (ci >= 0) & (ci < W) & (cj >= 0) & (cj < H)
            out.append(cj[inb] * W + ci[inb])
    return np.concatenate(out) if out else np.zeros(0, np.int64)


def main():
    tg = json.load(open(TARGETS))
    from shapely import wkt
    area = wkt.loads(tg["area_bng_wkt"])
    landmark_list = json.load(open(LANDMARKS))["landmarks"] if os.path.exists(LANDMARKS) else []
    out = {"walkable_coverage_pct": 0.0, "building_coverage_pct": 0.0, "ground_coverage_pct": 0.0,
           "landmarks_detailed": 0}

    mbuf = fetch("manifest.json")
    if not mbuf:
        log("no build found at", SRC)
        print(json.dumps(out))
        return
    man = json.loads(mbuf)
    if REMOTE:  # warm the cache with parallel downloads (same files, same requests as below)
        from concurrent.futures import ThreadPoolExecutor

        def warm(job):
            kind, rel = job
            if kind == "col":
                _CACHE[(rel, None)] = fetch(rel)
            else:
                h = fetch(rel, (0, 19))
                if h and len(h) >= 20 and h[:4] == b"glTF":
                    clen = struct.unpack("<I", h[12:16])[0]
                    _CACHE[(rel, (20, 20 + clen - 1))] = fetch(rel, (20, 20 + clen - 1))
                _CACHE[(rel, (0, 19))] = h
        jobs = [("col", t["collision"]) for t in man.get("tiles", []) if t.get("collision")]
        jobs += [("glb", t["glb"]) for t in man.get("tiles", []) if t.get("glb")]
        with ThreadPoolExecutor(16) as ex:
            list(ex.map(warm, jobs))
    e0, n0 = man["origin"]["e0"], man["origin"]["n0"]

    # ---------------- collision -> walk grid
    minx, miny, maxx, maxy = area.bounds
    gx0, gy0 = minx - MARGIN, miny - MARGIN
    W = int(math.ceil((maxx - minx + 2 * MARGIN) / CELL))
    H = int(math.ceil((maxy - miny + 2 * MARGIN) / CELL))
    ground = np.full(W * H, -np.inf)
    real_ground = np.zeros(W * H, bool)
    solids = []
    for tile in man.get("tiles", []):
        col = read_col(fetch(tile["collision"])) if tile.get("collision") else None
        if col is None:
            log("missing collision", tile.get("id"))
            continue
        v, t, kind, surf = col
        P = v[t] + np.array([e0, n0, 0.0])
        nrm = np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0])
        ln = np.linalg.norm(nrm, axis=1)
        ok = ln > 1e-9
        upish = np.zeros(len(P), bool)
        upish[ok] = np.abs(nrm[ok, 2]) / ln[ok] >= MAX_TILT_COS
        walk = (kind == 1) & upish
        surfmask = ((kind == 1) | (kind == 2)) & (surf != 0) & (surf != 255)
        for mask, target in ((walk, "ground"), (surfmask, "surface")):
            if not mask.any():
                continue
            lin, z = raster_cells(P[mask], gx0, gy0, W, H)
            if target == "ground":
                np.maximum.at(ground, lin, z)
            else:
                real_ground[lin] = True
        if (kind == 0).any():
            solids.append(P[kind == 0])

    blocked = np.zeros(W * H, bool)
    for S in solids:
        # local ground under each solid triangle = lowest finite walk height at its vertices
        vi = np.clip(np.floor((S[:, :, 0] - gx0) / CELL).astype(np.int64), 0, W - 1)
        vj = np.clip(np.floor((S[:, :, 1] - gy0) / CELL).astype(np.int64), 0, H - 1)
        gv = ground[vj * W + vi]
        gv = np.where(np.isfinite(gv), gv, np.nan)
        with np.errstate(all="ignore"):
            glo, ghi = np.nanmin(gv, 1), np.nanmax(gv, 1)
        ok = np.isfinite(glo)
        clipped = clip_slab(S[ok], glo[ok] + BODY_LO, ghi[ok] + BODY_HI)
        # the clipped pieces lie inside the body column: block every cell they cross
        if len(clipped):
            blocked[edge_cells(clipped, CELL * 0.5, gx0, gy0, W, H)] = True
            blocked[raster_cells(clipped, gx0, gy0, W, H)[0]] = True

    free = np.isfinite(ground) & ~blocked
    reach = np.zeros(W * H, bool)
    sp = man.get("spawn")
    if sp and free.any():
        from scipy.sparse import coo_matrix
        from scipy.sparse.csgraph import connected_components
        G = ground.reshape(H, W)
        F = free.reshape(H, W)
        ids = np.arange(W * H).reshape(H, W)
        with np.errstate(invalid="ignore"):
            eh = F[:, :-1] & F[:, 1:] & (np.abs(G[:, :-1] - G[:, 1:]) <= STEP_H)
            ev = F[:-1, :] & F[1:, :] & (np.abs(G[:-1, :] - G[1:, :]) <= STEP_H)
        r = np.concatenate([ids[:, :-1][eh], ids[:-1, :][ev]])
        c = np.concatenate([ids[:, 1:][eh], ids[1:, :][ev]])
        graph = coo_matrix((np.ones(len(r), np.int8), (r, c)), shape=(W * H, W * H))
        _, lab = connected_components(graph, directed=False)
        si = int((sp["x"] + e0 - gx0) // CELL)
        sj = int((sp["y"] + n0 - gy0) // CELL)
        # spawn cell = nearest free cell within 2 m of the spawn point
        best = None
        R = int(2 / CELL)
        for dj in range(-R, R + 1):
            for di in range(-R, R + 1):
                i, j = si + di, sj + dj
                if 0 <= i < W and 0 <= j < H and F[j, i]:
                    d = di * di + dj * dj
                    if best is None or d < best[0]:
                        best = (d, j * W + i)
        if best is not None:
            reach = lab == lab[best[1]]
    log("grid", W, H, "walk cells", int(np.isfinite(ground).sum()), "free", int(free.sum()), "reachable", int(reach.sum()))

    # ---------------- walkable coverage
    S = np.array([[s[0], s[1], s[3]] for s in tg["walk"]["samples"]])
    R = int(math.ceil(SNAP / CELL))
    si = np.floor((S[:, 0] - gx0) / CELL).astype(np.int64)
    sj = np.floor((S[:, 1] - gy0) / CELL).astype(np.int64)
    hit = np.zeros(len(S), bool)
    RG = reach.reshape(H, W)
    for dj in range(-R, R + 1):
        for di in range(-R, R + 1):
            cx = gx0 + (si + di + 0.5) * CELL
            cy = gy0 + (sj + dj + 0.5) * CELL
            near = (cx - S[:, 0]) ** 2 + (cy - S[:, 1]) ** 2 <= SNAP ** 2
            i, j = si + di, sj + dj
            inb = (i >= 0) & (i < W) & (j >= 0) & (j < H)
            ok = np.zeros(len(S), bool)
            ok[inb] = RG[j[inb], i[inb]]
            hit |= near & ok
            if VERBOSE:
                fr = np.zeros(len(S), bool); fr[inb] = free.reshape(H, W)[j[inb], i[inb]]
                anyfree = (anyfree if dj + R or di + R else np.zeros(len(S), bool)) | (near & fr)
    out["walkable_coverage_pct"] = round(100.0 * S[hit, 2].sum() / S[:, 2].sum(), 2)
    if VERBOSE:  # diagnostics: missed samples -> data/derived/walk_misses.json (BNG, way id)
        W_ = np.array([s[2] for s in tg["walk"]["samples"]])
        json.dump([[float(a), float(b), int(c), int(f)] for (a, b, _), c, f in zip(S[~hit], W_[~hit], anyfree[~hit])],
                  open(os.path.join(ROOT, "data/derived/walk_misses.json"), "w"))
        np.savez_compressed(os.path.join(ROOT, "data/derived/walk_grid.npz"), free=free.reshape(H, W), reach=RG, ground=ground.reshape(H, W),
                            blocked=blocked.reshape(H, W), gx0=gx0, gy0=gy0, cell=CELL)

    # ---------------- ground coverage (5 m cells with centre in study area)
    from shapely import vectorized
    gs = tg["grid"]["step"]
    xs = np.arange(minx + gs / 2, maxx, gs)
    ys = np.arange(miny + gs / 2, maxy, gs)
    X, Y = np.meshgrid(xs, ys)
    inside = vectorized.contains(area, X, Y)
    cx, cy = X[inside], Y[inside]
    ci = np.floor((cx - gx0) / CELL).astype(np.int64)
    cj = np.floor((cy - gy0) / CELL).astype(np.int64)
    out["ground_coverage_pct"] = round(100.0 * real_ground[cj * W + ci].mean(), 2)

    # ---------------- buildings
    targets = {b["osm_id"]: b for b in tg["buildings"]}
    by_tile = {}
    for b in man.get("buildings", []):
        if b.get("osm_id") in targets:
            by_tile.setdefault(b.get("tile"), []).append(b)
    tiles = {t["id"]: t for t in man.get("tiles", [])}
    present, tops = set(), {}
    for tid, blist in by_tile.items():
        t = tiles.get(tid)
        js = glb_json(t["glb"]) if t and t.get("glb") else None
        if not js:
            continue
        nodes = js.get("nodes", [])
        meshes = js.get("meshes", [])
        accs = js.get("accessors", [])
        byname = {n.get("name"): n for n in nodes if n.get("name")}
        for b in blist:
            n = byname.get(b.get("node") or "b:" + b["osm_id"])
            if not n or "mesh" not in n:
                continue
            top, cnt = -np.inf, 0
            for prim in meshes[n["mesh"]].get("primitives", []):
                a = accs[prim["attributes"]["POSITION"]] if "POSITION" in prim.get("attributes", {}) else None
                if a and a.get("count", 0) > 0:
                    cnt += a["count"]
                    if "max" in a:
                        top = max(top, a["max"][1])
            if cnt > 0:
                present.add(b["osm_id"])
                if np.isfinite(top):
                    tops[b["osm_id"]] = top + (n.get("translation") or [0, 0, 0])[1]
    out["building_coverage_pct"] = round(100.0 * len(present) / max(1, len(targets)), 2)

    # ---------------- height accuracy
    stats = lidar_stats(tg["buildings"])
    if stats is not None and tops:
        good = n = 0
        for oid, top in tops.items():
            s = stats.get(oid)
            if not s:
                continue
            n += 1
            good += abs((top - s["dtm_med"]) - s["ndsm_p95"]) <= HEIGHT_TOL
        if n:
            out["height_accuracy_pct"] = round(100.0 * good / n, 2)

    # ---------------- landmarks
    fixed = {l["id"] for l in landmark_list}
    cnt = 0
    for l in man.get("landmarks", []):
        if l.get("id") in fixed and l.get("detailed") and os.path.isfile(os.path.join(ROOT, "landmarks", l["id"] + ".png")):
            cnt += 1
    out["landmarks_detailed"] = cnt

    # ---------------- street objects: OSM street-object nodes in the study area (scripts/street_objects.py TYPES,
    # plus natural=tree) present within 1 m of their mapped position in a layer the viewer draws by default
    sp = os.path.join(ROOT, "data/derived/street_object_targets.json")
    if os.path.exists(sp):
        st = json.load(open(sp))   # [[E, N, type]], type 0 = tree
        layers = man.get("layers", {})
        pts = {0: [], 1: []}   # 0 = trees layer, 1 = objects layer: [x, y, type]
        for tile in man.get("tiles", []):
            for key, lay, rec in (("trees", 0, 6), ("objects", 1, 7)):
                if tile.get(key) and layers.get(key):
                    b = fetch(tile[key])
                    if b:
                        a = np.frombuffer(b, np.float32).reshape(-1, rec)
                        pts[lay] += [(x + e0, y + n0, 0 if lay == 0 else int(k)) for x, y, k in zip(a[:, 0], a[:, 1], a[:, 3])]
        from scipy.spatial import cKDTree
        hit = 0
        trees = cKDTree(np.array([p[:2] for p in pts[0]])) if pts[0] else None
        objs = np.array(pts[1]) if pts[1] else np.zeros((0, 3))
        okd = cKDTree(objs[:, :2]) if len(objs) else None
        for E, N, k in st:
            if k == 0:
                hit += bool(trees is not None and trees.query([E, N])[0] <= 1.0)
            elif okd is not None:
                hit += any(int(objs[i, 2]) == k for i in okd.query_ball_point([E, N], 1.0))
        out["street_objects_pct"] = round(100.0 * hit / max(1, len(st)), 2)

    # ---------------- real facades: area of photo-textured wall quads in the build's default-on facades layer
    # (scripts/facades.py) / street-facing wall area in the study area (building edges within 30 m of a walkable
    # way, ground to LiDAR eave; the denominator is written by facades.py to data/derived/facades.json)
    fp = os.path.join(ROOT, "data/derived/facades.json")
    if os.path.exists(fp):
        tot = json.load(open(fp))["area_total"]
        real = 0.0
        if man.get("layers", {}).get("facades"):
            for tile in man.get("tiles", []):
                fl = tile.get("facades") or []
                for b in (fetch(f) for f in ([fl] if isinstance(fl, str) else fl)):
                    q = np.frombuffer(b, np.float32).reshape(-1, 4, 5)
                    w = np.hypot(q[:, 1, 0] - q[:, 0, 0], q[:, 1, 1] - q[:, 0, 1])
                    real += float((w * (q[:, 3, 2] - q[:, 0, 2])).sum())
        out["real_facade_pct"] = round(100.0 * min(real, tot) / max(tot, 1.0), 2)
    if FAILED:
        out["fetch_failures"] = len(FAILED)
    print(json.dumps(out))


def lidar_stats(buildings):
    """Per building: median DTM and 95th percentile of DSM-DTM inside its OSM footprint. Cached."""
    dtm_p, dsm_p = os.path.join(LIDAR_DIR, "dtm_1m.tif"), os.path.join(LIDAR_DIR, "dsm_1m.tif")
    for res in ("50cm", "25cm"):
        a, b = os.path.join(LIDAR_DIR, f"dtm_{res}.tif"), os.path.join(LIDAR_DIR, f"dsm_{res}.tif")
        if os.path.exists(a) and os.path.exists(b):
            dtm_p, dsm_p = a, b
    if not (os.path.exists(dtm_p) and os.path.exists(dsm_p)):
        return None
    key = f"{dtm_p}:{os.path.getmtime(dtm_p)}:{dsm_p}:{os.path.getmtime(dsm_p)}:{os.path.getmtime(TARGETS)}"
    if os.path.exists(CACHE):
        c = json.load(open(CACHE))
        if c.get("key") == key:
            return c["stats"]
    import rasterio
    from rasterio.features import geometry_mask
    from rasterio.windows import from_bounds
    from shapely.geometry import shape
    stats = {}
    with rasterio.open(dtm_p) as dtm, rasterio.open(dsm_p) as dsm:
        for b in buildings:
            if not b.get("footprint"):
                continue
            g = shape(b["footprint"])
            x0, y0, x1, y1 = g.bounds
            win = from_bounds(x0 - 1, y0 - 1, x1 + 1, y1 + 1, dtm.transform).round_offsets().round_lengths()
            if win.width < 1 or win.height < 1:
                continue
            a = dtm.read(1, window=win, masked=True).astype("f8")
            s = dsm.read(1, window=from_bounds(*dtm.window_bounds(win), dsm.transform).round_offsets().round_lengths(), masked=True).astype("f8")
            if a.shape != s.shape:
                continue
            m = geometry_mask([b["footprint"]], a.shape, dtm.window_transform(win), invert=True, all_touched=False)
            if m.sum() == 0:
                m = geometry_mask([b["footprint"]], a.shape, dtm.window_transform(win), invert=True, all_touched=True)
            valid = m & ~np.ma.getmaskarray(a) & ~np.ma.getmaskarray(s)
            if valid.sum() == 0:
                continue
            nd = (s.data - a.data)[valid]
            stats[b["osm_id"]] = {"dtm_med": float(np.median(a.data[valid])), "ndsm_p95": float(np.percentile(nd, 95))}
    json.dump({"key": key, "stats": stats}, open(CACHE, "w"))
    return stats


if __name__ == "__main__":
    main()
