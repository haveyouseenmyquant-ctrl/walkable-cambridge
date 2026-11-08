"""Bespoke geometry for the Senate House (OSM way/5094870; James Gibbs, 1722-30, west end 1768), session 33.

zone_build.load_bespoke() picks up BUILDS. The building lies outside the Market Square wall annotations, so build()
gets no walls and works from the OSM footprint (a clean 34.76 x 13.83 m rectangle, long axis ~5.6 deg north of east).
Design from Wikimedia Commons (Category:Senate House, Cambridge: "Senate House, Cambridge.jpg" (south front from the
lawn) and "Cambridge - King's Parade - View West on Senate House 1730 by James Gibbs ... .jpg" (east end), both
CC BY-SA): Portland stone throughout.
- south (lawn) front: 9 bays; the centre 3 bays are a frontispiece of four engaged Corinthian columns carrying a
  pediment (urns on the apex and both ends), the other bays have single Corinthian pilasters and paired pilasters
  at the corners; ground-floor windows with alternating triangular/segmental pediments (centre door, triangular),
  round-headed first-floor windows with archivolts and keystones; full entablature, balustrade with pedestals over
  the pilasters, corner urns; low podium with steps across the frontispiece;
- east end (King's Parade): 3 bays, temple front of four engaged columns under a full-width pediment, centre door,
  ground windows with segmental pediments; west end the same with pilasters (the 1768 end);
- north side (Senate House Passage): like the south front without the frontispiece;
- low lead roof, ridge on the long axis, a short cross roof behind the south pediment.
Heights above Z0 = 9.5 m (DTM 9.2-9.7) from the LiDAR DSM (data/lidar/dsm_1m.tif and the 2023 first-return DSM):
balustrade top 13.1 (DSM 22.4-22.9 over the wall line), gutter behind it 12.4 (21.9), roof ridge 14.25
(23.7-23.8), end pediment apex 14.45 (24.2-24.5 with the urn), south pediment apex 14.3 (23.4-23.9 behind it,
24.6-25.1 at the apex urn), urn tops ~15.4.
NB: the LiDAR roof is ~17.5 m deep (t 0..17.5, ridge at t ~9.4) while the OSM footprint is 13.83 m; the model keeps
to the OSM footprint (= the tile collision and Senate House Passage alignment), heights from the LiDAR.
"""
import math
import os
import sys

import numpy as np
from shapely.geometry import Polygon, box
from shapely.ops import unary_union

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import facade_parts as F  # noqa: E402

OSM = "way/5094870"
Z0 = 9.5
REV = 0.38            # window reveal depth
STONE = F.rgb("#eee7d6")   # Portland stone, weathered cream-white
STONE_D = F.shade(STONE, 0.74)
STONE_L = F.shade(STONE, 1.05)
GLASS = F.rgb(F.GLASS_COL)
SASH = F.rgb("#ece8de")
DOOR = F.rgb("#6a4a30")
LEAD = F.rgb("#7f8589")

# building frame: s east along the south wall from the SW corner, t north (OSM footprint corners)
O = np.array([-229.92, 71.67])
U = np.array([0.99517579, 0.09810782])
V = np.array([-U[1], U[0]])
LEN = 34.76
WID = 13.83

# heights above Z0
Z_POD = 0.6           # podium top (bases of the order)
Z_CAP = 8.95          # capital bottom
Z_ENT = 9.7           # entablature bottom (abacus top)
Z_COR = 11.2          # cornice top
Z_BAL = 13.05         # balustrade rail top
Z_PED = 13.2          # pedestal tops
Z_GUT = 12.4          # lead gutter / roof eaves behind the balustrade
Z_RIDGE = 14.25
Z_APEX_END = 14.45    # end pediment top
Z_APEX_S = 14.3       # south pediment top
LOW = (1.3, 4.0)      # ground-floor window opening
UPP = (6.0, 9.0)      # first-floor round-headed opening (top of the arch)
WW = 1.4              # window width

E_LONG = 1.6
B_LONG = (LEN - 2 * E_LONG) / 9


def L2W(s, t):
    return O + s * U + t * V


