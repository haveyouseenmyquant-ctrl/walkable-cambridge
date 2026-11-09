"""Bespoke geometry for the Round Church (Church of the Holy Sepulchre, Bridge Street / Round Church Street,
OSM way/92878394), session 63, ring 1/2 edge. zone_build.load_bespoke() picks up BUILDS / HIDE_TILE.

Form (shape / proportion / colour only; general knowledge of the church: a c.1130 Norman round nave, restored by
Salvin in 1841, with a 19th-century chancel and north aisle; no held-out benchmark photos): a circular ambulatory
wall in pale buff rubble/ashlar with small round-headed Norman windows under a lean-to ring roof, a central drum
with round-headed clerestory lights under a conical roof, the Norman west door (three recessed round orders), and
an east block of two parallel gabled ranges (chancel and north aisle) with pointed windows.

Heights from the LiDAR DSM over Z0 = 8.75 (DTM): ambulatory eaves ~13.5 (4.8 m), drum top ~20 (11 m), cone apex
24.2 (15.4 m; the DSM peak sits ~3 m SW of the OSM circle centre, kept at the OSM centre for collision); east
block ridges 17.5-18.2 (~9.2 m), valleys / eaves ~15.5 (6.6 m).
"""
import math
import os
import sys

import numpy as np
from shapely.geometry import Point, Polygon, box
from shapely.ops import unary_union

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import facade_parts as F  # noqa: E402
from zone_bespoke_churches import Church, Pal, window, parapet, wall_face, coping, cross, Y, REV, GLASS, DOOR  # noqa: E402

OSM = "way/92878394"
Z0 = 8.75
# OSM nodes of the round nave (world collision frame, E/N metres), fitted to a circle below
RING = [(-113.44, 400.79), (-115.54, 399.11), (-118.1, 398.27), (-120.8, 398.33), (-123.31, 399.32), (-125.33, 401.11),
        (-126.61, 403.47), (-127.01, 406.13), (-126.47, 408.76), (-125.06, 411.07), (-122.95, 412.73), (-120.39, 413.58)]
# east block (chancel + north aisle) rectangle: O, s along U (ENE), t along V
EO, EU = (-111.85, 399.23), (10.56, 5.37)
ES, ET = 11.85, 19.0
NUB = [(-119.17, 413.55), (-120.09, 415.36), (-120.56, 415.25), (-121.36, 415.73), (-121.58, 416.63), (-121.12, 417.38),
       (-121.88, 418.86), (-114.79, 422.46), (-113.33, 419.6)]
Z_AMB, Z_DRUM, Z_APEX = 4.8, 11.0, 15.4
R_DRUM = 4.2
E_EAVE, E_RIDGE = 6.6, 9.2


def _fit_circle(pts):
    P = np.asarray(pts, float)
    A = np.c_[2 * P, np.ones(len(P))]
    b = (P ** 2).sum(1)
    cx, cy, c = np.linalg.lstsq(A, b, rcond=None)[0]
    return (cx, cy), math.sqrt(c + cx * cx + cy * cy)


CEN, R_OUT = _fit_circle(RING)


def roundhead(P, pal, xc, w, zb, zt, y=Y, splay=0.45):
    """Norman round-headed window: deep reveal, glass, a roll-moulded label and a sill."""
    r = w / 2
    zs = zt - r
    op = box(xc - r, zb, xc + r, zs).union(Point(xc, zs).buffer(r, 12).intersection(box(xc - r, zs, xc + r, zt + 1)))
    yg = y - splay
    P.sides_xz(op, yg, y, pal.dark, inward=True, mat="stone")
    P.face_xz(op, yg, GLASS, mat="glass")
    lab = op.buffer(0.16).difference(op).intersection(box(xc - w, zs - 0.05, xc + w, zt + 1))
    P.slab(lab, y, y + 0.09, pal.dress, mat="stone")
    P.extrude_profile([(y - 0.05, zb - 0.14), (y + 0.12, zb - 0.14), (y + 0.12, zb - 0.06), (y - 0.05, zb + 0.04)],
                      xc - r - 0.08, xc + r + 0.08, pal.dress, mat="stone")
    if not hasattr(P, "openings"):
        P.openings = []
    P.openings.append(("window", xc))
    return op


