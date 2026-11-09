"""Bespoke geometry for Clare College Old Court (1638-1715) and the west (Backs) face of King's College's Gibbs Building
(James Gibbs, 1724-30), ring 2, session 72.

OSM (real ids; the faces are pseudo-keyed as zone_bespoke_christs.py, so the tile body (LiDAR roof) and the city skins
stay and each face sits just proud of the OSM wall line, hiding the city skin of that wall):
- way/139308028 (CLARE010, addr:housename "Old Court (Clare College)"): the east range. Its outer (east) wall runs
  from (E -326.7, N 5.0) to (E -333.2, N 45.5), 41 m; the OSM wall steps 0.6 m out between N 25.5 and 32.4 = the gate
  tower frontispiece (centre at x 24.1 along the wall).
- way/139308031 (CLARE011, south range + south half of the west range) and way/139308035 (CLARE012, "Master's Lodge",
  north half of the west range): their west walls form the river front, from (E -398.1, N 52.4) to (E -391.0, N -3.4),
  56.3 m, a slight polyline within 0.5 m of the straight line used here.
- way/12688565 (KINGS012, "Gibbs' Building"): west wall from (E -320.2, N -29.8) to (E -310.5, N -101.2), 72.1 m.
Frames: x along the wall (east range: northwards; river fronts: southwards), y out of the building, z above Z0.

Heights from the LiDAR DSM (data/lidar/dsm_1m.tif) and DTM: Clare east ground 8.6-9.2 (Z0 8.7), parapet line ~20.0-20.5
(11.5 m), roof ridge ~22.4, gate tower peak 24.1 (15.4 m) at x 20-24; Clare west ground 7.4-7.6 (river side, Z0 7.55),
parapet ~20.8-21.0 (13.2 m) on the southern 34 m (the DSM over the northern 22 m reads 26-27 m: probably tree canopy, not
used); Gibbs ground 9.3-9.5 (Z0 9.4), parapet ~24.2-24.9 (15.0 m), centre (x 36-40) up to 26.7 (pediment, 17.3 m).

Design: general knowledge only (no photos used; nothing under data/benchmark opened). Clare Old Court is classical
ashlar (Ketton / Barnack type, warm buff), three storeys with a balustraded parapet and regular windows with moulded
architraves; the east range has a central frontispiece gate tower with superimposed pilaster orders, niches either side
and a vaulted passage; the river front has Ionic pilasters between the bays. Gibbs Building is pale Portland stone,
three storeys, rusticated ground storey, plain parapet, a central pedimented frontispiece with a great arched opening
and a Diocletian-like lunette above it.
UNVERIFIED (no photo check): bay counts and window rhythm, the exact orders and niche positions on the Clare gate tower,
whether the river front pilasters are giant or per storey (per storey used), the Gibbs west-face centre treatment
(modelled like its east front), window glazing patterns (sashes used throughout).
"""
import math
import os
import sys

import numpy as np
from shapely.geometry import Point, Polygon, box
from shapely.ops import unary_union

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import facade_parts as F  # noqa: E402
from zone_bespoke_kings import box6, slab2, frame_world  # noqa: E402

ASHLAR = F.rgb("#d8c69c")       # Ketton / Barnack buff
PORTLAND = F.rgb("#e2dccd")     # Gibbs: Portland stone
GLASS = F.rgb(F.GLASS_COL)
FRAME = F.rgb("#ece8dc")
OAK = F.rgb("#4a3626")
DARK = F.rgb("#3a362f")

# Clare east range
E_A, E_B = np.array([-326.7, 5.0]), np.array([-333.2, 45.5])
# Clare river front (south end of CLARE011 to north end of CLARE012, reversed: north -> south)
W_A, W_B = np.array([-398.1, 52.4]), np.array([-391.0, -3.4])
# Gibbs west face (north -> south)
G_A, G_B = np.array([-320.2, -29.8]), np.array([-310.5, -101.2])


