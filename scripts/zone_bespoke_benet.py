"""Bespoke geometry for St Bene't's Church, Bene't Street (OSM way/134521042, building=church), session 36.
zone_build.load_bespoke() picks up BUILDS / HIDE_TILE. The church lies outside the Market Square walls.json, so
build() gets no walls and works from the OSM footprint (ELEMENTS stays empty).

Frame: O = the OSM SW corner (E -156.67, N -129.31), s east along the OSM south wall (axis 1.0 deg north of east),
t north (towards Bene't Street). Z0 = 9.6 (DTM 9.5-9.6 round the church).
NB: the LiDAR DSM puts the building ~0.5-1.5 m west and ~2 m south of the OSM outline (north aisle wall at N -112.9 vs
OSM -111.3, south aisle at -131.8 vs -129.3); the model keeps the OSM outline (tile collision, paths, churchyard
fence) and takes the internal divisions from the DSM, t scaled by 0.958 to fit the OSM depth.

Parts and heights (data/lidar/dsm_1m.tif, 2023 first-return DSM as check; tree pixels south of the tower in the
older DSM ignored, the 2023 one reads 15.5 there):
- Anglo-Saxon west tower s -1.0..5.1, t 5.3..11.1 (projects ~1 m west of the aisle west walls as in the DSM):
  coursed rubble (clunch / fieldstone / ironstone) with long-and-short quoins in paler stone at every corner,
  two string courses (10.8, 15.0), small round-headed lights in the lower and middle stages; belfry stage with the
  paired round-headed openings on a turned baluster shaft under a through-stone impost, a raised square label
  round the pair and a pilaster strip above it, single round-headed louvred lights either side with circular
  sound-holes in square frames above; flat lead roof behind a plain coped top at 29.7 (DSM 29.5-29.9, first
  return 29.4-30.2), weathervane cross;
- nave s 5.1..17.1, t 5.3..12.2: clerestory with square-headed two-light windows, plain parapets at 19.5 (DSM
  19.2-19.9 along both clerestory lines), low-pitched lead roof, ridge 20.7 (DSM 20.6-20.8 at N -122.5);
- north aisle t 11.1..18.1 (Bene't Street side): own pitched slate roof, eaves 15.4 (DSM 15.6 edge pixels / 16.2
  first full row), ridge 17.3 (DSM 17.3-17.4), west gable with a three-light Decorated window beside the tower,
  two-light windows, buttresses; gabled north porch s 4.2..9.6, ridge 14.7 (DSM 14.3-14.8), pointed doorway and
  trefoil in the gable; vestry east of the aisle, ridge 16.0 (DSM 15.9-16.0);
- south aisle t 0..5.3: flat lead roof behind a parapet at 15.6 (DSM 15.4-15.6);
- chancel s 17.1..24.6, t 6.6..12.0, ridge 19.5 (DSM 19.4-19.6), eaves 16.8, three-light east window; south chapel /
  Corpus gallery block t 0..6.6, parallel gable, ridge 19.2 (DSM 19.0-19.2), eaves 16.8, windows in two storeys.

References (shape/proportion/colour only, no pixels used): Wikimedia Commons "1126252 I CHURCH OF ST BENE'T, BENE'T
STREET Cambridge 20260523 0001.jpg", "... 0002.jpg", "... 0003.jpg" (Tilman2007, CC BY-SA 4.0) and "Church in
Cambridge.jpg" (Christopher, flickr 47038415@N00, CC BY 2.0); credited in DATA.md.
"""
import math
import os
import sys

import numpy as np
from shapely.geometry import Point, Polygon, box
from shapely.ops import unary_union

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import facade_parts as F  # noqa: E402

OSM = "way/134521042"
Z0 = 9.6
O = np.array([-156.67, -129.31])
U = np.array([25.34, 0.46]) / math.hypot(25.34, 0.46)
V = np.array([-U[1], U[0]])

Y = 0.08     # wall face, just proud of the OSM wall line
REV = 0.4
GLASS = F.rgb(F.GLASS_COL)
LOUVRE = F.rgb("#3b3631")
DARK = F.rgb("#2c2824")
DOOR = F.rgb("#4a3020")
LEAD = F.rgb("#80868a")
RUBBLE = F.rgb("#957853")      # tower: clunch / fieldstone / ironstone rubble
QUOIN = F.rgb("#c9bd9e")       # Barnack-type quoins and dressings
AISLE = F.rgb("#a8936f")       # 19th-century coursed rubble of the aisles
DRESS = F.rgb("#c4b593")
SLATE = F.rgb("#5c6064")
IRON = F.rgb("#3a3631")
GILT = F.rgb("#a8863c")


def W(s, t):
    return O + s * U + t * V


# ------------------------------------------------------------------ helpers (wall frame: x along, y out, z up)

