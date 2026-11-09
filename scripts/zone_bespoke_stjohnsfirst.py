"""Bespoke street (east) front of St John's College First Court east range on St John's Street (ring 2), session 74:
the brick ranges either side of the Great Gate (zone_bespoke_stjohnsgate.py builds the gate tower and its turrets).

OSM: way/158913878 (JOH010). Its street wall, south -> north (local x along the gate frame of zone_bespoke_stjohnsgate):
- south range: (E -199.86, N 304.17) -> (E -191.02, N 324.79), 22.4 m, ending at the south street turret of the gate;
- north range: (E -186.48, N 334.84) -> (E -180.23, N 348.61), 15.1 m, from the north street turret;
- north end: the wall steps back 0.97 m, (E -181.14, N 349.02) -> (E -178.05, N 355.48), 7.2 m (towards the chapel).
Pseudo-keyed ("way/158913878:first") so the tile body (LiDAR roof) and the city skin stay; every face sits Y = 0.65 m
proud of its OSM wall line so the window glass (Y - 0.3) clears the city skin (0.25 m out) -- the s72 Clare bug.
Frames: x along the wall (northwards), y out of the building (towards St John's Street), z above the range's Z0.

Heights from the LiDAR DSM (data/lidar/dsm_1m.tif) and DTM: ground 9.2 (south end) to 8.6 (north end); the DSM 0.5-1.5 m
inside the wall reads 18.2-18.9 (parapet / eaves line ~9.7 m over ground), ridge ~19.8 at 3.5 m in; chimney spikes at
x ~24 (24.0 at 3.5 m in), x ~-21 (20.8-21.9 at 5.5-6.5 m in) and x ~28 (21.3).

Design (general knowledge only; no photos used, nothing under data/benchmark opened): early Tudor red brick (1511-20) with
stone dressings, like the gate tower: three storeys of stone-mullioned two-light windows with four-centred light heads and
hood moulds, a stone plinth, stone string courses, a battlemented brick parapet with stone coping, a dark-header diaper,
brick chimney stacks with stone caps behind the parapet, one doorway on the south range.
UNVERIFIED (no photo check): the bay rhythm and light counts, whether the street front is battlemented, the door position.
"""
import math
import os
import sys

import numpy as np
from shapely.geometry import Polygon, box
from shapely.ops import unary_union

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import facade_parts as F  # noqa: E402
from zone_bespoke_kings import box6, tudor, frame_world  # noqa: E402
from zone_bespoke_stjohnsgate import lights, BRICK, STONE, STONE_D, STONE_L, OAK  # noqa: E402

KEY = "way/158913878:first"
Y = 0.65                       # face proud of the OSM wall line; glass at Y - 0.3 = 0.35 > skin 0.25
Z_STR1, Z_STR2 = 3.35, 6.55    # string courses
Z_PAR = 9.0                    # parapet base (cornice); merlon tops ~9.75
Z_MER = 9.75
FLOORS = [(0.95, 2.65), (4.05, 5.85), (7.1, 8.55)]
# (name, a, b, Z0, door bay or None, chimneys [(x, y, top over Z0)]), a/b local E,N south -> north
RANGES = [
    ("stjohns:first_court_east_south", (-199.86, 304.17), (-191.02, 324.79), 8.95, 2,
     [(1.2, -5.8, 12.4), (12.0, -5.5, 11.6)]),
    ("stjohns:first_court_east_north", (-186.48, 334.84), (-180.23, 348.61), 8.6, None,
     [(13.1, -3.4, 15.2)]),
    ("stjohns:first_court_east_end", (-181.14, 349.02), (-178.05, 355.48), 8.6, None,
     [(2.0, -2.5, 12.7)]),
]


def chimney(P, x, y, ztop):
    """Brick stack (two flues) with a stone cap and two pots, rising from behind the parapet."""
    z0 = Z_PAR - 1.0
    box6(P, x - 0.75, x + 0.75, y - 0.45, y + 0.45, z0, ztop - 0.35, BRICK, mat="brick")
    box6(P, x - 0.85, x + 0.85, y - 0.55, y + 0.55, ztop - 0.35, ztop - 0.2, STONE_L)
    box6(P, x - 0.8, x + 0.8, y - 0.5, y + 0.5, ztop - 0.6, ztop - 0.5, BRICK, mat="brick")   # oversailing course
    for u in (-0.38, 0.38):
        box6(P, x + u - 0.14, x + u + 0.14, y - 0.14, y + 0.14, ztop - 0.2, ztop, F.shade(BRICK, 0.8), mat="brick")


