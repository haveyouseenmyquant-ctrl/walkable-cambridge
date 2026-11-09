"""Bespoke geometry for King's College Chapel (OSM way/164848633; 1446-1515, Perpendicular Gothic), session 54.
Until now the chapel was the generic detail.py landmark on the tile body: from King's Parade it read as a plain grey
block with one pinnacle. This module models it as real 3D geometry and hides the tile body (HIDE_TILE).

Frame: u along the chapel from the midpoint of the west turret pair to the midpoint of the east pair (OSM turret
circles, BNG E 544684.25 N 258388.55 -> E 544777.80 N 258401.30, 94.4 m, 7.76 deg north of east); v north. From the
OSM footprint in this frame: main walls at v -8.0 / +7.8 over u 0..94.1 (west / east end walls), corner turret circles
r ~1.9 at the four corners, chantry chapels between the buttresses out to v -11.8 / +11.6 over u 10.7..86.

Design from Wikimedia Commons (references for shape and proportion only, no pixels used): category "King's College
Chapel, Cambridge" exterior views (Txllxt TxllxT "Cambridge - King's Parade - View NW on Neo Gothic Gatehouse 1828 by
William Wilkins & King's College Chapel 1446-1544", and the south-side and east-end views in the same category,
CC BY-SA 4.0 / 3.0). 12 bays a side; buttresses between them with crocketed pinnacles above the parapet (22 in all with
the turret-flanked ends counted as in the guide books); five-light windows with two transoms and panel tracery in
four-centred heads; low chantry chapels between the buttresses with four-light windows and battlements; pierced
battlemented parapet; huge nine-light east and west windows; four octagonal corner turrets with panelled stages,
battlemented crowns with pinnacles and crocketed ogee caps; west door under the west window. Pale Clipsham / Weldon
limestone; low-pitched lead roof.
Heights from the EA 2023 LiDAR (nlp2023 DSM and first-return DSM; ground DTM 9.3 west to 10.1 east, Z0 = 9.7):
chantry parapets 15.8 (6.1 m), main parapet 39.3-39.6 (29.8 m), lead ridge 41.7 (32.0 m), turret tips 52.5-53.0
(43 m). NB the older data/lidar/dsm_1m.tif has the roof ~3.6 m lower (ridge 38.0) but the same turrets and chantries;
the 2023 survey agrees with OSM height=29 and the published ~29 m parapet, so it is used here.
"""
import math
import os
import sys

import numpy as np
from shapely.geometry import Point, Polygon, box
from shapely.ops import unary_union

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import facade_parts as F  # noqa: E402
import zone_bespoke_kings as K  # noqa: E402  (shared Gothic helpers: lathe, box6, pinnacle, tudor, crockets, ...)

OSM = "way/164848633"
Z0 = 9.7
STONE = F.rgb("#e4dac1")      # pale Clipsham / Weldon limestone
STONE_D = F.shade(STONE, 0.70)
STONE_L = F.shade(STONE, 1.05)
STONE_W = F.shade(STONE, 0.86)  # weathered lower courses
LEAD = F.rgb("#80878b")
GLASS = F.rgb("#2a2f36")
DOOR = F.rgb("#3b2a1c")

W0 = np.array([544684.25 - 545000.0, 258388.55 - 258400.0])     # local frame origin (build.py E0, N0)
U = np.array([0.99083983, 0.13504231])
V = np.array([-0.13504231, 0.99083983])

L = 94.1                        # west to east end wall
VS, VN = -8.0, 7.8              # south / north main wall faces
CH_S, CH_N = -11.8, 11.6        # chantry outer faces
TR = 1.95                       # turret circumradius
Z_PAR0, Z_PAR1 = 29.3, 30.15    # parapet base / top of battlements
Z_RIDGE = 32.0
Z_CH = 5.4                      # chantry roof (parapet top 6.1)
Z_SILL, Z_SPR = 7.9, 25.0       # side window sill / springing of the four-centred head
BAYS = [1.9 + 7.525 * k for k in range(13)]     # bay boundaries (buttress centres), 12 bays
CHANTRY = range(1, 11)          # bays with chantry chapels (footprint u 10.7..86)


