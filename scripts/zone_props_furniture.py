"""Street furniture in the Market Square zone as real geometry, at the mapped OSM node positions.

    .venv/bin/python -I scripts/zone_props_furniture.py      # prints a summary (objects by kind, triangles)

build() -> list of {"name", "tris" (k,3,3) collision-frame triangles, "col", "mat"} -- merged into
site/zone/market_square.glb by scripts/zone_build.py (loads every scripts/zone_props*.py).

Which objects: the OSM nodes scripts/street_objects.py classifies as street_lamp (1), bench (2), bollard (3),
waste_basket (4), bicycle_parking (5), post_box (6), telephone (7), whose position lies within ZONE_R of ZONE_C
(52.2053N 0.1190E, collision frame). site/app/objects.js skips its generic instanced versions of those types inside
the same circle (keep the two constants in sync), so nothing is drawn twice. The street_objects_pct KPI (kpi.py)
reads the per-tile objects/*.bin records, which are unchanged; the objects are still drawn at those positions.

Models (heading = direction of the nearest highway way, like street_objects.py; `direction=*` overrides):
- post_box: Royal Mail pillar box (type B/C), red, black plinth, flared cap and domed top, black aperture
  (two for post_box:apertures=2), white collection plate.
- telephone: K6 kiosk (Giles Gilbert Scott, 1935): 0.91 m square, 2.42 m, red, glazed on all four sides with
  8 x 3 panes (glazing bars as geometry), cream TELEPHONE fascia under a domed roof.
- bench: cast-iron ends with timber seat (+ backrest unless backrest=no).
- waste_basket: black Cambridge City Council litter bin with gold band and domed hood.
- bicycle_parking: black Sheffield stands 1 m apart along the way (n = capacity / 2, 1..12, as in
  street_objects.py), about half the stand sides with a parked bike.
- bollard: barrier=bollard black cast-iron post with a cap (bollard=rising: steel with red reflective band).
- street_lamp: black heritage column with a lantern (no lamp nodes are currently mapped inside the zone).
Ground: zone_props.Ground (DTM 3x3 median).
"""
import math
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from zone_props import E0, N0, Ground  # noqa: E402

ZONE_C = (-96.8, 57.0)   # collision frame (52.2053N 0.1190E); also in site/app/objects.js ZONE_SKIP
ZONE_R = 140.0
KINDS = {1, 2, 3, 4, 5, 6, 7}

RED = (0.66, 0.05, 0.06)
RED_K6 = (0.70, 0.07, 0.07)
BLACK = (0.045, 0.045, 0.05)
IRON = (0.06, 0.06, 0.065)
STEEL = (0.62, 0.64, 0.66)
GOLD = (0.72, 0.56, 0.20)
WHITE = (0.90, 0.90, 0.86)
CREAM = (0.93, 0.91, 0.82)
GLASS = (0.16, 0.20, 0.22)
WOOD = (0.50, 0.36, 0.22)
TYRE = (0.05, 0.05, 0.05)
FRAMES = [(0.15, 0.22, 0.38), (0.45, 0.10, 0.12), (0.16, 0.30, 0.20), (0.08, 0.08, 0.09), (0.60, 0.60, 0.58),
          (0.80, 0.78, 0.72), (0.30, 0.45, 0.60)]


