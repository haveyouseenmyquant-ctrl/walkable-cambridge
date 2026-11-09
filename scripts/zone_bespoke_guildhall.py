"""Bespoke facades for the Cambridge Guildhall (OSM way/5094872; C. Cowles-Voysey, 1937-39), session 31.

zone_build.load_bespoke() picks up BUILDS. Modelled from Wikimedia Commons photos (category "Cambridge Guildhall":
Cambridge Guildhall.jpg (PD), geograph 3901382/3901385/7017897/5400630/4332545/5711938/514416/5277623 (CC BY-SA 2.0)).

What the photos show (and what is built):
- buff-brown brick body, 4 storeys + attic; Portland-stone ground storey with channelled rustication and a moulded
  band at ~4.7 m;
- Market Square front (north): 9 bays = a 7-bay main block (OSM: 1.5 m proud) between recessed single end bays;
  tall first-floor windows with stone architraves and cornice hoods, standing on a long iron balcony carried along
  the main block; 2nd/3rd-floor windows with stone architraves; multi-pane dark metal windows;
- central entrance (THE GUILDHALL) in a stone surround with the coat of arms on the balcony above;
- big stone main cornice at ~16.5 m, brick attic storey with stone-framed balustraded panels over each bay, the clock
  in a stone frame at the centre, flagpole on the roof behind it;
- Peas Hill (west) and Guildhall Street (east) sides: same storeys / cornice / attic, plainer windows.
The OSM footprint has a ~7.6 m wide, 1.5 m deep central projection on the front (portal + balcony outline). The
landmark body in the tiles extrudes it full height, so it is modelled as a shallow full-height frontispiece to hide
that box. Everything sits >= SK proud of the OSM wall line so it covers the tile landmark model (its pilasters stand
0.3 m out; body top is ~20.7 m above ground).
"""
import math
import os
import sys

import numpy as np
from shapely.geometry import Polygon, box

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import facade_parts as F  # noqa: E402

OSM = "way/5094872"
Z0 = 9.50            # building datum (lowest ground along the front); horizontal courses are level from here
SK = 0.55            # skin plane, metres proud of the OSM wall line (covers the landmark body + its pilasters)
REV = 0.24           # window reveal depth
BRICK = F.rgb("#9e7c5c")   # s70: warmer brown brick (was #a08a66 khaki; judge: wall colour wrong)
BRICK_D = F.shade(BRICK, 0.78)
STONE = F.rgb("#d9cba6")
STONE_D = F.shade(STONE, 0.62)
FRAME = F.rgb("#3a3d3b")
GLASS = F.rgb(F.GLASS_COL)
RAIL = F.rgb("#3c4842")
DOOR = F.rgb("#26282a")

# storey heights above Z0 (from the near-frontal photos, bay spacing 4.7 m as scale)
Z_BASE_TOP = 4.55    # top of the rusticated stone storey
Z_BAND = (4.55, 4.85)
W1 = (5.05, 8.25)    # first-floor windows (sill on the balcony)
W2 = (9.45, 11.85)
W3 = (13.05, 15.05)
Z_CORN = 16.3        # main cornice (bottom); top at Z_CORN + 0.8
Z_ATTIC = 17.1
Z_TOP = 20.55        # attic coping bottom; top 20.9 (tile landmark body top is ~20.7)
GW = (1.15, 3.15)    # ground-floor windows


def P_():
    P = F.Parts(mat="brick", wall_col=BRICK)
    P.ops = []          # emitted openings (kind, x, y) in the wall frame, for ELEMENTS
    return P


_OPS = []               # world-xy openings of the last build()


# ------------------------------------------------------------------ elements (wall frame: x along, y out, z up)

