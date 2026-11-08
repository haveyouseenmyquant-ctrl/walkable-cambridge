"""Railings, fences, walls, gates and outdoor steps around Market Square / Great St Mary's / Senate House, from OSM.

    .venv/bin/python -I scripts/zone_props_barriers.py      # prints a summary (ways by type, length, triangles)

build() -> list of {"name", "tris" (k,3,3) collision-frame triangles (CCW seen from outside; every part is a closed
solid), "col", "mat"} -- merged into site/zone/market_square.glb by scripts/zone_build.py.

Evidence / rules:
- Ways from data/raw/osm/cambridge_overpass.json with barrier=fence|railing|wall|retaining_wall|gate or
  highway=steps whose nearest point is within 170 m of 52.2053N 0.1190E. Hedges are vegetation (skipped). Ways
  lying inside a building footprint (indoor stairs, escalators: conveying=*, indoor=yes, tunnel/layer<0) are
  skipped, and so is any short piece of a barrier that falls inside a footprint.
- barrier=fence/railing (fence_type unset, railing or metal; wall=metal): black painted cast-iron railings with
  spear finials on a low stone plinth, stone piers at run ends, sharp corners and gates. Senate House lawn
  (way/95404090) is tall iron on a 0.45 m plinth; Great St Mary's churchyard (way/134521036, 134521043, gate way
  1228735832) ~1.3 m on a 0.4 m plinth. Other fence_type values (wood, chain_link, ...) get plain panel fences.
  height=* overrides the overall height.
- barrier=wall/retaining_wall: stone (material=* respected: brick, flint, ...) with a coping. Height from height=*,
  else the LiDAR DSM-DTM median along the way when it reads 0.6-3.2 m, else 0.9 m where the DSM sees nothing
  (low walls, e.g. King's Parade), else 2.0 m.
- barrier=gate nodes on a way: a gap (width=*, else 1.4 m, 2.4 m for entrance=main) with an iron gate leaf
  (named college gates on walls are buildings / arches: gap only); barrier=gate ways: an iron leaf between piers.
- highway=steps: stone flight, step_count=* risers (else from the way length), 0.15 m risers, width=* else 2 m,
  climbing in the incline=* direction (else up the DTM); implausibly steep flights (interior stairs) are skipped.
- Ground: data/lidar/dtm_1m.tif via zone_props.Ground (3x3 median).
"""
import json
import math
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from zone_props import E0, N0, Ground  # noqa: E402

OSM = os.path.join(ROOT, "data/raw/osm/cambridge_overpass.json")
DTM = os.path.join(ROOT, "data/lidar/dtm_1m.tif")
DSM = os.path.join(ROOT, "data/lidar/dsm_1m.tif")
CENTRE = (0.1190, 52.2053)
R = 170.0

IRON = (0.055, 0.055, 0.06)
STONE = (0.74, 0.70, 0.60)
STONE_CAP = (0.66, 0.62, 0.54)
STEP = (0.70, 0.68, 0.63)
WALL_COLS = {"stone": STONE, "brick": (0.62, 0.36, 0.26), "flint": (0.45, 0.43, 0.40), "render": (0.85, 0.82, 0.74),
             "concrete": (0.68, 0.67, 0.64)}
TIMBER = (0.42, 0.33, 0.24)

BAR_PITCH = 0.13
BAR_R = 0.016
SPECIAL = {   # way id -> (railing height above plinth, plinth height)
    95404090: (1.55, 0.45),     # Senate House lawn
    134521036: (1.30, 0.40),    # Great St Mary's churchyard
    134521043: (1.30, 0.40),
    1228735832: (1.30, 0.40),
}
RAIL_H, PLINTH_H = 1.25, 0.35
PIECE = 2.5   # terrain-following piece length (m)


