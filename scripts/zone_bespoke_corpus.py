"""Bespoke geometry for the Trumpington Street front of Corpus Christi College's New Court (William Wilkins, 1823-27),
session 36. OSM way/148880379 (building=university, ref CORPUS010) is the whole New Court ring (1089 m2, 57 nodes:
west range on Trumpington Street, south range, chapel/library ranges), so only the street (west) front is modelled and
the tile body stays visible (no HIDE_TILE): every face sits FY = 0.42 m proud of the OSM wall line and the glass of
each opening is at YG = 0.08 m (in front of the tile wall), as zone_bespoke_caius.py. The court side, the south range
and the roof are left to the tile body (LiDAR roof). zone_build.load_bespoke() picks up BUILDS. The building is
outside the Market Square walls.json, so build() gets no walls and works from the OSM footprint (no ELEMENTS).
NB: listing the way in BUILDS also makes city_facades.py skip its generic skins (way/148880379:1/:3/:9/:10/:16/:28/
:35/:36/:55, i.e. the two 29 m west walls this model replaces plus small south/east walls that lose their windows).

Frame: x = metres south along the west front from its north corner (OSM node 1619379567, E -186.79 N -180.25) to the
SW corner (node 1469982928, E -171.46 N -245.83), 67.35 m, axis 13.2 deg east of grid south; y = metres out of the
building (west, towards the street); z above Z0 = 9.55 (DTM on the pavement 9.6 at the north end, 9.2 at the south:
the plinth runs down to Z0 - 0.6).

Design (shape / proportion / colour only, no pixels used; downloaded to data/raw/commons_ref/corpus_*.jpg):
- "William Wilkins - Elevation for the West Front of the New Quadrangle of Corpus Christi College, Cambridge -
  B1977.14.1066 - Yale Center for British Art.jpg" (Wilkins' own elevation, Yale Center for British Art, CC0);
- geograph 7017873 "View of Corpus Christi College from Trumpington Street" (Robert Lamb, CC BY-SA 2.0);
- geograph 631710 "The Main Gate, Corpus Christi College" (RichTea, CC BY-SA 2.0).
Pale buff ashlar (Ketton/Bath type) throughout.
- two flanking ranges of six bays (x 10.5-29.1 and 38.3-56.85), three storeys: square-headed two-light cusped
  ground-floor windows in deep reveals under square label moulds; tall two-light pointed windows with a transom on the
  first floor and two-light pointed windows on the second, hood moulds with label stops; plinth, two string courses,
  a cornice with carved paterae and a battlemented parapet; grouped chimney stacks behind the parapet;
- central gate tower (turrets at x 30.2 / 37.2 = the OSM turret bumps, gate axis x 33.7 = the OSM gate footway):
  four-centred arch with three moulded orders, roundels in the spandrels, square label; the traceried timber gates
  stand open, folded against the reveals of the tile's gate passage; canopied statue niche between two-light windows, two windows above, raised battlemented parapet with a
  stepped centre and shield; two octagonal turrets with blind traceried panels, string rings, corbelled
  battlemented crowns;
- end pavilions (x 0-10.5 and 56.85-67.35): octagonal corner turrets, a corbelled canted oriel with a battlemented
  top on the first floor over a quatrefoil band, a tall three-light traceried window above, coped gable with a
  chimney at the apex.
Heights from the LiDAR DSM (data/lidar/dsm_1m.tif, 2023 first-return DSM as check) sampled 1-10 m inside the front:
range parapet merlons 15.95 (DSM 1 m inside 25.2-25.9 = 15.6-16.3), roof (tile body) ridge DSM 26.2-26.5 at 3-4 m
inside; gate parapet centre 16.9 (DSM 15.7-16.3 over the gate block); gate turret crowns 18.4 (DSM peaks 27.2-27.9 =
17.7-18.4 at x 32-33 / 39); pavilion turret crowns 17.5 (DSM 27.0 at x 61); chimney tops 18.4 (DSM spikes 27.9-28.1 =
18.4-18.6 at x 10, 22, 49 and 64-67); gable apex 17.9.
"""
import math
import os
import sys

import numpy as np
from shapely.geometry import Point, Polygon, box
from shapely.ops import unary_union

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import facade_parts as F  # noqa: E402
from zone_bespoke_kings import lathe, box6, pointed, tudor, quatrefoil, finial, place, slab2, frame_world  # noqa: E402

