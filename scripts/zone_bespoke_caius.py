"""Bespoke geometry for the Gonville & Caius College buildings in the Market Square zone (session 34).

zone_build.load_bespoke() picks up BUILDS. Every wall is built in its own wall frame (x along p0 -> p1, y out of the
building = right of p0 -> p1, z up from the wall's ground_z) and mapped to world collision-frame triangles like
zone_build.to_collision. The tile bodies stay visible (no HIDE_TILE: none of these models is a closed exterior; the
walls.json list only has the street-facing walls), so every wall face sits SK = 0.42 m proud of the OSM wall line and
the glass of each opening at >= 0.08 m (in front of the tile wall).

What the ways are (from the references below):
- way/13864058 (walls :26 Senate House Passage return, :27 corner splay, :28 Trinity Street): Alfred Waterhouse's
  range of 1868-70 (Tree Court, Trinity St / Senate House Passage corner). Honey-coloured Ancaster-type ashlar,
  high plinth with basement grilles, three storeys of stone cross windows (mullion + transom) under square hood
  moulds, string courses, corbel-table cornice with gargoyles and a pierced parapet, steep slate roof with stone
  gabled dormers; a corbelled two-storey oriel on the corner splay; the gate tower on Senate House Passage
  (square, battlemented, with a round corner turret and conical cap), placed from the DSM.
  Heights (above ground 9.7 m): parapet 12.9 (DSM at 0.5-1.5 m inside 21.6-22.9 m, i.e. 12-13 m), roof flat/ridge
  16.4 (DSM 26.0-26.1), tower parapet 23.3 / pyramid 28.0 / turret cap 26.5 (DSM 30-38, peak 38.0 = 28.3).
- way/13864148 (:7-:13): the curved 1930s Portland-stone block on Market Hill / St Mary's Street (Caius
  property, shops): recessed ground-floor shop arcade on square piers, four storeys of white multi-pane metal
  casements, carved panels between the windows on the curved corner, iron balconettes on the curved first floor,
  parapet. Flat roof 15.7 m (DSM 24.8-24.9 over ground 9.1-9.2); the curved SE corner carries a set-back attic to
  18.2 m (DSM 27.3-27.7). The north end of :13 is a one-storey (4.2 m, DSM 13.3-13.4) front with the upper storeys
  set back ~3 m; the set-back part is left to the tile body.
- way/137017433 (:4 Market Hill west side, north of 13864148): the same Portland-stone arcade + three storeys
  (parapet 10.8 m, DSM 19.3-20.6 at 0.5 m inside over ground 9.5; flat roof 12.6, DSM 22.0-22.1). Listed building
  1125528 "North and East ranges of St Michael's Court" covers the Rose Crescent side; :0/:1/:2/:21/:22 are
  courtyard/rear walls without references: plain stone with a regular window grid.
- way/137017435 (:4/:5/:7/:8): low single-storey (3.7 m, DSM 13.1-13.3 over 9.5) ashlar block beside St Michael's
  passage: plinth, plain ashlar, moulded coping. :2/:3 have no height and get nothing.
Not modelled here (left to their annotations / generic skins): way/137017428 and way/137017430 are Caius-owned
townhouses (1-6 Trinity Street, 27-28 Market Hill) with medium/high-confidence annotations, and their street walls
duplicate way/1099847936 / 1099847940 (zone_build.duplicate_walls keeps the addressed ways).

Sources (all used for layout/colour only; nothing pasted as texture), in data/raw/commons_ref/:
- "Cambridge - Trinity Street - View SSW along Gonville & Caius College 1876 by Alfred Waterhouse.jpg",
  "Cambridge - King's Parade - View West into Senate House Passage - On the Right- Gonville & Caius College 1876 by
  Alfred Waterhouse.jpg", "Cambridge - King's Parade - View North into Trinity Street - On the Left- Gonville & Caius
  College 1876 by Alfred Waterhouse.jpg", "Cambridge - Market Hill - View NNW into Rose Crescent.jpg":
  Wikimedia Commons, user Txllxt TxllxT, CC BY-SA 4.0.
- "1125528 II GONVILLE AND CAIUS COLLEGE, NORTH AND EAST RANGES OF ST MICHAELS COURT Cambridge 20260523 000x.jpg":
  Wikimedia Commons, user Tilman2007, CC BY-SA 4.0.
- Mapillary (CC BY-SA 4.0) references already in walls.json: 150365460382983, 138292341951529 (Market Hill block),
  3304474719779190.
Heights: data/lidar/nlp2023_first_return_dsm_1m.tif sampled 0.5-11 m inside each wall, dtm_1m.tif outside.
"""
import math
import os
import sys

import numpy as np
from shapely.geometry import Point, Polygon, box
from shapely.ops import unary_union

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import facade_parts as F  # noqa: E402

SK = 0.42                       # wall face, metres proud of the OSM wall line
YG = 0.08                       # glass plane
GLASS = F.rgb(F.GLASS_COL)
# Waterhouse range: warm honey ashlar (weathered), darker reveals, slate roof
WH = F.rgb("#b89d72")
WH_D = F.shade(WH, 0.7)
WH_L = F.shade(WH, 1.08)
SLATE = F.rgb("#4f5157")
LEAD = F.rgb("#7d8286")
FRAME_W = F.rgb("#ece9e2")
# 1930s block: Portland stone
PS = F.rgb("#d8d1c0")
PS_D = F.shade(PS, 0.72)
PS_L = F.shade(PS, 1.05)
SOFFIT = F.rgb("#8d887e")
SHOP = F.rgb("#3a3c3e")
RAIL = F.rgb("#2a2b2c")
# low block
LB = F.rgb("#cbbd9c")


