"""Real photo facades: project non-held-out Mapillary photos onto street-facing building walls, centre first.

  .venv/bin/python -I scripts/facades.py [--out site] [--radius 150]

For every building edge (in the study area for the real_facade_pct denominator; textured only within RADIUS) of Great St Mary's whose midpoint lies within 30 m of a walkable way, pick the
best Mapillary photo (perspective, SfM pose; never a held-out benchmark photo or a same-sequence frame within 15 m of
one): the whole wall piece in frame, facing the camera, 4-35 m away, and no other building footprint in between.
The wall rectangle (ground to eave, eave from the LiDAR DSM just inside the edge) is resampled from the photo through
the camera model (OpenSfM rotation vector + focal, k1, k2) into a texture at PX px/m and packed into per-tile atlases.

Output: <out>/facades/<tile>.webp (RGBA atlas; sky above the roofline is transparent) and <tile>.bin: float32 records of 4 corners [x, y, z, u, v] in the
collision frame (x east, y north, z up), corner order bottom-left, bottom-right, top-right, top-left seen from
outside. Manifest tiles get "facades"/"facade_tex"/"nfacades"; manifest.layers.facades = True. Also writes
data/derived/facades.json (per piece: building, area, photo id) used by kpi.py for real_facade_pct.
"""
import hashlib
import io
import json
import math
import os
import sys
import time
import urllib.request

import numpy as np
import rasterio
from PIL import Image
from pyproj import Transformer
from scipy.ndimage import map_coordinates
from scipy.spatial.transform import Rotation
from shapely import STRtree
from shapely.geometry import LineString, Point, Polygon

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build as B  # noqa: E402

ROOT = B.ROOT
RADIUS = float(sys.argv[sys.argv.index("--radius") + 1]) if "--radius" in sys.argv else 150.0
STRICT = "--strict" in sys.argv   # also skip every frame of a sequence that holds a benchmark photo
PX = 40.0             # texture resolution (px per metre)
MAXPIECE = 6.0       # split long edges into pieces of at most this length (m)
MAXDIST = 40.0        # farthest camera used for a piece (m)
BANDS = 3             # vertical bands per wall piece, each from its own photo
MAXELEV = 50.0        # deg: wall tops seen steeper than this from the camera are stretched/unreliable; cap the textured height
COSN = float(os.environ.get("WC_FAC_COSN", "0.12"))   # min cos(angle) between the wall normal and the camera direction
SPLITS = int(os.environ.get("WC_FAC_SPLITS", "3"))    # a piece with no photo is halved up to this many times
CAM_H = 2.0           # assumed camera height above the DTM (m): most sequences are bike/helmet or car mounted
ATLAS = 2048
ALTS = 4              # other cameras tried for pixels the best photo has masked (people, bikes, vehicles)
MASKS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data/raw/mapillary_masks")
USE_MASKS = os.environ.get("WC_FAC_MASKS", "1") == "1"
CACHE = os.path.join(ROOT, "data/raw/mapillary_facade")
GSM = (0.1183, 52.2052)
to_bng = Transformer.from_crs(4326, 27700, always_xy=True)


def log(*a):
    print("[facades]", *a, flush=True)


def cameras(heldout, cx, cy):
    held = set(heldout["images"])
    near = heldout["sequence_near"]
    out = []
    for x in json.load(open(os.path.join(ROOT, "data/raw/mapillary_list.json"))):
        if x["id"] in held or x.get("is_pano") or x.get("camera_type") not in ("perspective", None) or not x.get("computed_rotation"):
            continue
        lon, lat = x["computed_geometry"]["coordinates"]
        e, n = to_bng.transform(lon, lat)
        if math.hypot(e - cx, n - cy) > RADIUS + 40:
            continue
        if any(s == x.get("sequence") and (STRICT or math.hypot(e - se, n - sn) < r) for s, se, sn, r in near):
            continue
        # local ENU -> BNG grid: finite differences (grid convergence ~1.7 deg here)
        e1, n1 = to_bng.transform(lon + 1e-4, lat)
        e2, n2 = to_bng.transform(lon, lat + 1e-4)
        M = np.array([[e1 - e, e2 - e], [n1 - n, n2 - n]])
        M /= np.linalg.norm(M, axis=0)
        R = Rotation.from_rotvec(x["computed_rotation"]).as_matrix()   # world ENU -> camera (x right, y down, z fwd)
        G = np.eye(3); G[:2, :2] = M                                     # ENU -> grid
        Rg = R @ G.T                                                    # grid -> camera
        flip = (Rg.T @ [0, 1, 0])[2] > 0                                # stored image is upside down vs pose
        f, k1, k2 = (x.get("camera_parameters") or [0.85, 0, 0])[:3]
        out.append(dict(id=x["id"], e=e - B.E0, n=n - B.N0, R=Rg, f=f, k1=k1, k2=k2, w=x["width"], h=x["height"],
                        flip=bool(flip), seq=x.get("sequence")))
    return out