OSM = "way/148880379"
Z0 = 9.55
A = np.array([-186.79, -180.25])
B_ = np.array([-171.46, -245.83])
LEN = float(np.linalg.norm(B_ - A))          # 67.35
D = (B_ - A) / LEN

FY, YG = 0.42, 0.08
STONE = F.rgb("#d9cba8")
STONE_D = F.shade(STONE, 0.72)
STONE_L = F.shade(STONE, 1.06)
GLASS = F.rgb(F.GLASS_COL)
DOOR = F.rgb("#4a3322")
DARK = F.rgb("#34302a")
LEAD = F.rgb("#7f8589")

# storeys (z above Z0)
Z_STR1, Z_STR2, Z_CORN = 5.0, 10.1, 14.3
Z_PAR, Z_CREN, Z_MER = 14.65, 15.3, 15.95
G_XC, G_T = 33.7, (30.2, 37.2)          # gate axis, gate turret centres
NR = (10.5, 29.1)                       # north range (x)
SR = (38.3, 56.85)                      # south range
PAV = ((0.0, 10.5), (56.85, LEN))       # end pavilions


def P_():
    return F.Parts(mat="stone", wall_col=STONE)


# ------------------------------------------------------------------ windows

def hood(P, op, x0, x1, zs, y=FY, stops=True):
    """Hood mould over an arched opening (ring above the springing) with square label stops."""
    ring = op.buffer(0.13, join_style=1, resolution=3).difference(op.buffer(0.02, join_style=1, resolution=3))
    P.slab(ring.intersection(box(x0 - 1, zs, x1 + 1, zs + 9)), y, y + 0.09, STONE_L)
    if stops:
        for xx in (x0 - 0.08, x1 + 0.08):
            P.box(xx - 0.09, xx + 0.09, y, y + 0.12, zs - 0.22, zs + 0.02, STONE_L)


def label(P, x0, x1, z1, y=FY, drop=0.35):
    """Square Tudor label mould over a flat-headed opening, with returns."""
    g = unary_union([box(x0 - 0.16, z1 + 0.06, x1 + 0.16, z1 + 0.2),
                     box(x0 - 0.16, z1 + 0.2 - drop, x0 - 0.04, z1 + 0.2),
                     box(x1 + 0.04, z1 + 0.2 - drop, x1 + 0.16, z1 + 0.2)])
    P.slab(g, y, y + 0.1, STONE_L)
    for xx in (x0 - 0.1, x1 + 0.1):
        P.box(xx - 0.08, xx + 0.08, y, y + 0.13, z1 + 0.2 - drop - 0.14, z1 + 0.2 - drop, STONE_L)


def lights_pointed(xc, w, z0, zs, n, transom=None, k=0.6):
    """Opening split into n pointed lights with mullions (0.09 m), an optional transom and a head roundel."""
    mw = 0.09
    lw = (w - mw * (n + 1)) / n
    ls = []
    for i in range(n):
        xl = xc - w / 2 + mw + lw / 2 + i * (lw + mw)
        ls.append(pointed(xl, lw, z0, zs - 0.02, k=0.6, n=4))
    g = unary_union(ls)
    if transom is not None:
        g = g.difference(box(xc - w, transom - 0.045, xc + w, transom + 0.045))
    return g


