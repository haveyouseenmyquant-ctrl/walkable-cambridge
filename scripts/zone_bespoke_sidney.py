"""Bespoke geometry for Sidney Sussex College's street front on Sidney Street (ring 1), session 66.

The college is E-shaped towards the street: three ranges run east-north-east from Sidney Street and end in gables on
the street line, with Hall Court and Chapel Court between them behind the brick boundary walls (wisteria). Sir Jeffry
Wyatville refaced the college in 1821-33 in Roman cement lined out as buff ashlar, in a Tudor-Gothic manner: crow-
stepped gables with an apex stack, square-headed mullioned and transomed windows under label moulds, corbelled oriels,
and the gate tower at the street end of the middle range with the four-centred entrance arch.
OSM ways (all building=university): way/147456527 SID013 (north range, street end = edge 10), way/147456522 SID010
(middle range / gate tower, street end = edges 9-12), way/147456529 SID019 (south range, street end = edge 7). Only
the street gable ends are modelled; the tile bodies (LiDAR roofs) and the city facade skins on every other wall stay,
so BUILDS uses pseudo ids ("way/...:sidney") as zone_bespoke_stjohnsgate.py does. Each gable face sits FY proud of
the OSM wall line so the city skin of the same wall stays hidden behind it.

Frame per gable: x = metres along the OSM edge from p0 to p1 (south-south-east), y = metres out (west-south-west,
towards Sidney Street), z above the DTM at the wall (Z0).

Design (shape / proportion / colour only, no pixels used; none of these are held-out benchmark photos):
- "1125495 II SIDNEY SUSSEX COLLEGE, WALLS FRONTING SIDNEY STREET Cambridge 20250614 0001.jpg" and "... 0003.jpg"
  (Tilman2007, CC BY-SA 4.0): south gable with the corbelled oriel carrying the founder's shield, crow-stepped gable
  with the apex stack; the gate tower with stepped gable, corner stubs and flagpole;
- "Cambridge - Sidney Street - View ENE on the Wisteria of Sidney Sussex College - Buildings altered in early 19th
  Century to the designs of Sir Jeffrey Wyattville.jpg" (Txllxt TxllxT, CC BY-SA 4.0): the three gables and the wall;
- "Entrance, Sidney Sussex College - geograph.org.uk - 4840872.jpg" (CC BY-SA 2.0): the entrance arch with traceried
  spandrels under a square label, the canted oriel above it and a three-light window over that.
Heights from the LiDAR DSM (data/lidar/dsm_1m.tif) sampled 0.5-3 m inside each gable (DTM 9.1-9.8 on the street):
SID013 apex 21.8-22.0 (12.1 over Z0 9.8); SID010 tower top 24.4-24.6 (14.9 over 9.6), one 27.1 spike (flagpole /
stack); SID019 apex 22.4-22.7 (13.4 over 9.1), shoulders 19.1-20.1. NB the LiDAR gables sit ~2 m south-south-east of
the OSM edges; the OSM footprints (= tile collision) are kept.
"""
import math
import os
import sys

import numpy as np
from shapely.geometry import Polygon, box
from shapely.ops import unary_union

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import facade_parts as F  # noqa: E402
from zone_bespoke_kings import box6, tudor, slab2, frame_world  # noqa: E402

REND = F.rgb("#cbb895")          # Roman cement lined out as buff ashlar
REND_D = F.shade(REND, 0.78)
STONE = F.rgb("#d3c39f")         # dressings
STONE_L = F.shade(STONE, 1.05)
GLASS = F.rgb(F.GLASS_COL)
FRAME = F.rgb("#ece8dc")         # white-painted window frames
DARK = F.rgb("#3a3631")
LEAD = F.rgb("#7f8589")
GULES, AZURE, OR = F.rgb("#9a2a24"), F.rgb("#2b4a8a"), F.rgb("#c8a24a")

# (key, p0, p1, Z0, eave, apex, kind); p0/p1 = OSM street edge (local E, N), kind: oriel / gate / plain
GABLES = [
    ("way/147456527:sidney", (-60.04, 293.02), (-56.12, 286.79), 9.8, 9.4, 12.1, "plain"),
    ("way/147456522:sidney", (-43.21, 266.32), (-38.77, 259.04), 9.6, 12.4, 14.9, "gate"),
    ("way/147456529:sidney", (-26.09, 241.70), (-21.44, 234.75), 9.1, 10.2, 13.4, "oriel"),
]
FY = 0.65   # gable face proud of the OSM wall line (covers the city skin's shopfront / reveals behind it)
_OPS = []   # (kind, E, N) of every opening, world frame (for the facade KPI, city_facades.bespoke_elements)


def P_():
    return F.Parts(mat="stone", wall_col=REND)