class Mesh:
    """Triangles grouped by (colour, material). Parts are placed in a local frame (u along the way, v across,
    z up) at origin p0 with heading h."""

    def __init__(self):
        self.t = {}

    def frame(self, x, y, z, h):
        self.o = np.array([x, y, z], float)
        self.U = np.array([math.cos(h), math.sin(h), 0.0])
        self.V = np.array([-math.sin(h), math.cos(h), 0.0])

    def w(self, p):
        return self.o + self.U * p[0] + self.V * p[1] + np.array([0, 0, p[2]])

    def tri(self, a, b, c, col, mat="plain"):
        self.t.setdefault((col, mat), []).append((a, b, c))

    def quad(self, a, b, c, d, col, mat="plain"):
        self.tri(a, b, c, col, mat)
        self.tri(a, c, d, col, mat)

    def box(self, c, s, col, top=None, mat="plain", bottom=False):
        """Axis-aligned (local frame) box: centre-bottom c=(u,v,z), size s=(du,dv,dz)."""
        u, v, z = c
        a, b, h = s[0] / 2, s[1] / 2, s[2]
        p = [self.w((u + x, v + y, z)) for x, y in ((-a, -b), (a, -b), (a, b), (-a, b))]
        q = [x + [0, 0, h] for x in p]
        for i in range(4):
            j = (i + 1) % 4
            self.quad(p[i], p[j], q[j], q[i], col, mat)
        self.quad(q[0], q[1], q[2], q[3], top or col, mat)
        if bottom:
            self.quad(p[0], p[3], p[2], p[1], col, mat)

    def cyl(self, u, v, z0, z1, r0, r1=None, n=10, col=BLACK, cap=True, top=None):
        r1 = r0 if r1 is None else r1
        a = [2 * math.pi * (i + 0.5) / n for i in range(n)]
        lo = [self.w((u + r0 * math.cos(t), v + r0 * math.sin(t), z0)) for t in a]
        hi = [self.w((u + r1 * math.cos(t), v + r1 * math.sin(t), z1)) for t in a]
        for i in range(n):
            j = (i + 1) % n
            self.quad(lo[i], lo[j], hi[j], hi[i], col)
        if cap and r1 > 0:
            c = self.w((u, v, z1))
            for i in range(n):
                self.tri(c, hi[i], hi[(i + 1) % n], top or col)

    def dome(self, u, v, z0, r, hgt, n=10, rings=3, col=RED):
        prev = [self.w((u + r * math.cos(2 * math.pi * (i + 0.5) / n), v + r * math.sin(2 * math.pi * (i + 0.5) / n), z0))
                for i in range(n)]
        for k in range(1, rings + 1):
            f = k / rings
            rr = r * math.cos(f * math.pi / 2)
            zz = z0 + hgt * math.sin(f * math.pi / 2)
            if k == rings:
                c = self.w((u, v, zz))
                for i in range(n):
                    self.tri(prev[i], prev[(i + 1) % n], c, col)
            else:
                cur = [self.w((u + rr * math.cos(2 * math.pi * (i + 0.5) / n), v + rr * math.sin(2 * math.pi * (i + 0.5) / n), zz))
                       for i in range(n)]
                for i in range(n):
                    j = (i + 1) % n
                    self.quad(prev[i], prev[j], cur[j], cur[i], col)
                prev = cur

    def tube(self, a, b, r, col, n=4):
        """Open tube between local points a, b."""
        A, Bp = self.w(a), self.w(b)
        d = Bp - A
        L = np.linalg.norm(d)
        if L < 1e-6:
            return
        d /= L
        e = np.cross(d, [0, 0, 1.0])
        if np.linalg.norm(e) < 1e-3:
            e = np.cross(d, [1.0, 0, 0])
        e /= np.linalg.norm(e)
        f = np.cross(d, e)
        ring = [e * math.cos(2 * math.pi * i / n) * r + f * math.sin(2 * math.pi * i / n) * r for i in range(n)]
        for i in range(n):
            j = (i + 1) % n
            self.quad(A + ring[i], A + ring[j], Bp + ring[j], Bp + ring[i], col)

    def poly_tube(self, pts, r, col, n=4):
        for a, b in zip(pts[:-1], pts[1:]):
            self.tube(a, b, r, col, n)

    def out(self, name):
        res = []
        for (col, mat), T in sorted(self.t.items(), key=lambda kv: str(kv[0])):
            T = np.asarray(T, np.float32).reshape(-1, 3, 3)   # every primitive is wound CCW seen from outside
            res.append({"name": name, "tris": T, "col": np.asarray(col, np.float32), "mat": mat})
        return res


