"""Procedural landmark detail for build.py (session 3).

Each of the 25 fixed landmarks gets a style recipe (SPECS) built from a few primitives: towers and spires
found in the LiDAR DSM, corner turrets, pinnacles, buttresses, pointed or square windows, crenellations,
pilasters, cornices, pediments, porticos, domes, cupolas, gable roofs, and arched bridges with galleries,
trusses or stone balls.

Geometry is in the collision frame (x east, y north, z up, metres from E0/N0). Two outputs per landmark:
  solid: replaces the plain body (towers, nave, roofs); goes to the GLB node and the collision file.
  deco:  thin facade detail that sticks out of the footprint; GLB only, so it never blocks walkable ways.
"""
import math

import numpy as np
from rasterio.features import geometry_mask
from shapely.geometry import MultiPoint, Point, Polygon, mapping

STONE = np.array([0.80, 0.74, 0.60])
STONE_D = np.array([0.66, 0.60, 0.48])
LEAD = np.array([0.42, 0.44, 0.46])
TILE_R = np.array([0.52, 0.33, 0.27])
GLASS = np.array([0.10, 0.12, 0.16])
BRICK = np.array([0.62, 0.38, 0.28])
TIMBER = np.array([0.40, 0.29, 0.19])
WHITE = np.array([0.90, 0.88, 0.83])

# style recipes. front: compass bearing the main facade faces (degrees). Defaults in Ctx.
SPECS = {
    "kings-college-chapel": dict(style="gothic", turrets=True, buttress=5.4, crenel=True, roof="lead_low",
                                 big_windows=True, wall=STONE),
    "senate-house": dict(style="classical", front=90, pediment=True, balustrade=True, wall=WHITE),
    "great-st-marys": dict(style="gothic", tower=True, buttress=4.5, crenel=True, wall=STONE),
    "bridge-of-sighs": dict(style="bridge", arches=1, gallery=True, wall=STONE),
    "mathematical-bridge": dict(style="bridge", arches=1, truss=True, wall=TIMBER),
    "fitzwilliam-museum": dict(style="classical", front=90, portico=8, pediment=True, balustrade=True, dome=True,
                               wall=STONE),
    "round-church": dict(style="round", wall=STONE),
    "trinity-great-gate": dict(style="gate_tower", wall=BRICK),
    "wren-library": dict(style="classical", front=280, arcade=True, balustrade=True, statues=True, wall=STONE),
    "st-johns-chapel": dict(style="gothic", tower=True, buttress=4.8, crenel=True, roof="gable", wall=STONE),
    "gibbs-building": dict(style="classical", front=270, pediment=True, balustrade=True, central_arch=True,
                           wall=WHITE),
    "old-schools": dict(style="classical", front=90, balustrade=True, pediment=False, central_arch=True,
                        wall=WHITE),
    "corn-exchange": dict(style="brick_hall", wall=BRICK, roof="gable"),
    "guildhall": dict(style="classical", front=0, balustrade=False, pilaster=4.0, wall=BRICK),
    "pembroke-chapel": dict(style="classical", front=0, pediment=True, cupola=True, roof="gable", wall=WHITE),
    "peterhouse-chapel": dict(style="gothic", buttress=3.6, gables=True, roof="gable", wall=STONE),
    "little-st-marys": dict(style="gothic", buttress=4.0, big_windows=True, roof="gable", wall=STONE),
    "st-benets": dict(style="gothic", tower=True, buttress=0, roof="gable", wall=STONE_D),
    "holy-trinity": dict(style="gothic", tower=True, spire=True, buttress=4.0, roof="gable", wall=STONE),
    "pitt-building": dict(style="gothic", tower=True, buttress=3.8, crenel=True, wall=STONE),
    "gate-of-honour": dict(style="gate", wall=STONE),
    "clare-bridge": dict(style="bridge", arches=3, balls=True, wall=STONE),
    "pepys-library": dict(style="classical", front=225, arcade=True, curved_gables=True, wall=BRICK),
    "emmanuel-chapel": dict(style="classical", front=270, arcade=True, pediment=True, cupola=True, wall=STONE),
    "our-lady-english-martyrs": dict(style="gothic", tower=True, spire=True, buttress=4.2, roof="gable",
                                     wall=STONE),
}


# ---------------------------------------------------------------- primitives (append to build.Mesh)
def quad(m, a, b, c, d, color, kind=0):
    m.tris(np.array([[a, b, c], [a, c, d]]), color, kind)


def ring_prism(m, ring, z0, z1, color, top=True, top_color=None):
    """ring: (n,2) CCW convex polygon; walls + fan top."""
    r = np.asarray(ring, float)
    n = len(r)
    W = []
    for i in range(n):
        a, b = r[i], r[(i + 1) % n]
        W += [[[*a, z0], [*b, z0], [*b, z1]], [[*a, z0], [*b, z1], [*a, z1]]]
    m.tris(np.array(W), color, 0)
    if top:
        c = r.mean(0)
        m.tris(np.array([[[*c, z1], [*r[i], z1], [*r[(i + 1) % n], z1]] for i in range(n)]),
               color if top_color is None else top_color, 0)


def cone(m, ring, z0, apex, color):
    r = np.asarray(ring, float)
    c = r.mean(0)
    n = len(r)
    m.tris(np.array([[[*r[i], z0], [*r[(i + 1) % n], z0], [*c, apex]] for i in range(n)]), color, 0)