def _frame(a, b):
    L = float(np.linalg.norm(b - a))
    return a, (b - a) / L, L


def arch(xc, w, z0, z1):
    """Round-headed opening: springing at z1 - w/2."""
    r = w / 2
    zs = z1 - r
    return box(xc - r, z0, xc + r, zs).union(Point(xc, zs).buffer(r, resolution=6).intersection(box(xc - r, zs, xc + r, z1)))


def sash(P, xc, z0, z1, w, holes, y, col, pediment=None):
    """Sash window: reveal, glass, glazing bars, moulded architrave, sill; optional pediment / cornice head."""
    op = box(xc - w / 2, z0, xc + w / 2, z1)
    holes.append(op)
    yg = y - 0.22
    P.sides_xz(op, yg, y, F.shade(col, 0.74), inward=True)
    P.face_xz(op, yg, GLASS, mat="glass")
    zm = (z0 + z1) / 2
    bars = [box(xc - w / 2, zm - 0.035, xc + w / 2, zm + 0.035), box(xc - 0.02, z0, xc + 0.02, z1)]
    for zz in ((z0 + zm) / 2, (zm + z1) / 2):
        bars.append(box(xc - w / 2, zz - 0.02, xc + w / 2, zz + 0.02))
    P.slab(unary_union(bars).intersection(op), yg, yg + 0.05, FRAME, sides=False, mat="plain")
    P.slab(op.buffer(0.14, join_style=2).difference(op), y, y + 0.06, F.shade(col, 1.05), sides=False)
    P.box(xc - w / 2 - 0.14, xc + w / 2 + 0.14, y, y + 0.13, z0 - 0.14, z0, F.shade(col, 1.06), bottom=False)
    if pediment == "cornice":
        P.box(xc - w / 2 - 0.25, xc + w / 2 + 0.25, y, y + 0.2, z1 + 0.14, z1 + 0.3, F.shade(col, 1.07))
    elif pediment == "tri":
        tri = Polygon([(xc - w / 2 - 0.3, z1 + 0.16), (xc + w / 2 + 0.3, z1 + 0.16), (xc, z1 + 0.62)])
        P.slab(tri, y, y + 0.18, F.shade(col, 1.07))
    P.count("window")


def pilaster(P, x, z0, z1, w, y, col, cap="ionic"):
    """Pilaster with base, shaft and a capital (ionic: small volute blocks)."""
    c = F.shade(col, 1.04)
    P.box(x - w / 2 - 0.06, x + w / 2 + 0.06, y, y + 0.2, z0, z0 + 0.22, c, bottom=False)
    P.box(x - w / 2, x + w / 2, y, y + 0.14, z0 + 0.22, z1 - 0.28, c, top=False, bottom=False)
    P.box(x - w / 2 - 0.08, x + w / 2 + 0.08, y, y + 0.2, z1 - 0.28, z1, F.shade(col, 1.08))
    if cap == "ionic":
        for s in (-1, 1):
            P.box(x + s * (w / 2 + 0.02) - 0.07, x + s * (w / 2 + 0.02) + 0.07, y + 0.2, y + 0.26, z1 - 0.26, z1 - 0.1,
                  F.shade(col, 1.1))
    elif cap == "corinthian":
        P.box(x - w / 2 - 0.02, x + w / 2 + 0.02, y + 0.14, y + 0.24, z1 - 0.5, z1 - 0.28, F.shade(col, 0.95))


def entablature(P, x0, x1, z, y, col, deep=0.32):
    P.extrude_profile([(y, z - 0.45), (y + 0.06, z - 0.45), (y + 0.06, z - 0.2), (y + 0.12, z - 0.18),
                       (y + deep, z - 0.04), (y + deep, z + 0.06), (y, z + 0.08)], x0, x1, F.shade(col, 1.06))