def norman_door(P, pal, xc, w, h, y=Y):
    """Round-arched doorway of three recessed orders (each a step back with a roll), the timber door at the back."""
    def arch(ww, hh):
        r = ww / 2
        return box(xc - r, 0, xc + r, hh - r).union(Point(xc, hh - r).buffer(r, 14).intersection(
            box(xc - r, hh - r, xc + r, hh + 1)))
    orders = 3
    outer = arch(w + 0.36 * orders, h + 0.18 * orders)
    for k in range(orders, 0, -1):
        o = arch(w + 0.36 * k, h + 0.18 * k)
        i = arch(w + 0.36 * (k - 1), h + 0.18 * (k - 1))
        yk = y - 0.18 * (orders - k + 1)
        P.face_xz(o.difference(i), yk, pal.dress if k % 2 else F.shade(pal.dress, 0.88), mat="stone")
        P.sides_xz(i, yk - 0.18, yk, pal.dark, inward=True, skip_ground=True, mat="stone")
    P.sides_xz(outer, y - 0.18, y, pal.dark, inward=True, skip_ground=True, mat="stone")
    P.face_xz(arch(w, h), y - 0.18 * (orders + 1), DOOR, mat="timber")
    if not hasattr(P, "openings"):
        P.openings = []
    P.openings.append(("door", xc))
    return outer