def P_():
    return F.Parts(mat="stone", wall_col=STONE)


def to_world(P, p0, d, nout, name):
    """Wall frame (x along d, y along the outward normal nout, z up) -> world collision frame (E, N, z)."""
    T, N, C = P.arrays()
    if not len(T):
        return None
    M = P.mats()
    X = p0[0] + T[..., 0] * d[0] + T[..., 1] * nout[0]
    Y = p0[1] + T[..., 0] * d[1] + T[..., 1] * nout[1]
    Wt = np.stack([X, Y, Z0 + T[..., 2]], -1)
    Nw = np.stack([N[:, 0] * d[0] + N[:, 1] * nout[0], N[:, 0] * d[1] + N[:, 1] * nout[1], N[:, 2]], -1)
    g = np.cross(Wt[:, 1] - Wt[:, 0], Wt[:, 2] - Wt[:, 0])
    flip = (g * Nw).sum(1) < 0
    Wt[flip] = Wt[flip][:, ::-1]
    return {"name": name, "tris": Wt, "col": np.clip(C, 0, 1), "mat": M}


def C(u, v):
    """Chapel frame -> local world."""
    return W0 + u * U + v * V


# ------------------------------------------------------------------ windows

def tracery(op, xc, w, z0, zs, lights, transoms, y0, y1):
    """Perpendicular panel tracery inside opening op: mullions running up into the head, transoms with little cusped
    sub-arches under them, and a supermullion grid in the head."""
    lw = w / lights
    bars = []
    for i in range(1, lights):
        bars.append(box(xc - w / 2 + i * lw - 0.07, z0, xc - w / 2 + i * lw + 0.07, zs + w))
    for zt in transoms:
        bars.append(box(xc - w / 2, zt - 0.09, xc + w / 2, zt + 0.09))
        for i in range(lights):     # sub-arch heads under each transom
            cx = xc - w / 2 + (i + 0.5) * lw
            bars.append(box(cx - lw / 2, zt - 0.09 - lw * 0.42, cx + lw / 2, zt - 0.09)
                        .difference(K.pointed(cx, lw * 0.82, zt - 0.09 - lw * 0.9, zt - 0.09 - lw * 0.5, k=0.6, n=3)))
    # head: supermullions between the main mullions, a horizontal panel band at the springing
    for i in range(lights):
        bars.append(box(xc - w / 2 + (i + 0.5) * lw - 0.05, zs + 0.4, xc - w / 2 + (i + 0.5) * lw + 0.05, zs + w))
    bars.append(box(xc - w / 2, zs - 0.06, xc + w / 2, zs + 0.06))
    bars.append(box(xc - w / 2, zs + w * 0.28 - 0.05, xc + w / 2, zs + w * 0.28 + 0.05))
    return unary_union([b.buffer(0) for b in bars]).buffer(0).intersection(op.buffer(0))


def window(P, xc, w, z0, zs, lights, transoms, depth=0.75):
    """Recessed four-centred window in a wall whose face is y = 0; returns the opening polygon."""
    op = K.tudor(xc, w, z0, zs, n=5).buffer(0)
    P.sides_xz(op, -depth, 0.0, STONE_D, inward=True)
    P.face_xz(op, -depth, GLASS, mat="glass")
    tr = tracery(op, xc, w, z0, zs, lights, transoms, -depth + 0.1, -depth + 0.3)
    P.slab(tr, -depth + 0.08, -depth + 0.3, STONE_L)
    # chamfered outer order and hood mould over the head
    ring = op.buffer(0.22, join_style=2).difference(op).intersection(box(xc - w, zs - 0.4, xc + w, zs + w * 2))
    P.slab(ring, 0.0, 0.12, STONE_L)
    P.box(xc - w / 2 - 0.15, xc + w / 2 + 0.15, 0.0, 0.22, z0 - 0.18, z0, STONE_L)      # sill
    return op