def balustrade(P, x0, x1, z, y, col, h=0.95, gap_w=0.26, pitch=0.5):
    """Pierced balustrade: plinth, rail and openings between balusters (as cut-outs), with dies every ~4 m."""
    g = box(x0, z, x1, z + h)
    n = int((x1 - x0) / pitch)
    holes = []
    for i in range(n):
        xc = x0 + (i + 0.5) * (x1 - x0) / n
        if (i % 8) in (0, 7):
            continue                   # die / pedestal
        holes.append(box(xc - gap_w / 2, z + 0.22, xc + gap_w / 2, z + h - 0.16))
    slab2(P, g.difference(unary_union(holes)), y - 0.3, y, col)
    box6(P, x0, x1, y - 0.36, y + 0.06, z + h - 0.02, z + h + 0.08, F.shade(col, 1.07))


def niche(P, xc, z0, z1, w, y, col, holes):
    op = arch(xc, w, z0, z1)
    holes.append(op)
    P.sides_xz(op, y - 0.28, y, F.shade(col, 0.82), inward=True)
    P.face_xz(op, y - 0.28, F.shade(col, 0.78))
    P.slab(op.buffer(0.1, join_style=2).difference(op), y, y + 0.05, F.shade(col, 1.06))


def range_face(P, x0, x1, nb, floors, z_cor, z_par_top, y, col, pil=None, skip=(), heads=("cornice", None, None),
               rust=False):
    """Regular classical range from x0 to x1 with nb bays; floors [(z0, z1), ...] (window sill/head); pilasters
    between bays if pil (cap name); bays whose index is in skip are left for a frontispiece."""
    holes = []
    b = (x1 - x0) / nb
    for i in range(nb):
        if i in skip:
            continue
        xc = x0 + (i + 0.5) * b
        for k, (za, zb) in enumerate(floors):
            sash(P, xc, za, zb, min(1.2, b * 0.42), holes, y, col, pediment=heads[k] if k < len(heads) else None)
    if pil:
        for i in range(nb + 1):
            if i in skip or (i - 1) in skip:
                continue
            xp = x0 + i * b
            zz = [-0.4] + [f[1] + 0.55 for f in floors[:-1]] + [z_cor - 0.45]
            for k in range(len(zz) - 1):
                pilaster(P, xp, zz[k], zz[k + 1], 0.5, y, col, cap=pil if k == len(zz) - 2 else "doric")
    keep = [box(x0 + i * b, -0.6, x0 + (i + 1) * b, z_cor) for i in range(nb) if i not in skip]
    face = unary_union(keep).difference(unary_union(holes))
    P.face_xz(face, y, col)
    if rust:                                   # rusticated ground storey only (the ashlar above reads smooth)
        jt = [box(x0, z - 0.02, x1, z + 0.02) for z in np.arange(0.6, floors[0][1] + 0.6, 0.6)]
        jg = unary_union(jt).intersection(unary_union(keep)).difference(unary_union([h.buffer(0.16, join_style=2) for h in holes]))
        P.slab(jg, y, y + 0.03, F.shade(col, 0.86), sides=False)
    # plinth, floor bands, cornice, parapet
    P.extrude_profile([(y, -0.6), (y + 0.16, -0.6), (y + 0.16, 0.35), (y, 0.45)], x0, x1, F.shade(col, 0.8))
    for (za, zb) in floors[:-1]:
        P.box(x0, x1, y, y + 0.1, zb + 0.5, zb + 0.66, F.shade(col, 1.04))
    entablature(P, x0, x1, z_cor, y, col)
    P.face_xz(box(x0, -0.6, x1, z_par_top), y - 0.4, F.shade(col, 0.7), n=(0, -1, 0))
    return holes