def P_(col):
    return F.Parts(mat="stone", wall_col=col)


# ------------------------------------------------------------------ frames

def frame_world(P, p0, d, name, z0):
    T, N, C = P.arrays()
    if not len(T):
        return None
    M = P.mats()
    n = np.array([d[1], -d[0]])
    X = p0[0] + T[..., 0] * d[0] + T[..., 1] * n[0]
    Y = p0[1] + T[..., 0] * d[1] + T[..., 1] * n[1]
    W = np.stack([X, Y, z0 + T[..., 2]], -1)
    Nw = np.stack([N[:, 0] * d[0] + N[:, 1] * n[0], N[:, 0] * d[1] + N[:, 1] * n[1], N[:, 2]], -1)
    g = np.cross(W[:, 1] - W[:, 0], W[:, 2] - W[:, 0])
    flip = (g * Nw).sum(1) < 0
    W[flip] = W[flip][:, ::-1]
    return {"name": name, "tris": W, "col": np.clip(C, 0, 1), "mat": M}


ELEMENTS = {}   # wall id -> opening counts actually emitted (filled by build(); see _count_elements)


def on_wall(P, w, name):
    c = {k: int(P.counts.get(k, 0)) for k in ("window", "door", "shopfront", "dormer")}
    ELEMENTS[w["id"]] = c
    p0 = np.asarray(w["p0"], float)
    d = (np.asarray(w["p1"], float) - p0) / w["length"]
    return frame_world(P, p0, d, name, w["ground_z"])


def extents(walls, sk=SK):
    """Like zone_build.corner_extents with our skin depth: extend at convex corners, shorten at concave ones."""
    ext = {w["id"]: [0.0, w["length"]] for w in walls}
    starts = {tuple(np.round(w["p0"], 1)): w for w in walls}
    for a in walls:
        b = starts.get(tuple(np.round(a["p1"], 1)))
        if b is None or b is a:
            continue
        da = np.subtract(a["p1"], a["p0"]) / a["length"]
        db = np.subtract(b["p1"], b["p0"]) / b["length"]
        cr = da[0] * db[1] - da[1] * db[0]
        if abs(cr) < 0.2:
            continue
        ang = math.atan2(abs(cr), float(da @ db))
        dd = sk * math.tan(ang / 2) * (1 if cr > 0 else -1)
        ext[a["id"]][1] += dd
        ext[b["id"]][0] -= dd
    return ext


# ------------------------------------------------------------------ elements (wall frame)

def grid_bars(op, cols, rows, bw, zsplit=None):
    x0, z0, x1, z1 = op.bounds
    parts = [op.difference(op.buffer(-bw, join_style=2))]
    for i in range(1, cols):
        x = x0 + (x1 - x0) * i / cols
        parts.append(box(x - bw / 2, z0, x + bw / 2, z1))
    zs = [z0 + (z1 - z0) * j / rows for j in range(1, rows)] if zsplit is None else zsplit
    for z in zs:
        parts.append(box(x0, z - bw / 2, x1, z + bw / 2))
    return unary_union(parts).intersection(op)


def cross_window(P, xc, w, zb, zt, col, col_d, col_l, hood=True, lights=2, y=SK):
    """Stone mullion-and-transom window: reveal, glass, stone mullion(s)/transom, leaded white casement frames,
    chamfered sill, square hood mould with returns. Returns the opening."""
    op = box(xc - w / 2, zb, xc + w / 2, zt)
    P.count("window")
    P.sides_xz(op, YG, y, col_d, inward=True, mat="stone")
    P.face_xz(op, YG, GLASS, mat="glass")
    zt_ = zb + (zt - zb) * 0.68
    stone = unary_union([box(xc - w / 2 + w * i / lights - 0.07, zb, xc - w / 2 + w * i / lights + 0.07, zt)
                         for i in range(1, lights)] + [box(xc - w / 2, zt_ - 0.07, xc + w / 2, zt_ + 0.07)])
    P.slab(stone, YG, YG + 0.2, col_l, mat="stone")
    fr = []
    for i in range(lights):
        a = xc - w / 2 + w * i / lights
        for (q0, q1) in ((zb, zt_ - 0.07), (zt_ + 0.07, zt)):
            cell = box(a + (0.07 if i else 0), q0, a + w / lights - (0.07 if i < lights - 1 else 0), q1)
            fr.append(cell.difference(cell.buffer(-0.05, join_style=2)))
    P.slab(unary_union(fr), YG, YG + 0.04, FRAME_W, mat="frame")
    P.extrude_profile([(y - 0.02, zb - 0.16), (y + 0.12, zb - 0.16), (y + 0.12, zb - 0.06), (y - 0.02, zb + 0.03)],
                      xc - w / 2 - 0.1, xc + w / 2 + 0.1, col_l, mat="stone")
    if hood:
        ring = box(xc - w / 2 - 0.2, zt, xc + w / 2 + 0.2, zt + 0.16).union(
            box(xc - w / 2 - 0.2, zt - 0.45, xc - w / 2 - 0.06, zt)).union(
            box(xc + w / 2 + 0.06, zt - 0.45, xc + w / 2 + 0.2, zt))
        P.slab(ring, y, y + 0.12, col_l, mat="stone")
    return op