def project(cam, P):
    """P (k,3) local grid coords -> normalised image coords (u,v in [0,1]) and depth."""
    q = (P - [cam["e"], cam["n"], cam["z"]]) @ cam["R"].T
    z = q[:, 2]
    xn, yn = q[:, 0] / np.maximum(z, 1e-6), q[:, 1] / np.maximum(z, 1e-6)
    r2 = xn * xn + yn * yn
    d = 1 + cam["k1"] * r2 + cam["k2"] * r2 * r2
    s = max(cam["w"], cam["h"])
    u = (cam["f"] * s * xn * d + cam["w"] / 2) / cam["w"]
    v = (cam["f"] * s * yn * d + cam["h"] / 2) / cam["h"]
    if cam["flip"]:
        u, v = 1 - u, 1 - v
    return u, v, z


def fetch(img_id, token):
    p = os.path.join(CACHE, img_id + ".jpg")
    if not os.path.exists(p):
        q = "https://graph.mapillary.com/%s?fields=thumb_2048_url&access_token=%s" % (img_id, token)
        url = json.load(urllib.request.urlopen(q, timeout=30))["thumb_2048_url"]
        data = urllib.request.urlopen(url, timeout=60).read()
        open(p, "wb").write(data)
    return np.asarray(Image.open(p).convert("RGB"), np.float32)


def mask_of(img_id):
    """Transient-object mask (scripts/masks.py) as a bool array, or None if there is none."""
    p = os.path.join(MASKS, img_id + ".png")
    return np.asarray(Image.open(p)) > 127 if (USE_MASKS and os.path.exists(p)) else None


def sample_mask(m, u, v):
    mh, mw = m.shape
    return m[np.clip((v * mh).astype(int), 0, mh - 1), np.clip((u * mw).astype(int), 0, mw - 1)]