# ------------------------------------------------------------------ parts

def parapet(P, x0, x1, z0=Z_PAR0, pierced=True):
    """Pierced battlemented parapet on a wall face y = 0 (outward +y), with a moulded cornice under it."""
    P.extrude_profile([(0.0, z0 - 0.55), (0.28, z0 - 0.3), (0.28, z0), (0.0, z0)], x0, x1, STONE_L)
    g = box(x0, z0, x1, z0 + 0.6)
    if pierced:
        m = max(1, int((x1 - x0) / 1.05))
        g = g.difference(unary_union([K.pointed(x0 + (i + 0.5) * (x1 - x0) / m, 0.42, z0 + 0.1, z0 + 0.34, k=0.8, n=2)
                                      for i in range(m)]))
    K.slab2(P, g, -0.35, 0.0, STONE)
    # battlements: merlons with coping
    n = max(1, int((x1 - x0) / 1.5))
    step = (x1 - x0) / n
    for i in range(n):
        a = x0 + i * step + step * 0.22
        P.box(a, a + step * 0.56, -0.38, 0.04, z0 + 0.6, Z_PAR1 - 0.06, STONE)
        P.box(a - 0.04, a + step * 0.56 + 0.04, -0.42, 0.08, Z_PAR1 - 0.06, Z_PAR1 + 0.02, STONE_L)
    P.box(x0, x1, -0.42, 0.06, z0 + 0.6, z0 + 0.7, STONE_L)


def buttress(P, x, deep, w=1.35, top=Z_PAR0 - 0.6, pin=True):
    """Stepped buttress on a wall face y = 0, projecting `deep` at the base; set-offs at the chantry roof and
    two thirds up; crocketed pinnacle rising above the parapet."""
    h = w / 2
    steps = [(-0.8, Z_CH + 0.6, deep), (Z_CH + 0.6, 17.5, deep * 0.62), (17.5, top, deep * 0.38)]
    for k, (z0, z1, d) in enumerate(steps):
        P.box(x - h, x + h, 0.0, d, z0, z1, STONE)
        # sloped weathering at each set-off, from the step's face back to the next (narrower) stage
        dn = steps[k + 1][2] if k + 1 < len(steps) else 0.0
        rise = 0.6 * (d - dn)
        P.quad((x - h, d, z1), (x + h, d, z1), (x + h, dn, z1 + rise), (x - h, dn, z1 + rise), (0, 0.7, 0.7), STONE_L)
        if k + 1 < len(steps):
            for sx in (-h, h):    # triangular cheeks
                P.add(np.array([[(x + sx, d, z1), (x + sx, dn, z1), (x + sx, dn, z1 + rise)]]), (np.sign(sx), 0, 0), STONE)
    # blind panel on the upper face
    P.slab(K.pointed(x, w * 0.55, 19.0, top - 1.6, k=0.65, n=3), deep * 0.38, deep * 0.38 + 0.05, STONE_D)
    if pin:
        K.pinnacle(P, x, deep * 0.38 * 0.5 + 0.1, 0.95, top, Z_PAR1 + 0.6, Z_PAR1 + 3.2)


