"""Bespoke geometry for the street (east) face of Trinity College's Great Gate (begun 1490s as King's Hall gate,
finished c.1530-35; statue of Henry VIII 1615), session 37. OSM has no separate way for the gate: it is part of
way/151179441 (TRIN010, "Great Court E, F, G, H, I and K", 81 nodes), whose east wall carries the two turret
bumps at N 252.4-255.5 and 262.6-265.7 (E -205.5 wall line, turret fronts at E -203.9). So, as
zone_bespoke_corpus.py, only the street face is modelled and the tile body stays (no HIDE_TILE): the body face sits
FY = 0.3 m proud of the OSM wall line and the turrets are full octagons centred on the wall line. The court face
and the range roofs are left to the tile (LiDAR roof). NB: listing the way in BUILDS makes the zone / city skins
skip their generic skins for the whole TRIN010 ring.

Frame: x = metres north along the east wall line E -205.5 from N 251.0; y = metres out (east, towards Trinity
Street); z above Z0 = 9.0 (DTM 8.9-9.0 on the cobbled forecourt).

Design (shape / proportion / colour only, no pixels used):
- "Great Gate, Trinity College, Cambridge (outside).jpg" (Hans Wolff, public domain);
- "Cambridge - Trinity Street - View West on the Great Gate of Trinity College early 17th century.jpg"
  (Txllxt TxllxT, CC BY-SA 4.0).
Two octagonal turrets of red-brown brick with long-and-short stone quoins at every angle, stone string courses,
battlemented crowns on a corbel ring; the centre is buff ashlar: wide four-centred carriage arch (south of centre)
with closed timber gates and a wicket, small pedestrian arch to the north, carved spandrels, an inscription band,
a band of six painted shields round the royal arms, a canopied niche with the statue of Henry VIII between two
three-light windows, a shield panel between two three-light windows on the second floor, panelled battlemented
parapet.
Heights from the LiDAR DSM (data/lidar/dsm_1m.tif; 2023 first-return DSM as check): parapet merlons 16.0
(DSM 24.8-25.1 = 15.8-16.1 over the gate block), turret crowns 19.4 (DSM peaks 28.1-28.6 = 19.1-19.6).
"""
import math
import os
import sys

import numpy as np
from shapely.geometry import Point, Polygon, box
from shapely.ops import unary_union

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import facade_parts as F  # noqa: E402
from zone_bespoke_kings import lathe, box6, tudor, quatrefoil, slab2, frame_world  # noqa: E402

OSM = "way/151179441"
Z0 = 9.0
A = np.array([-205.5, 251.0])
D = np.array([0.0, 1.0])
# OSM way/151179441 outline (local E, N), for range_body()
FOOT = [
        (-194.08, 245.74),
        (-194.0, 234.81),
        (-196.94, 234.79),
        (-196.9, 233.41),
        (-199.56, 233.4),
        (-199.65, 230.96),
        (-203.06, 231.12),
        (-205.08, 231.06),
        (-205.12, 229.43),
        (-205.19, 226.52),
        (-202.1, 226.48),
        (-202.16, 225.77),
        (-201.35, 225.25),
        (-201.33, 223.32),
        (-202.2, 222.9),
        (-202.18, 222.34),
        (-203.67, 222.26),
        (-203.69, 221.34),
        (-203.85, 214.4),
        (-204.09, 209.01),
        (-204.33, 203.62),
        (-204.38, 202.56),
        (-204.44, 201.13),
        (-204.51, 199.7),
        (-205.51, 199.73),
        (-206.68, 199.78),
        (-207.14, 184.71),
        (-207.49, 174.98),
        (-216.3, 176.85),
        (-216.05, 181.56),
        (-212.66, 181.44),
        (-212.33, 187.48),
        (-211.99, 201.93),
        (-212.04, 202.7),
        (-211.84, 203.93),
        (-211.38, 216.25),
        (-211.35, 221.32),
        (-211.05, 229.78),
        (-210.82, 236.97),
        (-210.72, 251.67),
        (-210.78, 252.33),
        (-211.87, 252.2),
        (-212.74, 252.63),
        (-212.99, 254.57),
        (-211.75, 255.53),
        (-213.38, 256.46),
        (-213.37, 258.44),
        (-213.25, 261.8),
        (-213.23, 262.72),
        (-213.79, 262.71),
        (-214.57, 263.63),
        (-214.51, 265.07),
        (-213.64, 265.84),
        (-213.15, 265.81),
        (-212.8, 279.9),
        (-212.65, 286.3),
        (-204.71, 286.2),
        (-204.94, 272.17),
        (-200.95, 272.25),
        (-201.06, 266.68),
        (-205.3, 266.79),
        (-205.3, 265.65),
        (-204.93, 265.63),
        (-203.93, 265.03),
        (-203.87, 263.42),
        (-204.55, 262.61),
        (-205.39, 262.58),
        (-205.41, 261.7),
        (-205.45, 260.56),
        (-205.5, 258.87),
        (-205.52, 256.34),
        (-205.53, 255.48),
        (-205.08, 255.45),
        (-204.1, 254.86),
        (-204.02, 253.25),
        (-204.69, 252.44),
        (-205.55, 252.42),
        (-205.55, 251.82),
        (-205.55, 245.62),
        (-196.97, 245.66),
        (-194.08, 245.74)]