# ---------------------------------------------------------------- models (local frame: u along way, v across)
def post_box(m, two):
    m.cyl(0, 0, -0.1, 0.08, 0.30, n=12, col=BLACK)                       # plinth
    m.cyl(0, 0, 0.08, 1.30, 0.265, n=12, col=RED, cap=False)              # body
    m.cyl(0, 0, 1.30, 1.36, 0.30, n=12, col=RED, cap=False)               # flared cap rim
    m.cyl(0, 0, 1.30, 1.30, 0.265, 0.30, n=12, col=RED, cap=False)
    m.dome(0, 0, 1.36, 0.30, 0.16, n=12, rings=3, col=RED)
    # aperture(s) on the front (local -v faces the way): black hood + slot
    for k, du in enumerate([-0.1, 0.1] if two else [0.0]):
        m.box((du, -0.268, 1.05), (0.18 if two else 0.26, 0.04, 0.035), BLACK)
        m.box((du, -0.275, 1.09), (0.20 if two else 0.28, 0.05, 0.03), RED)
    m.box((0, -0.262, 0.80), (0.16, 0.02, 0.14), WHITE)                   # collection plate
    m.box((0, -0.262, 0.55), (0.10, 0.02, 0.08), GOLD)                    # cypher


def k6(m):
    W, H = 0.91, 2.42
    a = W / 2
    m.box((0, 0, 0), (W + 0.04, W + 0.04, 0.10), RED_K6)                     # plinth
    m.box((0, 0, 0.10), (W - 0.10, W - 0.10, 2.05), GLASS)                   # glazed core
    for su, sv in ((1, 1), (1, -1), (-1, 1), (-1, -1)):                    # corner piers
        m.box((su * (a - 0.06), sv * (a - 0.06), 0.10), (0.12, 0.12, 2.0), RED_K6)
    # each side: frame + 8 x 3 panes (glazing bars) + cream fascia
    for side in range(4):
        ang = side * math.pi / 2
        ca, sa = math.cos(ang), math.sin(ang)
        rot = lambda u, v: (u * ca - v * sa, u * sa + v * ca)  # noqa: E731
        d = a - 0.035
        def bx(u, z, du, dz, col=RED_K6, depth=0.05):
            cu, cv = rot(u, -d)
            s = (du, depth, dz) if side % 2 == 0 else (depth, du, dz)
            m.box((cu, cv, z), s, col)
        bx(0, 0.10, W - 0.2, 0.22)                                         # bottom rail
        bx(0, 1.88, W - 0.2, 0.08)                                         # top rail
        for u in (-0.115, 0.115):                                         # 2 mullions -> 3 panes across
            bx(u, 0.32, 0.03, 1.56, depth=0.04)
        for k in range(1, 8):                                             # 7 transoms -> 8 panes up
            bx(0, 0.32 + k * 1.56 / 8 - 0.015, W - 0.2, 0.03, depth=0.04)
        bx(0, 1.96, W - 0.06, 0.20, col=RED_K6, depth=0.06)               # fascia band
        bx(0, 2.0, 0.60, 0.12, col=CREAM, depth=0.075)                     # TELEPHONE sign
    m.box((0, 0, 2.16), (W, W, 0.08), RED_K6)
    # domed roof: segmental arcs on all four sides -> a shallow square dome, plus crown boss
    m.box((0, 0, 2.24), (W - 0.04, W - 0.04, 0.06), RED_K6)
    m.dome(0, 0, 2.30, (W - 0.06) / 2 * 1.41, 0.12, n=4, rings=3, col=RED_K6)
    m.box((0, 0, 2.30), (0.20, 0.20, 0.12), RED_K6)


def bench(m, back):
    for u in (-0.75, 0.75):                                               # cast-iron ends
        m.box((u, 0.0, 0.0), (0.06, 0.50, 0.42), IRON)
        if back:
            m.box((u, 0.24, 0.42), (0.06, 0.06, 0.42), IRON)
    for k in range(4):                                                    # seat slats
        m.box((0, -0.20 + k * 0.13, 0.42), (1.80, 0.10, 0.04), WOOD)
    if back:
        for k in range(3):
            m.box((0, 0.26, 0.52 + k * 0.12), (1.80, 0.03, 0.09), WOOD)