def chantry(P, x0, x1, deep):
    """Low chantry chapel filling a bay between buttresses: front face at y = deep, four-light window, battlements."""
    S = P_()     # its own frame: face at y = 0 (= deep in the wall frame)
    op = K.tudor((x0 + x1) / 2, min(3.4, (x1 - x0) - 1.2), 1.5, 3.6, n=4).buffer(0)
    g = box(x0, -0.8, x1, Z_CH).difference(op)
    S.face_xz(g, 0.0, STONE)
    S.box(x0, x1, -deep, 0.0, Z_CH - 0.02, Z_CH, LEAD, bottom=False)       # flat lead roof
    S.sides_xz(op, -0.5, 0.0, STONE_D, inward=True)
    S.face_xz(op, -0.5, GLASS, mat="glass")
    wq = min(3.4, (x1 - x0) - 1.2)
    S.slab(tracery(op, (x0 + x1) / 2, wq, 1.5, 3.6, 4, [], -0.4, -0.25), -0.42, -0.25, STONE_L)
    S.slab(op.buffer(0.18, join_style=2).difference(op).intersection(box(x0, 3.2, x1, 9)), 0.0, 0.1, STONE_L)
    S.box(x0, x1, 0.0, 0.25, -0.8, 0.5, STONE_W)            # plinth
    # parapet with battlements
    S.extrude_profile([(0.0, Z_CH - 0.35), (0.2, Z_CH - 0.15), (0.2, Z_CH), (0.0, Z_CH)], x0, x1, STONE_L)
    S.box(x0, x1, -0.3, 0.0, Z_CH, Z_CH + 0.35, STONE)
    n = max(1, int((x1 - x0) / 1.3))
    st = (x1 - x0) / n
    for i in range(n):
        a = x0 + i * st + st * 0.2
        S.box(a, a + st * 0.6, -0.3, 0.02, Z_CH + 0.35, Z_CH + 0.7, STONE_L)
    T, N, Cc = S.arrays()
    if len(T):
        T = T.copy(); T[..., 1] += deep
        P.t.append(T); P.n.append(N); P.c.append(Cc); P.m.append(S.mats().astype(np.int16))
    # side walls of the chantry against the buttresses are hidden by them; close the roof edge at the wall
    P.box(x0, x1, 0.0, deep, Z_CH - 0.3, Z_CH, STONE, top=False, bottom=False)


def side(north):
    """One long side in its wall frame: x along the wall (west -> east for south, east -> west for north)."""
    P = P_()
    deep = (CH_N - VN) if north else (VS - CH_S)
    xs = [(L - b) if north else b for b in BAYS]   # buttress centres in wall x
    holes = []
    for i in range(12):
        a, b = sorted((xs[i], xs[i + 1]))
        xc = (a + b) / 2
        holes.append(window(P, xc, 4.7, Z_SILL, Z_SPR, 5, [13.5, 19.2]))
        bay = i
        if bay in CHANTRY:
            chantry(P, a + 0.68, b - 0.68, deep)
        else:
            # blind panelling under the window; a door in the west bay
            for k in range(3):
                px = a + 0.9 + (k + 0.5) * (b - a - 1.8) / 3
                P.slab(K.pointed(px, (b - a - 1.8) / 3 - 0.35, 1.2, 5.6, k=0.65, n=3), 0.0, 0.06, STONE_L)
            if bay == 0:
                d = K.tudor(xc, 1.9, -0.2, 2.6, n=4)
                holes.append(d)
                P.sides_xz(d, -0.7, 0.0, STONE_D, inward=True)
                P.face_xz(d, -0.7, DOOR, mat="timber")
                P.box(xc - 1.45, xc + 1.45, 0.0, 0.18, 3.4, 3.6, STONE_L)
    wall = box(0.0, -0.8, L, Z_PAR0).difference(unary_union(holes))
    P.face_xz(wall, 0.0, STONE)
    P.box(0.0, L, 0.0, 0.22, -0.8, 0.6, STONE_W)                                   # plinth
    P.extrude_profile([(0.0, Z_SILL - 0.6), (0.18, Z_SILL - 0.45), (0.18, Z_SILL - 0.3), (0.0, Z_SILL - 0.3)],
                      0.0, L, STONE_L)                                             # string course
    for k, x in enumerate(xs[1:-1]):
        buttress(P, x, deep + 0.25)
    parapet(P, 1.9, L - 1.9)
    return P