# ---------------------------------------------------------------- mesh
class Mesh:
    def __init__(self):
        self.t = {}   # (col, mat) -> list of tris

    def tri(self, a, b, c, col, mat, ctr):
        a, b, c = (np.asarray(x, float) for x in (a, b, c))
        n = np.cross(b - a, c - a)
        if np.dot(n, (a + b + c) / 3 - ctr) < 0:
            b, c = c, b
        self.t.setdefault((col, mat), []).append((a, b, c))

    def poly(self, pts, col, mat, ctr):
        for i in range(1, len(pts) - 1):
            self.tri(pts[0], pts[i], pts[i + 1], col, mat, ctr)

    def hexa(self, p, q, col, mat, top=None, bottom=False):
        """Convex hexahedron: bottom ring p[0..3], top ring q[0..3] (same order); faces oriented outward."""
        p, q = np.asarray(p, float), np.asarray(q, float)
        ctr = np.vstack([p, q]).mean(0)
        for i in range(4):
            j = (i + 1) % 4
            self.poly([p[i], p[j], q[j], q[i]], col, mat, ctr)
        self.poly(list(q), top or col, mat, ctr)
        if bottom:
            self.poly(list(p), col, mat, ctr)

    def prism3(self, x, y, z0, z1, r, col, mat, phase=0.0, tip=0.0):
        """Triangular bar with an optional pyramidal spear tip."""
        a = phase + np.arange(3) * 2 * np.pi / 3
        lo = [np.array([x + r * math.cos(t), y + r * math.sin(t), z0]) for t in a]
        hi = [v + [0, 0, z1 - z0] for v in lo]
        ctr = np.array([x, y, (z0 + z1) / 2])
        for i in range(3):
            j = (i + 1) % 3
            self.poly([lo[i], lo[j], hi[j], hi[i]], col, mat, ctr)
        if tip > 0:
            ap = np.array([x, y, z1 + tip])
            c2 = np.array([x, y, z1])
            hi2 = [np.array([x + 1.6 * r * math.cos(t), y + 1.6 * r * math.sin(t), z1]) for t in a]
            for i in range(3):
                self.tri(hi2[i], hi2[(i + 1) % 3], ap, col, mat, c2 - [0, 0, 0.01])

    def out(self, name):
        res = []
        for k, ((col, mat), T) in enumerate(sorted(self.t.items(), key=lambda kv: kv[0][1])):
            res.append({"name": "%s:%d" % (name, k), "tris": np.asarray(T, np.float32).reshape(-1, 3, 3),
                        "col": np.asarray(col, np.float32), "mat": mat})
        return res