def waste_basket(m):
    m.cyl(0, 0, 0.0, 0.05, 0.25, n=10, col=BLACK)
    m.cyl(0, 0, 0.05, 0.80, 0.27, n=10, col=BLACK, cap=False)
    m.cyl(0, 0, 0.62, 0.68, 0.275, n=10, col=GOLD, cap=False)             # gold band / crest
    m.cyl(0, 0, 0.80, 0.86, 0.29, n=10, col=BLACK, cap=False)
    m.box((0, -0.26, 0.86), (0.30, 0.06, 0.10), (0.01, 0.01, 0.01))       # throw slot
    m.dome(0, 0, 0.86, 0.29, 0.16, n=10, rings=2, col=BLACK)


def sheffield(m, u):
    m.poly_tube([(u, -0.36, 0.0), (u, -0.36, 0.68), (u, -0.30, 0.76), (u, 0.30, 0.76), (u, 0.36, 0.68),
                 (u, 0.36, 0.0)], 0.025, IRON, n=5)


def bicycle(m, u, col):
    """Bike leaning against a stand at local u (side offset), length along v."""
    R = 0.33
    for vw in (-0.53, 0.53):                                              # wheels: 10-sided rings of tubes
        pts = [(u, vw + R * math.cos(2 * math.pi * i / 10), R + R * math.sin(2 * math.pi * i / 10)) for i in range(11)]
        m.poly_tube(pts, 0.022, TYRE, n=3)
        m.tube((u, vw, R - 0.04), (u, vw, R + 0.04), 0.03, STEEL, n=3)    # hub
    bb, st, ht = (u, 0.0, 0.32), (u, -0.22, 0.85), (u, 0.38, 0.82)
    m.poly_tube([(u, -0.53, R), bb, st, (u, -0.53, R)], 0.02, col, n=3)   # chainstay, seat tube, seat stay
    m.poly_tube([bb, ht, (u, 0.53, R)], 0.022, col, n=3)                  # down tube, fork
    m.tube(st, (u, 0.36, 0.78), 0.02, col, n=3)                           # top tube
    m.tube((u, -0.25, 0.85), (u, -0.25, 0.92), 0.012, STEEL, n=3)
    m.box((u, -0.27, 0.92), (0.08, 0.22, 0.05), BLACK)                    # saddle
    m.tube(ht, (u, 0.38, 0.98), 0.018, col, n=3)
    m.tube((u - 0.26, 0.38, 0.98), (u + 0.26, 0.38, 0.98), 0.015, BLACK, n=3)   # handlebar


def bollard(m, rising):
    if rising:
        m.cyl(0, 0, -0.02, 0.02, 0.17, n=10, col=STEEL)
        m.cyl(0, 0, 0.02, 0.75, 0.11, n=10, col=STEEL, cap=False)
        m.cyl(0, 0, 0.55, 0.65, 0.112, n=10, col=(0.75, 0.08, 0.06), cap=False)
        m.dome(0, 0, 0.75, 0.11, 0.04, n=10, rings=2, col=STEEL)
    else:
        m.cyl(0, 0, 0.0, 0.10, 0.12, n=10, col=IRON)
        m.cyl(0, 0, 0.10, 0.82, 0.10, 0.085, n=10, col=IRON, cap=False)
        m.cyl(0, 0, 0.82, 0.88, 0.11, n=10, col=IRON, cap=False)
        m.dome(0, 0, 0.88, 0.11, 0.10, n=10, rings=2, col=IRON)