def win(P, xc, w, z0, z1, y, cols=3, rows=3, arch=True, hood=False, sill=True, wall=BRICK):
    """Window opening at skin plane y: reveals, glass, metal frame + glazing bars, stone architrave/hood/sill.
    Returns the opening polygon (to cut from the skin)."""
    op = box(xc - w / 2, z0, xc + w / 2, z1)
    P.ops.append(("window", xc, y))
    yg = y - REV
    P.sides_xz(op, yg, y, F.shade(wall, 0.8), inward=True, mat="stone" if wall is STONE else "brick")
    P.face_xz(op, yg, GLASS, mat="glass")
    fw, bw = 0.07, 0.04
    inner = op.buffer(-fw, join_style=2)
    bx0, bz0, bx1, bz1 = inner.bounds
    bars = [box(bx0 + (bx1 - bx0) * i / cols - bw / 2, bz0, bx0 + (bx1 - bx0) * i / cols + bw / 2, bz1)
            for i in range(1, cols)]
    bars += [box(bx0, bz0 + (bz1 - bz0) * j / rows - bw / 2, bx1, bz0 + (bz1 - bz0) * j / rows + bw / 2)
             for j in range(1, rows)]
    from shapely.ops import unary_union
    P.slab(unary_union([op.difference(inner)] + bars), yg, yg + 0.04, FRAME, sides=False, mat="frame")
    if arch:   # stone architrave: flat band round the opening, slightly proud
        a = 0.2
        ring = box(xc - w / 2 - a, z0, xc + w / 2 + a, z1 + a).difference(op)
        P.slab(ring, y, y + 0.06, STONE, mat="stone")
    if sill:
        P.box(xc - w / 2 - 0.25, xc + w / 2 + 0.25, y, y + 0.12, z0 - 0.14, z0, STONE, mat="stone")
    if hood:   # flat cornice hood on the first-floor windows
        zt = z1 + (0.2 if arch else 0.0)
        P.extrude_profile([(y, zt), (y + 0.1, zt), (y + 0.1, zt + 0.12), (y + 0.24, zt + 0.2), (y + 0.24, zt + 0.3),
                           (y, zt + 0.3)], xc - w / 2 - 0.4, xc + w / 2 + 0.4, STONE, mat="stone")
    return op


def attic_panel(P, xc, y, w=1.5):
    """Balustraded panel in the attic: recess, stone frame, balusters."""
    z0, z1 = Z_ATTIC + 0.55, Z_ATTIC + 1.75
    op = box(xc - w / 2, z0, xc + w / 2, z1)
    P.sides_xz(op, y - 0.3, y, BRICK_D, inward=True, mat="brick")
    P.face_xz(op, y - 0.3, F.shade(GLASS, 1.3), mat="glass")
    P.slab(box(xc - w / 2 - 0.15, z0 - 0.15, xc + w / 2 + 0.15, z1 + 0.15).difference(op), y, y + 0.05, STONE,
           mat="stone")
    P.box(xc - w / 2, xc + w / 2, y - 0.3, y - 0.1, z0, z0 + 0.12, STONE, mat="stone")        # plinth
    P.box(xc - w / 2, xc + w / 2, y - 0.3, y - 0.1, z0 + 0.72, z0 + 0.84, STONE, mat="stone")  # rail
    n = 6
    for i in range(n):
        x = xc - w / 2 + w * (i + 0.5) / n
        P.box(x - 0.055, x + 0.055, y - 0.3, y - 0.12, z0 + 0.12, z0 + 0.72, STONE, top=False, bottom=False, mat="stone")
    return op