def P_(mat="flint", col=AISLE):
    return F.Parts(mat=mat, wall_col=col)


def frame_world(P, p0, d, name):
    T, N, C = P.arrays()
    if not len(T):
        return None
    M = P.mats()
    n = np.array([d[1], -d[0]])
    X = p0[0] + T[..., 0] * d[0] + T[..., 1] * n[0]
    Yw = p0[1] + T[..., 0] * d[1] + T[..., 1] * n[1]
    Wd = np.stack([X, Yw, Z0 + T[..., 2]], -1)
    Nw = np.stack([N[:, 0] * d[0] + N[:, 1] * n[0], N[:, 0] * d[1] + N[:, 1] * n[1], N[:, 2]], -1)
    g = np.cross(Wd[:, 1] - Wd[:, 0], Wd[:, 2] - Wd[:, 0])
    flip = (g * Nw).sum(1) < 0
    Wd[flip] = Wd[flip][:, ::-1]
    return {"name": name, "tris": Wd, "col": np.clip(C, 0, 1), "mat": M}


def lathe(P, x, y, prof, col, n=8, mat="stone"):
    a = math.pi / n + np.linspace(0, 2 * math.pi, n + 1)
    tris, nrm = [], []
    for (r0, z0), (r1, z1) in zip(prof[:-1], prof[1:]):
        dz, dr = z1 - z0, r1 - r0
        L = math.hypot(dz, dr) or 1.0
        for k in range(n):
            c0, s0, c1, s1 = math.cos(a[k]), math.sin(a[k]), math.cos(a[k + 1]), math.sin(a[k + 1])
            am = (a[k] + a[k + 1]) / 2
            nv = (math.cos(am) * dz / L, math.sin(am) * dz / L, -dr / L)
            p00, p01 = (x + r0 * c0, y + r0 * s0, z0), (x + r0 * c1, y + r0 * s1, z0)
            p11, p10 = (x + r1 * c1, y + r1 * s1, z1), (x + r1 * c0, y + r1 * s0, z1)
            if r0 > 1e-4:
                tris.append([p00, p01, p11]); nrm.append(nv)
            if r1 > 1e-4:
                tris.append([p00, p11, p10]); nrm.append(nv)
    if tris:
        P.add(tris, np.asarray(nrm, float), col, mat)


def round_head(xc, w, zb, zt, n=8):
    """Round-headed (semicircular) opening, apex at zt."""
    r = w / 2
    zs = zt - r
    a = np.linspace(0, math.pi, n + 1)
    return Polygon([(xc - r, zb), (xc + r, zb)] + list(zip(xc + r * np.cos(a), zs + r * np.sin(a))))


def pointed(xc, w, zb, zt, k=0.85, n=7):
    r = k * w
    h = math.sqrt(max(r * r - (r - w / 2) ** 2, 1e-6))
    zs = max(zb + 0.05, zt - h)
    x0, x1 = xc - w / 2, xc + w / 2
    a_end = math.acos((r - w / 2) / r)
    right = [(x1 - r + r * math.cos(a), zs + r * math.sin(a)) for a in np.linspace(0, a_end, n)]
    left = [(x0 + r - r * math.cos(a), zs + r * math.sin(a)) for a in np.linspace(a_end, 0, n)]
    return Polygon([(x0, zb), (x1, zb)] + right[:-1] + [(xc, zs + h)] + left[1:]), zs


def gothic_window(P, xc, w, zb, zt, lights=2, dress=DRESS, y=Y):
    """Victorian Decorated window: reveals, glass, mullions, pointed sub-arches, roundel/trefoil head, hood mould."""
    op, zs = pointed(xc, w, zb, zt)
    yg = y - REV
    P.sides_xz(op, yg, y, F.shade(dress, 0.75), inward=True, mat="stone")
    P.face_xz(op, yg, GLASS, mat="glass")
    strips = [op.difference(op.buffer(-0.08, join_style=2))]
    lw = w / lights
    sub_top = zs + min(0.55 * (zt - zs), 0.9 * lw)
    for i in range(lights):
        sub, _ = pointed(xc - w / 2 + lw * (i + 0.5), lw, zb, sub_top, k=0.8, n=4)
        strips.append(sub.difference(sub.buffer(-0.07, join_style=2)))
    head_r = min(0.28 * w, 0.42 * (zt - sub_top))
    if head_r > 0.12:
        c = Point(xc, sub_top + 0.12 + head_r * 0.85).buffer(head_r, 10)
        strips.append(c.difference(c.buffer(-0.07, 10)))
    P.slab(unary_union(strips).intersection(op), yg, yg + 0.13, dress, mat="stone")
    lab = op.buffer(0.14, join_style=2).difference(op).intersection(box(xc - w, zs - 0.3, xc + w, zt + 1))
    P.slab(lab, y, y + 0.09, dress, mat="stone")
    P.extrude_profile([(y - 0.05, zb - 0.15), (y + 0.13, zb - 0.15), (y + 0.13, zb - 0.08), (y - 0.05, zb + 0.03)],
                      xc - w / 2 - 0.1, xc + w / 2 + 0.1, dress, mat="stone")
    return op


