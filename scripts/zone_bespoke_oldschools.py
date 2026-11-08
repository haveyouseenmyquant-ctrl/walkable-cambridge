"""Bespoke geometry for the east front of the Old Schools (Stephen Wright, 1754-58) on the Senate House lawn,
session 37. OSM way/135762298 (building=university, ref A011, no name) is a 20.9 x 3.7 m strip in front of the
Old Schools east range (way/135762297, A011.2): exactly Wright's five-bay centre block with its open ground-floor
loggia (the footway way/135762307 runs through it from end to end, entering by open end arches at both ends).
The model is a complete closed exterior over the strip, so the tile body is hidden (HIDE_TILE) and the arcade is
really open: five open round arches in a rusticated ground storey, a loggia (back wall, ceiling, open end arches),
then the piano nobile: five round-headed recesses, each with a window under alternating triangular / segmental
pediments over a balustraded apron; a frieze of carved swags, a modillion cornice and a balustrade with
pedestals and urns over the piers. Flat lead roof behind the balustrade (the A011.2 tile body rises behind it).
The south end bay (part of way/135762301) and the Cockerell building (way/95406725) keep their generic skins.
zone_build.load_bespoke() picks up BUILDS; the building is outside the Market Square walls.json (no ELEMENTS).

Frame: x = metres north along the front from the OSM SE corner (E -233.1 N 41.1) to the NE corner (E -235.1
N 61.9), 20.9 m, axis 5.5 deg west of grid north; y = metres out of the building (east, onto the lawn); z above
Z0 = 9.6 (DTM 9.6 on the lawn along the whole front).

Design (shape / proportion / colour only, no pixels used):
- "Old Schools from Kings Parade, Cambridge, UK - Diliff.jpg" (Diliff, CC BY-SA 3.0);
- "Cambridge - King's Parade - View WNW on Old Schools 1837 & Senate House 1730.jpg" (Txllxt TxllxT, CC BY-SA 4.0).
Pale grey-buff ashlar (Ketton type), a shade warmer than the Senate House's Portland stone.
Heights from the LiDAR DSM (data/lidar/dsm_1m.tif; 2023 first-return DSM as check) sampled 0.5-1.5 m inside the
front: balustrade 22.2-23.2 (= 12.6-13.6 above Z0; model rail 12.85, pedestals 13.05, urns 14.1); 3 m inside
23.6-24.2 (the A011.2 roof starts there), ridge 25.2 at 5 m (A011.2 tile body, not modelled).
"""
import math
import os
import sys

import numpy as np
from shapely.geometry import Point, Polygon, box
from shapely.ops import unary_union

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import facade_parts as F  # noqa: E402
from zone_bespoke_kings import lathe, box6, face_yz, face_xy, slab2, frame_world  # noqa: E402

OSM = "way/135762298"
Z0 = 9.6
A = np.array([-233.1, 41.1])
B_ = np.array([-235.1, 61.9])
LEN = float(np.linalg.norm(B_ - A))      # 20.9
D = (B_ - A) / LEN
DEP = 3.65                               # strip depth (back wall in front of the A011.2 tile wall)
NB = 5
BW = LEN / NB                            # 4.18 m bays
TW = 0.6                                 # front wall thickness

STONE = F.rgb("#e2d8c2")
STONE_D = F.shade(STONE, 0.72)
STONE_L = F.shade(STONE, 1.05)
SHADOW = F.shade(STONE, 0.6)
GLASS = F.rgb(F.GLASS_COL)
SASH = F.rgb("#ece8de")
LEAD = F.rgb("#7f8589")

Z_GS = 5.2          # ground storey top (string course)
Z_FR = 10.45        # frieze bottom
Z_COR = 11.45       # cornice top
Z_BAL = 12.85       # balustrade rail top
Z_PED = 13.05       # pedestal tops
AW, AS = 2.5, 2.75  # loggia arch width, springing (apex AS + AW/2 = 4.0)


def P_():
    return F.Parts(mat="stone", wall_col=STONE)


def arch(xc, w, z0, zs, n=10):
    r = w / 2
    pts = [(xc + r * math.cos(a), zs + r * math.sin(a)) for a in np.linspace(0, math.pi, n)]
    return Polygon([(xc + r, z0)] + pts + [(xc - r, z0)])


def bays():
    return [BW * (i + 0.5) for i in range(NB)]


# ------------------------------------------------------------------ ground storey: rusticated open arcade

