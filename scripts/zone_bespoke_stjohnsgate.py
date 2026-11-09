"""Bespoke geometry for the street (east) face of St John's College Great Gate (c.1511-20, St John's Street; ring 2),
session 64. OSM has no separate way for the gate: it is part of way/158913878 (JOH010, the east range of First Court),
whose street wall carries two half-octagon turret bumps (local x -0.04..2.84 and 8.21..11.05 along the wall line,
both ~2.1 m proud) and whose court wall carries two more (x 0.2..3.1 and 8.3..11.1 at y -7.5..-10.4).
As zone_bespoke_greatgate.py only the street face and the four turrets are modelled; the tile body (LiDAR roof) stays.
The BUILDS key is a pseudo id ("way/158913878:gate") so the city facade skin still dresses the rest of the range: the
gate face sits FY = 1.05 m proud of the OSM wall line (between the 2.1 m turret bumps) and hides the generic skin
of the gate bay behind it.

Frame: x = metres north-north-east along the street wall line from OSM node (-191.02, 324.79) (local E, N), direction
(0.4117, 0.9113); y = metres out (east-south-east, towards St John's Street); z above Z0 = 8.6 (DTM 8.58-8.70).

Design (shape / proportion / colour only; general knowledge of the gate, no photo pixels, no held-out photos):
red brick tower with stone dressings, four octagonal brick turrets with stone strings and battlemented crowns;
a four-centred carriage arch with closed oak gates and a wicket, carved spandrels; above it a recessed stone panel with
the founder's painted arms supported by two yales under a crown, with a rose and a portcullis, on a ground strewn
with daisies; a canopied niche with a standing saint between two-light windows; a three-light window on the top
floor; a battlemented stone parapet.
Heights from the LiDAR DSM (data/lidar/dsm_1m.tif): gate block 22.7-23.1 (= 14.1-14.5 over Z0) -> merlon tops 14.5;
turret peaks 26.3-27.1 (= 17.7-18.5) -> turret crown merlon tops 18.1.
"""
import math
import os
import sys

import numpy as np
from shapely.geometry import Point, Polygon, box
from shapely.ops import unary_union

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import facade_parts as F  # noqa: E402
from zone_bespoke_kings import lathe, box6, tudor, quatrefoil, slab2, frame_world, place  # noqa: E402
from zone_bespoke_greatgate import shield  # noqa: E402

KEY = "way/158913878:gate"
Z0 = 8.6
A = np.array([-191.02, 324.79])
D = np.array([4.54, 10.05]) / math.hypot(4.54, 10.05)
FY = 1.05                 # gate bay face: the deepest recess (arch, 0.75 m) still clears the city skin of the OSM wall line
TURRETS = [(1.42, 0.65), (9.63, 0.75), (1.67, -8.95), (9.70, -8.95)]   # (x, y) centres from the OSM bumps
TA = 1.6                  # turret apothem (OSM bumps ~1.45; a little more so the tile body's bump faces stay inside)
TR = TA / math.cos(math.pi / 8)
AX = 5.53                 # gate axis (mid-way between the street turrets)
Z_PAR, Z_MER = 13.4, 14.5
Z_TC = 18.1

BRICK = F.rgb("#8b4c3a")
STONE = F.rgb("#cfbd98")
STONE_D = F.shade(STONE, 0.7)
STONE_L = F.shade(STONE, 1.06)
GLASS = F.rgb(F.GLASS_COL)
OAK = F.rgb("#4a3626")
LEAD = F.rgb("#7f8589")
GULES, AZURE, OR, ARGENT = F.rgb("#9a2a24"), F.rgb("#2b4a8a"), F.rgb("#c8a24a"), F.rgb("#e4e0d4")
YALE = F.rgb("#d8cfb4")


def P_():
    return F.Parts(mat="brick", wall_col=BRICK)