def square_window(P, xc, w, zb, zt, lights=2, dress=DRESS, y=Y):
    """Square-headed Perpendicular clerestory window with mullions and a label."""
    op = box(xc - w / 2, zb, xc + w / 2, zt)
    yg = y - 0.3
    P.sides_xz(op, yg, y, F.shade(dress, 0.75), inward=True, mat="stone")
    P.face_xz(op, yg, GLASS, mat="glass")
    for i in range(1, lights):
        x = xc - w / 2 + w * i / lights
        P.box(x - 0.05, x + 0.05, yg, yg + 0.12, zb, zt, dress, mat="stone", bottom=False, top=False)
    P.extrude_profile([(y - 0.05, zt + 0.02), (y + 0.1, zt + 0.02), (y + 0.1, zt + 0.12), (y - 0.05, zt + 0.16)],
                      xc - w / 2 - 0.15, xc + w / 2 + 0.15, dress, mat="stone")
    P.extrude_profile([(y - 0.05, zb - 0.12), (y + 0.1, zb - 0.12), (y + 0.1, zb - 0.06), (y - 0.05, zb + 0.02)],
                      xc - w / 2 - 0.08, xc + w / 2 + 0.08, dress, mat="stone")
    return op


def saxon_light(P, xc, w, zb, zt, y=Y, depth=0.55, louvre=False):
    """Small round-headed light deep in the tower wall: splayed reveals, dark or louvred back."""
    op = round_head(xc, w, zb, zt)
    P.sides_xz(op, y - depth, y, F.shade(RUBBLE, 0.7), inward=True, mat="stone")
    P.face_xz(op, y - depth, LOUVRE if louvre else DARK, mat="timber" if louvre else "plain")
    if louvre:
        z = zb + 0.18
        while z < zt - w / 2:
            P.extrude_profile([(y - depth + 0.05, z), (y - depth + 0.2, z - 0.09), (y - depth + 0.2, z - 0.04),
                               (y - depth + 0.05, z + 0.06)], xc - w / 2, xc + w / 2, LOUVRE, mat="timber")
            z += 0.24
    ring = op.buffer(0.1, join_style=2).difference(op).intersection(box(xc - w, zt - w / 2 - 0.05, xc + w, zt + 1))
    P.slab(ring, y, y + 0.04, QUOIN, mat="stone")
    return op


def door(P, xc, w, h, y=Y, depth=0.5, dress=DRESS):
    op, zs = pointed(xc, w, 0, h, k=0.75)
    P.sides_xz(op, y - depth, y, F.shade(dress, 0.7), inward=True, skip_ground=True, mat="stone")
    P.face_xz(op, y - depth, DOOR, mat="timber")
    for k in range(2):
        ring = op.buffer(0.12 * (k + 1), join_style=2).difference(op.buffer(0.12 * k, join_style=2))
        ring = ring.intersection(box(xc - w, 0, xc + w, h + 2))
        P.slab(ring, y - depth * (1 - k) / 2, y - depth * (1 - k) / 2 + 0.07, dress, mat="stone")
    lab = op.buffer(0.38, join_style=2).difference(op.buffer(0.26, join_style=2))
    P.slab(lab.intersection(box(xc - w, zs - 0.3, xc + w, h + 1)), y, y + 0.08, dress, mat="stone")
    return op


def buttress(P, x, ztop, d0=0.6, bw=0.55, y=Y, col=AISLE):
    za = ztop * 0.5
    d1 = d0 * 0.6
    prof = [(y - 0.05, -0.6), (y + d0, -0.6), (y + d0, za), (y + d1, za + 0.3), (y + d1, ztop),
            (y - 0.05, ztop + d1 * 1.2)]
    P.extrude_profile(prof, x - bw / 2, x + bw / 2, col, mat="stone")
    P.extrude_profile([(y + d0 - 0.02, za - 0.02), (y + d0 + 0.05, za), (y + d1 + 0.05, za + 0.32),
                       (y + d1 - 0.02, za + 0.32)], x - bw / 2 - 0.02, x + bw / 2 + 0.02, DRESS, mat="stone")