def window(P, xc, w, z0, z1, holes, n=2, transom=None, head="pointed", y=FY, yg=YG):
    """Opening in the wall face at y with reveals back to the glass at YG, stone mullion/transom tracery, sill and
    hood mould. Appends the opening polygon to holes. z1 = apex (pointed) or head (square)."""
    if head == "square":
        op = box(xc - w / 2, z0, xc + w / 2, z1)
        zs = z1
    elif head == "tudor":
        zs = z1 - 0.22 * w
        op = tudor(xc, w, z0, zs, n=4)
    else:
        zs = z1 - 0.6 * w * math.sin(math.acos((w / 2 - 0.6 * w) / (0.6 * w)))   # two-centred apex height
        op = pointed(xc, w, z0, zs, k=0.6, n=5)
    holes.append(op)
    P.sides_xz(op, yg, y, STONE_D, inward=True)
    P.face_xz(op, yg, GLASS, mat="glass")
    if head == "square":   # cusped heads to the lights
        mw = 0.09
        lw = (w - mw * (n + 1)) / n
        lights = unary_union([pointed(xc - w / 2 + mw + lw / 2 + i * (lw + mw), lw, z0, z1 - 0.32, k=0.75, n=3)
                              for i in range(n)])
        if transom is not None:
            lights = lights.difference(box(xc - w, transom - 0.045, xc + w, transom + 0.045))
    else:
        lights = lights_pointed(xc, w, z0, zs, n, transom)
        lights = lights.union(Point(xc, zs + (z1 - zs) * 0.45).buffer(min(0.16, w * 0.12), resolution=2))
    trac = op.difference(lights)
    if not trac.is_empty:
        P.slab(trac, yg + 0.02, yg + 0.13, STONE_L)
    P.box(xc - w / 2 - 0.08, xc + w / 2 + 0.08, y, y + 0.12, z0 - 0.14, z0, STONE_L)   # sill
    if head == "square":
        label(P, xc - w / 2, xc + w / 2, z1, y)
    else:
        hood(P, op, xc - w / 2, xc + w / 2, zs, y)
    return op


# ------------------------------------------------------------------ continuous wall elements

def wall_face(P, x0, x1, z0, z1, holes, y=FY):
    g = box(x0, z0, x1, z1)
    if holes:
        g = g.difference(unary_union(holes))
    P.face_xz(g, y, STONE)


def strings(P, x0, x1, y=FY, cornice=True):
    P.extrude_profile([(y, -0.6), (y + 0.16, -0.6), (y + 0.16, 0.45), (y, 0.62)], x0, x1, STONE_D)      # plinth
    for z in (Z_STR1, Z_STR2):
        P.extrude_profile([(y, z - 0.1), (y + 0.13, z - 0.04), (y + 0.13, z + 0.06), (y, z + 0.1)], x0, x1, STONE_L)
    if cornice:
        P.extrude_profile([(y, Z_CORN - 0.12), (y + 0.12, Z_CORN - 0.05), (y + 0.24, Z_CORN + 0.2),
                           (y + 0.24, Z_CORN + 0.32), (y, Z_CORN + 0.35)], x0, x1, STONE_L)
        n = int((x1 - x0) / 1.55)
        for i in range(n):   # carved paterae under the cornice
            xc = x0 + (i + 0.5) * (x1 - x0) / n
            P.slab(quatrefoil(xc, Z_CORN - 0.32, 0.15), y, y + 0.08, STONE_L)


def battlements(P, x0, x1, zb, zc, zm, y=FY, mw=0.75, pitch=1.45):
    """Parapet wall zb..zc with merlons up to zm (front face at y, 0.32 m thick), coped."""
    n = max(1, int(round((x1 - x0) / pitch)))
    p = (x1 - x0) / n
    g = box(x0, zb, x1, zc)
    merl = [box(x0 + i * p + (p - mw) / 2, zc - 0.01, x0 + i * p + (p + mw) / 2, zm) for i in range(n)]
    g = unary_union([g] + merl)
    slab2(P, g, y - 0.32, y, STONE)
    P.box(x0, x1, y - 0.36, y + 0.04, zc - 0.08, zc, STONE_L, bottom=False)   # coping of the crenels
    for m in merl:
        a, _, b, _ = m.bounds
        box6(P, a - 0.03, b + 0.03, y - 0.35, y + 0.03, zm - 0.08, zm + 0.02, STONE_L)


def chimney(P, x, y, z0, z1):
    box6(P, x - 0.85, x + 0.85, y - 0.45, y + 0.45, z0, z1 - 1.2, STONE)
    P.box(x - 0.9, x + 0.9, y - 0.5, y + 0.5, z1 - 1.3, z1 - 1.15, STONE_L)
    for dx in (-0.55, 0.0, 0.55):
        lathe(P, x + dx, y, [(0.2, z1 - 1.15), (0.2, z1 - 0.15), (0.25, z1 - 0.1), (0.25, z1), (0.12, z1)], STONE,
              n=8)
        lathe(P, x + dx, y, [(0.12, z1), (0.12, z1 - 0.3), (0.0, z1 - 0.3)], DARK, n=4)


