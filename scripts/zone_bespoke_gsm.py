"""Bespoke geometry for Great St Mary's, the University Church (OSM way/26344507; Perpendicular, 1478-1608), session 31.

zone_build.load_bespoke() picks up BUILDS. Modelled from general knowledge / Wikimedia Commons (category "Church of
St Mary the Great, Cambridge"); heights from the LiDAR DSM (data/lidar/dsm_1m.tif) sampled over the footprint.

Layout (building frame: s east along the nave from the SW corner, t north; the footprint is a clean rectangle):
- west tower at s -0.9..9.3, t 4.9..15.3, rising from the west front (aisles run west alongside it);
- nave + clerestory t 4.9..14.7, s 9.3..35.5; north aisle t 14.7..21.6, south aisle t 0..4.9 (+ south porch);
- chancel s 35.5..41.7, t 6.4..14.1 with a big east window.
Heights above the datum Z0 = 9.5 m (LiDAR): aisle battlements 9.9 (DSM 19.3), chancel 11.3 (20.8), clerestory
battlements 15.8 / nave roof ridge 16.4 (25.2-26.4), tower battlements 29.0 (38.2-38.9), corner pinnacles 33.0 (42.6).
Pale buff limestone ashlar ("stone"), lead roofs, dark glass. Everything sits SK proud of the OSM wall line so it
covers the tile landmark body.
"""
import math
import os
import sys

import numpy as np
from shapely.geometry import Polygon, box
from shapely.ops import unary_union

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import facade_parts as F  # noqa: E402

OSM = "way/26344507"
Z0 = 9.5
SK = 0.35
REV = 0.45
STONE = F.rgb("#cfc2a0")
STONE_D = F.shade(STONE, 0.72)
STONE_L = F.shade(STONE, 1.06)
GLASS = F.rgb(F.GLASS_COL)
LEAD = F.rgb("#7d8286")
LOUVRE = F.rgb("#4a4440")
DOOR = F.rgb("#3b2a20")

# building frame (from the walls: SW corner = way/26344507:3 p1, east along the south aisle wall)
O = np.array([-170.68, 48.11])
U = np.array([0.99468521, 0.10296273])
V = np.array([-U[1], U[0]])

H_AISLE = 9.9      # aisle battlement top
H_CHAN = 11.3
H_CLER = 15.8      # clerestory battlement top
H_RIDGE = 16.4
H_TOWER = 29.0     # tower battlement top
H_PIN = 33.0       # corner pinnacle tips
T_TOWER = (-0.9, 9.3, 4.9, 15.3)   # s0, s1, t0, t1
T_NAVE = (4.9, 14.7)


def L2W(s, t):
    return O + s * U + t * V


def P_():
    return F.Parts(mat="stone", wall_col=STONE)


# ------------------------------------------------------------------ elements (wall frame: x along, y out, z up)

def perp_shape(xc, w, zb, zt):
    """Perpendicular four-centred window head."""
    hh = min(0.32 * w, 0.45 * (zt - zb))
    zs = zt - hh
    x0, x1 = xc - w / 2, xc + w / 2
    return Polygon([(x0, zb), (x1, zb), (x1, zs), (x1 - 0.1 * w, zs + 0.5 * hh), (xc + 0.22 * w, zs + 0.88 * hh),
                    (xc, zt), (xc - 0.22 * w, zs + 0.88 * hh), (x0 + 0.1 * w, zs + 0.5 * hh), (x0, zs)])