def end(east):
    """End wall between the turrets, face y = 0, x from the south (east end) / north (west end) turret."""
    P = P_()
    Wd = VN - VS
    xc = Wd / 2
    w, zs = 9.6, 23.4
    z0 = 6.4 if east else 8.6
    holes = [window(P, xc, w, z0, zs, 9, [13.5, 18.8], depth=0.9)]
    # low gable over the parapet line
    gable = Polygon([(0.0, Z_PAR0), (Wd, Z_PAR0), (xc, Z_RIDGE + 0.4)])
    if east:
        for k in range(5):     # blind panelling under the window
            px = 1.9 + (k + 0.5) * (Wd - 3.8) / 5
            P.slab(K.pointed(px, (Wd - 3.8) / 5 - 0.3, 0.8, 4.8, k=0.65, n=3), 0.0, 0.06, STONE_L)
        P.box(1.9, Wd - 1.9, 0.0, 0.14, 5.4, 5.65, STONE_L)
    else:
        d = K.tudor(xc, 3.0, -0.2, 3.9, n=5)
        holes.append(d)
        P.sides_xz(d, -1.0, 0.0, STONE_D, inward=True)
        P.face_xz(d, -1.0, DOOR, mat="timber")
        lab = box(xc - 2.3, -0.2, xc + 2.3, 5.6).difference(box(xc - 2.05, -0.3, xc + 2.05, 5.35))
        P.slab(lab, 0.0, 0.14, STONE_L)                                          # square label over the door
        for k in (-1, 1):
            P.slab(K.quatrefoil(xc + k * 1.15, 4.75, 0.5), 0.0, 0.05, STONE_D)  # spandrel roundels
    wall = box(0.0, -0.8, Wd, Z_PAR0).union(gable).difference(unary_union(holes))
    P.face_xz(wall, 0.0, STONE)
    P.box(0.0, Wd, 0.0, 0.22, -0.8, 0.6, STONE_W)
    parapet(P, 1.9, Wd - 1.9)
    # coping on the gable behind the parapet, with a small central pinnacle
    for sgn in (-1, 1):
        a = (0.0 if sgn < 0 else Wd, Z_PAR0)
        P.quad((a[0], -0.5, a[1]), (xc, -0.5, Z_RIDGE + 0.4), (xc, 0.1, Z_RIDGE + 0.4), (a[0], 0.1, a[1]),
               (0, 0, 1), STONE_L)
    K.pinnacle(P, xc, -0.2, 0.8, Z_RIDGE + 0.4, Z_RIDGE + 1.6, Z_RIDGE + 3.8)
    return P


def turret(P, x, y):
    """Octagonal corner turret (chapel frame), plinth to ogee cap at 43 m."""
    r = TR
    prof = [(r + 0.22, -0.8), (r + 0.22, 0.6), (r, 0.75), (r, Z_SILL - 0.6), (r + 0.15, Z_SILL - 0.45),
            (r + 0.15, Z_SILL - 0.3), (r, Z_SILL - 0.2), (r, 18.0), (r + 0.12, 18.15), (r + 0.12, 18.4), (r, 18.5),
            (r, Z_PAR0 - 0.4), (r + 0.25, Z_PAR0 - 0.2), (r + 0.25, Z_PAR0 + 0.2), (r - 0.1, Z_PAR0 + 0.35),
            (r - 0.1, 34.3), (r + 0.12, 34.45), (r + 0.12, 34.8), (r - 0.45, 34.9), (r - 0.45, 38.2),
            (r - 0.3, 38.35), (r - 0.3, 38.6)]
    K.lathe(P, x, y, prof, STONE, n=8)
    # tall blind traceried panels on the eight faces of the upper stages
    for i in range(8):
        a = i * math.pi / 4
        for rr, z0, z1 in ((r - 0.1, Z_PAR0 + 0.6, 34.0), (r - 0.45, 35.2, 37.9), (r, 19.0, Z_PAR0 - 0.8)):
            side_ = 2 * rr * math.sin(math.pi / 8)
            ap = rr * math.cos(math.pi / 8)
            S = P_()
            S.slab(K.pointed(0, side_ * 0.6, z0, z1 - side_ * 0.4, k=0.6, n=3), 0.0, 0.04, STONE_D)
            K.place(P, S, x + ap * math.cos(a), y + ap * math.sin(a), a - math.pi / 2)
    # battlemented crown with corner pinnacles at 34.8
    for i in range(8):
        a = math.pi / 8 + i * math.pi / 4
        cx, cy = x + (r - 0.05) * math.cos(a), y + (r - 0.05) * math.sin(a)
        K.box6(P, cx - 0.17, cx + 0.17, cy - 0.17, cy + 0.17, 34.8, 35.5, STONE_L)
        K.lathe(P, cx, cy, [(0.17, 35.5), (0.0, 36.9)], STONE_L, n=4, a0=math.pi / 4)
    # crocketed ogee cap
    cap = [(r - 0.2, 38.6), (r - 0.12, 39.3), (r - 0.4, 40.2), (0.75, 41.0), (0.32, 41.8), (0.0, 42.6)]
    K.lathe(P, x, y, cap, STONE_L, n=8)
    K.crockets(P, x, y, [(r - 0.3, 39.6), (0.2, 42.0)], n=8, k=4, sz=0.11, col=STONE_L)
    K.finial(P, x, y, 42.5, 1.2)


