"""Bespoke geometry for Holy Trinity Church, Market Street / Sidney Street (OSM way/26269190), session 61, ring 1.
zone_build.load_bespoke() picks up BUILDS / HIDE_TILE (replaces detail.py's generic 'gothic' landmark).

Form (shape / proportion / colour only; general knowledge of the church and the Commons category "Holy Trinity
Church, Cambridge", no held-out benchmark photos): a Perpendicular town church in pale clunch/limestone ashlar, an
aisled nave with a clerestory, transepts, a chancel, embattled parapets over low-pitched lead roofs, big
three/four-light Perpendicular windows between buttresses, and a west tower with a belfry stage, battlements, corner
pinnacles and a short lead spire.

Heights come from the LiDAR DSM (data/lidar/dsm_1m.tif), read on a grid over the footprint in s62 (aisle parapets ~6 m,
nave / transepts / chancel ~10.6 m above Z0 = 8.8); each wall takes the height of the roof region behind it. The DSM peak (33.6 m) sits over the west
end at about (-26.6, 122.5): tower ~5.4 m square, battlements at 17.4 m, spire tip 24.8 m. The model keeps the OSM
outline (tile collision); the tower is set into the west end of the nave.
"""
import math
import os
import sys

import mapbox_earcut as earcut
import numpy as np
from shapely.geometry import Point, Polygon, box
from shapely.ops import unary_union

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import facade_parts as F  # noqa: E402
from zone_bespoke_churches import (Church, Pal, window, door, buttress, parapet, wall_face, Y, LEAD,  # noqa: E402
                                   LOUVRE)

OSM = "way/26269190"
Z0 = 8.8
PTS = [(-20.33, 138.2), (-11.43, 140.54), (-9.29, 132.48), (0.37, 135.03), (2.7, 126.27), (-8.14, 123.41),
       (-6.11, 115.78), (-17.26, 113.27), (-17.85, 115.99), (-26.59, 114.09), (-31.06, 132.09), (-19.51, 135.13)]
TOWER_C = (-26.6, 122.6)
TOWER_W = 5.4
Z_TW, Z_SPIRE = 17.4, 24.8
DOORS = {9: 0.45}   # edge index -> door position (fraction along): west door on Market Street side of the tower