def turret(P, x, y, r, ztop, panels=True):
    """Octagonal turret from the plinth to the crown base ztop - 0.8, string rings, blind panels, corbelled
    battlemented crown with a lead flat."""
    zc = ztop - 0.8
    prof = [(r + 0.12, -0.6), (r + 0.12, 0.5), (r, 0.65)]
    for z in (Z_STR1, Z_STR2, Z_CORN + 0.1):
        if z < zc - 0.5:
            prof += [(r, z - 0.1), (r + 0.1, z - 0.02), (r + 0.1, z + 0.08), (r, z + 0.12)]
    prof += [(r, zc - 0.25), (r + 0.2, zc), (r + 0.2, zc + 0.1)]
    lathe(P, x, y, prof, STONE, n=8)
    ap, side = r * math.cos(math.pi / 8), 2 * r * math.sin(math.pi / 8)
    if panels:
        tiers = [(Z_STR2 + 0.3, Z_CORN - 0.3), (Z_CORN + 0.35, zc - 0.4), (Z_STR1 + 0.35, Z_STR2 - 0.4)]
        for i in range(8):
            a = i * math.pi / 4
            nx, ny = math.cos(a), math.sin(a)
            if ny < -0.3:    # faces turned into the building are hidden
                continue
            S = P_()
            for za, zb in tiers:
                if zb - za > 0.8:
                    S.slab(pointed(0, side * 0.6, za, zb - side * 0.36, k=0.6, n=3).exterior.buffer(0.035, join_style=2),
                           0, 0.03, STONE_L)
            place(P, S, x + ap * nx, y + ap * ny, a - math.pi / 2)
    rr = r + 0.2
    lathe(P, x, y, [(rr, zc + 0.1), (rr - 0.25, zc + 0.1)], LEAD, n=8)   # lead flat
    for i in range(8):   # merlons on the eight angles
        a = math.pi / 8 + i * math.pi / 4
        cx, cy = x + (rr - 0.12) * math.cos(a), y + (rr - 0.12) * math.sin(a)
        box6(P, cx - 0.16, cx + 0.16, cy - 0.16, cy + 0.16, zc + 0.1, ztop, STONE_L)
    lathe(P, x, y, [(rr - 0.05, zc + 0.1), (rr - 0.05, zc + 0.35), (rr - 0.3, zc + 0.35)], STONE, n=8)


# ------------------------------------------------------------------ parts of the front

def range_front(P, x0, x1, nb=6):
    holes = []
    bw = (x1 - x0) / nb
    for i in range(nb):
        xc = x0 + (i + 0.5) * bw
        window(P, xc, 1.05, 1.45, 3.3, holes, head="square")
        window(P, xc, 1.25, 5.75, 9.35, holes, transom=7.6)
        window(P, xc, 1.15, 10.75, 13.45, holes)
    wall_face(P, x0, x1, -0.6, Z_PAR, holes)
    strings(P, x0, x1)
    battlements(P, x0, x1, Z_PAR, Z_CREN, Z_MER)


