"""Street-facing walls of the Market Square zone, for facade annotation and the parts-based facade builder.

    .venv/bin/python -I scripts/zone_walls.py

Zone: OSM building edges (>= 2 m) whose midpoint lies within 90 m of 52.2053N, 0.1190E and which face a walkable
way (an OSM walk sample within 3 m of a point 2-25 m out along the outward normal, with no other footprint between).
Per wall: id "<osm_id>:<edge index>", p0/p1 in the collision frame (x east, y north; the wall runs p0 -> p1 with the
outside on the right), ground z (DTM 1.5 m outside), eave z (median DSM 1-2.5 m inside), building tags, and up to 6
reference photos: cached non-held-out Mapillary photos (data/raw/mapillary_facade) whose camera is 4-35 m in front of
the wall and looks at it. Held out: data/benchmark/heldout.json + heldout_ms.json (never offered as references).
Writes data/annotations/market_square/walls.json.

Street-facing rule for facade_geometry_match_pct (session 46; used by zone_kpi.py and city_facades.py, see
faces_street()): the KPI's written definition counts STREET-FACING facades only. The wall lists above (built with
every walk sample, so they also hold college-court, back-yard and private-path walls, which still get built) are
filtered for the KPI by: wall length >= 3 m; along the outward normal, probing 2, 5, 9, 14, 20, 25 m out, the first
probe point within 3 m of a PUBLIC walk sample is reached before any other building footprint crosses the line
from 0.3 m out (so party walls and walls hidden behind a neighbour fail). Public walk sample: an osm_targets walk
sample whose OSM way is not access=private/no (unless foot=yes/designated/permissive) and not foot=private/no;
this drops the gated college courts, private yards and staircases (their paths are access=private in OSM).
"""
import json
import math
import os
import sys

import numpy as np
import rasterio
from pyproj import Transformer
from scipy.spatial import cKDTree
from shapely import STRtree
from shapely.geometry import LineString, Point

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build as B  # noqa: E402
import make_benchmark as MB  # noqa: E402

ROOT = B.ROOT
CENTRE = (0.1190, 52.2053)
R = 90.0
OUT = os.path.join(ROOT, "data/annotations/market_square/walls.json")
REF = os.path.join(ROOT, "data/raw/mapillary_ref")   # 1024 px thumbnails of non-held-out reference photos


STREET_MIN_LEN = 3.0
PROBES = (2, 5, 9, 14, 20, 25)
_NOACC = ("private", "no")


def is_public(tags):
    """A walkable OSM way the public can use (not a gated court / private path)."""
    if tags.get("foot") in _NOACC:
        return False
    return not (tags.get("access") in _NOACC and tags.get("foot") not in ("yes", "designated", "permissive"))


def public_walk_tree(ways, tg=None):
    """cKDTree of the osm_targets walk samples on public ways (BNG metres)."""
    if tg is None:
        tg = json.load(open(os.path.join(ROOT, "data/derived/osm_targets.json")))
    pts = [(s[0], s[1]) for s in tg["walk"]["samples"] if is_public(ways.get(int(s[2]), {}).get("tags", {}))]
    return cKDTree(np.array(pts))


def faces_street(m, nrm, L, g, geoms, tree, pub):
    """Street-facing test (module docstring): wall midpoint m, unit outward normal nrm (BNG), length L, own footprint g,
    all footprints geoms with their STRtree, public walk sample tree pub."""
    if L < STREET_MIN_LEN:
        return False
    m, nrm = np.asarray(m, float), np.asarray(nrm, float)
    for s in PROBES:
        seg = LineString([m + nrm * 0.3, m + nrm * s])
        if any(geoms[i] is not g and geoms[i].intersects(seg) for i in tree.query(seg)):
            return False
        if pub.query(m + nrm * s)[0] < 3:
            return True
    return False


def street_facing_ids(walls):
    """ids of the walls (zone/ring walls.json rows: osm_id, p0/p1 in the collision frame, length) that pass faces_street."""
    nodes, ways, rels, _ = B.load_osm()
    geoms, own = [], {}
    for w in ways.values():
        if "building" in w.get("tags", {}):
            g = B.way_area(w, nodes)
            if g is not None and not g.is_empty:
                for p in B.polys_of(g):
                    geoms.append(p); own.setdefault("way/%d" % w["id"], []).append(p)
    for r in rels:
        if "building" in r.get("tags", {}):
            try:
                g = B.rel_area(r, ways, nodes)
            except Exception:
                g = None
            if g is not None and not g.is_empty:
                for p in B.polys_of(g):
                    geoms.append(p); own.setdefault("relation/%d" % r["id"], []).append(p)
    tree = STRtree(geoms)
    pub = public_walk_tree(ways)
    out = set()
    for w in walls:
        p0 = np.add(w["p0"], [B.E0, B.N0]); p1 = np.add(w["p1"], [B.E0, B.N0])
        d = (p1 - p0) / w["length"]; nrm = np.array([d[1], -d[0]]); m = (p0 + p1) / 2
        cands = own.get(w["osm_id"], [])
        g = min(cands, key=lambda p: p.exterior.distance(Point(*m))) if cands else None
        if faces_street(m, nrm, w["length"], g, geoms, tree, pub):
            out.add(w["id"])
    return out


def heldout():
    imgs, near = set(), []
    for f in ("heldout.json", "heldout_ms.json"):
        h = json.load(open(os.path.join(ROOT, "data/benchmark", f)))
        imgs |= set(h["images"]); near += h["sequence_near"]
    return imgs, near