def P_():
    return F.Parts(mat="stone", wall_col=STONE)


# ------------------------------------------------------------------ helpers (wall frame: x along, y out, z up)

def lathe(P, x, y, prof, col, n=12, mat="stone", a0=0.0, a1=2 * math.pi):
    """Surface of revolution about the vertical axis at (x, y); prof = [(r, z), ...] bottom to top."""
    full = abs(a1 - a0 - 2 * math.pi) < 1e-6
    a = np.linspace(a0, a1, n + 1)
    tris, nrm = [], []
    for (r0, z0), (r1, z1) in zip(prof[:-1], prof[1:]):
        dz, dr = z1 - z0, r1 - r0
        for k in range(n):
            c0, s0, c1, s1 = math.cos(a[k]), math.sin(a[k]), math.cos(a[k + 1]), math.sin(a[k + 1])
            p00 = (x + r0 * c0, y + r0 * s0, z0)
            p01 = (x + r0 * c1, y + r0 * s1, z0)
            p11 = (x + r1 * c1, y + r1 * s1, z1)
            p10 = (x + r1 * c0, y + r1 * s0, z1)
            am = (a[k] + a[k + 1]) / 2
            L = math.hypot(dz, dr) or 1.0
            nv = (math.cos(am) * dz / L, math.sin(am) * dz / L, -dr / L)
            if r0 > 1e-4:
                tris.append([p00, p01, p11]); nrm.append(nv)
            if r1 > 1e-4:
                tris.append([p00, p11, p10]); nrm.append(nv)
    r, z = prof[-1]
    if r > 1e-4 and full:
        for k in range(n):
            tris.append([(x + r * math.cos(a[k]), y + r * math.sin(a[k]), z),
                         (x + r * math.cos(a[k + 1]), y + r * math.sin(a[k + 1]), z), (x, y, z)])
            nrm.append((0, 0, 1))
    if tris:
        P.add(tris, np.asarray(nrm, float), col, mat)


def urn(P, x, y, z, s=1.0):
    prof = [(0.28, 0.0), (0.28, 0.12), (0.12, 0.2), (0.1, 0.3), (0.3, 0.55), (0.34, 0.75), (0.24, 0.92),
            (0.13, 0.98), (0.16, 1.02), (0.06, 1.12), (0.08, 1.2), (0.0, 1.3)]
    lathe(P, x, y, [(r * s, z + h * s) for r, h in prof], STONE_L, n=10)


def column(P, x, y):
    """Engaged Corinthian column (front ~3/4 modelled), base on the podium, abacus top at Z_ENT."""
    P.box(x - 0.55, x + 0.55, y - 0.55, y + 0.55, Z_POD, Z_POD + 0.25, STONE, bottom=False)   # plinth
    a0, a1 = -0.25 * math.pi, 1.25 * math.pi
    lathe(P, x, y, [(0.53, Z_POD + 0.25), (0.53, Z_POD + 0.35), (0.48, Z_POD + 0.45), (0.45, Z_POD + 0.5)],
          STONE, n=16, a0=a0, a1=a1)
    shaft = [(0.44, Z_POD + 0.5), (0.44, 3.4), (0.42, 6.0), (0.38, Z_CAP - 0.1), (0.41, Z_CAP - 0.05), (0.41, Z_CAP)]
    lathe(P, x, y, shaft, STONE, n=20, a0=a0, a1=a1)
    # capital: acanthus bell (two leaf rows as bulges) under a hollow-sided abacus
    bell = [(0.39, Z_CAP), (0.46, Z_CAP + 0.18), (0.42, Z_CAP + 0.25), (0.52, Z_CAP + 0.45), (0.47, Z_CAP + 0.52),
            (0.58, Z_CAP + 0.62)]
    lathe(P, x, y, bell, STONE_L, n=16, a0=a0, a1=a1)
    P.box(x - 0.62, x + 0.62, y - 0.62, y + 0.62, Z_CAP + 0.62, Z_ENT, STONE_L)
    for sx in (-1, 1):   # corner volutes
        P.box(x + sx * 0.5 - 0.1, x + sx * 0.5 + 0.1, y + 0.4, y + 0.62, Z_CAP + 0.4, Z_CAP + 0.62, STONE_L)