def slab(m, a, b, za, zb, base, w, col, mat, top=None, off=0.0):
    """Terrain-following box along a->b (2D), half-width w, bottom at `base`, top at za/zb (+off sideways)."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    d = b - a
    L = np.linalg.norm(d)
    if L < 1e-3:
        return
    n = np.array([-d[1], d[0]]) / L * w
    P = [a + n, b + n, b - n, a - n]
    zt = [za, zb, zb, za]
    zbase = base if np.ndim(base) else [base] * 4
    m.hexa([[*P[i], zbase[i]] for i in range(4)], [[*P[i], zt[i]] for i in range(4)], col, mat, top=top)


def pier(m, c, d, z, h, s=0.24, col=STONE, cap=STONE_CAP):
    d = np.asarray(d, float) / max(np.linalg.norm(d), 1e-9)
    n = np.array([-d[1], d[0]])
    c = np.asarray(c, float)
    ring = lambda r: [c + (d * sx + n * sy) * r for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]  # noqa: E731
    m.hexa([[*p, z - 0.2] for p in ring(s)], [[*p, z + h] for p in ring(s)], col, "stone")
    m.hexa([[*p, z + h] for p in ring(s + 0.04)], [[*p, z + h + 0.08] for p in ring(s + 0.04)], cap, "stone")
    m.hexa([[*p, z + h + 0.08] for p in ring(s + 0.04)], [[*p, z + h + 0.2] for p in ring(0.03)], cap, "stone")


# ---------------------------------------------------------------- polyline helpers
def cut(pts, s0, s1):
    """Sub-polyline of pts between arc lengths s0 < s1."""
    pts = np.asarray(pts, float)
    seg = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    cs = np.concatenate([[0], np.cumsum(seg)])

    def at(s):
        i = min(max(int(np.searchsorted(cs, s) - 1), 0), len(seg) - 1)
        t = (s - cs[i]) / max(seg[i], 1e-9)
        return pts[i] + (pts[i + 1] - pts[i]) * t
    out = [at(s0)] + [pts[i] for i in range(len(pts)) if s0 < cs[i] < s1] + [at(s1)]
    return np.array(out)


def pieces(pts, step=PIECE):
    """Split a polyline into straight pieces <= step long."""
    for a, b in zip(pts[:-1], pts[1:]):
        L = np.linalg.norm(b - a)
        k = max(1, int(math.ceil(L / step)))
        for i in range(k):
            yield a + (b - a) * i / k, a + (b - a) * (i + 1) / k


# ---------------------------------------------------------------- barrier types
def railing_run(m, g, pts, H, P, inside, gate=False):
    """Iron railing (bars + rails + spears) on a stone plinth of height P (0 = none) along pts."""
    tot = 0.0
    for a, b in pieces(pts):
        if inside((a + b) / 2):
            continue
        za, zb = g(*a), g(*b)
        L = np.linalg.norm(b - a)
        tot += L
        d = (b - a) / L
        if P > 0:
            slab(m, a, b, za + P, zb + P, min(za, zb) - 0.25, 0.17, STONE, "stone", top=STONE_CAP)
        zb0 = 0.08 if gate else P
        r0, r1 = (za + zb0 + 0.10, zb + zb0 + 0.10), (za + P + H - 0.10, zb + P + H - 0.10)
        for zz in (r0, r1) + (((za + zb0 + H * 0.5), (zb + zb0 + H * 0.5)),) * gate:
            slab(m, a, b, zz[0] + 0.035, zz[1] + 0.035, [zz[0], zz[1], zz[1], zz[0]], 0.02, IRON, "plain")
        nb = max(1, int(round(L / BAR_PITCH)))
        ph = math.atan2(d[1], d[0])
        for i in range(nb):
            t = (i + 0.5) / nb
            x, y = a + (b - a) * t
            z = za + (zb - za) * t
            m.prism3(x, y, z + zb0, z + P + H, BAR_R, IRON, "plain", phase=ph, tip=0.11)
    return tot


def panel_run(m, g, pts, H, inside, col=TIMBER):
    tot = 0.0
    for a, b in pieces(pts):
        if inside((a + b) / 2):
            continue
        za, zb = g(*a), g(*b)
        tot += np.linalg.norm(b - a)
        slab(m, a, b, za + H, zb + H, min(za, zb) - 0.1, 0.03, col, "timber")
    return tot


def wall_run(m, g, pts, H, T, col, mat, inside):
    tot = 0.0
    for a, b in pieces(pts):
        if inside((a + b) / 2):
            continue
        za, zb = g(*a), g(*b)
        tot += np.linalg.norm(b - a)
        slab(m, a, b, za + H, zb + H, min(za, zb) - 0.3, T / 2, col, mat)
        slab(m, a, b, za + H + 0.1, zb + H + 0.1, [za + H, zb + H, zb + H, za + H], T / 2 + 0.04,
             STONE_CAP, "stone")
    return tot


def steps(m, g, pts, n, width, up):
    """Stone flight along pts (straight from first to last point), n risers of 0.15 m."""
    a, b = np.asarray(pts[0], float), np.asarray(pts[-1], float)
    if not up:
        a, b = b, a
    L = np.linalg.norm(b - a)
    d = (b - a) / L
    nr = np.array([-d[1], d[0]]) * width / 2
    z0 = g(*a)
    rise = max(0.15, min(0.18, (g(*b) - z0) / n if n else 0.15))
    tread = L / n
    for i in range(n):
        p0, p1 = a + d * tread * i, a + d * tread * (i + 1)
        zt = z0 + rise * (i + 1)
        P = [p0 - nr, p1 - nr, p1 + nr, p0 + nr]
        m.hexa([[*p, z0 - 0.3] for p in P], [[*p, zt] for p in P], STEP, "stone")
    return L


# ---------------------------------------------------------------- main
def num(v, default):
    try:
        return float(str(v).split()[0].replace("m", ""))
    except (TypeError, ValueError, IndexError):
        return default


def build(verbose=False):
    import rasterio
    from pyproj import Transformer
    from shapely import STRtree
    from shapely.geometry import LineString, Point, Polygon

    els = json.load(open(OSM))["elements"]
    tf = Transformer.from_crs(4326, 27700, always_xy=True)
    nd = {e["id"]: e for e in els if e["type"] == "node"}
    ids = list(nd)
    E, N = tf.transform(np.array([nd[i]["lon"] for i in ids]), np.array([nd[i]["lat"] for i in ids]))
    xy = dict(zip(ids, zip(E - E0, N - N0)))
    cx, cy = tf.transform(*CENTRE)
    C = Point(cx - E0, cy - N0)
    ways = [e for e in els if e["type"] == "way"]

    blds = []
    for w in ways:
        if "building" in w.get("tags", {}) and len(w["nodes"]) >= 4 and w["nodes"][0] == w["nodes"][-1]:
            c = [xy[i] for i in w["nodes"] if i in xy]
            if len(c) >= 4:
                p = Polygon(c)
                p = p if p.is_valid else p.buffer(0)
                if p.distance(C) < R + 100:
                    blds.append(p.buffer(-0.3))
    tree = STRtree(blds)

    def inside(p):
        q = Point(*p)
        return any(blds[i].contains(q) for i in tree.query(q))

    g = Ground()
    dtm, dsm = rasterio.open(DTM), rasterio.open(DSM)

    def lidar_h(line):
        P = [(line.interpolate(s).x + E0, line.interpolate(s).y + N0) for s in np.arange(0, line.length, 0.5)]
        a = np.array([v[0] for v in dtm.sample(P)])
        b = np.array([v[0] for v in dsm.sample(P)])
        return float(np.median(b - a)), float(np.percentile(b - a, 80))

    out, summary = [], {}
    for w in ways:
        t = w.get("tags", {})
        bar, hw = t.get("barrier"), t.get("highway")
        if bar not in ("fence", "railing", "wall", "retaining_wall", "gate") and hw != "steps":
            continue
        if any(k in t for k in ("conveying", "tunnel")) or t.get("indoor") == "yes" or num(t.get("layer"), 0) < 0:
            continue
        pts = np.array([xy[i] for i in w["nodes"] if i in xy])
        if len(pts) < 2:
            continue
        line = LineString(pts)
        if line.length < 0.3 or line.distance(C) > R:
            continue
        samples = [line.interpolate(s) for s in np.arange(0, line.length, 0.5)] + [Point(*pts[-1])]
        if np.mean([inside((p.x, p.y)) for p in samples]) > 0.5:
            continue
        m = Mesh()
        name = "barrier:way/%d" % w["id"]
        kind, length = None, 0.0

        if hw == "steps":
            n = int(num(t.get("step_count"), 0)) or max(2, min(int(round(line.length / 0.3)),
                                                              int(round(abs(g(*pts[-1]) - g(*pts[0])) / 0.15))))
            if line.length < 1.0 or n * 0.26 > line.length + 0.6:   # door steps / interior stairs
                continue
            up = t.get("incline") == "up" or (t.get("incline") != "down" and g(*pts[-1]) >= g(*pts[0]))
            length = steps(m, g, pts, n, num(t.get("width"), 2.0), up)
            kind = "steps"
        else:
            # gates on the way -> gaps
            gates = []
            cs = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))])
            for k, i in enumerate(w["nodes"]):
                nt = nd.get(i, {}).get("tags", {})
                if nt.get("barrier") == "gate" and bar != "gate":
                    gw = num(nt.get("width"), 2.4 if nt.get("entrance") == "main" else 1.4)
                    gates.append((cs[k], gw, "name" in nt and bar in ("wall", "retaining_wall")))
            spans, s = [], 0.0
            for sg, gw, _ in sorted(gates):
                if sg - gw / 2 > s + 0.05:
                    spans.append((s, sg - gw / 2))
                s = max(s, sg + gw / 2)
            if line.length > s + 0.05:
                spans.append((s, line.length))
            metal = (t.get("fence_type") in (None, "railing", "metal", "metal_bars", "bars")
                     or t.get("wall") == "metal" or t.get("material") in ("metal", "iron", "steel"))
            H, P = SPECIAL.get(w["id"], (RAIL_H, PLINTH_H))
            if "height" in t:
                H = max(0.5, num(t["height"], H + P) - P)
            if bar in ("fence", "railing", "gate"):
                if bar == "gate":
                    length = railing_run(m, g, pts, H, P, inside, gate=True)
                    kind = "gate"
                elif metal:
                    kind = "railing"
                    for s0, s1 in spans:
                        length += railing_run(m, g, cut(pts, s0, s1), H, P, inside)
                else:
                    kind = "fence"
                    for s0, s1 in spans:
                        length += panel_run(m, g, cut(pts, s0, s1), num(t.get("height"), 1.5), inside)
                top = P + H
            else:
                kind = "wall"
                if "height" in t:
                    WH = num(t["height"], 2.0)
                else:
                    h50, h80 = lidar_h(line)
                    WH = h50 if 0.6 < h50 <= 3.2 else (0.9 if h80 < 0.4 else 2.0)
                mat = (t.get("material") or "stone").lower()
                col = WALL_COLS.get(mat, STONE)
                mat = mat if mat in ("brick", "stone", "flint", "render") else "stone"
                T = num(t.get("width"), 0.45 if WH < 1.5 else 0.5)
                for s0, s1 in spans:
                    length += wall_run(m, g, cut(pts, s0, s1), WH, T, col, mat, inside)
                top = WH + 0.1
            # gate leaves in the gaps
            for sg, gw, named in gates:
                if named:
                    continue
                gp = cut(pts, max(sg - gw / 2 + 0.25, 0), min(sg + gw / 2 - 0.25, line.length))
                if len(gp) >= 2 and np.linalg.norm(gp[-1] - gp[0]) > 0.3:
                    railing_run(m, g, gp, top - 0.08 if kind == "wall" else P + H - 0.1, 0.0, inside, gate=True)
            # piers: run ends + sharp corners (railings, gates); wall ends get none
            if kind in ("railing", "gate"):
                pp = []
                if kind == "gate":
                    pp = [(pts[0], pts[1] - pts[0]), (pts[-1], pts[-1] - pts[-2])]
                for s0, s1 in spans if kind == "railing" else []:
                    sp = cut(pts, s0, s1)
                    pp += [(sp[0], sp[1] - sp[0]), (sp[-1], sp[-1] - sp[-2])]
                    for i in range(1, len(sp) - 1):
                        u, v = sp[i] - sp[i - 1], sp[i + 1] - sp[i]
                        cosang = np.dot(u, v) / max(np.linalg.norm(u) * np.linalg.norm(v), 1e-9)
                        if cosang < math.cos(math.radians(35)):
                            pp.append((sp[i], u + v))
                seen = []
                for c, d in pp:
                    if inside(c) or any(np.linalg.norm(c - q) < 0.4 for q in seen):
                        continue
                    seen.append(c)
                    pier(m, c, d, g(*c), P + H + 0.05)
        if kind is None or not m.t:
            continue
        out += m.out(name)
        s = summary.setdefault(kind, [0, 0.0, 0])
        s[0] += 1
        s[1] += length
        s[2] += sum(len(v) for v in m.t.values())
        if verbose:
            zz = np.concatenate([np.asarray(v)[..., 2].ravel() for v in m.t.values()])
            print("  way/%d %-8s L=%6.1f m  tris=%6d  z %.2f..%.2f  start (%.1f, %.1f)" % (
                w["id"], kind, length, sum(len(v) for v in m.t.values()), zz.min(), zz.max(), *pts[0]))
    if verbose:
        for k, (n, L, tr) in sorted(summary.items()):
            print("%-8s ways=%3d  length=%7.1f m  tris=%6d" % (k, n, L, tr))
        print("total tris:", sum(len(p["tris"]) for p in out))
    return out


if __name__ == "__main__":
    build(verbose=True)
