"""Market Square (Market Hill) props for the zone build: market stalls, Hobson's Conduit fountain
remains, the two burger trailers.

build() -> list of {"name": str, "tris": (k,3,3) float32 collision-frame triangles (CCW seen from
outside; canopies are double-sided), "col": (k,3) float32 RGB 0..1}.

Evidence:
- Layout: OSM building=roof layer=1 strips way/400160678..400160685 are the permanent stall rows
  (each 3.5-8 m wide, 18-31 m long); stalls are laid on a 3 m pitch along each strip's long axis,
  two back-to-back rows when the strip is >= 6 m wide, one row otherwise, kept where the stall
  centre lies inside the strip polygon (handles the notches in 400160680/400160682).
  way/400160677 ("Trailer of Life") and way/400160686 ("Frank's Burgers") are food trailers.
  The fountain is the OSM node "Hobson's Conduit" (disused:amenity=drinking_water) at the
  square's centre, in the gap the stall strips leave around it.
- Look (Mapillary refs of the market-facing walls, e.g. mapillary_facade/3304474719779190,
  138292341951529, 150365460382983): stalls have dark metal posts, white-boarded counters and
  back boards, gabled canvas canopies with eaves ~2.3 m and ridge ~3 m, white with broad
  red / green / blue / yellow stripes running down the slope.
- Ground heights from data/lidar/dtm_1m.tif (BNG), sampled per prop.
"""
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
E0, N0 = 545000.0, 258400.0
DTM = os.path.join(ROOT, "data/lidar/dtm_1m.tif")

STALL_ROOFS = list(range(400160678, 400160686))
TRAILERS = {400160677: "Trailer of Life", 400160686: "Frank's Burgers"}
FOUNTAIN_FALLBACK = (-96.3, 65.2)

WHITE = (0.92, 0.92, 0.89)
STRIPES = [(0.80, 0.14, 0.16), (0.12, 0.48, 0.30), (0.14, 0.30, 0.68), (0.94, 0.72, 0.14)]   # red, green, blue, yellow
STRIPE_W = 0.62      # canvas stripe width along the row (m)
BAY = 3.0            # stall bay pitch along the row (m)
FRAME = (0.58, 0.60, 0.61)   # galvanised scaffold tube
CLOTHS = [(0.12, 0.45, 0.28), (0.12, 0.45, 0.28), (0.10, 0.10, 0.11), (0.85, 0.85, 0.82), (0.55, 0.12, 0.14),
          (0.16, 0.22, 0.45), (0.45, 0.62, 0.30)]
SHEETS = [(0.62, 0.14, 0.17), (0.62, 0.14, 0.17), (0.16, 0.22, 0.45), (0.88, 0.88, 0.85), (0.12, 0.40, 0.25),
          (0.25, 0.25, 0.27)]
CRATE = (0.55, 0.42, 0.28)
GOODS = [(0.80, 0.20, 0.12), (0.92, 0.62, 0.15), (0.35, 0.55, 0.20), (0.85, 0.75, 0.45), (0.55, 0.30, 0.45),
         (0.75, 0.68, 0.55), (0.30, 0.35, 0.55), (0.90, 0.85, 0.70)]
SKIRTS = [(0.10, 0.45, 0.28), (0.10, 0.45, 0.28), (0.72, 0.12, 0.14), (0.15, 0.28, 0.62)]   # stripe on white cloth
POST = (0.12, 0.12, 0.13)
BOARD = (0.86, 0.85, 0.80)
COUNTER_TOP = (0.55, 0.42, 0.28)
STONE = (0.72, 0.68, 0.60)
STONE_DK = (0.58, 0.55, 0.49)
WATER = (0.25, 0.30, 0.30)


