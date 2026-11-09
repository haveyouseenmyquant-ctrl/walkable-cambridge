"""Bespoke geometry for the Gate of Honour, Gonville and Caius College (1573-75, after a design left by John Caius),
session 60, ring 1 (Senate House Passage). OSM way/137017447 is a small sheared quadrilateral, about 5.1 m along the
passage and 1.9 m deep; the model is a rectangle on its south edge (mean of the shear), facing south onto the passage.
It replaces build.py's detail.py 'gate' landmark (piers, a box, a hexagon and a dome), so the tile node is hidden;
collision is kept from the tile.

Frame: x = metres east along the south face from P0, y = metres out (south, into the passage), z above Z0 = 8.82
(DTM 8.79-8.86 round the footprint). The back (court) face is at y = -DEPTH.

Design (shape / proportion / colour only, no pixels used): the general form as recorded in the RCHME Cambridge
inventory and the Commons category "Gate of Honour" (non-benchmark views from the passage and from Caius Court).
- stage 1: round carriage arch with a moulded archivolt and keystone, flanked on each face by paired engaged
  columns on pedestals; full entablature with a frieze (the inscription band) and projecting cornice;
- stage 2: a narrower attic aedicule with small columns and a pediment on the passage side, four obelisks with balls
  at the corners of the first stage;
- stage 3: a hexagonal drum with a sundial on each face, then a stepped lead-covered cupola with a ball finial and
  weathervane.
Heights from the LiDAR DSM (data/lidar/dsm_1m.tif): top about 9.6 m above the passage (DSM peak 18.4 m). The DSM peak
sits about 2.5 m north of the OSM outline; the OSM position is kept because the tile collision uses it.
"""
import math
import os
import sys

import numpy as np
from shapely.geometry import Polygon, box

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import facade_parts as F  # noqa: E402
from zone_bespoke_kings import lathe, box6, place, frame_world  # noqa: E402

OSM = "way/137017447"
Z0 = 8.82
P0 = np.array([-242.88, 89.85])            # SW corner (south edge, mid-shear)
D = np.array([0.99677, 0.08030])           # along the south edge (OSM -243.46,89.80 -> -238.40,90.21)
L, DEPTH = 5.08, 1.92
XC = L / 2
YB = -DEPTH / 2                            # mid-depth (drum / cupola axis)

STONE = F.rgb("#c9bc9f")                    # weathered clunch / Ketton-type limestone
STONE_D = F.shade(STONE, 0.72)
STONE_L = F.shade(STONE, 1.07)
DIAL = F.rgb("#e9e5d8")
GILT = F.rgb("#b8913f")
OAK = F.rgb("#4a3828")
LEAD = F.rgb("#7c8286")
IRON = F.rgb("#2b2b2d")

AW, AS = 1.72, 2.25                        # arch span, springing height
AR = AW / 2
Z_ENT0, Z_ENT1 = 3.85, 4.65                # entablature
Z_ATT = 6.35                               # attic top (pediment base)
Z_DRUM0, Z_DRUM1 = 6.55, 8.05
Z_TOP = 9.6


def P_():
    return F.Parts(mat="stone", wall_col=STONE)


def arch_poly(xc, w, z0, zs, n=12):
    r = w / 2
    a = np.linspace(math.pi, 0, n + 1)
    return Polygon([(xc - r, z0)] + list(zip(xc + r * np.cos(a), zs + r * np.sin(a))) + [(xc + r, z0)])


def column(P, x, y, z0, z1, r, col=STONE):
    """Engaged column on a pedestal: pedestal z0..z0+0.85, base, shaft with entasis, Ionic-like capital."""
    zp = z0 + 0.85
    box6(P, x - r - 0.1, x + r + 0.1, y - r - 0.1, y + r + 0.1, z0, zp, STONE_D, bottom=False)
    box6(P, x - r - 0.14, x + r + 0.14, y - r - 0.14, y + r + 0.14, zp - 0.08, zp, STONE_L)
    zc = z1 - 0.22
    lathe(P, x, y, [(r + 0.06, zp), (r + 0.06, zp + 0.08), (r + 0.02, zp + 0.14), (r, zp + 0.2),
                    (r * 1.03, zp + (zc - zp) * 0.35), (r * 0.86, zc), (r * 0.95, zc + 0.04)], col, n=10)
    box6(P, x - r - 0.08, x + r + 0.08, y - r - 0.08, y + r + 0.08, zc + 0.04, z1, STONE_L)   # abacus
    for sx in (-1, 1):   # volutes as small drums either side
        lathe(P, x + sx * (r + 0.02), y + 0.0, [(0.0, zc - 0.02), (0.07, zc - 0.02), (0.08, zc + 0.05), (0.07, zc + 0.12),
                                               (0.0, zc + 0.12)], STONE_L, n=6)