FY = 0.3
TX = (2.9, 13.1)          # turret centres (OSM bumps, N 253.9 / 264.1)
TR = 1.6                  # turret radius (to the angles)
AX = 8.0                  # gate block axis
Z_PAR, Z_MER = 14.5, 16.0
Z_TC = 19.4               # turret crown merlon tops

STONE = F.rgb("#cdb68e")
STONE_D = F.shade(STONE, 0.7)
STONE_L = F.shade(STONE, 1.06)
BRICK = F.rgb("#8c5a45")
GLASS = F.rgb(F.GLASS_COL)
OAK = F.rgb("#4b3a2a")
LEAD = F.rgb("#7f8589")
GULES, AZURE, OR = F.rgb("#9a2a24"), F.rgb("#2b4a8a"), F.rgb("#c8a24a")


def P_():
    return F.Parts(mat="stone", wall_col=STONE)


def window3(P, xc, z0, z1, holes, w=1.7, y=FY):
    """Three-light square-headed window with four-centred heads to the lights, mullions and a label mould."""
    op = box(xc - w / 2, z0, xc + w / 2, z1)
    holes.append(op)
    yg = y - 0.3
    P.sides_xz(op, yg, y, STONE_D, inward=True)
    P.face_xz(op, yg, GLASS, mat="glass")
    mw = 0.1
    lw = (w - mw * 4) / 3
    lights = unary_union([tudor(xc - w / 2 + mw + lw / 2 + i * (lw + mw), lw, z0, z1 - 0.22, n=3) for i in range(3)])
    P.slab(op.difference(lights), yg, yg + 0.14, STONE_L)
    P.box(xc - w / 2 - 0.08, xc + w / 2 + 0.08, y, y + 0.12, z0 - 0.14, z0, STONE_L)
    g = unary_union([box(xc - w / 2 - 0.16, z1 + 0.06, xc + w / 2 + 0.16, z1 + 0.2),
                     box(xc - w / 2 - 0.16, z1 - 0.3, xc - w / 2 - 0.04, z1 + 0.2),
                     box(xc + w / 2 + 0.04, z1 - 0.3, xc + w / 2 + 0.16, z1 + 0.2)])
    P.slab(g, y, y + 0.1, STONE_L)


