"""Bespoke geometry for the Bridge Street frontages (ring 2), session 70: the shop / restaurant terraces from the
St John's Street - Round Church junction north-west to Magdalene Bridge (east side Nos 8-9, 10-20, 21-24, the
unnumbered houses, 29, 33 Galleria) and the west-side group facing the Round Church (Nos 63-71). The Round Church,
St Clement's church and St John's College ranges are not touched; no id here has another bespoke module.

As zone_bespoke_trinitystreet.py: each OSM building in SPEC becomes a bespoke building (BUILDS keyed by its real OSM id),
so city_facades.py stops building its generic skin, and every wall city_facades would have built for it is rebuilt here.
Most of these walls are outside ring 1 (400 m), so data/annotations/ring1/walls.json does not list them; the wall
geometry is recomputed exactly as city_facades.py does (OSM footprint ring made counter-clockwise, edge k = wall
"<osm id>:k", ground = DTM 1.5 m out from the wall, eave = median DSM 1-2.5 m inside the wall), restricted to the wall ids
data/derived/facade_geometry_city.json lists for the building.
- Bridge Street walls (edge parallel to the street, <= 9 m from the OSM highway, facing it) get a layout built from SPEC:
  storeys from the LiDAR eave height (shop ground floor 3.4 m, upper floors ~2.9 m), a regular sash-window bay rhythm
  per upper floor, shopfronts with fascias and raised lettering carrying the business names of the OSM POIs inside the
  footprint (blank where OSM tags none), the facing material / colour, string courses, dormers where noted, LiDAR
  chimney stacks and an eave gutter (shared with the Trinity Street module); timber-framed fronts get a black post and
  rail frame with a jetty bressumer on brackets;
- other walls: facade_styles.layout (what city_facades would have built), so nothing regresses.

References (shape / colour / sequence only; none is a held-out benchmark photo, nothing under data/benchmark opened):
Mapillary (CC BY-SA 4.0) 2578991052406189 (looking NW from St Clement's: Cote's tall 4-storey gault-brick front with dark
shopfront and striped awnings, then a cream-rendered red-fronted restaurant with dormers, a gault-brick front with black
window frames, white-rendered gabled houses towards the bridge), 199084495378242 (looking SE: a black-and-white
timber-framed gable among the pubs, pink-rendered corner group at the junction), 1128782817595891 and 513570889821825
(No 20 "Bridges": gault brick with a red-brick band, white sashes, blue shopfront).
Uncertain / not verified: per-building materials south of St Clement's (which pub front is the timber-framed one - put
on No 17 The Mitre - and the colours of Nos 8-16 and 63-71 are from memory and the photo-atlas colour hints); window
counts are a regular bay rhythm, not counted from photos; the unnumbered houses' business names are left blank
(the photo shows Cafe Rouge in way/191541528, but OSM does not tag it); dormers only where noted in SPEC.
"""
import json
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import facade_parts as F  # noqa: E402
from zone_bespoke_kings import frame_world  # noqa: E402
from zone_bespoke_trinitystreet import lettering, chimneys, gutter  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
E0, N0 = 545000.0, 258400.0
STREET_WAYS = (9042753, 148815860, 3992999, 4604368, 24443713, 169507718)   # OSM highway ways named Bridge Street