def roof():
    P = P_()
    yS, yN = VS + 0.5, VN - 0.5
    ym = (yS + yN) / 2
    for y0, y1, nz in ((yS, ym, 1), (ym, yN, 1)):
        za, zb = (Z_PAR0 - 0.2, Z_RIDGE) if y0 == yS else (Z_RIDGE, Z_PAR0 - 0.2)
        dz, dy = zb - za, y1 - y0
        ln = math.hypot(dz, dy)
        P.quad((0.6, y0, za), (L - 0.6, y0, za), (L - 0.6, y1, zb), (0.6, y1, zb), (0, -dz / ln, dy / ln), LEAD,
               "plain")
    # lead rolls along the slopes
    for k in range(1, 40):
        x = k * L / 40
        for y0, y1, za, zb in ((yS, ym, Z_PAR0 - 0.2, Z_RIDGE), (ym, yN, Z_RIDGE, Z_PAR0 - 0.2)):
            P.quad((x - 0.04, y0, za + 0.05), (x + 0.04, y0, za + 0.05), (x + 0.04, y1, zb + 0.05),
                   (x - 0.04, y1, zb + 0.05), (0, 0, 1), F.shade(LEAD, 0.85), "plain")
    return P


def build(walls=None):
    out = []
    # long sides: south wall runs west -> east (outward = -V), north wall east -> west (outward = +V)
    out.append(to_world(side(False), C(0.0, VS), U, -V, "kingschapel:south"))
    out.append(to_world(side(True), C(L, VN), -U, V, "kingschapel:north"))
    # ends: east face runs south -> north (outward +U), west face north -> south (outward -U)
    out.append(to_world(end(True), C(L, VS), V, U, "kingschapel:east"))
    out.append(to_world(end(False), C(0.0, VN), -V, -U, "kingschapel:west"))
    T = P_()
    for x, y in ((0.0, VS), (0.0, VN), (L, VS), (L, VN)):
        turret(T, x, y)
    out.append(to_world(T, C(0.0, 0.0), U, V, "kingschapel:turrets"))
    out.append(to_world(roof(), C(0.0, 0.0), U, V, "kingschapel:roof"))
    return [o for o in out if o is not None]


BUILDS = {OSM: build}
HIDE_TILE = [OSM]

if __name__ == "__main__":
    items = build([])
    for it in items:
        Tz = np.asarray(it["tris"])[..., 2]
        print(it["name"], len(it["tris"]), round(float(Tz.min()), 2), round(float(Tz.max()), 2))
    print("total", sum(len(i["tris"]) for i in items))