def shield(P, xc, zc, s, y, cols):
    """Heater shield (quartered in two colours) on a square stone panel."""
    sh = Polygon([(xc - 0.25 * s, zc + 0.3 * s), (xc + 0.25 * s, zc + 0.3 * s), (xc + 0.25 * s, zc - 0.02 * s),
                  (xc + 0.12 * s, zc - 0.22 * s), (xc, zc - 0.3 * s), (xc - 0.12 * s, zc - 0.22 * s),
                  (xc - 0.25 * s, zc - 0.02 * s)])
    a, b = cols
    for k, q in enumerate((box(xc - s, zc, xc, zc + s), box(xc, zc, xc + s, zc + s), box(xc - s, zc - s, xc, zc),
                           box(xc, zc - s, xc + s, zc))):
        g = sh.intersection(q)
        if not g.is_empty:
            P.slab(g, y, y + 0.08, a if k in (0, 3) else b, mat="render")


def gate_face(P):
    y = FY
    holes = []
    # carriage arch (south of the axis) and wicket arch (north)
    big = tudor(AX - 1.35, 3.3, 0.0, 3.25, n=6)
    small = tudor(AX + 2.15, 1.35, 0.0, 2.25, n=4)
    holes += [big, small]
    for op, dep in ((big, 0.7), (small, 0.6)):
        P.sides_xz(op, y - dep, y, STONE_D, inward=True, skip_ground=True)
        for k, b in enumerate((0.14, 0.28)):   # moulded orders
            ring = op.buffer(b, join_style=1, resolution=4).difference(op.buffer(b - 0.14, join_style=1, resolution=4))
            P.slab(ring.intersection(box(-50, 0.0, 50, 9)), y, y + 0.05 * (k + 1), STONE_L)
    # closed gates: two oak leaves with planks, ribs and a wicket in the south leaf
    yg = y - 0.7
    P.face_xz(big, yg, OAK, mat="timber")
    x0, x1 = AX - 1.35 - 1.65, AX - 1.35 + 1.65
    ribs = [box(AX - 1.35 - 0.04, 0, AX - 1.35 + 0.04, 4.5)]
    for k in range(1, 12):
        xx = x0 + k * (x1 - x0) / 12
        ribs.append(box(xx - 0.015, 0.05, xx + 0.015, 4.5))
    for zz in (0.9, 2.2):
        ribs.append(box(x0, zz - 0.05, x1, zz + 0.05))
    P.slab(unary_union(ribs).intersection(big), yg, yg + 0.05, F.shade(OAK, 1.25), mat="timber")
    wk = box(AX - 2.35, 0.15, AX - 1.55, 1.95)
    P.slab(wk.exterior.buffer(0.03, join_style=2).intersection(big), yg, yg + 0.07, F.shade(OAK, 0.7), mat="timber")
    # pedestrian arch: door ajar (dark passage beyond)
    P.face_xz(small, y - 0.6, F.shade(OAK, 0.55), mat="timber")
    # carved spandrels and a traceried panel over the wicket arch
    for xc, w, zs in ((AX - 1.35, 3.3, 3.25), (AX + 2.15, 1.35, 2.25)):
        top = 4.75
        sp = box(xc - w / 2 - 0.2, zs, xc + w / 2 + 0.2, top).difference(
            (big if w > 2 else small).buffer(0.3, join_style=1, resolution=4))
        for p in F.polys(sp):
            P.slab(p.buffer(-0.06, join_style=2), y, y + 0.04, STONE_L)
            c = p.representative_point()
            P.slab(quatrefoil(c.x, c.y, 0.22), y + 0.04, y + 0.1, STONE_D)
    P.slab(box(AX + 1.3, 2.8, AX + 3.0, 4.6).difference(small.buffer(0.3, join_style=1, resolution=4)).buffer(-0.08),
           y, y + 0.04, STONE_L)
    # inscription band and the band of shields with the royal arms in the middle
    P.box(TX[0] + 1.4, TX[1] - 1.4, y, y + 0.1, 4.85, 5.25, STONE_D)
    P.box(TX[0] + 1.4, TX[1] - 1.4, y, y + 0.06, 4.95, 5.15, OR, mat="render")
    P.box(TX[0] + 1.4, TX[1] - 1.4, y, y + 0.12, 5.25, 5.4, STONE_L)
    for k, xc in enumerate((AX - 3.0, AX - 2.0, AX - 1.0, AX + 1.0, AX + 2.0, AX + 3.0)):
        P.slab(box(xc - 0.4, 5.5, xc + 0.4, 6.75).difference(box(xc - 0.33, 5.57, xc + 0.33, 6.68)), y, y + 0.08,
               STONE_L)
        shield(P, xc, 6.1, 1.1, y, (GULES, AZURE) if k % 2 else (AZURE, GULES))
    P.slab(box(AX - 0.55, 5.45, AX + 0.55, 6.85), y, y + 0.06, STONE_L)
    shield(P, AX, 6.15, 1.7, y + 0.06, (AZURE, GULES))
    for sx in (-1, 1):   # supporters
        P.slab(Polygon([(AX + sx * 0.5, 5.6), (AX + sx * 0.75, 5.6), (AX + sx * 0.7, 6.5), (AX + sx * 0.55, 6.7)]),
               y + 0.06, y + 0.14, OR, mat="render")
    P.box(TX[0] + 1.4, TX[1] - 1.4, y, y + 0.12, 6.95, 7.1, STONE_L)   # string course
    # first floor: niche with Henry VIII between three-light windows
    window3(P, AX - 2.05, 7.5, 9.35, holes)
    window3(P, AX + 2.05, 7.5, 9.35, holes)
    niche = tudor(AX, 0.95, 7.35, 9.3, n=4)
    holes.append(niche)
    P.sides_xz(niche, y - 0.35, y, STONE_D, inward=True)
    P.face_xz(niche, y - 0.35, F.shade(STONE, 0.6))
    ys = y - 0.15
    P.box(AX - 0.45, AX + 0.45, y, y + 0.32, 7.05, 7.35, STONE_L)                                    # corbel
    lathe(P, AX, ys, [(0.3, 7.35), (0.33, 7.9), (0.3, 8.3), (0.36, 8.65), (0.34, 8.9), (0.1, 8.95),
                      (0.1, 9.0), (0.13, 9.05), (0.13, 9.28), (0.0, 9.32)], STONE_L, n=8)             # robed king
    lathe(P, AX, ys, [(0.14, 9.26), (0.15, 9.38), (0.0, 9.42)], OR, n=6)                              # crown
    box6(P, AX + 0.28, AX + 0.33, ys - 0.03, ys + 0.03, 8.4, 9.6, F.shade(STONE, 0.8))               # sceptre / chair leg
    for sx in (-1, 1):   # canopy shafts and pinnacles
        box6(P, AX + sx * 0.62 - 0.07, AX + sx * 0.62 + 0.07, y, y + 0.14, 7.2, 10.0, STONE_L)
        lathe(P, AX + sx * 0.62, y + 0.07, [(0.1, 10.0), (0.0, 10.45)], STONE_L, n=4)
    P.slab(box(AX - 0.62, 9.35, AX + 0.62, 9.95).difference(quatrefoil(AX, 9.65, 0.2)), y, y + 0.16, STONE_L)
    P.slab(box(AX - 0.5, 10.05, AX + 0.5, 10.85), y, y + 0.05, STONE_L)                             # arms over niche
    shield(P, AX, 10.45, 1.2, y + 0.05, (GULES, AZURE))
    P.box(TX[0] + 1.4, TX[1] - 1.4, y, y + 0.12, 10.95, 11.1, STONE_L)
    # second floor
    window3(P, AX - 2.05, 11.75, 13.4, holes)
    window3(P, AX + 2.05, 11.75, 13.4, holes)
    P.slab(box(AX - 0.4, 12.3, AX + 0.4, 13.1), y, y + 0.05, STONE_L)
    shield(P, AX, 12.7, 1.0, y + 0.05, (AZURE, GULES))
    # wall face (between the turrets: they cover its ends)
    x0, x1 = TX[0] + 0.6, TX[1] - 0.6
    P.face_xz(box(x0, -0.6, x1, Z_PAR).difference(unary_union(holes)), y, STONE)
    P.extrude_profile([(y, -0.6), (y + 0.15, -0.6), (y + 0.15, 0.4), (y, 0.55)], x0, AX - 1.35 - 1.9, STONE_D)
    P.extrude_profile([(y, -0.6), (y + 0.15, -0.6), (y + 0.15, 0.4), (y, 0.55)], AX - 1.35 + 1.9, AX + 2.15 - 0.95,
                      STONE_D)
    P.extrude_profile([(y, -0.6), (y + 0.15, -0.6), (y + 0.15, 0.4), (y, 0.55)], AX + 2.15 + 0.95, x1, STONE_D)
    # parapet: cornice, panelled band with quatrefoils, battlements with panelled merlons
    P.extrude_profile([(y, Z_PAR - 0.2), (y + 0.25, Z_PAR), (y + 0.25, Z_PAR + 0.12), (y, Z_PAR + 0.15)], x0, x1,
                      STONE_L)
    g = box(x0, Z_PAR, x1, Z_PAR + 0.75)
    n = 6
    p = (x1 - x0) / n
    merl = [box(x0 + i * p + 0.12, Z_PAR + 0.74, x0 + (i + 1) * p - 0.12, Z_MER) for i in range(n)]
    slab2(P, unary_union([g] + merl), y - 0.32, y, STONE)
    for i in range(n):
        xc = x0 + (i + 0.5) * p
        P.slab(quatrefoil(xc, Z_PAR + 0.4, 0.22), y, y + 0.05, STONE_L)
        P.slab(box(xc - 0.25, Z_PAR + 0.9, xc + 0.25, Z_MER - 0.2).exterior.buffer(0.03, join_style=2), y, y + 0.04,
               STONE_L)
        box6(P, xc - p / 2 + 0.09, xc + p / 2 - 0.09, y - 0.36, y + 0.05, Z_MER - 0.06, Z_MER + 0.02, STONE_L)
    for i in range(n + 1):   # coping of the crenels
        xa = x0 + i * p
        a, b = max(x0, xa - 0.13), min(x1, xa + 0.13)
        box6(P, a, b, y - 0.36, y + 0.05, Z_PAR + 0.68, Z_PAR + 0.76, STONE_L)
    # back of the parapet over the tile roof
    P.face_xz(box(x0, Z_PAR, x1, Z_PAR + 0.75), y - 0.32, STONE_D, n=(0, -1, 0))


