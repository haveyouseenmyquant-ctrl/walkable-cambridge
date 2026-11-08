"""Bespoke geometry for the King's College gatehouse and the Gothic screen on King's Parade (William Wilkins, 1824-28),
session 35. OSM way/164708972 "Wilkins' screen" (building=university, ref KINGS010): one footprint holding the north
screen (32.4 m, 0.96 m thick, from the chapel's SE corner to the gatehouse), the gatehouse (25.1 x 7.1-9.3 m, the
central gate block projecting 2.1 m towards the street) and the south screen (30.5 m, ~0.8 m thick, to Scott's
Building). King's College Chapel (way/164848633) is a separate detailed landmark and is not touched; the screen stops
at its footprint. zone_build.load_bespoke() picks up BUILDS / HIDE_TILE. The building lies outside the Market Square
walls.json, so build() gets no walls and works from the OSM footprint (no ELEMENTS).

Frames: s = metres south along the screen line from its north end (OSM node at E -224.16, N -7.32), axis 8.43 deg west
of grid south; t = metres east (towards the street). Gatehouse wall frame x = 57.5 - s (northwards), y = t.

Design from Wikimedia Commons (references for shape/proportion only, no pixels used; downloaded to
data/raw/commons_ref/kings_*.jpg): "Cambridge - King's Parade - View WSW on King's College Gatehouse 1828 by William
Wilkins.jpg", "Cambridge - King's Parade - View NW on Neo Gothic Gatehouse 1828 by William Wilkins & King's College
Chapel 1446-1544.jpg", "Cambridge - King's College - King's Parade - View South along Gatehouse & Screen 1828 by
William Wilkins.jpg" (all Txllxt TxllxT, CC BY-SA 4.0). Buff limestone (Ketton type) throughout.
- screens: 5 bays each; tall open two-centred arches (4 cusped lancets, a roundel and two small circles in the head)
  through the wall, hood moulds with label stops; stepped buttresses between the bays rising into crocketed
  pinnacles with gablets and finials; quatrefoil frieze, cornice and a pierced (arcaded) parapet;
- gatehouse: big four-centred arch with three moulded orders and a crocketed ogee hood with finial, royal arms shield
  in the ogee, crown-over-Tudor-rose bosses either side, tall blind panels, quatrefoil frieze and pierced cresting;
  timber gates with traceried panels and a wicket; wings with tall two-light transomed windows and crowned bosses;
  four octagonal corner turrets with string courses, battlemented crowns and crocketed spirelets (corner pinnacles);
  pierced arched flyers between the front and rear turrets; central octagonal lantern with clock faces, blind
  traceried panels, pinnacled cornice and a crocketed ogee cap with finial; court side with the second arch.
Heights from the LiDAR DSM (data/lidar/dsm_1m.tif; 2023 first-return DSM as check), Z0 = 10.0 (DTM 10.0-10.1 on the
street side, 9.6-9.8 in the court: the plinth runs down to Z0 - 0.6):
screen parapet top 15.6 (DSM 15.0-15.7 over the piers; ground seen through the openings at 7.0 m centres = the 5 open
bays), screen pinnacle tips 18.4 (DSM spikes 16.9-19.0); gatehouse parapet 19.9 (DSM body 19.5-20.1), lead roof 19.2;
turret spirelet tips 25.0 (DSM 1 m peaks 22.3-24.2 front, 22.4-23.4 rear); lantern cornice 26.8 (DSM shoulders
26.9-27.7), ogee cap 31.0 and finial tip 32.3 (DSM 31.7, first return 32.3).
NB: the DSM peaks put the turret pairs ~1 m south of the OSM centre line of the gate block; the model keeps the gate,
turrets and lantern symmetric on the OSM gate (s 45.0, where the OSM gate barrier is).
"""
import math
import os
import sys

import numpy as np
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import facade_parts as F  # noqa: E402

OSM = "way/164708972"
Z0 = 10.0
STONE = F.rgb("#d8c9a6")     # buff limestone
STONE_D = F.shade(STONE, 0.72)
STONE_L = F.shade(STONE, 1.06)
DOOR = F.rgb("#3e2c1e")
LEAD = F.rgb("#7f8589")
DARK = F.rgb("#2e2b27")      # shadowed blind panels / clock dial background
GOLD = F.rgb("#b8973e")
RED = F.rgb("#8a2a24")
BLUE = F.rgb("#2c3d6b")

O = np.array([-224.16, -7.32])
U = np.array([0.14667124, -0.98918529])      # s: south along the screen
V = np.array([0.98918529, 0.14667124])       # t: east (towards King's Parade)

# gatehouse (frame x = 57.5 - s, y = t)
GX0, GX1 = 0.0, 25.11          # south / north ends
BX0, BX1 = 5.56, 19.62         # central gate block
XC = 12.59                     # gate axis (OSM gate, s 45.0)
Y_SW, Y_NW, Y_C, Y_B = 0.56, 0.43, 2.13, -7.12   # south wing / north wing / gate block front, back
Z_ROOF, Z_PAR = 9.2, 9.9
BACK_WIN = (2.8, 6.2, 25.11 - 6.2, 25.11 - 2.8)   # court-side windows (x from the north end)
TUR = [(XC - 4.6, 0.95), (XC + 4.6, 0.95), (XC - 4.6, -6.0), (XC + 4.6, -6.0)]
LAN = (XC, -2.5)