def gate_tower(P, xc, w, Z_COR, y, col, Ztop):
    """Clare east frontispiece: arched gateway into a vaulted passage, three storeys of paired pilasters (Doric, Ionic,
    Corinthian) with niches between them, an arched window over the gate, entablatures and a balustraded top."""
    holes = []
    x0, x1 = xc - w / 2, xc + w / 2
    g = arch(xc, 2.9, 0.0, 4.6)
    holes.append(g)
    P.sides_xz(g, y - 3.0, y, F.shade(col, 0.78), inward=True, skip_ground=True)       # the vaulted passage
    P.face_xz(g, y - 3.0, OAK, mat="timber")
    leaves = [box(xc - 0.03, 0, xc + 0.03, 4.3)] + [box(xc - 1.45, z - 0.04, xc + 1.45, z + 0.04) for z in (1.2, 2.5, 3.6)]
    P.slab(unary_union(leaves).intersection(g), y - 3.0, y - 2.95, F.shade(OAK, 1.25), mat="timber")
    P.slab(g.buffer(0.22, join_style=1, resolution=4).difference(g).intersection(box(x0, 0, x1, 9)), y, y + 0.08,
           F.shade(col, 1.06))
    P.box(xc - 0.22, xc + 0.22, y, y + 0.22, 4.15, 4.85, F.shade(col, 1.1))                # keystone
    zs = [-0.4, 4.9, 8.45, Z_COR]
    caps = ["doric", "ionic", "corinthian"]
    for k in range(3):
        for s in (-1, 1):
            for u in (w / 2 - 0.45, w / 2 - 1.35):
                pilaster(P, xc + s * u, zs[k], zs[k + 1] - 0.45, 0.48, y, col, cap=caps[k])
        entablature(P, x0, x1, zs[k + 1], y, col, deep=0.36)
        if k > 0:
            for s in (-1, 1):
                sash(P, xc + s * (w / 2 - 0.9), zs[k] + 0.7, zs[k + 1] - 1.1, 0.6, holes, y, col)
    win = arch(xc, 1.25, 5.7, 7.9)
    holes.append(win)
    P.sides_xz(win, y - 0.25, y, F.shade(col, 0.75), inward=True)
    P.face_xz(win, y - 0.25, GLASS, mat="glass")
    P.slab(win.buffer(0.15, join_style=2).difference(win), y, y + 0.06, F.shade(col, 1.06))
    sash(P, xc, 9.0, 10.6, 1.1, holes, y, col, pediment="tri")
    face = box(x0, -0.6, x1, Z_COR).difference(unary_union(holes))
    P.face_xz(face, y, col)
    P.extrude_profile([(y, -0.6), (y + 0.18, -0.6), (y + 0.18, 0.35), (y, 0.45)], x0, xc - 1.7, F.shade(col, 0.8))
    P.extrude_profile([(y, -0.6), (y + 0.18, -0.6), (y + 0.18, 0.35), (y, 0.45)], xc + 1.7, x1, F.shade(col, 0.8))
    # attic stage up to the DSM peak: panel with a segmental pediment-like cap
    att = box(xc - 1.9, Z_COR, xc + 1.9, Ztop - 0.5).union(
        Point(xc, Ztop - 1.3).buffer(2.0, resolution=6).intersection(box(xc - 1.9, Ztop - 0.5, xc + 1.9, Ztop)))
    slab2(P, att, y - 0.6, y, col)
    P.slab(box(xc - 1.2, Z_COR + 0.4, xc + 1.2, Ztop - 0.9).exterior.buffer(0.05, join_style=2), y, y + 0.05,
           F.shade(col, 1.07))
    # side returns over the OSM step
    for xe in (x0, x1):
        box6(P, xe - 0.04, xe + 0.04, y - 0.7, y, -0.6, Z_COR + 0.1, col)


# world-xy openings of build_clare_east() (kind, E, N): city_facades.py counts them onto KPI_WALLS (session 76)
_OPS = []
KPI_WALLS = {"way/139308028:clare": ["way/139308028:14", "way/139308028:15"]}