def turret(P, x):
    """Octagonal brick turret with long-and-short stone quoins, stone strings, slit windows, corbelled crown."""
    r = TR
    zc = Z_TC - 1.4
    prof = [(r + 0.1, -0.6), (r + 0.1, 0.5), (r, 0.6)]
    for z in (7.0, 11.0, Z_PAR):
        prof += [(r, z - 0.1), (r + 0.08, z - 0.02), (r + 0.08, z + 0.08), (r, z + 0.14)]
    prof += [(r, zc - 0.5)]
    lathe(P, x, 0.0, prof, BRICK, n=8, mat="brick")
    # stone string rings (lathe is single-coloured: overlay thin stone bands)
    for z in (0.55, 7.0, 11.0, Z_PAR):
        lathe(P, x, 0.0, [(r + 0.1, z - 0.12), (r + 0.1, z + 0.12)], STONE_L, n=8)
    ap = r * math.cos(math.pi / 8)
    side = 2 * r * math.sin(math.pi / 8)
    # quoins at the angles (angles at a = k*pi/4 + pi/8 with lathe a0 = pi/8)
    for k in range(8):
        a = math.pi / 8 + k * math.pi / 4
        ca, sa = math.cos(a), math.sin(a)
        if sa < -0.3:
            continue
        cx, cy = x + r * ca, r * sa
        z, lng = 0.7, True
        while z < zc - 0.6:
            h = 0.32 if lng else 0.22
            s = 0.24 if lng else 0.15
            box6(P, cx - s, cx + s, cy - s, cy + s, z, z + h - 0.03, STONE)
            z += h
            lng = not lng
    # slit windows on the faces turned to the street
    for k in range(8):
        a = k * math.pi / 4
        ca, sa = math.cos(a), math.sin(a)
        if sa < 0.3:
            continue
        for zb in (3.0, 8.6, 12.2, 16.0):
            if zb > zc - 1.2:
                continue
            fx, fy = x + (ap + 0.02) * ca, (ap + 0.02) * sa
            tx, ty = -sa, ca
            w, h = 0.22, 0.9
            pts = [(fx - tx * w, fy - ty * w, zb), (fx + tx * w, fy + ty * w, zb),
                   (fx + tx * w, fy + ty * w, zb + h), (fx - tx * w, fy - ty * w, zb + h)]
            P.quad(*pts, (ca, sa, 0), F.shade(OAK, 0.5))
            P.quad(*[(px + ca * 0.02 - tx * 0.0, py + sa * 0.02, pz) for px, py, pz in
                     [(fx - tx * (w + 0.1), fy - ty * (w + 0.1), zb + h), (fx + tx * (w + 0.1), fy + ty * (w + 0.1), zb + h),
                      (fx + tx * (w + 0.1), fy + ty * (w + 0.1), zb + h + 0.12),
                      (fx - tx * (w + 0.1), fy - ty * (w + 0.1), zb + h + 0.12)]], (ca, sa, 0), STONE_L)
    del side
    # corbel ring and crown
    lathe(P, x, 0.0, [(r, zc - 0.5), (r + 0.12, zc - 0.3), (r + 0.25, zc - 0.05), (r + 0.25, zc + 0.35),
                      (r + 0.33, zc + 0.45), (r + 0.33, zc + 0.55)], STONE_L, n=8)
    lathe(P, x, 0.0, [(r + 0.25, zc + 0.55), (r + 0.25, zc + 0.6)], BRICK, n=8, mat="brick")
    rr = r + 0.25
    for k in range(8):   # merlons on the faces, crenels at the angles
        a = k * math.pi / 4
        cx, cy = x + (rr * math.cos(math.pi / 8) - 0.15) * math.cos(a), (rr * math.cos(math.pi / 8) - 0.15) * math.sin(a)
        S = P_()
        box6(S, -0.38, 0.38, -0.15, 0.15, zc + 0.55, Z_TC - 0.08, STONE)
        box6(S, -0.42, 0.42, -0.19, 0.19, Z_TC - 0.08, Z_TC, STONE_L)
        from zone_bespoke_kings import place
        place(P, S, cx, cy, a - math.pi / 2)
    lathe(P, x, 0.0, [(rr - 0.3, zc + 0.6), (0.0, zc + 0.6)], LEAD, n=8)