# ---------------------------------------------------------------- geometry helpers
class Mesh:
    def __init__(self):
        self.t, self.c = [], []

    def tri(self, a, b, c, col):
        self.t.append((a, b, c))
        self.c.append(col)

    def quad(self, a, b, c, d, col, two=False):
        """a,b,c,d CCW seen from the front."""
        self.tri(a, b, c, col)
        self.tri(a, c, d, col)
        if two:
            self.tri(a, c, b, col)
            self.tri(a, d, c, col)

    def box(self, o, u, v, w, col, top=None, bottom=False):
        """Oriented box: origin corner o, edge vectors u, v, w (right-handed, w up)."""
        o, u, v, w = (np.asarray(x, float) for x in (o, u, v, w))
        if np.dot(np.cross(u, v), w) < 0:
            u, v = v, u
        p = [o, o + u, o + u + v, o + v]
        q = [x + w for x in p]
        for i in range(4):
            j = (i + 1) % 4
            self.quad(p[i], p[j], q[j], q[i], col)
        self.quad(q[0], q[1], q[2], q[3], top or col)
        if bottom:
            self.quad(p[0], p[3], p[2], p[1], col)

    def prism(self, cx, cy, z0, z1, r, n, col, top=None, r_top=None, cap=True):
        r_top = r if r_top is None else r_top
        a = np.arange(n) * 2 * np.pi / n + np.pi / n
        lo = [np.array([cx + r * np.cos(t), cy + r * np.sin(t), z0]) for t in a]
        hi = [np.array([cx + r_top * np.cos(t), cy + r_top * np.sin(t), z1]) for t in a]
        for i in range(n):
            j = (i + 1) % n
            self.quad(lo[i], lo[j], hi[j], hi[i], col)
        if cap:
            ctr = np.array([cx, cy, z1])
            for i in range(n):
                self.tri(ctr, hi[i], hi[(i + 1) % n], top or col)

    def out(self, name):
        return {"name": name, "tris": np.asarray(self.t, np.float32).reshape(-1, 3, 3),
                "col": np.asarray(self.c, np.float32).reshape(-1, 3)}


class Ground:
    def __init__(self):
        import rasterio
        self.ds = rasterio.open(DTM)
        self.a = self.ds.read(1)

    def __call__(self, x, y):
        r, c = self.ds.index(x + E0, y + N0)
        win = self.a[max(r - 1, 0):r + 2, max(c - 1, 0):c + 2]
        win = win[win > -100]
        return float(np.median(win)) if win.size else 9.3


# ---------------------------------------------------------------- props
def strip_base(gB, a, ds):
    """Median DTM of the pixels inside the footprint (BNG): the same `dmed` build.py uses for the tile canopy."""
    from rasterio.features import geometry_mask
    from rasterio.windows import from_bounds
    from shapely.geometry import mapping
    x0, y0, x1, y1 = gB.bounds
    win = from_bounds(x0 - 1, y0 - 1, x1 + 1, y1 + 1, ds.transform).round_offsets().round_lengths()
    r0, c0 = int(win.row_off), int(win.col_off)
    sub = a[r0:r0 + int(win.height), c0:c0 + int(win.width)]
    import rasterio
    wtf = rasterio.transform.from_origin(ds.transform.c + c0, ds.transform.f - r0, 1, 1)
    msk = geometry_mask([mapping(gB)], sub.shape, wtf, invert=True)
    if not msk.any():
        msk = geometry_mask([mapping(gB)], sub.shape, wtf, invert=True, all_touched=True)
    return float(np.median(sub[msk]))


def strip_frame(gB):
    """Same frame as build.canopy_parts: o = rect corner, ax = long axis, nr = across, L, W (local frame)."""
    r = np.asarray(gB.minimum_rotated_rectangle.exterior.coords)[:4] - [E0, N0]
    e1, e2 = r[1] - r[0], r[2] - r[1]
    if np.linalg.norm(e1) < np.linalg.norm(e2):
        r = np.roll(r, -1, 0)
        e1, e2 = e2, e1
    L, W = np.linalg.norm(e1), np.linalg.norm(e2)
    return r[0], e1 / L, e2 / W, L, W