def ngon(cx, cy, rad, n=8, rot=0.0):
    a = rot + np.arange(n) * 2 * math.pi / n
    return np.stack([cx + rad * np.cos(a), cy + rad * np.sin(a)], 1)


def obox(c, u, hu, hv):
    """oriented rectangle ring (CCW) centred at c with unit axis u, half sizes hu (along u), hv."""
    v = np.array([-u[1], u[0]])
    return np.array([c - u * hu - v * hv, c + u * hu - v * hv, c + u * hu + v * hv, c - u * hu + v * hv])


def beam(m, p, q, w, color):
    """square beam between 3D points p and q."""
    p, q = np.asarray(p, float), np.asarray(q, float)
    d = q - p
    L = np.linalg.norm(d)
    if L < 1e-6:
        return
    d /= L
    a = np.cross(d, [0, 0, 1.0])
    if np.linalg.norm(a) < 1e-3:
        a = np.array([1.0, 0, 0])
    a /= np.linalg.norm(a)
    b = np.cross(a, d)
    h = w / 2
    cs = [(-1, -1), (1, -1), (1, 1), (-1, 1)]
    P = [p + (a * i + b * j) * h for i, j in cs]
    Q = [q + (a * i + b * j) * h for i, j in cs]
    for k in range(4):
        quad(m, P[k], P[(k + 1) % 4], Q[(k + 1) % 4], Q[k], color)
    quad(m, P[3], P[2], P[1], P[0], color)
    quad(m, Q[0], Q[1], Q[2], Q[3], color)


def dome(m, cx, cy, rad, z0, color, rise=None, nlat=6, nlon=16):
    rise = rad if rise is None else rise
    rings = []
    for i in range(nlat + 1):
        t = i / nlat * math.pi / 2
        rings.append((rad * math.cos(t), z0 + rise * math.sin(t)))
    T = []
    for i in range(nlat):
        (r0, z_0), (r1, z_1) = rings[i], rings[i + 1]
        for j in range(nlon):
            a0, a1 = 2 * math.pi * j / nlon, 2 * math.pi * (j + 1) / nlon
            p00 = [cx + r0 * math.cos(a0), cy + r0 * math.sin(a0), z_0]
            p01 = [cx + r0 * math.cos(a1), cy + r0 * math.sin(a1), z_0]
            p10 = [cx + r1 * math.cos(a0), cy + r1 * math.sin(a0), z_1]
            p11 = [cx + r1 * math.cos(a1), cy + r1 * math.sin(a1), z_1]
            T += [[p00, p01, p11], [p00, p11, p10]]
    m.tris(np.array(T), color, 0)


def wall_panel(m, a, u, nrm, s0, s1, z0, z1, color, off=0.06, pointed=False, arched=False):
    """flat panel on a wall: a = edge start (2D), u = edge direction, nrm = outward normal."""
    p0 = a + u * s0 + nrm * off
    p1 = a + u * s1 + nrm * off
    quad(m, [*p0, z0], [*p1, z0], [*p1, z1], [*p0, z1], color)
    w = s1 - s0
    if pointed:
        pm = (p0 + p1) / 2
        m.tris(np.array([[[*p0, z1], [*p1, z1], [*pm, z1 + w * 0.8]]]), color, 0)
    elif arched:
        k = 6
        pts = [(p0 + p1) / 2 + u * (w / 2) * math.cos(math.pi * i / k) for i in range(k + 1)]
        zs = [z1 + (w / 2) * math.sin(math.pi * i / k) for i in range(k + 1)]
        c = [*((p0 + p1) / 2), z1]
        m.tris(np.array([[c, [*pts[i], zs[i]], [*pts[i + 1], zs[i + 1]]] for i in range(k)]), color, 0)


def edges(poly, min_len=3.0):
    """exterior edges of a polygon (CCW) as (a, u, nrm, length), local frame given by poly coords."""
    p = poly.simplify(0.4)
    if p.geom_type != "Polygon":
        p = max(getattr(p, "geoms", [poly]), key=lambda q: q.area)
    r = np.asarray(p.exterior.coords)
    if not p.exterior.is_ccw:
        r = r[::-1]
    out = []
    for a, b in zip(r[:-1], r[1:]):
        d = b - a
        L = float(np.hypot(*d))
        if L >= min_len:
            u = d / L
            out.append((a, u, np.array([u[1], -u[0]]), L))
    return out


def bearing_vec(deg):
    return np.array([math.sin(math.radians(deg)), math.cos(math.radians(deg))])