# screens
S_CORN, S_PAR, S_PIN = 5.0, 5.6, 8.0


def W(s, t):
    return O + s * U + t * V


def P_():
    return F.Parts(mat="stone", wall_col=STONE)


# ------------------------------------------------------------------ generic helpers (local frame x, y, z)

def lathe(P, x, y, prof, col, n=8, mat="stone", a0=math.pi / 8):
    """Closed surface of revolution (n-gon prism/pyramid stack) about the vertical axis at (x, y); prof [(r, z), ...]."""
    a = a0 + np.linspace(0, 2 * math.pi, n + 1)
    tris, nrm = [], []
    for (r0, z0), (r1, z1) in zip(prof[:-1], prof[1:]):
        dz, dr = z1 - z0, r1 - r0
        L = math.hypot(dz, dr) or 1.0
        for k in range(n):
            c0, s0, c1, s1 = math.cos(a[k]), math.sin(a[k]), math.cos(a[k + 1]), math.sin(a[k + 1])
            am = (a[k] + a[k + 1]) / 2
            nv = (math.cos(am) * dz / L, math.sin(am) * dz / L, -dr / L)
            p00, p01 = (x + r0 * c0, y + r0 * s0, z0), (x + r0 * c1, y + r0 * s1, z0)
            p11, p10 = (x + r1 * c1, y + r1 * s1, z1), (x + r1 * c0, y + r1 * s0, z1)
            if r0 > 1e-4:
                tris.append([p00, p01, p11]); nrm.append(nv)
            if r1 > 1e-4:
                tris.append([p00, p11, p10]); nrm.append(nv)
    r, z = prof[-1]
    if r > 1e-4:
        for k in range(n):
            tris.append([(x + r * math.cos(a[k]), y + r * math.sin(a[k]), z),
                         (x + r * math.cos(a[k + 1]), y + r * math.sin(a[k + 1]), z), (x, y, z)])
            nrm.append((0, 0, 1))
    if tris:
        P.add(tris, np.asarray(nrm, float), col, mat)


def box6(P, x0, x1, y0, y1, z0, z1, col, mat="stone", bottom=False):
    P.box(x0, x1, y0, y1, z0, z1, col, bottom=bottom, mat=mat)
    P.quad((x0, y0, z0), (x0, y0, z1), (x1, y0, z1), (x1, y0, z0), (0, -1, 0), col, mat)


def face_yz(P, g, x, col, nx, mat="stone"):
    for p in F.polys(g):
        T2 = F.earcut2d(p)
        if len(T2):
            P.add(np.stack([np.full(T2.shape[:2], x), T2[..., 0], T2[..., 1]], -1), (nx, 0, 0), col, mat)


def face_xy(P, g, z, col, nz=1, mat="plain"):
    for p in F.polys(g):
        T2 = F.earcut2d(p)
        if len(T2):
            P.add(np.stack([T2[..., 0], T2[..., 1], np.full(T2.shape[:2], z)], -1), (0, 0, nz), col, mat)


def slab2(P, g, y0, y1, col, mat="stone"):
    """Free-standing slab of polygon(s) g (xz) between y0 < y1: both faces and the sides."""
    P.face_xz(g, y1, col, mat=mat)
    P.face_xz(g, y0, col, n=(0, -1, 0), mat=mat)
    P.sides_xz(g, y0, y1, col, mat=mat)


def place(P, S, cx, cy, ang):
    """Add sub-part S (its own x along, y out) rotated by ang about z and moved to (cx, cy)."""
    T, N, C = S.arrays()
    if not len(T):
        return
    M = S.mats()
    c, s = math.cos(ang), math.sin(ang)
    T2 = T.copy()
    T2[..., 0] = cx + T[..., 0] * c - T[..., 1] * s
    T2[..., 1] = cy + T[..., 0] * s + T[..., 1] * c
    N2 = N.copy()
    N2[:, 0] = N[:, 0] * c - N[:, 1] * s
    N2[:, 1] = N[:, 0] * s + N[:, 1] * c
    P.t.append(T2); P.n.append(N2); P.c.append(C); P.m.append(M.astype(np.int16))


def pointed(xc, w, z0, zs, k=0.75, n=7):
    """Two-centred pointed arch opening (radius k*w, k >= 0.5); polygon in xz."""
    r = k * w
    x0, x1 = xc - w / 2, xc + w / 2
    aa = math.acos((w / 2 - r) / r)       # apex angle on the arc centred right of x0
    left = [(x0 + r + r * math.cos(a), zs + r * math.sin(a)) for a in np.linspace(math.pi, aa, n)]
    right = [(x1 - r + r * math.cos(a), zs + r * math.sin(a)) for a in np.linspace(math.pi - aa, 0, n)][1:]
    return Polygon([(x0, z0)] + left + right + [(x1, z0)])