def section(P, x0, x1, y, bays, front=False, hoods=False, door_x=None, panels=True, attic=True, ret=None):
    """One flat stretch of facade at skin plane y from x0 to x1 with window bays at x in `bays`."""
    holes_b, holes_s, holes_a = [], [], []
    for x in bays:
        holes_b.append(win(P, x, 1.75 if front else 1.6, *W1, y, cols=3, rows=4, hood=hoods))
        holes_b.append(win(P, x, 1.6, *W2, y, cols=3, rows=3))
        holes_b.append(win(P, x, 1.6, *W3, y, cols=3, rows=3))
        if door_x is not None and abs(x - door_x) < 0.5:
            continue
        holes_s.append(win(P, x, 1.6, *GW, y + 0.1, cols=3, rows=3, arch=False, wall=STONE))
        if panels and attic:
            holes_a.append(attic_panel(P, x, y))
    # brick body (first floor up to the cornice) and attic
    from shapely.ops import unary_union
    body = box(x0, Z_BASE_TOP, x1, Z_ATTIC)
    if holes_b:
        body = body.difference(unary_union(holes_b))
    P.face_xz(body, y, BRICK, mat="brick")
    if attic:
        at = box(x0, Z_ATTIC, x1, Z_TOP)
        if holes_a:
            at = at.difference(unary_union(holes_a))
        P.face_xz(at, y, BRICK, mat="brick")
        # coping (projects 0.45 to hide the tile model's cornice ring) and roof cap back to the wall line
        P.extrude_profile([(y, Z_TOP), (y + 0.3, Z_TOP), (y + 0.3, Z_TOP + 0.12), (y + 0.42, Z_TOP + 0.22),
                           (y + 0.42, Z_TOP + 0.35), (y - SK - 0.3, Z_TOP + 0.35), (y - SK - 0.3, Z_TOP)],
                          x0 - 0.3, x1 + 0.3, STONE, mat="stone")
    # stone ground storey (proud by 0.1) with rustication channels
    ys = y + 0.1
    base = box(x0, -0.7, x1, Z_BASE_TOP)
    gd = None
    if door_x is not None:
        gd = box(door_x - 1.1, 0, door_x + 1.1, 3.6)
        holes_s.append(gd)
    if holes_s:
        base = base.difference(unary_union(holes_s))
    P.face_xz(base, ys, STONE, mat="stone")
    yr = y - SK if ret is None else ret            # returns run back to the neighbouring (recessed) skin plane
    for x in (x0, x1):
        nx = -1 if x == x0 else 1
        P.quad((x, yr, Z_BASE_TOP), (x, y, Z_BASE_TOP), (x, y, Z_TOP), (x, yr, Z_TOP), (nx, 0, 0), BRICK, mat="brick")
        P.quad((x, yr, -0.7), (x, ys, -0.7), (x, ys, Z_BASE_TOP), (x, yr, Z_BASE_TOP), (nx, 0, 0), STONE, mat="stone")
    zc = 0.6
    while zc < Z_BASE_TOP - 0.3:
        strip = box(x0, zc - 0.035, x1, zc + 0.035)
        if holes_s:
            strip = strip.difference(unary_union(holes_s).buffer(0.05))
        P.face_xz(strip, ys + 0.005, STONE_D, mat="stone")
        zc += 0.62
    # staggered vertical joints (blocks ~1.25 m long)
    from shapely.geometry import MultiPolygon
    k, zl = 0, 0.6
    hs = unary_union(holes_s).buffer(0.05) if holes_s else None
    while zl < Z_BASE_TOP - 0.3:
        zh = min(zl + 0.62, Z_BASE_TOP)
        xs = np.arange(x0 + (0.62 if k % 2 else 0.0) + 1.25, x1 - 0.2, 1.25)
        g = MultiPolygon([box(x - 0.02, zl, x + 0.02, zh) for x in xs])
        if hs is not None:
            g = g.difference(hs)
        P.face_xz(g, ys + 0.005, STONE_D, mat="stone")
        zl += 0.62
        k += 1
    P.box(x0, x1, y, ys + 0.12, -0.7, 0.35, F.shade(STONE, 0.9), top=True, bottom=False, mat="stone")   # plinth
    # moulded band at the top of the stone storey
    b0, b1 = Z_BAND
    P.extrude_profile([(y, b0), (ys + 0.05, b0), (ys + 0.05, b0 + 0.1), (ys + 0.2, b0 + 0.2), (ys + 0.2, b1),
                       (y, b1)], x0 - 0.2, x1 + 0.2, STONE, mat="stone")
    # main cornice: architrave band, frieze, dentils, corona
    z = Z_CORN
    P.extrude_profile([(y, z), (y + 0.08, z), (y + 0.08, z + 0.18), (y + 0.2, z + 0.3), (y + 0.24, z + 0.42),
                       (y + 0.7, z + 0.5), (y + 0.7, z + 0.68), (y + 0.8, z + 0.8), (y, z + 0.8)],
                      x0 - 0.75, x1 + 0.75, STONE, mat="stone")
    nd = int((x1 - x0) / 0.5)
    for i in range(nd):
        x = x0 + (x1 - x0) * (i + 0.5) / nd
        P.box(x - 0.1, x + 0.1, y + 0.2, y + 0.42, z + 0.3, z + 0.48, STONE_D, top=False, mat="stone")
    if door_x is not None:
        entrance(P, door_x, ys)