def gate_block():
    P = P_()
    yb = FY + 0.38
    x0, x1 = G_T[0], G_T[1]
    holes = []
    arch = tudor(G_XC, 3.6, 0.0, 3.4, n=6)
    holes.append(arch)
    # arch: reveals back to the gates, moulded orders, spandrel roundels
    # the gates stand open (as in the references): the arch reveals run back to the tile's gate passage and the two
    # traceried timber leaves are folded back against the reveals
    P.sides_xz(arch, -0.3, yb, STONE_D, inward=True, skip_ground=True)
    for sx in (-1, 1):
        xl = G_XC + sx * 1.72
        S = P_()
        for za, zb2 in ((0.3, 1.5), (1.8, 3.1)):
            S.slab(box(-0.65, za, 0.65, zb2).exterior.buffer(0.04, join_style=2), 0.0, 0.04, F.shade(DOOR, 1.25),
                   mat="timber")
        for k in range(3):
            S.slab(pointed(-0.4 + 0.4 * k, 0.28, 3.3, 3.85, k=0.6, n=3).exterior.buffer(0.025, join_style=2), 0.0, 0.04,
                   F.shade(DOOR, 1.25), mat="timber")
        slab2(S, box(-0.8, 0.02, 0.8, 3.4), -0.08, 0.0, DOOR, mat="timber")
        # leaf in its own frame: x along the leaf (back into the passage), y = into the opening
        place(P, S, xl, yb - 0.95, -math.pi / 2 if sx < 0 else math.pi / 2)
    for k, (b, dy) in enumerate(((0.16, 0.06), (0.32, 0.13), (0.5, 0.2))):
        ring = arch.buffer(b, join_style=1, resolution=4).difference(arch.buffer(b - 0.16, join_style=1, resolution=4))
        P.slab(ring.intersection(box(G_XC - 4, 0, G_XC + 4, 9)), yb, yb + dy, STONE_L if k != 1 else STONE)
    # square label over the arch and roundels with roses in the spandrels
    label(P, G_XC - 2.35, G_XC + 2.35, 4.75, yb, drop=1.6)
    for sx in (-1, 1):
        xr = G_XC + sx * 1.75
        P.slab(Point(xr, 4.15).buffer(0.42, resolution=4).difference(Point(xr, 4.15).buffer(0.32, resolution=4)), yb,
               yb + 0.08, STONE_L)
        P.slab(unary_union([Point(xr + 0.14 * math.cos(a), 4.15 + 0.14 * math.sin(a)).buffer(0.1, resolution=2)
                            for a in np.linspace(0, 2 * math.pi, 6)[:-1]]), yb, yb + 0.1, STONE_L)
    # first floor: canopied niche between two-light windows; second floor: two windows and a panel
    window(P, G_XC - 1.75, 1.0, 6.0, 9.1, holes, y=yb)
    window(P, G_XC + 1.75, 1.0, 6.0, 9.1, holes, y=yb)
    niche = pointed(G_XC, 0.85, 5.9, 8.6, k=0.6, n=4)
    holes.append(niche)
    P.sides_xz(niche, yb - 0.3, yb, STONE_D, inward=True)
    P.face_xz(niche, yb - 0.3, F.shade(STONE, 0.62))
    lathe(P, G_XC, yb - 0.15, [(0.22, 5.95), (0.22, 7.3), (0.14, 7.5), (0.0, 7.7)], STONE_L, n=6)   # statue
    P.box(G_XC - 0.4, G_XC + 0.4, yb, yb + 0.3, 5.6, 5.9, STONE_L)                                 # corbel
    lathe(P, G_XC, yb + 0.1, [(0.45, 8.9), (0.45, 9.4), (0.0, 10.6)], STONE_L, n=4, a0=math.pi / 4)  # canopy spirelet
    finial(P, G_XC, yb + 0.1, 10.55, 0.7)
    window(P, G_XC - 1.5, 0.9, 10.8, 13.4, holes, y=yb)
    window(P, G_XC + 1.5, 0.9, 10.8, 13.4, holes, y=yb)
    P.slab(Polygon([(G_XC - 0.45, 13.0), (G_XC + 0.45, 13.0), (G_XC + 0.45, 12.2), (G_XC + 0.25, 11.75),
                    (G_XC, 11.6), (G_XC - 0.25, 11.75), (G_XC - 0.45, 12.2)]), yb, yb + 0.12, STONE_L)   # shield
    wall_face(P, x0, x1, -0.6, Z_PAR + 0.3, holes, y=yb)
    for x in (x0, x1):   # returns back to the range face
        P.quad((x, FY, -0.6), (x, yb, -0.6), (x, yb, Z_PAR + 0.3), (x, FY, Z_PAR + 0.3), (-1 if x == x0 else 1, 0, 0),
               STONE)
    P.extrude_profile([(yb, -0.6), (yb + 0.16, -0.6), (yb + 0.16, 0.45), (yb, 0.62)], x0, G_XC - 1.8, STONE_D)
    P.extrude_profile([(yb, -0.6), (yb + 0.16, -0.6), (yb + 0.16, 0.45), (yb, 0.62)], G_XC + 1.8, x1, STONE_D)
    for z in (Z_STR1 + 0.3, Z_STR2):
        P.extrude_profile([(yb, z - 0.1), (yb + 0.13, z - 0.04), (yb + 0.13, z + 0.06), (yb, z + 0.1)], x0, x1, STONE_L)
    P.extrude_profile([(yb, Z_CORN), (yb + 0.25, Z_CORN + 0.25), (yb + 0.25, Z_CORN + 0.4), (yb, Z_CORN + 0.45)],
                      x0, x1, STONE_L)
    for i in range(5):   # quatrefoil frieze under the cornice
        xc = x0 + 1.4 + i * (x1 - x0 - 2.8) / 4
        P.slab(box(xc - 0.3, 13.75, xc + 0.3, 14.25).difference(quatrefoil(xc, 14.0, 0.2)), yb, yb + 0.05, STONE_L)
    # raised parapet, battlemented, with a stepped centre carrying a shield
    zb = Z_PAR + 0.3
    battlements(P, x0 + 0.9, G_XC - 1.0, zb, zb + 0.6, zb + 1.2, yb, mw=0.6, pitch=1.1)
    battlements(P, G_XC + 1.0, x1 - 0.9, zb, zb + 0.6, zb + 1.2, yb, mw=0.6, pitch=1.1)
    step = Polygon([(G_XC - 1.0, zb), (G_XC + 1.0, zb), (G_XC + 1.0, zb + 1.3), (G_XC + 0.6, zb + 1.3),
                    (G_XC + 0.6, zb + 1.95), (G_XC - 0.6, zb + 1.95), (G_XC - 0.6, zb + 1.3), (G_XC - 1.0, zb + 1.3)])
    slab2(P, step, yb - 0.32, yb, STONE)
    P.slab(Polygon([(G_XC - 0.35, zb + 1.75), (G_XC + 0.35, zb + 1.75), (G_XC + 0.35, zb + 1.3), (G_XC, zb + 0.95),
                    (G_XC - 0.35, zb + 1.3)]), yb, yb + 0.1, STONE_L)
    for x in G_T:
        turret(P, x, FY + 0.05, 1.1, 18.4)
    return P