def tudor(xc, w, z0, zs, n=6):
    """Four-centred arch opening: small haunch arcs (r = w/4, 60 deg) and large arcs (r = w) meeting at the apex."""
    r1, al = 0.25 * w, math.radians(60)
    pts = []
    for sx in (-1, 1):
        x0 = xc + sx * w / 2
        c1 = np.array([x0 - sx * r1, zs])
        half = []
        for a in np.linspace(0, al, n):
            half.append((c1[0] + sx * r1 * math.cos(a), c1[1] + r1 * math.sin(a)))
        u = np.array([sx * math.cos(al), math.sin(al)])
        p1 = c1 + r1 * u
        R = w
        c2 = p1 - R * u
        phi1 = math.atan2(u[1], u[0])
        phi2 = math.acos(np.clip((xc - c2[0]) / R, -1, 1))
        for a in np.linspace(phi1, phi2, n)[1:]:
            half.append((c2[0] + R * math.cos(a), c2[1] + R * math.sin(a)))
        pts.append(half)
    left, right = pts
    return Polygon([(xc - w / 2, z0)] + left + right[::-1] + [(xc + w / 2, z0)])


def quatrefoil(xc, zc, r):
    return unary_union([Point(xc + dx * r * 0.5, zc + dz * r * 0.5).buffer(r * 0.5, resolution=2)
                        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1))])


def crockets(P, x, y, prof, n=8, a0=math.pi / 8, k=3, sz=0.09, col=None):
    """Small crocket knobs on the n arrises of a spire with lathe profile [(r0, z0), (r1, z1)]."""
    (r0, z0), (r1, z1) = prof
    for j in range(k):
        f = (j + 0.6) / (k + 0.4)
        r, z = r0 + (r1 - r0) * f, z0 + (z1 - z0) * f
        for i in range(n):
            a = a0 + 2 * math.pi * i / n
            cx, cy = x + (r + sz * 0.6) * math.cos(a), y + (r + sz * 0.6) * math.sin(a)
            box6(P, cx - sz, cx + sz, cy - sz, cy + sz, z - sz, z + sz, col if col is not None else STONE_L,
                 bottom=True)


def finial(P, x, y, z, s=1.0):
    lathe(P, x, y, [(0.08 * s, z), (0.16 * s, z + 0.12 * s), (0.12 * s, z + 0.25 * s), (0.03 * s, z + 0.55 * s),
                    (0.0, z + 0.62 * s)], STONE_L, n=4, a0=math.pi / 4)


def pinnacle(P, x, y, w, z0, zs, zt):
    """Square crocketed pinnacle: shaft (w square) z0..zs with gablets, four-sided spire to zt, finial."""
    h = w / 2
    box6(P, x - h, x + h, y - h, y + h, z0, zs, STONE)
    gz = 0.45 * w + 0.15
    for dx, dy in ((0, -1), (1, 0), (0, 1), (-1, 0)):   # gablets on the four faces
        S = P_()
        S.slab(Polygon([(-h - 0.02, zs), (h + 0.02, zs), (0, zs + gz)]), 0.0, 0.05, STONE_L)
        place(P, S, x + dx * h, y + dy * h, math.atan2(-dx, dy))
    prof = [(h * 1.15, zs), (0.0, zt)]
    lathe(P, x, y, prof, STONE_L, n=4, a0=math.pi / 4)
    crockets(P, x, y, [(h * 1.15, zs), (0.02, zt)], n=4, a0=math.pi / 4, k=3, sz=0.06)
    finial(P, x, y, zt - 0.05, 0.8)


# ------------------------------------------------------------------ screen