def window(P, xc, w, zb, zt, y, lights=4, transoms=1, louvre=False):
    """Recessed traceried window (reveals, glass, mullions running up into the head, transom, label mould, sill).
    Returns the opening polygon to cut from the wall face."""
    op = perp_shape(xc, w, zb, zt)
    yg = y - REV
    P.sides_xz(op, yg, y, STONE_D, inward=True, mat="stone")
    P.face_xz(op, yg, LOUVRE if louvre else GLASS, mat="trim" if louvre else "glass")
    mw = 0.11
    strips = [op.difference(op.buffer(-0.09, join_style=2))]
    for i in range(1, lights):
        x = xc - w / 2 + w * i / lights
        strips.append(box(x - mw / 2, zb, x + mw / 2, zt).intersection(op))
    zs = zt - min(0.32 * w, 0.45 * (zt - zb))
    for j in range(1, transoms + 1):
        z = zb + (zs - zb) * j / (transoms + 1)
        strips.append(box(xc - w / 2, z - 0.06, xc + w / 2, z + 0.06))
    # head: a sub-arch springing line and two inner arches (Perpendicular panel tracery, simplified)
    strips.append(box(xc - w / 2, zs - 0.05, xc + w / 2, zs + 0.05))
    if lights >= 3:
        inner = perp_shape(xc, w * 0.5, zs - 0.4, zt - 0.25)
        strips.append(inner.difference(inner.buffer(-0.07, join_style=2)).intersection(op))
    tr = unary_union(strips).intersection(op)
    if louvre:   # belfry: horizontal louvre boards behind the tracery
        z = zb + 0.25
        while z < zs:
            P.extrude_profile([(yg + 0.05, z), (yg + 0.25, z - 0.12), (yg + 0.25, z - 0.06), (yg + 0.05, z + 0.08)],
                              xc - w / 2, xc + w / 2, LOUVRE, mat="timber")
            z += 0.3
    P.slab(tr, yg, yg + 0.14, STONE_L, mat="stone")
    # label (hood) mould over the head and down to the springing
    lab = op.buffer(0.16, join_style=2).difference(op).intersection(box(xc - w, zs - 0.45, xc + w, zt + 1))
    P.slab(lab, y, y + 0.1, STONE_L, mat="stone")
    P.extrude_profile([(y - 0.05, zb - 0.18), (y + 0.16, zb - 0.18), (y + 0.16, zb - 0.1), (y - 0.05, zb + 0.02)],
                      xc - w / 2 - 0.12, xc + w / 2 + 0.12, STONE_L, mat="stone")
    return op


def door(P, xc, w, h, y, depth=0.6):
    op = perp_shape(xc, w, 0, h)
    P.sides_xz(op, y - depth, y, STONE_D, inward=True, skip_ground=True, mat="stone")
    P.face_xz(op, y - depth, DOOR, mat="timber")
    for k in range(3):   # moulded orders stepping out
        ring = op.buffer(0.14 * (k + 1), join_style=2).difference(op.buffer(0.14 * k, join_style=2))
        ring = ring.intersection(box(xc - w, 0, xc + w, h + 2))
        P.slab(ring, y - depth * (2 - k) / 3, y - depth * (2 - k) / 3 + 0.08, STONE_L, mat="stone")
    # square label over the arch (Perpendicular door frame) with spandrels
    P.slab(box(xc - w / 2 - 0.55, h + 0.3, xc + w / 2 + 0.55, h + 0.5), y, y + 0.12, STONE_L, mat="stone")
    for s in (-1, 1):
        P.slab(box(xc + s * (w / 2 + 0.45) - 0.1, h - 0.9, xc + s * (w / 2 + 0.45) + 0.1, h + 0.3), y, y + 0.12,
               STONE_L, mat="stone")
    return op


def buttress(P, x, y, ztop, d0=1.1, bw=0.75, setoffs=(0.45, 0.7)):
    """Buttress with sloped set-offs: projects d0 at the bottom, steps back at the given fractions of ztop."""
    za, zb = ztop * setoffs[0], ztop * setoffs[1]
    d1, d2 = d0 * 0.7, d0 * 0.42
    prof = [(y - 0.05, -0.9), (y + d0, -0.9), (y + d0, za), (y + d1, za + 0.35), (y + d1, zb), (y + d2, zb + 0.35),
            (y + d2, ztop), (y - 0.05, ztop + d2 * 1.1)]
    P.extrude_profile(prof, x - bw / 2, x + bw / 2, STONE, mat="stone")