def build(walls=None):
    pal = Pal("#cdbf9f", "#ddd2b6", "#7d8387")
    pts = [np.asarray(p, float) for p in PTS]
    poly = Polygon(PTS)
    if not poly.exterior.is_ccw:  # walk counter-clockwise so the outside is on the right of every edge (Church.put)
        pts = pts[::-1]
    U = (np.asarray(PTS[11]) - np.asarray(PTS[10]))
    C = Church("holytrinity", PTS[9], U, Z0, pal)
    # roof regions (local s, t; DSM grid checked in s62): the nave band T_S..T_N between the tower and the crossing
    # (s 12.2) is high (clerestory); the transepts and chancel east of the crossing are high, and so is the south
    # transept's west bay (s 8.8-12.2, t < T_S); the aisles either side of the nave and the tower's flanks are low
    loc = [tuple(np.linalg.solve(np.c_[C.U, C.V], np.asarray(p) - C.O)) for p in PTS]
    lpoly = Polygon(loc)
    T_S, T_N = 4.2, 14.2          # nave clerestory band (aisles are t < 4.2 and t > 14.2 west of the transepts)
    S_X = loc[11][0]              # crossing / north transept west wall (12.2)
    S_ST = loc[7][0]              # south transept west wall (8.8)
    high = unary_union([lpoly.intersection(box(TOWER_W - 0.3, T_S, S_X + 0.01, T_N)),
                        lpoly.intersection(box(S_X, -5, 60, 40)), lpoly.intersection(box(S_ST, -5, S_X + 0.01, T_S))])
    low = lpoly.difference(high)
    n = len(pts)
    edges = []
    for i in range(n):
        a, b = pts[i], pts[(i + 1) % n]
        L = float(np.linalg.norm(b - a))
        d = (b - a) / L
        inn = np.array([-d[1], d[0]])        # left of a counter-clockwise walk = inside
        # s62: wall height follows the roof region behind it (1 m inside the midpoint), so no lead flat overhangs a
        # lower wall; per-edge DSM medians misread the short transept walls and the tree-shaded north transept end
        m = a + d * L / 2 + inn * 1.0
        h = 10.6 if high.contains(Point(*np.linalg.solve(np.c_[C.U, C.V], m - C.O))) else 6.0
        edges.append((a, b, L, h))
    # walls: Perpendicular windows between buttresses, embattled parapet
    for i, (a, b, L, h) in enumerate(edges):
        P = C.P()
        ze = h - 0.9
        holes, bx = [], []
        if L > 2.5:
            nb = max(1, int(round(L / 3.6)))
            step = L / nb
            for k in range(nb):
                xc = step * (k + 0.5)
                if i in DOORS and abs(xc / L - DOORS[i]) < 0.5 / nb:
                    holes.append(door(P, pal, xc, 1.5, 3.0))
                    continue
                tall = h > 8 and step > 4.5
                w = min(2.6, step - 1.1) if tall else min(2.0, step - 1.0)
                lights = 4 if w > 2.3 else (3 if w > 1.5 else 2)
                if w > 0.7:
                    zb, zt = (2.2, ze - 1.0) if not (h > 8 and L > 8) else (2.4, ze - 1.2)
                    if L < 9 and h > 8:      # gable-like transept / chancel end walls: one big window
                        if k != nb // 2:
                            continue
                        w, lights, zb, zt = min(L - 2.2, 4.2), 5, 2.4, ze - 1.0
                    holes.append(window(P, pal, xc, w, zb, zt, lights))
            bx = [step * k for k in range(nb + 1)]
        wall_face(P, pal, -0.1, L + 0.1, [(-0.1, ze), (L + 0.1, ze)], holes)
        parapet(P, pal, -0.15, L + 0.15, ze, h, embattled=True)
        for x in bx:
            buttress(P, pal, min(max(x, 0.3), L - 0.3), min(ze - 1.0, 4.6), d0=0.8)
        C.put(P, tuple(np.linalg.solve(np.c_[C.U, C.V], a - C.O)), tuple(np.linalg.solve(np.c_[C.U, C.V], b - C.O)),
              "w%d" % i)
    # clerestory: the nave / transept / chancel core is the footprint minus the low aisle strips; its walls stand on
    # the boundary between the two roof levels, with windows, and carry a parapet at 10.6
    for t, (A, B) in ((T_S, ((TOWER_W - 0.3, T_S), (S_ST, T_S))), (T_N, ((S_X, T_N), (TOWER_W - 0.3, T_N)))):
        P = C.P()
        L = abs(B[0] - A[0])
        holes = [window(P, pal, x, 1.6, 6.6, 9.0, 3) for x in np.arange(1.2, L - 0.8, 2.6)]
        g = box(-0.1, 5.4, L + 0.1, 9.7).difference(unary_union(holes)) if holes else box(-0.1, 5.4, L + 0.1, 9.7)
        P.face_xz(g, Y, pal.wall, mat="stone")
        parapet(P, pal, -0.1, L + 0.1, 9.7, 10.6, embattled=True)
        C.put(P, A, B, "clere%d" % int(t))
    # s62: clerestory west ends either side of the tower (nave roof edge above the aisle roofs)
    for A, B in (((TOWER_W - 0.3, T_S), (TOWER_W - 0.3, 5.4)), ((TOWER_W - 0.3, 5.4 + TOWER_W), (TOWER_W - 0.3, T_N)),
                 ((S_ST, loc[8][1]), (S_ST, T_S)), ((S_X, T_N), (S_X, loc[11][1]))):   # + transept west walls over the aisles
        P = C.P()
        L = math.dist(A, B)
        P.face_xz(box(-0.05, 5.0, L + 0.05, 9.7), Y, pal.wall, mat="stone")
        parapet(P, pal, -0.1, L + 0.1, 9.7, 10.6, embattled=True)
        C.put(P, B, A, "clerew%d_%d" % (int(A[0]), int(A[1])))
    # roofs: low-pitched lead, laid flat just under the parapet tops (the pitch is hidden behind the battlements)
    for g, z in ((low, 5.2), (high, 9.8)):
        for part in getattr(g, "geoms", [g]):
            if part.area < 0.5:
                continue
            ring = np.asarray(part.simplify(0.05).exterior.coords)[:-1]
            idx = earcut.triangulate_float64(ring, np.array([len(ring)], dtype=np.uint32)).reshape(-1, 3)
            C.roof([[(ring[k][0], ring[k][1], z) for k in tri] for tri in idx], LEAD)
    # west tower: square shaft set into the west end, belfry with louvres, battlements, pinnacles, lead spire
    s0, s1, t0, t1 = -0.3, TOWER_W - 0.3, 5.4, 5.4 + TOWER_W
    corners = [(s0, t1), (s0, t0), (s1, t0), (s1, t1)]    # outside on the right: west face first (walking south)
    zb0 = Z_TW - 0.9
    for i in range(4):
        A, B = corners[i], corners[(i + 1) % 4]
        L = math.dist(A, B)
        P = C.P()
        holes = [window(P, pal, L / 2, 1.7, 12.0, 15.2, 2, louvre=True)]
        zlow = (0.0, 5.0, 9.6, 5.0)[i]    # s62: down to the aisle roofs (5.2) N/S, the nave roof (9.8) E
        if i == 0:
            holes.append(window(P, pal, L / 2, 1.6, 6.2, 9.4, 3))
        g = box(-0.08, zlow, L + 0.08, zb0).difference(unary_union(holes))
        P.face_xz(g, Y, pal.wall, mat="stone")
        for zc in (10.6, 11.6):
            P.extrude_profile([(Y - 0.05, zc - 0.2), (Y + 0.12, zc - 0.2), (Y + 0.18, zc), (Y - 0.05, zc + 0.04)],
                              -0.1, L + 0.1, pal.dress, mat="stone")
        parapet(P, pal, -0.12, L + 0.12, zb0, Z_TW, embattled=True)
        for x in (0.15, L - 0.15):        # corner pinnacles
            P.box(x - 0.22, x + 0.22, Y - 0.1, Y + 0.34, Z_TW, Z_TW + 1.3, pal.dress, mat="stone")
        C.put(P, A, B, "tower%d" % i)
    sc, tc = (s0 + s1) / 2, (t0 + t1) / 2
    r0 = TOWER_W * 0.3
    ring = [C.w(sc + r0 * math.cos(a), tc + r0 * math.sin(a)) for a in np.arange(8) * math.pi / 4 + math.pi / 8]
    apex = (*C.w(sc, tc), Z0 + Z_SPIRE)
    zs = Z0 + Z_TW - 0.6
    tris = [[(*ring[k], zs), (*ring[(k + 1) % 8], zs), apex] for k in range(8)]
    C.out.append({"name": "holytrinity:spire", "tris": np.asarray(tris), "col": np.asarray([F.shade(LEAD, 0.95)] * 8),
                  "mat": "plain"})
    C.flat(s0, s1, t0, t1, zb0 - 0.05)   # tower roof under the spire (s62: walls do render; the s61 slab was the nave roof)
    return C.done()


BUILDS = {OSM: build}
ELEMENTS = {}   # not in walls.json (ring 1, outside the Market Square zone)
HIDE_TILE = [OSM]

if __name__ == "__main__":
    items = build([])
    print(sum(len(i["tris"]) for i in items), round(max(float(np.asarray(i["tris"])[..., 2].max()) for i in items), 2))