def casement(P, xc, w, zb, zt, col_d, col_l, cols=3, rows=4, y=SK, sill=True):
    """1930s metal casement window: shallow reveal, white frames with small panes, stone sill."""
    op = box(xc - w / 2, zb, xc + w / 2, zt)
    yg = YG if y >= SK - 1e-6 else y - 0.3
    P.count("window")
    P.sides_xz(op, yg, y, col_d, inward=True, mat="stone")
    P.face_xz(op, yg, GLASS, mat="glass")
    big = grid_bars(op, cols, 1, 0.07)
    small = grid_bars(op, cols * 2, rows, 0.025)
    P.slab(big, yg, yg + 0.06, FRAME_W, mat="frame")
    P.face_xz(small, yg + 0.035, FRAME_W, mat="frame")   # thin glazing bars: front face only
    if sill:
        P.box(xc - w / 2 - 0.08, xc + w / 2 + 0.08, y - 0.02, y + 0.1, zb - 0.1, zb, col_l, mat="stone")
    return op


def wall_face(P, x0, x1, z1, holes, col, y=SK, z0=-0.6):
    g = box(x0, z0, x1, z1)
    if holes:
        g = g.difference(unary_union(holes))
    P.face_xz(g, y, col, mat="stone")


def band(P, x0, x1, z, h, d, col, y=SK):
    P.extrude_profile([(y - 0.02, z), (y + d * 0.6, z), (y + d, z + h * 0.4), (y + d, z + h), (y - 0.02, z + h)],
                      x0, x1, col, mat="stone")


def pierced_parapet(P, x0, x1, z0, z1, col, col_d, y=SK):
    """Parapet with a row of quatrefoil piercings (dark recesses) and a coping."""
    L = x1 - x0
    n = max(1, int(L / 0.75))
    holes = []
    zc = (z0 + z1) / 2 - 0.03
    for k in range(n):
        xc = x0 + L * (k + 0.5) / n
        r = min(0.16, (z1 - z0) * 0.28)
        holes.append(unary_union([Point(xc + dx, zc + dz).buffer(r * 0.55, resolution=3)
                                  for dx, dz in ((r * 0.5, 0), (-r * 0.5, 0), (0, r * 0.5), (0, -r * 0.5))]))
    hu = unary_union(holes)
    P.face_xz(box(x0, z0, x1, z1).difference(hu), y + 0.05, col, mat="stone")
    P.face_xz(hu, y - 0.12, col_d, mat="stone")
    P.sides_xz(hu, y - 0.12, y + 0.05, col_d, inward=True, mat="stone")
    P.box(x0, x1, y - 0.3, y + 0.05, z0, z1, col, mat="stone", bottom=False, top=False)
    P.extrude_profile([(y - 0.35, z1), (y + 0.15, z1), (y + 0.15, z1 + 0.08), (y - 0.1, z1 + 0.18),
                       (y - 0.35, z1 + 0.18)], x0, x1, col, mat="stone")


def corbel_table(P, x0, x1, z, col, y=SK):
    band(P, x0, x1, z + 0.28, 0.22, 0.3, col, y)
    n = max(1, int((x1 - x0) / 0.5))
    for k in range(n):
        xc = x0 + (x1 - x0) * (k + 0.5) / n
        P.extrude_profile([(y - 0.02, z), (y + 0.05, z), (y + 0.2, z + 0.28), (y - 0.02, z + 0.28)],
                          xc - 0.1, xc + 0.1, col, mat="stone")


def gargoyle(P, x, z, col):
    P.box(x - 0.12, x + 0.12, SK, SK + 0.75, z - 0.15, z + 0.12, col, mat="stone")
    P.box(x - 0.16, x + 0.16, SK + 0.55, SK + 0.85, z - 0.25, z + 0.16, col, mat="stone")


def slope_roof(P, x0, x1, ye, ze, yr, zr, col, flat_to=None, mat="plain"):
    """Roof plane from the eaves line (y=ye, z=ze) up and back to (yr, zr); optional flat top back to flat_to."""
    P.quad((x0, ye, ze), (x1, ye, ze), (x1, yr, zr), (x0, yr, zr), (0, ye - yr, zr - ze), col, mat)
    if flat_to is not None:
        P.quad((x0, yr, zr), (x1, yr, zr), (x1, flat_to, zr), (x0, flat_to, zr), (0, 0, 1), LEAD, mat)


def dormer(P, xc, w, zb, col, col_d, col_l, y=SK - 0.9):
    """Stone gabled dormer standing on the roof slope behind the parapet: 2-light cross window, coped gable, finial,
    slate cheeks/roof back to the ridge."""
    zs, zp = zb + 2.3, zb + 3.3
    hw = w / 2
    face = Polygon([(xc - hw, zb), (xc + hw, zb), (xc + hw, zs), (xc, zp), (xc - hw, zs)])
    op = box(xc - 0.55, zb + 0.35, xc + 0.55, zs - 0.15)
    P.count("dormer")
    P.face_xz(face.difference(op), y, col, mat="stone")
    P.sides_xz(op, y - 0.3, y, col_d, inward=True, mat="stone")
    P.face_xz(op, y - 0.3, GLASS, mat="glass")
    P.slab(box(xc - 0.05, op.bounds[1], xc + 0.05, op.bounds[3]), y - 0.3, y - 0.12, col_l, mat="stone")
    # coping on the gable
    for s in (-1, 1):
        a, b = (xc + s * (hw + 0.1), zs - 0.05), (xc, zp + 0.12)
        P.slab(Polygon([a, b, (b[0], b[1] + 0.22), (a[0], a[1] + 0.22)]).buffer(0), y - 0.05, y + 0.12, col_l,
               mat="stone")
    P.box(xc - 0.1, xc + 0.1, y - 0.1, y + 0.1, zp + 0.3, zp + 0.85, col_l, mat="stone")
    # cheeks and roof back 2.6 m
    yb = y - 2.6
    for s in (-1, 1):
        x = xc + s * hw
        P.quad((x, yb, zb), (x, y, zb), (x, y, zs), (x, yb, zs), (s, 0, 0), col, "stone")
        P.quad((x + s * 0.1, y, zs - 0.05), (xc, y, zp + 0.1), (xc, yb, zp + 0.1), (x + s * 0.1, yb, zs - 0.05),
               (s * (zp - zs), 0, hw), SLATE, "plain")