def stage1(P):
    """Body with the arch through it, both faces, archivolts, columns, entablature."""
    body = box(0.0, 0.0, L, Z_ENT0)
    hole = arch_poly(XC, AW, 0.0, AS)
    face = body.difference(hole)
    for y, n in ((0.0, (0, 1, 0)), (-DEPTH, (0, -1, 0))):
        P.face_xz(face, y, STONE, n=n)
    # ends and the arch soffit
    P.quad((0, -DEPTH, 0), (0, 0, 0), (0, 0, Z_ENT0), (0, -DEPTH, Z_ENT0), (-1, 0, 0), STONE)
    P.quad((L, 0, 0), (L, -DEPTH, 0), (L, -DEPTH, Z_ENT0), (L, 0, Z_ENT0), (1, 0, 0), STONE)
    P.sides_xz(hole, -DEPTH, 0.0, STONE_D, inward=True, skip_ground=True)
    # plinth band
    for y, s in ((0.0, 1), (-DEPTH, -1)):
        P.add([], (0, 1, 0), STONE)
        g = box(0.0, 0.0, L, 0.35).difference(hole)
        P.face_xz(g, y + s * 0.06, STONE_D, n=(0, s, 0))
    for y, s in ((0.0, 1), (-DEPTH, -1)):
        # archivolt ring + keystone + imposts
        ring = arch_poly(XC, AW + 0.36, 0.0, AS).difference(hole).difference(box(-1, -1, L + 1, AS - 0.01))
        yy = y + s * 0.08
        P.face_xz(ring, yy, STONE_L, n=(0, s, 0))
        P.sides_xz(ring, min(y, yy), max(y, yy), STONE_L)
        kz = AS + AR
        box6(P, XC - 0.16, XC + 0.16, min(y, y + s * 0.14), max(y, y + s * 0.14), kz - 0.2, kz + 0.42, STONE_L)
        for sx in (-1, 1):
            xi = XC + sx * (AR + 0.09)
            box6(P, xi - 0.16, xi + 0.16, min(y, y + s * 0.1), max(y, y + s * 0.1), AS - 0.2, AS, STONE_L)
            # spandrel roundels
            g = Polygon([(XC + sx * (AR + 0.75) + 0.28 * math.cos(a), AS + 1.05 + 0.28 * math.sin(a))
                         for a in np.linspace(0, 2 * math.pi, 12, endpoint=False)])
            P.face_xz(g, y + s * 0.03, STONE_D, n=(0, s, 0))
        # paired engaged columns each side of the arch
        for x in (0.42, 1.0, L - 1.0, L - 0.42):
            column(P, x, y + s * 0.14, 0.0, Z_ENT0, 0.16)
    # entablature: architrave, frieze (inscription band), cornice (projecting on all four sides)
    for (z0, z1, o, c) in ((Z_ENT0, Z_ENT0 + 0.22, 0.18, STONE_L), (Z_ENT0 + 0.22, Z_ENT0 + 0.5, 0.14, STONE),
                           (Z_ENT0 + 0.5, Z_ENT0 + 0.62, 0.26, STONE_L), (Z_ENT0 + 0.62, Z_ENT1, 0.34, STONE_L)):
        box6(P, -o + 0.1, L + o - 0.1, -DEPTH - o, o, z0, z1, c, bottom=True)
    # inscription panel on the frieze, both faces
    for y, s in ((0.32 - 0.18 + 0.0, 1), (-DEPTH - 0.14, -1)):
        P.face_xz(box(XC - 1.1, Z_ENT0 + 0.27, XC + 1.1, Z_ENT0 + 0.45), y + s * 0.005, STONE_D, n=(0, s, 0))
    P.count("arch")


