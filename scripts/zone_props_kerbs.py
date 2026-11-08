"""Granite kerbs (session 37): kerb lines along the carriageway edges around Market Square and in ring 1.

    .venv/bin/python -I scripts/zone_props_kerbs.py      # prints a summary (length raised / low / flush, triangles)

build() -> list of {"name", "tris" (k,3,3) collision-frame triangles, "col", "mat"} -- merged into
site/zone/market_square.glb by scripts/zone_build.py (render only: collision and walkability are untouched; the
kerb is 0.12 m, a walkable step).

Rules / evidence:
- Area: within 90 m of 52.2053N 0.1190E (the square) or 300 m of Great St Mary's (52.2052N 0.1183E).
- Carriageways: OSM highway=primary..residential/living_street ways, and the highway=pedestrian ways that really have
  a kerbed carriageway in the centre (KERBED_PED: Trinity St, Sidney St, Market St, Market Hill road, St Mary's St,
  Peas Hill, St Andrew's St, Green St), buffered by build.road_half (the ground builder's width); Market Street by
  the half width of its brick carriageway in data/annotations/ground/surfaces.json (2.3 m). The kerb line is the
  outline of their union, minus: parts inside other walkable ways that join (pedestrian streets, service lanes,
  footways) -- these are flush; parts against a building (footprint + 0.3 m) or where the ground on the outside is
  another carriageway / under a building (collision surface 1, 0, 9).
- Profile: pale grey granite 0.30 m wide, 0.12 m upstand, small arris; the carriageway face is visible, the back
  steps down to the pavement over a 0.45 m pavement-coloured wedge (the ground mesh is one surface, so the kerb
  cannot sit in a raised footway). A 0.25 m channel of darker setts on the carriageway side.
- Dropped / flush (0.015 m granite band, no wedge): within reach of OSM highway=crossing nodes and footway=crossing
  ways, kerb=lowered|flush|no nodes, joining walkable ways, and where the outside is the Market Square setts
  (collision surface 5); low (0.04 m) where the carriageway itself is setts (King's Parade east strip, Senate House
  Hill, sett lanes).
- Heights: the rendered ground (the 2 m collision ground grid of site/collision, triangle-exact), so kerbs sit on
  the visible ground. Run after build.py.
"""
import json
import math
import os
import struct
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from zone_props import E0, N0  # noqa: E402

SQ = (-102.91, 57.36)        # 52.2053N 0.1190E, collision frame
GSM = (-150.41, 44.84)       # Great St Mary's
R_SQ, R_GSM = 90.0, 300.0

KERB_W, UP, LOW, FLUSH = 0.30, 0.12, 0.04, 0.015
CHAN_W, WEDGE_W = 0.25, 0.45
PIECE = 1.5
ROADS = {"primary", "secondary", "tertiary", "unclassified", "residential", "living_street"}
KERBED_PED = {"Trinity Street", "Sidney Street", "Market Street", "Market Hill", "St Mary's Street", "Peas Hill",
              "Saint Andrew's Street", "Green Street"}
HALF_OVR = {169385438: 2.3}   # Market Street: brick carriageway (surfaces.json market_street_brick)
GRANITE = (0.60, 0.60, 0.59)
GRANITE_TOP = (0.66, 0.66, 0.64)
CHANNEL = (0.30, 0.30, 0.31)
PAVE = (0.58, 0.56, 0.52)

GSTEP, EXT, TILE = 2.0, 1000.0, 250.0
NG = int(TILE / GSTEP)   # 125 cells per tile side


