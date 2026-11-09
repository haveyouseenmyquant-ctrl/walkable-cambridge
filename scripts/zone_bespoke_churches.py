"""Bespoke geometry for two medieval churches in the Market Square zone (session 34):
St Edward King and Martyr (OSM way/26344576, Peas Hill / St Edward's Passage) and St Michael's (way/95406730,
Trinity Street). zone_build.load_bespoke() picks up BUILDS / HIDE_TILE.

Both models follow the OSM footprints (= tile collision); heights come from the LiDAR DSM (data/lidar/dsm_1m.tif,
1 m) sampled over each footprint, ground from the DTM. Nothing stands more than ~0.3 m above the DSM.

St Edward King and Martyr (Z0 = 10.1 m; frame s east along the south wall from its SW corner, t north):
- west tower s -2.75..2.62, t 2.05..9.95: rubble/clunch lower stage, rendered buff upper stages, two-light belfry
  openings on every face, red-brick battlements; top 19.1 (DSM 29.2-29.4 -> 19.1-19.3);
- nave + aisles under one steep tiled roof s 2.62..14.5, eaves 4.8 (DSM 14.9-15.0), ridge 11.9 at t 6.3
  (DSM 21.9-22.0), brick east gable over the chancel roof;
- chancel s 14.5..23.86, t 3.5..10.5, eaves 5.9, ridge 10.1 at t 7.0 (DSM 20.2), five-light east window with
  flowing (Decorated) tracery;
- south chapel (t 0..3.5) flat lead roof behind a parapet at 5.6 (DSM 15.6-15.7); north chapel / vestry block
  (t 10.5..18.21) flat roof + parapet at 6.0 (DSM 16.0-16.1) with a small east-west gable, ridge 6.9 (DSM 17.0);
- lean-to in the angle south of the tower; buttresses, plinths, three-light Decorated windows with reveals,
  mullions, sub-arches, a roundel in the head and hood moulds; north door from St Edward's Passage, east door.
St Michael's (Z0 = 9.5 m; frame s east along the south wall from the SW corner):
- one wide slate roof over nave, chancel and aisles, ridge 10.95 at t 9.3 (DSM 20.4-20.5), plain parapet at 5.7 on
  the south (DSM 15.1-15.3), eaves 5.7 on the north (DSM 15.2-15.4);
- south-west tower s 0..6.3, t 0..6.0 (DSM plateau 25.5-25.9 -> 16.4): flint/clunch rubble, string courses,
  two-light belfry openings, plain parapet with a flagpole;
- west (Trinity Street) gable with a four-light window, east gable with a five-light window, aisle windows
  between buttresses, gabled north porch with a pointed doorway (ridge 4.8, DSM 14.3).

References (visual only; no held-out benchmark photos used):
- Commons "St Edward King and Martyr, Cambridge (exterior).jpg" (Magnus Manske, CC BY-SA 3.0) and
  "Church of St Edward, King and Martyr - geograph.org.uk - 5524920.jpg" (N Chadwick, CC BY-SA 2.0), already in
  data/raw/commons_ref and credited in DATA.md;
- Commons "Church of St Michael, Trinity St - geograph.org.uk - 3803723.jpg" (N Chadwick, CC BY-SA 2.0) ->
  data/raw/commons_ref/St_Michael_Trinity_St_geograph_3803723.jpg;
- Commons "Cambridge - Trinity Street - View East on Churchyard of St Michael's Church - Michaelhouse.jpg"
  (Txllxt TxllxT, CC BY-SA 4.0) -> data/raw/commons_ref/St_Michael_Trinity_St_view_east_churchyard.jpg.
"""
import math
import os
import sys

import numpy as np
from shapely.geometry import Point, Polygon, box
from shapely.ops import unary_union

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import facade_parts as F  # noqa: E402

Y = 0.08     # wall face, just proud of the OSM wall line
REV = 0.4    # window reveal depth
GLASS = F.rgb(F.GLASS_COL)
LOUVRE = F.rgb("#3e3934")
DOOR = F.rgb("#4a3020")
LEAD = F.rgb("#80868a")


class Pal:
    def __init__(self, wall, dress, roof, wall_mat="stone"):
        self.wall = F.rgb(wall)
        self.dress = F.rgb(dress)
        self.dark = F.shade(self.dress, 0.7)
        self.roof = F.rgb(roof)
        self.mat = wall_mat


# ------------------------------------------------------------------ elements (wall frame: x along, y out, z up)

def _note(P, kind, x):
    """Record an emitted opening (kind, x along the wall) on the Parts object for ELEMENTS."""
    if not hasattr(P, "openings"):
        P.openings = []
    P.openings.append((kind, x))


def pointed(xc, w, zb, zt, k=0.85, n=7):
    """Two-centred pointed arch opening (radius k*w), apex at zt."""
    r = k * w
    h = math.sqrt(max(r * r - (r - w / 2) ** 2, 1e-6))
    zs = max(zb + 0.05, zt - h)
    x0, x1 = xc - w / 2, xc + w / 2
    a_end = math.acos((r - w / 2) / r)
    right = [(x1 - r + r * math.cos(a), zs + r * math.sin(a)) for a in np.linspace(0, a_end, n)]
    left = [(x0 + r - r * math.cos(a), zs + r * math.sin(a)) for a in np.linspace(a_end, 0, n)]
    pts = [(x0, zb), (x1, zb)] + right[:-1] + [(xc, zs + h)] + left[1:]
    return Polygon(pts), zs