def main():
    tf = Transformer.from_crs(4326, 27700, always_xy=True)
    cx, cy = tf.transform(*CENTRE)
    nodes, ways, rels, _ = B.load_osm()
    blds = []
    for w in ways.values():
        t = w.get("tags", {})
        if "building" in t:
            g = B.way_area(w, nodes)
            if g is not None and g.geom_type == "Polygon" and g.distance(Point(cx, cy)) < R + 30:
                blds.append(("way/%d" % w["id"], t, g))
    allb = [g for _, _, g in blds]
    tree = STRtree(allb)
    tg = json.load(open(os.path.join(ROOT, "data/derived/osm_targets.json")))
    wt = cKDTree(np.array([[s[0], s[1]] for s in tg["walk"]["samples"]]))
    dtm = rasterio.open(os.path.join(ROOT, "data/lidar/dtm_1m.tif")); dsm = rasterio.open(os.path.join(ROOT, "data/lidar/dsm_1m.tif"))
    samp = lambda r, pts: np.array([v[0] for v in r.sample(pts)])
    held, near = heldout()
    cached = {f[:-4] for f in os.listdir(os.path.join(ROOT, "data/raw/mapillary_facade")) if f.endswith(".jpg")}
    cams = []
    for im in json.load(open(os.path.join(ROOT, "data/raw/mapillary_list.json"))):
        if im["id"] in held or not im.get("computed_geometry") or im.get("is_pano"):
            continue
        e, n = tf.transform(*im["computed_geometry"]["coordinates"])
        if math.hypot(e - cx, n - cy) > R + 60:
            continue
        if any(s == im.get("sequence") and math.hypot(e - se, n - sn) < r for s, se, sn, r in near):
            continue
        hd, _ = MB.pose(im)
        cams.append((im["id"], e, n, hd - 1.7))   # grid convergence ~1.7 deg
    walls = []
    for oid, t, g in blds:
        ring = list(g.exterior.coords)
        if not g.exterior.is_ccw:
            ring = ring[::-1]   # CCW: outside is on the right of each edge p0 -> p1
        for k in range(len(ring) - 1):
            a, b = np.array(ring[k]), np.array(ring[k + 1])
            L = float(np.linalg.norm(b - a))
            m = (a + b) / 2
            if L < 2 or math.hypot(m[0] - cx, m[1] - cy) > R:
                continue
            d = (b - a) / L
            nrm = np.array([d[1], -d[0]])
            ok = False
            for s in (2, 5, 9, 14, 20, 25):
                q = m + nrm * s
                seg = LineString([m + nrm * 0.3, q])
                if any(allb[i] is not g and allb[i].intersects(seg) for i in tree.query(seg)):
                    break
                if wt.query(q)[0] < 3:
                    ok = True; break
            if not ok:
                continue
            gz = float(samp(dtm, [tuple(m + nrm * 1.5)])[0])
            ins = [tuple(a + d * L * f - nrm * s) for f in (0.2, 0.4, 0.6, 0.8) for s in (1, 1.75, 2.5)]
            ez = float(np.median(samp(dsm, ins)))
            refs = []
            for cid, e, n, hd in cams:
                v = np.array([e, n]) - m
                dist = float(v @ nrm)
                if not (4 <= dist <= 35) or abs(float(v @ d)) > dist * 1.2 + L / 2:
                    continue
                look = np.array([math.sin(math.radians(hd)), math.cos(math.radians(hd))])
                to = -v / np.linalg.norm(v)
                if look @ to < 0.6:
                    continue
                refs.append((float(look @ to) - dist / 100, cid))
            refs = [c for _, c in sorted(refs, reverse=True)[:5]]
            walls.append(dict(id="%s:%d" % (oid, k), osm_id=oid, tags=t, length=round(L, 2),
                              p0=[round(a[0] - B.E0, 2), round(a[1] - B.N0, 2)], p1=[round(b[0] - B.E0, 2), round(b[1] - B.N0, 2)],
                              ground_z=round(gz, 2), eave_z=round(ez, 2), height=round(ez - gz, 2),
                              dist_centre=round(math.hypot(m[0] - cx, m[1] - cy), 1), refs=refs))
    need = sorted({c for w in walls for c in w["refs"]} - cached)
    os.makedirs(REF, exist_ok=True)
    tok = MB.token()
    for i, cid in enumerate(need):
        p = os.path.join(REF, cid + ".jpg")
        if os.path.exists(p):
            continue
        try:
            u = json.loads(MB.get("https://graph.mapillary.com/%s?fields=thumb_1024_url&access_token=%s" % (cid, tok)))["thumb_1024_url"]
            open(p, "wb").write(MB.get(u))
        except Exception as ex:
            print("ref", cid, ex, file=sys.stderr)
    for w in walls:
        w["ref_files"] = [os.path.relpath(os.path.join(REF if c in need else os.path.join(ROOT, "data/raw/mapillary_facade"), c + ".jpg"), ROOT)
                          for c in w["refs"]]
        w["ref_files"] = [f for f in w["ref_files"] if os.path.exists(os.path.join(ROOT, f))]
    json.dump({"centre": CENTRE, "radius": R, "walls": walls}, open(OUT, "w"), indent=1)
    print(json.dumps({"walls": len(walls), "with_refs": sum(1 for w in walls if w["ref_files"]), "ref_photos": len({f for w in walls for f in w["ref_files"]}),
                      "buildings": len({w["osm_id"] for w in walls}), "length_m": round(sum(w["length"] for w in walls))}))


if __name__ == "__main__":
    main()