def parapet(P, x0, x1, zp, zt, col=AISLE, thick=0.32, y=Y):
    g = box(x0, zp, x1, zt - 0.12)
    P.extrude_profile([(y - thick - 0.05, zt - 0.12), (y + 0.1, zt - 0.12), (y + 0.1, zt - 0.04),
                       (y - 0.12, zt), (y - thick - 0.05, zt)], x0, x1, DRESS, mat="stone")   # coping
    P.slab(g, y - thick, y, col, mat="flint")
    P.face_xz(g, y - thick, F.shade(col, 0.8), n=(0, -1, 0), mat="flint")
    P.extrude_profile([(y - 0.05, zp - 0.2), (y + 0.1, zp - 0.2), (y + 0.15, zp - 0.07), (y + 0.15, zp),
                       (y - 0.05, zp)], x0, x1, DRESS, mat="stone")   # string course under the parapet


def wall_face(P, x0, x1, top, holes, zfoot=-0.6, plinth=True, col=AISLE, mat="flint", y=Y, zbot=None):
    zb = zfoot if zbot is None else zbot
    g = Polygon([(x0, zb), (x1, zb)] + list(reversed(top))).buffer(0)
    if holes:
        g = g.difference(unary_union(holes))
    P.face_xz(g, y, col, mat=mat)
    if plinth and zbot is None:
        P.extrude_profile([(y - 0.05, zfoot), (y + 0.2, zfoot), (y + 0.2, 0.4), (y + 0.04, 0.58), (y - 0.05, 0.58)],
                          x0, x1, DRESS, mat="stone")


def coping(P, pts, y=Y, w=0.3, h=0.17):
    for (ax, az), (bx, bz) in zip(pts[:-1], pts[1:]):
        L = math.hypot(bx - ax, bz - az)
        nx, nz = -(bz - az) / L, (bx - ax) / L
        if nz < 0:
            nx, nz = -nx, -nz
        q = Polygon([(ax, az), (bx, bz), (bx + nx * h, bz + nz * h), (ax + nx * h, az + nz * h)])
        P.slab(q, y - w, y + 0.06, DRESS, mat="stone")


def cross(P, x, z, y=Y):
    g = unary_union([box(x - 0.06, z, x + 0.06, z + 0.75), box(x - 0.24, z + 0.42, x + 0.24, z + 0.54)])
    P.slab(g, y - 0.16, y + 0.06, DRESS, mat="stone")


class Model:
    def __init__(self):
        self.out, self.roof_t, self.roof_c = [], [], []

    def put(self, P, A, B, name):
        """A -> B in local (s, t), walked with the outside on the right."""
        a, b = W(*A), W(*B)
        d = (b - a) / np.linalg.norm(b - a)
        r = frame_world(P, a, d, "benet:" + name)
        if r is not None:
            self.out.append(r)

    def roof(self, quads, col):
        for q in quads:
            p = [(*W(s, t), Z0 + z) for s, t, z in q]
            for T in ([p[:3]] if len(p) == 3 else [[p[0], p[1], p[2]], [p[0], p[2], p[3]]]):
                T = np.asarray(T, float)
                if np.cross(T[1] - T[0], T[2] - T[0])[2] < 0:
                    T = T[::-1]
                self.roof_t += [T, T[::-1]]
                self.roof_c += [col, F.shade(col, 0.55)]

    def gable_roof(self, s0, s1, t0, t1, ze, tr, zr, col, ov=0.3, verge=0.2):
        k0, k1 = (zr - ze) / (tr - t0), (zr - ze) / (t1 - tr)
        a, b = s0 - verge, s1 + verge
        self.roof([[(a, t0 - ov, ze - k0 * ov), (b, t0 - ov, ze - k0 * ov), (b, tr, zr), (a, tr, zr)],
                   [(a, t1 + ov, ze - k1 * ov), (b, t1 + ov, ze - k1 * ov), (b, tr, zr), (a, tr, zr)]], col)

    def flat(self, s0, s1, t0, t1, z, col=LEAD):
        self.roof([[(s0, t0, z), (s1, t0, z), (s1, t1, z), (s0, t1, z)]], col)

    def done(self):
        if self.roof_t:
            self.out.append({"name": "benet:roofs", "tris": np.asarray(self.roof_t), "col": np.asarray(self.roof_c),
                             "mat": "plain"})
        return self.out


# ------------------------------------------------------------------ layout (s, t, z relative to Z0)