def mullioned(P, xc, z0, z1, n, holes, lw=0.55, y=FY, label=True):
    """n-light square-headed window: reveal, white sashes with glazing bars, stone mullions, a transom if tall, sill
    and a label mould with return drops."""
    mw = 0.12
    w = n * lw + (n + 1) * mw
    op = box(xc - w / 2, z0, xc + w / 2, z1)
    holes.append(op)
    yg = y - 0.28
    P.sides_xz(op, yg, y, REND_D, inward=True)
    P.face_xz(op, yg, GLASS, mat="glass")
    tall = (z1 - z0) > 1.6
    zt = z0 + (z1 - z0) * 0.62
    bars = [box(xc - w / 2 + mw + lw + i * (lw + mw), z0, xc - w / 2 + (i + 1) * (lw + mw) + mw, z1) for i in range(n - 1)]
    if tall:
        bars.append(box(xc - w / 2, zt - 0.06, xc + w / 2, zt + 0.06))
    P.slab(unary_union(bars), yg, yg + 0.16, STONE_L)
    # glazing bars of the sashes (thin white grid)
    gb = []
    for i in range(n):
        lx0 = xc - w / 2 + mw + i * (lw + mw)
        gb.append(box(lx0 + lw / 2 - 0.02, z0, lx0 + lw / 2 + 0.02, z1))
        for zz in np.arange(z0 + 0.45, z1 - 0.2, 0.45):
            gb.append(box(lx0, zz - 0.02, lx0 + lw, zz + 0.02))
    P.slab(unary_union(gb).intersection(op), yg, yg + 0.05, FRAME, sides=False, mat="plain")
    P.box(xc - w / 2 - 0.1, xc + w / 2 + 0.1, y, y + 0.1, z0 - 0.14, z0, STONE_L)            # sill
    if label:
        g = unary_union([box(xc - w / 2 - 0.18, z1 + 0.1, xc + w / 2 + 0.18, z1 + 0.24),
                         box(xc - w / 2 - 0.18, z1 - 0.32, xc - w / 2 - 0.06, z1 + 0.24),
                         box(xc + w / 2 + 0.06, z1 - 0.32, xc + w / 2 + 0.18, z1 + 0.24)])
        P.slab(g, y, y + 0.1, STONE_L)
    return w


def stepped(L, He, Ha, k=5, sw=0.42):
    """Crow-stepped gable outline above the eave line: k steps a side up to an apex stack of width 2 * sw."""
    pts = [(0, He)]
    run = (L / 2 - sw) / k
    rise = (Ha - He) / (k + 0.5)
    for i in range(k):
        z = He + rise * (i + 1)
        pts += [(i * run, z), ((i + 1) * run, z)]
    pts += [(L / 2 - sw, Ha), (L / 2 + sw, Ha)]
    for i in reversed(range(k)):
        z = He + rise * (i + 1)
        pts += [(L - (i + 1) * run, z), (L - i * run, z)]
    pts += [(L, He)]
    return Polygon(pts), run, rise