def window(P, pal, xc, w, zb, zt, lights=3, louvre=False, y=Y):
    """Recessed Decorated window: reveals, glass, mullions, pointed sub-arches per light, a roundel in the head,
    hood mould and sill. Returns the opening polygon."""
    op, zs = pointed(xc, w, zb, zt)
    _note(P, "window", xc)
    yg = y - REV
    P.sides_xz(op, yg, y, pal.dark, inward=True, mat="stone")
    P.face_xz(op, yg, LOUVRE if louvre else GLASS, mat="trim" if louvre else "glass")
    strips = [op.difference(op.buffer(-0.08, join_style=2))]
    lw = w / lights
    sub_top = zs + min(0.55 * (zt - zs), 0.9 * lw)
    for i in range(lights):
        sub, _ = pointed(xc - w / 2 + lw * (i + 0.5), lw, zb, sub_top, k=0.8, n=4)
        strips.append(sub.difference(sub.buffer(-0.07, join_style=2)))
    head_r = min(0.3 * w, 0.42 * (zt - sub_top))
    if lights >= 2 and head_r > 0.15:
        c = Point(xc, sub_top + 0.15 + head_r * 0.85).buffer(head_r, 10)
        strips.append(c.difference(c.buffer(-0.07, 10)))
        if lights >= 4:   # flowing tracery: two smaller roundels either side
            for s in (-1, 1):
                c2 = Point(xc + s * w * 0.27, sub_top + 0.1 + head_r * 0.45).buffer(head_r * 0.5, 8)
                strips.append(c2.difference(c2.buffer(-0.06, 8)))
    tr = unary_union(strips).intersection(op)
    if louvre:
        z = zb + 0.2
        while z < zs:
            P.extrude_profile([(yg + 0.05, z), (yg + 0.22, z - 0.1), (yg + 0.22, z - 0.05), (yg + 0.05, z + 0.07)],
                              xc - w / 2, xc + w / 2, LOUVRE, mat="timber")
            z += 0.28
    P.slab(tr, yg, yg + 0.13, pal.dress, mat="stone")
    lab = op.buffer(0.15, join_style=2).difference(op).intersection(box(xc - w, zs - 0.35, xc + w, zt + 1))
    P.slab(lab, y, y + 0.09, pal.dress, mat="stone")
    P.extrude_profile([(y - 0.05, zb - 0.16), (y + 0.14, zb - 0.16), (y + 0.14, zb - 0.09), (y - 0.05, zb + 0.03)],
                      xc - w / 2 - 0.1, xc + w / 2 + 0.1, pal.dress, mat="stone")
    return op


def door(P, pal, xc, w, h, y=Y, depth=0.5):
    op, zs = pointed(xc, w, 0, h, k=0.75)
    _note(P, "door", xc)
    P.sides_xz(op, y - depth, y, pal.dark, inward=True, skip_ground=True, mat="stone")
    P.face_xz(op, y - depth, DOOR, mat="timber")
    for k in range(2):
        ring = op.buffer(0.13 * (k + 1), join_style=2).difference(op.buffer(0.13 * k, join_style=2))
        ring = ring.intersection(box(xc - w, 0, xc + w, h + 2))
        P.slab(ring, y - depth * (1 - k) / 2, y - depth * (1 - k) / 2 + 0.07, pal.dress, mat="stone")
    lab = op.buffer(0.42, join_style=2).difference(op.buffer(0.28, join_style=2))
    P.slab(lab.intersection(box(xc - w, zs - 0.3, xc + w, h + 1)), y, y + 0.08, pal.dress, mat="stone")
    return op


def buttress(P, pal, x, ztop, d0=0.75, bw=0.6, y=Y):
    za = ztop * 0.5
    d1 = d0 * 0.6
    prof = [(y - 0.05, -0.6), (y + d0, -0.6), (y + d0, za), (y + d1, za + 0.3), (y + d1, ztop),
            (y - 0.05, ztop + d1 * 1.2)]
    P.extrude_profile(prof, x - bw / 2, x + bw / 2, pal.dress if pal.mat == "render" else pal.wall, mat="stone")