TW = (-1.0, 5.1, 5.3, 11.1, 20.1)    # tower s0, s1, t0, t1, top
SC1, SC2 = 10.8, 15.0                # tower string courses
S_W, S_C, S_E = 0.0, 17.1, 24.6      # aisle west walls, chancel arch, east end
T_SA, T_NV, T_NA0, T_NA = 5.3, 12.2, 11.1, 18.1   # south aisle / nave, nave / north aisle, north aisle start, N wall
SA_P = 6.0                           # south aisle parapet top (DSM 15.4-15.6)
NA = (5.8, 7.7, 14.6)                # north aisle eaves, ridge, ridge t (DSM ridge 17.3-17.4 at N -116)
CL = (9.4, 9.9, 11.1)                # clerestory wall top, parapet top, nave ridge (DSM 20.6-20.8)
CH = (6.6, 12.0, 7.2, 9.9, 9.3)      # chancel t0, t1, eaves, ridge, ridge t (DSM ridge 19.4-19.6)
SCH = (0.0, 6.6, 7.2, 9.6, 3.3)      # south chapel t0, t1, eaves, ridge, ridge t (DSM ridge 19.0-19.2)
VE = (17.1, 21.7, 12.0, 18.1, 5.4, 6.4)   # vestry s0, s1, t0, t1, eaves, ridge (DSM 15.9-16.0)
PO = (4.2, 9.6, 18.1, 22.0, 3.2, 5.1)     # north porch s0, s1, t0, t1, eaves, ridge (DSM 14.3-14.8)


def quoins_ls(P, L, z0, z1, y=Y):
    """Anglo-Saxon long-and-short quoins at both ends of a tower face: tall upright stones alternating with flat
    slabs running into the wall, proud of the rubble."""
    z, i = z0, 0
    while z < z1 - 0.15:
        if i % 2 == 0:
            h, wq = min(1.05, z1 - z), 0.34
        else:
            h, wq = 0.24, 0.78
        for a, b in ((-0.06, wq), (L - wq, L + 0.06)):
            P.box(a, b, y, y + 0.06, z + 0.01, z + h - 0.01, QUOIN, mat="stone", bottom=False)
        z += h
        i += 1


def belfry(P, L, y=Y):
    """Belfry stage of one tower face: baluster-shafted pair, flanking louvred lights, sound-holes, pilaster strip."""
    xc = L / 2
    holes = []
    zb, zt, wl = SC2 + 0.3, SC2 + 1.95, 0.52        # the pair
    gap = 0.3
    for s in (-1, 1):
        holes.append(saxon_light(P, xc + s * (wl + gap) / 2, wl, zb, zt, depth=0.75))
    # the dividing pier is cut through the wall face; the baluster stands in the middle of the wall thickness
    pier = box(xc - gap / 2, zb, xc + gap / 2, zt - wl / 2)
    holes.append(pier)
    yb = y - 0.38
    P.sides_xz(pier, y - 0.75, y, F.shade(RUBBLE, 0.7), inward=True, mat="stone")
    lathe(P, xc, yb, [(0.13, zb), (0.13, zb + 0.1), (0.09, zb + 0.18), (0.11, zb + 0.4), (0.15, zb + 0.62),
                      (0.11, zb + 0.84), (0.09, zb + 1.0), (0.12, zb + 1.08), (0.0, zb + 1.08)], QUOIN, n=8)
    P.box(xc - 0.17, xc + 0.17, yb - 0.17, yb + 0.17, zb + 1.08, zt - wl / 2 - 0.02, QUOIN, mat="stone")
    # through-stone impost: a long slab spanning the wall thickness, projecting in front of the face
    P.box(xc - 0.24, xc + 0.24, y - 0.75, y + 0.22, zt - wl / 2 - 0.02, zt - wl / 2 + 0.2, QUOIN, mat="stone")
    P.box(xc - 0.17, xc + 0.17, yb - 0.17, yb + 0.17, zb - 0.02, zb, QUOIN, mat="stone", bottom=False)
    # raised square label round the pair, and the pilaster strip rising from it
    x0, x1 = xc - wl - gap / 2 - 0.22, xc + wl + gap / 2 + 0.22
    lab = box(x0, zb - 0.12, x1, zt + 0.18).difference(box(x0 + 0.16, zb - 0.12, x1 - 0.16, zt + 0.02))
    P.slab(lab, y, y + 0.08, QUOIN, mat="stone")
    P.box(xc - 0.13, xc + 0.13, y, y + 0.07, zt + 0.18, TW[4] - 0.55, QUOIN, mat="stone", bottom=False)
    # flanking single lights and sound-holes
    for s in (-1, 1):
        xf = xc + s * (L * 0.31)
        holes.append(saxon_light(P, xf, 0.42, SC2 + 1.0, SC2 + 2.45, depth=0.6, louvre=True))
        c = Point(xf, SC2 + 3.25).buffer(0.15, 10)
        holes.append(c)
        P.sides_xz(c, y - 0.5, y, F.shade(RUBBLE, 0.6), inward=True, mat="stone")
        P.face_xz(c, y - 0.5, DARK, mat="plain")
        fr = box(xf - 0.3, SC2 + 2.95, xf + 0.3, SC2 + 3.55).difference(c)
        P.slab(fr, y, y + 0.05, QUOIN, mat="stone")
    return holes