def lights(P, xc, z0, z1, n, holes, lw=0.5, y=FY):
    """n-light mullioned window, four-centred light heads, stone surround and hood mould."""
    mw = 0.1
    w = n * lw + (n + 1) * mw
    op = box(xc - w / 2, z0, xc + w / 2, z1)
    holes.append(op)
    yg = y - 0.3
    P.sides_xz(op, yg, y, STONE_D, inward=True, mat="stone")
    P.face_xz(op, yg, GLASS, mat="glass")
    L = unary_union([tudor(xc - w / 2 + mw + lw / 2 + i * (lw + mw), lw, z0, z1 - 0.2, n=3) for i in range(n)])
    P.slab(op.difference(L), yg, yg + 0.14, STONE_L, mat="stone")
    if (z1 - z0) > 1.5:   # transom
        P.slab(box(xc - w / 2, (z0 + z1) / 2 - 0.05, xc + w / 2, (z0 + z1) / 2 + 0.05).intersection(L), yg, yg + 0.12,
               STONE_L, mat="stone")
    sur = op.buffer(0.14, join_style=2).difference(op)
    P.slab(sur, y, y + 0.05, STONE, mat="stone")
    P.box(xc - w / 2 - 0.1, xc + w / 2 + 0.1, y, y + 0.12, z0 - 0.16, z0, STONE_L, mat="stone")
    g = unary_union([box(xc - w / 2 - 0.2, z1 + 0.1, xc + w / 2 + 0.2, z1 + 0.24),
                     box(xc - w / 2 - 0.2, z1 - 0.3, xc - w / 2 - 0.08, z1 + 0.24),
                     box(xc + w / 2 + 0.08, z1 - 0.3, xc + w / 2 + 0.2, z1 + 0.24)])
    P.slab(g, y, y + 0.1, STONE_L, mat="stone")


def yale(P, xc, z0, s, y, flip):
    """Heraldic yale (antelope-like supporter) as a rampant relief silhouette: body, legs, neck, head, swept horns."""
    f = -1 if flip else 1
    X = lambda u: xc + f * u * s  # noqa: E731
    body = Polygon([(X(-0.18), z0 + 0.35 * s), (X(0.12), z0 + 0.3 * s), (X(0.2), z0 + 0.75 * s), (X(0.05), z0 + 1.05 * s),
                    (X(-0.15), z0 + 0.95 * s)])
    neck = Polygon([(X(0.02), z0 + 0.95 * s), (X(0.16), z0 + 1.0 * s), (X(0.2), z0 + 1.3 * s), (X(0.06), z0 + 1.28 * s)])
    head = Polygon([(X(0.05), z0 + 1.25 * s), (X(0.24), z0 + 1.28 * s), (X(0.32), z0 + 1.22 * s), (X(0.3), z0 + 1.36 * s),
                    (X(0.1), z0 + 1.42 * s)])
    legs = unary_union([box(min(X(-0.15), X(-0.07)), z0, max(X(-0.15), X(-0.07)), z0 + 0.42 * s),
                        box(min(X(0.02), X(0.1)), z0, max(X(0.02), X(0.1)), z0 + 0.4 * s),
                        Polygon([(X(0.15), z0 + 0.72 * s), (X(0.38), z0 + 0.88 * s), (X(0.36), z0 + 0.96 * s),
                                 (X(0.12), z0 + 0.84 * s)]),
                        Polygon([(X(0.12), z0 + 0.86 * s), (X(0.34), z0 + 1.08 * s), (X(0.3), z0 + 1.14 * s),
                                 (X(0.08), z0 + 0.95 * s)])])
    tail = Polygon([(X(-0.16), z0 + 0.5 * s), (X(-0.3), z0 + 0.62 * s), (X(-0.28), z0 + 0.7 * s), (X(-0.14), z0 + 0.6 * s)])
    g = unary_union([body, neck, head, legs, tail]).buffer(0)
    P.slab(g, y, y + 0.14, YALE, mat="stone")
    for dz, du in ((0.0, 0.0), (0.04, 0.05)):   # two horns sweeping back
        h = Polygon([(X(0.1 + du), z0 + 1.38 * s), (X(0.14 + du), z0 + 1.4 * s), (X(-0.08 + du), z0 + (1.72 + dz) * s),
                     (X(-0.1 + du), z0 + (1.69 + dz) * s)]).buffer(0)
        P.slab(h, y + 0.14, y + 0.18, OR, mat="render")
    # spots (yales are spotted)
    for u, v in ((-0.06, 0.6), (0.06, 0.8), (-0.08, 0.85), (0.08, 0.55)):
        P.slab(Point(X(u), z0 + v * s).buffer(0.03 * s, resolution=2), y + 0.14, y + 0.16, OR, mat="render")


