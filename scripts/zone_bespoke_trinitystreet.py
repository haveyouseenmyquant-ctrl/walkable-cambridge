"""Bespoke geometry for the Trinity Street shopfront terraces (ring 1), session 69: the street fronts of Nos 9-24 (east
side, Market Street corner to the Green Street corner and on to No 24 opposite the Great Gate) and Nos 26-38 (west side,
Angel Court to the St Michael's corner). Caius, the Great Gate, St Michael's, Trinity Chapel and Holy Trinity have their
own modules and are not touched.

What it does. Each OSM building listed in TERRACE becomes a bespoke building (BUILDS keyed by its real OSM id), so
city_facades.py stops building its generic skin and counts the openings this module emits (_OPS) on the ring-1 KPI rows.
Every wall of each building is rebuilt (the back and side walls too, else they would lose their skin):
- walls with a ring-1 annotation (data/annotations/ring1/way_*.json; storeys, floor heights, every window / door /
  shopfront / dormer position, materials and colours, fascia names) go through the shared parts library
  (facade_parts.wall_facade: windows with reveals, frames, glazing bars, sills and lintels; panelled / fanlit doors with
  surrounds; shopfronts with stallrisers, mullions, transoms, recessed doors, end pilasters, fascia boards and fascia
  cornices; string courses, cornices, parapets, dormers), and this module adds on top:
  * raised fascia lettering with the real shop names (the annotation's fascia_text, taken from the OSM shop tags /
    the photos), rendered from Georgia Bold as merged pixel-run quads, in the annotation's text colour (or a contrast
    colour for the fascia);
  * chimney stacks with pots, only where the LiDAR DSM shows a stack (DSM max within 0.4-2.6 m behind a party-wall end
    of the street wall rises 0.9-4.5 m over the eave); stack top = that DSM height;
  * a plain lead-grey roof-edge gutter line along the eave (no invention: every Cambridge terrace front has one);
- walls without an annotation (rear / side walls) get exactly what city_facades would have built for them
  (facade_styles.layout or facade_parts.default_layout), so nothing regresses.
Heights: ground_z and eave_z of every wall come from data/annotations/ring1/walls.json, which city_facades.py computes
from the LiDAR (DTM at the wall foot, DSM median along a 1-2.5 m inset behind the wall = eave, i.e. DSM minus DTM); the
height is raised to clear the annotation's own cornice / top window if the DSM eave sample is lower.

Reference photos (shape / layout / colour only, recorded in each annotation file's "sources"; none is a held-out
benchmark photo, nothing under data/benchmark was opened):
- Wikimedia Commons: "19, Trinity Street.jpg", "16 And 16A, Trinity Street.jpg", "15, Trinity Street.jpg",
  "14 Trinity Street, Cambridge.JPG", "32, Trinity Street.jpg", "38 Trinity Street, Cambridge.jpg",
  "35-37, Trinity Street.jpg", "33 And 34, Trinity Street.jpg", "Green Street, Cambridge.jpg"
  (CC BY-SA 2.0 / 3.0 / 4.0 per their file pages; the numbered-house series is the Historic England listed-building set);
- Mapillary images (CC BY-SA 4.0): 274161827742448, 218778726265898, 556976891953894, 166355842062342,
  952996672184960, 935055160579489 (ids as in the annotation files).
Uncertain / not verified this session:
- fascia names reflect the annotations (OSM shop tags at annotation time); shops change, e.g. 30-31 was photographed as
  Jaeger but OSM says SageBrown; 9 (Market St return) and 38 (Market St return) have blank fascias in the annotation and
  get no lettering;
- chimney stacks are only where the 1 m DSM shows a peak; small stacks between the 1 m samples are missed and some
  "peaks" may be dormers or roof plant;
- the gutter colour (lead grey) is generic;
- Nos 11, 12, 17 and 25 have no OSM building with that address and are not modelled here.
"""
import json
import math
import os
import sys

import numpy as np
from shapely.geometry import box

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import facade_parts as F  # noqa: E402
from zone_bespoke_kings import frame_world  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ANN = os.path.join(ROOT, "data/annotations/ring1")
E0, N0 = 545000.0, 258400.0

# OSM ways (addr:street = Trinity Street), north to south on each side
TERRACE = ["way/1288648586", "way/1288648577", "way/1288648573", "way/1288648574", "way/1288648581",
           "way/1288648582", "way/1288648587", "way/1288648583", "way/1288648571", "way/1288644220",
           "way/1288730364",                                                         # east side: 23-24 .. 9
           "way/166155959", "way/1288738591", "way/1288738585", "way/1288738589", "way/1288738586",
           "way/1288738595", "way/1288738592", "way/1288738587"]                     # west side: 26 .. 38

BRICK_STACK = F.rgb("#8a5a44")
POT = F.rgb("#a8623e")
LEAD = F.rgb("#5f6468")
FONT = "/System/Library/Fonts/Supplemental/Georgia Bold.ttf"

