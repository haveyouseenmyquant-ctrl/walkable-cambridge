"""Bespoke geometry for St Andrew the Great, St Andrew's Street (OSM way/135595981, building=church), session 62,
ring 1. zone_build.load_bespoke() picks up BUILDS / HIDE_TILE (city_facades.py skips bespoke buildings).

Form (shape / proportion / colour only; general knowledge of the church, Ambrose Poynter's Perpendicular-revival
rebuild of 1842-43, no held-out benchmark photos): a broad aisleless preaching box in pale buff ashlar under a
low-pitched slate roof hidden behind embattled parapets, tall three-light Perpendicular windows between
buttresses, coped gables east and west, a short square chancel with a five-light east window, a low flat-roofed
block south-west of the tower, and a west tower on St Andrew's Street with the entrance door, a west window,
string courses, louvred two-light belfry openings, battlements and corner pinnacles.

Frame: O = OSM SE corner of the SW block / SW corner of the nave (E 77.93, N 16.66), s east along the south wall
(axis 18.5 deg north of east), t north. Footprint in (s, t): nave s 0..27.0, t 0..17.8; chancel s 27.0..29.1,
t 5.8..13.3; SW block s -4.5..0, t 0..5.6.
Heights from the LiDAR DSM (data/lidar/dsm_1m.tif) over Z0 = 9.55 (DTM): nave edges 9-10 m (parapet 9.6), ridge
~12 at t 8-9; chancel 10-12; SW block 8-11 (parapet 8.0); tower plateau 21-22 m over s -2..2, t 4..10.5 (it
projects ~2 m west of the OSM line; the model keeps the OSM outline for collision: tower s 0..5.2, t 4.2..9.4,
battlements 21.6, pinnacles 23.3).
"""
import math
import os
import sys

import numpy as np
from shapely.geometry import box
from shapely.ops import unary_union

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import facade_parts as F  # noqa: E402
from zone_bespoke_churches import (Church, Pal, window, door, buttress, parapet, wall_face, coping, cross,  # noqa: E402
                                   Y, LEAD)

OSM = "way/135595981"
Z0 = 9.55
O = (77.93, 16.66)
U = (25.64, 8.58)
S_E, T_N = 27.03, 17.77            # nave east wall, north wall
HP, ZE = 9.7, 8.9                  # parapet top, wall top under the parapet
ZR, TR = 12.0, 8.9                 # nave ridge height and line
CH = (27.03, 29.1, 5.83, 13.28)    # chancel s0, s1, t0, t1
CH_E, CH_R = 8.6, 10.9
TW = (0.0, 5.2, 4.2, 9.4)          # tower s0, s1, t0, t1 (DSM plateau t 4..10.5; OSM west-face vertex at 8.72)
Z_TW = 21.6
SW = (-4.46, 0.0, 0.0, 5.56)       # SW block
Z_SW = 8.0


def roof_z(t):
    return ZR - (ZR - 9.0) * abs(t - TR) / TR