# ------------------------------------------------------------------ way/13864058: Waterhouse range

WZ = dict(gr0=1.7, gr1=4.0, s1=4.6, f10=5.3, f11=7.7, s2=8.3, f20=8.9, f21=11.0, cor=11.85, par0=12.35, par1=12.95,
          eave=12.6, ridge=16.4)


def waterhouse_wall(w, x0, x1, kind):
    P = P_(WH)
    z = WZ
    holes = []
    L = w["length"]
    if kind in ("trinity", "passage"):
        nb = 4 if kind == "trinity" else 3
        xs = [L * (i + 0.5) / nb for i in range(nb)]
        for xc in xs:
            holes.append(cross_window(P, xc, 1.55, z["gr0"], z["gr1"], WH, WH_D, WH_L))
            holes.append(cross_window(P, xc, 1.55, z["f10"], z["f11"], WH, WH_D, WH_L))
            holes.append(cross_window(P, xc, 1.4, z["f20"], z["f21"], WH, WH_D, WH_L, hood=False))
            for gx in (xc - 0.45, xc + 0.45):   # basement grilles in the plinth
                g = box(gx - 0.25, 0.25, gx + 0.25, 0.95)
                holes.append(g)
                P.sides_xz(g, YG, SK + 0.2, WH_D, inward=True, mat="stone")
                P.face_xz(g, YG, F.rgb("#1d1d1d"), mat="trim")
                P.slab(grid_bars(g, 5, 1, 0.04), YG, YG + 0.05, RAIL, mat="trim")
    elif kind == "splay":
        xc = L / 2
        holes.append(cross_window(P, xc, 1.0, z["gr0"], z["gr1"], WH, WH_D, WH_L, lights=1))
    else:   # short return on Senate House Passage
        xc = L / 2
        for (a, b) in ((z["gr0"], z["gr1"]), (z["f10"], z["f11"]), (z["f20"], z["f21"])):
            holes.append(cross_window(P, xc, 0.8, a, b, WH, WH_D, WH_L, lights=1, hood=False))
    plinth = box(x0, -0.6, x1, 1.15)
    hp = [h for h in holes if h.bounds[3] < 1.2]
    wall_face(P, x0, x1, z["par0"], holes, WH)
    # plinth projecting 0.15 with a chamfered top
    g = plinth.difference(unary_union(hp)) if hp else plinth
    P.face_xz(g, SK + 0.15, WH_D if False else F.shade(WH, 0.9), mat="stone")
    P.extrude_profile([(SK - 0.02, 1.15), (SK + 0.15, 1.15), (SK + 0.15, 1.15), (SK - 0.02, 1.32)], x0, x1, WH_L,
                      mat="stone")
    band(P, x0, x1, z["s1"], 0.22, 0.14, WH_L)
    band(P, x0, x1, z["s2"], 0.22, 0.14, WH_L)
    corbel_table(P, x0, x1, z["cor"], WH_L)
    pierced_parapet(P, x0, x1, z["par0"] + 0.2, z["par1"], WH_L, WH_D)
    slope_roof(P, x0, x1, SK - 0.35, z["eave"] + 0.1, -3.4, z["ridge"], SLATE, flat_to=-6.0)
    if kind == "trinity":
        for xg in (0.6, L / 2, L - 0.6):
            gargoyle(P, xg, z["cor"] + 0.1, WH_L)
        for xc in (L * 1.5 / 4, L * 3.5 / 4):
            dormer(P, xc, 2.0, z["eave"] + 0.1, WH, WH_D, WH_L)
    if kind == "passage":
        for xg in (0.6, L - 0.6):
            gargoyle(P, xg, z["cor"] + 0.1, WH_L)
        for xc in (L / 6, L * 5 / 6):
            dormer(P, xc, 2.0, z["eave"] + 0.1, WH, WH_D, WH_L)
    if kind == "splay":
        oriel(P, L / 2, min(2.6, L - 0.1))
    return P