def gable(key, p0, p1, Z0, He, Ha, kind):
    p0, p1 = np.array(p0, float), np.array(p1, float)
    L = float(np.linalg.norm(p1 - p0))
    d = (p1 - p0) / L
    n_out = np.array([d[1], -d[0]])
    P = P_()
    holes = []
    xc = L / 2
    y = FY

    def op(kind_, x, z=None):
        w = p0 + d * x + n_out * 0.0
        _OPS.append((kind_, float(w[0]), float(w[1])))

    k = 5 if kind != "gate" else 4
    gpoly, run, rise = stepped(L, He, Ha, k=k)
    # ---- openings by type
    if kind == "gate":
        # entrance: four-centred arch under a square label with traceried spandrels, vaulted passage behind
        aw, az = 3.0, 2.6
        arch = tudor(xc, aw, -0.05, az, n=6)
        holes.append(arch)
        P.sides_xz(arch, y - 1.6, y, STONE, inward=True)
        P.face_xz(arch, y - 1.6, F.shade(DARK, 1.3), mat="plain")
        surround = arch.buffer(0.22, join_style=2).difference(arch).intersection(box(0, 0, L, 10))
        P.slab(surround, y, y + 0.08, STONE_L)
        lab = box(xc - aw / 2 - 0.42, -0.05, xc + aw / 2 + 0.42, az + 1.35)
        span = box(xc - aw / 2 - 0.3, az - 0.2, xc + aw / 2 + 0.3, az + 1.2).difference(arch.buffer(0.22))
        P.slab(span, y, y + 0.04, STONE)
        for sx in (-1, 1):
            cx = xc + sx * (aw / 2 - 0.15)
            ring = Polygon([(cx + 0.32 * math.cos(a), az + 0.75 + 0.32 * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 9)[:-1]])
            P.slab(ring.exterior.buffer(0.04), y + 0.04, y + 0.09, STONE_L, sides=False)
        lb = lab.exterior.buffer(0.08, join_style=2).intersection(box(0, az - 0.6, L, az + 1.5))
        P.slab(lb.difference(box(xc - aw / 2 - 0.34, -1, xc + aw / 2 + 0.34, az + 1.27)), y, y + 0.14, STONE_L)
        # iron gates folded back against the reveals
        for sx in (-1, 1):
            box6(P, xc + sx * (aw / 2 - 0.05) - 0.03, xc + sx * (aw / 2 - 0.05) + 0.03, y - 1.5, y - 0.2, 0, az - 0.1,
                 DARK, mat="plain")
        op("door", xc)
        # canted oriel above the entrance, three-light window over it
        oriel(P, xc, 4.2, 6.9, 2.5, holes, y)
        op("window", xc)
        w3 = mullioned(P, xc, 8.1, 9.6, 3, holes)
        op("window", xc)
        # side lights low down either side of the arch
        for sx in (-1, 1):
            mullioned(P, xc + sx * 3.05, 4.6, 6.2, 1, holes, lw=0.45)
            op("window", xc + sx * 3.05)
        # attic light in the gable
        mullioned(P, xc, He + 0.35, He + 1.35, 2, holes, lw=0.45)
        op("window", xc)
        # corner stubs (square buttress-turrets rising above the shoulders with stepped caps) and the flagpole
        for x0 in (-0.35, L - 0.55):
            box6(P, x0, x0 + 0.9, y - 0.2, y + 0.3, -0.6, He + 1.2, REND)
            box6(P, x0 - 0.06, x0 + 0.96, y - 0.26, y + 0.36, He + 1.2, He + 1.38, STONE_L)
            for j in range(3):
                box6(P, x0 + 0.1 * j + 0.05, x0 + 0.85 - 0.1 * j, y - 0.15, y + 0.25 - 0.08 * j,
                     He + 1.38 + 0.35 * j, He + 1.73 + 0.35 * j, REND)
        box6(P, xc - 0.04, xc + 0.04, y - 0.5, y - 0.42, Ha + 0.6, Ha + 5.5, FRAME, mat="plain")
        for zz in (2.7 + 0.05, 7.6):
            P.extrude_profile([(y, zz - 0.1), (y + 0.14, zz), (y + 0.14, zz + 0.1), (y, zz + 0.16)], 0.55, L - 0.55,
                              STONE_L)
    else:
        floors = [(1.0, 2.6), (4.0, 5.9), (7.0, 8.5)] if He < 10 else [(1.0, 2.6), (4.1, 6.0), (7.3, 9.0)]
        if kind == "oriel":
            # ground floor blank (boundary wall side), oriel on the first floor with the founder's shield on the corbel
            oriel(P, xc, 3.8, 6.5, 2.3, holes, y, shield=True)
            op("window", xc)
            mullioned(P, xc, 7.5, 9.0, 3, holes)
            op("window", xc)
        else:
            for z0, z1 in floors:
                mullioned(P, xc, z0, z1, 2 if z0 < 3 else 3, holes)
                op("window", xc)
        mullioned(P, xc, He + 0.3, He + 1.3, 2, holes, lw=0.45)
        op("window", xc)
    # ---- the face: rendered body + stepped gable, plinth, coping on every step, apex stack
    face = unary_union([box(0, -0.6, L, He), gpoly]).difference(unary_union(holes))
    slab2(P, face, -0.25, y, REND)
    # lined-out ashlar: horizontal joints every 0.55 m, staggered perpends every 1.1 m
    jt = []
    for i, z in enumerate(np.arange(0.4, Ha, 0.55)):
        jt.append(box(0, z - 0.012, L, z + 0.012))
        off = 0.55 if i % 2 else 0.0
        for x in np.arange(off, L, 1.1):
            jt.append(box(x - 0.012, z, x + 0.012, z + 0.55))
    jg = unary_union(jt).intersection(face.buffer(-0.08))
    P.slab(jg, y, y + 0.006, F.shade(REND, 0.88), sides=False)
    P.extrude_profile([(y, -0.6), (y + 0.16, -0.6), (y + 0.16, 0.45), (y, 0.6)], -0.05, L + 0.05, STONE)
    for i in range(k):
        z = He + rise * (i + 1)
        for xa, xb in ((i * run - 0.08, (i + 1) * run + 0.05), (L - (i + 1) * run - 0.05, L - i * run + 0.08)):
            box6(P, xa, xb, -0.3, y + 0.1, z, z + 0.16, STONE_L)
    # first step block under the coping (the shoulders) and the apex stack with a moulded cap and two pots
    box6(P, L / 2 - 0.42, L / 2 + 0.42, -0.4, y + 0.02, Ha, Ha + 1.1, REND)
    box6(P, L / 2 - 0.52, L / 2 + 0.52, -0.5, y + 0.12, Ha + 1.1, Ha + 1.28, STONE_L)
    for sx in (-0.2, 0.2):
        box6(P, L / 2 + sx - 0.1, L / 2 + sx + 0.1, -0.3, -0.1, Ha + 1.28, Ha + 1.62, F.rgb("#a5634a"), mat="brick")
    # gutter-level string at the eaves
    P.extrude_profile([(y, He - 0.15), (y + 0.16, He - 0.05), (y + 0.16, He + 0.05), (y, He + 0.1)], -0.05, L + 0.05,
                      STONE_L)
    it = frame_world(P, p0, d, "sidney:" + kind, z0=Z0)
    return [it] if it else []