def heraldry(P, holes):
    """Recessed stone panel over the arch: crowned arms between yales, rose and portcullis, daisies strewn over it."""
    y = FY
    x0, x1, z0, z1 = AX - 2.25, AX + 2.25, 4.75, 8.45
    pan = box(x0, z0, x1, z1)
    holes.append(pan)
    yb = y - 0.25
    P.sides_xz(pan, yb, y, STONE_D, inward=True, mat="stone")
    P.face_xz(pan, yb, F.shade(STONE, 0.92), mat="stone")
    P.slab(pan.buffer(0.18, join_style=2).difference(pan), y, y + 0.08, STONE_L, mat="stone")   # frame moulding
    # daisies (white petals, gold eye) and forget-me-not dots on the ground
    rng = np.random.default_rng(1511)
    keep = box(AX - 0.95, 5.0, AX + 0.95, 7.8).union(box(x0 + 0.15, 4.9, AX - 1.0, 7.0)).union(
        box(AX + 1.0, 4.9, x1 - 0.15, 7.0))
    for _ in range(26):
        u, v = rng.uniform(x0 + 0.2, x1 - 0.2), rng.uniform(z0 + 0.2, z1 - 0.2)
        if keep.intersects(box(u - 0.1, v - 0.1, u + 0.1, v + 0.1)):
            continue
        P.slab(quatrefoil(u, v, 0.12), yb, yb + 0.05, ARGENT, mat="render")
        P.slab(box(u - 0.025, v - 0.025, u + 0.025, v + 0.025), yb + 0.05, yb + 0.07, OR, mat="render")
    # arms: quarterly azure / gules, a gold border, on a projecting stone shield
    P.slab(box(AX - 0.62, 5.25, AX + 0.62, 7.0).buffer(0.0), yb, yb + 0.05, STONE_L, mat="stone")
    shield(P, AX, 6.1, 2.4, yb + 0.05, (AZURE, GULES))
    for k in range(4):   # gold charges on the quarters (lilies / lions as small blocks)
        qx, qz = AX + (-0.3 if k % 2 == 0 else 0.3), 6.35 if k < 2 else 5.95
        P.slab(box(qx - 0.1, qz - 0.1, qx + 0.1, qz + 0.1).buffer(0.04, join_style=1, resolution=2), yb + 0.13,
               yb + 0.16, OR, mat="render")
    # crown over the arms
    cr = unary_union([box(AX - 0.55, 7.05, AX + 0.55, 7.25)] +
                     [Polygon([(AX + u - 0.1, 7.25), (AX + u + 0.1, 7.25), (AX + u, 7.55)]) for u in (-0.45, -0.15, 0.15, 0.45)])
    P.slab(cr, yb, yb + 0.16, OR, mat="render")
    P.slab(box(AX - 0.06, 7.55, AX + 0.06, 7.8).union(box(AX - 0.14, 7.62, AX + 0.14, 7.7)), yb, yb + 0.12, OR,
           mat="render")
    # supporters
    yale(P, AX - 1.55, 5.0, 1.2, yb, flip=False)
    yale(P, AX + 1.55, 5.0, 1.2, yb, flip=True)
    # rose (left) and crowned portcullis (right) in the upper corners
    rx, rz = x0 + 0.55, 7.85
    P.slab(Polygon([(rx + 0.3 * math.cos(a), rz + 0.3 * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 11)[:-1]]),
           yb, yb + 0.08, GULES, mat="render")
    P.slab(Polygon([(rx + 0.16 * math.cos(a), rz + 0.16 * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 9)[:-1]]),
           yb + 0.08, yb + 0.12, ARGENT, mat="render")
    px, pz = x1 - 0.55, 7.8
    grid = [box(px - 0.3, pz + 0.25, px + 0.3, pz + 0.32)]
    grid += [box(px + u - 0.025, pz - 0.35, px + u + 0.025, pz + 0.3) for u in (-0.24, -0.08, 0.08, 0.24)]
    grid += [box(px - 0.3, pz + v - 0.025, px + 0.3, pz + v + 0.025) for v in (-0.15, 0.05, 0.22)]
    P.slab(unary_union(grid), yb, yb + 0.1, OR, mat="render")
    for u in (-0.32, 0.32):   # chains
        P.slab(box(px + u - 0.02, pz - 0.2, px + u + 0.02, pz + 0.3), yb, yb + 0.06, OR, mat="render")