GAULT, GAULT_T = "#c9b98f", "#f2efe6"
REDB = "#9a5a44"
# osm id -> facing, colours, shop names (OSM POIs inside the footprint, longest street wall first), extras
SPEC = {
    "way/965378229":  dict(no="8-9", mat="render", col="#e9e2d2", trim="#f6f3ea", shops=["Crosstown", "Catherine Jones"],
                           fas=["#1d1d1f", "#2f3d4a"]),
    "way/1288750542": dict(no="10", mat="render", col="#f1ece0", trim="#ffffff", shops=["Toni & Guy", "Bould Brothers"],
                           fas=["#151515", "#3a4a3a"], dormers=True),
    "way/1288750543": dict(no="12", mat="render", col="#e8d9b4", trim="#f4efe2", shops=["Byron"], fas=["#2a2a2a"]),
    "way/1288750540": dict(no="14", mat="render", col="#e4c6b8", trim="#f5efe6", shops=[""], fas=["#4b3a34"], dormers=True),
    "way/1288750539": dict(no="15-16", mat="brick", col=GAULT, trim=GAULT_T, shops=["PizzaExpress"], fas=["#1c3f6e"],
                           string=True),
    "way/191541100":  dict(no="17", mat="render", col="#f3f0e8", trim="#f3f0e8", shops=["The Mitre"], fas=["#1e2b24"],
                           timber=True),
    "way/191541101":  dict(no="19", mat="render", col="#ece3cc", trim="#f6f2e8", shops=["Baron of Beef"], fas=["#22322a"]),
    "way/191541099":  dict(no="20", mat="brick", col=GAULT, trim=GAULT_T, shops=["Bridges"], fas=["#1d4f9c"], string=True,
                           string_col="#9a4a34"),
    "way/191541526":  dict(no="21-24", mat="brick", col=GAULT, trim=GAULT_T, shops=["Côte"], fas=["#23302c"], string=True),
    "way/191541528":  dict(no="25-28?", mat="render", col="#efe2bc", trim="#b0211c", shops=[""], fas=["#a81f1a"],
                           dormers=True),
    "way/191541529":  dict(no="?", mat="brick", col=GAULT, trim="#1e1e1e", shops=[""], fas=["#1f2a24"]),
    "way/191541522":  dict(no="29", mat="render", col="#f1eee6", trim="#ffffff", shops=[""], fas=["#2b2b2b"], jetty=True),
    "way/191541523":  dict(no="30?", mat="render", col="#f0ece2", trim="#ffffff", shops=[""], fas=["#30393f"], jetty=True),
    "way/191541524":  dict(no="31-32?", mat="render", col="#ead8cc", trim="#fbf8f2", shops=[""], fas=["#3b2f2a"]),
    "way/165370805":  dict(no="33", mat="render", col="#efe6cf", trim="#ffffff", shops=["Galleria"], fas=["#2a3f5a"]),
    "way/1288738594": dict(no="63-66", mat="render", col="#e7c4b6", trim="#f8f3ec", shops=["Crêpeaffaire",
                           "Distinctive Cambridge"], fas=["#c8102e", "#20303a"]),
    "way/1288738597": dict(no="67", mat="render", col="#efe5c9", trim="#ffffff", shops=["Mr & Mrs Clarks"],
                           fas=["#1f1f1f"], dormers=True),
    "way/1288738599": dict(no="68", mat="render", col="#f2efe8", trim="#ffffff", shops=[""], fas=["#33413c"],
                           dormers=True),
    "way/263621281":  dict(no="69", mat="brick", col=REDB, trim="#efe9dc", shops=["Scruffs"], fas=["#1a1a1a"],
                           string=True),
    "way/1288738590": dict(no="71-72", mat="render", col="#f3eee2", trim="#ffffff", shops=["Lilac Rose", "Pure Source"],
                           fas=["#6b4a7a", "#2c5a3a"]),
}
TIMBER = F.rgb("#26211d")
INFILL = F.rgb("#f2efe6")

_OPS = []
ELEMENTS = {}
_CACHE = {}