def oriel(P, xc, w):
    """Corbelled two-storey corner oriel (1st + 2nd floor): stepped corbel, carved frieze, 2-light cross windows on
    the front and single lights on the canted sides, pierced parapet."""
    z = WZ
    d = 0.85
    zb, zt = z["s1"] - 0.1, z["f21"] + 0.55
    y0, y1 = SK, SK + d
    hw = w / 2
    # corbel: stacked receding courses
    for k in range(4):
        zz = zb - 0.28 * (k + 1)
        P.box(xc - hw + 0.18 * k, xc + hw - 0.18 * k, y0, y1 - 0.2 * k, zz, zz + 0.28, F.shade(WH, 1.0 - 0.03 * k),
              mat="stone")
    holes = []
    for (a, b) in ((z["f10"], z["f11"]), (z["f20"], z["f21"])):
        op = box(xc - hw + 0.35, a, xc + hw - 0.35, b)
        P.count("window")
        holes.append(op)
        P.sides_xz(op, y1 - 0.25, y1, WH_D, inward=True, mat="stone")
        P.face_xz(op, y1 - 0.25, GLASS, mat="glass")
        zt_ = a + (b - a) * 0.66
        P.slab(unary_union([box(xc - 0.06, a, xc + 0.06, b), box(op.bounds[0], zt_ - 0.06, op.bounds[2], zt_ + 0.06)]),
               y1 - 0.25, y1 - 0.08, WH_L, mat="stone")
        P.slab(grid_bars(op, 2, 1, 0.05, zsplit=[zt_]), y1 - 0.25, y1 - 0.21, FRAME_W, mat="frame")
        # carved panel band below each window
        for k in range(3):
            px = xc - hw + 0.45 + (w - 0.9) * (k + 0.5) / 3
            P.slab(box(px - 0.3, a - 0.62, px + 0.3, a - 0.22), y1, y1 + 0.06, WH_L, mat="stone")
    P.face_xz(box(xc - hw, zb, xc + hw, zt).difference(unary_union(holes)), y1, WH, mat="stone")
    for s in (-1, 1):   # sides with narrow lights
        x = xc + s * hw
        P.quad((x, y0, zb), (x, y1, zb), (x, y1, zt), (x, y0, zt), (s, 0, 0), WH, "stone")
        for (a, b) in ((z["f10"], z["f11"]), (z["f20"], z["f21"])):
            P.quad((x + s * 0.01, y0 + 0.2, a), (x + s * 0.01, y1 - 0.2, a), (x + s * 0.01, y1 - 0.2, b),
                   (x + s * 0.01, y0 + 0.2, b), (s, 0, 0), GLASS, "glass")
    band(P, xc - hw - 0.05, xc + hw + 0.05, z["s2"], 0.2, 0.12, WH_L, y=y1)
    P.box(xc - hw - 0.08, xc + hw + 0.08, y0, y1 + 0.12, zt - 0.2, zt, WH_L, mat="stone")
    pierced_parapet(P, xc - hw, xc + hw, zt, zt + 0.6, WH_L, WH_D, y=y1 - 0.05)


# Gate tower on Senate House Passage (DSM cells > 29 m: E -190..-185, N 95..101), axis-aligned box
TOWER = (-190.6, -184.4, 94.1, 101.2)
TOWER_Z0 = 9.7
TW = dict(top=23.3, merlon=0.7, roof=28.0, turret_r=1.05, turret_top=24.6, cone=26.6)


def tower_face(L, full, door=False):
    P = P_(WH)
    zlo = 0.0 if full else 12.2
    holes = []
    xc = L / 2
    levels = [(5.3, 7.7), (8.9, 11.0), (13.2, 15.6), (16.8, 19.2), (20.2, 22.2)]
    for (a, b) in levels:
        if a < zlo + 0.5:
            continue
        holes.append(cross_window(P, xc, 1.5 if b < 20 else 1.2, a, b, WH, WH_D, WH_L))
    if door:
        r = 1.35
        op = Polygon([(xc - r, 0), (xc + r, 0)] + [(xc + r * math.cos(t), 2.6 + r * math.sin(t))
                                                  for t in np.linspace(0, math.pi, 13)])
        holes.append(op)
        # leaf 0.12 m behind the face: the OSM line runs up to 0.2 m south of TOWER's y0, so a leaf at YG sat
        # behind the tile body's wall and the arch showed its grey texture (session 58)
        P.sides_xz(op, SK - 0.12, SK + 0.3, WH_D, inward=True, skip_ground=True, mat="stone")
        P.face_xz(op, SK - 0.12, F.rgb("#3b2a20"), mat="timber")
        for k in range(3):
            ring = op.buffer(0.13 * (k + 1)).difference(op.buffer(0.13 * k)).intersection(box(-50, 0, 50, 50))
            P.slab(ring, SK, SK + 0.3 - 0.1 * k, WH_L, mat="stone")
        # statue niches either side above the arch
        for s in (-1, 1):
            nx = xc + s * 2.0
            nich = box(nx - 0.4, 4.6, nx + 0.4, 6.6)
            holes.append(nich)
            P.sides_xz(nich, SK - 0.3, SK, WH_D, inward=True, mat="stone")
            P.face_xz(nich, SK - 0.3, WH_D, mat="stone")
            P.box(nx - 0.2, nx + 0.2, SK - 0.3, SK - 0.05, 4.6, 6.2, WH_L, mat="stone")   # figure
            P.box(nx - 0.5, nx + 0.5, SK, SK + 0.3, 6.6, 7.1, WH_L, mat="stone")          # canopy
    wall_face(P, 0, L, TW["top"] - 0.8, holes, WH, z0=zlo if not full else -0.6)
    for zc in (4.6, 8.3, 12.4, 16.2, 19.7):
        if zc > zlo + 0.2:
            band(P, 0, L, zc, 0.2, 0.12, WH_L)
    corbel_table(P, 0, L, TW["top"] - 0.8, WH_L)
    # battlements
    zt = TW["top"]
    P.box(0, L, SK - 0.35, SK + 0.3, zt - 0.3, zt, WH_L, mat="stone", bottom=False)
    n = max(2, int(L / (TW["merlon"] * 1.8)))
    for k in range(n):
        x = L * (k + 0.25) / n
        P.box(x, x + L / n * 0.5, SK - 0.3, SK + 0.25, zt, zt + 0.75, WH_L, mat="stone", bottom=False)
    return P