def screen(L, T, centres, wo=2.7):
    """Screen wall in its wall frame (x 0..L, east face y = 0, back face y = -T)."""
    P = P_()
    z0, zsp = 0.6, 2.7
    ops = [pointed(c, wo, z0, zsp, k=0.6) for c in centres]
    holes = unary_union(ops)
    wall = box(0, -0.6, L, S_CORN).difference(holes)
    P.face_xz(wall, 0.0, STONE)
    P.face_xz(wall, -T, STONE, n=(0, -1, 0))
    P.sides_xz(holes, -T, 0.0, STONE_D, inward=True)
    P.quad((0, -T, S_CORN), (L, -T, S_CORN), (L, 0, S_CORN), (0, 0, S_CORN), (0, 0, 1), STONE)
    face_yz(P, box(-T, -0.6, 0, S_CORN), 0.0, STONE, -1)
    face_yz(P, box(-T, -0.6, 0, S_CORN), L, STONE, 1)
    # plinth, string course under the frieze, cornice (front and back)
    P.extrude_profile([(0, -0.6), (0.14, -0.6), (0.14, 0.45), (0.0, 0.62)], 0, L, STONE_D)
    for (a, b) in [(0, centres[0] - wo / 2)] + [(c1 + wo / 2, c2 - wo / 2) for c1, c2 in zip(centres[:-1], centres[1:])] \
            + [(centres[-1] + wo / 2, L)]:
        if b - a > 0.05:   # sill-level weathering between the openings
            P.extrude_profile([(0, z0 - 0.08), (0.08, z0 - 0.04), (0.08, z0), (0, z0)], a, b, STONE_L)
    P.extrude_profile([(0, 4.86), (0.12, 4.9), (0.2, 4.98), (0.2, S_CORN + 0.06), (0, S_CORN + 0.06)], 0, L, STONE_L)
    # quatrefoil frieze
    n = int(L / 0.62)
    for i in range(n):
        xc = (i + 0.5) * L / n
        if any(abs(xc - c) < 0.4 for c in BUTT_X(centres, L)):
            continue
        P.slab(box(xc - 0.25, 4.45, xc + 0.25, 4.84).difference(quatrefoil(xc, 4.645, 0.18)), 0.0, 0.05, STONE)
    # pierced arcaded parapet
    pz0, pz1 = S_CORN + 0.06, S_PAR - 0.1
    par = box(0, pz0, L, pz1)
    m = int(L / 0.5)
    arc_holes = [pointed((i + 0.5) * L / m, 0.26, pz0 + 0.08, pz1 - 0.28, k=0.8, n=3) for i in range(m)]
    slab2(P, par.difference(unary_union(arc_holes)), -0.25, 0.0, STONE)
    box6(P, 0, L, -0.3, 0.05, pz1, S_PAR, STONE_L)
    # tracery in the openings, hood moulds and label stops
    for c, op in zip(centres, ops):
        lw = (wo - 0.11 * 5) / 4
        lights = []
        for k in range(4):
            xl = c - wo / 2 + 0.11 + lw / 2 + k * (lw + 0.11)
            lights.append(pointed(xl, lw, z0, zsp - 0.05, k=0.6, n=4))
        head = [Point(c, zsp + 0.95).buffer(0.32, resolution=3),
                Point(c - 0.62, zsp + 0.55).buffer(0.17, resolution=2),
                Point(c + 0.62, zsp + 0.55).buffer(0.17, resolution=2)]
        lights = unary_union(lights + head)
        trac = op.difference(lights).intersection(op)
        slab2(P, trac, -T / 2 - 0.07, -T / 2 + 0.07, STONE_L)
        ring = op.buffer(0.14, join_style=1, resolution=3).difference(op).intersection(box(c - 2, zsp, c + 2, 9))
        P.slab(ring, 0.0, 0.09, STONE_L)
        for sx in (-1, 1):
            P.box(c + sx * (wo / 2 + 0.07) - 0.09, c + sx * (wo / 2 + 0.07) + 0.09, 0, 0.12, zsp - 0.25, zsp, STONE_L)
    # buttresses with pinnacles
    for xb in BUTT_X(centres, L):
        P.box(xb - 0.33, xb + 0.33, 0, 0.5, -0.6, 2.2, STONE)
        P.extrude_profile([(0, 2.2), (0.5, 2.2), (0.36, 2.5), (0, 2.5)], xb - 0.33, xb + 0.33, STONE_L)
        P.box(xb - 0.28, xb + 0.28, 0, 0.36, 2.5, S_PAR + 0.25, STONE)
        P.box(xb - 0.33, xb + 0.33, -0.05, 0.42, S_CORN - 0.12, S_CORN + 0.06, STONE_L)
        pinnacle(P, xb, 0.1, 0.48, S_PAR + 0.25, S_PAR + 1.05, S_PIN)
    return P


def BUTT_X(centres, L):
    xs = [(a + b) / 2 for a, b in zip(centres[:-1], centres[1:])]
    return xs


# ------------------------------------------------------------------ gatehouse

def turret(P, x, y, zb):
    r = 1.25
    lathe(P, x, y, [(r + 0.12, zb), (r + 0.12, zb + 0.3), (r, zb + 0.4), (r, 10.4), (r + 0.1, 10.5), (r + 0.1, 10.7),
                    (r, 10.8), (r, 11.85), (r + 0.18, 12.0), (r + 0.18, 12.25)], STONE, n=8)
    # blind lancet panels on the eight faces above the roof
    ap = r * math.cos(math.pi / 8)
    side = 2 * r * math.sin(math.pi / 8)
    for i in range(8):
        a = i * math.pi / 4
        S = P_()
        for zz0, zz1 in ((Z_PAR + 0.1, 10.35), (10.85, 11.75)):
            S.slab(pointed(0, side * 0.62, zz0, zz1 - side * 0.35, k=0.6, n=3).exterior.buffer(0.04, join_style=2), 0, 0.03, STONE_L)
        place(P, S, x + ap * math.cos(a), y + ap * math.sin(a), a - math.pi / 2)
    # battlemented crown
    for i in range(8):
        a = math.pi / 8 + i * math.pi / 4
        cx, cy = x + (r + 0.08) * math.cos(a), y + (r + 0.08) * math.sin(a)
        box6(P, cx - 0.16, cx + 0.16, cy - 0.16, cy + 0.16, 12.25, 12.75, STONE_L)
        finial(P, cx, cy, 12.75, 0.9)
    lathe(P, x, y, [(1.0, 12.25), (0.0, 15.0)], STONE_L, n=8)
    crockets(P, x, y, [(1.0, 12.25), (0.05, 15.0)], n=8, k=3, sz=0.08)
    finial(P, x, y, 14.9, 1.4)