def rustication(P, x0, x1, holes, y=0.0, z1=Z_GS - 0.25):
    """Banded rustication: courses 0.5 m with recessed joints; voussoirs and keystones round the arches."""
    face = box(x0, -0.5, x1, z1)
    if holes:
        face = face.difference(unary_union([h.buffer(0.6, join_style=1, resolution=4) for h in holes]))
    P.face_xz(box(x0, -0.5, x1, z1).difference(unary_union(holes)) if holes else box(x0, -0.5, x1, z1), y, STONE_D)
    z = -0.5
    while z < z1 - 0.05:
        band = box(x0, z + 0.03, x1, min(z + 0.47, z1)).intersection(face)
        if not band.is_empty:
            P.slab(band, y, y + 0.06, STONE)
        z += 0.5


def voussoirs(P, xc, w, zs, y=0.0, n=9, depth=0.55):
    r0, r1 = w / 2, w / 2 + depth
    for k in range(n):
        a0 = math.pi * k / n + 0.012
        a1 = math.pi * (k + 1) / n - 0.012
        key = k == n // 2
        rr = r1 + (0.2 if key else 0.0)
        g = Polygon([(xc + r0 * math.cos(a0), zs + r0 * math.sin(a0)), (xc + rr * math.cos(a0), zs + rr * math.sin(a0)),
                     (xc + rr * math.cos(a1), zs + rr * math.sin(a1)), (xc + r0 * math.cos(a1), zs + r0 * math.sin(a1))])
        P.slab(g, y, y + (0.12 if key else 0.07), STONE_L if key else STONE)


def front(P):
    holes_g = [arch(x, AW, -0.6, AS) for x in bays()]
    rustication(P, 0.0, LEN, holes_g)
    for x, h in zip(bays(), holes_g):
        voussoirs(P, x, AW, AS)
        P.sides_xz(h, -TW, 0.0, STONE_D, inward=True, skip_ground=True)
        for sx in (-1, 1):   # impost blocks
            xa = x + sx * AW / 2
            P.box(min(xa, xa + sx * 0.4), max(xa, xa + sx * 0.4), 0.0, 0.1, AS - 0.22, AS, STONE_L)
    # inner face of the arcade wall (seen from the loggia)
    P.face_xz(box(0, -0.6, LEN, Z_GS + 0.1).difference(unary_union(holes_g)), -TW, STONE_D, n=(0, -1, 0))
    # string course over the ground storey
    P.extrude_profile([(0, Z_GS - 0.25), (0.14, Z_GS - 0.2), (0.14, Z_GS + 0.1), (0.22, Z_GS + 0.18),
                       (0.22, Z_GS + 0.3), (0, Z_GS + 0.3)], -0.05, LEN + 0.05, STONE_L)
    # piano nobile
    holes = []
    for i, x in enumerate(bays()):
        rec = arch(x, 2.6, 5.95, 8.75, n=12)
        P.face_xz(rec.difference(box(x - 0.625, 6.45, x + 0.625, 8.6)), -0.16, STONE, mat="stone")
        P.sides_xz(rec, -0.16, 0.0, STONE_D, inward=True)
        holes.append(rec)
        # archivolt round the recess
        ring = rec.buffer(0.2, join_style=1, resolution=6).difference(rec).intersection(box(x - 2, 8.75, x + 2, 11))
        P.slab(ring, 0.0, 0.06, STONE_L)
        P.box(x - 0.18, x + 0.18, 0.0, 0.14, 9.85, 10.3, STONE_L)   # keystone
        win(P, x, i)
    P.face_xz(box(0, Z_GS + 0.3, LEN, Z_FR).difference(unary_union(holes)), 0.0, STONE)
    # piers: shallow rusticated pilaster strips between the bays
    for k in range(NB + 1):
        x = k * BW
        a, b = max(0.0, x - 0.4), min(LEN, x + 0.4)
        z = Z_GS + 0.3
        while z < Z_FR - 0.1:
            P.box(a, b, 0.0, 0.06, z + 0.03, min(z + 0.47, Z_FR - 0.05), STONE_L, bottom=False)
            z += 0.5
    # frieze of swags, cornice
    P.face_xz(box(0, Z_FR, LEN, Z_COR - 0.4), 0.0, STONE)
    for x in bays():
        for dx in (-1.0, 1.0):
            c = Point(x + dx, Z_FR + 0.62).buffer(0.62, resolution=8)
            swag = c.difference(Point(x + dx, Z_FR + 0.75).buffer(0.55, resolution=8)).intersection(
                box(x + dx - 1, Z_FR - 1, x + dx + 1, Z_FR + 0.55))
            P.slab(swag, 0.0, 0.1, STONE_L)
            P.slab(Point(x + dx - 0.62, Z_FR + 0.62).buffer(0.09, resolution=2), 0.0, 0.12, STONE_L)   # ties
    P.extrude_profile([(0, Z_COR - 0.4), (0.1, Z_COR - 0.36), (0.1, Z_COR - 0.28), (0.3, Z_COR - 0.24),
                       (0.3, Z_COR - 0.14), (0.62, Z_COR - 0.08), (0.62, Z_COR), (0, Z_COR)], -0.05, LEN + 0.05,
                      STONE_L)
    nm = int(LEN / 0.55)
    for k in range(nm):   # modillions
        x = (k + 0.5) * LEN / nm
        P.box(x - 0.07, x + 0.07, 0.1, 0.52, Z_COR - 0.24, Z_COR - 0.08, STONE_L)