def tower(M):
    s0, s1, t0, t1, H = TW
    corners = [(s0, t0), (s1, t0), (s1, t1), (s0, t1)]
    for i in range(4):
        A, B = corners[i], corners[(i + 1) % 4]
        L = math.dist(A, B)
        P = P_("flint", RUBBLE)
        xc = L / 2
        holes = belfry(P, L)
        if i in (0, 3):     # south and west: small round-headed lights in the lower and middle stages
            holes.append(saxon_light(P, xc, 0.4, SC1 + 0.9, SC1 + 2.1))
        if i == 3:
            holes.append(saxon_light(P, xc, 0.55, 2.9, 4.5))
            holes.append(saxon_light(P, xc, 0.45, 7.2, 8.5))
        g = box(-0.06, -0.6, L + 0.06, H - 0.3).difference(unary_union(holes))
        P.face_xz(g, Y, RUBBLE, mat="flint")
        quoins_ls(P, L, -0.3, H - 0.3)
        for zc in (SC1, SC2):
            P.extrude_profile([(Y - 0.05, zc - 0.16), (Y + 0.14, zc - 0.16), (Y + 0.14, zc - 0.04),
                               (Y + 0.06, zc + 0.02), (Y - 0.05, zc + 0.02)], -0.12, L + 0.12, QUOIN, mat="stone")
        # plain top with a lead-capped coping
        P.extrude_profile([(Y - 0.4, H - 0.3), (Y + 0.1, H - 0.3), (Y + 0.1, H - 0.08), (Y - 0.05, H),
                           (Y - 0.4, H)], -0.12, L + 0.12, F.shade(LEAD, 1.05), mat="plain")
        P.extrude_profile([(Y - 0.05, -0.6), (Y + 0.22, -0.6), (Y + 0.22, 0.35), (Y + 0.05, 0.5), (Y - 0.05, 0.5)],
                          -0.06, L + 0.06, QUOIN, mat="stone")
        M.put(P, A, B, "tower%d" % i)
    M.flat(s0, s1, t0, t1, H - 0.15)
    # weathervane cross (wrought iron) on a short post
    P = P_("plain", IRON)
    xm = (t1 - t0) / 2
    P.box(xm - 0.04, xm + 0.04, -0.04, 0.04, H - 0.15, H + 1.6, IRON, mat="plain")
    P.box(xm - 0.45, xm + 0.45, -0.025, 0.025, H + 0.95, H + 1.02, IRON, mat="plain")
    P.box(xm - 0.025, xm + 0.025, -0.45, 0.45, H + 0.95, H + 1.02, IRON, mat="plain")
    P.box(xm - 0.5, xm + 0.15, -0.015, 0.015, H + 1.25, H + 1.45, GILT, mat="plain")   # vane
    lathe(P, xm, 0, [(0.07, H + 1.6), (0.0, H + 1.75)], GILT, n=6, mat="plain")
    sm = (s0 + s1) / 2
    M.put(P, (sm, t0), (sm, t1), "vane")