# ---------------------------------------------------------------- context
class Ctx:
    """Per-landmark geometry from footprint + LiDAR."""

    def __init__(self, poly_local, dmed, base, top, DTM, DSM, tf, E0, N0):
        self.g = poly_local
        self.dmed, self.base, self.top = dmed, base, top
        rr = poly_local.minimum_rotated_rectangle
        c = np.asarray(rr.exterior.coords)[:4]
        e0, e1 = c[1] - c[0], c[2] - c[1]
        if np.hypot(*e0) >= np.hypot(*e1):
            self.u, self.L, self.W = e0 / np.hypot(*e0), np.hypot(*e0) / 2, np.hypot(*e1) / 2
        else:
            self.u, self.L, self.W = e1 / np.hypot(*e1), np.hypot(*e1) / 2, np.hypot(*e0) / 2
        self.v = np.array([-self.u[1], self.u[0]])
        self.c = c.mean(0)
        self.rect = obox(self.c, self.u, self.L, self.W)
        # nDSM cells inside the footprint (local coords of cell centres)
        x0, y0, x1, y1 = poly_local.bounds
        left, topy = tf.c, tf.f
        j0, j1 = int(x0 + E0 - left) - 1, int(x1 + E0 - left) + 2
        i0, i1 = int(topy - (y1 + N0)) - 1, int(topy - (y0 + N0)) + 2
        i0, j0 = max(i0, 0), max(j0, 0)
        import rasterio
        wtf = rasterio.transform.from_origin(left + j0 - E0, topy - i0 - N0, 1, 1)
        a, s = DTM[i0:i1, j0:j1], DSM[i0:i1, j0:j1]
        msk = geometry_mask([mapping(poly_local)], a.shape, wtf, invert=True) if a.size else np.zeros((0, 0), bool)
        jj, ii = np.meshgrid(np.arange(a.shape[1]), np.arange(a.shape[0]))
        self.cx = (left + j0 + jj + 0.5 - E0)[msk]
        self.cy = (topy - i0 - ii - 0.5 - N0)[msk]
        self.nd = (s - a)[msk] if a.size else np.zeros(0)
        self.ndmax = float(self.nd.max()) if len(self.nd) else top - dmed

    def front_edge(self, deg):
        f = bearing_vec(deg)
        es = edges(self.g, 4.0)
        return max(es, key=lambda e: (e[2] @ f) * min(e[3], 30)) if es else None

    def tower(self, min_cells=6):
        """Find the high compact blob (tower / spire) in the nDSM: returns (ring, top_p90, max, cells) or None."""
        if len(self.nd) < 10:
            return None
        p50, mx = float(np.median(self.nd)), self.ndmax
        if mx - p50 < 7:
            return None
        thr = p50 + 0.45 * (mx - p50)
        sel = self.nd > thr
        if sel.sum() < min_cells:
            return None
        # keep the blob around the maximum
        k = int(np.argmax(self.nd))
        d = np.hypot(self.cx - self.cx[k], self.cy - self.cy[k])
        sel &= d < 9
        pts = MultiPoint(list(zip(self.cx[sel], self.cy[sel])))
        rr = pts.buffer(0.6, cap_style=3).minimum_rotated_rectangle
        rr = rr.intersection(self.g.buffer(0.5))
        if rr.is_empty or rr.area < 4:
            return None
        rr = rr.minimum_rotated_rectangle
        ring = np.asarray(rr.exterior.coords)[:4]
        if not Polygon(ring).exterior.is_ccw:
            ring = ring[::-1]
        return ring, float(np.percentile(self.nd[sel], 80)), mx, int(sel.sum())

    def body_height(self, exclude_ring=None):
        nd = self.nd
        if exclude_ring is not None and len(nd):
            P = Polygon(exclude_ring).buffer(1.0)
            from shapely import vectorized
            inside = vectorized.contains(P, self.cx, self.cy)
            nd = nd[~inside]
        nd = nd[nd > 2.0] if len(nd) else nd
        return float(np.percentile(nd, 85)) if len(nd) > 5 else self.top - self.dmed


# ---------------------------------------------------------------- recipes
def roof_gable(m, ctx, z_eave, z_ridge, color):
    c, u, v, L, W = ctx.c, ctx.u, ctx.v, ctx.L, ctx.W
    A, B = c - u * L, c + u * L
    a0, a1, b0, b1 = A - v * W, A + v * W, B - v * W, B + v * W
    rA, rB = [*A, z_ridge], [*B, z_ridge]
    quad(m, [*a0, z_eave], [*b0, z_eave], rB, rA, color)
    quad(m, [*b1, z_eave], [*a1, z_eave], rA, rB, color)
    m.tris(np.array([[[*a1, z_eave], [*a0, z_eave], rA], [[*b0, z_eave], [*b1, z_eave], rB]]), ctx.wall, 0)


def pinnacle(m, x, y, z, h, rad, color):
    ring_prism(m, ngon(x, y, rad, 4, math.pi / 4), z - 0.2, z + h * 0.35, color, top=False)
    cone(m, ngon(x, y, rad, 4, math.pi / 4), z + h * 0.35, z + h, color)