def entrance(P, xc, y):
    """Central doorway: deep stone surround, bronze doors, name panel; coat of arms above on the balcony."""
    w, h = 2.2, 3.6
    P.ops.append(("door", xc, y))
    P.sides_xz(box(xc - w / 2, 0, xc + w / 2, h), y - 0.5, y, STONE_D, inward=True, mat="stone")
    P.face_xz(box(xc - w / 2, 0, xc + w / 2, h), y - 0.5, DOOR, mat="frame")
    for i in range(2):   # door leaves with raised square panels
        lx = xc - w / 2 + 0.15 + i * (w / 2)
        for k in range(4):
            P.box(lx, lx + w / 2 - 0.3, y - 0.5, y - 0.46, 0.4 + k * 0.78, 0.4 + k * 0.78 + 0.6, F.shade(DOOR, 1.4),
                  mat="frame")
    ring = box(xc - w / 2 - 0.7, 0, xc + w / 2 + 0.7, h + 0.9).difference(box(xc - w / 2, 0, xc + w / 2, h))
    P.slab(ring, y, y + 0.22, F.shade(STONE, 1.04), mat="stone")
    P.box(xc - 0.9, xc + 0.9, y + 0.22, y + 0.25, h + 0.3, h + 0.6, F.shade(STONE_D, 0.6), mat="trim")  # lettering
    # coat of arms (shield + supporters' mass) on the balcony front
    yb = y + 1.15
    P.slab(Polygon([(xc - 0.45, 5.6), (xc + 0.45, 5.6), (xc + 0.45, 5.0), (xc, 4.6), (xc - 0.45, 5.0)]), yb - 0.1,
           yb + 0.08, F.rgb("#b8352e"), mat="trim")
    P.box(xc - 0.4, xc + 0.4, yb + 0.08, yb + 0.1, 5.25, 5.55, F.rgb("#d9b44a"), mat="trim")
    P.box(xc - 0.4, xc + 0.4, yb + 0.08, yb + 0.1, 4.95, 5.2, F.rgb("#3a5a9a"), mat="trim")
    for s in (-1, 1):
        P.box(xc + s * 0.55 - 0.18, xc + s * 0.55 + 0.18, yb - 0.1, yb + 0.06, 4.75, 5.75, F.rgb("#4f7a62"), mat="trim")


def balcony(P, x0, x1, y, depth=1.05):
    """First-floor balcony: stone slab on consoles, iron railing (rails + bars)."""
    z = Z_BAND[1]
    yf = y + depth
    P.box(x0, x1, y, yf, z - 0.22, z, STONE, mat="stone")
    nc = max(2, int((x1 - x0) / 1.6))
    for i in range(nc + 1):
        x = x0 + 0.15 + (x1 - x0 - 0.3) * i / nc
        P.box(x - 0.1, x + 0.1, y, yf - 0.15, z - 0.6, z - 0.22, STONE_D, top=False, mat="stone")   # console
    zr = z + 1.0
    for (a, b) in ((x0, x1),):   # one run
        P.box(a, b, yf - 0.08, yf - 0.02, zr, zr + 0.06, RAIL, mat="frame")             # top rail
        P.box(a, b, yf - 0.08, yf - 0.02, z + 0.1, z + 0.15, RAIL, mat="frame")         # bottom rail
        P.box(a, b, yf - 0.07, yf - 0.03, z + 0.75, z + 0.8, RAIL, mat="frame")
        nb = int((b - a) / 0.14)
        for i in range(nb + 1):
            x = a + (b - a) * i / nb
            P.box(x - 0.012, x + 0.012, yf - 0.07, yf - 0.03, z, zr, RAIL, top=False, bottom=False, mat="frame")
    for x in (x0, x1):   # end returns of the railing
        P.quad((x, y, zr), (x, yf - 0.02, zr), (x, yf - 0.02, zr + 0.06), (x, y, zr + 0.06), (1, 0, 0), RAIL, mat="frame")
        for k in range(1, 7):
            yy = y + (yf - y) * k / 7
            P.box(x - 0.012, x + 0.012, yy - 0.02, yy + 0.02, z, zr, RAIL, top=False, bottom=False, mat="frame")