def tower():
    x0, x1, y0, y1 = TOWER
    ring = [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]   # clockwise: outside on the right of each edge
    out = []
    for i in range(4):
        a, b = np.array(ring[i]), np.array(ring[i + 1])
        L = float(np.linalg.norm(b - a))
        d = (b - a) / L
        south = i == 0
        P = tower_face(L, full=south, door=south)
        out.append(frame_world(P, a, d, "caius:tower:" + ("south", "east", "north", "west")[i], TOWER_Z0))
    # pyramid roof inside the battlements
    c = np.array([(x0 + x1) / 2, (y0 + y1) / 2])
    zt = TOWER_Z0 + TW["top"]
    zr = TOWER_Z0 + TW["roof"]
    m = 0.5
    base = [(x0 + m, y0 + m), (x1 - m, y0 + m), (x1 - m, y1 - m), (x0 + m, y1 - m)]
    tris = []
    for i in range(4):
        a, b = base[i], base[(i + 1) % 4]
        tris.append([(a[0], a[1], zt), (b[0], b[1], zt), (c[0], c[1], zr)])
    out.append({"name": "caius:tower:roof", "tris": np.asarray(tris), "col": SLATE, "mat": "plain"})
    # round turret at the SE corner (King's Parade side), corbelled out from the parapet level of the range
    tx, ty, r = x1 + 0.2, y0 - 0.1, TW["turret_r"]
    prof = [(0.2, 11.0), (r, 12.4), (r, TW["turret_top"]), (r + 0.12, TW["turret_top"] + 0.1),
            (r + 0.12, TW["turret_top"] + 0.35), (r * 0.95, TW["turret_top"] + 0.35)]
    out.append(lathe(tx, ty, TOWER_Z0, prof, WH_L, 14, "caius:turret", "stone"))
    cone = [(r * 0.98, TW["turret_top"] + 0.35), (0.0, TW["cone"])]
    out.append(lathe(tx, ty, TOWER_Z0, cone, SLATE, 14, "caius:turret:cap", "plain"))
    return [o for o in out if o is not None]


def lathe(x, y, z0, prof, col, n, name, mat):
    a = np.linspace(0, 2 * math.pi, n + 1)
    tris = []
    for (r0, za), (r1, zb) in zip(prof[:-1], prof[1:]):
        for k in range(n):
            c0, s0, c1, s1 = math.cos(a[k]), math.sin(a[k]), math.cos(a[k + 1]), math.sin(a[k + 1])
            p00 = (x + r0 * c0, y + r0 * s0, z0 + za)
            p01 = (x + r0 * c1, y + r0 * s1, z0 + za)
            p11 = (x + r1 * c1, y + r1 * s1, z0 + zb)
            p10 = (x + r1 * c0, y + r1 * s0, z0 + zb)
            if r0 > 1e-4:
                tris.append([p00, p01, p11])
            if r1 > 1e-4:
                tris.append([p00, p11, p10])
    T = np.asarray(tris, float)
    # outward normals: flip triangles whose normal points to the axis
    g = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
    cen = T.mean(1)
    radial = np.stack([cen[:, 0] - x, cen[:, 1] - y, np.zeros(len(T))], -1)
    flip = (g * radial).sum(1) < 0
    T[flip] = T[flip][:, ::-1]
    return {"name": name, "tris": T, "col": col, "mat": mat}


def build_waterhouse(walls):
    ext = extents(walls)
    kinds = {"way/13864058:26": "return", "way/13864058:27": "splay", "way/13864058:28": "trinity"}
    out = []
    for w in walls:
        k = kinds.get(w["id"])
        if k is None or w["length"] < 0.5:
            continue
        x0, x1 = ext[w["id"]]
        out.append(on_wall(waterhouse_wall(w, x0, x1, k), w, "caius:waterhouse:" + w["id"].split(":")[-1]))
    out += tower()
    if walls:
        out.append(passage_wall(PASSAGE, "passage"))
        out.append(passage_wall(PASSAGE_E, "return"))
    return [o for o in out if o is not None]


# session 58: the range continues west of the gate tower along Senate House Passage (way/13864058 edge
# (-184.4, 94.0) -> (-200.7, 93.5)); outside the 90 m walls.json radius, so it was only the tile body (a grey block
# with a DSM roof, seen in every view up Senate House Hill). Same three storeys of cross windows as the Trinity
# Street front (commons_ref "King's Parade - View West into Senate House Passage", CC BY-SA 4.0, layout only).
PASSAGE = ((-200.7, 93.5), (-190.6, 93.81))   # p0 -> p1 eastward: the wall frame faces south


PASSAGE_E = ((-184.4, 94.0), (-182.5, 94.1))   # the 2 m strip between the tower and wall :26, behind the turret


def passage_wall(seg, kind):
    p0, p1 = np.asarray(seg[0]), np.asarray(seg[1])
    L = float(np.linalg.norm(p1 - p0))
    w = {"id": "caius:" + kind, "p0": p0.tolist(), "p1": p1.tolist(), "length": L, "ground_z": TOWER_Z0}
    P = waterhouse_wall(w, 0.0, L, kind)
    d = (p1 - p0) / L
    return frame_world(P, p0, d, "caius:waterhouse:passage" + ("" if kind == "passage" else "_e"), TOWER_Z0)


# ------------------------------------------------------------------ 1930s Portland-stone block (13864148, 137017433)