def build(walls=None):
    pal = Pal("#c8bc9b", "#d9ceb1", "#6c7378")
    C = Church("standrew", O, U, Z0, pal)

    def bays(P, L, n, zb, zt, w=2.2, lights=3, skip=()):
        step = L / n
        holes = [window(P, pal, step * (k + 0.5), w, zb, zt, lights) for k in range(n) if k not in skip]
        return holes, [step * k for k in range(n + 1)]

    # --- south and north walls: four tall Perpendicular windows between buttresses (ring1 annotation
    # way_135595981.json, wall :6: windows at 3.75 / 10.25 / 16.75 / 23.25, w 2.4, sill 2.6, h 5.6, pilasters at
    # 0.5 / 7 / 13.5 / 20 / 26.5), embattled parapet; the north wall (no annotation) mirrors the south
    WX, BX = (3.75, 10.25, 16.75, 23.25), (0.5, 7.0, 13.5, 20.0, 26.5)
    for A, B, nm, mirror in (((0, 0), (S_E, 0), "south", False), ((S_E - 0.2, T_N), (0, T_N), "north", True)):
        P = C.P()
        L = math.dist(A, B)
        xs = [L - x if mirror else x for x in WX]
        holes = [window(P, pal, x, 2.4, 2.6, 8.2, 3) for x in xs]
        wall_face(P, pal, -0.1, L + 0.1, [(-0.1, ZE), (L + 0.1, ZE)], holes)
        parapet(P, pal, -0.15, L + 0.15, ZE, HP, embattled=True)
        for x in BX:
            buttress(P, pal, min(max(L - x if mirror else x, 0.3), L - 0.3), 6.8, d0=0.8)
        C.put(P, A, B, nm)
    # --- west wall north of the tower (annotation :1: two windows at 2.35 / 6.7, w 1.8, 2.6..7.6), coped
    # half-gable rising to the tower
    P = C.P()
    L = T_N - TW[3]
    top = [(0, ZE + 0.2), (L, roof_z(TW[3]) + 0.3)]
    wall_face(P, pal, 0, L, top, [window(P, pal, x, 1.8, 2.6, 7.6, 2) for x in (2.35, 6.7)])
    coping(P, pal, top)
    buttress(P, pal, 0.3, 6.4, d0=0.9)
    C.put(P, (0, T_N), (0, TW[3]), "west_n")
    # --- east nave gable (the chancel stands in front of its middle), coped, with a cross
    P = C.P()
    L = T_N
    top = [(0, ZE + 0.2), (TR, ZR + 0.2), (L, ZE + 0.2)]
    holes = [window(P, pal, 2.9, 2.8, 3.6, 8.6, 3), window(P, pal, L - 2.3, 1.9, 3.6, 8.6, 3)]   # :7 annotation
    wall_face(P, pal, 0, L, top, holes)
    coping(P, pal, top)
    cross(P, pal, TR, ZR + 0.35)
    for x in (0.3, L - 0.3):
        buttress(P, pal, x, 6.4, d0=0.9)
    C.put(P, (S_E - 0.1, 0), (S_E - 0.1, T_N), "east")
    # --- chancel: five-light east window under a coped gable, short side walls
    s0, s1, t0, t1 = CH
    P = C.P()
    L = t1 - t0
    top = [(0, CH_E), (L / 2, CH_R), (L, CH_E)]
    wall_face(P, pal, 0, L, top, [window(P, pal, L / 2, 4.0, 2.3, 8.0, 5)])
    coping(P, pal, top)
    for x in (0.3, L - 0.3):
        buttress(P, pal, x, 5.8, d0=0.9)
    C.put(P, (s1, t0), (s1, t1), "chancel_e")
    for A, B, nm in (((s0, t0), (s1, t0), "chancel_s"), ((s1, t1), (s0, t1), "chancel_n")):
        P = C.P()
        L = math.dist(A, B)
        wall_face(P, pal, -0.1, L + 0.1, [(-0.1, CH_E), (L + 0.1, CH_E)], [])
        C.put(P, A, B, nm)
    C.gable_roof(s0 - 0.1, s1, t0, t1, None, CH_E, (t0 + t1) / 2, CH_R, pal.roof, ov=0.0, verge=0.0)
    # --- SW block: plain flat-roofed ashlar block with a two-light window per face and a parapet
    a0, a1, b0, b1 = SW
    for A, B, nm, win in (((a1, b1), (a0, b1), "sw_n", False), ((a0, b1), (a0, b0), "sw_w", True),
                          ((a0, b0), (a1, b0), "sw_s", True)):
        P = C.P()
        L = math.dist(A, B)
        if nm == "sw_w":    # annotation :4 (walked t 5.56 -> 0): door at 2.4 (w 1.6, h 2.6), window over it
            holes = [door(P, pal, 2.4, 1.6, 2.6), window(P, pal, 2.4, 1.5, 4.2, 7.0, 2)]
        else:
            holes = [window(P, pal, L / 2, 1.3, 2.2, 5.4, 2)] if win else []
        wall_face(P, pal, -0.1, L + 0.1, [(-0.1, Z_SW - 0.8), (L + 0.1, Z_SW - 0.8)], holes)
        parapet(P, pal, -0.12, L + 0.12, Z_SW - 0.8, Z_SW, embattled=True)
        C.put(P, A, B, nm)
    C.flat(a0 + 0.1, a1, b0 + 0.1, b1 - 0.1, Z_SW - 0.9, LEAD)
    # --- nave roof: low-pitched slate, eaves just behind the parapets
    C.gable_roof(0.0, S_E - 0.1, 0.0, T_N, None, 9.0, TR, ZR, pal.roof, ov=0.0, verge=0.0)
    # --- west tower
    s0, s1, t0, t1 = TW
    corners = [(s0, t1), (s0, t0), (s1, t0), (s1, t1)]   # outside on the right: west face first (walking south)
    zp = Z_TW - 1.0
    for i in range(4):
        A, B = corners[i], corners[(i + 1) % 4]
        L = math.dist(A, B)
        P = C.P()
        holes = [window(P, pal, L / 2, 1.8, 15.4, 18.8, 2, louvre=True)]
        if i == 0:
            zlow = -0.6
            holes += [door(P, pal, L / 2, 1.7, 3.4), window(P, pal, L / 2, 2.3, 5.0, 9.0, 3),
                      window(P, pal, L / 2, 0.7, 11.2, 13.2, 1)]
        else:
            zlow = roof_z(TR if i == 2 else A[1]) - 0.4   # start just below the nave roof
            if i == 3:
                holes.append(window(P, pal, L / 2, 0.7, 12.4, 13.8, 1))
        g = box(-0.08, zlow, L + 0.08, zp).difference(unary_union(holes))
        P.face_xz(g, Y, pal.wall, mat="stone")
        if i == 0:
            P.extrude_profile([(Y - 0.05, -0.6), (Y + 0.22, -0.6), (Y + 0.22, 0.4), (Y + 0.04, 0.6),
                               (Y - 0.05, 0.6)], -0.08, L + 0.08, pal.dress, mat="stone")   # plinth
            for x in (0.3, L - 0.3):
                buttress(P, pal, x, 13.6, d0=0.9, bw=0.7)
        for zc in (10.0, 14.6):
            if zc > zlow + 0.3:
                P.extrude_profile([(Y - 0.05, zc - 0.2), (Y + 0.12, zc - 0.2), (Y + 0.18, zc),
                                   (Y - 0.05, zc + 0.04)], -0.1, L + 0.1, pal.dress, mat="stone")
        parapet(P, pal, -0.12, L + 0.12, zp, Z_TW, embattled=True)
        for x in (0.2, L - 0.2):          # corner pinnacles with a small pyramid cap
            P.box(x - 0.24, x + 0.24, Y - 0.1, Y + 0.38, Z_TW, Z_TW + 1.1, pal.dress, mat="stone")
            P.box(x - 0.12, x + 0.12, Y + 0.02, Y + 0.26, Z_TW + 1.1, Z_TW + 1.7, pal.dress, mat="stone")
        C.put(P, A, B, "tower%d" % i)
    C.flat(s0 + 0.2, s1 - 0.2, t0 + 0.2, t1 - 0.2, zp - 0.1, LEAD)
    return C.done()


BUILDS = {OSM: build}
ELEMENTS = {}   # not in walls.json (ring 1, outside the Market Square zone)
HIDE_TILE = [OSM]

if __name__ == "__main__":
    items = build([])
    print(sum(len(i["tris"]) for i in items), round(max(float(np.asarray(i["tris"])[..., 2].max()) for i in items), 2))