def obelisk(P, x, y, z0):
    box6(P, x - 0.24, x + 0.24, y - 0.24, y + 0.24, z0, z0 + 0.45, STONE, bottom=False)
    box6(P, x - 0.28, x + 0.28, y - 0.28, y + 0.28, z0 + 0.45, z0 + 0.53, STONE_L)
    for k, (dx, dy) in enumerate(((-1, -1), (1, -1), (1, 1), (-1, 1))):   # ball feet
        lathe(P, x + dx * 0.13, y + dy * 0.13, [(0.0, z0 + 0.53), (0.07, z0 + 0.56), (0.07, z0 + 0.64), (0.0, z0 + 0.67)],
              STONE_L, n=6)
    lathe(P, x, y, [(0.17, z0 + 0.67), (0.05, z0 + 1.95), (0.0, z0 + 2.02)], STONE, n=4, a0=math.pi / 4)
    lathe(P, x, y, [(0.0, z0 + 2.0), (0.08, z0 + 2.06), (0.09, z0 + 2.14), (0.06, z0 + 2.22), (0.0, z0 + 2.25)], STONE_L,
          n=8)


def stage2(P):
    """Attic: narrower block with an aedicule (two small columns + pediment) on the passage face; corner obelisks."""
    x0, x1 = 1.05, L - 1.05
    y0, y1 = -DEPTH + 0.25, -0.25
    box6(P, x0, x1, y0, y1, Z_ENT1, Z_ATT, STONE, bottom=False)
    P.quad((x0, y0, Z_ENT1), (x1, y0, Z_ENT1), (x1, y0, Z_ATT), (x0, y0, Z_ATT), (0, -1, 0), STONE)
    for y, s in ((y1, 1), (y0, -1)):
        # niche / panel between the small columns
        P.face_xz(arch_poly(XC, 0.9, Z_ENT1 + 0.35, Z_ENT1 + 0.95), y + s * 0.01, STONE_D, n=(0, s, 0))
        for x in (x0 + 0.25, x1 - 0.25):
            lathe(P, x, y + s * 0.1, [(0.11, Z_ENT1), (0.11, Z_ENT1 + 0.1), (0.09, Z_ENT1 + 0.16),
                                      (0.085, Z_ATT - 0.2), (0.12, Z_ATT - 0.1), (0.12, Z_ATT - 0.05)], STONE_L, n=8)
    # pediment over the attic (both faces), with a raking cornice
    zb = Z_ATT
    box6(P, x0 - 0.15, x1 + 0.15, y0 - 0.15, y1 + 0.15, zb - 0.05, zb + 0.1, STONE_L, bottom=True)
    tri = Polygon([(x0 - 0.15, zb + 0.1), (x1 + 0.15, zb + 0.1), (XC, zb + 0.62)])
    for y, s in ((y1 + 0.12, 1), (y0 - 0.12, -1)):
        P.face_xz(tri, y, STONE, n=(0, s, 0))
    P.sides_xz(tri, y0 - 0.12, y1 + 0.12, STONE_L, skip_ground=False)
    for x in (0.25, L - 0.25):
        for y in (-0.18, -DEPTH + 0.18):
            obelisk(P, x, y, Z_ENT1)