def stall_strip(m, B, g, gB, centre, seed, base=None):
    """One OSM building=roof stall row (way/400160678..685): a continuous gabled canvas canopy wrapped around the
    tile's canopy slab (build.add_canopy), galvanised frame, and stalls (table with cloth, goods crates, back and
    side sheets) on a ~3 m bay pitch, back to back when the strip is >= 6 m wide."""
    from shapely.geometry import Point, Polygon
    rng = np.random.default_rng(1000 + seed)
    o, ax, nr, L, W = strip_frame(gB)
    zb = strip_base(gB, g.a, g.ds) if base is None else base
    ze = zb + B.CANOPY_EAVE
    parts_f = B.canopy_parts(gB, True)

    def hgt(P):
        """Canopy height above the eave at local points: the slope part nearest each point (B.canopy_height takes
        the max over every part's plane, which reads the ridge height everywhere)."""
        Q = np.asarray(P, float).reshape(-1, 2) + [E0, N0]
        if not parts_f:
            return np.zeros(len(Q))
        from shapely.geometry import Point as _P
        d = np.array([[pt.distance(_P(*q)) for q in Q] for pt, _ in parts_f])
        vals = np.array([f(Q) for _, f in parts_f])
        return np.clip(vals[d.argmin(0), np.arange(len(Q))], 0, None)
    off = B.CANOPY_T / 2 + 0.04          # canvas sits 4 cm off the tile slab, top and bottom
    cols = [STRIPES[i] for i in rng.permutation(len(STRIPES))]
    loc = lambda q: q + [E0, N0]  # noqa: E731
    # --- canopy: bands across the ridge, colour / white alternating (Commons: "Cambridge Market stalls at lunchtime")
    nb = max(1, int(round(L / STRIPE_W)))
    sw = L / nb
    for part, f in B.canopy_parts(gB, True):
        for k in range(nb):
            band = Polygon([loc(o + ax * sw * k - nr), loc(o + ax * sw * (k + 1) - nr),
                            loc(o + ax * sw * (k + 1) + nr * (W + 1)), loc(o + ax * sw * k + nr * (W + 1))])
            col = cols[(k // 2) % len(cols)] if k % 2 else WHITE
            for p in B.polys_of(part.intersection(band)):
                T = B.triangulate(p)
                if not len(T):
                    continue
                h = f(T.reshape(-1, 2) + [E0, N0]).reshape(-1, 3, 1) + ze
                for tri in np.concatenate([T, h + off], 2):
                    m.tri(*tri, col)
                for tri in np.concatenate([T, h - off], 2)[:, ::-1]:
                    m.tri(*tri, col)
    # --- valance along the long eave edges: a 0.28 m flap, outer face + inner face 2 cm inside (no coincident faces)
    for part, _ in B.canopy_parts(gB, True):
        for p in B.polys_of(part):
            ring = np.asarray((p if p.exterior.is_ccw else Polygon(p.exterior.coords[::-1])).exterior.coords) - [E0, N0]
            for a, b in zip(ring[:-1], ring[1:]):
                d = b - a
                ln = np.linalg.norm(d)
                if ln >= 0.3 and abs(np.dot(d / ln, nr)) > 0.95:
                    # gable / notch edge across the row: a canvas band hiding the tile slab's textured edge
                    outn = np.array([d[1], -d[0]]) / ln
                    k = int(min(max(np.dot((a + b) / 2 - o, ax), 0), L - 1e-3) // sw)
                    col = cols[(k // 2) % len(cols)] if k % 2 else WHITE
                    nseg = max(1, int(np.ceil(ln / 0.4)))
                    Ps = [a + d * j / nseg + outn * 0.03 for j in range(nseg + 1)]
                    hs = hgt([a + d * j / nseg - outn * 0.05 for j in range(nseg + 1)])   # sampled just inside
                    for j in range(nseg):
                        p0, p1, h0, h1 = Ps[j], Ps[j + 1], hs[j], hs[j + 1]
                        m.quad([*p0, ze + h0 - off - 0.12], [*p1, ze + h1 - off - 0.12], [*p1, ze + h1 + off + 0.03],
                               [*p0, ze + h0 + off + 0.03], col, two=True)
                    continue
                if ln < 0.3 or abs(np.dot(d / ln, ax)) < 0.95 or hgt([(a + b) / 2])[0] > 0.05:
                    continue
                outn = np.array([d[1], -d[0]]) / ln
                s0, s1 = sorted((np.dot(a - o, ax), np.dot(b - o, ax)))
                cuts = [s0] + [sw * k for k in range(int(s0 // sw) + 1, int(np.ceil(s1 / sw)))] + [s1]
                for u0, u1 in zip(cuts[:-1], cuts[1:]):
                    k = int(((u0 + u1) / 2) // sw)
                    col = cols[(k // 2) % len(cols)] if k % 2 else WHITE
                    t = np.dot(a - o, nr)
                    P0, P1 = o + ax * u0 + nr * t, o + ax * u1 + nr * t
                    if np.dot(np.cross([*ax, 0], [*outn, 0]), [0, 0, 1]) > 0:
                        P0, P1 = P1, P0
                    zt, zl = ze + off, ze - 0.22
                    m.quad([*P0, zl], [*P1, zl], [*P1, zt], [*P0, zt], col)
                    Q0, Q1 = P0 - outn * 0.02, P1 - outn * 0.02
                    m.quad([*Q1, zl], [*Q0, zl], [*Q0, zt - 2 * off], [*Q1, zt - 2 * off], col)
                    # scalloped hem: half-round tongues below the flap, ~0.3 m wide, both faces
                    nsc = max(1, int(round(np.linalg.norm(P1 - P0) / 0.3)))
                    for j in range(nsc):
                        A_, B_ = P0 + (P1 - P0) * j / nsc, P0 + (P1 - P0) * (j + 1) / nsc
                        arc = [A_ + (B_ - A_) * f for f in (0.0, 0.25, 0.75, 1.0)]
                        dz = [0.0, 0.075, 0.075, 0.0]
                        for a_, b_, da, db in zip(arc[:-1], arc[1:], dz[:-1], dz[1:]):
                            m.quad([*a_, zl - da], [*b_, zl - db], [*b_, zl], [*a_, zl], col, two=True)
    # --- bays, frame and stalls
    nst = max(1, int(round(L / BAY)))
    bw = L / nst
    inside = gB.buffer(0.05)
    inn = lambda q, buf=0.0: (gB.buffer(buf) if buf else inside).contains(Point(*loc(q)))  # noqa: E731
    up = np.array([0, 0, 1.0])
    A3, N3 = np.array([*ax, 0]), np.array([*nr, 0])
    # posts on the two eave lines and the ridge line at every bay boundary
    for i in range(nst + 1):
        s = min(max(bw * i, 0.12), L - 0.12)
        for t in (0.15, W / 2, W - 0.15):
            q = o + ax * s + nr * t
            if not inn(q, 0.1):
                continue
            z0 = g(*q)
            zt = ze + hgt([q])[0] - off
            m.box(np.array([*(q - ax * 0.03 - nr * 0.03), z0]), A3 * 0.06, N3 * 0.06, up * (zt - z0), FRAME)
    # eave rails (one per bay, both eave lines) and ridge rail
    for i in range(nst):
        for t in (0.15, W / 2, W - 0.15):
            q0, q1 = o + ax * bw * i + nr * t, o + ax * bw * (i + 1) + nr * t
            if inn((q0 + q1) / 2, 0.1):
                zr = ze + hgt([(q0 + q1) / 2])[0] - off - 0.06
                m.box(np.array([*(q0 - nr * 0.025), zr]), A3 * bw, N3 * 0.05, up * 0.05, FRAME)
    # stalls
    if W >= 6.0:
        rows = [(W / 4, -nr, W / 2), (3 * W / 4, nr, W / 2)]
    else:
        f = nr if np.dot(centre - (o + ax * L / 2 + nr * W / 2), nr) > 0 else -nr
        rows = [(W / 2, f, W)]
    cnt = 0
    for ri, (t, front, depth) in enumerate(rows):
        for i in range(nst):
            c = o + ax * bw * (i + 0.5) + nr * t
            if not inn(c, 0.3) or not inn(c + front * (depth / 2 - 0.3), 0.6):
                continue
            stall(m, g, c, ax, front, depth, bw, rng, ze, hgt, off)
            cnt += 1
    return cnt


def stall(m, g, c, ax, front, depth, width, rng, ze, hgt, off):
    """Stall goods/sheets under the shared canopy, centred at c; front = unit towards the aisle."""
    z = g(*c)
    up = np.array([0, 0, 1.0])
    A3, F3 = np.array([*ax, 0]), np.array([*front, 0])
    P = lambda s, t, h: np.array([*(c + s * ax + t * front), z + h])  # noqa: E731
    hw, hd = width / 2, depth / 2
    # table along the front, cloth to the ground (box), slightly lighter top
    cloth = CLOTHS[rng.integers(len(CLOTHS))]
    tw, td, th = width - 0.4, 0.85, 0.78
    if rng.random() < 0.08:     # closed / empty bay: just a stack of crates at the back
        tw = 0
    if tw:
        m.box(P(-tw / 2, hd - 0.25 - td, 0), A3 * tw, F3 * td, up * th, cloth, top=tuple(min(1, x * 1.12 + 0.03) for x in cloth))
        if rng.random() < 0.45:   # striped counter skirt (green/white, Commons "Cambridge Market stalls at lunchtime")
            sk = SKIRTS[rng.integers(len(SKIRTS))]
            ns = max(2, int(round(tw / 0.12)))
            for k in range(ns):
                if k % 2:
                    continue
                s0, s1 = -tw / 2 + tw * k / ns, -tw / 2 + tw * (k + 1) / ns
                fy = hd - 0.25 + 0.012
                m.quad(P(s1, fy, 0.02), P(s0, fy, 0.02), P(s0, fy, th - 0.02), P(s1, fy, th - 0.02), sk) \
                    if np.dot(np.cross(A3, F3), up) > 0 else \
                    m.quad(P(s0, fy, 0.02), P(s1, fy, 0.02), P(s1, fy, th - 0.02), P(s0, fy, th - 0.02), sk)
        # goods: a row of crates / trays on the table, tilted display not modelled
        n = int(rng.integers(2, 5))
        cw = tw / n
        for k in range(n):
            gc = GOODS[rng.integers(len(GOODS))]
            h = rng.uniform(0.10, 0.22)
            m.box(P(-tw / 2 + cw * k + 0.05, hd - 0.25 - td + 0.08, th), A3 * (cw - 0.1), F3 * (td - 0.16), up * h,
                  CRATE, top=gc)
            # heaped produce: a low four-sided mound on the crate
            cx0, cy0, zt0 = -tw / 2 + cw * k + cw / 2, hd - 0.25 - td / 2, th + h
            ex, ey = (cw - 0.14) / 2, (td - 0.2) / 2
            apex = P(cx0, cy0, zt0 + rng.uniform(0.06, 0.14))
            cs = [P(cx0 - ex, cy0 - ey, zt0), P(cx0 + ex, cy0 - ey, zt0), P(cx0 + ex, cy0 + ey, zt0), P(cx0 - ex, cy0 + ey, zt0)]
            for a_, b_ in zip(cs, cs[1:] + cs[:1]):
                m.tri(a_, b_, apex, gc)
                m.tri(a_, apex, b_, tuple(x * 0.8 for x in gc))
    if rng.random() < 0.3:   # hanging goods (bags, clothes, baskets) on the front eave rail
        q = c + front * (hd - 0.1)
        zr = ze + hgt([q])[0] - off - 0.1
        for k in range(int(rng.integers(3, 7))):
            s0 = -hw + 0.25 + k * (width - 0.5) / 6
            ln = rng.uniform(0.35, 0.7)
            m.box(P(s0, hd - 0.12, zr - z - ln), A3 * rng.uniform(0.2, 0.35), F3 * 0.06, up * ln, GOODS[rng.integers(len(GOODS))])
    # crates stacked under / behind
    for k in range(int(rng.integers(0, 3))):
        s0 = rng.uniform(-hw + 0.2, hw - 0.7)
        m.box(P(s0, -hd + 0.25, 0), A3 * 0.5, F3 * 0.35, up * (0.3 * (k + 1)), CRATE, top=GOODS[rng.integers(len(GOODS))])
    # back sheet: thin board/sheet at the back of the bay, up to the canopy underside
    if rng.random() < 0.75:
        sc = SHEETS[rng.integers(len(SHEETS))]
        q = c - front * (hd - 0.04)
        zt = ze + hgt([q])[0] - off - 0.02
        m.box(np.array([*(q - ax * (hw - 0.05)), z + 0.05]), A3 * (width - 0.1), F3 * 0.02, up * (zt - z - 0.05), sc)
        if rng.random() < 0.4:   # side sheet on one side, back half
            s = hw - 0.06 if rng.random() < 0.5 else -hw + 0.04
            q1 = c + ax * s - front * (hd - 0.06)
            zt1 = ze + min(hgt([q1])[0], hgt([q1 + front * depth * 0.5])[0]) - off - 0.02
            m.box(np.array([*q1, z + 0.05]), A3 * 0.02, F3 * (depth * 0.5), up * (zt1 - z - 0.05), sc)


def fountain(m, g, cx, cy):
    """Hobson's Conduit market fountain remains: octagonal stone basin with a central pedestal
    (the 1856 Gothic fountain was cut down in the 1950s to the basin and pillar stump)."""
    z = g(cx, cy)
    # stepped plinth
    m.prism(cx, cy, z - 0.2, z + 0.15, 2.95, 8, STONE_DK)
    # basin wall (outer, inner faces + coping)
    R, r, H = 2.7, 2.35, 0.75
    a = np.arange(8) * np.pi / 4 + np.pi / 8
    for i in range(8):
        j = (i + 1) % 8
        po = [np.array([cx + R * np.cos(t), cy + R * np.sin(t)]) for t in (a[i], a[j])]
        pi = [np.array([cx + r * np.cos(t), cy + r * np.sin(t)]) for t in (a[i], a[j])]
        lo, hi = z + 0.15, z + H
        m.quad([*po[0], lo], [*po[1], lo], [*po[1], hi], [*po[0], hi], STONE)
        m.quad([*pi[1], lo], [*pi[0], lo], [*pi[0], hi], [*pi[1], hi], STONE)
        m.quad([*po[0], hi], [*po[1], hi], [*pi[1], hi], [*pi[0], hi], STONE_DK)
    # water / basin floor
    m.prism(cx, cy, z + 0.15, z + 0.35, r, 8, WATER)
    # central pedestal: square base, shaft, cap
    m.prism(cx, cy, z + 0.35, z + 1.0, 0.85, 4, STONE)
    m.prism(cx, cy, z + 1.0, z + 2.5, 0.5, 8, STONE, r_top=0.42)
    m.prism(cx, cy, z + 2.5, z + 2.75, 0.62, 8, STONE_DK)
    m.prism(cx, cy, z + 2.75, z + 3.3, 0.35, 8, STONE, r_top=0.08)


def trailer(m, g, poly):
    rect = np.array(poly.buffer(0.08, join_style=2).minimum_rotated_rectangle.exterior.coords)[:4]
    e1, e2 = rect[1] - rect[0], rect[3] - rect[0]
    o = rect[0]
    if np.cross(e1, e2) < 0:
        e1, e2 = e2, e1
    zc = g(*rect.mean(0))
    up = np.array([0, 0, 1.0])
    O = np.array([*o, zc])
    E1, E2 = np.array([*e1, 0]), np.array([*e2, 0])
    m.box(O + up * 0.0, E1, E2, up * 0.45, POST)                       # chassis / wheels skirt
    m.box(O + up * 0.45, E1, E2, up * 2.15, (0.85, 0.83, 0.78), top=(0.6, 0.6, 0.6))
    # red band along the body
    m.box(O + up * 1.0 - E2 * 0.005 - E1 * 0.005, E1 * 1.01, E2 * 1.01, up * 0.25, (0.70, 0.12, 0.10))


def build():
    import build as B
    from shapely.geometry import Polygon
    nodes, ways, rels, pnodes = B.load_osm()
    g = Ground()

    def poly(wid):
        w = ways.get(wid)
        if not w:
            return None
        c = [nodes[n] for n in w["nodes"] if n in nodes]
        return Polygon([(e - E0, n - N0) for e, n in c]).buffer(0)

    fx, fy = FOUNTAIN_FALLBACK
    for p in pnodes:
        if p["tags"].get("name") == "Hobson's Conduit" and p["id"] in nodes:
            e, n = nodes[p["id"]]
            if abs(e - E0 - fx) < 20 and abs(n - N0 - fy) < 20:
                fx, fy = e - E0, n - N0
    centre = np.array([fx, fy])

    from shapely.affinity import translate
    import json
    try:   # canopy base from the tile build (build.py writes "base" for building=roof entries); else recomputed
        bases = {b["osm_id"]: b["base"] for b in json.load(open(os.path.join(ROOT, "site/manifest.json")))["buildings"]
                 if "base" in b}
    except (OSError, ValueError, KeyError):
        bases = {}
    out = []
    for k, wid in enumerate(STALL_ROOFS):
        pg = poly(wid)
        if pg is None or pg.is_empty:
            continue
        m = Mesh()
        n = stall_strip(m, B, g, translate(pg, E0, N0), centre, k, bases.get(f"way/{wid}"))
        if n:
            out.append(m.out(f"market_stalls:way/{wid}"))
    m = Mesh()
    fountain(m, g, fx, fy)
    out.append(m.out("fountain:hobsons_conduit"))
    for wid, nm in TRAILERS.items():
        pg = poly(wid)
        if pg is not None and not pg.is_empty:
            m = Mesh()
            trailer(m, g, pg)
            out.append(m.out(f"trailer:way/{wid}"))
    return out


if __name__ == "__main__":
    props = build()
    tot = 0
    for p in props:
        t = p["tris"]
        tot += len(t)
        mn, mx = t.reshape(-1, 3).min(0), t.reshape(-1, 3).max(0)
        print(f"{p['name']:32s} {len(t):6d} tris  x[{mn[0]:.1f},{mx[0]:.1f}] y[{mn[1]:.1f},{mx[1]:.1f}] "
              f"z[{mn[2]:.2f},{mx[2]:.2f}]")
    print("total", tot)