def north_side(M):
    ze, zr, tr = NA
    # north aisle north wall (Bene't Street side), porch in the middle bay
    P = P_()
    L = S_C
    holes = [gothic_window(P, x, 1.5, 1.3, 4.3, 2) for x in (L - 2.3, L - 5.9, 2.1)]
    wall_face(P, 0, L, [(0, ze), (L, ze)], holes)
    P.extrude_profile([(Y - 0.05, ze - 0.2), (Y + 0.16, ze - 0.2), (Y + 0.16, ze), (Y - 0.05, ze)], -0.1, L + 0.1,
                      DRESS, mat="stone")
    for x in (0.35, 4.0, L - 4.1, L - 0.3):
        buttress(P, x, ze - 1.3)
    M.put(P, (S_C, T_NA), (0, T_NA), "naisle_n")
    # north aisle west gable beside the tower (three-light window)
    P = P_()
    L = T_NA - T_NA0
    xr = T_NA - tr
    top = [(0, ze), (xr, zr), (L, ze)]
    wall_face(P, 0, L, top, [gothic_window(P, xr, 1.9, 1.5, 5.2, 3)])
    coping(P, top)
    cross(P, xr, zr + 0.08)
    M.put(P, (0, T_NA), (0, T_NA0), "naisle_w")
    # north aisle east gable above the vestry roof
    P = P_()
    top = [(0, ze), (tr - T_NA0, zr), (L, ze)]
    wall_face(P, 0, L, top, [], zbot=VE[4] - 0.3)
    coping(P, top)
    M.put(P, (S_C, T_NA0), (S_C, T_NA), "naisle_e")
    M.gable_roof(0, S_C, T_NA0, T_NA, ze, tr, zr, SLATE, ov=0.0, verge=0.2)
    M.roof([[(-0.2, T_NA, ze), (S_C + 0.2, T_NA, ze), (S_C + 0.2, T_NA + 0.3, ze - 0.16),
             (-0.2, T_NA + 0.3, ze - 0.16)]], SLATE)
    # vestry
    s0, s1, t0, t1, vze, vzr = VE
    vtr = (t0 + t1) / 2
    P = P_()
    wall_face(P, 0, s1 - s0, [(0, vze), (s1 - s0, vze)], [gothic_window(P, (s1 - s0) / 2, 1.1, 1.5, 3.9, 2)])
    M.put(P, (s1, t1), (s0, t1), "vestry_n")
    P = P_()
    top = [(0, vze), (vtr - t0, vzr), (t1 - t0, vze)]
    wall_face(P, 0, t1 - t0, top, [door(P, 1.5, 0.95, 2.4)])
    coping(P, top)
    M.put(P, (s1, t0), (s1, t1), "vestry_e")
    M.gable_roof(s0, s1, t0, t1, vze, vtr, vzr, SLATE, ov=0.25, verge=0.15)
    # north porch (ridge runs north-south)
    s0, s1, t0, t1, pze, pzr = PO
    sm = (s0 + s1) / 2
    for (A, B, nm) in (((s1, t0), (s1, t1), "porch_e"), ((s0, t1), (s0, t0), "porch_w")):
        P = P_()
        Lp = t1 - t0
        wall_face(P, 0, Lp, [(0, pze), (Lp, pze)], [gothic_window(P, Lp / 2, 0.5, 1.2, 2.5, 1)])
        M.put(P, A, B, nm)
    P = P_()
    Lp = s1 - s0
    top = [(0, pze), (Lp / 2, pzr), (Lp, pze)]
    holes = [door(P, Lp / 2, 1.5, 3.0, depth=0.45)]
    tre = unary_union([Point(Lp / 2 + dx, pze + 0.95 + dz).buffer(0.17, 8)
                       for dx, dz in ((-0.15, 0), (0.15, 0), (0, 0.24))])
    holes.append(tre)
    P.sides_xz(tre, Y - 0.25, Y, F.shade(DRESS, 0.7), inward=True, mat="stone")
    P.face_xz(tre, Y - 0.25, DARK, mat="plain")
    wall_face(P, 0, Lp, top, holes)
    coping(P, top)
    cross(P, Lp / 2, pzr + 0.08)
    for x in (0.25, Lp - 0.25):
        buttress(P, x, pze - 0.6, d0=0.5, bw=0.45)
    M.put(P, (s1, t1), (s0, t1), "porch_n")
    k = (pzr - pze) / (Lp / 2)
    M.roof([[(s0 - 0.25, t0, pze - 0.25 * k), (s0 - 0.25, t1 + 0.2, pze - 0.25 * k), (sm, t1 + 0.2, pzr),
             (sm, t0, pzr)],
            [(s1 + 0.25, t0, pze - 0.25 * k), (s1 + 0.25, t1 + 0.2, pze - 0.25 * k), (sm, t1 + 0.2, pzr),
             (sm, t0, pzr)]], SLATE)


def south_side(M):
    # south aisle south wall with parapet
    P = P_()
    L = S_C
    zp = SA_P - 0.75
    holes = [gothic_window(P, x, 1.6, 1.3, 4.4, 2) for x in (2.6, 7.2, 11.6, 15.3)]
    wall_face(P, 0, L, [(0, zp), (L, zp)], holes)
    parapet(P, -0.08, L, zp, SA_P)
    for x in (0.35, 4.9, 9.4, 13.5, L - 0.3):
        buttress(P, x, zp - 1.0)
    M.put(P, (0, 0), (S_C, 0), "saisle_s")
    # south aisle west end
    P = P_()
    L = T_SA
    wall_face(P, 0, L, [(0, zp), (L, zp)], [gothic_window(P, L / 2, 1.3, 1.5, 4.3, 2)])
    parapet(P, 0, L + 0.08, zp, SA_P)
    M.put(P, (0, T_SA), (0, 0), "saisle_w")
    M.flat(0, S_C, 0, T_SA, SA_P - 0.3)
    # south chapel / gallery block: south wall (two storeys of windows), east gable
    t0, t1, ze, zr, tr = SCH
    P = P_()
    L = S_E - S_C
    holes = [square_window(P, x, 1.4, 1.2, 2.9, 2) for x in (2.2, 5.4)]
    holes += [square_window(P, x, 1.4, 4.3, 5.9, 2) for x in (2.2, 5.4)]
    wall_face(P, 0, L, [(0, ze), (L, ze)], holes)
    P.extrude_profile([(Y - 0.05, 3.5), (Y + 0.12, 3.5), (Y + 0.16, 3.66), (Y - 0.05, 3.7)], -0.08, L + 0.08,
                      DRESS, mat="stone")
    P.extrude_profile([(Y - 0.05, ze - 0.2), (Y + 0.16, ze - 0.2), (Y + 0.16, ze), (Y - 0.05, ze)], -0.1, L + 0.1,
                      DRESS, mat="stone")
    M.put(P, (S_C, 0), (S_E, 0), "chapel_s")
    M.gable_roof(S_C, S_E, t0, t1, ze, tr, zr, SLATE, ov=0.25, verge=0.12)