def clock(P, xc, y):
    """Clock on the attic at the centre: stone frame with scrolls, white dial, hands."""
    zc, r = Z_ATTIC + 1.65, 0.85
    P.slab(box(xc - 1.35, Z_ATTIC + 0.1, xc + 1.35, Z_TOP + 0.2), y, y + 0.12, STONE, mat="stone")
    a = np.linspace(0, 2 * math.pi, 25)[:-1]
    ring = Polygon(np.c_[xc + (r + 0.18) * np.cos(a), zc + (r + 0.18) * np.sin(a)])
    dial = Polygon(np.c_[xc + r * np.cos(a), zc + r * np.sin(a)])
    P.slab(ring.difference(dial), y + 0.12, y + 0.28, F.rgb("#b59a52"), mat="trim")
    P.slab(dial, y + 0.12, y + 0.18, F.rgb("#ece6d2"), sides=False, mat="trim")
    for ang, ln in ((math.radians(60), 0.5), (math.radians(-80), 0.72)):
        c, s = math.cos(ang), math.sin(ang)
        hand = Polygon([(xc - 0.03 * s, zc + 0.03 * c), (xc + ln * c, zc + ln * s), (xc + 0.03 * s, zc - 0.03 * c)])
        P.slab(hand, y + 0.18, y + 0.21, F.rgb("#1c1c1c"), sides=False, mat="trim")


# ------------------------------------------------------------------ frames -> world

def frame_of(p0, p1):
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    L = float(np.linalg.norm(p1 - p0))
    return p0, (p1 - p0) / L, L


def to_world(P, p0, d, name):
    n = np.array([d[1], -d[0]])
    for k, x, y in getattr(P, "ops", []):
        _OPS.append((k, *(p0 + x * d + y * n)))
    T, N, C = P.arrays()
    if not len(T):
        return None
    M = P.mats()
    X = p0[0] + T[..., 0] * d[0] + T[..., 1] * n[0]
    Y = p0[1] + T[..., 0] * d[1] + T[..., 1] * n[1]
    W = np.stack([X, Y, Z0 + T[..., 2]], -1)
    Nw = np.stack([N[:, 0] * d[0] + N[:, 1] * n[0], N[:, 0] * d[1] + N[:, 1] * n[1], N[:, 2]], -1)
    g = np.cross(W[:, 1] - W[:, 0], W[:, 2] - W[:, 0])
    flip = (g * Nw).sum(1) < 0
    W[flip] = W[flip][:, ::-1]
    return {"name": name, "tris": W, "col": np.clip(C, 0, 1), "mat": M}