def pilaster(P, x, w=0.85, d=0.22):
    P.box(x - w / 2 - 0.08, x + w / 2 + 0.08, -0.05, d + 0.08, Z_POD, Z_POD + 0.35, STONE)   # base
    P.box(x - w / 2, x + w / 2, -0.05, d, Z_POD + 0.35, Z_CAP, STONE, top=False, bottom=False)
    P.box(x - w / 2 - 0.02, x + w / 2 + 0.02, -0.05, d + 0.06, Z_CAP, Z_CAP + 0.3, STONE_L, bottom=False)
    P.box(x - w / 2 - 0.08, x + w / 2 + 0.08, -0.05, d + 0.12, Z_CAP + 0.3, Z_CAP + 0.6, STONE_L, bottom=False)
    P.box(x - w / 2 - 0.13, x + w / 2 + 0.13, -0.05, d + 0.16, Z_CAP + 0.6, Z_ENT, STONE_L)


def glazing(P, op, yg, cols, rows, zspring=None, xc=None):
    """Sash frame + glazing bars inside opening op (polygon in xz) on the glass plane yg."""
    x0, z0, x1, z1 = op.bounds
    inner = op.buffer(-0.08, join_style=2)
    bw = 0.035
    zt = zspring if zspring is not None else z1
    parts = [op.difference(inner)]
    for i in range(1, cols):
        x = x0 + (x1 - x0) * i / cols
        parts.append(box(x - bw / 2, z0, x + bw / 2, z1))
    for j in range(1, rows):
        z = z0 + (zt - z0) * j / rows
        parts.append(box(x0, z - bw / 2, x1, z + bw / 2))
    if zspring is not None:   # fanlight bars radiating from the springing centre
        parts.append(box(x0, zspring - 0.04, x1, zspring + 0.04))
        r = (x1 - x0) / 2
        for ang in (math.radians(55), math.radians(125)):
            parts.append(Polygon([(xc - 0.02, zspring), (xc + 0.02, zspring),
                                  (xc + r * math.cos(ang) + 0.02, zspring + r * math.sin(ang)),
                                  (xc + r * math.cos(ang) - 0.02, zspring + r * math.sin(ang))]))
    meeting = (z0 + zt) / 2   # meeting rail of the sash
    parts.append(box(x0, meeting - 0.04, x1, meeting + 0.04))
    g = unary_union(parts).intersection(op)
    P.slab(g, yg, yg + 0.06, SASH, mat="frame")