def oriel(P, xc, z0, z1, w, holes, y, shield=False):
    """Canted oriel on a moulded corbel: front of 3 lights, canted sides of 1 light each, a parapet cap."""
    dp = 0.75
    # back opening hidden by the bay: just a recess in the face
    holes.append(box(xc - w / 2 - dp + 0.05, z0, xc + w / 2 + dp - 0.05, z1))
    yf = y + dp
    # front panel
    front = box(xc - w / 2, z0, xc + w / 2, z1 + 0.45)
    hf = []
    mullioned(P, xc, z0 + 0.45, z1 - 0.1, 3, hf, lw=(w - 0.6) / 3 - 0.12, y=yf, label=False)
    slab2(P, front.difference(unary_union(hf)), yf - 0.2, yf, STONE)
    # canted sides: quads from the wall face out to the front corners, with one light each
    for sx in (-1, 1):
        xa, xb = xc + sx * (w / 2 + dp), xc + sx * w / 2
        for (za, zb, col, mat) in ((z0, z0 + 0.45, STONE, "stone"), (z0 + 0.45, z1 - 0.1, GLASS, "glass"),
                                   (z1 - 0.1, z1 + 0.45, STONE, "stone")):
            P.quad((xa, y, za), (xb, yf, za), (xb, yf, zb), (xa, y, zb), (sx * dp, w * 0 + 1.0, 0), col, mat)
        P.quad((xa, y, z0 + 0.45 + 0.6), (xb, yf, z0 + 0.45 + 0.6), (xb, yf, z0 + 0.53 + 0.6),
               (xa, y, z0 + 0.53 + 0.6), (sx, 1, 0), STONE_L, "stone")
    # floor / cap plates
    trap = Polygon([(xc - w / 2 - dp, y), (xc + w / 2 + dp, y), (xc + w / 2, yf), (xc - w / 2, yf)])
    for zz, nz in ((z1 + 0.45, 1), (z0, -1)):
        for p in [trap]:
            T2 = F.earcut2d(p)
            if len(T2):
                P.add(np.stack([T2[..., 0], T2[..., 1], np.full(T2.shape[:2], zz)], -1), (0, 0, nz), STONE_L, "stone")
    # crenellated cap over the oriel
    for i in range(4):
        x0 = xc - w / 2 + 0.05 + i * (w - 0.1) / 4
        box6(P, x0 + 0.08, x0 + (w - 0.1) / 4 - 0.08, yf - 0.25, yf + 0.03, z1 + 0.45, z1 + 0.8, STONE)
    # corbel: three receding mouldings down to a point under the bay
    for j, (ww, za, zb) in enumerate(((w + 2 * dp - 0.2, z0 - 0.35, z0), (w * 0.8, z0 - 0.75, z0 - 0.35),
                                      (w * 0.45, z0 - 1.2, z0 - 0.75))):
        box6(P, xc - ww / 2, xc + ww / 2, y, y + dp * (1 - 0.3 * j), za, zb, STONE)
    if shield:   # the founder's arms on the corbel face (or, a bend engrailed azure; simplified colours)
        sh = Polygon([(xc - 0.28, z0 - 0.12), (xc + 0.28, z0 - 0.12), (xc + 0.28, z0 - 0.5), (xc, z0 - 0.72),
                      (xc - 0.28, z0 - 0.5)])
        P.slab(sh, y + dp + 0.0, y + dp + 0.05, OR, sides=False, mat="plain")
        P.slab(box(xc - 0.3, z0 - 0.45, xc + 0.3, z0 - 0.33).intersection(sh), y + dp + 0.05, y + dp + 0.07, AZURE,
               sides=False, mat="plain")


def make(spec):
    return lambda walls=None: gable(*spec)


BUILDS = {s[0]: make(s) for s in GABLES}
ELEMENTS = {}

if __name__ == "__main__":
    tot = 0
    for s in GABLES:
        for it in BUILDS[s[0]]([]):
            Tz = np.asarray(it["tris"])[..., 2]
            tot += len(it["tris"])
            print(it["name"], len(it["tris"]), round(float(Tz.min()), 2), round(float(Tz.max()), 2))
    print("total", tot)