class GroundCol:
    """Rendered ground from site/collision: the first (NG+1)^2 vertices of each tile are the 2 m grid, the first
    2*NG^2 triangles the ground (abc then acd halves of each cell)."""

    def __init__(self):
        self.t = {}

    def _tile(self, tx, ty):
        k = (tx, ty)
        if k not in self.t:
            f = open(os.path.join(ROOT, "site/collision/t_%d_%d.col" % (tx, ty)), "rb").read()
            nv, nt = struct.unpack("<II", f[8:16])
            V = np.frombuffer(f, "<f4", nv * 3, 16).reshape(-1, 3)
            o = 16 + nv * 12 + nt * 12
            S = np.frombuffer(f, "u1", nt, o + nt)
            self.t[k] = (V[:(NG + 1) ** 2, 2].reshape(NG + 1, NG + 1).astype(float), S[:2 * NG * NG].copy())
        return self.t[k]

    def at(self, x, y):
        """(z, surface) at a collision-frame point."""
        tx, ty = int((x + EXT) // TILE), int((y + EXT) // TILE)
        Z, S = self._tile(tx, ty)
        lx, ly = (x + EXT - tx * TILE) / GSTEP, (y + EXT - ty * TILE) / GSTEP
        c, r = min(int(lx), NG - 1), min(int(ly), NG - 1)
        fx, fy = lx - c, ly - r
        za, zb, zc, zd = Z[r, c], Z[r, c + 1], Z[r + 1, c + 1], Z[r + 1, c]
        if fx >= fy:
            return za + fx * (zb - za) + fy * (zc - zb), int(S[r * NG + c])
        return za + fy * (zd - za) + fx * (zc - zd), int(S[NG * NG + r * NG + c])


def in_area(x, y):
    return math.hypot(x - SQ[0], y - SQ[1]) < R_SQ or math.hypot(x - GSM[0], y - GSM[1]) < R_GSM


class Out:
    def __init__(self):
        self.t = {}   # (cell, mat) -> ([tris], [cols])

    def quad(self, a, b, c, d, col, mat, up):
        """Quad a-b-c-d, wound so its normal agrees with `up` (a direction)."""
        a, b, c, d = (np.asarray(v, float) for v in (a, b, c, d))
        n = np.cross(b - a, c - a) + np.cross(c - a, d - a)
        if np.dot(n, up) < 0:
            a, b, c, d = d, c, b, a
        key = (int((a[0] + EXT) // 200), int((a[1] + EXT) // 200), mat)
        T, C = self.t.setdefault(key, ([], []))
        T += [(a, b, c), (a, c, d)]
        C += [col, col]

    def items(self):
        res = []
        for (cx, cy, mat), (T, C) in sorted(self.t.items()):
            res.append({"name": "kerb:%d_%d:%s" % (cx, cy, mat), "tris": np.asarray(T, np.float32),
                        "col": np.asarray(C, np.float32), "mat": mat})
        return res


def build(verbose=False):
    import build as B
    from shapely.geometry import LineString, Point
    from shapely.ops import unary_union

    nodes, ways, _, pnodes = B.load_osm()
    off = np.array([E0, N0])
    sq, gsm = Point(SQ[0] + E0, SQ[1] + N0), Point(GSM[0] + E0, GSM[1] + N0)
    zone = unary_union([sq.buffer(R_SQ + 20), gsm.buffer(R_GSM + 20)])

    kerbed, joins, xways, bld, setts = [], [], [], [], []
    for w in ways.values():
        t = w.get("tags", {})
        if not t:
            continue
        hw = t.get("highway")
        if "building" in t and t["building"] not in ("no", "roof"):
            g = B.way_area(w, nodes)
            if g is not None and g.intersects(zone):
                bld.append(g)
            continue
        if not hw:
            continue
        c = B.coords(w, nodes)
        if not c or len(c) < 2:
            continue
        ln = LineString(c)
        if not ln.intersects(zone) or t.get("tunnel", "no") != "no":
            continue
        if t.get("footway") == "crossing" or t.get("crossing"):
            xways.append(ln)
            continue
        if t.get("area") == "yes":
            continue
        is_carr = hw in ROADS or (hw == "pedestrian" and t.get("name") in KERBED_PED)
        if is_carr:
            hh = HALF_OVR.get(w["id"], B.road_half(t))
            g = ln.buffer(hh)
            kerbed.append(g)
            if B.road_class(t) == B.S_COURT:
                setts.append(g)
        elif hw in ("pedestrian", "service", "living_street", "residential", "unclassified", "track"):
            hh = B.road_half(t) if hw in B.ROAD_HALF else 1.0
            joins.append(ln.buffer(hh))
    xnodes, flushn = [], []
    for n in pnodes:
        t = n["tags"]
        if n["id"] not in nodes:
            continue
        p = Point(nodes[n["id"]])
        if not p.intersects(zone):
            continue
        if t.get("highway") == "crossing" or t.get("railway") == "crossing":
            xnodes.append(p)
        if t.get("kerb") in ("lowered", "flush", "no") or t.get("barrier") == "kerb" and t.get("kerb") != "raised":
            flushn.append(p)
    U = unary_union(kerbed)
    J = unary_union(joins).difference(U.buffer(-0.01)) if joins else None
    BL = unary_union(bld).buffer(0.3) if bld else None
    ST = unary_union(setts) if setts else None
    drop = [ln.buffer(1.8) for ln in xways] + [p.buffer(1.5) for p in flushn]
    # a crossing node on a road's centreline drops both kerbs: reach the edge (road half + 1.5 m)
    drop += [p.buffer(B.road_half({"highway": "residential"}) + 2.0) for p in xnodes if U.contains(p)]
    DROP = unary_union(drop) if drop else None
    from shapely.prepared import prep
    Up = prep(U)
    J, BL, ST, DROP = (prep(g) if g is not None else None for g in (J, BL, ST, DROP))

    G = GroundCol()
    out = Out()
    stats = {"raised_m": 0.0, "low_m": 0.0, "flush_m": 0.0}
    edges = [U.exterior] if U.geom_type == "Polygon" else [g.exterior for g in U.geoms]
    edges += [r for g in ([U] if U.geom_type == "Polygon" else U.geoms) for r in g.interiors]
    for ring in edges:
        L = ring.length
        n = max(2, int(math.ceil(L / PIECE)))
        S = np.linspace(0, L, n + 1)
        P = np.array([ring.interpolate(s).coords[0] for s in S])
        # classify each piece by its midpoint
        kinds = []
        for i in range(n):
            a, b = P[i], P[i + 1]
            m = (a + b) / 2
            d = b - a
            ln_ = np.linalg.norm(d)
            if ln_ < 1e-6:
                kinds.append(None)
                continue
            nrm = np.array([-d[1], d[0]]) / ln_
            if Up.contains(Point(*(m + nrm * 0.2))):
                nrm = -nrm
            x, y = m - off
            k = None
            if in_area(x, y):
                po, pi = Point(*(m + nrm * 0.6)), Point(*(m - nrm * 0.6))
                so = G.at(*(m + nrm * 0.9 - off))[1]
                if BL is not None and BL.contains(po):
                    k = None
                elif so in (0, 1, 4, 9):
                    k = None
                elif J is not None and J.contains(po):
                    k = "flush"
                elif DROP is not None and DROP.contains(Point(*m)):
                    k = "flush"
                elif so == 5:
                    k = "flush"
                elif ST is not None and ST.contains(pi):
                    k = "low"
                else:
                    k = "up"
            kinds.append((k, nrm) if k else None)
        for i in range(n):
            if kinds[i] is None:
                continue
            k, nrm = kinds[i]
            a, b = P[i] - off, P[i + 1] - off
            # vertex normals averaged with neighbours of the same run (mitred joins)
            na = nrm if i == 0 or kinds[i - 1] is None else kinds[i - 1][1] + nrm
            nb = nrm if i == n - 1 or kinds[i + 1] is None else kinds[i + 1][1] + nrm
            na, nb = na / np.linalg.norm(na), nb / np.linalg.norm(nb)
            h = {"up": UP, "low": LOW, "flush": FLUSH}[k]
            stats[{"up": "raised_m", "low": "low_m", "flush": "flush_m"}[k]] += float(np.linalg.norm(b - a))

            def pt(p, nv, o, dz):
                q = p + nv * o
                return np.array([q[0], q[1], G.at(*q)[0] + dz])

            def h_of(j):
                if j < 0 or j >= n or kinds[j] is None:
                    return None
                return {"up": UP, "low": LOW, "flush": FLUSH}[kinds[j][0]]
            # ramp the upstand down over the piece next to a flush/low neighbour (dropped kerb transition)
            ha = h if h_of(i - 1) is None else min(h, max(h_of(i - 1), h))
            hb = h if h_of(i + 1) is None else min(h, max(h_of(i + 1), h))
            if h_of(i - 1) is not None and h_of(i - 1) < h:
                ha = h_of(i - 1)
            if h_of(i + 1) is not None and h_of(i + 1) < h:
                hb = h_of(i + 1)
            Z = np.array([0, 0, 1.0])
            # channel (darker setts) on the carriageway side
            out.quad(pt(a, na, -CHAN_W, 0.012), pt(b, nb, -CHAN_W, 0.012), pt(b, nb, 0, 0.012), pt(a, na, 0, 0.012),
                     CHANNEL, "stone", Z)
            if max(ha, hb) <= FLUSH + 1e-6:
                out.quad(pt(a, na, 0, FLUSH), pt(b, nb, 0, FLUSH), pt(b, nb, KERB_W, FLUSH), pt(a, na, KERB_W, FLUSH),
                         GRANITE_TOP, "stone", Z)
                continue
            ar = 0.02   # arris
            fa, fb = -np.append(na, 0), -np.append(nb, 0)
            out.quad(pt(a, na, 0, -0.04), pt(b, nb, 0, -0.04), pt(b, nb, 0, hb - ar), pt(a, na, 0, ha - ar),
                     GRANITE, "stone", fa)
            out.quad(pt(a, na, 0, ha - ar), pt(b, nb, 0, hb - ar), pt(b, nb, ar, hb), pt(a, na, ar, ha),
                     GRANITE_TOP, "stone", fa + Z)
            out.quad(pt(a, na, ar, ha), pt(b, nb, ar, hb), pt(b, nb, KERB_W, hb), pt(a, na, KERB_W, ha),
                     GRANITE_TOP, "stone", Z)
            out.quad(pt(a, na, KERB_W, ha), pt(b, nb, KERB_W, hb), pt(b, nb, KERB_W + WEDGE_W, 0.004),
                     pt(a, na, KERB_W + WEDGE_W, 0.004), PAVE, "plain", Z)
            # end caps where the run stops (next to a gap)
            for j, p, nv, hh, sgn in ((i - 1, a, na, ha, -1), (i + 1, b, nb, hb, 1)):
                if h_of(j) is None:
                    d3 = np.append((b - a) * sgn, 0)
                    out.quad(pt(p, nv, 0, -0.04), pt(p, nv, KERB_W, -0.04), pt(p, nv, KERB_W, hh), pt(p, nv, 0, hh),
                             GRANITE, "stone", d3)
    res = out.items()
    if verbose:
        ntri = sum(len(r["tris"]) for r in res)
        print({k: round(v) for k, v in stats.items()}, "nodes", len(res), "tris", ntri)
    return res


if __name__ == "__main__":
    build(verbose=True)