def street_lamp(m):
    m.cyl(0, 0, 0.0, 0.9, 0.17, 0.12, n=10, col=IRON)                      # fluted base
    m.cyl(0, 0, 0.9, 1.0, 0.13, n=10, col=IRON)
    m.cyl(0, 0, 1.0, 3.9, 0.075, 0.06, n=8, col=IRON, cap=False)
    m.cyl(0, 0, 3.9, 4.05, 0.10, n=8, col=IRON)                            # collar
    m.cyl(0, 0, 4.05, 4.15, 0.08, 0.22, n=4, col=IRON, cap=False)          # lantern bottom
    m.cyl(0, 0, 4.15, 4.60, 0.20, 0.26, n=4, col=(0.92, 0.88, 0.70), cap=False)   # glass (lit cream)
    for k in range(4):                                                     # corner frames
        a = math.pi / 4 + k * math.pi / 2
        m.tube((0.2 * math.cos(a), 0.2 * math.sin(a), 4.15), (0.26 * math.cos(a), 0.26 * math.sin(a), 4.6), 0.015, IRON, n=3)
    m.cyl(0, 0, 4.60, 4.75, 0.30, 0.10, n=4, col=IRON)                     # hood
    m.cyl(0, 0, 4.75, 4.90, 0.03, 0.0, n=4, col=IRON, cap=False)           # finial


# Session 38: the square's lamps are not in OSM. Type from photos (Commons/geograph, CC BY-SA 2.0/4.0: geograph
# 5509393, 5524917, 5617767, 6453814, 7414782, 7790439/40, 8005736, 6052227, 6242734, "Market Hill Cambridge UK";
# Mapillary 138292341951529 (2021), 3304474719779190 (2015), 918215512073749 (2017), 652094232632931 (2021)):
# black tapered column ~7.5 m, a short cross-arm at the top carrying two grey saucer luminaires (one on some).
# Positions: medium confidence (+-3 m), from the Mapillary pose + bearing of the column in 138292341951529 (west
# edge) and ground-plane back-projection of column bases in Commons "View from Great St Mary's Cambridge - 03"
# (The wub, CC BY-SA 4.0) through a camera fitted to the OSM stall-row ends; each also seen in >= 1 street photo.
PHOTO_LAMPS = [   # (x, y collision frame, heads)
    (-121.0, 83.0, 2),    # west edge of the square, north part (Mapillary 138292341951529; c66 geograph 6052227)
    (-86.0, 104.0, 2),    # north side, east of the Trailer of Life (Market Hill north footway; geograph 5617767, 8005736)
    (-71.0, 66.0, 2),     # east side of the square, kerb line (geograph 5509393, 5711954)
    (-66.0, 38.0, 1),     # south-east corner, Petty Cury entrance (geograph 5032491 / 7790439)
]


def twin_lamp(m, heads):
    m.cyl(0, 0, 0.0, 0.35, 0.16, 0.14, n=10, col=IRON)                    # base shoe
    m.cyl(0, 0, 0.35, 7.3, 0.10, 0.06, n=10, col=IRON, cap=False)          # tapered column
    m.cyl(0, 0, 7.3, 7.45, 0.07, n=8, col=IRON)
    arms = [-1, 1] if heads == 2 else [1]
    for sg in arms:
        m.tube((0, 0, 7.38), (sg * 0.55, 0, 7.5), 0.035, IRON, n=4)
        m.tube((sg * 0.55, 0, 7.5), (sg * 0.75, 0, 7.48), 0.035, IRON, n=4)
        m.cyl(sg * 0.75, 0, 7.30, 7.36, 0.24, 0.27, n=12, col=(0.95, 0.93, 0.85), cap=False)   # diffuser
        m.cyl(sg * 0.75, 0, 7.36, 7.40, 0.29, n=12, col=(0.55, 0.57, 0.58), cap=False)          # rim
        m.dome(sg * 0.75, 0, 7.40, 0.29, 0.10, n=12, rings=2, col=(0.55, 0.57, 0.58))           # saucer hood
        m.cyl(sg * 0.75, 0, 7.30, 7.30, 0.0, 0.24, n=12, col=(0.95, 0.93, 0.85), cap=False)     # lit underside