def lantern(P):
    x, y = LAN
    r = 2.3
    lathe(P, x, y, [(r + 0.15, Z_ROOF), (r + 0.15, 10.2), (r, 10.35), (r, 12.4), (r + 0.1, 12.5), (r + 0.1, 12.7),
                    (r, 12.8), (r, 16.3), (r + 0.18, 16.45), (r + 0.18, 16.8), (r - 0.1, 16.8)], STONE, n=8)
    ap = r * math.cos(math.pi / 8)
    side = 2 * r * math.sin(math.pi / 8)
    for i in range(8):
        a = i * math.pi / 4
        S = P_()
        # lower blind tracery (two lights), upper open-looking belfry lights (dark) with tracery, clock dials
        for xl in (-side * 0.22, side * 0.22):
            S.face_xz(pointed(xl, side * 0.32, 10.5, 11.9, k=0.6, n=3), 0.015, F.shade(STONE, 0.6))
        S.slab(box(-side * 0.42, 10.4, side * 0.42, 12.35).difference(
            unary_union([pointed(xl, side * 0.32, 10.5, 11.9, k=0.6, n=3) for xl in (-side * 0.22, side * 0.22)])),
            0, 0.04, STONE_L)
        if i % 2 == 0:   # clock dials on the four faces square to the frame (street, court, ends)
            S.slab(Point(0, 13.6).buffer(0.62, resolution=4), 0.0, 0.05, STONE_L)
            S.slab(Point(0, 13.6).buffer(0.52, resolution=4), 0.05, 0.07, DARK)
            S.box(-0.02, 0.02, 0.07, 0.1, 13.6, 14.0, GOLD)
            S.box(-0.25, 0.0, 0.07, 0.1, 13.58, 13.62, GOLD)
            S.face_xz(pointed(0, side * 0.6, 14.5, 15.7, k=0.6, n=3), 0.015, DARK)
        else:
            S.face_xz(pointed(0, side * 0.6, 13.0, 15.7, k=0.6, n=3), 0.015, DARK)
        S.slab(Polygon([(-0.03, 13.0), (0.03, 13.0), (0.03, 16.0), (-0.03, 16.0)]), 0.0, 0.05, STONE_L)
        place(P, S, x + ap * math.cos(a), y + ap * math.sin(a), a - math.pi / 2)
        # corner pinnacles on the cornice
        ac = math.pi / 8 + a
        pinnacle(P, x + (r + 0.05) * math.cos(ac), y + (r + 0.05) * math.sin(ac), 0.3, 16.8, 17.3, 18.2)
    # ogee cap with crockets and finial
    cap = [(r - 0.1, 16.8), (r - 0.05, 17.3), (r - 0.25, 17.9), (1.5, 18.6), (0.85, 19.4), (0.5, 20.2), (0.3, 20.8),
           (0.18, 21.1)]
    lathe(P, x, y, cap, STONE_L, n=8)
    for (ra, za), (rb, zb) in zip(cap[1:-1], cap[2:]):
        crockets(P, x, y, [(ra, za), (rb, zb)], n=8, k=1, sz=0.1)
    lathe(P, x, y, [(0.18, 21.1), (0.3, 21.35), (0.22, 21.6), (0.05, 22.3), (0.0, 22.32)], STONE_L, n=6)


def flyer(P, xa, ya, xb, yb, z0, z1):
    """Pierced arched flyer (a stone slab with a pointed arch) between two turrets."""
    L = math.hypot(xb - xa, yb - ya)
    S = P_()
    g = box(0, z0, L, z1).difference(tudor(L / 2, L - 0.6, z0 - 0.01, z0 + 0.1, n=5))
    if L > 3.5:
        g = g.difference(unary_union([quatrefoil(L * f, z1 - 0.32, 0.2) for f in (0.12, 0.88)]))
    slab2(S, g, -0.16, 0.16, STONE)
    place(P, S, xa, ya, math.atan2(yb - ya, xb - xa))


def blind_panel(P, xc, w, z0, z1, y):
    op = pointed(xc, w, z0, z1 - w * 0.55, k=0.62, n=4)
    P.slab(op.exterior.buffer(0.05, join_style=2), y, y + 0.06, STONE_L)
    P.slab(box(xc - 0.03, z0, xc + 0.03, z1 - w * 0.5), y, y + 0.05, STONE_L)


def crown_rose(P, xc, zc, y):
    """Crown over a Tudor rose (carved bosses either side of the gate)."""
    rose = unary_union([Point(xc + 0.22 * math.cos(a), zc + 0.22 * math.sin(a)).buffer(0.17, resolution=2)
                        for a in np.linspace(0, 2 * math.pi, 6)[:-1]])
    P.slab(rose, y, y + 0.12, STONE_L)
    P.slab(Point(xc, zc).buffer(0.13, resolution=2), y + 0.12, y + 0.18, STONE_L)
    lathe(P, xc, y + 0.25, [(0.3, zc + 0.45), (0.36, zc + 0.6), (0.36, zc + 0.8), (0.4, zc + 0.85), (0.0, zc + 1.0)],
          STONE_L, n=8)
    for i in range(5):
        a = math.pi * i / 4
        finial(P, xc + 0.36 * math.cos(a), y + 0.25 + 0.36 * math.sin(a) * 0.6, zc + 0.85, 0.5)


def frieze(P, x0, x1, y, z0=8.05, z1=8.85):
    n = max(1, int((x1 - x0) / 0.85))
    w = (x1 - x0) / n
    for i in range(n):
        xc = x0 + (i + 0.5) * w
        zc = (z0 + z1) / 2
        P.slab(box(xc - w / 2 + 0.05, z0, xc + w / 2 - 0.05, z1).difference(quatrefoil(xc, zc, (z1 - z0) * 0.42)),
               y, y + 0.06, STONE_L)
        P.slab(Point(xc, zc).buffer(0.07, resolution=2), y, y + 0.1, STONE_L)
    P.extrude_profile([(y, z1), (y + 0.2, z1 + 0.08), (y + 0.2, Z_ROOF), (y, Z_ROOF)], x0, x1, STONE_L)