def doorway(P, xc, holes):
    """Four-centred stone doorway with an oak door, label mould over carved spandrels."""
    op = tudor(xc, 1.2, 0.0, 2.55, n=5)
    holes.append(op)
    P.sides_xz(op, Y - 0.45, Y, STONE_D, inward=True, skip_ground=True, mat="stone")
    P.face_xz(op, Y - 0.45, OAK, mat="timber")
    rib = [box(xc - 0.6 + k * 0.2 - 0.012, 0.0, xc - 0.6 + k * 0.2 + 0.012, 2.5) for k in range(1, 6)]
    P.slab(unary_union(rib).intersection(op), Y - 0.45, Y - 0.42, F.shade(OAK, 1.25), sides=False, mat="timber")
    dr = box(xc - 0.95, 0.0, xc + 0.95, 2.95)
    P.slab(dr.difference(op.buffer(0.02)), Y, Y + 0.05, STONE, mat="stone")
    holes.append(dr)
    P.slab(unary_union([box(xc - 1.05, 2.95, xc + 1.05, 3.08), box(xc - 1.05, 2.55, xc - 0.95, 3.08),
                        box(xc + 0.95, 2.55, xc + 1.05, 3.08)]), Y, Y + 0.12, STONE_L, mat="stone")
    P.count("door")


def range_front(name, a, b, z0, door, chim):
    a, b = np.array(a), np.array(b)
    L = float(np.linalg.norm(b - a))
    d = (b - a) / L
    P = F.Parts(mat="brick", wall_col=BRICK)
    nb = max(1, int(round(L / 3.7)))
    bw = L / nb
    holes = []
    for i in range(nb):
        xc = (i + 0.5) * bw
        for k, (za, zb) in enumerate(FLOORS):
            if k == 0 and door == i:
                doorway(P, xc, holes)
                continue
            lights(P, xc, za, zb, 2, holes, lw=0.48, y=Y)
            P.count("window")
    face = box(0.0, -0.6, L, Z_PAR).difference(unary_union(holes))
    P.face_xz(face, Y, BRICK, mat="brick")
    # dark-header diaper on the brick
    dia = []
    for k in range(-1, int(L / 0.9) + 2):
        for j in range(0, 10):
            cx, cz = k * 0.9 + (0.45 if j % 2 else 0.0), 0.9 + j * 0.9
            dia.append(Polygon([(cx, cz - 0.3), (cx + 0.3, cz), (cx, cz + 0.3), (cx - 0.3, cz)]).exterior.buffer(0.03, join_style=2, cap_style=2))
    dg = unary_union(dia).intersection(face.buffer(-0.15))
    P.slab(dg, Y, Y + 0.01, F.shade(BRICK, 0.8), sides=False, mat="brick")
    # stone plinth with a weathered top, string courses (broken by nothing: the windows sit between them)
    P.extrude_profile([(Y, -0.6), (Y + 0.15, -0.6), (Y + 0.15, 0.4), (Y, 0.55)], 0.0, L, STONE_D, mat="stone")
    for z in (Z_STR1, Z_STR2):
        P.extrude_profile([(Y, z - 0.1), (Y + 0.12, z - 0.06), (Y + 0.12, z + 0.06), (Y, z + 0.1)], 0.0, L, STONE_L,
                          mat="stone")
    # parapet: stone cornice, brick battlements with stone coping, back face
    P.extrude_profile([(Y, Z_PAR - 0.18), (Y + 0.2, Z_PAR), (Y + 0.2, Z_PAR + 0.08), (Y, Z_PAR + 0.1)], 0.0, L,
                      STONE_L, mat="stone")
    n = max(2, int(round(L / 1.5)))
    p = L / n
    g = box(0.0, Z_PAR, L, Z_PAR + 0.42)
    merl = [box(i * p + 0.3, Z_PAR + 0.4, (i + 1) * p - 0.3, Z_MER - 0.06) for i in range(n)]
    sl = unary_union([g] + merl)
    P.slab(sl, Y - 0.35, Y, BRICK, mat="brick")
    P.face_xz(sl, Y - 0.35, F.shade(BRICK, 0.8), n=(0, -1, 0), mat="brick")
    box6(P, 0.0, L, Y - 0.39, Y + 0.04, Z_PAR + 0.38, Z_PAR + 0.44, STONE_L)
    for i in range(n):
        box6(P, i * p + 0.26, (i + 1) * p - 0.26, Y - 0.39, Y + 0.04, Z_MER - 0.08, Z_MER, STONE_L)
    # ends: short returns back to the OSM wall line (the gate turrets hide the ends next to the gate)
    for xe, s in ((0.0, -1), (L, 1)):
        P.quad((xe, -0.05, -0.6), (xe, Y, -0.6), (xe, Y, Z_PAR + 0.42), (xe, -0.05, Z_PAR + 0.42), (s, 0, 0),
               F.shade(BRICK, 0.85), "brick")
    for (x, y, zt) in chim:
        chimney(P, x, y, zt)
    return frame_world(P, a, d, name, z0=z0)


def build(walls=None):
    return [it for it in (range_front(*r) for r in RANGES) if it]


BUILDS = {KEY: build}
ELEMENTS = {}

if __name__ == "__main__":
    tot = 0
    for it in build([]):
        Tz = np.asarray(it["tris"])[..., 2]
        tot += len(it["tris"])
        print(it["name"], len(it["tris"]), round(float(Tz.min()), 2), round(float(Tz.max()), 2))
    print("total", tot)