# ------------------------------------------------------------------ walls (as city_facades.py)
def _walls():
    if "W" in _CACHE:
        return _CACHE
    import rasterio
    from shapely.geometry import LineString, Point
    from shapely.ops import unary_union
    import build as B
    nodes, ways, rels, _ = B.load_osm()
    keep_ids = set()
    try:
        for r in json.load(open(os.path.join(ROOT, "data/derived/facade_geometry_city.json")))["walls"]:
            if r["osm_id"] in SPEC:
                keep_ids.add(r["id"])
    except Exception:
        keep_ids = None
    segs = []
    for wid in STREET_WAYS:
        w = ways.get(wid)
        if w:
            c = [nodes[n] for n in w["nodes"] if n in nodes]
            segs += [LineString([c[i], c[i + 1]]) for i in range(len(c) - 1)]
    street = unary_union(segs)
    dtm = rasterio.open(os.path.join(ROOT, "data/lidar/dtm_1m.tif"))
    dsm = rasterio.open(os.path.join(ROOT, "data/lidar/dsm_1m.tif"))
    DT, DS = dtm.read(1), dsm.read(1)

    def samp(R, A, P):
        r, c = rasterio.transform.rowcol(R.transform, P[:, 0], P[:, 1])
        r = np.clip(np.asarray(r), 0, A.shape[0] - 1)
        c = np.clip(np.asarray(c), 0, A.shape[1] - 1)
        return A[r, c].astype(float)

    W = []
    for oid in SPEC:
        w = ways.get(int(oid.split("/")[1]))
        if not w:
            continue
        g = B.way_area(w, nodes)
        if g is None or g.is_empty:
            continue
        for p in B.polys_of(g):
            ring = list(p.exterior.coords)
            if not p.exterior.is_ccw:
                ring = ring[::-1]
            for k in range(len(ring) - 1):
                a, b = np.array(ring[k]), np.array(ring[k + 1])
                L = float(np.linalg.norm(b - a))
                wid = "%s:%d" % (oid, k)
                if L < 2 or (keep_ids is not None and wid not in keep_ids):
                    continue
                d = (b - a) / L
                n = np.array([d[1], -d[0]])
                m = (a + b) / 2
                gz = float(samp(dtm, DT, (m + n * 1.5)[None])[0])
                ins = np.array([a + d * L * f - n * s for f in (0.2, 0.4, 0.6, 0.8) for s in (1, 1.75, 2.5)])
                ez = float(np.median(samp(dsm, DS, ins)))
                dd = street.distance(Point(*m))
                sf = False
                if dd <= (13 if oid == "way/165370805" else 9) and street.distance(Point(*(m + n * 2))) < dd:
                    s = min(segs, key=lambda s: s.distance(Point(*m)))
                    sc = np.array(s.coords)
                    sd = (sc[1] - sc[0]) / max(np.linalg.norm(sc[1] - sc[0]), 1e-6)
                    sf = abs(float(d @ sd)) >= 0.8
                W.append(dict(id=wid, osm_id=oid, tags=w.get("tags", {}), length=round(L, 2),
                              p0=[round(a[0] - B.E0, 2), round(a[1] - B.N0, 2)],
                              p1=[round(b[0] - B.E0, 2), round(b[1] - B.N0, 2)],
                              ground_z=round(gz, 2), eave_z=round(max(ez, gz + 2.5), 2),
                              height=round(max(ez - gz, 2.5), 2), street_facing=True, bridge_st=sf))
    _CACHE["W"] = W
    _CACHE["by"] = {}
    for w in W:
        _CACHE["by"].setdefault(w["osm_id"], []).append(w)
    try:
        import zone_build as Z
        _CACHE["ext"] = Z.corner_extents(W)
    except Exception:
        _CACHE["ext"] = {}
    return _CACHE