def low_window(P, xc, kind, door=False):
    """Ground-floor window (or door) with architrave, frieze, cornice and a triangular ('T') or segmental ('S')
    pediment. Returns the opening polygon."""
    w = 1.7 if door else WW
    z0, z1 = (Z_POD, 4.1) if door else LOW
    op = box(xc - w / 2, z0, xc + w / 2, z1)
    dep = 0.5 if door else REV
    P.sides_xz(op, -dep, 0.0, STONE_D, inward=True, skip_ground=door, mat="stone")
    if door:
        P.face_xz(op, -dep, DOOR, mat="timber")
        for lx in (xc - w / 4, xc + w / 4):   # two leaves, three raised panels each
            for (pz0, pz1) in ((z0 + 0.3, z0 + 1.2), (z0 + 1.45, z0 + 2.4), (z0 + 2.65, z1 - 0.25)):
                P.slab(box(lx - w / 4 + 0.13, pz0, lx + w / 4 - 0.13, pz1), -dep, -dep + 0.05, F.shade(DOOR, 1.1),
                       mat="timber")
        P.slab(box(xc - 0.02, z0, xc + 0.02, z1), -dep, -dep + 0.06, F.shade(DOOR, 0.8), mat="timber")
    else:
        P.face_xz(op, -REV, GLASS, mat="glass")
        glazing(P, op, -REV + 0.02, 3, 4)
        # sill on small blocks
        P.box(xc - w / 2 - 0.2, xc + w / 2 + 0.2, -0.05, 0.16, z0 - 0.14, z0, STONE_L)
        P.box(xc - w / 2 - 0.1, xc + w / 2 + 0.1, -0.05, 0.08, z0 - 0.45, z0 - 0.14, STONE)
    a = 0.2   # architrave
    ring = box(xc - w / 2 - a, z0 if door else z0, xc + w / 2 + a, z1 + a).difference(op)
    P.slab(ring, -0.05, 0.08, STONE_L)
    zf = z1 + a
    P.box(xc - w / 2 - a, xc + w / 2 + a, -0.05, 0.05, zf, zf + 0.3, STONE)     # frieze
    for sx in (-1, 1):   # consoles either side of the frieze
        P.box(xc + sx * (w / 2 + a + 0.08) - 0.09, xc + sx * (w / 2 + a + 0.08) + 0.09, -0.05, 0.2,
              zf - 0.35, zf + 0.3, STONE_L)
    zc = zf + 0.3
    P.extrude_profile([(-0.05, zc), (0.1, zc), (0.26, zc + 0.12), (0.26, zc + 0.2), (-0.05, zc + 0.2)],
                      xc - w / 2 - a - 0.2, xc + w / 2 + a + 0.2, STONE_L)
    zp = zc + 0.2
    hw = w / 2 + a + 0.2
    if kind == "T":
        outer = Polygon([(xc - hw, zp), (xc + hw, zp), (xc, zp + 0.55)])
        inner = Polygon([(xc - hw + 0.35, zp + 0.06), (xc + hw - 0.35, zp + 0.06), (xc, zp + 0.42)])
    else:
        r = (hw ** 2 + 0.45 ** 2) / (2 * 0.45)
        ang = math.asin(hw / r)
        pts = [(xc + r * math.sin(t), zp + 0.45 - r + r * math.cos(t)) for t in np.linspace(ang, -ang, 12)]
        outer = Polygon(pts)
        r2 = r - 0.15
        hw2 = hw - 0.35
        ang2 = math.asin(min(hw2 / r2, 1.0))
        pts2 = [(xc + r2 * math.sin(t), zp + 0.45 - r + r * math.cos(0) - 0.15 - (r2 - r2 * math.cos(t)))
                for t in np.linspace(ang2, -ang2, 10)]
        inner = Polygon(pts2 + [(xc - hw2, zp + 0.06), (xc + hw2, zp + 0.06)][::-1]) if len(pts2) > 2 else None
        if inner is not None:
            inner = inner.buffer(0).intersection(outer)
    P.slab(outer, -0.05, 0.24, STONE_L)
    if inner is not None and not inner.is_empty:
        P.slab(inner, 0.24, 0.26, STONE, sides=False)   # tympanum face, a touch proud: shadow line on the mould
    return op


def upp_window(P, xc):
    """First-floor round-headed window: reveals, sash with fanlight, archivolt, keystone, sill with apron."""
    w = WW
    z0, zt = UPP
    zs = zt - w / 2
    pts = [(xc - w / 2, z0), (xc + w / 2, z0)] + [(xc + w / 2 * math.cos(t), zs + w / 2 * math.sin(t))
                                                  for t in np.linspace(0, math.pi, 13)]
    op = Polygon(pts)
    P.sides_xz(op, -REV, 0.0, STONE_D, inward=True, mat="stone")
    P.face_xz(op, -REV, GLASS, mat="glass")
    glazing(P, op, -REV + 0.02, 3, 4, zspring=zs, xc=xc)
    arc = op.buffer(0.18, join_style=1, resolution=6).difference(op).intersection(box(xc - w, zs - 0.01, xc + w, zt + 1))
    P.slab(arc, -0.05, 0.08, STONE_L)
    for sx in (-1, 1):   # impost blocks
        P.slab(box(xc + sx * w / 2 - 0.09 + sx * 0.09, zs - 0.12, xc + sx * w / 2 + 0.09 + sx * 0.09, zs),
               -0.05, 0.1, STONE_L)
    P.slab(Polygon([(xc - 0.14, zt - 0.05), (xc + 0.14, zt - 0.05), (xc + 0.2, zt + 0.3), (xc - 0.2, zt + 0.3)]),
           -0.05, 0.14, STONE_L)   # keystone
    P.box(xc - w / 2 - 0.25, xc + w / 2 + 0.25, -0.05, 0.17, z0 - 0.15, z0, STONE_L)   # sill
    P.box(xc - w / 2 - 0.1, xc + w / 2 + 0.1, -0.05, 0.06, z0 - 0.6, z0 - 0.15, STONE)  # apron panel
    for sx in (-1, 1):
        P.box(xc + sx * (w / 2 + 0.05) - 0.08, xc + sx * (w / 2 + 0.05) + 0.08, -0.05, 0.14, z0 - 0.45, z0 - 0.15,
              STONE_L)
    return op