_OPS = []          # (kind, E, N) of every emitted opening (city_facades.bespoke_elements)
ELEMENTS = {}      # wall id -> opening counts actually emitted (filled by build)
_CACHE = {}


def _walls():
    if "W" not in _CACHE:
        W = json.load(open(os.path.join(ANN, "walls.json")))["walls"]
        _CACHE["W"] = W
        _CACHE["by"] = {}
        for w in W:
            _CACHE["by"].setdefault(w["osm_id"], []).append(w)
        try:
            import zone_build as Z
            _CACHE["ext"] = Z.corner_extents(W)
        except Exception:
            _CACHE["ext"] = {}
        ann = {}
        for oid in TERRACE:
            f = os.path.join(ANN, oid.replace("/", "_") + ".json")
            if os.path.exists(f):
                for a in json.load(open(f)).get("walls", []):
                    ann[a["id"]] = a
        _CACHE["ann"] = ann
    return _CACHE


def _dsm():
    if "dsm" not in _CACHE:
        try:
            import rasterio
            R = rasterio.open(os.path.join(ROOT, "data/lidar/dsm_1m.tif"))
            _CACHE["dsm"] = (R, R.read(1))
        except Exception:
            _CACHE["dsm"] = None
    return _CACHE["dsm"]


def _dsm_at(pts):
    d = _dsm()
    if d is None:
        return None
    R, A = d
    import rasterio
    r, c = rasterio.transform.rowcol(R.transform, pts[:, 0] + E0, pts[:, 1] + N0)
    r = np.clip(np.asarray(r), 0, A.shape[0] - 1)
    c = np.clip(np.asarray(c), 0, A.shape[1] - 1)
    return A[r, c].astype(float)


# ------------------------------------------------------------------ fascia lettering
def _glyph_rects(text, px=22):
    """Text -> list of (u0, v0, u1, v1) rectangles in units of the text height (v up), merged pixel runs."""
    from PIL import Image, ImageDraw, ImageFont
    try:
        font = ImageFont.truetype(FONT, px)
    except Exception:
        font = ImageFont.load_default()
    bb = font.getbbox(text)
    w, h = bb[2] - bb[0] + 2, bb[3] - bb[1] + 2
    im = Image.new("L", (w, h), 0)
    ImageDraw.Draw(im).text((1 - bb[0], 1 - bb[1]), text, fill=255, font=font)
    a = np.asarray(im) > 110
    rows = np.where(a.any(1))[0]
    if not len(rows):
        return [], 1.0
    a = a[rows[0]:rows[-1] + 1]
    H = a.shape[0]
    # horizontal runs per row, then merge identical runs on consecutive rows into rectangles
    open_, out = {}, []
    for j in range(H):
        row = a[j]
        runs = []
        i = 0
        while i < len(row):
            if row[i]:
                k = i
                while k < len(row) and row[k]:
                    k += 1
                runs.append((i, k))
                i = k
            else:
                i += 1
        nxt = {}
        for rn in runs:
            nxt[rn] = open_.pop(rn, j)
        for rn, j0 in open_.items():
            out.append((rn[0], j0, rn[1], j))
        open_ = nxt
    for rn, j0 in open_.items():
        out.append((rn[0], j0, rn[1], H))
    s = 1.0 / H
    return [(u0 * s, (H - j1) * s, u1 * s, (H - j0) * s) for u0, j0, u1, j1 in out], a.shape[1] * s


def _contrast(c):
    return F.rgb("#1a1a1a") if float(np.dot(c, [0.3, 0.59, 0.11])) > 0.5 else F.rgb("#efe6c8")


def lettering(P, el, H):
    txt = (el.get("fascia_text") or "").strip()
    if not txt:
        return
    x0, x1, z1 = el["x0"], el["x1"], min(el.get("z1", 3.3), H - 0.3)
    fh = min(0.7, z1 * 0.22)
    zf = z1 - fh
    fcol = F.rgb(el.get("fascia_colour", "#26343a"))
    tcol = F.rgb(el["text_colour"]) if el.get("text_colour") else _contrast(fcol)
    rects, wu = _glyph_rects(txt)
    if not rects:
        return
    hb = fh - 0.12                             # fascia board height (zf .. z1 - 0.12)
    th = min(hb * 0.62, 0.34)
    s = min(th, 0.82 * (x1 - x0) / wu)
    xc, zc = (x0 + x1) / 2, zf + hb / 2
    ux, uz = xc - wu * s / 2, zc - s / 2
    y = F.SKIN + 0.125
    for u0, v0, u1, v1 in rects:
        a, b, c0, c1 = ux + u0 * s, ux + u1 * s, uz + v0 * s, uz + v1 * s
        P.quad((a, y, c0), (b, y, c0), (b, y, c1), (a, y, c1), (0, 1, 0), tcol, mat="plain")