def crenellate(deco, ctx, z, color, step=1.4):
    for a, u, nrm, L in edges(ctx.g, 2.0):
        n = int(L // step)
        for i in range(n):
            s = (i + 0.5) * L / n
            p = a + u * s - nrm * 0.25
            ring_prism(deco, obox(p, u, step * 0.25, 0.25), z, z + 0.8, color)


def tower_block(solid, deco, ctx, tw, spire=False, round_=False):
    ring, ttop, tmax, _ = tw
    z0 = ctx.base
    if round_:
        c = ring.mean(0)
        rad = 0.5 * min(np.hypot(*(ring[1] - ring[0])), np.hypot(*(ring[2] - ring[1])))
        circ = ngon(c[0], c[1], rad, 20)
        zt = ctx.dmed + ttop - 3.0
        ring_prism(solid, circ, z0, zt, ctx.wall, top=False)
        cone(solid, circ, zt, ctx.dmed + tmax, LEAD)
        for k in range(10):
            a = 2 * math.pi * (k + 0.5) / 10
            p0 = c + rad * np.array([math.cos(a), math.sin(a)])
            uu = np.array([-math.sin(a), math.cos(a)])
            wall_panel(deco, p0 - uu * 0.5, uu, np.array([math.cos(a), math.sin(a)]), 0, 1.0,
                       ctx.dmed + 2.5, ctx.dmed + 4.2, GLASS, off=0.05, arched=True)
        return
    if spire:
        zt = ctx.dmed + min(ttop, ctx.body_height(ring) + 8, tmax - 10)
        zt = max(zt, ctx.dmed + 6)
        ring_prism(solid, ring, z0, zt, ctx.wall, top=True)
        sr = ring.mean(0) + (ring - ring.mean(0)) * 0.85
        sp = ngon(*ring.mean(0), 0.85 * 0.5 * min(np.hypot(*(ring[1] - ring[0])), np.hypot(*(ring[2] - ring[1]))), 8,
                  math.pi / 8)
        cone(solid, sp, zt, ctx.dmed + tmax + 1.0, STONE_D)
        for p in sr:
            pinnacle(deco, p[0], p[1], zt, 3.0, 0.35, ctx.wall)
    else:
        zt = ctx.dmed + ttop
        ring_prism(solid, ring, z0, zt, ctx.wall, top=True, top_color=LEAD)
        for p in ring:
            q = ring.mean(0) + (p - ring.mean(0)) * 0.92
            pinnacle(deco, q[0], q[1], zt, max(2.0, tmax - ttop + 1.0), 0.45, ctx.wall)
        crenellate(deco, type("C", (), {"g": Polygon(ring)})(), zt, ctx.wall, 1.2)
    # belfry openings on every tower face
    for i in range(4):
        a, b = ring[i], ring[(i + 1) % 4]
        L = np.hypot(*(b - a))
        u = (b - a) / L
        nrm = np.array([u[1], -u[0]])
        zt_ = zt - 5.5
        for s0, s1 in ((0.2 * L, 0.45 * L), (0.55 * L, 0.8 * L)):
            wall_panel(deco, a, u, nrm, s0, s1, zt_, zt_ + 2.5, GLASS, pointed=not round_)


def gothic(solid, deco, ctx, sp):
    tw = ctx.tower() if sp.get("tower") else None
    hb = ctx.body_height(tw[0] if tw else None)
    if sp.get("turrets"):
        hb = float(np.percentile(ctx.nd, 80)) if len(ctx.nd) else hb
    zt = ctx.dmed + hb
    gabled = sp.get("roof") == "gable"
    z_eave = zt - min(0.35 * ctx.W, 6.0) if gabled else zt
    body = ctx.g
    from build import add_prism_local
    add_prism_local(solid, body, ctx.base, z_eave, ctx.wall, LEAD if not gabled else ctx.wall)
    if gabled:
        roof_gable(solid, ctx, z_eave, zt, LEAD if sp.get("wall") is not BRICK else TILE_R)
    elif sp.get("roof") == "lead_low":
        roof_gable(solid, ctx, z_eave - 0.1, z_eave + 1.6, LEAD)
    if tw:
        tower_block(solid, deco, ctx, tw, spire=sp.get("spire", False))
    if sp.get("turrets"):
        for p in ctx.rect:
            q = ctx.c + (p - ctx.c) * np.array([1, 1]) - (p - ctx.c) / np.linalg.norm(p - ctx.c) * 1.2
            ring_prism(solid, ngon(q[0], q[1], 2.0, 8, math.pi / 8), ctx.base, ctx.dmed + ctx.ndmax - 7.0, ctx.wall)
            crenellate(deco, type("C", (), {"g": Polygon(ngon(q[0], q[1], 2.0, 8, math.pi / 8))})(),
                       ctx.dmed + ctx.ndmax - 7.0, ctx.wall, 1.0)
            ring_prism(solid, ngon(q[0], q[1], 1.1, 8, math.pi / 8), ctx.dmed + ctx.ndmax - 7.0,
                       ctx.dmed + ctx.ndmax - 4.0, ctx.wall, top=False)
            cone(solid, ngon(q[0], q[1], 1.1, 8, math.pi / 8), ctx.dmed + ctx.ndmax - 4.0, ctx.dmed + ctx.ndmax, ctx.wall)
    if sp.get("crenel"):
        crenellate(deco, ctx, z_eave, ctx.wall)
    bs = sp.get("buttress", 4.5)
    for a, u, nrm, L in edges(ctx.g, 6.0):
        if bs:
            n = max(1, int(round(L / bs)))
            step = L / n
            for i in range(n + 1):
                s = min(max(i * step, 0.5), L - 0.5)
                p = a + u * s + nrm * 0.55
                ring_prism(deco, obox(p, u, 0.45, 0.55), ctx.base, z_eave - 1.0, ctx.wall)
                pinnacle(deco, p[0], p[1], z_eave - 1.0, 3.2, 0.3, ctx.wall)
            for i in range(n):
                s0, s1 = i * step + 0.22 * step, (i + 1) * step - 0.22 * step
                zb = ctx.dmed + (0.30 if sp.get("big_windows") else 0.35) * (z_eave - ctx.dmed)
                wall_panel(deco, a, u, nrm, s0, s1, zb, z_eave - 2.2 - 0.8 * (s1 - s0), GLASS, pointed=True)
        else:
            n = max(1, int(L // 4))
            for i in range(n):
                s = (i + 0.5) * L / n
                wall_panel(deco, a, u, nrm, s - 0.4, s + 0.4, ctx.dmed + 2.5, ctx.dmed + 4.0, GLASS, arched=True)
        if sp.get("gables") and L < ctx.W * 2.4:   # stepped/baroque gable on the short ends
            pm = a + u * L / 2 + nrm * 0.1
            for k, f in enumerate((0.8, 0.55, 0.3)):
                quad(deco, [*(pm - u * L * f / 2), zt + k * 1.2], [*(pm + u * L * f / 2), zt + k * 1.2],
                     [*(pm + u * L * f / 2), zt + (k + 1) * 1.2], [*(pm - u * L * f / 2), zt + (k + 1) * 1.2], ctx.wall)
    return {"features": ["tower" if tw else None, "spire" if sp.get("spire") and tw else None,
                         "turrets" if sp.get("turrets") else None, "buttresses" if bs else None, "windows",
                         "pinnacles", "crenellations" if sp.get("crenel") else None]}


def classical(solid, deco, ctx, sp):
    hb = ctx.body_height()
    zt = ctx.dmed + hb
    gabled = sp.get("roof") == "gable"
    z_eave = zt - min(0.3 * ctx.W, 4.0) if gabled else zt
    from build import add_prism_local
    add_prism_local(solid, ctx.g, ctx.base, z_eave, ctx.wall, LEAD)
    if gabled:
        roof_gable(solid, ctx, z_eave, zt, LEAD)
    # cornice
    from shapely.geometry import Polygon as P_
    add_prism_local(deco, ctx.g.buffer(0.35, join_style=2), z_eave - 1.0, z_eave - 0.55, ctx.wall, ctx.wall)
    feats = ["cornice", "windows"]
    pil = sp.get("pilaster", 3.6)
    storeys = max(1, int((z_eave - ctx.dmed - 1.5) // 4.2))
    fe = ctx.front_edge(sp.get("front", 90))
    for a, u, nrm, L in edges(ctx.g, 4.0):
        n = max(1, int(round(L / pil)))
        step = L / n
        for i in range(n + 1):
            s = min(max(i * step, 0.3), L - 0.3)
            p = a + u * s + nrm * 0.15
            ring_prism(deco, obox(p, u, 0.3, 0.15), ctx.base + 0.8, z_eave - 1.0, ctx.wall)
        is_front = fe is not None and np.allclose(a, fe[0])
        for k in range(storeys):
            zb = ctx.dmed + 1.4 + k * 4.2
            for i in range(n):
                s0, s1 = i * step + 0.3 * step, (i + 1) * step - 0.3 * step
                arched = (sp.get("arcade") and k == 0) or (sp.get("central_arch") and is_front and i == n // 2 and k == 0)
                wall_panel(deco, a, u, nrm, s0, s1, zb, zb + (2.6 if arched else 2.2), GLASS, arched=arched)
    if sp.get("balustrade"):
        feats.append("balustrade")
        for a, u, nrm, L in edges(ctx.g, 2.0):
            n = int(L // 0.6)
            for i in range(n):
                p = a + u * (i + 0.5) * L / n - nrm * 0.2
                ring_prism(deco, obox(p, u, 0.12, 0.12), z_eave, z_eave + 0.8, ctx.wall, top=False)
            p0, p1 = a - nrm * 0.2, a + u * L - nrm * 0.2
            beam(deco, [*p0, z_eave + 0.9], [*p1, z_eave + 0.9], 0.25, ctx.wall)
    if sp.get("statues"):
        feats.append("statues")
        a, u, nrm, L = fe
        for i in range(4):
            p = a + u * L * (i + 1) / 5 - nrm * 0.2
            ring_prism(deco, ngon(p[0], p[1], 0.3, 6), z_eave + 0.9, z_eave + 2.6, WHITE)
    if fe is not None and (sp.get("pediment") or sp.get("portico")):
        a, u, nrm, L = fe
        w = min(L * 0.6, 22.0)
        mid = a + u * L / 2
        out = 0.4
        if sp.get("portico"):
            nc = sp["portico"]
            depth = 4.0
            feats += ["portico", "columns"]
            zc = z_eave - 1.0
            for i in range(nc):
                p = mid + u * (-w / 2 + w * i / (nc - 1)) + nrm * (depth - 0.6)
                ring_prism(deco, ngon(p[0], p[1], 0.45, 10), ctx.dmed, zc, WHITE, top=False)
            # entablature
            ring_prism(deco, obox(mid + nrm * depth / 2, u, w / 2 + 0.7, depth / 2), zc, zc + 1.2, WHITE)
            quad(deco, [*(mid + nrm * 0.5 - u * (w / 2 + 0.7)), ctx.dmed + 0.05], [*(mid + nrm * depth - u * (w / 2 + 0.7)), ctx.dmed + 0.05],
                 [*(mid + nrm * depth + u * (w / 2 + 0.7)), ctx.dmed + 0.05], [*(mid + nrm * 0.5 + u * (w / 2 + 0.7)), ctx.dmed + 0.05], WHITE)
            out = depth
            zp = zc + 1.2
        else:
            zp = z_eave - 0.2
        feats.append("pediment")
        hp = w * 0.18
        L0, R0 = mid - u * (w / 2 + 0.7) + nrm * out, mid + u * (w / 2 + 0.7) + nrm * out
        L1, R1 = mid - u * (w / 2 + 0.7), mid + u * (w / 2 + 0.7)
        T0, T1 = mid + nrm * out, mid
        deco.tris(np.array([[[*L0, zp], [*R0, zp], [*T0, zp + hp]], [[*R1, zp], [*L1, zp], [*T1, zp + hp]]]), WHITE, 0)
        quad(deco, [*R0, zp], [*R1, zp], [*T1, zp + hp], [*T0, zp + hp], LEAD)
        quad(deco, [*L1, zp], [*L0, zp], [*T0, zp + hp], [*T1, zp + hp], LEAD)
    if sp.get("dome"):
        feats.append("dome")
        k = int(np.argmax(ctx.nd)) if len(ctx.nd) else None
        x, y = (ctx.cx[k], ctx.cy[k]) if k is not None else ctx.c
        zd = ctx.dmed + max(hb, ctx.ndmax - 5.0)
        ring_prism(solid, ngon(x, y, 5.0, 16), z_eave - 0.5, zd, ctx.wall, top=False)
        dome(solid, x, y, 5.0, zd, LEAD, rise=4.0)
    if sp.get("cupola"):
        feats += ["cupola", "lantern"]
        x, y = ctx.c
        z0 = zt if not gabled else zt - 0.5
        ring_prism(solid, ngon(x, y, 1.6, 8, math.pi / 8), z0, z0 + 2.5, WHITE, top=False)
        for i in range(8):
            a0 = math.pi / 8 + i * math.pi / 4
            pp = np.array([x, y]) + 1.62 * np.array([math.cos(a0 + math.pi / 8), math.sin(a0 + math.pi / 8)])
            uu = np.array([-math.sin(a0 + math.pi / 8), math.cos(a0 + math.pi / 8)])
            wall_panel(deco, pp - uu * 0.35, uu, np.array([math.cos(a0 + math.pi / 8), math.sin(a0 + math.pi / 8)]),
                       0, 0.7, z0 + 0.6, z0 + 1.8, GLASS, arched=True)
        dome(solid, x, y, 1.6, z0 + 2.5, LEAD, rise=1.6, nlat=4, nlon=8)
        ring_prism(solid, ngon(x, y, 0.15, 6), z0 + 4.0, z0 + 5.2, LEAD, top=False)
    if sp.get("curved_gables"):
        feats.append("curved gables")
        a, u, nrm, L = fe
        for f in (0.2, 0.8):
            pm = a + u * L * f + nrm * 0.1
            k = 8
            pts = [pm + u * 2.0 * math.cos(math.pi * i / k) for i in range(k + 1)]
            zs = [z_eave + 2.2 * math.sin(math.pi * i / k) for i in range(k + 1)]
            deco.tris(np.array([[[*pm, z_eave], [*pts[i + 1], zs[i + 1]], [*pts[i], zs[i]]] for i in range(k)]), ctx.wall, 0)
    return {"features": feats}


def brick_hall(solid, deco, ctx, sp):
    hb = ctx.body_height()
    zt = ctx.dmed + hb
    z_eave = zt - min(0.3 * ctx.W, 5.0)
    from build import add_prism_local
    add_prism_local(solid, ctx.g, ctx.base, z_eave, ctx.wall, TILE_R)
    roof_gable(solid, ctx, z_eave, zt, LEAD)
    for a, u, nrm, L in edges(ctx.g, 4.0):
        n = max(1, int(round(L / 3.5)))
        step = L / n
        for i in range(n + 1):
            s = min(max(i * step, 0.3), L - 0.3)
            ring_prism(deco, obox(a + u * s + nrm * 0.2, u, 0.35, 0.2), ctx.base, z_eave, STONE)
        for i in range(n):
            s0, s1 = i * step + 0.28 * step, (i + 1) * step - 0.28 * step
            wall_panel(deco, a, u, nrm, s0, s1, ctx.dmed + 1.2, ctx.dmed + 3.6, GLASS, arched=True)
            wall_panel(deco, a, u, nrm, s0, s1, ctx.dmed + 5.5, z_eave - 2.5, GLASS, arched=True)
    # roof lantern along the ridge
    ring_prism(solid, obox(ctx.c, ctx.u, ctx.L * 0.6, 1.5), zt - 0.8, zt + 0.6, GLASS)
    return {"features": ["pilasters", "arched windows", "roof lantern", "gable roof"]}


def round_church(solid, deco, ctx, sp):
    from build import add_prism_local
    tw = ctx.tower(min_cells=4)
    hb = float(np.percentile(ctx.nd[ctx.nd > 2], 50)) if (ctx.nd > 2).sum() > 5 else 7.0
    add_prism_local(solid, ctx.g, ctx.base, ctx.dmed + hb - 1.5, ctx.wall, ctx.wall)
    roof_gable(solid, ctx, ctx.dmed + hb - 1.5, ctx.dmed + hb + 0.5, TILE_R)
    if tw is None:
        k = int(np.argmax(ctx.nd))
        tw = (ngon(ctx.cx[k], ctx.cy[k], 6.0, 4), ctx.ndmax - 3, ctx.ndmax, 0)
    tower_block(solid, deco, ctx, tw, round_=True)
    return {"features": ["round nave", "conical roof", "round-arched windows"]}


def gate_tower(solid, deco, ctx, sp, gate_xy):
    """Trinity Great Gate: the range keeps its plain body; add the gate tower with four octagonal turrets."""
    if gate_xy is None:
        return None
    gx, gy = gate_xy
    # orient with the nearest footprint edge
    es = edges(ctx.g, 5.0)
    a, u, nrm, L = min(es, key=lambda e: Point(gx, gy).distance(Polygon([e[0], e[0] + e[1] * e[3], e[0] + e[1] * e[3] + 0.01 * e[2]]).buffer(0.01)))
    c = np.array([gx, gy])
    hu, hv = 6.0, 6.0
    ring = obox(c, u, hu, hv)
    ztop = ctx.dmed + max(ctx.ndmax - 4.0, 14.0)
    ring_prism(solid, ring, ctx.dmed + 4.0, ztop, ctx.wall, top=True, top_color=LEAD)
    feats = ["gate tower", "octagonal turrets", "windows", "crenellations"]
    for p in ring:
        q = c + (p - c) * 1.0
        oc = ngon(q[0], q[1], 1.6, 8, math.pi / 8)
        ring_prism(solid, oc, ctx.base, ztop + 3.5, ctx.wall, top=True, top_color=LEAD)
        crenellate(deco, type("C", (), {"g": Polygon(oc)})(), ztop + 3.5, ctx.wall, 0.9)
    crenellate(deco, type("C", (), {"g": Polygon(ring)})(), ztop, ctx.wall, 1.2)
    for i in range(4):
        a2, b2 = ring[i], ring[(i + 1) % 4]
        uu = (b2 - a2) / np.hypot(*(b2 - a2))
        nn = np.array([uu[1], -uu[0]])
        for k in range(2):
            wall_panel(deco, a2, uu, nn, 4.0, 8.0, ctx.dmed + 6.5 + k * 3.6, ctx.dmed + 8.7 + k * 3.6, GLASS)
        wall_panel(deco, a2, uu, nn, 4.6, 7.4, ctx.dmed + 0.0, ctx.dmed + 3.2, GLASS * 0.5, pointed=True)
    return {"features": feats}


def gate(solid, deco, ctx, sp):
    """Gate of Honour: piers, arch, entablature, hexagonal domed cupola with obelisks."""
    c, u, v, L, W = ctx.c, ctx.u, ctx.v, ctx.L, ctx.W
    z0 = ctx.dmed
    for s in (-1, 1):
        p = c + u * s * (L - 0.9)
        ring_prism(solid, obox(p, u, 0.9, W), ctx.base, z0 + 4.2, ctx.wall)
    ring_prism(solid, obox(c, u, L, W), z0 + 3.8, z0 + 5.0, ctx.wall)
    # arch soffit
    k = 8
    span = L - 1.8
    for i in range(k):
        a0, a1 = math.pi * i / k, math.pi * (i + 1) / k
        p0 = c + u * span * math.cos(a0); p1 = c + u * span * math.cos(a1)
        z_0, z_1 = z0 + 2.6 + 1.2 * math.sin(a0), z0 + 2.6 + 1.2 * math.sin(a1)
        for f in (-1, 1):
            deco.tris(np.array([[[*(p0 + v * f * (W + 0.03)), z_0], [*(p1 + v * f * (W + 0.03)), z_1],
                                 [*(p1 + v * f * (W + 0.03)), z0 + 3.85]],
                                [[*(p0 + v * f * (W + 0.03)), z_0], [*(p1 + v * f * (W + 0.03)), z0 + 3.85],
                                 [*(p0 + v * f * (W + 0.03)), z0 + 3.85]]]), ctx.wall, 0)
    hexr = ngon(c[0], c[1], 1.3, 6)
    ring_prism(solid, hexr, z0 + 5.0, z0 + 7.0, ctx.wall, top=False)
    dome(solid, c[0], c[1], 1.3, z0 + 7.0, LEAD, rise=1.2, nlat=4, nlon=6)
    for sgn in ((-1, -1), (-1, 1), (1, -1), (1, 1)):
        p = c + u * sgn[0] * (L - 0.5) + v * sgn[1] * (W - 0.3)
        cone(solid, ngon(p[0], p[1], 0.3, 4), z0 + 5.0, z0 + 7.2, ctx.wall)
    # sundial faces on the cupola
    for i in range(0, 6, 2):
        a, b = hexr[i], hexr[(i + 1) % 6]
        uu = (b - a) / np.hypot(*(b - a))
        wall_panel(deco, a, uu, np.array([uu[1], -uu[0]]), 0.25, 1.05, z0 + 5.3, z0 + 6.6, WHITE)
    return {"features": ["piers", "arch", "hexagonal cupola", "dome", "sundials", "obelisks"]}


def bridge(solid, deco, ctx, sp, deck_z):
    """Arched bridge: arch rings + spandrel walls under the deck, parapets, then gallery / truss / balls."""
    c, u, v, L, W = ctx.c, ctx.u, ctx.v, ctx.L, ctx.W
    zw = ctx.dmed - 0.3
    zd = deck_z
    feats = ["arches", "parapet"]
    nA = sp.get("arches", 1)
    col = ctx.wall
    if not sp.get("truss"):
        # piers/abutments and arches as faces on both sides plus soffits
        seg = 2 * L / nA
        for ai in range(nA):
            s0 = -L + ai * seg
            k = 10
            span = seg * 0.42
            mid = s0 + seg / 2
            rise = min(zd - zw - 0.8, span * 0.8)
            for i in range(k):
                a0, a1 = math.pi * i / k, math.pi * (i + 1) / k
                x0, x1 = mid + span * math.cos(a0), mid + span * math.cos(a1)
                z_0, z_1 = zw + rise * math.sin(a0), zw + rise * math.sin(a1)
                for f in (-1, 1):
                    P = lambda x, z: [*(c + u * x + v * f * W), z]
                    T = [[P(x0, z_0), P(x1, z_1), P(x1, zd)], [P(x0, z_0), P(x1, zd), P(x0, zd)]]
                    deco.tris(np.array(T)[:, ::(1 if f > 0 else -1)], col, 0)
                q = [[*(c + u * x0 - v * W), z_0], [*(c + u * x1 - v * W), z_1],
                     [*(c + u * x1 + v * W), z_1], [*(c + u * x0 + v * W), z_0]]
                quad(deco, q[3], q[2], q[1], q[0], STONE_D)
            # piers between arches
            for x_a, x_b in ((s0, mid - span), (mid + span, s0 + seg)):
                if x_b - x_a > 0.05:
                    for f in (-1, 1):
                        P = lambda x, z: [*(c + u * x + v * f * W), z]
                        quad(deco, *(P(x_a, zw), P(x_b, zw), P(x_b, zd), P(x_a, zd))[::(1 if f > 0 else -1)], col)
        # parapets
        for f in (-1, 1):
            p = c + v * f * (W - 0.2)
            ring_prism(deco, obox(p, u, L, 0.2), zd - 0.1, zd + 1.0, col)
        if sp.get("balls"):
            feats.append("stone balls")
            for f in (-1, 1):
                for i in range(7):
                    p = c + u * (-L + 0.4 + i * (2 * L - 0.8) / 6) + v * f * (W - 0.2)
                    ring_prism(deco, obox(p, u, 0.25, 0.25), zd + 1.0, zd + 1.5, col)
                    dome(deco, p[0], p[1], 0.35, zd + 1.5, col, nlat=3, nlon=8)
                    dome(deco, p[0], p[1], 0.35, zd + 1.5, col, rise=-0.0001, nlat=1, nlon=8)
    if sp.get("gallery"):
        feats += ["covered gallery", "tracery windows", "roof"]
        zr = zd + 3.4
        for f in (-1, 1):
            a = c - u * L * f + v * f * W
            uu, nn = u * f, v * f
            quad(deco, [*a, zd + 1.0], [*(a + uu * 2 * L), zd + 1.0], [*(a + uu * 2 * L), zr], [*a, zr], col)
            n = 5
            for i in range(n):
                s0 = (i + 0.2) * 2 * L / n
                s1 = (i + 0.8) * 2 * L / n
                wall_panel(deco, a, uu, nn, s0, s1, zd + 1.2, zr - 1.4, GLASS, pointed=True)
                pinnacle(deco, *(a + uu * i * 2 * L / n), zr, 1.6, 0.18, col)
        crenellate(deco, type("C", (), {"g": Polygon(ctx.rect)})(), zr, col, 1.0)
        quad(deco, [*(c - u * L - v * W), zr + 0.01], [*(c + u * L - v * W), zr + 0.01],
             [*(c + u * L + v * W), zr + 0.01], [*(c - u * L + v * W), zr + 0.01], LEAD)
    if sp.get("truss"):
        feats += ["timber truss", "radial and tangent members"]
        R = L * 1.15
        zc = zd - math.sqrt(max(R * R - L * L, 0.0)) - 0.0
        for f in (-1, 1):
            pts_in, pts_out = [], []
            k = 9
            for i in range(k + 1):
                x = -L + 2 * L * i / k
                zi = zc + math.sqrt(max(R * R - x * x, 0.0))
                pts_in.append([*(c + u * x + v * f * (W - 0.15)), zi - 0.6])
                pts_out.append([*(c + u * x + v * f * (W - 0.15)), zi + 0.9])
            for i in range(k):
                beam(deco, pts_in[i], pts_in[i + 1], 0.25, col)
                beam(deco, pts_out[i], pts_out[i + 1], 0.2, col)
                beam(deco, pts_in[i], pts_out[i + 1], 0.16, col)
                beam(deco, pts_out[i], pts_in[i + 1], 0.16, col)
            for i in range(k + 1):
                beam(deco, pts_in[i], pts_out[i], 0.18, col)
            # posts down to the abutments
            for i in (0, k):
                beam(deco, pts_in[i], [pts_in[i][0], pts_in[i][1], zw], 0.35, col)
        # cross beams under the deck
        for i in range(10):
            x = -L + 2 * L * (i + 0.5) / 10
            zi = zc + math.sqrt(max(R * R - x * x, 0.0)) - 0.7
            beam(deco, [*(c + u * x - v * W), zi], [*(c + u * x + v * W), zi], 0.2, col)
    return {"features": feats}