def pavilion(P, x0, x1):
    xc = (x0 + x1) / 2
    holes = []
    t0, t1 = x0 + 0.85, x1 - 0.85
    # ground floor: two small square-headed windows; quatrefoil band
    for dx in (-1.6, 1.6):
        window(P, xc + dx, 0.95, 1.45, 3.0, holes, head="square")
    for i in range(7):
        xq = xc - 2.7 + i * 0.9
        P.slab(box(xq - 0.38, 3.35, xq + 0.38, 3.95).difference(quatrefoil(xq, 3.65, 0.24)), FY, FY + 0.05, STONE_L)
    # first floor: corbelled canted oriel (front 2.4 m, splayed sides, 0.9 m out)
    yo, wf, wb = FY + 0.9, 2.4, 3.6
    ob = Polygon([(xc - wb / 2, FY), (xc + wb / 2, FY), (xc + wf / 2, yo), (xc - wf / 2, yo)])
    S = P_()
    zb, zt = 4.6, 9.3
    fh = []
    window(S, 0.0, 1.9, 5.0, 8.9, fh, n=3, transom=7.0, head="square", y=0.0, yg=-0.25)
    S.face_xz(box(-wf / 2, zb, wf / 2, zt).difference(unary_union(fh)), 0.0, STONE)
    battlements(S, -wf / 2, wf / 2, zt, zt + 0.45, zt + 0.95, y=0.0, mw=0.4, pitch=0.8)
    place(P, S, xc, yo, 0)
    for sgn in (-1, 1):   # splayed sides with one light each
        pa = np.array([xc + sgn * wb / 2, FY])
        pb = np.array([xc + sgn * wf / 2, yo])
        L = float(np.linalg.norm(pb - pa))
        S = P_()
        sh = []
        window(S, L / 2, 0.55, 5.0, 8.9, sh, n=1, transom=7.0, head="square", y=0.0, yg=-0.2)
        S.face_xz(box(0, zb, L, zt + 0.45).difference(unary_union(sh)), 0.0, STONE)
        if sgn < 0:
            place(P, S, pa[0], pa[1], math.atan2(pb[1] - pa[1], pb[0] - pa[0]))
        else:
            place(P, S, pb[0], pb[1], math.atan2(pa[1] - pb[1], pa[0] - pb[0]))
    for k in range(4):   # stepped corbelling under the oriel, shrinking downwards
        sc = 1 - k / 4
        za, zb2 = zb - 0.15 * (k + 1), zb - 0.15 * k
        hw = wf / 2 * (0.55 + 0.45 * sc)
        g = [(xc - wb / 2 * (0.55 + 0.45 * sc), FY), (xc + wb / 2 * (0.55 + 0.45 * sc), FY),
             (xc + hw, FY + 0.9 * sc), (xc - hw, FY + 0.9 * sc)]
        if sc <= 0.05:
            break
        T2 = F.earcut2d(Polygon(g))
        P.add(np.stack([T2[..., 0], T2[..., 1], np.full(T2.shape[:2], za)], -1), (0, 0, -1), STONE_L)
        for i, j in ((1, 2), (2, 3), (3, 0)):
            (ax, ay), (bx, by) = g[i], g[j]
            nx, ny = by - ay, -(bx - ax)          # right of a CCW edge (x right, y out) = outward
            ln = math.hypot(nx, ny) or 1
            P.quad((ax, ay, za), (bx, by, za), (bx, by, zb2), (ax, ay, zb2), (nx / ln, ny / ln, 0), STONE_L)
    T2 = F.earcut2d(ob)
    P.add(np.stack([T2[..., 0], T2[..., 1], np.full(T2.shape[:2], zt + 0.45)], -1), (0, 0, 1), LEAD)
    # second floor: tall three-light traceried window into the gable
    window(P, xc, 1.85, 10.6, 14.6, holes, n=3)
    # wall up to the gable and the coped gable
    apex = 17.9
    gable = Polygon([(t0, -0.6), (t1, -0.6), (t1, Z_CORN + 0.35), (xc, apex - 0.35), (t0, Z_CORN + 0.35)])
    P.face_xz(gable.difference(unary_union(holes)), FY, STONE)
    strings(P, t0, t1, cornice=False)
    for (ax, az), (bx, bz) in (((t0 - 0.05, Z_CORN + 0.3), (xc, apex - 0.4)), ((xc, apex - 0.4), (t1 + 0.05, Z_CORN + 0.3))):
        dx, dz = bx - ax, bz - az
        L = math.hypot(dx, dz)
        nx, nz = -dz / L * 0.4, dx / L * 0.4
        cop = Polygon([(ax, az), (bx, bz), (bx + nx, bz + nz), (ax + nx, az + nz)])
        slab2(P, cop, -1.0, FY + 0.1, STONE_L)
    chimney(P, xc, FY - 0.5, apex - 1.0, 18.4)
    for x in (t0, t1):
        turret(P, x, FY + 0.05, 0.85, 17.5)
    # end returns (the facade layer edge) at the outer corners
    for x, nx in ((x0, -1), (x1, 1)):
        if x in (0.0, LEN):
            P.quad((x, 0, -0.6), (x, FY, -0.6), (x, FY, Z_MER), (x, 0, Z_MER), (nx, 0, 0), STONE)