def dormer(P, xc, zb, y, col):
    """Pedimented ashlar dormer standing 1.2 m behind the balustrade face, slate cheeks."""
    yf, yk, w, z0, z1 = y - 1.2, y - 3.0, 1.5, zb - 0.6, zb + 1.3
    box6(P, xc - w / 2, xc + w / 2, yk, yf, z0, z1, col)
    P.quad((xc - 0.38, yf + 0.01, z0 + 0.7), (xc + 0.38, yf + 0.01, z0 + 0.7), (xc + 0.38, yf + 0.01, z1 - 0.15),
           (xc - 0.38, yf + 0.01, z1 - 0.15), (0, 1, 0), GLASS, "glass")
    tri = Polygon([(xc - w / 2 - 0.1, z1), (xc + w / 2 + 0.1, z1), (xc, z1 + 0.55)])
    P.slab(tri, yf - 0.1, yf + 0.08, F.shade(col, 1.05))
    for sx in (-1, 1):
        P.quad((xc + sx * w / 2, yk, z1), (xc + sx * w / 2, yf, z1), (xc, yf, z1 + 0.5), (xc, yk, z1 + 0.5),
               (sx * 0.5, 0, 0.86), DARK, "plain")


def build_clare_east():
    a, d, L = _frame(E_A, E_B)
    col = ASHLAR
    P = F.Parts(mat="stone", wall_col=col)
    Y, YG = 0.55, 1.2           # s73: glass (Y - 0.22) and niche backs (YG - 0.28) clear the city skin (<= 0.25 m proud of walls :14/:15, 0.88 at the step wall :17)
    Z_COR, Z_PT = 10.6, 11.65                 # cornice; balustrade top (DSM parapet line ~20.3 over Z0 8.7)
    AX, GW = 24.1, 6.6
    floors = [(0.9, 2.9), (4.2, 6.3), (7.4, 9.3)]
    for xa, xb in ((0.0, AX - GW / 2), (AX + GW / 2, L)):
        nb = max(1, int(round((xb - xa) / 3.3)))
        range_face(P, xa, xb, nb, floors, Z_COR, Z_PT, Y, col)
        balustrade(P, xa, xb, Z_COR + 0.08, Y, col)
    gate_tower(P, AX, GW, Z_COR, YG, col, 15.3)
    # session 76 (Commons photos, data/annotations/ring1/way_139308028.json): pedimented dormers over every bay behind
    # the balustrade, and the gate tower's 1st/2nd floors have a small sash window either side of the oriel, not niches
    _OPS.clear()
    for xa, xb in ((0.0, AX - GW / 2), (AX + GW / 2, L)):
        nb = max(1, int(round((xb - xa) / 3.3)))
        b = (xb - xa) / nb
        for i in range(nb):
            xc = xa + (i + 0.5) * b
            dormer(P, xc, Z_PT, Y, col)
            pt = a + d * xc + np.array([d[1], -d[0]]) * Y
            _OPS.extend([("window", float(pt[0]), float(pt[1]))] * len(floors) + [("dormer", float(pt[0]), float(pt[1]))])
    balustrade(P, AX - GW / 2, AX - 1.9, Z_COR + 0.1, YG, col)
    balustrade(P, AX + 1.9, AX + GW / 2, Z_COR + 0.1, YG, col)
    for xe, s in ((0.0, -1), (L, 1)):
        P.quad((xe, Y - 0.4, -0.6), (xe, Y, -0.6), (xe, Y, Z_PT), (xe, Y - 0.4, Z_PT), (s, 0, 0), F.shade(col, 0.8), "stone")
    return frame_world(P, a, d, "clare:old_court_east", z0=8.7)