def stage3(P):
    """Hexagonal drum with six sundials, stepped lead cupola, ball finial and vane."""
    r = 0.78
    a0 = 0.0     # a vertex on the axis: one flat face looks straight down the passage (south)
    ang = [a0 + math.pi / 6 + k * math.pi / 3 for k in range(6)]
    lathe(P, XC, YB, [(r + 0.12, Z_ATT + 0.55), (r + 0.12, Z_DRUM0 + 0.12), (r, Z_DRUM0 + 0.12), (r, Z_DRUM1 - 0.15),
                      (r + 0.1, Z_DRUM1 - 0.1), (r + 0.16, Z_DRUM1)], STONE, n=6, a0=-math.pi / 2 + math.pi / 6)
    # sundials: a white dial on each face, gilt gnomon
    for k in range(6):
        am = -math.pi / 2 + k * math.pi / 3          # face normal directions (k=0 faces -y in frame = north?)
        S = P_()
        apo = r * math.cos(math.pi / 6)
        w = r * 0.78
        S.face_xz(box(-w / 2, Z_DRUM0 + 0.32, w / 2, Z_DRUM1 - 0.35), 0.012, DIAL)
        S.face_xz(box(-w / 2 - 0.04, Z_DRUM0 + 0.28, w / 2 + 0.04, Z_DRUM0 + 0.32), 0.012, GILT)
        zc = Z_DRUM1 - 0.5
        S.add([[(0, 0.012, zc), (0, 0.3, zc), (0, 0.012, zc - 0.42)]], (1, 0, 0), GILT)
        S.add([[(0, 0.012, zc), (0, 0.012, zc - 0.42), (0, 0.3, zc)]], (-1, 0, 0), GILT)
        place(P, S, XC + apo * math.cos(am), YB + apo * math.sin(am), am - math.pi / 2)
    # cupola: stepped ogee-ish dome in lead, then lantern-ball and vane
    z = Z_DRUM1
    lathe(P, XC, YB, [(r + 0.16, z), (r + 0.05, z + 0.15), (r - 0.05, z + 0.35), (r * 0.75, z + 0.6), (r * 0.45, z + 0.8),
                      (0.12, z + 0.95)], LEAD, n=6, a0=-math.pi / 2 + math.pi / 6)
    lathe(P, XC, YB, [(0.12, z + 0.95), (0.16, z + 1.02), (0.16, z + 1.1), (0.0, z + 1.12)], STONE_L, n=8)
    lathe(P, XC, YB, [(0.0, z + 1.1), (0.11, z + 1.15), (0.13, z + 1.23), (0.11, z + 1.31), (0.0, z + 1.36)], GILT, n=8)
    box6(P, XC - 0.012, XC + 0.012, YB - 0.012, YB + 0.012, z + 1.3, Z_TOP, IRON)
    S = P_()
    S.face_xz(Polygon([(0.0, Z_TOP - 0.28), (0.42, Z_TOP - 0.2), (0.38, Z_TOP - 0.1), (0.0, Z_TOP - 0.12)]), 0.0, GILT)
    S.face_xz(Polygon([(0.0, Z_TOP - 0.28), (0.42, Z_TOP - 0.2), (0.38, Z_TOP - 0.1), (0.0, Z_TOP - 0.12)]), -0.01, GILT,
              n=(0, -1, 0))
    place(P, S, XC, YB, 0.6)


def gates(P):
    """Closed oak gates set at mid-depth in the arch, with an iron strap or two."""
    g = arch_poly(XC, AW - 0.02, 0.0, AS)
    for y, s in ((YB + 0.04, 1), (YB - 0.04, -1)):
        P.face_xz(g, y, OAK, n=(0, s, 0), mat="frame")
        P.face_xz(box(XC - 0.012, 0.0, XC + 0.012, AS + AR - 0.05), y + s * 0.01, F.shade(OAK, 0.6), n=(0, s, 0))
        for zz in (0.5, 1.6):
            P.face_xz(box(XC - AR + 0.08, zz, XC + AR - 0.08, zz + 0.06), y + s * 0.012, IRON, n=(0, s, 0))


def build(walls=None):
    P = P_()
    stage1(P)
    gates(P)
    stage2(P)
    stage3(P)
    out = frame_world(P, P0, D, "caius:gate_of_honour", z0=Z0)
    return [o for o in (out,) if o is not None]


BUILDS = {OSM: build}
ELEMENTS = {}   # not in walls.json
HIDE_TILE = [OSM]   # complete model over the footprint; the tile node carries detail.py's simple 'gate' landmark

if __name__ == "__main__":
    items = build([])
    for it in items:
        Tz = np.asarray(it["tris"])[..., 2]
        print(it["name"], len(it["tris"]), round(float(Tz.min()), 2), round(float(Tz.max()), 2))