def front():
    P = P_()
    range_front(P, *NR)
    range_front(P, *SR)
    # short wall pieces between the ranges and the gate turrets
    for a, b in ((NR[1], G_T[0]), (G_T[1], SR[0])):
        wall_face(P, a, b, -0.6, Z_PAR, [])
        strings(P, a, b, cornice=False)
    for x0, x1 in PAV:
        pavilion(P, x0, x1)
    G = gate_block()
    P.t += G.t; P.n += G.n; P.c += G.c; P.m += G.m
    for x in (10.8, 22.0, 49.5):   # grouped stacks behind the parapet, on the range roof (DSM spikes)
        chimney(P, x, -3.6, 15.6, 18.4)
    return P


def build(walls=None):
    out = frame_world(front(), A, D, "corpus:west_front", z0=Z0)
    return [out] if out is not None else []


BUILDS = {OSM: build}
ELEMENTS = {}   # not in walls.json
# no HIDE_TILE: only the street front of the New Court ring is modelled; the tile body carries the rest

if __name__ == "__main__":
    items = build([])
    for it in items:
        Tz = np.asarray(it["tris"])[..., 2]
        print(it["name"], len(it["tris"]), round(float(Tz.min()), 2), round(float(Tz.max()), 2))
    print("total", sum(len(i["tris"]) for i in items))