# ------------------------------------------------------------------ chimneys, gutter
def chimneys(P, w, H, L):
    """Party-wall stacks where the DSM shows one behind the ends of the street wall."""
    p0 = np.asarray(w["p0"], float)
    d = (np.asarray(w["p1"], float) - p0) / L
    n = np.array([d[1], -d[0]])
    eave = w["ground_z"] + H
    for xe in (0.45, L - 0.45):
        if L < 3.0:
            break
        best = None
        for xx in (xe - 0.5, xe, xe + 0.5):
            for yy in (-0.4, -1.0, -1.6, -2.2, -2.6):
                pt = p0 + d * min(max(xx, 0.2), L - 0.2) + n * yy
                z = _dsm_at(pt[None])
                if z is None:
                    return
                z = float(z[0])
                if best is None or z > best[0]:
                    best = (z, xx, yy)
        if best is None:
            continue
        rise = best[0] - eave
        if not (0.9 <= rise <= 4.5):
            continue
        xs = min(max(best[1], 0.55), L - 0.55)
        ys = min(best[2], -0.5)
        zt = H + rise
        P.box(xs - 0.5, xs + 0.5, ys - 0.35, ys + 0.35, H - 0.6, zt, BRICK_STACK)
        P.box(xs - 0.56, xs + 0.56, ys - 0.41, ys + 0.41, zt - 0.22, zt - 0.1, F.shade(BRICK_STACK, 1.12))
        for k in (-0.25, 0.25):
            P.box(xs + k - 0.1, xs + k + 0.1, ys - 0.1, ys + 0.1, zt, zt + 0.45, POT)


def gutter(P, H, x0, x1):
    y = F.SKIN
    P.extrude_profile([(y, H + 0.1), (y + 0.14, H + 0.1), (y + 0.16, H + 0.22), (y, H + 0.22)], x0, x1, LEAD)


# ------------------------------------------------------------------ assembly
def _layout(w):
    try:
        import facade_styles as S
        return S.layout(w)
    except Exception:
        lay = F.default_layout(w)
        if w.get("colour_hint"):
            lay["wall_colour"] = w["colour_hint"]
        return lay


def _height(w, a):
    H = w["eave_z"] - w["ground_z"]
    if a is None:
        return H
    top = max([a.get("cornice_z", 0) or 0] +
              [e.get("z", 1) + e.get("h", 1.6) + 0.2 for e in a.get("elements", []) if e.get("type") == "window"])
    return max(H, top)


def _ops(w, a, P, L, H):
    """World positions of the openings the facade really emitted (count per kind = P.counts)."""
    p0 = np.asarray(w["p0"], float)
    d = (np.asarray(w["p1"], float) - p0) / L
    for kind in ("window", "door", "shopfront", "dormer"):
        xs = []
        for e in a.get("elements", []):
            if e.get("type") != kind:
                continue
            xs.append((e["x0"] + e["x1"]) / 2 if kind == "shopfront" else e.get("x", L / 2))
        k = P.counts.get(kind, 0)
        for x in xs[:k]:
            pt = p0 + d * min(max(x, 0.1), L - 0.1)
            _OPS.append((kind, float(pt[0]), float(pt[1])))


def build_building(oid):
    C = _walls()
    out = []
    for w in C["by"].get(oid, []):
        L = float(w["length"])
        if L < 0.3:
            continue
        a = C["ann"].get(w["id"])
        lay = a if a is not None else _layout(w)
        H = _height(w, a)
        x0s, x1s = C["ext"].get(w["id"], (0.0, L))
        P = F.wall_facade(L, H, lay, x0s, x1s)
        if a is not None:
            for e in a.get("elements", []):
                if e.get("type") == "shopfront" and min(e["x1"], x1s - 0.05) - max(e["x0"], x0s + 0.05) >= 1.0:
                    lettering(P, dict(e, x0=max(e["x0"], x0s + 0.05), x1=min(e["x1"], x1s - 0.05)), H)
            if w.get("street_facing"):
                gutter(P, H, x0s, x1s)
                chimneys(P, w, H, L)
            _ops(w, a, P, L, H)
            ELEMENTS[w["id"]] = {k: P.counts.get(k, 0) for k in ("window", "door", "shopfront", "dormer")}
        p0 = np.asarray(w["p0"], float)
        d = (np.asarray(w["p1"], float) - p0) / L
        it = frame_world(P, p0, d, "trinityst:" + w["id"], z0=w["ground_z"])
        if it:
            out.append(it)
    return out


def _mk(oid):
    def fn(walls=None):
        # drop this building's previous openings (city_facades clears nothing between builds)
        _OPS.clear()
        return build_building(oid)
    return fn


BUILDS = {oid: _mk(oid) for oid in TERRACE}

if __name__ == "__main__":
    tot = 0
    for oid in TERRACE:
        n = sum(len(it["tris"]) for it in BUILDS[oid]([]))
        tot += n
        print(oid, n)
    print("total", tot)
    print("annotated walls", len(ELEMENTS), "openings", len(_OPS))