def build_front(walls):
    """Market Square front in one frame: x from the NE corner (OSM node 10) to the NW corner (node 24)."""
    p0, d, L = frame_of((-64.52, 26.16), (-108.12, 20.85))
    by = {w["id"]: w for w in walls}
    if "way/5094872:12" in by:   # use the zone wall list when present (same OSM nodes)
        p0, d, L = frame_of(by["way/5094872:10"]["p0"], by["way/5094872:23"]["p1"])
    P = P_()
    yE, yM, yC = SK, 1.52 + SK, 3.02 + SK          # end bays / main block / central frontispiece skin planes
    xa, xb = 5.12, L - 5.55                        # main block extent (OSM nodes 11/12 and 22/23)
    xc0, xc1 = 18.2, 25.8                          # central projection (nodes 13-14 .. 20-21)
    mid = (xc0 + xc1) / 2
    bay = (xb - xa) / 7
    bays = [xa + bay * (i + 0.5) for i in range(7)]
    # end bays (recessed): one window column each, no hoods
    section(P, -SK, xa, yE, [(xa - SK) / 2 + 0.1], front=False)
    section(P, xb, L + SK, yE, [(xb + L) / 2], front=False)
    # main block either side of the frontispiece
    section(P, xa, xc0, yM, [b for b in bays if b < xc0 - 0.5], front=True, hoods=True, ret=yE - 0.05)
    section(P, xc1, xb, yM, [b for b in bays if b > xc1 + 0.5], front=True, hoods=True, ret=yE - 0.05)
    # frontispiece: centre bay with the entrance, clock above
    section(P, xc0, xc1, yC, [mid], front=True, hoods=True, door_x=mid, panels=False, ret=yM - 0.05)
    clock(P, mid, yC)
    # balcony along the main block, stepping round the frontispiece
    balcony(P, xa + 0.15, xc0, yM)
    balcony(P, xc1, xb - 0.15, yM)
    balcony(P, xc0 - 0.0, xc1, yC, depth=1.05)
    # flagpole on the roof behind the clock
    fx, fy = mid, yM - 4.0
    P.box(fx - 0.07, fx + 0.07, fy - 0.07, fy + 0.07, Z_TOP + 0.35, Z_TOP + 8.5, F.rgb("#e4e4e0"), mat="trim")
    P.box(fx - 0.2, fx + 0.2, fy - 0.2, fy + 0.2, Z_TOP + 0.35, Z_TOP + 0.8, STONE_D, mat="stone")
    P.box(fx + 0.07, fx + 1.5, fy - 0.01, fy + 0.01, Z_TOP + 7.4, Z_TOP + 8.3, F.rgb("#3b7fc4"), mat="trim")
    return to_world(P, p0, d, "guildhall:front")


def build_side(w, nb=None, name="side"):
    p0, d, L = frame_of(w["p0"], w["p1"])
    P = P_()
    if nb is None:
        nb = int(L // 3.9)
    bays = [L * (i + 0.5) / nb for i in range(nb)] if nb else []
    section(P, -SK, L + SK, SK, bays, front=False)
    return to_world(P, p0, d, "guildhall:" + name)


def build(walls):
    _OPS.clear()
    out = []
    ids = {w["id"]: w for w in walls}
    out.append(build_front(walls))
    for wid, nb in (("way/5094872:24", 12), ("way/5094872:9", 4), ("way/5094872:8", 7), ("way/5094872:26", 2),
                    ("way/5094872:25", 0), ("way/5094872:7", 0)):
        if wid in ids:
            out.append(build_side(ids[wid], nb, wid.split(":")[1]))
    ELEMENTS.update(F.count_on_walls(_OPS, walls))
    return [o for o in out if o is not None]


ELEMENTS = {}   # wall id -> opening counts actually emitted (filled by build(); zone_build reads it for the KPI)
BUILDS = {OSM: build}


def _count_elements():
    import json
    try:
        W = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                                        "data/annotations/market_square/walls.json")))["walls"]
        build([w for w in W if w["osm_id"] == OSM])
    except Exception as e:   # never break the zone build
        print("zone_bespoke_guildhall: element count failed", repr(e), file=sys.stderr)


_count_elements()

if __name__ == "__main__":
    import json
    W = json.load(open(os.path.join(os.path.dirname(__file__), "..", "data/annotations/market_square/walls.json")))["walls"]
    items = build([w for w in W if w["osm_id"] == OSM])
    for it in items:
        print(it["name"], len(it["tris"]))
    print("total", sum(len(i["tris"]) for i in items))