def gate_face(P):
    y = FY
    holes = []
    big = tudor(AX, 3.0, 0.0, 3.35, n=6)
    holes.append(big)
    P.sides_xz(big, y - 0.75, y, STONE_D, inward=True, skip_ground=True, mat="stone")
    for k, b in enumerate((0.15, 0.3, 0.45)):   # moulded stone orders
        ring = big.buffer(b, join_style=1, resolution=4).difference(big.buffer(b - 0.15, join_style=1, resolution=4))
        P.slab(ring.intersection(box(-50, 0.0, 50, 9)), y, y + 0.05 * (k + 1), STONE_L if k % 2 == 0 else STONE,
               mat="stone")
    # closed oak gates: two leaves with vertical boarding, ribs and a wicket
    yg = y - 0.75
    P.face_xz(big, yg, OAK, mat="timber")
    xa, xb = AX - 1.5, AX + 1.5
    ribs = [box(AX - 0.04, 0, AX + 0.04, 4.6)]
    for k in range(1, 12):
        xx = xa + k * (xb - xa) / 12
        ribs.append(box(xx - 0.015, 0.05, xx + 0.015, 4.6))
    for zz in (0.8, 1.9, 2.9):
        ribs.append(box(xa, zz - 0.05, xb, zz + 0.05))
    P.slab(unary_union(ribs).intersection(big), yg, yg + 0.05, F.shade(OAK, 1.25), mat="timber")
    wk = box(AX - 1.25, 0.15, AX - 0.35, 1.95)
    P.slab(wk.exterior.buffer(0.03, join_style=2).intersection(big), yg, yg + 0.07, F.shade(OAK, 0.7), mat="timber")
    # stone dressing round the arch up to a square label with carved spandrels (roses in quatrefoils)
    dr = box(AX - 2.15, 0.0, AX + 2.15, 4.35)
    P.slab(dr.difference(big.buffer(0.46, join_style=1, resolution=4)), y, y + 0.04, STONE, mat="stone")
    holes.append(dr)
    for sx in (-1, 1):
        cx, cz = AX + sx * 1.55, 3.75
        P.slab(quatrefoil(cx, cz, 0.42), y + 0.04, y + 0.1, STONE_D, mat="stone")
        P.slab(Polygon([(cx + 0.14 * math.cos(a), cz + 0.14 * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 9)[:-1]]),
               y + 0.1, y + 0.16, GULES, mat="render")
    P.slab(unary_union([box(AX - 2.3, 4.35, AX + 2.3, 4.55), box(AX - 2.3, 3.7, AX - 2.12, 4.55),
                        box(AX + 2.12, 3.7, AX + 2.3, 4.55)]), y, y + 0.14, STONE_L, mat="stone")   # label mould
    heraldry(P, holes)
    P.box(AX - 2.6, AX + 2.6, y, y + 0.14, 8.65, 8.85, STONE_L, mat="stone")   # string course
    # first floor: canopied niche with a standing saint between two-light windows
    lights(P, AX - 1.75, 9.3, 11.0, 2, holes)
    lights(P, AX + 1.75, 9.3, 11.0, 2, holes)
    niche = tudor(AX, 0.85, 9.15, 11.0, n=4)
    holes.append(niche)
    P.sides_xz(niche, y - 0.35, y, STONE_D, inward=True, mat="stone")
    P.face_xz(niche, y - 0.35, F.shade(STONE, 0.6), mat="stone")
    ys = y - 0.15
    P.box(AX - 0.42, AX + 0.42, y, y + 0.3, 8.85, 9.15, STONE_L, mat="stone")
    lathe(P, AX, ys, [(0.26, 9.15), (0.3, 9.7), (0.26, 10.1), (0.3, 10.35), (0.12, 10.45), (0.11, 10.5), (0.13, 10.56),
                      (0.12, 10.78), (0.0, 10.82)], STONE_L, n=8)                                     # robed figure
    box6(P, AX + 0.22, AX + 0.27, ys - 0.03, ys + 0.03, 9.9, 10.5, STONE_L)                          # book / palm
    for sx in (-1, 1):
        box6(P, AX + sx * 0.56 - 0.06, AX + sx * 0.56 + 0.06, y, y + 0.12, 8.95, 11.6, STONE_L)
        lathe(P, AX + sx * 0.56, y + 0.06, [(0.09, 11.6), (0.0, 12.0)], STONE_L, n=4)
    P.slab(box(AX - 0.56, 11.0, AX + 0.56, 11.55).difference(quatrefoil(AX, 11.27, 0.18)), y, y + 0.16, STONE_L,
           mat="stone")
    P.box(AX - 2.6, AX + 2.6, y, y + 0.12, 11.85, 12.0, STONE_L, mat="stone")
    # second floor: three-light window
    lights(P, AX, 12.2, 13.15, 3, holes)
    # brick wall face between the turrets (they cover its ends), diaper of dark headers
    x0, x1 = TURRETS[0][0] + 0.5, TURRETS[1][0] - 0.5
    face = box(x0, -0.6, x1, Z_PAR).difference(unary_union(holes))
    P.face_xz(face, y, BRICK, mat="brick")
    dia = []
    for k in range(-8, 20):
        for j in range(0, 16):
            cx, cz = x0 + k * 0.9 + (0.45 if j % 2 else 0.0), 0.8 + j * 0.9
            dia.append(Polygon([(cx, cz - 0.3), (cx + 0.3, cz), (cx, cz + 0.3), (cx - 0.3, cz)]).exterior.buffer(0.03))
    dg = unary_union(dia).intersection(face.buffer(-0.15))
    P.slab(dg, y, y + 0.01, F.shade(BRICK, 0.62), sides=False, mat="brick")
    P.extrude_profile([(y, -0.6), (y + 0.15, -0.6), (y + 0.15, 0.4), (y, 0.55)], x0, AX - 2.15, STONE_D, mat="stone")
    P.extrude_profile([(y, -0.6), (y + 0.15, -0.6), (y + 0.15, 0.4), (y, 0.55)], AX + 2.15, x1, STONE_D, mat="stone")
    # stone parapet: cornice, battlements
    P.extrude_profile([(y, Z_PAR - 0.2), (y + 0.22, Z_PAR), (y + 0.22, Z_PAR + 0.1), (y, Z_PAR + 0.13)], x0, x1,
                      STONE_L, mat="stone")
    g = box(x0, Z_PAR, x1, Z_PAR + 0.55)
    n = 4
    p = (x1 - x0) / n
    merl = [box(x0 + i * p + 0.14, Z_PAR + 0.54, x0 + (i + 1) * p - 0.14, Z_MER) for i in range(n)]
    slab2(P, unary_union([g] + merl), y - 0.32, y, STONE)
    for i in range(n):
        xc = x0 + (i + 0.5) * p
        box6(P, xc - p / 2 + 0.1, xc + p / 2 - 0.1, y - 0.36, y + 0.05, Z_MER - 0.06, Z_MER + 0.02, STONE_L)
    P.face_xz(box(x0, Z_PAR, x1, Z_PAR + 0.55), y - 0.32, STONE_D, n=(0, -1, 0))