def main():
    t0 = time.time()
    os.makedirs(CACHE, exist_ok=True)
    cx, cy = to_bng.transform(*GSM)
    nodes, ways, rels, pnodes = B.load_osm()
    blds, walks = [], []
    for w in ways.values():
        t = w.get("tags", {})
        if t.get("building", "no") != "no":
            g = B.way_area(w, nodes)
            if g is not None and g.area > 4:
                blds.append(("way/%d" % w["id"], g))
        elif t.get("highway") in B.WALK and t.get("foot") != "no":
            c = B.coords(w, nodes)
            if c and len(c) >= 2:
                walks.append(LineString(c))
    for r in rels:
        t = r.get("tags", {})
        if t.get("building", "no") != "no":
            g = B.rel_area(r, ways, nodes)
            if g is not None and g.area > 4:
                blds.append(("relation/%d" % r["id"], g))
    wtree = STRtree(walks)
    btree = STRtree([g for _, g in blds])
    centre = Point(cx, cy)
    sx0, sy0 = to_bng.transform(0.1080, 52.1975); sx1, sy1 = to_bng.transform(0.1330, 52.2125)
    study = Polygon([(sx0, sy0), (sx1, sy0), (sx1, sy1), (sx0, sy1)])   # study area (bbox in BNG, close enough)
    dtm_r = rasterio.open(os.path.join(ROOT, "data/lidar/dtm_1m.tif"))
    dsm_r = rasterio.open(os.path.join(ROOT, "data/lidar/dsm_1m.tif"))
    DTM, DSM = dtm_r.read(1).astype("f8"), dsm_r.read(1).astype("f8")
    LEFT, TOP = dtm_r.transform.c, dtm_r.transform.f

    def samp(A, E, N):
        return map_coordinates(A, [TOP - np.asarray(N) - 0.5, np.asarray(E) - LEFT - 0.5], order=1, mode="nearest")

    # ---- wall pieces (street-facing, within RADIUS)
    pieces = []
    for bi, (bid, g) in enumerate(blds):
        if not g.intersects(study):
            continue
        gd = g.distance(centre)
        for poly in B.polys_of(g):
            p = poly if poly.exterior.is_ccw else Polygon(poly.exterior.coords[::-1])
            ring = np.asarray(p.exterior.coords)
            for a, b in zip(ring[:-1], ring[1:]):
                L = float(np.hypot(*(b - a)))
                if L < 2.0:
                    continue
                k = int(math.ceil(L / MAXPIECE))
                for j in range(k):
                    pa, pb = a + (b - a) * j / k, a + (b - a) * (j + 1) / k
                    mid = (pa + pb) / 2
                    if not len(wtree.query(Point(mid).buffer(30.0), predicate="intersects")):
                        continue
                    d = (pb - pa) / np.linalg.norm(pb - pa)
                    nrm = np.array([d[1], -d[0]])          # outward for a CCW ring
                    ts = np.linspace(0.1, 0.9, 7)
                    S = pa + (pb - pa) * ts[:, None]
                    In = S - nrm * 1.5
                    z0 = float(samp(DTM, S[:, 0] + nrm[0] * 1.5, S[:, 1] + nrm[1] * 1.5).min())
                    eave = float(np.percentile(samp(DSM, In[:, 0], In[:, 1]), 20)) - z0
                    eave = float(np.clip(eave, 3.0, 30.0))
                    pieces.append(dict(b=bid, bi=bi, a=pa, bb=pb, n=nrm, z0=z0, h=eave, L=float(np.linalg.norm(pb - pa)),
                                       d=float(np.hypot(*(mid - [cx, cy])))))
    log(len(pieces), "street-facing wall pieces in the study area")
    all_pieces = [(round(p["d"], 1), round(p["L"] * p["h"], 2)) for p in pieces]
    tot_area = sum(a for _, a in all_pieces)
    pieces = [p for p in pieces if p["d"] <= RADIUS]
    log(len(pieces), "within", RADIUS, "m of GSM")

    held = json.load(open(os.path.join(ROOT, "data/benchmark/heldout.json")))
    cams = cameras(held, cx, cy)
    for c in cams:
        c["z"] = float(samp(DTM, [c["e"] + B.E0], [c["n"] + B.N0])[0]) + CAM_H
    log(len(cams), "usable non-held-out photos")
    cp = np.array([[c["e"], c["n"]] for c in cams])

    # ---- best photo per piece. A piece with no photo is split into halves (once); the part of a wall above the
    # best photo's visible band becomes a new piece (an upper band, up to BANDS per wall) and gets its own photo.
    queue, done = list(pieces), []
    why = {"angle": 0, "frame": 0, "occluded": 0}
    while queue:
        pc = queue.pop(0)
        a, b, z0, h = pc["a"] - [B.E0, B.N0], pc["bb"] - [B.E0, B.N0], pc["z0"], pc["h"]
        band = pc.get("band", 0)
        hmin = 2.5 if band == 0 else 1.5
        mid = (a + b) / 2
        dist = np.hypot(*(cp - mid).T)
        best, cands = None, []
        for i in np.where((dist > 4) & (dist < MAXDIST))[0]:
            c = cams[i]
            v = np.array([c["e"], c["n"]]) - mid
            cosn = float(v @ pc["n"] / np.linalg.norm(v))
            if cosn < COSN:
                why["angle"] += 1
                continue
            # visible height: the tallest top edge (<= eave) whose corners are in frame; at least 2.5 m (or the eave)
            hv = None
            hcap = c["z"] - z0 + math.tan(math.radians(MAXELEV)) * float(np.linalg.norm(v))
            if hcap < min(h, hmin):
                continue
            for hh in np.linspace(min(h, hcap), min(h, hmin), 8):
                C = np.array([[a[0], a[1], z0], [b[0], b[1], z0], [b[0], b[1], z0 + hh], [a[0], a[1], z0 + hh]])
                u, vv, zz = project(c, C)
                if not ((zz < 1).any() or (u < 0.01).any() or (u > 0.99).any() or (vv < 0.01).any() or (vv > 0.99).any()):
                    hv = float(hh)
                    break
            if hv is None:
                why["frame"] += 1
                continue
            # occlusion: sight lines to 3 points along the wall foot must not cross another footprint
            ok = True
            for t in (0.15, 0.5, 0.85):
                q = a + (b - a) * t + pc["n"] * 0.3
                ln = LineString([(c["e"] + B.E0, c["n"] + B.N0), (q[0] + B.E0, q[1] + B.N0)])
                for j in btree.query(ln, predicate="intersects"):
                    ok = False
                    break
                if not ok:
                    break
            if not ok:
                why["occluded"] += 1
                continue
            du, dv = u[1] - u[0], vv[1] - vv[0]
            area = abs(du * (vv[3] - vv[0]) - dv * (u[3] - u[0])) * c["w"] * c["h"]
            score = min(area, 2e5) * cosn * cosn * hv / h
            cands.append((score, i))
            if best is None or score > best[0]:
                best = (score, i, hv)
        pc["cam"] = None if best is None else best[1]
        pc["alts"] = [i for _, i in sorted(cands, reverse=True) if best is None or i != best[1]][:ALTS]
        if best is None:
            if band == 0 and pc.get("half", 0) < SPLITS and pc["L"] > 2.5:
                m = (pc["a"] + pc["bb"]) / 2
                for pa, pb in ((pc["a"], m), (m, pc["bb"])):
                    queue.append(dict(pc, a=pa, bb=pb, L=pc["L"] / 2, half=pc.get("half", 0) + 1))
                continue
        else:
            if best[2] < h - 1.0 and band + 1 < BANDS:
                queue.append(dict(pc, z0=z0 + best[2], h=h - best[2], band=band + 1))
            pc["h"] = best[2]
        done.append(pc)
    pieces = done
    got = [pc for pc in pieces if pc["cam"] is not None]
    log(len(got), "pieces have a photo;", len({pc["cam"] for pc in got}), "photos needed; camera rejections", why)
    for r in (50, 100, 150, 300, 500):
        a1 = sum(p["L"] * p["h"] for p in got if p["d"] <= r); a0 = sum(a for d, a in all_pieces if d <= r)
        log("  within %d m: %.1f%% of street-facing wall area has a photo (before sky crop)" % (r, 100 * a1 / max(a0, 1)))
    if "--dry" in sys.argv:
        return

    # ---- rectify and pack (shelf packing per tile)
    token = open(os.path.join(ROOT, "data/mapillary_token")).read().strip()
    tiles = {}
    for pc in got:
        mid = (pc["a"] + pc["bb"]) / 2 - [B.E0, B.N0]
        tx = int((mid[0] + B.EXT) // B.TILE); ty = int((mid[1] + B.EXT) // B.TILE)
        tiles.setdefault("t_%d_%d" % (tx, ty), []).append(pc)
    out_dir = os.path.join(B.OUT, "facades")
    os.makedirs(out_dir, exist_ok=True)
    for f in os.listdir(out_dir):
        os.remove(os.path.join(out_dir, f))
    imgs, meta, man_t, n_photos = {}, [], {}, set()
    n_alt, n_hole, n_px = [0], [0], [0]
    for tid, lst in sorted(tiles.items()):
        imgs.clear()   # decoded photos are ~40 MB each: keep only this tile's (all of them once filled RAM, swap and the disk)
        lst.sort(key=lambda p: -p["h"])
        pages, cur = [], None
        for pc in lst:
            W = int(min(ATLAS, max(8, round(pc["L"] * PX)))); H = int(min(ATLAS // 2, max(8, round(pc["h"] * PX))))
            if cur is not None and cur["x"] + W > ATLAS:          # next shelf
                cur["x"], cur["y"], cur["shelf"] = 0, cur["y"] + cur["shelf"] + 2, 0
            if cur is None or cur["y"] + H > ATLAS:                # next page
                cur = dict(atlas=np.zeros((ATLAS, ATLAS, 4), np.uint8), x=0, y=0, shelf=0, recs=[]); pages.append(cur)
            x, y, atlas, recs = cur["x"], cur["y"], cur["atlas"], cur["recs"]
            c = cams[pc["cam"]]
            if c["id"] not in imgs:
                try:
                    imgs[c["id"]] = fetch(c["id"], token)
                except Exception as e:  # noqa: BLE001
                    log("fetch failed", c["id"], e); imgs[c["id"]] = None
            im = imgs[c["id"]]
            n_photos.add(c["id"])
            if im is None:
                continue
            a, b = pc["a"] - [B.E0, B.N0], pc["bb"] - [B.E0, B.N0]
            s = (np.arange(W) + 0.5) / W; t = 1 - (np.arange(H) + 0.5) / H
            S, T = np.meshgrid(s, t)
            P = np.c_[(a[0] + (b[0] - a[0]) * S).ravel(), (a[1] + (b[1] - a[1]) * S).ravel(), (pc["z0"] + pc["h"] * T).ravel()]
            u, v, _ = project(c, P)
            ih, iw = im.shape[:2]
            rgb = np.stack([map_coordinates(im[..., k], [v * ih - 0.5, u * iw - 0.5], order=1, mode="nearest") for k in range(3)], 1)
            # people, bikes and vehicles in the photo: take those pixels from the next-best photos, else leave them
            # transparent (the procedural wall shows through) rather than bake a smeared passer-by into the wall
            hole = np.zeros(len(P), bool)
            mk = mask_of(c["id"])
            if mk is not None:
                hole = sample_mask(mk, u, v)
                for j in pc.get("alts", []) if hole.any() else []:
                    cj = cams[j]
                    mj = mask_of(cj["id"])
                    if cj["id"] not in imgs:
                        try:
                            imgs[cj["id"]] = fetch(cj["id"], token)
                        except Exception:  # noqa: BLE001
                            imgs[cj["id"]] = None
                    imj = imgs[cj["id"]]
                    if imj is None or mj is None:
                        continue
                    idx = np.where(hole)[0]
                    uj, vj, zj = project(cj, P[idx])
                    ok = (zj > 1) & (uj > 0) & (uj < 1) & (vj > 0) & (vj < 1)
                    ok[ok] = ~sample_mask(mj, uj[ok], vj[ok])
                    if ok.any():
                        jh, jw = imj.shape[:2]
                        for k in range(3):
                            rgb[idx[ok], k] = map_coordinates(imj[..., k], [vj[ok] * jh - 0.5, uj[ok] * jw - 0.5], order=1, mode="nearest")
                        hole[idx[ok]] = False
                        n_alt[0] += int(ok.sum())
                    if not hole.any():
                        break
                n_hole[0] += int(hole.sum()); n_px[0] += len(P)
            hole = hole.reshape(H, W)
            rgb = np.clip(rgb, 0, 255).reshape(H, W, 3)
            # sky above the real roofline: bright, bluish or grey-white pixels connected to the top edge -> transparent
            r_, g_, b_ = rgb[..., 0], rgb[..., 1], rgb[..., 2]
            lum = 0.3 * r_ + 0.59 * g_ + 0.11 * b_
            sat = rgb.max(-1) - rgb.min(-1)
            sky = ((lum > 175) & (sat < 40)) | ((b_ > r_ + 12) & (b_ > 140) & (lum > 120))
            sky = np.cumprod(sky, axis=0).astype(bool)          # only runs that start at the top row
            keep_rows = np.where(~sky.all(1))[0]
            if len(keep_rows) == 0 or keep_rows[-1] - keep_rows[0] < H * 0.3:
                continue
            top = int(keep_rows[0])                             # crop all-sky rows off the quad top
            h_new = pc["h"] * (H - top) / H
            rgb, sky, hole = rgb[top:], sky[top:], hole[top:]
            H = H - top
            atlas[y:y + H, x:x + W, :3] = rgb.astype(np.uint8)
            atlas[y:y + H, x:x + W, 3] = np.where(sky | hole, 0, 255)
            pc["h"] = h_new
            u0, u1, v0, v1 = x / ATLAS, (x + W) / ATLAS, 1 - (y + H) / ATLAS, 1 - y / ATLAS
            o = pc["n"] * 0.04
            z0, z1 = pc["z0"], pc["z0"] + pc["h"]
            recs += [a[0] + o[0], a[1] + o[1], z0, u0, v0, b[0] + o[0], b[1] + o[1], z0, u1, v0,
                     b[0] + o[0], b[1] + o[1], z1, u1, v1, a[0] + o[0], a[1] + o[1], z1, u0, v1]
            meta.append(dict(b=pc["b"], d=round(pc["d"], 1), area=round(pc["L"] * pc["h"], 2), photo=c["id"], tile=tid))
            cur["x"] = x + W + 2; cur["shelf"] = max(cur["shelf"], H)
        out = []
        for k, pg in enumerate(pages):
            if not pg["recs"]:
                continue
            used = min(ATLAS, pg["y"] + pg["shelf"] + 2)
            hpx = 1 << max(8, int(math.ceil(math.log2(used))))
            # v was computed for a full-height atlas; rescale to the cropped one
            r = np.asarray(pg["recs"], np.float32).reshape(-1, 5)
            r[:, 4] = 1 - (1 - r[:, 4]) * ATLAS / hpx
            name = "%s_%d" % (tid, k)
            Image.fromarray(pg["atlas"][:hpx], "RGBA").save(os.path.join(out_dir, name + ".webp"), quality=82, method=5)
            r.tofile(os.path.join(out_dir, name + ".bin"))
            out.append(("facades/%s.bin" % name, "facades/%s.webp" % name, len(r) // 4))
        if out:
            man_t[tid] = out
    # attribution (CC-BY-SA 4.0): every photo used, with its Mapillary contributor
    L = {x["id"]: x for x in json.load(open(os.path.join(ROOT, "data/raw/mapillary_list.json")))}
    used = sorted({m["photo"] for m in meta})
    json.dump({"licence": "CC-BY-SA 4.0 (Mapillary); the facade atlases are adaptations and share alike",
               "photos": [{"id": i, "url": "https://www.mapillary.com/app/?pKey=" + i,
                           "creator": (L[i].get("creator") or {}).get("username", "")} for i in used]},
              open(os.path.join(out_dir, "credits.json"), "w"), indent=0)
    man_path = os.path.join(B.OUT, "manifest.json")
    man = json.load(open(man_path))
    for tile in man["tiles"]:
        for k in ("facades", "facade_tex", "nfacades"):
            tile.pop(k, None)
        if tile["id"] in man_t:
            o = man_t[tile["id"]]   # one entry per atlas page
            tile["facades"], tile["facade_tex"], tile["nfacades"] = [x[0] for x in o], [x[1] for x in o], sum(x[2] for x in o)
    man.setdefault("layers", {})["facades"] = True
    # atlas contents can change with an identical layout (e.g. masks): put their digest in the manifest so the build
    # hash (scripts/build_hash.py) and the benchmark cache see a new build
    hd = hashlib.sha256()
    for f in sorted(os.listdir(out_dir)):
        hd.update(open(os.path.join(out_dir, f), "rb").read())
    man["facades_digest"] = hd.hexdigest()[:16]
    json.dump(man, open(man_path, "w"), separators=(",", ":"))
    json.dump({"radius": RADIUS, "area_total": round(tot_area, 1), "all_pieces": all_pieces,
               "photos": sorted({m["photo"] for m in meta}), "textured": meta},
              open(os.path.join(ROOT, "data/derived/facades.json"), "w"))
    log("textured %d pieces, %.1f%% of the study area's street-facing wall area, %d photos, %d atlas pages, %.0fs" % (
        len(meta), 100 * sum(m["area"] for m in meta) / max(tot_area, 1), len(n_photos), sum(len(v) for v in man_t.values()), time.time() - t0))
    near = {}
    for m in meta:
        near[m["photo"]] = min(near.get(m["photo"], 1e9), m["d"])
    json.dump(sorted(near, key=near.get), open(os.path.join(ROOT, "data/derived/facade_photo_order.json"), "w"))
    log("masks: %d px filled from other photos, %.1f%% of pixels left transparent" % (n_alt[0], 100 * n_hole[0] / max(n_px[0], 1)))


if __name__ == "__main__":
    main()