def build(walls=None):
    pal = Pal("#c9bea4", "#d8cfb8", "#6f7478")
    C = Church("roundchurch", CEN, (1.0, 0.0), Z0, pal)   # local (s, t) = world offset from the circle centre
    u = np.asarray(EU, float) / np.linalg.norm(EU)
    v = np.array([-u[1], u[0]])
    eo = np.asarray(EO, float)
    rect = [eo, eo + ES * u, eo + ES * u + ET * v, eo + ET * v]
    block = Polygon(rect)
    # --- round nave: outer ambulatory wall (CCW, outside on the right), skipping the arc inside the east block
    n = 20
    for k in range(n):
        a0, a1 = 2 * math.pi * k / n, 2 * math.pi * (k + 1) / n
        A = (R_OUT * math.cos(a0), R_OUT * math.sin(a0))
        B = (R_OUT * math.cos(a1), R_OUT * math.sin(a1))
        mid = Point(CEN[0] + R_OUT * math.cos((a0 + a1) / 2), CEN[1] + R_OUT * math.sin((a0 + a1) / 2))
        if block.buffer(-0.3).contains(mid):
            continue
        L = math.dist(A, B)
        P = C.P()
        am = math.degrees((a0 + a1) / 2) % 360
        holes = []
        if k == n // 2:            # west (189 deg, towards Bridge St): the Norman doorway
            holes.append(norman_door(P, pal, L / 2, 1.2, 2.9))
        elif k % 2 == 0:
            holes.append(roundhead(P, pal, L / 2, 0.75, 1.9, 3.5))
        wall_face(P, pal, -0.12, L + 0.12, [(-0.12, Z_AMB), (L + 0.12, Z_AMB)], holes)
        P.extrude_profile([(Y - 0.05, Z_AMB - 0.25), (Y + 0.14, Z_AMB - 0.2), (Y + 0.2, Z_AMB), (Y - 0.05, Z_AMB + 0.05)],
                          -0.12, L + 0.12, pal.dress, mat="stone")   # corbel-table eaves course
        if k % 2 == 1 and k != n // 2:     # flat Norman pilaster buttresses between windows
            P.box(L / 2 - 0.35, L / 2 + 0.35, Y - 0.05, Y + 0.18, -0.6, Z_AMB - 0.25, pal.wall, mat="stone")
        C.put(P, A, B, "amb%d" % k)
    # --- central drum with round-headed clerestory lights
    m = 16
    for k in range(m):
        a0, a1 = 2 * math.pi * k / m, 2 * math.pi * (k + 1) / m
        A = (R_DRUM * math.cos(a0), R_DRUM * math.sin(a0))
        B = (R_DRUM * math.cos(a1), R_DRUM * math.sin(a1))
        L = math.dist(A, B)
        P = C.P()
        holes = [roundhead(P, pal, L / 2, 0.6, 8.1, 9.9, splay=0.35)] if k % 2 == 0 else []
        wall_face(P, pal, -0.06, L + 0.06, [(-0.06, Z_DRUM), (L + 0.06, Z_DRUM)], holes, zbot=Z_AMB + 1.8)
        P.extrude_profile([(Y - 0.05, Z_DRUM - 0.3), (Y + 0.15, Z_DRUM - 0.25), (Y + 0.2, Z_DRUM), (Y - 0.05, Z_DRUM + 0.05)],
                          -0.06, L + 0.06, pal.dress, mat="stone")
        C.put(P, A, B, "drum%d" % k)
    # --- ring roof (lean-to) and conical roof
    q = 32
    amb, cone = [], []
    r0, z0 = R_OUT + 0.35, Z_AMB - 0.12
    r1, z1 = R_DRUM + 0.05, Z_AMB + 2.9
    rc, zc = R_DRUM + 0.4, Z_DRUM - 0.1
    for k in range(q):
        a0, a1 = 2 * math.pi * k / q, 2 * math.pi * (k + 1) / q
        c0, s0, c1, s1 = math.cos(a0), math.sin(a0), math.cos(a1), math.sin(a1)
        amb.append([(r0 * c0, r0 * s0, z0), (r0 * c1, r0 * s1, z0), (r1 * c1, r1 * s1, z1), (r1 * c0, r1 * s0, z1)])
        cone.append([(rc * c0, rc * s0, zc), (rc * c1, rc * s1, zc), (0.0, 0.0, Z_APEX)])
    C.roof(amb, F.rgb("#767a7c"))
    C.roof(cone, F.rgb("#6c7174"))
    out = C.done()
    # --- east block: chancel (south) and north aisle as two parallel gabled ranges along s, pointed windows
    D = Church("roundchurch_e", EO, EU, Z0, pal)
    th = ET / 2
    for t0, t1, nm in ((0.0, th, "chancel"), (th, ET, "aisle")):
        tr = (t0 + t1) / 2
        P = D.P()     # east gable
        L = t1 - t0
        top = [(0, E_EAVE), (L / 2, E_RIDGE), (L, E_EAVE)]
        wall_face(P, pal, 0, L, top, [window(P, pal, L / 2, 2.6 if nm == "chancel" else 2.0, 2.0, 6.6, 3)])
        coping(P, pal, top)
        cross(P, pal, L / 2, E_RIDGE + 0.15)
        D.put(P, (ES, t0), (ES, t1), nm + "_e")
        D.gable_roof(-0.2, ES, t0, t1, None, E_EAVE, tr, E_RIDGE, pal.roof, ov=0.25, verge=0.15)
    for A, B, nm, xs in (((0, 0), (ES, 0), "s", (6.0, 9.6)), ((ES, ET), (0, ET), "n", (2.4, 6.0, 9.6))):
        P = D.P()
        L = math.dist(A, B)
        holes = [window(P, pal, x, 1.4, 1.9, 5.4, 2) for x in xs]
        wall_face(P, pal, -0.1, L + 0.1, [(-0.1, E_EAVE), (L + 0.1, E_EAVE)], holes)
        P.extrude_profile([(Y - 0.05, E_EAVE - 0.2), (Y + 0.12, E_EAVE - 0.2), (Y + 0.18, E_EAVE), (Y - 0.05, E_EAVE + 0.04)],
                          -0.1, L + 0.1, pal.dress, mat="stone")
        D.put(P, A, B, "side_" + nm)
    P = D.P()      # west wall of the aisle range north of the round (gable end, mostly hidden by the round)
    top = [(0, E_EAVE), (th / 2, E_RIDGE), (th, E_EAVE)]
    wall_face(P, pal, 0, th, top, [])
    coping(P, pal, top)
    D.put(P, (0, ET), (0, th), "aisle_w")
    out += D.done()
    # --- small low annex north-west (OSM nub between the round and the aisle): plain walls, lead flat
    E = Church("roundchurch_nw", (0.0, 0.0), (1.0, 0.0), Z0, pal)
    ring = Polygon(NUB)
    pts = list(ring.exterior.coords)[:-1]
    if not ring.exterior.is_ccw:     # CCW walk = outside on the right
        pts = pts[::-1]
    for i in range(len(pts)):
        A, B = pts[i], pts[(i + 1) % len(pts)]
        L = math.dist(A, B)
        if L < 0.3:
            continue
        P = E.P()
        wall_face(P, pal, -0.05, L + 0.05, [(-0.05, 4.2), (L + 0.05, 4.2)],
                  [roundhead(P, pal, L / 2, 0.7, 1.6, 3.1)] if L > 3.0 else [])
        parapet(P, pal, -0.05, L + 0.05, 4.2, 4.6)
        E.put(P, A, B, "nw%d" % i)
    T = [tuple(pts[i]) for i in range(len(pts))]
    import mapbox_earcut as earcut
    tri = earcut.triangulate_float64(np.asarray(T, float), np.array([len(T)], np.uint32))
    E.roof([[(T[a][0], T[a][1], 4.15), (T[b][0], T[b][1], 4.15), (T[c][0], T[c][1], 4.15)]
            for a, b, c in tri.reshape(-1, 3)], F.rgb("#80868a"))
    out += E.done()
    return out


BUILDS = {OSM: build}
ELEMENTS = {}
HIDE_TILE = [OSM]

if __name__ == "__main__":
    items = build([])
    print(len(items), sum(len(i["tris"]) for i in items), round(max(float(np.asarray(i["tris"])[..., 2].max()) for i in items), 2),
          "centre", [round(c, 2) for c in CEN], "R", round(R_OUT, 2))