def parapet(P, pal, x0, x1, zp, zt, embattled=False, col=None, mat="stone", thick=0.35, y=Y):
    col = pal.wall if col is None else col
    if embattled:
        zc = zp + 0.5 * (zt - zp)
        parts = [box(x0, zp, x1, zc)]
        mer, gap = 0.7, 0.5
        n = max(1, int((x1 - x0 + gap) // (mer + gap)))
        pad = (x1 - x0 - n * mer - (n - 1) * gap) / 2
        parts += [box(x0 + pad + i * (mer + gap), zc - 0.01, x0 + pad + i * (mer + gap) + mer, zt) for i in range(n)]
        g = unary_union(parts)
    else:
        g = box(x0, zp, x1, zt - 0.12)
        P.extrude_profile([(y - thick - 0.05, zt - 0.12), (y + 0.1, zt - 0.12), (y + 0.1, zt - 0.04),
                           (y - 0.12, zt), (y - thick - 0.05, zt)], x0, x1, pal.dress, mat="stone")   # coping
    P.slab(g, y - thick, y, col, mat=mat)
    P.face_xz(g, y - thick, F.shade(col, 0.8), n=(0, -1, 0), mat=mat)
    P.extrude_profile([(y - 0.05, zp - 0.22), (y + 0.1, zp - 0.22), (y + 0.16, zp - 0.08), (y + 0.16, zp),
                       (y - 0.05, zp)], x0, x1, pal.dress, mat="stone")   # string course under the parapet


def wall_face(P, pal, x0, x1, top, holes, zfoot=-0.6, plinth=True, col=None, mat=None, y=Y, zbot=None):
    """Wall polygon from zfoot up to the polyline `top` [(x, z), ...] running x0 -> x1."""
    col = pal.wall if col is None else col
    zb = zfoot if zbot is None else zbot
    g = Polygon([(x0, zb), (x1, zb)] + list(reversed(top))).buffer(0)
    if holes:
        g = g.difference(unary_union(holes))
    P.face_xz(g, y, col, mat=mat or pal.mat)
    if plinth and zbot is None:
        P.extrude_profile([(y - 0.05, zfoot), (y + 0.22, zfoot), (y + 0.22, 0.4), (y + 0.04, 0.6), (y - 0.05, 0.6)],
                          x0, x1, pal.dress, mat="stone")


def coping(P, pal, pts, y=Y, w=0.3, h=0.18):
    """Stone coping along a gable's raking edges (polyline in xz)."""
    for (ax, az), (bx, bz) in zip(pts[:-1], pts[1:]):
        L = math.hypot(bx - ax, bz - az)
        nx, nz = -(bz - az) / L, (bx - ax) / L
        if nz < 0:
            nx, nz = -nx, -nz
        q = Polygon([(ax, az), (bx, bz), (bx + nx * h, bz + nz * h), (ax + nx * h, az + nz * h)])
        P.slab(q, y - w, y + 0.06, pal.dress, mat="stone")


def cross(P, pal, x, z, y=Y):
    g = unary_union([box(x - 0.06, z, x + 0.06, z + 0.8), box(x - 0.25, z + 0.45, x + 0.25, z + 0.57)])
    P.slab(g, y - 0.18, y + 0.06, pal.dress, mat="stone")


# ------------------------------------------------------------------ frames

def frame_world(P, p0, d, name, z0, col_mat=None):
    T, N, C = P.arrays()
    if not len(T):
        return None
    M = P.mats()
    n = np.array([d[1], -d[0]])
    X = p0[0] + T[..., 0] * d[0] + T[..., 1] * n[0]
    Yw = p0[1] + T[..., 0] * d[1] + T[..., 1] * n[1]
    W = np.stack([X, Yw, z0 + T[..., 2]], -1)
    Nw = np.stack([N[:, 0] * d[0] + N[:, 1] * n[0], N[:, 0] * d[1] + N[:, 1] * n[1], N[:, 2]], -1)
    g = np.cross(W[:, 1] - W[:, 0], W[:, 2] - W[:, 0])
    flip = (g * Nw).sum(1) < 0
    W[flip] = W[flip][:, ::-1]
    return {"name": name, "tris": W, "col": np.clip(C, 0, 1), "mat": M}


_LAST = [None]   # the most recently finished Church (for ELEMENTS)


class Church:
    def __init__(self, key, O, U, Z0, pal):
        self.key, self.O, self.Z0, self.pal = key, np.asarray(O, float), Z0, pal
        self.U = np.asarray(U, float) / np.linalg.norm(U)
        self.V = np.array([-self.U[1], self.U[0]])
        self.out = []
        self.roof_t, self.roof_c = [], []
        self.openings = []   # (kind, world xy) of every window/door emitted

    def w(self, s, t):
        return self.O + s * self.U + t * self.V

    def P(self):
        return F.Parts(mat=self.pal.mat, wall_col=self.pal.wall)

    def put(self, P, A, B, name):
        """A -> B in local (s, t), walked with the outside on the right."""
        a, b = self.w(*A), self.w(*B)
        d = (b - a) / np.linalg.norm(b - a)
        r = frame_world(P, a, d, "%s:%s" % (self.key, name), self.Z0)
        for kind, x in getattr(P, "openings", []):
            self.openings.append((kind, a + x * d))
        if r is not None:
            self.out.append(r)

    def roof(self, quads, col, under=None):
        """quads: [(s, t, z) x 3 or 4] in local; oriented upward; a darker flipped copy closes the underside."""
        for q in quads:
            p = [(*self.w(s, t), self.Z0 + z) for s, t, z in q]
            tris = [p[:3]] if len(p) == 3 else [[p[0], p[1], p[2]], [p[0], p[2], p[3]]]
            for T in tris:
                T = np.asarray(T, float)
                g = np.cross(T[1] - T[0], T[2] - T[0])
                if g[2] < 0:
                    T = T[::-1]
                self.roof_t.append(T)
                self.roof_c.append(col)
                self.roof_t.append(T[::-1])
                self.roof_c.append(F.shade(col, 0.55) if under is None else under)

    def gable_roof(self, s0, s1, t0, t1, te, ze, tr, zr, col, ov=0.3, verge=0.2):
        """Two planes: eaves at t0/t1 (height ze at the wall line, extended by ov), ridge at tr height zr."""
        k0 = (zr - ze) / (tr - t0)
        k1 = (zr - ze) / (t1 - tr)
        a, b = s0 - verge, s1 + verge
        self.roof([[(a, t0 - ov, ze - k0 * ov), (b, t0 - ov, ze - k0 * ov), (b, tr, zr), (a, tr, zr)],
                   [(a, t1 + ov, ze - k1 * ov), (b, t1 + ov, ze - k1 * ov), (b, tr, zr), (a, tr, zr)]], col)

    def flat(self, s0, s1, t0, t1, z, col=LEAD):
        self.roof([[(s0, t0, z), (s1, t0, z), (s1, t1, z), (s0, t1, z)]], col)

    def done(self):
        if self.roof_t:
            self.out.append({"name": self.key + ":roofs", "tris": np.asarray(self.roof_t), "col":
                             np.asarray(self.roof_c), "mat": "plain"})
        _LAST[0] = self
        return self.out


def gable_top(x0, x1, ze, xr, zr):
    return [(x0, ze), (xr, zr), (x1, ze)]


# ------------------------------------------------------------------ St Edward King and Martyr

SE_OSM = "way/26344576"


def st_edward(walls=None):
    pal = Pal("#a8997b", "#cdc0a0", "#6d625a")
    render = F.rgb("#cbb98f")
    brick = F.rgb("#a5543c")
    C = Church("stedward", (-143.26, -22.29), (23.80, 1.60), 10.1, pal)
    ZE, ZR, TR = 4.8, 11.9, 6.3        # nave + aisles eaves, ridge, ridge line t
    S_N, S_C, S_E = 2.62, 14.5, 23.86  # nave west gable, chancel / nave junction, east end
    T_N, T_NC = 12.57, 18.21
    CH = (3.5, 10.5, 5.9, 10.1, 7.0)   # chancel t0, t1, eaves, ridge, ridge t
    Z_SCH, Z_NCH = 5.6, 6.0           # parapet tops: south chapel, north block
    NG = (15.6, 18.21, 5.6, 6.9, 16.9)  # north block gable: t0, t1, eaves, ridge, ridge t
    TW = (-1.9, 3.2, 2.05, 8.9, 19.1)   # LiDAR tower (upper stages); the lower stage reaches the OSM west face
    TW_LOW = (-2.75, 9.6)               # lower stage west face s, set-off height (DSM 19.7-20.3 west of the tower)

    def nave_z(t):
        return ZR - (ZR - ZE) * abs(t - TR) / (TR if t < TR else T_N - TR)

    # --- south wall (wall 3): lean-to | aisle | south chapel
    P = C.P()
    # layout from the square-on south elevation (annotation way/26344576:3, session 53): a 3-light aisle window,
    # the tall 5-light south-chapel window, a smaller 3-light window and a pointed doorway at the east end
    holes = [window(P, pal, 6.5, 2.2, 1.2, 4.1, 3),
             window(P, pal, 14.2, 3.2, 1.3, 4.4, 5),
             window(P, pal, 19.9, 1.5, 1.3, 3.5, 3),
             door(P, pal, 22.6, 1.1, 2.4)]
    top = [(-0.0, 4.4), (S_N, 4.4), (S_N, ZE), (S_C, ZE), (S_C, Z_SCH - 0.95), (S_E, Z_SCH - 0.95)]
    wall_face(P, pal, 0.0, S_E, top, holes)
    parapet(P, pal, S_C, S_E + 0.08, Z_SCH - 0.95, Z_SCH)
    for x in (S_N + 0.3, 10.0, 17.4, 21.4, S_E - 0.3):
        buttress(P, pal, x, (ZE if x < S_C else Z_SCH) - 1.3)
    C.put(P, (0, 0), (S_E, 0), "south")
    # --- east wall (wall 4): south chapel end | chancel gable | north block (parapet) | small gable
    P = C.P()
    ct0, ct1, cze, czr, ctr = CH
    holes = [window(P, pal, 1.75, 1.6, 1.4, 4.4, 3),
             window(P, pal, ctr, 3.8, 1.6, 8.6, 5),
             window(P, pal, 13.0, 1.8, 1.4, 4.6, 3),
             window(P, pal, 16.4, 0.8, 1.2, 2.4, 2)]   # the vestry's small window (no east door in the photos)
    top = [(0, Z_SCH - 0.95), (ct0, Z_SCH - 0.95), (ct0, cze), (ctr, czr), (ct1, cze), (ct1, Z_NCH - 0.95),
           (NG[0], Z_NCH - 0.95), (NG[0], NG[2]), (NG[4], NG[3]), (NG[1], NG[2])]
    wall_face(P, pal, 0, T_NC, top, holes)
    parapet(P, pal, -0.08, ct0, Z_SCH - 0.95, Z_SCH)
    parapet(P, pal, ct1, NG[0], Z_NCH - 0.95, Z_NCH)
    coping(P, pal, [(ct0, cze), (ctr, czr), (ct1, cze)])
    coping(P, pal, [(NG[0], NG[2]), (NG[4], NG[3]), (NG[1], NG[2])])
    cross(P, pal, ctr, czr + 0.1)
    for x in (0.25, ct0 - 0.1, ct1 + 0.1, T_NC - 0.25):
        buttress(P, pal, x, 3.6, d0=0.65)
    C.put(P, (S_E, 0), (S_E, T_NC), "east")
    # --- north block: north wall (wall 5) and west wall (wall 6)
    P = C.P()
    L = S_E - 14.55
    holes = [window(P, pal, 2.6, 1.3, 1.5, 4.3, 2), window(P, pal, 6.6, 1.3, 1.5, 4.3, 2)]
    wall_face(P, pal, 0, L, [(0, NG[2]), (L, NG[2])], holes)
    P.extrude_profile([(Y - 0.05, NG[2] - 0.2), (Y + 0.15, NG[2] - 0.2), (Y + 0.15, NG[2]), (Y - 0.05, NG[2])],
                      -0.1, L + 0.1, pal.dress, mat="stone")
    C.put(P, (S_E, T_NC), (14.55, T_NC), "north_chapel")
    P = C.P()
    L = T_NC - T_N
    xg = T_NC - NG[0]   # from this wall's start (t 18.21) to the gable foot
    holes = [window(P, pal, 3.9, 1.2, 1.5, 4.2, 2)]
    top = [(0, NG[2]), (T_NC - NG[4], NG[3]), (xg, NG[2]), (xg, Z_NCH - 0.95), (L, Z_NCH - 0.95)]
    wall_face(P, pal, 0, L, top, holes)
    parapet(P, pal, xg, L + 0.08, Z_NCH - 0.95, Z_NCH)
    coping(P, pal, [(0, NG[2]), (T_NC - NG[4], NG[3]), (xg, NG[2])])
    C.put(P, (14.55, T_NC), (14.55, T_N), "north_chapel_w")
    # --- north aisle (wall 7) with the north door from St Edward's Passage
    P = C.P()
    L = 14.55 - S_N
    holes = [door(P, pal, L - 2.0, 1.3, 2.7)]
    for xc in (2.4, 6.4):
        holes.append(window(P, pal, xc, 1.7, 1.2, 4.1, 3))
    wall_face(P, pal, 0, L, [(0, ZE), (L, ZE)], holes)
    for x in (0.4, 4.4, 8.4, L - 0.3):
        buttress(P, pal, x, ZE - 1.3)
    C.put(P, (14.55, T_N), (S_N, T_N), "north")
    # --- west end of the north aisle (wall 8) and the nave west gable either side of the tower
    P = C.P()
    top = [(0, ZE), (T_N - TW[3], nave_z(TW[3]))]
    wall_face(P, pal, 0, T_N - TW[3], top, [window(P, pal, 1.3, 1.0, 1.4, 3.6, 2)])
    C.put(P, (S_N, T_N), (S_N, TW[3]), "west_n")
    P = C.P()
    top = [(0, nave_z(TW[2])), (TW[2], ZE)]
    wall_face(P, pal, 0, TW[2], top, [], zbot=4.2)
    C.put(P, (S_N, TW[2]), (S_N, 0), "west_s_gable")
    # lean-to south of the tower (walls 2 and 1)
    P = C.P()
    wall_face(P, pal, 0, TW[2], [(0, 5.4), (TW[2], 4.4)], [window(P, pal, 1.0, 0.7, 1.4, 3.2, 1)])
    C.put(P, (0, TW[2]), (0, 0), "leanto_w")
    C.roof([[(-0.2, TW[2], 5.5), (S_N, TW[2], 5.5), (S_N, -0.3, 4.2), (-0.2, -0.3, 4.2)]], LEAD)
    # low annex north of the tower (DSM ~2.5 m) filling the OSM strip t 8.9..9.95
    for (A, B, nm) in (((-2.75, 9.95), (-2.75, TW[3]), "annex_w"), ((S_N, 9.95), (-2.75, 9.95), "annex_n")):
        P = C.P()
        L = math.dist(A, B)
        wall_face(P, pal, 0, L, [(0, 2.5), (L, 2.5)], [])
        P.extrude_profile([(Y - 0.05, 2.4), (Y + 0.12, 2.4), (Y + 0.12, 2.6), (Y - 0.05, 2.6)], 0, L, pal.dress,
                          mat="stone")
        C.put(P, A, B, nm)
    C.flat(-2.75, S_N, TW[3], 9.95, 2.45)
    # nave east gable (brick) above the chancel and chapel roofs
    P = C.P()
    top = [(0, ZE), (TR, ZR), (T_N, ZE)]
    wall_face(P, pal, 0, T_N, top, [], col=brick, mat="brick", zbot=4.6)
    coping(P, pal, top)
    C.put(P, (S_C, 0), (S_C, T_N), "nave_east_gable")
    # chancel side walls above the chapel roofs
    for (t, za, nm, A, B) in ((ct0, Z_SCH - 0.6, "chancel_s", (S_C, ct0), (S_E, ct0)),
                              (ct1, Z_NCH - 0.6, "chancel_n", (S_E, ct1), (S_C, ct1))):
        P = C.P()
        P.face_xz(box(0, za, S_E - S_C, cze), Y, pal.wall, mat=pal.mat)
        C.put(P, A, B, nm)
    # --- tower
    s0, s1, t0, t1, H = TW
    corners = [(s0, t0), (s1, t0), (s1, t1), (s0, t1)]
    zp = H - 1.3
    for i in range(4):
        A, B = corners[i], corners[(i + 1) % 4]
        L = math.dist(A, B)
        P = C.P()
        xc = L / 2
        holes = []
        if i == 3:   # west face above the lower stage
            holes += [window(P, pal, xc, 0.6, 10.6, 12.0, 1)]
        zlow = {0: -0.6, 1: 6.5, 2: -0.6, 3: TW_LOW[1] - 0.2}[i]
        for xo in ((-1.2, 1.2) if L > 6 else (0.0,)):
            holes.append(window(P, pal, xc + xo, 1.3, 14.1, 16.9, 2, louvre=True))
        g_low = box(-0.08, zlow, L + 0.08, 12.6).difference(unary_union(holes))
        g_up = box(-0.08, 12.6, L + 0.08, zp).difference(unary_union(holes))
        P.face_xz(g_low, Y, pal.wall, mat="stone")
        P.face_xz(g_up, Y, render, mat="render")
        if i == 3:
            P.extrude_profile([(Y - 0.05, -0.6), (Y + 0.25, -0.6), (Y + 0.25, 0.5), (Y + 0.05, 0.7),
                               (Y - 0.05, 0.7)], -0.08, L + 0.08, pal.dress, mat="stone")
        for zc in (12.6, 17.6):
            P.extrude_profile([(Y - 0.05, zc - 0.2), (Y + 0.12, zc - 0.2), (Y + 0.18, zc), (Y - 0.05, zc + 0.04)],
                              -0.1, L + 0.1, pal.dress, mat="stone")
        parapet(P, pal, -0.08, L + 0.08, zp, H, embattled=True, col=brick, mat="brick")
        C.put(P, A, B, "tower%d" % i)
    # lower stage, thicker to the west (OSM west face), with the west door and window and a sloped set-off
    sl, zl = TW_LOW
    P = C.P()
    L = t1 - t0
    holes = [door(P, pal, L / 2, 1.2, 2.7), window(P, pal, L / 2, 1.6, 4.0, 7.4, 2)]
    wall_face(P, pal, 0, L, [(0, zl), (L, zl)], holes)
    d_ = s0 - sl
    P.extrude_profile([(Y - d_ - 0.1, zl), (Y + 0.12, zl), (Y + 0.12, zl + 0.12), (Y - d_ - 0.1, zl + 0.75)],
                      -0.08, L + 0.08, pal.dress, mat="stone")
    C.put(P, (sl, t1), (sl, t0), "tower_low_w")
    for (A, B, nm) in (((sl, t0), (s0, t0), "tower_low_s"), ((s0, t1), (sl, t1), "tower_low_n")):
        P = C.P()
        wall_face(P, pal, 0, d_, [(0, zl + 0.1), (d_, zl + 0.1)], [])
        C.put(P, A, B, nm)
    p = [C.w(*c) for c in corners]
    zr = C.Z0 + H - 1.5
    C.out.append({"name": "stedward:tower_roof", "tris": np.array([[(*p[0], zr), (*p[1], zr), (*p[2], zr)],
                                                                   [(*p[0], zr), (*p[2], zr), (*p[3], zr)]]),
                  "col": LEAD, "mat": "plain"})
    # --- roofs
    C.gable_roof(S_N, S_C, 0.0, T_N, None, ZE, TR, ZR, pal.roof, verge=0.15)
    C.gable_roof(S_C, S_E, ct0, ct1, None, cze, ctr, czr, pal.roof, ov=0.25, verge=0.12)
    C.flat(S_C, S_E, 0.0, ct0, Z_SCH - 1.1)
    C.flat(S_C, S_E, ct1, NG[0], Z_NCH - 1.1)
    C.flat(S_C, 14.55, ct1, T_N, Z_NCH - 1.1)
    k = (NG[3] - NG[2]) / (NG[4] - NG[0])
    C.roof([[(14.4, NG[0], NG[2]), (S_E + 0.12, NG[0], NG[2]), (S_E + 0.12, NG[4], NG[3]), (14.4, NG[4], NG[3])],
            [(14.4, NG[1] + 0.25, NG[2] - 0.25 * k), (S_E + 0.12, NG[1] + 0.25, NG[2] - 0.25 * k),
             (S_E + 0.12, NG[4], NG[3]), (14.4, NG[4], NG[3])]], pal.roof)
    return C.done()


# ------------------------------------------------------------------ St Michael's

SM_OSM = "way/95406730"
SM_PTS = [(-162.58, 143.84), (-164.10, 143.94), (-165.85, 125.66), (-160.54, 125.33), (-147.33, 124.37),
          (-134.79, 123.76), (-133.25, 141.38), (-151.38, 142.98), (-158.14, 143.57), (-157.93, 146.47),
          (-162.35, 146.84)]


def st_michael(walls=None):
    pal = Pal("#9d907a", "#cfc3a4", "#52575c")
    C = Church("stmichael", (-165.85, 125.66), (31.06, -1.90), 9.5, pal)
    loc = [tuple(np.linalg.solve(np.c_[C.U, C.V], np.asarray(p) - C.O)) for p in SM_PTS]
    S_E = loc[5][0]                             # 31.12 (east wall leans to 31.58 at the north end)
    T_S = -0.05
    T_N = 18.2                                  # north wall t 18.35 (west) .. 17.68 (east)
    ZP, ZE, ZR, TR = 5.7, 5.7, 10.95, 9.3      # south parapet top, north eaves, ridge, ridge line
    TW = (1.6, 6.3, 0.0, 5.6, 16.4)   # LiDAR plateau 25.5-25.9: set back ~1.6 m behind the Trinity Street gable

    def roof_z(t):
        return ZR - (ZR - (ZP - 0.4)) * (TR - t) / (TR - T_S) if t < TR else ZR - (ZR - ZE) * (t - TR) / (T_N - TR)

    # --- south wall (the tower's south face stands on its line from s 1.0 to 6.2)
    P = C.P()
    L = math.dist((0, T_S), loc[5])
    holes = [window(P, pal, xc, 1.9, 1.6, 4.6, 3) for xc in (9.4, 15.8, 22.2, 27.6)]
    holes.append(window(P, pal, 3.95, 1.5, 2.0, 5.0, 2))   # tower ground stage
    holes.append(door(P, pal, 19.0, 1.2, 2.6))
    wall_face(P, pal, 0, L, [(0, ZP - 0.9), (L, ZP - 0.9)], holes)
    parapet(P, pal, -0.1, TW[0], ZP - 0.9, ZP)
    parapet(P, pal, TW[1], L + 0.08, ZP - 0.9, ZP)
    for x in (TW[1] + 0.4, 12.6, 25.0, L - 0.3):
        buttress(P, pal, x, ZP - 1.4, d0=0.8)
    C.put(P, (0, T_S), loc[5], "south")
    # --- east gable: five-light east window, aisle-end windows
    P = C.P()
    L = math.dist(loc[5], loc[6])
    xr = TR - T_S
    holes = [window(P, pal, xr, 3.6, 2.4, 8.9, 5), window(P, pal, 3.2, 1.6, 1.6, 4.4, 3),
             window(P, pal, L - 3.2, 1.6, 1.6, 4.4, 3)]
    top = [(0, ZP - 0.9), (0.4, ZP - 0.4), (xr, ZR), (L, ZE)]
    wall_face(P, pal, 0, L, top, holes)
    coping(P, pal, [(0.4, ZP - 0.4), (xr, ZR), (L, ZE)])
    cross(P, pal, xr, ZR + 0.05)
    for x in (0.3, L - 0.3):
        buttress(P, pal, x, ZE - 1.2, d0=0.9)
    C.put(P, loc[5], loc[6], "east")
    # --- north wall: east part, porch gap, west part
    sp0, sp1 = loc[8][0], loc[0][0]    # porch s range (~7.5 .. 3.2)
    P = C.P()
    L = math.dist(loc[6], loc[8])
    holes = [window(P, pal, xc, 1.9, 1.6, 4.6, 3) for xc in (2.6, 8.4, 14.2, 20.0)]
    wall_face(P, pal, -0.1, L, [(-0.1, ZE), (L, ZE)], holes)
    for x in (0.3, 5.5, 11.3, 17.1, L - 0.3):
        buttress(P, pal, x, ZE - 1.4, d0=0.8)
    C.put(P, loc[6], loc[8], "north_e")
    P = C.P()
    wall_face(P, pal, -0.1, sp0 - sp1, [(-0.1, ZE), (sp0 - sp1, ZE)], [], zbot=2.8)
    C.put(P, loc[8], loc[0], "north_porchback")
    P = C.P()
    Lw = sp1 - loc[1][0]
    wall_face(P, pal, 0, Lw, [(0, ZE), (Lw, ZE)], [window(P, pal, Lw / 2, 0.8, 1.8, 4.2, 1)])
    C.put(P, loc[0], loc[1], "north_w")
    # --- west gable on Trinity Street (the tower rises behind its south end)
    P = C.P()
    L = math.dist(loc[1], loc[2])
    xr = loc[1][1] - TR
    holes = [window(P, pal, 5.6, 2.8, 2.2, 8.0, 4), door(P, pal, L - 3.0, 1.3, 2.8)]
    top = [(0, ZE), (xr, ZR), (L, ZP - 0.4)]
    wall_face(P, pal, 0, L, top, holes)
    coping(P, pal, top)
    cross(P, pal, xr, ZR + 0.05)
    for x in (0.3, L - 0.3):
        buttress(P, pal, x, ZE - 1.2, d0=0.9)
    C.put(P, loc[1], loc[2], "west")
    # --- north porch (gabled, pointed doorway)
    a, b, c, d = loc[8], loc[9], loc[10], loc[0]
    for (A, B, nm) in ((a, b, "porch_e"), (c, d, "porch_w")):
        P = C.P()
        L = math.dist(A, B)
        wall_face(P, pal, 0, L, [(0, 3.0), (L, 3.0)], [])
        C.put(P, A, B, nm)
    P = C.P()
    L = math.dist(b, c)
    top = [(0, 3.0), (L / 2, 4.8), (L, 3.0)]
    wall_face(P, pal, 0, L, top, [door(P, pal, L / 2, 1.5, 2.7)], col=F.rgb("#c9bd9f"))
    coping(P, pal, top)
    cross(P, pal, L / 2, 4.85)
    C.put(P, b, c, "porch_n")
    pm = ((b[0] + c[0]) / 2, (b[1] + c[1]) / 2)
    am = ((a[0] + d[0]) / 2, (a[1] + d[1]) / 2)
    C.roof([[(a[0] + 0.2, a[1], 3.0), (b[0] + 0.2, b[1] + 0.2, 3.0), (pm[0], pm[1] + 0.2, 4.8), (am[0], am[1], 4.8)],
            [(d[0] - 0.2, d[1], 3.0), (c[0] - 0.2, c[1] + 0.2, 3.0), (pm[0], pm[1] + 0.2, 4.8),
             (am[0], am[1], 4.8)]], pal.roof)
    # --- tower (SW corner)
    s0, s1, t0, t1, H = TW
    corners = [(s0, T_S), (s1, T_S - 0.02), (s1, t1), (s0, t1)]
    zp = H - 1.0
    for i in range(4):
        A, B = corners[i], corners[(i + 1) % 4]
        L = math.dist(A, B)
        P = C.P()
        xc = L / 2
        holes = [window(P, pal, xc, 1.5, 12.0, 14.8, 2, louvre=True)]
        if i in (0, 3):
            holes.append(window(P, pal, xc, 0.55, 8.9, 10.3, 1))
        zlow = {0: ZP - 0.9, 1: ZP - 1.0, 2: roof_z(t1) - 0.8, 3: roof_z(t1) - 0.8}[i]
        g = box(-0.08, zlow, L + 0.08, zp).difference(unary_union(holes))
        P.face_xz(g, Y, pal.wall, mat="flint")
        for zc in (7.6, 11.4):
            if zc > zlow:
                P.extrude_profile([(Y - 0.05, zc - 0.2), (Y + 0.12, zc - 0.2), (Y + 0.18, zc),
                                   (Y - 0.05, zc + 0.04)], -0.1, L + 0.1, pal.dress, mat="stone")
        parapet(P, pal, -0.08, L + 0.08, zp, H, col=pal.wall, mat="flint")
        C.put(P, A, B, "tower%d" % i)
    p = [C.w(*c) for c in corners]
    zr = C.Z0 + H - 1.2
    C.out.append({"name": "stmichael:tower_roof", "tris": np.array([[(*p[0], zr), (*p[1], zr), (*p[2], zr)],
                                                                    [(*p[0], zr), (*p[2], zr), (*p[3], zr)]]),
                  "col": LEAD, "mat": "plain"})
    # flagpole on the tower roof
    P = C.P()
    P.box(-0.05, 0.05, -0.05, 0.05, H - 1.2, H + 4.0, F.rgb("#e8e6e0"), bottom=False, mat="trim")
    C.put(P, (s1 - 1.0, t1 - 1.0), (s1, t1 - 1.0), "flagpole")
    # --- main roof: one span over nave, chancel and aisles (south eaves behind the parapet)
    s_e = 0.5 * (loc[5][0] + loc[6][0])
    C.gable_roof(0.2, s_e, T_S, T_N, None, ZP - 0.4, TR, ZR, pal.roof, ov=0.0, verge=0.35)
    C.roof([[(-0.15, T_N, ZE), (s_e + 0.4, T_N, ZE), (s_e + 0.4, T_N + 0.35, ZE - 0.22),
             (-0.15, T_N + 0.35, ZE - 0.22)]], pal.roof)   # north eaves overhang
    C.flat(0.0, S_E, T_S - 0.02, T_S + 0.3, ZP - 0.45, LEAD)   # parapet gutter
    return C.done()


BUILDS = {SE_OSM: st_edward, SM_OSM: st_michael}
def _elements():
    """{walls.json wall id: {"window", "door", "shopfront", "dormer"}} counted from the openings the builders
    actually emit: each opening's world position is assigned to the nearest walls.json wall of the building
    (within 1.2 m of the segment); openings on parts not on any walls.json wall (tower upper faces) are skipped."""
    import json
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data/annotations/market_square/walls.json")
    try:
        W = json.load(open(path))["walls"]
    except Exception:
        return {}
    res = {}
    for osm, fn in ((SE_OSM, st_edward), (SM_OSM, st_michael)):
        ws = [w for w in W if w["osm_id"] == osm]
        if not ws:
            continue
        fn([])
        ch = _LAST[0]
        for w in ws:
            res[w["id"]] = {"window": 0, "door": 0, "shopfront": 0, "dormer": 0}
        for kind, pt in ch.openings:
            best, bd = None, 1.2
            for w in ws:
                a, b = np.asarray(w["p0"], float), np.asarray(w["p1"], float)
                u = b - a
                L2 = float(u @ u)
                f = float(np.clip((pt - a) @ u / L2, 0, 1))
                dd = float(np.linalg.norm(a + f * u - pt))
                if dd < bd:
                    best, bd = w["id"], dd
            if best is not None:
                res[best][kind] += 1
    return res


ELEMENTS = _elements()
HIDE_TILE = [SE_OSM, SM_OSM]   # both models are complete closed exteriors over the OSM footprints

if __name__ == "__main__":
    tot = 0
    for k, fn in BUILDS.items():
        items = fn([])
        n = sum(len(i["tris"]) for i in items)
        tot += n
        print(k, n, "max z", round(max(float(np.asarray(i["tris"])[..., 2].max()) for i in items), 2))
    print("total", tot)
