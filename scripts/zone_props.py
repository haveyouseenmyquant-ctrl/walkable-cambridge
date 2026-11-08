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

WHITE = (0.90, 0.90, 0.87)
STRIPES = [(0.78, 0.12, 0.13), (0.10, 0.45, 0.25), (0.13, 0.27, 0.62), (0.90, 0.72, 0.12)]
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
def stall(m, g, c, ax, front, depth, width, stripe, idx):
    """Stall centred at c; ax = unit along-row, front = unit towards customers."""
    c, ax, front = np.asarray(c, float), np.asarray(ax, float), np.asarray(front, float)
    z = g(*c)
    up = np.array([0, 0, 1.0])
    hw, hd = width / 2, depth / 2
    ax2, fr2 = ax, front
    P = lambda s, t, h: np.array([*(c + s * ax2 + t * fr2), z + h])  # noqa: E731
    ax, front = np.array([*ax, 0.0]), np.array([*front, 0.0])
    EAVE, RIDGE, OVER = 2.3, 3.0, 0.35
    ps = 0.06
    # posts at the 4 corners
    for s in (-hw + 0.05, hw - 0.05 - ps):
        for t in (-hd + 0.05, hd - 0.05 - ps):
            m.box(P(s, t, 0), ax * ps, front * ps, up * (EAVE + 0.05), POST)
    # centre ridge posts (front and back gable)
    # counter: front, 0.65 deep, 0.9 high, boarded front
    m.box(P(-hw + 0.1, hd - 0.75, 0), ax * (width - 0.2), front * 0.65, up * 0.9, BOARD, top=COUNTER_TOP)
    # display shelf behind the counter
    m.box(P(-hw + 0.15, hd - 1.25, 0.6), ax * (width - 0.3), front * 0.4, up * 0.08, COUNTER_TOP)
    # back board up to under the eave
    m.box(P(-hw + 0.05, -hd + 0.05, 0), ax * (width - 0.1), front * 0.05, up * EAVE, BOARD)
    # side boards (lower half only, as in the photos)
    for s in (-hw + 0.05, hw - 0.08):
        m.box(P(s, -hd + 0.1, 0), ax * 0.03, front * (depth - 0.9), up * 1.2, BOARD)
    # gabled canopy, ridge along the row; striped down the slope
    n = 6
    col_a, col_b = WHITE, STRIPES[stripe % len(STRIPES)]
    for k in range(n):
        s0 = -hw - 0.05 + (width + 0.1) * k / n
        s1 = -hw - 0.05 + (width + 0.1) * (k + 1) / n
        col = col_b if (k + idx) % 2 else col_a
        # front slope: ridge (t=0) down to front eave (t=hd+OVER)
        m.quad(P(s0, hd + OVER, EAVE), P(s1, hd + OVER, EAVE), P(s1, 0, RIDGE), P(s0, 0, RIDGE), col, two=True)
        # back slope
        m.quad(P(s1, -hd - 0.1, EAVE), P(s0, -hd - 0.1, EAVE), P(s0, 0, RIDGE), P(s1, 0, RIDGE), col, two=True)
        # front valance (vertical flap)
        m.quad(P(s0, hd + OVER, EAVE - 0.25), P(s1, hd + OVER, EAVE - 0.25), P(s1, hd + OVER, EAVE),
               P(s0, hd + OVER, EAVE), col, two=True)
    # gable ends
    for s, sg in ((-hw - 0.05, -1), (hw + 0.05, 1)):
        a, b, r = P(s, hd + OVER, EAVE), P(s, -hd - 0.1, EAVE), P(s, 0, RIDGE)
        m.tri(a, b, r, WHITE)
        m.tri(a, r, b, WHITE)


def stall_rows(m, g, poly, centre, seed):
    from shapely.geometry import Point
    rect = np.array(poly.minimum_rotated_rectangle.exterior.coords)[:4]
    e1, e2 = rect[1] - rect[0], rect[2] - rect[1]
    if np.linalg.norm(e1) < np.linalg.norm(e2):
        e1, e2 = e2, e1
        o = rect[1]
    else:
        o = rect[0]
    L, W = np.linalg.norm(e1), np.linalg.norm(e2)
    ax, nr = e1 / L, e2 / W
    width = 3.0
    nst = max(1, int(L // width))
    width = L / nst
    if W >= 6.0:
        rows = [(W * 0.25, -nr, W / 2), (W * 0.75, nr, W / 2)]   # back to back, fronts outward
    else:
        f = nr if np.dot(centre - (o + e1 / 2 + e2 / 2), nr) > 0 else -nr
        rows = [(W * 0.5, f, W)]
    cnt = 0
    for ri, (off, front, depth) in enumerate(rows):
        for i in range(nst):
            c = o + ax * (width * (i + 0.5)) + nr * off
            if not poly.buffer(0.3).contains(Point(*c)):
                continue
            if not poly.buffer(0.6).contains(Point(*(c + front * (depth / 2 - 0.3)))):
                continue
            stall(m, g, c, ax, front, depth - 0.15, width - 0.1, seed + 3 * ri + i // 2, i)
            cnt += 1
    return cnt


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
    rect = np.array(poly.minimum_rotated_rectangle.exterior.coords)[:4]
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

    out = []
    for k, wid in enumerate(STALL_ROOFS):
        pg = poly(wid)
        if pg is None or pg.is_empty:
            continue
        m = Mesh()
        n = stall_rows(m, g, pg, centre, k)
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