def win(P, x, i):
    """Window in the arched recess: architrave, sashes, pediment (triangular / segmental alternately), apron."""
    w, z0, z1 = 1.25, 6.45, 8.6
    yr = -0.16
    op = box(x - w / 2, z0, x + w / 2, z1)
    P.sides_xz(op, yr - 0.25, yr, STONE_D, inward=True)
    P.face_xz(op, yr - 0.25, GLASS, mat="glass")
    # sash bars 3 x 4
    bars = [op.difference(op.buffer(-0.07, join_style=2))]
    for c in (1, 2):
        xx = x - w / 2 + w * c / 3
        bars.append(box(xx - 0.02, z0, xx + 0.02, z1))
    for r in (1, 2, 3):
        zz = z0 + (z1 - z0) * r / 4
        bars.append(box(x - w / 2, zz - 0.02, x + w / 2, zz + 0.02))
    P.slab(unary_union(bars).intersection(op), yr - 0.25, yr - 0.19, SASH, mat="frame")
    # recess back face around the window must not cover the opening: punch it by drawing the architrave over it
    arc = op.buffer(0.16, join_style=2).difference(op)
    P.slab(arc, yr, yr + 0.07, STONE_L)
    for sx in (-1, 1):   # ears of the architrave
        P.box(x + sx * (w / 2 + 0.16) - 0.08, x + sx * (w / 2 + 0.16) + 0.08, yr, yr + 0.07, z1 - 0.1, z1 + 0.16, STONE_L)
    # frieze + pediment
    P.box(x - w / 2 - 0.2, x + w / 2 + 0.2, yr, yr + 0.12, z1 + 0.16, z1 + 0.32, STONE_L)
    zb = z1 + 0.32
    if i % 2 == 0:
        ped = Polygon([(x - w / 2 - 0.3, zb), (x + w / 2 + 0.3, zb), (x, zb + 0.5)])
    else:
        r = 1.3
        cz = zb + 0.42 - r
        pts = [(x + r * math.cos(a), cz + r * math.sin(a)) for a in np.linspace(math.radians(60), math.radians(120), 7)]
        ped = Polygon([(x + w / 2 + 0.3, zb)] + [(x + w / 2 + 0.3, max(zb + 0.01, pts[0][1]))] + pts +
                      [(x - w / 2 - 0.3, max(zb + 0.01, pts[-1][1])), (x - w / 2 - 0.3, zb)])
    P.slab(ped.difference(ped.buffer(-0.1, join_style=2)), yr, yr + 0.16, STONE_L)
    P.slab(ped.buffer(-0.1, join_style=2), yr, yr + 0.05, STONE)
    # balustraded apron under the window
    P.box(x - w / 2 - 0.25, x + w / 2 + 0.25, yr, yr + 0.14, z0 - 0.12, z0, STONE_L, bottom=True)
    P.box(x - w / 2 - 0.25, x + w / 2 + 0.25, yr, yr + 0.12, Z_GS + 0.3, Z_GS + 0.45, STONE_L)
    nb = 5
    for k in range(nb):
        xb = x - w / 2 + (k + 0.5) * w / nb
        lathe(P, xb, yr + 0.02, [(0.07, Z_GS + 0.45), (0.05, Z_GS + 0.55), (0.09, Z_GS + 0.72), (0.04, z0 - 0.25),
                                 (0.07, z0 - 0.12)], STONE_L, n=6)
    P.face_xz(box(x - w / 2 - 0.25, Z_GS + 0.45, x + w / 2 + 0.25, z0 - 0.12), yr - 0.08, SHADOW)