def entablature(P, x0, x1, d=0.0):
    prof = [(-0.05, Z_ENT), (d + 0.36, Z_ENT), (d + 0.36, 9.95), (d + 0.39, 9.98), (d + 0.39, 10.2),
            (d + 0.3, 10.2), (d + 0.3, 10.66), (d + 0.42, 10.7), (d + 0.5, 10.8), (d + 0.9, 10.95),
            (d + 0.95, 11.05), (d + 0.95, Z_COR), (-0.05, Z_COR)]
    P.extrude_profile(prof, x0, x1, STONE_L)


def podium(P, x0, x1):
    P.extrude_profile([(-0.05, -0.9), (0.5, -0.9), (0.5, Z_POD - 0.15), (0.42, Z_POD - 0.05), (0.42, Z_POD),
                       (-0.05, Z_POD)], x0, x1, STONE_D)


def balustrade(P, x0, x1, posts):
    """Balustrade on the cornice from x0 to x1: plinth, turned balusters, rail; pedestals at posts (+ ends)."""
    y0, y1 = -0.4, 0.12
    yc = (y0 + y1) / 2
    zb = Z_COR
    P.box(x0, x1, y0 - 0.01, y1, zb, zb + 0.35, STONE, bottom=False)
    P.box(x0, x1, y0 - 0.06, y1 + 0.06, Z_BAL - 0.38, Z_BAL, STONE_L, bottom=True)
    P.quad((x0, y0 - 0.06, Z_BAL - 0.38), (x0, y0 - 0.06, Z_BAL), (x1, y0 - 0.06, Z_BAL), (x1, y0 - 0.06, Z_BAL - 0.38),
           (0, -1, 0), STONE_L)   # rail back (seen from the roof / afar)
    posts = sorted(set([x0 + 0.33, x1 - 0.33] + [p for p in posts if x0 + 0.33 <= p <= x1 - 0.33]))
    for p in posts:
        P.box(p - 0.33, p + 0.33, y0 - 0.08, y1 + 0.08, zb, Z_PED, STONE, bottom=False)
        P.box(p - 0.38, p + 0.38, y0 - 0.12, y1 + 0.12, Z_PED - 0.1, Z_PED, STONE_L, bottom=False)
    zl, zh = zb + 0.35, Z_BAL - 0.38
    hgt = zh - zl
    prof = [(0.1, 0.0), (0.07, 0.12), (0.13, 0.38), (0.055, 0.72), (0.1, 0.88), (0.1, 1.0)]
    for a, b in zip(posts[:-1], posts[1:]):
        s0, s1 = a + 0.33, b - 0.33
        n = int((s1 - s0) / 0.3)
        if n < 1:
            continue
        sp = (s1 - s0) / n
        for k in range(n):
            lathe(P, s0 + sp * (k + 0.5), yc, [(r, zl + h * hgt) for r, h in prof], STONE, n=6)


def wall_face(P, x0, x1, holes, ztop=Z_ENT + 0.05):
    g = box(x0, -0.9, x1, ztop)
    if holes:
        g = g.difference(unary_union(holes))
    P.face_xz(g, 0.0, STONE, mat="stone")