# ---------------------------------------------------------------- build
def build(verbose=False):
    import json
    import build as B
    import street_objects as S
    from shapely.geometry import LineString, Point
    from shapely.strtree import STRtree

    nodes, ways, _, _ = B.load_osm()
    lines = []
    for w in ways.values():
        t = w.get("tags", {})
        if "highway" in t and t["highway"] not in ("bus_stop", "platform"):
            c = B.coords(w, nodes)
            if c and len(c) >= 2:
                ln = LineString(c)
                if ln.distance(Point(ZONE_C[0] + E0, ZONE_C[1] + N0)) < ZONE_R + 60:
                    lines.append(ln)
    tree = STRtree(lines)
    g = Ground()
    out, counts, tris = [], {}, {}
    objs = S.objects_in_area() + [(x + E0, y + N0, 101, {"heads": h}) for x, y, h in PHOTO_LAMPS]
    kiosks = [(E, N) for E, N, k, _ in objs if k == 7]
    for E, N, k, t in objs:
        x, y = E - E0, N - N0
        if (k not in KINDS and k != 101) or (x - ZONE_C[0]) ** 2 + (y - ZONE_C[1]) ** 2 >= ZONE_R ** 2:
            continue
        p = Point(E, N)
        ln = lines[int(tree.nearest(p))]
        d = ln.project(p)
        a, b = ln.interpolate(max(d - 1, 0)), ln.interpolate(min(d + 1, ln.length))
        h = math.atan2(b.y - a.y, b.x - a.x)
        # local -v must face the way (fronts of post boxes, benches, kiosk doors)
        side = (b.x - a.x) * (N - a.y) - (b.y - a.y) * (E - a.x)    # > 0: object left of the way direction
        if side < 0:
            h += math.pi
        if "direction" in t:
            try:
                h = math.radians(90 - float(t["direction"])) + math.pi / 2   # facing bearing -> local -v
            except ValueError:
                pass
        if k == 7:   # a row of kiosks (3 K6 nodes 0.9 m apart by Great St Mary's): square them up with the row
            nb = [(e2, n2) for e2, n2 in kiosks if 0.3 < math.hypot(e2 - E, n2 - N) < 1.5]
            if nb:
                r = math.atan2(nb[0][1] - N, nb[0][0] - E)
                h = r + round((h - r) / (math.pi / 2)) * math.pi / 2
        m = Mesh()
        m.frame(x, y, g(x, y), h)
        name = "street_lamp_photo" if k == 101 else S.TYPES[k][0]
        if k == 6:
            post_box(m, t.get("post_box:apertures") == "2")
        elif k == 7:
            k6(m)
        elif k == 2:
            bench(m, t.get("backrest") != "no")
        elif k == 4:
            waste_basket(m)
        elif k == 3:
            bollard(m, t.get("bollard") == "rising" or t.get("barrier") == "rising_kerb")
        elif k == 1:
            street_lamp(m)
        elif k == 101:
            twin_lamp(m, t["heads"])
        elif k == 5:
            try:
                n = int(t.get("capacity", "4")) // 2
            except ValueError:
                n = 2
            n = int(np.clip(n, 1, 12))
            rng = np.random.default_rng(int(abs(x * 100 + y * 7)) % 2 ** 31)
            for j in range(n):
                u = (j - (n - 1) / 2) * 1.0
                sheffield(m, u)
                for s in (-0.12, 0.12):
                    if rng.random() < 0.5:
                        bicycle(m, u + s, FRAMES[int(rng.integers(len(FRAMES)))])
        nid = "%.1f,%.1f" % (x, y)
        parts = m.out(f"furniture:{name}@{nid}")
        out += parts
        counts[name] = counts.get(name, 0) + 1
        tris[name] = tris.get(name, 0) + sum(len(pt["tris"]) for pt in parts)
    if verbose:
        print(json.dumps({"objects": counts, "tris": tris, "total": sum(tris.values())}, indent=1))
    return out


if __name__ == "__main__":
    build(verbose=True)