def east_end(M):
    ct0, ct1, cze, czr, ctr = CH
    t0, t1, ze, zr, tr = SCH
    P = P_()
    L = T_NV - 0.2
    top = [(0, ze), (tr, zr), (t1, ze), (ct0, cze), (ctr, czr), (ct1, cze), (L, cze)]
    holes = [gothic_window(P, ctr, 2.4, 2.0, 6.6, 3), square_window(P, tr, 1.4, 1.3, 2.9, 2),
             square_window(P, tr, 1.4, 4.3, 5.9, 2)]
    wall_face(P, 0, L, top, holes)
    coping(P, [(0, ze), (tr, zr), (t1, ze)])
    coping(P, [(ct0, cze), (ctr, czr), (ct1, cze)])
    cross(P, ctr, czr + 0.08)
    for x in (0.3, ct1 - 0.1):
        buttress(P, x, 4.8, d0=0.6)
    M.put(P, (S_E, 0), (S_E, L), "east")
    # chancel north wall above the vestry
    P = P_()
    wall_face(P, 0, S_E - VE[1], [(0, cze), (S_E - VE[1], cze)],
              [gothic_window(P, (S_E - VE[1]) / 2, 1.1, 1.6, 4.4, 2)])
    M.put(P, (S_E, ct1), (VE[1], ct1), "chancel_n_e")
    P = P_()
    P.face_xz(box(0, VE[4] - 0.4, VE[1] - S_C, cze), Y, AISLE, mat="flint")
    M.put(P, (VE[1], ct1), (S_C, ct1), "chancel_n")
    M.gable_roof(S_C, S_E, ct0, ct1, cze, ctr, czr, SLATE, ov=0.25, verge=0.12)


def nave(M):
    zw, zpt, zr = CL
    tr = (T_SA + T_NV) / 2
    ze_n = NA[0] + (NA[1] - NA[0]) * (1 - (T_NV - NA[2]) / (T_NA - NA[2]))   # aisle roof at the clerestory
    for (A, B, z0, nm) in (((TW[1], T_SA), (S_C, T_SA), SA_P - 0.35, "clerestory_s"),
                           ((S_C, T_NV), (TW[1], T_NV), ze_n - 0.2, "clerestory_n")):
        P = P_()
        L = math.dist(A, B)
        holes = [square_window(P, x, 1.3, z0 + 1.0, zw - 0.9, 2) for x in (2.0, 6.0, 10.0)]
        wall_face(P, 0, L, [(0, zw - 0.6), (L, zw - 0.6)], holes, zbot=z0)
        parapet(P, 0, L, zw - 0.6, zpt)
        M.put(P, A, B, nm)
    # east gable of the nave above the chancel / chapel roofs, west gable stub north of the tower
    P = P_()
    L = T_NV - T_SA
    top = [(0, zpt), (tr - T_SA, zr), (L, zpt)]
    wall_face(P, 0, L, top, [], zbot=CH[2])
    coping(P, top)
    cross(P, tr - T_SA, zr + 0.05)
    M.put(P, (S_C, T_SA), (S_C, T_NV), "nave_e")
    P = P_()
    wall_face(P, 0, T_NV - TW[3], [(0, zw), (T_NV - TW[3], zw)], [], zbot=ze_n - 0.6)
    M.put(P, (TW[1], T_NV), (TW[1], TW[3]), "nave_w")
    M.gable_roof(TW[1], S_C, T_SA, T_NV, zw - 0.05, tr, zr, LEAD, ov=0.0, verge=0.0)


def benet(walls=None):
    M = Model()
    tower(M)
    nave(M)
    north_side(M)
    south_side(M)
    east_end(M)
    return M.done()


BUILDS = {OSM: benet}
ELEMENTS = {}          # not in data/annotations/market_square/walls.json
HIDE_TILE = [OSM]      # complete closed exterior over the OSM footprint

if __name__ == "__main__":
    items = benet([])
    n = sum(len(i["tris"]) for i in items)
    zs = np.concatenate([np.asarray(i["tris"])[..., 2].ravel() for i in items])
    print(OSM, "tris", n, "max z", round(float(zs.max()), 2), "min z", round(float(zs.min()), 2))