def pediment(P, xa, xb, zbase, ztop, y, yback):
    """Pediment on the cornice (zbase) spanning xa..xb, top of the raking cornice at ztop; tympanum at y."""
    xc = (xa + xb) / 2
    t = 0.5
    outer = Polygon([(xa, zbase), (xb, zbase), (xc, ztop)])
    k = (ztop - zbase) / ((xb - xa) / 2)
    dx = t * math.sqrt(1 + k * k) / k
    inner = Polygon([(xa + dx + 0.15, zbase + 0.3), (xb - dx - 0.15, zbase + 0.3), (xc, ztop - t * math.sqrt(1 + k * k))])
    P.face_xz(outer.difference(inner), y + 0.75, STONE_L)            # raking cornice front
    P.sides_xz(outer.difference(inner), y, y + 0.75, STONE_L)
    P.face_xz(inner, y, STONE)                                       # tympanum
    P.face_xz(outer, yback, STONE, n=(0, -1, 0))                     # back of the pediment wall
    P.sides_xz(outer, yback, y, STONE)
    # carved cartouche with festoons in the tympanum (low relief)
    ht = inner.bounds[3] - inner.bounds[1]
    car = Polygon([(xc + 0.55 * math.cos(a), zbase + 0.3 + ht * 0.42 + 0.6 * math.sin(a))
                   for a in np.linspace(0, 2 * math.pi, 14)[:-1]])
    P.slab(car, y, y + 0.18, STONE_L)
    for sx in (-1, 1):
        fest = Polygon([(xc + sx * 0.5, zbase + 0.3 + ht * 0.45), (xc + sx * 2.4, zbase + 0.45),
                        (xc + sx * 2.0, zbase + 0.4), (xc + sx * 0.5, zbase + 0.3 + ht * 0.3)])
        P.slab(fest.intersection(inner), y, y + 0.1, STONE_L)
    return xc


# ------------------------------------------------------------------ elevations

def long_front(south):
    P = P_()
    L = LEN
    xs = [E_LONG + B_LONG * (i + 0.5) for i in range(9)]
    posts = [E_LONG + B_LONG * i for i in range(10)]
    holes = []
    kinds = "TSTSTSTST"
    for i, x in enumerate(xs):
        holes.append(low_window(P, x, kinds[i], door=(south and i == 4)))
        holes.append(upp_window(P, x))
    wall_face(P, 0, L, holes)
    podium(P, -0.5, L + 0.5)
    # order: paired corner pilasters + pilasters on the bay divisions; engaged columns on the south frontispiece
    for x in (0.45, L - 0.45):
        pilaster(P, x)
    cols = posts[3:7] if south else []
    for p in posts:
        if p in cols:
            column(P, p, 0.28)
        else:
            pilaster(P, p)
    entablature(P, -0.95, L + 0.95)
    if south:
        xa, xb = cols[0] - 0.8, cols[-1] + 0.8
        entablature(P, xa, xb, d=0.42)
        # steps across the frontispiece up to the podium
        for k in range(4):
            P.box(xa - 0.6, xb + 0.6, 0.0, 0.5 + 0.38 * (k + 1), -0.9, Z_POD - 0.15 * k, STONE_D, bottom=False)
        pediment(P, xa - 0.15, xb + 0.15, Z_COR, Z_APEX_S, 0.62, -0.1)
        balustrade(P, 0.0, xa - 0.15, posts)
        balustrade(P, xb + 0.15, L, posts)
        urn(P, (xa + xb) / 2, 0.6, Z_APEX_S - 0.15, 1.05)
        for x in (xa + 0.25, xb - 0.25):
            P.box(x - 0.35, x + 0.35, -0.2, 0.75, Z_COR, Z_PED, STONE, bottom=False)
            urn(P, x, 0.27, Z_PED, 0.95)
    else:
        balustrade(P, 0.0, L, posts)
    for x in (0.33, L - 0.33):
        urn(P, x, -0.14, Z_PED, 0.95)
    return P