def build_clare_west():
    a, d, L = _frame(W_A, W_B)
    col = ASHLAR
    P = F.Parts(mat="stone", wall_col=col)
    Y = 0.55                  # s73: glass at Y - 0.22 clears the city skin of CLARE011 wall :3 (up to 0.27 m proud of this line)
    Z_COR, Z_PT = 12.15, 13.2
    floors = [(1.6, 3.9), (5.2, 7.6), (8.8, 10.9)]
    nb = 15
    b = L / nb
    mid = nb // 2
    range_face(P, 0.0, L, nb, floors, Z_COR, Z_PT, Y, col, pil="ionic", skip=(mid,),
               heads=("tri", "cornice", None))
    # centre bay: doorway to the bridge axis, slightly proud, with a pediment over the first-floor window
    xc = (mid + 0.5) * b
    Pc = P
    holes = []
    yc = Y + 0.35
    door = arch(xc, 1.6, 0.0, 3.6)
    holes.append(door)
    Pc.sides_xz(door, yc - 1.2, yc, F.shade(col, 0.76), inward=True, skip_ground=True)
    Pc.face_xz(door, yc - 1.2, OAK, mat="timber")
    Pc.slab(door.buffer(0.18, join_style=1, resolution=4).difference(door).intersection(box(0, 0, L, 9)), yc, yc + 0.08,
            F.shade(col, 1.06))
    sash(Pc, xc, floors[1][0], floors[1][1], 1.2, holes, yc, col, pediment="tri")
    sash(Pc, xc, floors[2][0], floors[2][1], 1.2, holes, yc, col)
    xa, xb = mid * b, (mid + 1) * b
    Pc.face_xz(box(xa, -0.6, xb, Z_COR).difference(unary_union(holes)), yc, col)
    for xp in (xa + 0.3, xb - 0.3):
        for k, (za, zb) in enumerate([(-0.4, 4.45), (4.45, 8.15), (8.15, Z_COR - 0.45)]):
            pilaster(Pc, xp, za, zb, 0.55, yc, col, cap="ionic" if k else "doric")
    entablature(Pc, xa, xb, Z_COR, yc, col, deep=0.36)
    for xe in (xa, xb):
        box6(Pc, xe - 0.04, xe + 0.04, Y - 0.05, yc, -0.6, Z_COR, col)
    tri = Polygon([(xa - 0.2, Z_COR + 0.1), (xb + 0.2, Z_COR + 0.1), (xc, Z_COR + 1.35)])
    slab2(Pc, tri, yc - 0.5, yc + 0.1, F.shade(col, 1.04))
    balustrade(P, 0.0, xa, Z_COR + 0.08, Y, col)
    balustrade(P, xb, L, Z_COR + 0.08, Y, col)
    for xe, s in ((0.0, -1), (L, 1)):
        P.quad((xe, Y - 0.4, -0.6), (xe, Y, -0.6), (xe, Y, Z_PT), (xe, Y - 0.4, Z_PT), (s, 0, 0), F.shade(col, 0.8), "stone")
    return frame_world(P, a, d, "clare:old_court_west", z0=7.55)