def turret(P, x, yc, street):
    """Octagonal brick turret, stone string rings, slit windows (street turrets), corbelled battlemented crown."""
    r = TR
    zc = Z_TC - 1.3
    prof = [(r + 0.1, -0.6), (r + 0.1, 0.5), (r, 0.6), (r, zc - 0.5)]
    lathe(P, x, yc, prof, BRICK, n=8, mat="brick")
    for z in (0.55, 4.55, 8.75, 11.92, Z_PAR + 0.05):
        lathe(P, x, yc, [(r + 0.07, z - 0.1), (r + 0.07, z + 0.1)], STONE_L, n=8)
    ap = r * math.cos(math.pi / 8)
    if street:
        for k in range(8):
            a = k * math.pi / 4
            ca, sa = math.cos(a), math.sin(a)
            if sa < 0.3:
                continue
            for zb in (2.6, 6.4, 10.0, 13.6):
                fx, fy = x + (ap + 0.02) * ca, yc + (ap + 0.02) * sa
                tx, ty = -sa, ca
                w, h = 0.16, 0.8
                e = 0.05
                P.quad((fx - tx * w + ca * e, fy - ty * w + sa * e, zb), (fx + tx * w + ca * e, fy + ty * w + sa * e, zb),
                       (fx + tx * w + ca * e, fy + ty * w + sa * e, zb + h), (fx - tx * w + ca * e, fy - ty * w + sa * e, zb + h),
                       (ca, sa, 0), F.shade(OAK, 0.45), "glass")
                w2 = w + 0.07
                P.quad((fx - tx * w2 + ca * 0.02, fy - ty * w2 + sa * 0.02, zb - 0.08),
                       (fx + tx * w2 + ca * 0.02, fy + ty * w2 + sa * 0.02, zb - 0.08),
                       (fx + tx * w2 + ca * 0.02, fy + ty * w2 + sa * 0.02, zb + h + 0.08),
                       (fx - tx * w2 + ca * 0.02, fy - ty * w2 + sa * 0.02, zb + h + 0.08), (ca, sa, 0), STONE, "stone")
    lathe(P, x, yc, [(r, zc - 0.5), (r + 0.12, zc - 0.3), (r + 0.22, zc - 0.05), (r + 0.22, zc + 0.3),
                     (r + 0.3, zc + 0.4), (r + 0.3, zc + 0.5)], STONE_L, n=8)
    rr = r + 0.22
    for k in range(8):
        a = k * math.pi / 4
        rm = rr * math.cos(math.pi / 8) - 0.14
        S = P_()
        box6(S, -0.36, 0.36, -0.14, 0.14, zc + 0.5, Z_TC - 0.08, BRICK, mat="brick")
        box6(S, -0.4, 0.4, -0.18, 0.18, Z_TC - 0.08, Z_TC, STONE_L)
        place(P, S, x + rm * math.cos(a), yc + rm * math.sin(a), a - math.pi / 2)
    lathe(P, x, yc, [(rr - 0.28, zc + 0.5), (0.0, zc + 0.5)], LEAD, n=8, mat="plain")


def build(walls=None):
    P = P_()
    gate_face(P)
    for i, (x, yc) in enumerate(TURRETS):
        turret(P, x, yc, i < 2)
    return [frame_world(P, A, D, "stjohns:great_gate", z0=Z0)]


BUILDS = {KEY: build}
ELEMENTS = {}

if __name__ == "__main__":
    items = build([])
    for it in items:
        Tz = np.asarray(it["tris"])[..., 2]
        print(it["name"], len(it["tris"]), round(float(Tz.min()), 2), round(float(Tz.max()), 2))