def parapet(P, x0, x1, y, pierced=True):
    """Parapet on the roof line, front at y (frame local, outward +y)."""
    g = box(x0, Z_ROOF, x1, Z_PAR - 0.12)
    if pierced:
        m = max(1, int((x1 - x0) / 0.55))
        g = g.difference(unary_union([pointed(x0 + (i + 0.5) * (x1 - x0) / m, 0.3, Z_ROOF + 0.1, Z_PAR - 0.42,
                                              k=0.8, n=3) for i in range(m)]))
    slab2(P, g, y - 0.3, y, STONE)
    box6(P, x0, x1, y - 0.34, y + 0.05, Z_PAR - 0.12, Z_PAR, STONE_L)


def wing_window(P, xc, y, holes):
    w, z0, zs = 1.5, 2.4, 6.6
    op = tudor(xc, w, z0, zs, n=4)
    holes.append(op)
    P.sides_xz(op, y - 0.35, y, STONE_D, inward=True)
    P.face_xz(op, y - 0.35, F.rgb(F.GLASS_COL), mat="glass")
    g = unary_union([box(xc - 0.05, z0, xc + 0.05, zs + 0.4), box(xc - w / 2, 4.55, xc + w / 2, 4.65)])
    for xl in (xc - w / 4, xc + w / 4):
        g = g.union(box(xl - 0.02, z0, xl + 0.02, zs + 0.3))
    P.slab(g.intersection(op), y - 0.33, y - 0.28, STONE_L)
    P.slab(op.buffer(0.14, join_style=2).difference(op).intersection(box(xc - 2, z0, xc + 2, 9)), y, y + 0.08, STONE_L)
    P.box(xc - w / 2 - 0.2, xc + w / 2 + 0.2, y, y + 0.16, z0 - 0.16, z0, STONE_L)
    crown_rose(P, xc, 7.4, y)