def build_gibbs_west():
    a, d, L = _frame(G_A, G_B)
    col = PORTLAND
    P = F.Parts(mat="stone", wall_col=col)
    Y = 0.25
    Z_COR, Z_PT = 14.0, 15.0
    floors = [(1.3, 3.9), (5.6, 8.6), (10.0, 12.3)]
    nb = 21
    b = L / nb
    cs = (9, 10, 11)                        # three-bay centrepiece
    range_face(P, 0.0, L, nb, floors, Z_COR, Z_PT, Y, col, skip=cs, heads=(None, "cornice", None), rust=True)
    xa, xb = cs[0] * b, (cs[-1] + 1) * b
    xc = (xa + xb) / 2
    yc = Y + 0.4
    holes = []
    big = arch(xc, 3.0, 0.0, 6.2)
    holes.append(big)
    P.sides_xz(big, yc - 1.0, yc, F.shade(col, 0.75), inward=True, skip_ground=True)
    P.face_xz(big, yc - 1.0, DARK)
    P.slab(big.buffer(0.3, join_style=2).difference(big).intersection(box(xa, 0, xb, 9)), yc, yc + 0.1, F.shade(col, 1.05))
    P.box(xc - 0.3, xc + 0.3, yc, yc + 0.25, 5.8, 6.8, F.shade(col, 1.08))
    lun = Point(xc, 9.4).buffer(1.6, resolution=8).intersection(box(xc - 1.6, 9.4, xc + 1.6, 11.0))
    holes.append(lun)
    P.sides_xz(lun, yc - 0.3, yc, F.shade(col, 0.75), inward=True)
    P.face_xz(lun, yc - 0.3, GLASS, mat="glass")
    P.slab(unary_union([box(xc - 0.55, 9.4, xc - 0.47, 11.0), box(xc + 0.47, 9.4, xc + 0.55, 11.0)]).intersection(lun),
           yc - 0.3, yc - 0.24, FRAME, sides=False, mat="plain")
    for s in (-1, 1):
        sash(P, xc + s * b, floors[1][0], floors[1][1], 1.2, holes, yc, col, pediment="tri")
        sash(P, xc + s * b, floors[2][0], floors[2][1], 1.2, holes, yc, col)
        sash(P, xc + s * b, floors[0][0], floors[0][1], 1.2, holes, yc, col)
    P.face_xz(box(xa, -0.6, xb, Z_COR).difference(unary_union(holes)), yc, col)
    jt = [box(xa, z - 0.02, xb, z + 0.02) for z in np.arange(0.6, 4.6, 0.6)]
    P.slab(unary_union(jt).difference(unary_union([h.buffer(0.2, join_style=2) for h in holes])), yc, yc + 0.03,
           F.shade(col, 0.85), sides=False)
    for xp in (xa + 0.35, xb - 0.35, xc - 1.95, xc + 1.95):
        pilaster(P, xp, 4.7, Z_COR - 0.45, 0.6, yc, col, cap="corinthian")
    P.box(xa, xb, yc, yc + 0.12, 4.5, 4.7, F.shade(col, 1.04))
    entablature(P, xa, xb, Z_COR, yc, col, deep=0.4)
    tri = Polygon([(xa - 0.2, Z_COR + 0.1), (xb + 0.2, Z_COR + 0.1), (xc, 17.2)])
    slab2(P, tri, yc - 0.6, yc + 0.1, F.shade(col, 1.03))
    inner = Polygon([(xa + 0.6, Z_COR + 0.35), (xb - 0.6, Z_COR + 0.35), (xc, 16.75)])
    P.slab(tri.difference(inner), yc + 0.1, yc + 0.22, F.shade(col, 1.07), sides=False)
    for xe in (xa, xb):
        box6(P, xe - 0.04, xe + 0.04, Y - 0.05, yc, -0.6, Z_COR, col)
    # plain parapet
    for x0_, x1_ in ((0.0, xa), (xb, L)):
        box6(P, x0_, x1_, Y - 0.35, Y + 0.02, Z_COR + 0.08, Z_PT, col)
        box6(P, x0_, x1_, Y - 0.4, Y + 0.08, Z_PT, Z_PT + 0.1, F.shade(col, 1.06))
    for xe, s in ((0.0, -1), (L, 1)):
        P.quad((xe, Y - 0.4, -0.6), (xe, Y, -0.6), (xe, Y, Z_PT), (xe, Y - 0.4, Z_PT), (s, 0, 0), F.shade(col, 0.8), "stone")
    return frame_world(P, a, d, "kings:gibbs_west", z0=9.4)


def build_clare(walls=None):
    return [it for it in (build_clare_east(), build_clare_west()) if it]


def build_gibbs(walls=None):
    return [it for it in (build_gibbs_west(),) if it]


BUILDS = {"way/139308028:clare": build_clare, "way/12688565:gibbs": build_gibbs}
ELEMENTS = {}

if __name__ == "__main__":
    tot = 0
    for fn in BUILDS.values():
        for it in fn([]):
            Tz = np.asarray(it["tris"])[..., 2]
            tot += len(it["tris"])
            print(it["name"], len(it["tris"]), round(float(Tz.min()), 2), round(float(Tz.max()), 2))
    print("total", tot)