def end_front(east):
    P = P_()
    W = WID
    e = 2.13
    b = (W - 2 * e) / 3
    xs = [e + b * (i + 0.5) for i in range(3)]
    posts = [e + b * i for i in range(4)]
    holes = []
    for i, x in enumerate(xs):
        holes.append(low_window(P, x, "T" if i == 1 else "S", door=(east and i == 1)))
        holes.append(upp_window(P, x))
    wall_face(P, 0, W, holes)
    podium(P, -0.5, W + 0.5)
    for x in (0.45, W - 0.45):
        pilaster(P, x)
    for p in posts:
        if east:
            column(P, p, 0.28)
        else:
            pilaster(P, p)
    entablature(P, -0.95, W + 0.95)
    if east:
        entablature(P, posts[0] - 0.8, posts[-1] + 0.8, d=0.42)
    pediment(P, -0.95, W + 0.95, Z_COR, Z_APEX_END, 0.2, -0.3)
    urn(P, W / 2, 0.2, Z_APEX_END - 0.15, 0.8)
    return P


# ------------------------------------------------------------------ assembly

def frame_world(P, p0, d, name, z0=Z0):
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


def on_local(P, A, B, name):
    a, b = L2W(*A), L2W(*B)
    d = (b - a) / np.linalg.norm(b - a)
    return frame_world(P, a, d, name)


def roofs():
    """Lead roof: two low slopes on the long axis between the end pediments, gutters behind the balustrades, and a
    short cross roof behind the south pediment. Built in (s, t, z) then mapped to world."""
    q = []
    tm = WID / 2
    s0, s1 = 0.0, LEN
    q.append([(s0, 0.15, Z_GUT), (s1, 0.15, Z_GUT), (s1, 1.0, Z_GUT), (s0, 1.0, Z_GUT)])               # gutters
    q.append([(s0, WID - 1.0, Z_GUT), (s1, WID - 1.0, Z_GUT), (s1, WID - 0.15, Z_GUT), (s0, WID - 0.15, Z_GUT)])
    q.append([(s0, 1.0, Z_GUT), (s1, 1.0, Z_GUT), (s1, tm, Z_RIDGE), (s0, tm, Z_RIDGE)])
    q.append([(s0, tm, Z_RIDGE), (s1, tm, Z_RIDGE), (s1, WID - 1.0, Z_GUT), (s0, WID - 1.0, Z_GUT)])
    # cross roof behind the south pediment (ridge just under the pediment top, dying into the main roof)
    posts = [E_LONG + B_LONG * i for i in range(10)]
    xa, xb = posts[3] - 0.95, posts[6] + 0.95
    xc = (xa + xb) / 2
    zr = Z_APEX_S - 0.45
    k = (Z_APEX_S - Z_COR) / ((xb - xa) / 2)
    ze = zr - k * (xb - xa) / 2 * 0.55
    xl, xr = xc - (xb - xa) / 2 * 0.55, xc + (xb - xa) / 2 * 0.55
    q.append([(xl, 0.2, ze), (xc, 0.2, zr), (xc, tm, zr), (xl, tm, ze)])
    q.append([(xc, 0.2, zr), (xr, 0.2, ze), (xr, tm, ze), (xc, tm, zr)])
    tris = []
    for a, b, c, d in q:
        A, B_, C, D = [(*L2W(s, t), Z0 + z) for s, t, z in (a, b, c, d)]
        tris += [[A, B_, C], [A, C, D]]
    T = np.asarray(tris, float)
    g = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
    T[g[:, 2] < 0] = T[g[:, 2] < 0][:, ::-1]
    return {"name": "senate:roof", "tris": T, "col": LEAD, "mat": "plain"}


def build(walls=None):
    out = [
        on_local(long_front(True), (0, 0), (LEN, 0), "senate:south"),
        on_local(end_front(True), (LEN, 0), (LEN, WID), "senate:east"),
        on_local(long_front(False), (LEN, WID), (0, WID), "senate:north"),
        on_local(end_front(False), (0, WID), (0, 0), "senate:west"),
        roofs(),
    ]
    return [o for o in out if o is not None]


BUILDS = {OSM: build}
HIDE_TILE = [OSM]   # complete model; the tile landmark body is hidden (collision kept)

if __name__ == "__main__":
    items = build([])
    for it in items:
        Tz = np.asarray(it["tris"])[..., 2]
        print(it["name"], len(it["tris"]), round(float(Tz.min()), 2), round(float(Tz.max()), 2))
    print("total", sum(len(i["tris"]) for i in items))