def gatehouse():
    P = P_()
    # ---- body walls: south wing, returns, gate block, north wing (fronts), ends, back
    holes_sw, holes_nw = [], []
    wing_window(P, (GX0 + BX0) / 2, Y_SW, holes_sw)
    wing_window(P, (BX1 + GX1) / 2, Y_NW, holes_nw)
    P.face_xz(box(GX0, -0.6, BX0, Z_ROOF).difference(unary_union(holes_sw)), Y_SW, STONE)
    P.face_xz(box(BX1, -0.6, GX1, Z_ROOF).difference(unary_union(holes_nw)), Y_NW, STONE)
    face_yz(P, box(Y_SW, -0.6, Y_C, Z_ROOF), BX0, STONE, -1)
    face_yz(P, box(Y_NW, -0.6, Y_C, Z_ROOF), BX1, STONE, 1)
    face_yz(P, box(Y_B, -0.6, Y_SW, Z_ROOF), GX0, STONE, -1)
    face_yz(P, box(Y_B, -0.6, Y_NW, Z_ROOF), GX1, STONE, 1)
    arch = tudor(XC, 4.0, 0.0, 4.3, n=6)
    P.face_xz(box(BX0, -0.6, BX1, Z_ROOF).difference(arch), Y_C, STONE)
    back_holes = [arch] + [tudor(GX1 - xc, 1.5, 2.4, 6.6, n=4) for xc in BACK_WIN]
    P.face_xz(box(GX0, -0.6, GX1, Z_ROOF).difference(unary_union(back_holes)), Y_B, STONE, n=(0, -1, 0))
    foot = Polygon([(GX0, Y_B), (GX1, Y_B), (GX1, Y_NW), (BX1, Y_NW), (BX1, Y_C), (BX0, Y_C), (BX0, Y_SW), (GX0, Y_SW)])
    face_xy(P, foot.buffer(-0.3, join_style=2), Z_ROOF - 0.05, LEAD)
    # ---- gate: recesses, timber gates with traceried panels and wicket, passage vault
    for yf, yd, sgn in ((Y_C, 0.9, 1), (Y_B, -5.9, -1)):
        lo, hi = sorted((yf, yd))
        P.sides_xz(arch, lo, hi, STONE_D, inward=True, skip_ground=True)
        P.face_xz(arch, yd, DOOR, n=(0, sgn, 0), mat="timber")
        d = yd + sgn * 0.02
        lines = [box(XC - 0.04, 0, XC + 0.04, 6.0)]
        for xl in (XC - 1.0, XC + 1.0):
            for zz0, zz1 in ((0.3, 1.6), (1.9, 3.4)):
                P.slab(box(xl - 0.65, zz0, xl + 0.65, zz1).exterior.buffer(0.04, join_style=2), min(d, d + sgn * 0.05),
                       max(d, d + sgn * 0.05), F.shade(DOOR, 1.25), mat="timber")
            for k in range(3):
                xx = xl - 0.6 + 0.3 + k * 0.3
                P.slab(pointed(xx, 0.24, 3.7, 4.6, k=0.6, n=3).exterior.buffer(0.025, join_style=2), min(d, d + sgn * 0.05),
                       max(d, d + sgn * 0.05), F.shade(DOOR, 1.25), mat="timber")
        P.slab(unary_union(lines + [box(XC + 0.25, 0.05, XC + 1.45, 2.3).exterior.buffer(0.035, join_style=2)]).intersection(arch),
               min(d, d + sgn * 0.06), max(d, d + sgn * 0.06), F.shade(DOOR, 0.8), mat="timber")
        if sgn > 0:   # three moulded orders round the street arch
            for k, (b, dy) in enumerate(((0.18, 0.08), (0.36, 0.16), (0.55, 0.24))):
                ring = arch.buffer(b, join_style=1, resolution=4).difference(arch.buffer(b - 0.18, join_style=1,
                                                                                        resolution=4))
                P.slab(ring.intersection(box(XC - 4, 0, XC + 4, 9)), Y_C, Y_C + dy, STONE_L if k != 1 else STONE)
        else:
            P.slab(arch.buffer(0.3, join_style=1, resolution=4).difference(arch).intersection(box(XC - 4, 0, XC + 4, 9)),
                   Y_B - 0.12, Y_B, STONE_L)
    # ---- street front of the gate block: ogee hood, arms, crowns, blind panels, frieze, cresting
    hood = []
    for sx in (-1, 1):
        for t in np.linspace(0, 1, 9):
            # ogee: convex from the springing, reverse curve up to the apex finial
            xo = XC + sx * (2.75 - 2.75 * (0.5 - 0.5 * math.cos(math.pi * t)))
            zo = 4.3 + 1.6 * math.sin(0.5 * math.pi * min(1, t * 1.6)) + 2.2 * max(0, t - 0.55) / 0.45
            hood.append((xo, zo))
    hl = LineString(hood[:9]).union(LineString(hood[9:]))
    P.slab(hl.buffer(0.12, cap_style=2, join_style=1, resolution=2), Y_C + 0.24, Y_C + 0.4, STONE_L)
    for (xo, zo) in hood[1:8] + hood[10:17]:
        box6(P, xo - 0.1, xo + 0.1, Y_C + 0.32, Y_C + 0.55, zo + 0.1, zo + 0.3, STONE_L, bottom=True)
    pinnacle(P, XC, Y_C + 0.35, 0.34, 8.1, 8.5, 9.6)
    shield = Polygon([(XC - 0.55, 7.55), (XC + 0.55, 7.55), (XC + 0.55, 6.9), (XC + 0.3, 6.45), (XC, 6.3),
                      (XC - 0.3, 6.45), (XC - 0.55, 6.9)])
    P.slab(shield, Y_C, Y_C + 0.18, STONE_L)
    for q, col in ((box(XC - 0.45, 7.0, XC, 7.45), RED), (box(XC, 7.0, XC + 0.45, 7.45), BLUE),
                   (box(XC - 0.45, 6.45, XC + 0.45, 6.98).intersection(shield), RED)):
        P.face_xz(q, Y_C + 0.19, F.shade(col, 0.9), mat="trim")
    lathe(P, XC, Y_C + 0.25, [(0.32, 7.6), (0.38, 7.75), (0.38, 7.95), (0.0, 8.1)], STONE_L, n=8)
    for sx in (-1, 1):
        crown_rose(P, XC + sx * 2.95, 5.4, Y_C)
        for xb in (XC + sx * 3.9, XC + sx * 5.3):
            blind_panel(P, xb, 1.0, 1.0, 7.6, Y_C)
        # angle shafts (polygonal buttress shafts at the block corners)
        xs = BX0 + 0.22 if sx < 0 else BX1 - 0.22
        lathe(P, xs, Y_C - 0.05, [(0.3, -0.6), (0.3, 0.6), (0.24, 0.75), (0.24, Z_PAR + 0.3)], STONE, n=6)
        pinnacle(P, xs, Y_C - 0.05, 0.36, Z_PAR + 0.3, Z_PAR + 0.9, Z_PAR + 2.2)
    frieze(P, BX0, BX1, Y_C)
    frieze(P, GX0, BX0, Y_SW)
    frieze(P, BX1, GX1, Y_NW)
    parapet(P, BX0, BX1, Y_C)
    parapet(P, GX0, BX0, Y_SW)
    parapet(P, BX1, GX1, Y_NW)
    # plinths
    for a, b in ((BX0, XC - 2.0), (XC + 2.0, BX1)):
        P.extrude_profile([(Y_C, -0.6), (Y_C + 0.15, -0.6), (Y_C + 0.15, 0.5), (Y_C, 0.65)], a, b, STONE_D)
    S = P_()
    S.extrude_profile([(0, -0.6), (0.15, -0.6), (0.15, 0.5), (0, 0.65)], 0, BX0 - GX0, STONE_D)
    place(P, S, GX0, Y_SW, 0)
    S = P_()
    S.extrude_profile([(0, -0.6), (0.15, -0.6), (0.15, 0.5), (0, 0.65)], 0, GX1 - BX1, STONE_D)
    place(P, S, BX1, Y_NW, 0)
    # ---- court side (y = Y_B): windows either side, string course, plain battlements; ends
    S = P_()
    Lb = GX1 - GX0
    hb = []
    for xc in BACK_WIN:
        wing_window(S, xc, 0.0, hb)
    S.extrude_profile([(0, 8.05), (0.2, 8.13), (0.2, 8.35), (0, 8.35)], 0, Lb, STONE_L)
    for i in range(int(Lb / 1.4)):
        x = 0.35 + i * 1.4
        box6(S, x, x + 0.7, -0.3, 0.0, Z_PAR, Z_PAR + 0.35, STONE_L)
    # mirror into the back face: local x -> GX1 - x, y -> Y_B - y (a 180 deg turn about z)
    place(P, S, GX1, Y_B, math.pi)
    box6(P, GX0, GX1, Y_B, Y_B + 0.32, Z_ROOF, Z_PAR, STONE)
    for (x, yy0, yy1, nx) in ((GX0, Y_B, Y_SW, -1), (GX1, Y_B, Y_NW, 1)):
        S = P_()
        L2 = yy1 - yy0
        g = box(0, Z_ROOF, L2, Z_PAR)
        S.slab(g, -0.3, 0.0, STONE)
        S.face_xz(tudor(L2 / 2, 1.2, 3.0, 6.2, n=4), 0.02, F.rgb(F.GLASS_COL), mat="glass")
        S.slab(tudor(L2 / 2, 1.2, 3.0, 6.2, n=4).buffer(0.12, join_style=2).difference(
            tudor(L2 / 2, 1.2, 3.0, 6.2, n=4)), 0.0, 0.08, STONE_L)
        if nx < 0:
            place(P, S, x, yy0, math.pi / 2)
        else:
            place(P, S, x, yy1, -math.pi / 2)
    # wing corner pinnacles
    for (x, y) in ((GX0 + 0.25, Y_SW - 0.15), (GX1 - 0.25, Y_NW - 0.15), (GX0 + 0.25, Y_B + 0.15), (GX1 - 0.25, Y_B + 0.15)):
        pinnacle(P, x, y, 0.36, Z_PAR, Z_PAR + 0.6, Z_PAR + 1.9)
    # ---- turrets, flyers, lantern
    for x, y in TUR:
        turret(P, x, y, Z_ROOF - 1.2)
    for sx in (-1, 1):
        xa = XC + sx * 4.6
        flyer(P, xa, 0.95 - 1.15, xa, -6.0 + 1.15, Z_PAR, 11.8)
        lx, ly = LAN
        for yy in (0.95, -6.0):
            dx, dy = lx - xa, ly - yy
            L = math.hypot(dx, dy)
            ux, uy = dx / L, dy / L
            flyer(P, xa + ux * 1.15, yy + uy * 1.15, lx - ux * 2.2, ly - uy * 2.2, Z_PAR + 0.6, 11.6)
    lantern(P)
    return P