def portland_wall(w, x0, x1, cfg):
    """cfg: arcade (bool), storeys [(zb, zt), ...], parapet z, attic (zb, zt) or None, curved (bool),
    low_from: x after which only the arcade storey is built (set-back upper floors)."""
    P = P_(PS)
    L = w["length"]
    par = cfg["parapet"]
    low_from = cfg.get("low_from", None)
    xu1 = min(x1, low_from) if low_from is not None else x1
    zarc = 4.4
    holes = []
    n = max(1, int(round(L / 3.3))) if L >= 2.2 else 0
    bays = [L * (i + 0.5) / n for i in range(n)]
    ww = min(2.1, L / max(n, 1) - 0.9) if n else 0
    ybay = SK
    # upper storeys
    for xc in bays:
        if xc + ww / 2 > xu1 - 0.2:
            continue
        for j, (a, b) in enumerate(cfg["storeys"]):
            holes.append(casement(P, xc, ww, a, b, PS_D, PS_L, cols=3 if ww > 1.6 else 2))
            if j == 0 and cfg.get("curved"):
                # iron balconette on the curved first floor
                P.box(xc - ww / 2 - 0.1, xc + ww / 2 + 0.1, SK, SK + 0.45, a - 0.25, a - 0.1, PS_L, mat="stone")
                rail = [box(xc - ww / 2 - 0.05, a + 0.85, xc + ww / 2 + 0.05, a + 0.9)]
                rail += [box(x - 0.012, a - 0.1, x + 0.012, a + 0.88)
                         for x in np.arange(xc - ww / 2, xc + ww / 2 + 0.01, 0.12)]
                P.slab(unary_union(rail), SK + 0.38, SK + 0.42, RAIL, mat="trim")
        if cfg.get("curved"):   # carved vertical panels between the windows
            for s in (-1, 1):
                px = xc + s * (ww / 2 + 0.3)
                if x0 + 0.1 < px < xu1 - 0.1:
                    for (a, b) in cfg["storeys"][:2]:
                        P.slab(box(px - 0.12, a + 0.2, px + 0.12, b - 0.2), SK, SK + 0.07, PS_L, mat="stone")
    top = par
    wall_face(P, x0, xu1, top, holes + [box(x0 - 1, -1, x1 + 1, zarc)], PS)
    if xu1 < x1:   # low part: arcade storey + parapet only
        P.face_xz(box(xu1, zarc, x1, 5.0), SK, PS, mat="stone")
        P.box(xu1, x1, SK - 0.3, SK + 0.1, 5.0, 5.5, PS_L, mat="stone", bottom=False)
    # arcade: square piers on the bay divisions, dark recessed soffit, shopfronts behind
    piers = [0.0 + 0.35] + [L * i / n for i in range(1, n)] + [L - 0.35] if n else [0.35, L - 0.35]
    piers = [p for p in piers if x0 - 0.01 <= p - 0.35 and p + 0.35 <= x1 + 0.01] or [max(x0 + 0.35, 0.35)]
    for p in piers:
        P.box(p - 0.35, p + 0.35, YG, SK + 0.02, -0.6, zarc, PS, mat="stone", bottom=False, top=False)
        P.box(p - 0.4, p + 0.4, YG, SK + 0.07, -0.6, 0.35, PS_D, mat="stone", bottom=False)
        P.box(p - 0.42, p + 0.42, YG, SK + 0.07, zarc - 0.3, zarc - 0.15, PS_L, mat="stone", bottom=False)
    # soffit + shop glass
    P.quad((x0, YG, zarc), (x1, YG, zarc), (x1, SK, zarc), (x0, SK, zarc), (0, 0, -1), SOFFIT, "plain")
    shop = box(x0, -0.6, x1, zarc)
    glass = []
    sp = sorted(piers)
    for a, b in zip([x0] + sp, sp + [x1]):
        a2, b2 = a + (0.35 if a != x0 else 0), b - (0.35 if b != x1 else 0)
        if b2 - a2 > 0.6:
            glass.append(box(a2 + 0.1, 0.45, b2 - 0.1, 3.3))
            P.count("shopfront")
    gl = unary_union(glass) if glass else None
    back = shop.difference(gl) if gl is not None else shop
    P.face_xz(back, YG - 0.01, SHOP, mat="timber")
    if gl is not None:
        P.face_xz(gl, YG - 0.005, GLASS, mat="glass")
        P.slab(grid_bars(gl.envelope, max(1, int((x1 - x0) / 1.4)), 1, 0.05).intersection(gl.buffer(0.05)),
               YG - 0.01, YG + 0.02, F.rgb("#2c2d2e"), mat="frame")
    # fascia/entablature over the arcade, cornice under the first-floor windows
    P.box(x0, x1, SK - 0.02, SK + 0.12, zarc, zarc + 0.6, PS_L, mat="stone")
    band(P, x0, xu1, zarc + 0.6, 0.18, 0.1, PS_L)
    # top storey band + parapet with coping
    band(P, x0, xu1, cfg["storeys"][-1][0] - 0.45, 0.16, 0.08, PS_L)
    P.box(x0, xu1, SK - 0.3, SK + 0.05, top - 0.6, top, PS, mat="stone", bottom=False, top=False)
    P.extrude_profile([(SK - 0.35, top), (SK + 0.12, top), (SK + 0.12, top + 0.1), (SK - 0.35, top + 0.16)],
                      x0, xu1, PS_L, mat="stone")
    if cfg.get("attic"):
        a, b = cfg["attic"]
        ya = SK - 1.3
        ah = []
        for xc in bays:
            if xc + 0.7 < xu1:
                ah.append(casement(P, xc, 1.3, a + 0.4, b - 0.45, PS_D, PS_L, cols=2, rows=3, y=ya, sill=False))
        P.face_xz(box(x0, top, xu1, b).difference(unary_union(ah)) if ah else box(x0, top, xu1, b), ya, PS,
                  mat="stone")
        P.extrude_profile([(ya - 0.3, b), (ya + 0.15, b), (ya + 0.15, b + 0.18), (ya - 0.3, b + 0.18)], x0, xu1,
                          PS_L, mat="stone")
        P.quad((x0, ya + 0.15, b + 0.18), (xu1, ya + 0.15, b + 0.18), (xu1, ya - 4.0, b + 0.18),
               (x0, ya - 4.0, b + 0.18), (0, 0, 1), LEAD, "plain")
    return P