# ------------------------------------------------------------------ layout from SPEC
def _layout(w, sp, shop_names, fascias):
    L, H = w["length"], w["eave_z"] - w["ground_z"]
    shop = bool(sp.get("shops")) and L >= 2.6
    g = 3.4 if shop else 3.0
    n_up = max(1, min(3, int(round((H - g - 0.5) / 2.9))))
    fh = (H - g - 0.4) / n_up if H - g - 0.4 > 2.2 * n_up else 2.6
    floors = [0.0] + [g + i * fh for i in range(n_up)]
    els = []
    nb = max(1, int((L - 0.6) / 2.3)) if L >= 2.4 else (1 if L >= 1.8 else 0)
    xs = [L * (i + 0.5) / nb for i in range(nb)]
    pane = [3, 3] if sp["mat"] != "brick" or sp.get("trim") != "#1e1e1e" else [1, 2]
    for fi, z in enumerate(floors[1:]):
        top = fi == n_up - 1
        h = max(1.0, min(1.75 if not top else 1.35, fh - 1.1))
        for x in xs:
            els.append({"type": "window", "style": "sash_georgian", "x": round(x, 2), "w": 0.95 if nb > 1 or L > 3 else 0.8,
                        "z": round(z + 0.75, 2), "h": round(h, 2), "panes": pane, "head": "flat", "sill": True})
    if shop:
        k = len(shop_names)
        if k >= 2 and L >= 7:
            mid = L / 2
            for j, (x0, x1) in enumerate(((0.3, mid - 0.15), (mid + 0.15, L - 0.3))):
                els.append({"type": "shopfront", "x0": round(x0, 2), "x1": round(x1, 2), "z1": g - 0.1,
                            "fascia_text": shop_names[j], "fascia_colour": fascias[min(j, len(fascias) - 1)],
                            "door_x": round(x0 + 0.8, 2), "stallriser": 0.45, "awning": False})
        else:
            els.append({"type": "shopfront", "x0": 0.3, "x1": round(L - 0.3, 2), "z1": g - 0.1,
                        "fascia_text": shop_names[0] if k else "", "fascia_colour": fascias[0],
                        "door_x": round(min(1.2, L / 2), 2), "stallriser": 0.45, "awning": False})
    else:
        for x in xs:
            els.append({"type": "window", "style": "sash_georgian", "x": round(x, 2), "w": 0.95, "z": 0.9, "h": 1.6,
                        "panes": [3, 3], "head": "flat", "sill": True})
    if sp.get("dormers") and L >= 3:
        for x in xs[: max(1, nb - 1)] if nb > 2 else xs:
            els.append({"type": "dormer", "x": round(x, 2), "w": 1.1, "h": 1.3})
    lay = {"id": w["id"], "storeys": len(floors), "floor_z": [round(z, 2) for z in floors], "material": sp["mat"],
           "wall_colour": sp["col"], "trim_colour": sp["trim"], "cornice_z": round(H, 2),
           "cornice": "simple" if sp["mat"] == "brick" else "bracketed", "parapet": False,
           "string_courses": [round(g, 2)] if sp.get("string") else [], "quoins": False, "pilasters": [],
           "elements": els}
    if sp.get("timber"):
        lay["wall_colour"] = "#f2efe6"
    return lay, floors, fh, xs


def timber_frame(P, L, H, floors, fh, xs, jetty=True):
    """Black posts and rails over a white infill on the upper floors, avoiding the windows; jetty bressumer + brackets."""
    y0, y1 = F.SKIN, F.SKIN + 0.07
    z0 = floors[1]
    win = [(x - 0.6, x + 0.6) for x in xs]
    posts = [0.15, L - 0.15]
    x = 0.15
    while x < L - 0.3:
        x += 0.75
        if all(not (a < x < b) for a, b in win) and x < L - 0.3:
            posts.append(x)
    for x in posts:
        P.box(x - 0.09, x + 0.09, y0, y1, z0, H, TIMBER, mat="timber")
    for z in floors[1:] + [H - 0.12]:
        P.box(0.05, L - 0.05, y0, y1 + 0.01, z - 0.06, z + 0.1, TIMBER, mat="timber")
    for z in floors[1:]:     # mid rails between the window bays
        zm = z + fh * 0.5
        for a, b in zip([0.0] + [w[1] for w in win], [w[0] for w in win] + [L]):
            if b - a > 0.4:
                P.box(a + 0.05, b - 0.05, y0, y1, zm - 0.06, zm + 0.06, TIMBER, mat="timber")
    if jetty:
        bres_z = z0 - 0.25
        P.box(0.0, L, F.SKIN, F.SKIN + 0.32, bres_z, z0 + 0.05, TIMBER, mat="timber")
        for x in posts[::2]:
            P.box(x - 0.08, x + 0.08, F.SKIN, F.SKIN + 0.28, bres_z - 0.45, bres_z, TIMBER, mat="timber")