# ------------------------------------------------------------------ assembly

def frame_world(P, p0, d, name, z0=Z0):
    T, N, C = P.arrays()
    if not len(T):
        return None
    M = P.mats()
    n = np.array([d[1], -d[0]])
    X = p0[0] + T[..., 0] * d[0] + T[..., 1] * n[0]
    Y = p0[1] + T[..., 0] * d[1] + T[..., 1] * n[1]
    Wt = np.stack([X, Y, z0 + T[..., 2]], -1)
    Nw = np.stack([N[:, 0] * d[0] + N[:, 1] * n[0], N[:, 0] * d[1] + N[:, 1] * n[1], N[:, 2]], -1)
    g = np.cross(Wt[:, 1] - Wt[:, 0], Wt[:, 2] - Wt[:, 0])
    flip = (g * Nw).sum(1) < 0
    Wt[flip] = Wt[flip][:, ::-1]
    return {"name": name, "tris": Wt, "col": np.clip(C, 0, 1), "mat": M}


def build(walls=None):
    out = []
    # north screen: east face t = 0 from s 32.39 (gatehouse) north to s 0 (chapel); 5 bays (DSM opening centres)
    Ln = 32.39
    out.append(frame_world(screen(Ln, 0.96, [2.6 + 6.95 * k for k in range(5)]), W(32.39, 0.0), -U, "kings:screen_n"))
    # south screen: its own east face line (OSM nodes at E -211.12 N -94.31 and E -216.15 N -64.26)
    A, B = np.array([-211.12, -94.31]), np.array([-216.15, -64.26])
    Ls = float(np.linalg.norm(B - A))
    b = Ls / 5
    out.append(frame_world(screen(Ls, 0.8, [b * (k + 0.5) for k in range(5)]), A, (B - A) / Ls, "kings:screen_s"))
    out.append(frame_world(gatehouse(), W(57.5, 0.0), -U, "kings:gatehouse"))
    return [o for o in out if o is not None]


BUILDS = {OSM: build}
HIDE_TILE = [OSM]   # screen + gatehouse is a complete model over the whole footprint (open screen bays need the box gone)

if __name__ == "__main__":
    items = build([])
    for it in items:
        Tz = np.asarray(it["tris"])[..., 2]
        print(it["name"], len(it["tris"]), round(float(Tz.min()), 2), round(float(Tz.max()), 2))
    print("total", sum(len(i["tris"]) for i in items))