PORT_STD = dict(storeys=[(5.5, 7.4), (8.2, 10.1), (10.9, 12.8), (13.6, 15.0)], parapet=15.75)
PORT_CFG = {
    "way/13864148:7": dict(PORT_STD, curved=True),
    "way/13864148:8": dict(PORT_STD),
    "way/13864148:9": dict(PORT_STD),
    "way/13864148:10": dict(PORT_STD, curved=True, attic=(15.75, 18.2)),
    "way/13864148:11": dict(PORT_STD, curved=True, attic=(15.75, 18.2)),
    "way/13864148:12": dict(PORT_STD, curved=True, attic=(15.75, 18.2)),
    "way/13864148:13": dict(PORT_STD, attic=(15.75, 18.2), low_from=9.4),
    "way/137017433:4": dict(storeys=[(5.4, 7.2), (7.9, 9.7)], parapet=10.8),
}


def plain_wall(w, x0, x1, col, h, storey=2.8, z1=3.6):
    """Rear / courtyard walls with no reference: ashlar, a regular grid of casements, parapet."""
    P = P_(col)
    L = w["length"]
    n = int(L / 3.0)
    holes = []
    for i in range(n):
        xc = L * (i + 0.5) / n
        z = z1
        while z + 1.8 < h - 0.8:
            holes.append(casement(P, xc, 1.4, z, z + 1.7, F.shade(col, 0.72), F.shade(col, 1.05), cols=1, rows=2))
            z += storey
    wall_face(P, x0, x1, h, holes, col)
    P.extrude_profile([(SK - 0.3, h), (SK + 0.1, h), (SK + 0.1, h + 0.12), (SK - 0.3, h + 0.18)], x0, x1,
                      F.shade(col, 1.05), mat="stone")
    return P


def build_portland(walls):
    ext = extents(walls)
    out = []
    for w in walls:
        if w["length"] < 0.5:
            continue
        x0, x1 = ext[w["id"]]
        cfg = PORT_CFG.get(w["id"])
        if cfg is not None:
            P = portland_wall(w, x0, x1, cfg)
        else:
            h = min(w["eave_z"] - w["ground_z"], 15.7)
            if h < 2.5:
                continue
            P = plain_wall(w, x0, x1, PS, h)
        out.append(on_wall(P, w, "caius:portland:" + w["id"]))
    return [o for o in out if o is not None]


# ------------------------------------------------------------------ way/137017435: low ashlar block

def build_low(walls):
    ext = extents(walls)
    out = []
    for w in walls:
        if w["eave_z"] - w["ground_z"] < 1.0 or w["length"] < 0.5:
            continue
        x0, x1 = ext[w["id"]]
        P = P_(LB)
        h = 3.7
        wall_face(P, x0, x1, h - 0.3, [], LB)
        P.box(x0, x1, SK - 0.02, SK + 0.12, -0.6, 0.45, F.shade(LB, 0.88), mat="stone", bottom=False)
        P.extrude_profile([(SK - 0.4, h - 0.3), (SK + 0.12, h - 0.3), (SK + 0.12, h - 0.15), (SK + 0.02, h),
                           (SK - 0.4, h)], x0, x1, F.shade(LB, 1.06), mat="stone")
        out.append(on_wall(P, w, "caius:low:" + w["id"]))
    return [o for o in out if o is not None]


BUILDS = {
    "way/13864058": build_waterhouse,
    "way/13864148": build_portland,
    "way/137017433": build_portland,
    "way/137017435": build_low,
}
HIDE_TILE = []   # none of these is a closed exterior (only the street walls are modelled)


def _count_elements():
    """Fill ELEMENTS by running the builders on walls.json (zone_build reads ELEMENTS for the facade KPI)."""
    import json
    ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    try:
        W = json.load(open(os.path.join(ROOT, "data/annotations/market_square/walls.json")))["walls"]
        for oid, fn in BUILDS.items():
            fn([w for w in W if w["osm_id"] == oid])
    except Exception as e:   # never break the zone build
        print("zone_bespoke_caius: element count failed", repr(e), file=sys.stderr)


_count_elements()

if __name__ == "__main__":
    import json
    ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    W = json.load(open(os.path.join(ROOT, "data/annotations/market_square/walls.json")))["walls"]
    tot = 0
    for oid, fn in BUILDS.items():
        items = fn([w for w in W if w["osm_id"] == oid])
        n = sum(len(i["tris"]) for i in items)
        tot += n
        zs = np.concatenate([np.asarray(i["tris"])[..., 2].ravel() for i in items])
        print(oid, len(items), "items", n, "tris", "z", round(float(zs.min()), 2), round(float(zs.max()), 2))
    print("total", tot)