def pinnacle(P, x, y, z, h=2.2, r=0.26):
    """Square pinnacle (shaft + pyramid) centred at (x, y) standing on z."""
    zs = z + 0.42 * h
    P.box(x - r, x + r, y - r, y + r, z, zs, STONE, bottom=False, mat="stone")
    top = (x, y, z + h)
    c = [(x - r - 0.05, y - r - 0.05), (x + r + 0.05, y - r - 0.05), (x + r + 0.05, y + r + 0.05),
         (x - r - 0.05, y + r + 0.05)]
    for i in range(4):
        a, b = c[i], c[(i + 1) % 4]
        n = np.array([b[1] - a[1], -(b[0] - a[0]), 0.4])
        P.add([[(a[0], a[1], zs), (b[0], b[1], zs), top]], n, STONE_L, mat="stone")
    P.box(x - r - 0.06, x + r + 0.06, y - r - 0.06, y + r + 0.06, zs - 0.08, zs, STONE_L, mat="stone")   # collar


def battlement(P, x0, x1, y, zp, zt, merlon=0.8, gap=0.55, thick=0.4):
    """Embattled parapet from zp to zt at the wall plane y (front face at y, back face at y - thick)."""
    zc = zp + 0.55 * (zt - zp)
    pts = [box(x0, zp, x1, zc)]
    n = max(1, int((x1 - x0 + gap) // (merlon + gap)))
    pad = (x1 - x0 - n * merlon - (n - 1) * gap) / 2
    for i in range(n):
        a = x0 + pad + i * (merlon + gap)
        pts.append(box(a, zc - 0.01, a + merlon, zt))
    g = unary_union(pts)
    P.slab(g, y - thick, y, STONE, mat="stone")
    P.face_xz(g, y - thick, STONE_D, n=(0, -1, 0), mat="stone")
    # moulded string course with the coping below the parapet
    P.extrude_profile([(y - 0.05, zp - 0.3), (y + 0.12, zp - 0.3), (y + 0.22, zp - 0.12), (y + 0.22, zp),
                       (y - 0.05, zp)], x0, x1, STONE_L, mat="stone")


def wall(P, x0, x1, y, z1, holes, zfoot=-0.9):
    g = box(x0, zfoot, x1, z1)
    if holes:
        g = g.difference(unary_union(holes))
    P.face_xz(g, y, STONE, mat="stone")
    for x, nx in ((x0, -1), (x1, 1)):   # end returns back behind the wall line
        P.quad((x, y - SK - 0.4, zfoot), (x, y, zfoot), (x, y, z1), (x, y - SK - 0.4, z1), (nx, 0, 0), STONE,
               mat="stone")
    # chamfered plinth
    P.extrude_profile([(y - 0.05, zfoot), (y + 0.3, zfoot), (y + 0.3, 0.45), (y + 0.05, 0.7), (y - 0.05, 0.7)],
                      x0, x1, STONE_D, mat="stone")


# ------------------------------------------------------------------ elevations

def elevation(L, H, nb, win_w, zb, zt, lights, butt=True, ext=(SK, SK), extra_holes=None, pins=True):
    """Generic embattled Perpendicular wall: nb window bays between buttresses, parapet H-1.0..H."""
    P = P_()
    y = SK
    x0, x1 = -ext[0], L + ext[1]
    zp = H - 1.05
    holes = list(extra_holes or [])
    bay = L / max(nb, 1)
    for i in range(nb):
        holes.append(window(P, bay * (i + 0.5), min(win_w, bay - 1.3), zb, zt, y, lights))
    wall(P, x0, x1, y, zp, holes)
    battlement(P, x0, x1, y, zp, H)
    if butt:
        xs = [bay * i for i in range(nb + 1)]
        for k, x in enumerate(xs):
            x = min(max(x, 0.45), L - 0.45)
            buttress(P, x, y, zp - 0.6)
            if pins:
                pinnacle(P, x, y + 0.1, H - 0.6, 2.0)
    return P


def frame_world(P, p0, d, name, z0=Z0):
    T, N, C = P.arrays()
    if not len(T):
        return None
    M = P.mats()
    n = np.array([d[1], -d[0]])
    X = p0[0] + T[..., 0] * d[0] + T[..., 1] * n[0]
    Y = p0[1] + T[..., 0] * d[1] + T[..., 1] * n[1]
    W = np.stack([X, Y, z0 + T[..., 2]], -1)
    Nw = np.stack([N[:, 0] * d[0] + N[:, 1] * n[0], N[:, 0] * d[1] + N[:, 1] * n[1], N[:, 2]], -1)
    g = np.cross(W[:, 1] - W[:, 0], W[:, 2] - W[:, 0])
    flip = (g * Nw).sum(1) < 0
    W[flip] = W[flip][:, ::-1]
    return {"name": name, "tris": W, "col": np.clip(C, 0, 1), "mat": M}


def seg(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    L = float(np.linalg.norm(b - a))
    return a, (b - a) / L, L


def on_local(P, A, B, name, z0=Z0):
    p0, d, _ = seg(L2W(*A), L2W(*B))
    return frame_world(P, p0, d, name, z0)


# ------------------------------------------------------------------ parts

def tower():
    s0, s1, t0, t1 = T_TOWER
    corners = [(s0, t0), (s1, t0), (s1, t1), (s0, t1)]   # CCW: S, E, N, W faces
    out = []
    for i in range(4):
        A, B = corners[i], corners[(i + 1) % 4]
        L = math.dist(A, B)
        west = i == 3
        P = P_()
        y = SK
        xc = L / 2
        z_low = H_AISLE - 0.2 if i in (0, 2) else (0.0 if west else H_CLER - 0.4)   # below this the aisles/nave hide it
        holes = []
        if west:
            holes.append(door(P, xc, 2.0, 3.6, y))
            holes.append(window(P, xc, 4.2, 5.6, 13.6, y, lights=5, transoms=1))
        if i != 1:   # small ringing-chamber window (not on the east face, roof crease)
            holes.append(window(P, xc, 1.3, 15.6, 18.0, y, lights=2, transoms=0))
        for xo in (-1.35, 1.35):   # belfry: two 2-light louvred openings per face
            holes.append(window(P, xc + xo, 1.75, 20.0, 25.4, y, lights=2, transoms=1, louvre=True))
        zp = H_TOWER - 1.25
        g = box(-SK, L + SK, z_low - 0.9 if not west else -0.9, zp)
        g = g.difference(unary_union(holes))
        P.face_xz(g, y, STONE, mat="stone")
        if west:
            P.extrude_profile([(y - 0.05, -0.9), (y + 0.3, -0.9), (y + 0.3, 0.45), (y + 0.05, 0.7), (y - 0.05, 0.7)],
                              -SK, L + SK, STONE_D, mat="stone")
        for zc in (14.8, 19.4, 26.3):   # string courses between stages
            if zc > z_low:
                P.extrude_profile([(y - 0.05, zc - 0.22), (y + 0.15, zc - 0.22), (y + 0.24, zc), (y - 0.05, zc + 0.05)],
                                  -SK, L + SK, STONE_L, mat="stone")
        battlement(P, -SK, L + SK, y, zp, H_TOWER, merlon=0.9, gap=0.6)
        # clasping corner buttresses (stepped), rising to the turrets
        for x in (0.15, L - 0.15):
            zb0 = z_low - 0.9 if not west else -0.9
            for (za, zb_, dp, bw) in ((zb0, 14.8, 0.75, 1.5), (14.8, 22.5, 0.5, 1.3)):
                if zb_ <= zb0:
                    continue
                za = max(za, zb0)
                P.extrude_profile([(y - 0.05, za), (y + dp, za), (y + dp, zb_ - 0.3), (y - 0.05, zb_ + 0.2)],
                                  x - bw / 2, x + bw / 2, STONE, mat="stone")
        out.append(on_local(P, A, B, "gsm:tower%d" % i))
    # octagonal corner turrets rising above the battlements, crowned with tall pinnacles
    P = F.Parts(mat="stone", wall_col=STONE)
    tris = []
    for (s, t) in corners:
        cs, ct = s + (0.25 if s < 5 else -0.25), t + (0.25 if t < 10 else -0.25)
        c = L2W(cs, ct)
        r = 0.85
        ang = [math.pi / 8 + k * math.pi / 4 for k in range(8)]
        ring = [(c[0] + r * math.cos(a), c[1] + r * math.sin(a)) for a in ang]
        ring2 = [(c[0] + (r + 0.12) * math.cos(a), c[1] + (r + 0.12) * math.sin(a)) for a in ang]
        za, zb, zc = Z0 + 22.5, Z0 + H_TOWER + 1.4, Z0 + H_PIN
        for k in range(8):
            a, b = ring[k], ring[(k + 1) % 8]
            tris += [[(a[0], a[1], za), (b[0], b[1], za), (b[0], b[1], zb)], [(a[0], a[1], za), (b[0], b[1], zb),
                                                                            (a[0], a[1], zb)]]
            a2, b2 = ring2[k], ring2[(k + 1) % 8]
            for (z1, z2) in ((zb - 0.0, zb + 0.35), (Z0 + 26.1, Z0 + 26.4)):   # cap moulding + string ring
                tris += [[(a2[0], a2[1], z1), (b2[0], b2[1], z1), (b2[0], b2[1], z2)],
                         [(a2[0], a2[1], z1), (b2[0], b2[1], z2), (a2[0], a2[1], z2)]]
            tris += [[(a2[0], a2[1], zb + 0.35), (b2[0], b2[1], zb + 0.35), (c[0], c[1], zb + 0.35)]]
            # spirelet with crockets (small ribs)
            tris += [[(a[0], a[1], zb + 0.35), (b[0], b[1], zb + 0.35), (c[0], c[1], zc)]]
        # small battlement-height pinnacles between: one finial ball
        for k in range(4):
            a = math.pi / 4 + k * math.pi / 2
            px, py = c[0] + 0.55 * math.cos(a), c[1] + 0.55 * math.sin(a)
            for (z1, z2) in ((zb + 1.0, zb + 1.25),):
                q = 0.09
                tris += [[(px - q, py, z1), (px + q, py, z1), (px, py, z2)], [(px, py - q, z1), (px, py + q, z1),
                                                                            (px, py, z2)]]
    T = np.asarray(tris, float)
    col = np.tile(STONE, (len(T), 1))
    # orient outward from each turret axis
    cen = []
    for (s, t) in corners:
        cs, ct = s + (0.25 if s < 5 else -0.25), t + (0.25 if t < 10 else -0.25)
        cen.append(L2W(cs, ct))
    cen = np.asarray(cen)
    m = T.mean(1)
    k = np.argmin(((m[:, None, :2] - cen[None]) ** 2).sum(-1), 1)
    g = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
    outv = np.c_[m[:, :2] - cen[k], np.zeros(len(T))]
    outv[:, 2] = 0.3
    flip = (g * outv).sum(1) < 0
    T[flip] = T[flip][:, ::-1]
    out.append({"name": "gsm:turrets", "tris": T, "col": col, "mat": "stone"})
    # tower roof (lead, flat behind the battlements)
    p = [L2W(s, t) for (s, t) in corners]
    zr = Z0 + H_TOWER - 1.2
    out.append({"name": "gsm:tower_roof", "tris": np.array([[(*p[0], zr), (*p[1], zr), (*p[2], zr)],
                                                            [(*p[0], zr), (*p[2], zr), (*p[3], zr)]]),
                "col": LEAD, "mat": "plain"})
    return out


def clerestory():
    s0, s1 = T_TOWER[1], 35.5
    t0, t1 = T_NAVE
    L = s1 - s0
    out = []
    for name, A, B in (("cler_s", (s0, t0), (s1, t0)), ("cler_n", (s1, t1), (s0, t1))):
        P = P_()
        y = SK
        zp = H_CLER - 0.9
        nb = 10
        holes = [window(P, L * (i + 0.5) / nb, 1.75, 10.7, 14.2, y, lights=2, transoms=0) for i in range(nb)]
        wall(P, -0.2, L + SK, y, zp, holes, zfoot=H_AISLE - 1.6)
        battlement(P, -0.2, L + SK, y, zp, H_CLER, merlon=0.7, gap=0.5)
        for i in range(0, nb + 1, 2):   # pinnacles on the bay divisions (5 bays)
            x = min(max(L * i / nb, 0.4), L - 0.3)
            P.box(x - 0.2, x + 0.2, y - 0.05, y + 0.25, H_AISLE - 0.8, zp, STONE, mat="stone")   # shallow pilaster
            pinnacle(P, x, y + 0.05, H_CLER - 0.5, 1.9, 0.22)
        out.append(on_local(P, A, B, "gsm:" + name))
    # nave east gable wall above the chancel roof
    P = P_()
    W = t1 - t0
    zp = H_CLER - 0.9
    g = box(-SK, W + SK, H_CHAN - 1.0, zp)
    P.face_xz(g, SK, STONE, mat="stone")
    battlement(P, -SK, W + SK, SK, zp, H_CLER, merlon=0.7, gap=0.5)
    for x in (0.2, W - 0.2):
        pinnacle(P, x, SK, H_CLER - 0.4, 2.4, 0.3)
    out.append(on_local(P, (s1, t0), (s1, t1), "gsm:nave_east"))
    # lead roofs: low-pitched nave roof (ridge on the axis), lean-to aisle roofs
    tris, cols = [], []
    sa, sb = s0 - 0.1, s1 + 0.1
    tm = (t0 + t1) / 2
    ze, zr = Z0 + H_CLER - 0.85, Z0 + H_RIDGE
    for (ta, za_, tb, zb_) in ((t0 - 0.05, ze, tm, zr), (t1 + 0.05, ze, tm, zr),
                               (-SK + 0.1, Z0 + H_AISLE - 1.1, t0, Z0 + H_AISLE - 0.2),
                               (21.6 + SK - 0.1, Z0 + H_AISLE - 1.1, t1, Z0 + H_AISLE - 0.2)):
        a, b, c, d = (*L2W(sa, ta), za_), (*L2W(sb, ta), za_), (*L2W(sb, tb), zb_), (*L2W(sa, tb), zb_)
        tris += [[a, b, c], [a, c, d]]
    T = np.asarray(tris, float)
    g = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
    T[g[:, 2] < 0] = T[g[:, 2] < 0][:, ::-1]
    out.append({"name": "gsm:roofs", "tris": T, "col": LEAD, "mat": "plain"})
    return out


def porch():
    """South porch (s 8.3..11.7, t -2.85..0): embattled, with a doorway on the south face."""
    out = []
    a, b, c = (8.3, -2.85), (11.7, -2.85), (11.7, 0.0)
    H = 7.0
    P = P_()
    L = b[0] - a[0]
    holes = [door(P, L / 2, 1.7, 3.3, SK)]
    holes.append(window(P, L / 2, 1.0, 4.4, 5.6, SK, lights=1, transoms=0))   # niche over the door
    wall(P, -SK, L + SK, SK, H - 1.0, holes)
    battlement(P, -SK, L + SK, SK, H - 1.0, H, merlon=0.55, gap=0.4)
    for x in (0.1, L - 0.1):
        buttress(P, x, SK, H - 1.6, d0=0.8, bw=0.55)
        pinnacle(P, x, SK + 0.1, H - 0.5, 1.6, 0.2)
    out.append(on_local(P, a, b, "gsm:porch_s"))
    P = P_()
    wall(P, -SK, 2.85, SK, H - 1.0, [])
    battlement(P, -SK, 2.85, SK, H - 1.0, H, merlon=0.55, gap=0.4)
    out.append(on_local(P, b, c, "gsm:porch_e"))
    p = [L2W(*q) for q in ((8.3, -2.85), (11.7, -2.85), (11.7, 0.0), (8.3, 0.0))]
    zr = Z0 + H - 1.1
    out.append({"name": "gsm:porch_roof", "tris": np.array([[(*p[0], zr), (*p[1], zr), (*p[2], zr)],
                                                            [(*p[0], zr), (*p[2], zr), (*p[3], zr)]]),
                "col": LEAD, "mat": "plain"})
    return out


def build(walls):
    by = {w["id"].split(":")[1]: w for w in walls}
    out = []

    def wall_el(k, P, name=None):
        w = by.get(k)
        if w is None:
            return
        p0, d, _ = seg(w["p0"], w["p1"])
        out.append(frame_world(P, p0, d, "gsm:" + (name or k)))

    def L_(k):
        return by[k]["length"] if k in by else 0
    # aisles: north (5 bays + 2 beside the tower), south (4 bays + 2 beside the tower)
    wall_el("0", elevation(L_("0"), H_AISLE, 5, 3.2, 2.5, 7.9, 4))
    wall_el("1", elevation(L_("1"), H_AISLE, 2, 2.6, 2.5, 7.9, 3))
    wall_el("9", elevation(L_("9"), H_AISLE, 4, 3.2, 2.5, 7.9, 4))
    wall_el("10", elevation(L_("10"), H_AISLE, 0, 0, 0, 0, 0, butt=False))
    wall_el("4", elevation(L_("4"), H_AISLE, 2, 2.6, 2.5, 7.9, 3))
    wall_el("5", elevation(L_("5"), 7.0, 0, 0, 0, 0, 0, butt=False, ext=(SK, -0.2)))
    # west front: aisle ends either side of the tower (wall 2 runs t 21.76 -> 10.39, wall 3 t 10.39 -> 0)
    if "2" in by and "3" in by:
        t_n = 21.76 - T_TOWER[3]                     # north aisle end width (along wall 2 from its start)
        P = elevation(t_n, H_AISLE, 1, 2.6, 2.5, 7.9, 3, butt=False, ext=(SK, 0.0))
        buttress(P, 0.45, SK, H_AISLE - 1.65)
        wall_el("2", P, "west_n")
        P = elevation(T_TOWER[2], H_AISLE, 1, 2.4, 2.5, 7.9, 3, butt=False, ext=(0.0, SK))
        buttress(P, T_TOWER[2] - 0.45, SK, H_AISLE - 1.65)
        w3 = by["3"]
        p0, d, _ = seg(L2W(0.0, T_TOWER[2]), w3["p1"])
        out.append(frame_world(P, p0, d, "gsm:west_s"))
    # east end: aisle ends, chancel sides, east window
    wall_el("11", elevation(L_("11"), H_AISLE, 1, 3.0, 2.5, 7.9, 3, butt=False))
    wall_el("16", elevation(L_("16"), H_AISLE, 1, 3.0, 2.5, 7.9, 3, butt=False))
    wall_el("12", elevation(L_("12"), H_CHAN, 1, 2.8, 3.2, 9.0, 3, butt=False))
    wall_el("15", elevation(L_("15"), H_CHAN, 1, 2.8, 3.2, 9.0, 3, butt=False))
    if "13" in by and "14" in by:
        p0, d, L = seg(by["13"]["p0"], by["14"]["p1"])
        P = elevation(L, H_CHAN, 1, 4.6, 2.6, 9.9, 5, butt=False)
        for x in (0.3, L - 0.3):
            buttress(P, x, SK, H_CHAN - 1.6, d0=1.0, bw=0.7)
            pinnacle(P, x, SK + 0.1, H_CHAN - 0.6, 2.2)
        out.append(frame_world(P, p0, d, "gsm:east"))
        zr = Z0 + H_CHAN - 1.1
        q = [L2W(*a) for a in ((35.5, 6.4), (41.68 + SK, 6.4), (41.68 + SK, 14.07), (35.5, 14.07))]
        out.append({"name": "gsm:chancel_roof", "tris": np.array([[(*q[0], zr), (*q[1], zr), (*q[2], zr)],
                                                                  [(*q[0], zr), (*q[2], zr), (*q[3], zr)]]),
                    "col": LEAD, "mat": "plain"})
    out += clerestory()
    out += tower()
    out += porch()
    return [o for o in out if o is not None]


BUILDS = {OSM: build}
HIDE_TILE = [OSM]   # the tile body is a plain box up to the clerestory; this model is complete

if __name__ == "__main__":
    import json
    W = json.load(open(os.path.join(os.path.dirname(__file__), "..", "data/annotations/market_square/walls.json")))["walls"]
    items = build([w for w in W if w["osm_id"] == OSM])
    for it in items:
        print(it["name"], len(it["tris"]), round(float(np.asarray(it["tris"])[..., 2].max()), 2))
    print("total", sum(len(i["tris"]) for i in items))