def balustrade(P, x0, x1):
    y0, y1 = -0.45, 0.1
    yc = (y0 + y1) / 2
    zb = Z_COR
    P.box(x0, x1, y0, y1, zb, zb + 0.3, STONE, bottom=False)
    box6(P, x0, x1, y0 - 0.05, y1 + 0.05, Z_BAL - 0.3, Z_BAL, STONE_L, bottom=True)
    posts = [k * BW for k in range(NB + 1)]
    posts = [min(max(p, 0.35), LEN - 0.35) for p in posts]
    for p in posts:
        box6(P, p - 0.35, p + 0.35, y0 - 0.08, y1 + 0.08, zb, Z_PED, STONE)
        box6(P, p - 0.4, p + 0.4, y0 - 0.12, y1 + 0.12, Z_PED - 0.1, Z_PED, STONE_L)
        prof = [(0.26, 0.0), (0.26, 0.1), (0.12, 0.18), (0.1, 0.28), (0.28, 0.5), (0.31, 0.68), (0.22, 0.84),
                (0.12, 0.9), (0.15, 0.94), (0.05, 1.02), (0.0, 1.05)]
        lathe(P, p, yc, [(r, Z_PED + h) for r, h in prof], STONE_L, n=8)
    prof = [(0.09, 0.0), (0.065, 0.12), (0.12, 0.38), (0.05, 0.72), (0.09, 0.88), (0.09, 1.0)]
    zl, zh = zb + 0.3, Z_BAL - 0.3
    for a, b in zip(posts[:-1], posts[1:]):
        s0, s1 = a + 0.35, b - 0.35
        n = int((s1 - s0) / 0.29)
        for k in range(n):
            lathe(P, s0 + (s1 - s0) * (k + 0.5) / n, yc, [(r, zl + h * (zh - zl)) for r, h in prof], STONE, n=6)


def loggia_and_shell(P):
    """Back wall, ceiling, end walls with open arches, lead roof."""
    yb = -DEP + 0.05
    # back wall of the loggia: two doors and plain ashlar
    doors = [box(x - 0.6, 0, x + 0.6, 2.7) for x in (bays()[1], bays()[3])]
    P.face_xz(box(0, 0, LEN, 4.7).difference(unary_union(doors)), yb, STONE_D)
    for d in doors:
        P.face_xz(d, yb - 0.01, F.rgb("#4a3a2c"), mat="timber")
        P.slab(d.buffer(0.12, join_style=2).difference(d), yb, yb + 0.06, STONE)
    # loggia ceiling (flat, with transverse ribs at the piers)
    face_xy(P, box(0, -TW, LEN, yb), 4.7, F.shade(STONE, 0.66), nz=-1, mat="stone")
    for k in range(1, NB):
        x = k * BW
        P.add([[(x - 0.2, -TW, 4.45), (x + 0.2, -TW, 4.45), (x + 0.2, yb, 4.45)],
               [(x - 0.2, -TW, 4.45), (x + 0.2, yb, 4.45), (x - 0.2, yb, 4.45)]], (0, 0, -1), STONE_D)
        for xx, nx in ((x - 0.2, -1), (x + 0.2, 1)):
            P.quad((xx, -TW, 4.45), (xx, yb, 4.45), (xx, yb, 4.7), (xx, -TW, 4.7), (nx, 0, 0), STONE_D)
    # end walls: open arch through each end (loggia path), solid above
    ea = arch(-(DEP / 2), 2.0, -0.6, 2.6, n=10)   # in (y, z) with y negative
    for x, nx in ((0.0, -1), (LEN, 1)):
        g = box(-DEP, -0.6, 0.0, Z_COR).difference(ea)
        face_yz(P, g, x, STONE, nx)
        face_yz(P, g, x - nx * 0.6, STONE_D, -nx)
        for p in F.polys(ea):
            cs = np.asarray(p.exterior.coords)
            for (ay, az), (by, bz) in zip(cs[:-1], cs[1:]):
                if az < 0 and bz < 0:
                    continue
                P.quad((x, ay, az), (x - nx * 0.6, ay, az), (x - nx * 0.6, by, bz), (x, by, bz), (0, 0, -1), STONE_D)
        # rustication bands on the ends
        z = -0.5
        while z < Z_GS - 0.3:
            band = box(-DEP, z + 0.03, 0.0, z + 0.47).difference(ea.buffer(0.5, join_style=1, resolution=4))
            face_yz(P, band, x + nx * 0.06, STONE, nx)
            z += 0.5
    # flat lead roof behind the balustrade, back to the A011.2 tile wall
    face_xy(P, box(0, -DEP, LEN, -0.45), Z_COR + 0.05, LEAD, nz=1, mat="plain")


def build(walls=None):
    P = P_()
    front(P)
    balustrade(P, 0.0, LEN)
    loggia_and_shell(P)
    out = frame_world(P, A, D, "oldschools:east_front", z0=Z0)
    return [out] if out is not None else []


BUILDS = {OSM: build}
HIDE_TILE = [OSM]   # complete closed model of the strip (the loggia arches are open)
ELEMENTS = {}       # not in walls.json

if __name__ == "__main__":
    items = build([])
    for it in items:
        Tz = np.asarray(it["tris"])[..., 2]
        print(it["name"], len(it["tris"]), round(float(Tz.min()), 2), round(float(Tz.max()), 2))
    print("total", sum(len(i["tris"]) for i in items))