def jetty_beam(P, L, z):
    P.box(0.0, L, F.SKIN, F.SKIN + 0.3, z - 0.28, z + 0.04, F.rgb("#3a3330"), mat="timber")


def _style_layout(w):
    try:
        import facade_styles as S
        return S.layout(w)
    except Exception:
        return F.default_layout(w)


def _ops(w, lay, P, L):
    p0 = np.asarray(w["p0"], float)
    d = (np.asarray(w["p1"], float) - p0) / L
    for kind in ("window", "door", "shopfront", "dormer"):
        xs = [((e["x0"] + e["x1"]) / 2 if kind == "shopfront" else e.get("x", L / 2))
              for e in lay["elements"] if e.get("type") == kind]
        for x in xs[: P.counts.get(kind, 0)]:
            pt = p0 + d * min(max(x, 0.1), L - 0.1)
            _OPS.append((kind, float(pt[0]), float(pt[1])))


def build_building(oid):
    C = _walls()
    sp = SPEC[oid]
    ws = C["by"].get(oid, [])
    street = sorted([w for w in ws if w["bridge_st"]], key=lambda w: -w["length"])
    named = {street[0]["id"]: True} if street else {}
    out = []
    for w in ws:
        L = float(w["length"])
        if L < 0.3:
            continue
        x0s, x1s = C["ext"].get(w["id"], (0.0, L))
        if w["bridge_st"]:
            names = sp["shops"] if w["id"] in named else [""]
            lay, floors, fh, xs = _layout(w, sp, names, sp["fas"])
            H = max(w["eave_z"] - w["ground_z"], floors[-1] + 2.0)
            P = F.wall_facade(L, H, lay, x0s, x1s)
            for e in lay["elements"]:
                if e["type"] == "shopfront" and e.get("fascia_text") and \
                        min(e["x1"], x1s - 0.05) - max(e["x0"], x0s + 0.05) >= 1.0:
                    lettering(P, dict(e, x0=max(e["x0"], x0s + 0.05), x1=min(e["x1"], x1s - 0.05)), H)
            if sp.get("timber") and len(floors) > 1:
                timber_frame(P, L, H, floors, fh, xs)
            elif sp.get("jetty") and len(floors) > 1:
                jetty_beam(P, L, floors[1])
            gutter(P, H, x0s, x1s)
            if L >= 3.0:
                chimneys(P, w, H, L)
            _ops(w, lay, P, L)
            ELEMENTS[w["id"]] = {k: P.counts.get(k, 0) for k in ("window", "door", "shopfront", "dormer")}
        else:
            H = w["eave_z"] - w["ground_z"]
            P = F.wall_facade(L, H, _style_layout(w), x0s, x1s)
        p0 = np.asarray(w["p0"], float)
        d = (np.asarray(w["p1"], float) - p0) / L
        it = frame_world(P, p0, d, "bridgest:" + w["id"], z0=w["ground_z"])
        if it:
            out.append(it)
    return out


def _mk(oid):
    def fn(walls=None):
        _OPS.clear()
        return build_building(oid)
    return fn


BUILDS = {oid: _mk(oid) for oid in SPEC}

if __name__ == "__main__":
    tot = 0
    for oid in SPEC:
        n = sum(len(it["tris"]) for it in BUILDS[oid]([]))
        tot += n
        print(oid, SPEC[oid]["no"], n, [w["id"] for w in _CACHE["by"].get(oid, []) if w["bridge_st"]])
    print("total", tot, "buildings", len(SPEC))
    print("street walls with ELEMENTS", len(ELEMENTS), sum(sum(v.values()) for v in ELEMENTS.values()), "openings")
