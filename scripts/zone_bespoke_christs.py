"""Bespoke geometry for Christ's College's street front on St Andrew's Street (ring 1), session 68: the Great Gate
(c.1505-11, Lady Margaret Beaufort's foundation) and the long west range of First Court, ashlar-faced in the
18th century with sash windows behind a plain parapet.

OSM: the whole of First Court's outer ranges is one way, way/147487949 (building=university). Its street wall runs
from node 21 (E 89.6, N 70.0; Hobson Street corner) south-south-east to node 6 (E 125.9, N 26.9; next to the Library),
56.3 m. On it two shallow half-octagon bumps (local x 10.1..11.8 and 15.3..17.1, <= 0.7 m proud) are the street turrets
of the gate tower; between them the OSM wall steps back to y = -1.0 (the gate bay). The court wall has the matching
inner turret bumps (x 9.9 / 13.6 / 17.2 at y -7.4..-8.4). As zone_bespoke_stjohnsgate.py, only the street face is
modelled; the tile body (LiDAR roof) and the city skins stay, so BUILDS uses a pseudo id ("way/147487949:christs") and
each face sits proud of the OSM wall line so the city skin of the same wall stays hidden behind it.

Frame: x = metres along the street wall from node 21 towards node 6, direction (0.6442, -0.7649); y = metres out
(west-south-west, towards St Andrew's Street; the road centreline is at y ~ 3.6-5.7, the churchyard fence of St Andrew
the Great at y ~ 12); z above the per-piece Z0 (DTM 8.74 at x 0 rising to 9.52 at x 56; the range is built in three
pieces with their own Z0).

Design (shape / proportion / colour only, no pixels used; none of these are held-out benchmark photos):
- "Cambridge - St Andrews Street - View ENE on the Main Gate of Christ's College.jpg" (Txllxt TxllxT, CC BY-SA 4.0),
  https://commons.wikimedia.org/wiki/File:Cambridge_-_St_Andrews_Street_-_View_ENE_on_the_Main_Gate_of_Christ%27s_College.jpg
- "Christ's College Cambridge Great Gate.jpg" and "Christs Great Gate.jpg" (Wikimedia Commons, Category:Christ's
  College Great Gate; CC BY-SA licences per their file pages);
- "Christ's College and St Andrew's Street - geograph.org.uk - 7007477.jpg" (CC BY-SA 2.0): the long ashlar range.
Plus general knowledge: the gate tower is pale stone, with polygonal turrets with battlemented tops either side; a
four-centred arch with carved spandrels under a square label and the old oak gates with a wicket; over it the carved
and painted arms of Lady Margaret (France modern quartering England, in a bordure compony) crowned, supported by two
yales, with the Tudor rose and the Beaufort portcullis on a ground strewn with daisies (marguerites); windows with
hood moulds above, a battlemented parapet. The tower looks squat because the street was raised and the bottom of the
gate "cut off" (Wikipedia). The range: two storeys of tall sash windows in a regular rhythm, a plinth, a string
course at first-floor level, a moulded cornice and a plain parapet.
Heights from the LiDAR DSM (data/lidar/dsm_1m.tif): range parapet line 16.2-16.6 (7.3-7.5 over the DTM), roof ridge
18.5-19.3 behind it; gate tower top 20.0-20.5 (11.2-11.7 over Z0 8.8); turret peaks 22.4-23.5 (13.6-14.7).
Uncertain: whether the gate has a niche/statue between the panel and the upper window (not modelled), the exact
window count of the range (a regular 3.1 m bay rhythm is used), and the turret plan (octagonal used).
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
from zone_bespoke_stjohnsgate import yale  # noqa: E402

KEY = "way/147487949:christs"
A = np.array([89.6, 70.0])
D = np.array([36.3, -43.1]) / math.hypot(36.3, -43.1)
L = 56.35

ASHLAR = F.rgb("#d6c8a6")         # 18th-c. ashlar (Ketton-like)
ASHLAR_D = F.shade(ASHLAR, 0.74)
STONE = F.rgb("#cdbd98")          # older, greyer gate-tower stone
STONE_D = F.shade(STONE, 0.7)
STONE_L = F.shade(STONE, 1.06)
GLASS = F.rgb(F.GLASS_COL)
FRAME = F.rgb("#ece8dc")          # white-painted sashes
OAK = F.rgb("#4a3626")
LEAD = F.rgb("#7f8589")
GULES, AZURE, OR, ARGENT = F.rgb("#9a2a24"), F.rgb("#2b4a8a"), F.rgb("#c8a24a"), F.rgb("#e4e0d4")

# gate tower
GZ0 = 8.82
AX = 13.5                                   # gate axis (mid-way between the street turrets, = the court-side middle bump)
TURRETS = [(10.95, -0.15), (16.2, -0.2)]    # street turret centres from the OSM bumps
TA = 1.05
TR = TA / math.cos(math.pi / 8)
GY = -0.55                                  # gate bay face (OSM bay wall at y -1.0)
Z_PAR, Z_MER = 10.55, 11.45
Z_TC = 14.1
# range
FY = 0.75                                   # range face proud of the OSM wall line
Z_COR, Z_PTOP = 6.75, 7.45                  # cornice and parapet top over Z0


def P_(col=ASHLAR):
    return F.Parts(mat="stone", wall_col=col)


# ------------------------------------------------------------------ the range
def sash(P, xc, z0, z1, w, holes, y):
    """Georgian sash window: reveal, glass, white six-over-six glazing bars, plain stone architrave, sill."""
    op = box(xc - w / 2, z0, xc + w / 2, z1)
    holes.append(op)
    yg = y - 0.24
    P.sides_xz(op, yg, y, ASHLAR_D, inward=True)
    P.face_xz(op, yg, GLASS, mat="glass")
    zm = (z0 + z1) / 2
    bars = [box(xc - w / 2, zm - 0.04, xc + w / 2, zm + 0.04),                          # meeting rail
            box(xc - w / 2 + 0.03, z0, xc - w / 2 + 0.08, z1), box(xc + w / 2 - 0.08, z0, xc + w / 2 - 0.03, z1)]
    for u in (-w / 6, w / 6):
        bars.append(box(xc + u - 0.02, z0, xc + u + 0.02, z1))
    for zz in (z0 + (zm - z0) / 2, zm + (z1 - zm) / 2):
        bars.append(box(xc - w / 2, zz - 0.02, xc + w / 2, zz + 0.02))
    P.slab(unary_union(bars).intersection(op), yg, yg + 0.06, FRAME, sides=False, mat="plain")
    arch = op.buffer(0.13, join_style=2).difference(op)
    P.slab(arch, y, y + 0.04, F.shade(ASHLAR, 1.05), sides=False)
    P.box(xc - w / 2 - 0.12, xc + w / 2 + 0.12, y, y + 0.12, z0 - 0.15, z0, F.shade(ASHLAR, 1.06))


def range_piece(x0, x1, z0, name, end_l=False, end_r=False):
    """A stretch of the ashlar range from x0 to x1 (own Z0): plinth, two floors of sashes, string course,
    cornice and parapet."""
    P = P_()
    y = FY
    holes = []
    bay = 3.1
    n = max(1, int(round((x1 - x0 - 0.6) / bay)))
    b = (x1 - x0) / n
    for i in range(n):
        xc = x0 + (i + 0.5) * b
        sash(P, xc, 0.85, 2.85, 1.05, holes, y)      # ground floor (raised over the pavement)
        sash(P, xc, 3.85, 5.95, 1.05, holes, y)      # first floor
    face = box(x0, -0.6, x1, Z_PTOP).difference(unary_union(holes))
    P.face_xz(face, y, ASHLAR)
    # coursed ashlar: horizontal joints only (cheap), a little darker
    jt = [box(x0, z - 0.012, x1, z + 0.012) for z in np.arange(0.95, Z_COR, 0.38)]
    jg = unary_union(jt).difference(unary_union([h.buffer(0.15, join_style=2) for h in holes]))
    P.slab(jg, y, y + 0.004, F.shade(ASHLAR, 0.88), sides=False)
    # plinth, first-floor string, cornice, parapet coping
    P.extrude_profile([(y, -0.6), (y + 0.14, -0.6), (y + 0.14, 0.5), (y, 0.6)], x0, x1, ASHLAR_D)
    P.extrude_profile([(y, 3.3), (y + 0.08, 3.33), (y + 0.08, 3.45), (y, 3.48)], x0, x1, F.shade(ASHLAR, 1.04))
    P.extrude_profile([(y, Z_COR - 0.25), (y + 0.1, Z_COR - 0.2), (y + 0.28, Z_COR - 0.02), (y + 0.28, Z_COR + 0.08),
                       (y, Z_COR + 0.1)], x0, x1, F.shade(ASHLAR, 1.05))
    box6(P, x0, x1, y - 0.35, y + 0.04, Z_PTOP - 0.02, Z_PTOP + 0.1, F.shade(ASHLAR, 1.07))
    P.face_xz(box(x0, Z_COR, x1, Z_PTOP), y - 0.3, ASHLAR_D, n=(0, -1, 0))        # parapet back
    for xe, s in ((x0, -1), (x1, 1)):     # close the slab ends so the face does not read as paper
        if (s < 0 and end_l) or (s > 0 and end_r):
            P.quad((xe, y - 0.3, -0.6), (xe, y, -0.6), (xe, y, Z_PTOP), (xe, y - 0.3, Z_PTOP), (s, 0, 0), ASHLAR_D, "stone")
    return frame_world(P, A, D, "christs:" + name, z0=z0)


# ------------------------------------------------------------------ the gate tower
def lights(P, xc, z0, z1, n, holes, lw=0.42, y=GY):
    """n-light window, four-centred light heads, hood mould with return drops."""
    mw = 0.1
    w = n * lw + (n + 1) * mw
    op = box(xc - w / 2, z0, xc + w / 2, z1)
    holes.append(op)
    yg = y - 0.28
    P.sides_xz(op, yg, y, STONE_D, inward=True)
    P.face_xz(op, yg, GLASS, mat="glass")
    Lg = unary_union([tudor(xc - w / 2 + mw + lw / 2 + i * (lw + mw), lw, z0, z1 - 0.18, n=3) for i in range(n)])
    P.slab(op.difference(Lg), yg, yg + 0.14, STONE_L)
    g = unary_union([box(xc - w / 2 - 0.2, z1 + 0.1, xc + w / 2 + 0.2, z1 + 0.24),
                     box(xc - w / 2 - 0.2, z1 - 0.3, xc - w / 2 - 0.08, z1 + 0.24),
                     box(xc + w / 2 + 0.08, z1 - 0.3, xc + w / 2 + 0.2, z1 + 0.24)])
    P.slab(g, y, y + 0.1, STONE_L)
    P.box(xc - w / 2 - 0.08, xc + w / 2 + 0.08, y, y + 0.1, z0 - 0.14, z0, STONE_L)


def heraldry(P, holes):
    """Lady Margaret's achievement over the arch: crowned arms in a bordure compony between two yales, the Tudor rose
    and the Beaufort portcullis above, daisies strewn over the ground."""
    y = GY
    x0, x1, z0, z1 = AX - 1.5, AX + 1.5, 3.55, 6.35
    pan = box(x0, z0, x1, z1)
    holes.append(pan)
    yb = y - 0.22
    P.sides_xz(pan, yb, y, STONE_D, inward=True)
    P.face_xz(pan, yb, F.shade(STONE, 0.9))
    P.slab(pan.buffer(0.15, join_style=2).difference(pan), y, y + 0.08, STONE_L)
    rng = np.random.default_rng(1505)
    keep = box(AX - 0.62, 3.7, AX + 0.62, 5.95).union(box(x0 + 0.1, 3.6, AX - 0.64, 5.3)).union(
        box(AX + 0.64, 3.6, x1 - 0.1, 5.3))
    for _ in range(22):
        u, v = rng.uniform(x0 + 0.15, x1 - 0.15), rng.uniform(z0 + 0.15, z1 - 0.15)
        if keep.intersects(box(u - 0.08, v - 0.08, u + 0.08, v + 0.08)):
            continue
        P.slab(quatrefoil(u, v, 0.09), yb, yb + 0.04, ARGENT, mat="render")
        P.slab(box(u - 0.02, v - 0.02, u + 0.02, v + 0.02), yb + 0.04, yb + 0.06, OR, mat="render")
    # arms: bordure compony (azure / argent blocks), quarterly France (azure) and England (gules) inside
    sx, sz, s = AX, 4.75, 1.75
    shp = Polygon([(sx - 0.25 * s, sz + 0.3 * s), (sx + 0.25 * s, sz + 0.3 * s), (sx + 0.25 * s, sz - 0.02 * s),
                   (sx + 0.12 * s, sz - 0.22 * s), (sx, sz - 0.3 * s), (sx - 0.12 * s, sz - 0.22 * s),
                   (sx - 0.25 * s, sz - 0.02 * s)])
    bord = shp.difference(shp.buffer(-0.07))
    for k in range(10):
        a0 = 2 * math.pi * k / 10
        wedge = Polygon([(sx, sz), (sx + 3 * math.cos(a0), sz + 3 * math.sin(a0)),
                         (sx + 3 * math.cos(a0 + 0.63), sz + 3 * math.sin(a0 + 0.63))])
        g = bord.intersection(wedge)
        if not g.is_empty:
            P.slab(g, yb + 0.05, yb + 0.12, AZURE if k % 2 else ARGENT, sides=False, mat="render")
    shield(P, sx, sz, s * 0.86, yb + 0.05, (AZURE, GULES))
    for k in range(4):
        qx, qz = sx + (-0.2 if k % 2 == 0 else 0.2), sz + (0.22 if k < 2 else -0.08)
        P.slab(Point(qx, qz).buffer(0.06, resolution=2), yb + 0.13, yb + 0.16, OR, mat="render")
    cr = unary_union([box(sx - 0.42, 5.4, sx + 0.42, 5.55)] +
                     [Polygon([(sx + u - 0.08, 5.55), (sx + u + 0.08, 5.55), (sx + u, 5.78)]) for u in (-0.34, -0.11, 0.11, 0.34)])
    P.slab(cr, yb, yb + 0.14, OR, mat="render")
    P.slab(box(sx - 0.05, 5.78, sx + 0.05, 5.98).union(box(sx - 0.11, 5.84, sx + 0.11, 5.9)), yb, yb + 0.1, OR,
           mat="render")
    yale(P, AX - 1.0, 3.7, 0.9, yb, flip=False)
    yale(P, AX + 1.0, 3.7, 0.9, yb, flip=True)
    rx, rz = x0 + 0.38, 6.0
    P.slab(Polygon([(rx + 0.22 * math.cos(a), rz + 0.22 * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 11)[:-1]]),
           yb, yb + 0.08, GULES, mat="render")
    P.slab(Polygon([(rx + 0.11 * math.cos(a), rz + 0.11 * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 9)[:-1]]),
           yb + 0.08, yb + 0.11, ARGENT, mat="render")
    px, pz = x1 - 0.38, 5.98
    grid = [box(px - 0.22, pz + 0.18, px + 0.22, pz + 0.24)]
    grid += [box(px + u - 0.02, pz - 0.26, px + u + 0.02, pz + 0.22) for u in (-0.17, -0.06, 0.06, 0.17)]
    grid += [box(px - 0.22, pz + v - 0.02, px + 0.22, pz + v + 0.02) for v in (-0.1, 0.05)]
    P.slab(unary_union(grid), yb, yb + 0.09, OR, mat="render")


def gate_face(P):
    y = GY
    holes = []
    big = tudor(AX, 2.7, 0.0, 2.55, n=6)       # squat: the street level was raised against the old gate
    holes.append(big)
    P.sides_xz(big, y - 0.7, y, STONE_D, inward=True, skip_ground=True)
    for k, b in enumerate((0.13, 0.26)):
        ring = big.buffer(b, join_style=1, resolution=4).difference(big.buffer(b - 0.13, join_style=1, resolution=4))
        P.slab(ring.intersection(box(-50, 0.0, 80, 9)), y, y + 0.05 * (k + 1), STONE_L if k == 0 else STONE)
    # the old oak gates: two leaves, vertical boarding with ribs, a wicket
    yg = y - 0.7
    P.face_xz(big, yg, OAK, mat="timber")
    xa, xb = AX - 1.35, AX + 1.35
    ribs = [box(AX - 0.04, 0, AX + 0.04, 3.8)]
    for k in range(1, 10):
        xx = xa + k * (xb - xa) / 10
        ribs.append(box(xx - 0.015, 0.05, xx + 0.015, 3.8))
    for zz in (0.7, 1.6, 2.4):
        ribs.append(box(xa, zz - 0.05, xb, zz + 0.05))
    P.slab(unary_union(ribs).intersection(big), yg, yg + 0.05, F.shade(OAK, 1.25), mat="timber")
    wk = box(AX - 1.15, 0.1, AX - 0.35, 1.8)
    P.slab(wk.exterior.buffer(0.03, join_style=2).intersection(big), yg, yg + 0.07, F.shade(OAK, 0.7), mat="timber")
    # spandrels with roses in quatrefoils, square label
    dr = box(AX - 1.85, 0.0, AX + 1.85, 3.3)
    P.slab(dr.difference(big.buffer(0.39, join_style=1, resolution=4)), y, y + 0.04, STONE)
    holes.append(dr)
    for sx in (-1, 1):
        cx, cz = AX + sx * 1.32, 2.85
        P.slab(quatrefoil(cx, cz, 0.32), y + 0.04, y + 0.1, STONE_D)
        P.slab(Point(cx, cz).buffer(0.11, resolution=2), y + 0.1, y + 0.15, GULES, mat="render")
    P.slab(unary_union([box(AX - 2.0, 3.3, AX + 2.0, 3.45), box(AX - 2.0, 2.75, AX - 1.86, 3.45),
                        box(AX + 1.86, 2.75, AX + 2.0, 3.45)]), y, y + 0.14, STONE_L)
    heraldry(P, holes)
    P.box(AX - 2.3, AX + 2.3, y, y + 0.14, 6.7, 6.88, STONE_L)              # string course
    lights(P, AX, 7.3, 8.75, 3, holes)                                       # first floor: three lights
    P.box(AX - 2.3, AX + 2.3, y, y + 0.12, 9.15, 9.3, STONE_L)
    lights(P, AX, 9.55, 10.25, 2, holes, lw=0.38)                            # small top-stage window
    x0, x1 = TURRETS[0][0] + 0.6, TURRETS[1][0] - 0.6
    face = box(x0, -0.6, x1, Z_PAR).difference(unary_union(holes))
    P.face_xz(face, y, STONE)
    jt = [box(x0, z - 0.012, x1, z + 0.012) for z in np.arange(0.9, Z_PAR, 0.42)]
    P.slab(unary_union(jt).intersection(face.buffer(-0.1)), y, y + 0.004, F.shade(STONE, 0.86), sides=False)
    for xa_, xb_ in ((x0, AX - 1.85), (AX + 1.85, x1)):
        P.extrude_profile([(y, -0.6), (y + 0.15, -0.6), (y + 0.15, 0.4), (y, 0.55)], xa_, xb_, STONE_D)
    # battlemented parapet
    P.extrude_profile([(y, Z_PAR - 0.2), (y + 0.2, Z_PAR), (y + 0.2, Z_PAR + 0.1), (y, Z_PAR + 0.13)], x0, x1, STONE_L)
    g = box(x0, Z_PAR, x1, Z_PAR + 0.5)
    n = 3
    p = (x1 - x0) / n
    merl = [box(x0 + i * p + 0.14, Z_PAR + 0.49, x0 + (i + 1) * p - 0.14, Z_MER) for i in range(n)]
    slab2(P, unary_union([g] + merl), y - 0.3, y, STONE)
    for i in range(n):
        xc = x0 + (i + 0.5) * p
        box6(P, xc - p / 2 + 0.1, xc + p / 2 - 0.1, y - 0.34, y + 0.05, Z_MER - 0.06, Z_MER + 0.02, STONE_L)
    # the tower's own side returns between the bay face and the range faces (hide the OSM step)
    for xe in (x0, x1):
        box6(P, xe - 0.05, xe + 0.05, y - 0.05, FY, -0.6, Z_PAR, STONE)


def turret(P, x, yc):
    """Polygonal stone turret: string rings, slit lights, corbelled battlemented crown with a lead cap."""
    r = TR
    zc = Z_TC - 1.25
    lathe(P, x, yc, [(r + 0.1, -0.6), (r + 0.1, 0.5), (r, 0.6), (r, zc - 0.5)], STONE, n=8)
    for z in (0.55, 3.4, 6.8, 9.25, Z_PAR + 0.05):
        lathe(P, x, yc, [(r + 0.06, z - 0.09), (r + 0.06, z + 0.09)], STONE_L, n=8)
    ap = r * math.cos(math.pi / 8)
    for k in range(8):
        a = k * math.pi / 4
        ca, sa = math.cos(a), math.sin(a)
        if sa < 0.3:          # street-side faces only (+y)
            continue
        for zb in (4.6, 7.8, 10.9):
            fx, fy = x + (ap + 0.03) * ca, yc + (ap + 0.03) * sa
            tx, ty = -sa, ca
            w, h = 0.12, 0.7
            P.quad((fx - tx * w, fy - ty * w, zb), (fx + tx * w, fy + ty * w, zb), (fx + tx * w, fy + ty * w, zb + h),
                   (fx - tx * w, fy - ty * w, zb + h), (ca, sa, 0), F.shade(OAK, 0.45), "glass")
    lathe(P, x, yc, [(r, zc - 0.5), (r + 0.12, zc - 0.3), (r + 0.2, zc - 0.05), (r + 0.2, zc + 0.3),
                     (r + 0.28, zc + 0.4), (r + 0.28, zc + 0.5)], STONE_L, n=8)
    rr = r + 0.2
    for k in range(8):
        a = k * math.pi / 4
        rm = rr * math.cos(math.pi / 8) - 0.13
        S = P_(STONE)
        box6(S, -0.3, 0.3, -0.13, 0.13, zc + 0.5, Z_TC - 0.08, STONE)
        box6(S, -0.34, 0.34, -0.17, 0.17, Z_TC - 0.08, Z_TC, STONE_L)
        place(P, S, x + rm * math.cos(a), yc + rm * math.sin(a), a - math.pi / 2)
    lathe(P, x, yc, [(rr - 0.26, zc + 0.5), (0.0, zc + 1.0)], LEAD, n=8, mat="plain")


def build_gate():
    P = P_(STONE)
    gate_face(P)
    for x, yc in TURRETS:
        turret(P, x, yc)
    return frame_world(P, A, D, "christs:great_gate", z0=GZ0)


def build(walls=None):
    out = [build_gate(),
           range_piece(-0.35, 10.15, 8.75, "range_n", end_l=True),
           range_piece(16.95, 36.6, 8.98, "range_s1"),
           range_piece(36.6, 56.5, 9.35, "range_s2", end_r=True)]
    return [it for it in out if it]


BUILDS = {KEY: build}
ELEMENTS = {}

if __name__ == "__main__":
    tot = 0
    for it in build([]):
        Tz = np.asarray(it["tris"])[..., 2]
        tot += len(it["tris"])
        print(it["name"], len(it["tris"]), round(float(Tz.min()), 2), round(float(Tz.max()), 2))
    print("total", tot)