def range_body():
    """Stand-in for the hidden tile body of the TRIN010 range (the tile node also carries build.py's procedural
    'gate_tower' landmark, a 12 m box in front of the real gate, so the node has to go): the OSM footprint extruded
    from the DTM to the LiDAR roof, roof = DSM heightfield (1 m grid, sampled 0.75 m inside the walls), as the tiles do.
    World frame (E, N, z)."""
    import rasterio
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import build as BB
    root = BB.ROOT
    poly = Polygon(FOOT)
    inner = poly.buffer(-0.75, join_style=2)
    with rasterio.open(os.path.join(root, "data/lidar/dsm_1m.tif")) as ds, \
            rasterio.open(os.path.join(root, "data/lidar/dtm_1m.tif")) as dt:
        def samp(r, pts):
            return np.array([v[0] for v in r.sample([(x + BB.E0, y + BB.N0) for x, y in pts])], float)
        x0, y0, x1, y1 = poly.bounds
        xs = np.arange(math.floor(x0) - 0.5, x1 + 1.0, 1.0)
        ys = np.arange(math.floor(y0) - 0.5, y1 + 1.0, 1.0)
        GX, GY = np.meshgrid(xs, ys)
        pts = []
        for x, y in zip(GX.ravel(), GY.ravel()):   # clamp grid nodes into the inner polygon for the DSM sample
            q = Point(x, y)
            if not inner.contains(q):
                from shapely.ops import nearest_points
                q = nearest_points(inner, q)[0]
            pts.append((q.x, q.y))
        H = samp(ds, pts).reshape(GX.shape)
        zg = float(np.median(samp(dt, list(poly.exterior.coords))))
    tris, nrm, cols = [], [], []
    ROOF = F.rgb("#6f6a66")
    for j in range(len(ys) - 1):
        for i in range(len(xs) - 1):
            cell = box(xs[i], ys[j], xs[i + 1], ys[j + 1])
            if not poly.intersects(cell):
                continue
            g = cell.intersection(poly)
            for p in F.polys(g):
                T2 = F.earcut2d(p)
                for t in T2:
                    tz = []
                    for x, y in t:   # bilinear DSM over the cell
                        u, v = (x - xs[i]), (y - ys[j])
                        tz.append((1 - u) * (1 - v) * H[j, i] + u * (1 - v) * H[j, i + 1] + (1 - u) * v * H[j + 1, i]
                                  + u * v * H[j + 1, i + 1])
                    tris.append([(t[0][0], t[0][1], tz[0]), (t[1][0], t[1][1], tz[1]), (t[2][0], t[2][1], tz[2])])
                    nrm.append((0, 0, 1)); cols.append(ROOF)
    # walls: each footprint edge from below the DTM to the roof heights at its ends
    def roof_at(x, y):
        fx = (x - xs[0]); fy = (y - ys[0])
        i = int(np.clip(math.floor(fx), 0, len(xs) - 2)); j = int(np.clip(math.floor(fy), 0, len(ys) - 2))
        u, v = fx - i, fy - j
        return (1 - u) * (1 - v) * H[j, i] + u * (1 - v) * H[j, i + 1] + (1 - u) * v * H[j + 1, i] + u * v * H[j + 1, i + 1]
    ring = list(poly.exterior.coords)
    if not poly.exterior.is_ccw:
        ring = ring[::-1]
    for (ax, ay), (bx, by) in zip(ring[:-1], ring[1:]):
        L = math.hypot(bx - ax, by - ay)
        if L < 1e-3:
            continue
        n = ((by - ay) / L, -(bx - ax) / L, 0)
        za, zb = roof_at(ax, ay), roof_at(bx, by)
        tris += [[(ax, ay, zg - 0.6), (bx, by, zg - 0.6), (bx, by, zb)], [(ax, ay, zg - 0.6), (bx, by, zb), (ax, ay, za)]]
        nrm += [n, n]; cols += [BRICK, BRICK]
    T = np.asarray(tris, float)
    Nw = np.asarray(nrm, float)
    g = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
    flip = (g * Nw).sum(1) < 0
    T[flip] = T[flip][:, ::-1]
    mats = np.array([F.mat_id("brick") if c is BRICK else F.mat_id("plain") for c in cols])
    return {"name": "trinity:range_body", "tris": T, "col": np.asarray(cols, float), "mat": mats}


def build(walls=None):
    P = P_()
    gate_face(P)
    for x in TX:
        turret(P, x)
    out = frame_world(P, A, D, "trinity:great_gate", z0=Z0)
    return [o for o in (out, range_body()) if o is not None]


BUILDS = {OSM: build}
ELEMENTS = {}   # not in walls.json
HIDE_TILE = [OSM]   # the tile node carries build.py's procedural gate_tower (a 12 m box in front of the real gate);
#                     range_body() stands in for the tile body (footprint + LiDAR DSM roof), collision is kept

if __name__ == "__main__":
    items = build([])
    for it in items:
        Tz = np.asarray(it["tris"])[..., 2]
        print(it["name"], len(it["tris"]), round(float(Tz.min()), 2), round(float(Tz.max()), 2))
    print("total", sum(len(i["tris"]) for i in items))
