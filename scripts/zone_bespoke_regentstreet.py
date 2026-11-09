"""Bespoke geometry for the Regent Street frontages (ring 2), session 71: the shop / restaurant terraces on both sides
of Regent Street from the Downing Street / Park Terrace end (Novi, PizzaExpress, The Regent hotel) south-east to the
Lensfield Road / Hills Road junction (Toni & Remi, 112-116). The University Arms hotel (way/970372393), the
Entopia Building (1 Regent St, way/135789461), Downing College porter's lodge (way/13222312) and Griphon House
(way/191546264) are left to the city skin, as are 2-4 Lensfield Road (way/191546274, no Regent Street wall) and
the three footprints city_facades lists no wall for (way/972907160, 191546275, 191546272); no id here has another bespoke module.

Structure copied from zone_bespoke_bridgestreet.py (session 70): each OSM building in SPEC becomes a bespoke building
(BUILDS keyed by its real OSM id), so city_facades.py stops building its generic skin, and every wall city_facades
would have built for it is rebuilt here (wall geometry recomputed exactly as city_facades.py does, restricted to the
wall ids data/derived/facade_geometry_city.json lists for the building).
- Regent Street walls (edge parallel to the street, <= 12 m from the OSM highway centreline - the even side's
  footprints stand behind deep forecourts - and facing it) get a layout from SPEC: storeys from the LiDAR eave height,
  sash bays per upper floor, shopfronts with fascias and raised lettering carrying the names of the OSM POIs inside the
  footprint (one shopfront per name on long walls), facing material / colour, string courses, LiDAR chimney stacks and
  an eave gutter. Walls under 5.2 m (the single-storey shop extensions built out over the front gardens of the
  even-side Victorian houses) are a shopfront under a parapet with no upper floor and no chimneys. "modern" fronts
  (De Luca / Kutchenhaus, Essex House, Mantle 95-97) get wide plain-glazed openings instead of sashes.
- other walls: facade_styles.layout (what city_facades would have built), so nothing regresses.

References: OSM tags only (building outlines, addr:housenumber, the shop / amenity POIs inside each footprint) and
the EA LiDAR DSM / DTM; nothing under data/benchmark opened.
Uncertain / not verified: every facing material and colour below is a plausible Cambridge Victorian mix (gault brick
dominant, some red brick and painted render) from general knowledge, NOT checked against photos; fascia colours are
guesses; window counts are a regular bay rhythm; shop names are OSM's and may be stale; which POI sits behind which
shopfront on multi-POI walls is by OSM order, not position.
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
STREET_WAYS = (3986744, 27421492, 44366388)   # OSM highway ways named Regent Street (not the footway 1464035153)
STREET_DIST = 12.0

GAULT, GAULT_T = "#c9b98f", "#f2efe6"
REDB, REDB_T = "#9a5a44", "#efe9dc"
# osm id -> facing, colours, shop names (OSM POIs inside the footprint), extras. North (Downing St end) to south.
SPEC = {
    # north-east side (Parker's Piece side)
    "way/191546292":  dict(no="Novi", mat="render", col="#ece6d6", trim="#ffffff", shops=["Novi"], fas=["#1b1b1b"]),
    "way/191546281":  dict(no="PizzaExpress row", mat="brick", col=GAULT, trim=GAULT_T,
                           shops=["PizzaExpress", "Cafe 24", "The Tiffin Truck", "Arthur Rank Hospice"],
                           fas=["#1c3f6e", "#3a2a20", "#7a1f1f", "#5a2a6e"]),
    "way/191546267":  dict(no="40", mat="brick", col=REDB, trim=REDB_T, shops=[""], fas=["#2b2b2b"], string=True),
    "way/191546277":  dict(no="?", mat="brick", col=GAULT, trim=GAULT_T, shops=["Harvey Jones", "Cancer Research UK"],
                           fas=["#24323c", "#2a1a5e"], string=True),
    "way/191546287":  dict(no="?", mat="brick", col=GAULT, trim=GAULT_T,
                           shops=["The Box Room", "Warhammer", "Salon 52", "Hidden Hearing", "Abbotts"],
                           fas=["#1f2a24", "#16181c", "#3a2f2a", "#22426e", "#6b1c24"]),
    "way/191546263":  dict(no="?", mat="render", col="#efe7d4", trim="#ffffff", shops=["Thomas William"],
                           fas=["#151515"]),
    "way/972907161":  dict(no="72?", mat="brick", col=GAULT, trim=GAULT_T, shops=["@72.China", "H&T Pawnbrokers"],
                           fas=["#7a1414", "#13305e"]),
    "way/191546270":  dict(no="?", mat="brick", col=GAULT, trim=GAULT_T, shops=["1+1 Rougamo", "Top Nails"],
                           fas=["#8a1d1d", "#2a2a2a"]),
    "way/191546271":  dict(no="?", mat="render", col="#f0e9d8", trim="#ffffff", shops=["Kung Woo"], fas=["#7a1a1a"]),
    "way/191546273":  dict(no="?", mat="brick", col=GAULT, trim=GAULT_T, shops=["Bould Brothers"], fas=["#3a4a3a"]),
    "way/191546279":  dict(no="?", mat="brick", col=REDB, trim=REDB_T, shops=["The Lab"], fas=["#141414"],
                           string=True),
    "way/191546269":  dict(no="?", mat="render", col="#e9dcc0", trim="#f8f4ea", shops=["Mr Wang Hot Pot"],
                           fas=["#8c1414"]),
    "way/191546280":  dict(no="96", mat="brick", col=GAULT, trim=GAULT_T, shops=["Reading Room"], fas=["#23344a"]),
    "way/191546284":  dict(no="?", mat="brick", col=GAULT, trim=GAULT_T, shops=["Rocca"], fas=["#2a2a2a"],
                           string=True),
    "way/191546291":  dict(no="?", mat="render", col="#efe6cf", trim="#ffffff", shops=["The Olive Grove"],
                           fas=["#3b4a2a"]),
    "way/191546293":  dict(no="102", mat="brick", col=GAULT, trim=GAULT_T, shops=["Regent Dental"], fas=["#e8e8e8"]),
    "way/191546288":  dict(no="?", mat="render", col="#f1ece0", trim="#ffffff", shops=["Old Bicycle Shop"],
                           fas=["#1e3a2e"]),
    "way/191546265":  dict(no="?", mat="brick", col=GAULT, trim=GAULT_T, shops=["The House", "The Chicken Shop"],
                           fas=["#1a1a1a", "#b0141a"], string=True),
    "way/191546266":  dict(no="112-116", mat="brick", col=REDB, trim=REDB_T, shops=["Toni & Remi", "ToothStation"],
                           fas=["#151515", "#e9eef2"], string=True),
    # south-west side (odd numbers)
    "way/137151163":  dict(no="41-45?", mat="brick", col=GAULT, trim=GAULT_T, shops=["The Regent", "Naked Kitchens"],
                           fas=["#13233a", "#1c1c1c"], string=True),
    "way/137151165":  dict(no="?", mat="brick", col=GAULT, trim=GAULT_T, shops=["Slim Chickens"], fas=["#1f3a5a"]),
    "way/137151151":  dict(no="?", mat="brick", col=REDB, trim=REDB_T, shops=["Zizzi"], fas=["#141414"], string=True),
    "way/137151176":  dict(no="?", mat="brick", col=GAULT, trim=GAULT_T, shops=["JWD Noodles"], fas=["#6e1a12"]),
    "way/137151152":  dict(no="Ravenscroft House", mat="render", col="#e6e0d2", trim="#f6f3ec",
                           shops=["Heartea Cherry", "Chickeez"], fas=["#7a2440", "#c0141a"]),
    "way/137151162":  dict(no="65", mat="brick", col=GAULT, trim=GAULT_T, shops=["VRXtra"], fas=["#1a1a2a"]),
    "way/137151161":  dict(no="?", mat="render", col="#efe6d0", trim="#ffffff", shops=["In Chá"], fas=["#2c4a3a"]),
    "way/137151158":  dict(no="71 Essex House", mat="brick", col="#b9a78a", trim="#e6e1d6",
                           shops=["Hi Sweety", "City Kebab", "Jiamart"], fas=["#c2577a", "#a01818", "#1d4e2e"],
                           modern=True),
    "way/137151157":  dict(no="?", mat="brick", col=GAULT, trim=GAULT_T,
                           shops=["Kim's Bulgogi", "Tom Howley", "Smart Services"], fas=["#2a2a2a", "#26354a", "#1a5a8a"]),
    "way/137151171":  dict(no="83?", mat="render", col="#e4e2dc", trim="#f4f4f2",
                           shops=["De Luca Cucina", "Kutchenhaus"], fas=["#1b1b1b", "#3a3a3a"], modern=True),
    "way/137151173":  dict(no="89", mat="brick", col=REDB, trim=REDB_T, shops=[], fas=["#2b2b2b"], string=True),
    "way/137151170":  dict(no="91 Prince Regent", mat="render", col="#f1ecdf", trim="#ffffff", shops=["Prince Regent"],
                           fas=["#1d3a2a"]),
    "way/1216816175": dict(no="93", mat="brick", col=GAULT, trim=GAULT_T, shops=[], fas=["#2b2b2b"], string=True),
    "way/1216816176": dict(no="95-97 Mantle", mat="brick", col="#b8a888", trim="#ecebe6", shops=["Mantle"],
                           fas=["#1c1c1c"], modern=True),
}

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
                if dd <= STREET_DIST and street.distance(Point(*(m + n * 2))) < dd:
                    s = min(segs, key=lambda s: s.distance(Point(*m)))
                    sc = np.array(s.coords)
                    sd = (sc[1] - sc[0]) / max(np.linalg.norm(sc[1] - sc[0]), 1e-6)
                    sf = abs(float(d @ sd)) >= 0.8
                W.append(dict(id=wid, osm_id=oid, tags=w.get("tags", {}), length=round(L, 2),
                              p0=[round(a[0] - B.E0, 2), round(a[1] - B.N0, 2)],
                              p1=[round(b[0] - B.E0, 2), round(b[1] - B.N0, 2)],
                              ground_z=round(gz, 2), eave_z=round(max(ez, gz + 2.5), 2),
                              height=round(max(ez - gz, 2.5), 2), street_facing=True, regent_st=sf, dist=round(float(dd), 2)))
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
LOW_H = 5.2


def _layout(w, sp, shop_names, fascias):
    L, H = w["length"], w["eave_z"] - w["ground_z"]
    low = H < LOW_H
    modern = bool(sp.get("modern"))
    shop = bool(sp.get("shops")) and L >= 2.6
    g = min(3.4, H - 0.45) if low else (3.4 if shop else 3.0)
    n_up = 0 if low else max(1, min(4, int(round((H - g - 0.5) / 2.9))))
    fh = ((H - g - 0.4) / n_up if H - g - 0.4 > 2.2 * n_up else 2.6) if n_up else 0.0
    floors = [0.0] + [g + i * fh for i in range(n_up)]
    els = []
    bay = 3.2 if modern else 2.3
    nb = max(1, int((L - 0.6) / bay)) if L >= 2.4 else (1 if L >= 1.8 else 0)
    xs = [L * (i + 0.5) / nb for i in range(nb)]
    for fi, z in enumerate(floors[1:]):
        top = fi == n_up - 1
        if modern:
            for x in xs:
                els.append({"type": "window", "style": "sash_georgian", "x": round(x, 2), "w": round(min(2.4, L / nb - 0.6), 2),
                            "z": round(z + 0.6, 2), "h": round(max(1.0, fh - 1.0), 2), "panes": [1, 2], "head": "flat",
                            "sill": False})
            continue
        h = max(1.0, min(1.75 if not top else 1.35, fh - 1.1))
        for x in xs:
            els.append({"type": "window", "style": "sash_georgian", "x": round(x, 2), "w": 0.95 if nb > 1 or L > 3 else 0.8,
                        "z": round(z + 0.75, 2), "h": round(h, 2), "panes": [3, 3] if sp["mat"] == "brick" else [2, 2],
                        "head": "flat", "sill": True})
    if shop:
        names = [n for n in shop_names] or [""]
        k = max(1, min(len(names), int(L / 5.0)))
        span = (L - 0.6) / k
        for j in range(k):
            x0 = 0.3 + j * span + (0.12 if j else 0.0)
            x1 = 0.3 + (j + 1) * span - (0.12 if j < k - 1 else 0.0)
            els.append({"type": "shopfront", "x0": round(x0, 2), "x1": round(x1, 2), "z1": round(g - 0.1, 2),
                        "fascia_text": names[j], "fascia_colour": fascias[min(j, len(fascias) - 1)],
                        "door_x": round(x0 + min(0.8, (x1 - x0) / 2), 2), "stallriser": 0.45, "awning": False})
    elif not low:
        for x in xs:
            els.append({"type": "window", "style": "sash_georgian", "x": round(x, 2), "w": 0.95, "z": 0.9, "h": 1.6,
                        "panes": [3, 3], "head": "flat", "sill": True})
        els.append({"type": "door", "style": "panelled", "x": round(min(1.0, L / 2), 2), "w": 1.0, "h": 2.3})
    lay = {"id": w["id"], "storeys": len(floors), "floor_z": [round(z, 2) for z in floors], "material": sp["mat"],
           "wall_colour": sp["col"], "trim_colour": sp["trim"], "cornice_z": round(H, 2),
           "cornice": "simple" if (sp["mat"] == "brick" or low) else "bracketed", "parapet": low or modern,
           "string_courses": [round(g, 2)] if sp.get("string") and not low else [], "quoins": False, "pilasters": [],
           "elements": els}
    return lay, floors, fh, xs, low


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
    street = sorted([w for w in ws if w["regent_st"] and w["length"] >= 3.0], key=lambda w: (round(w["dist"]), -w["length"]))
    named = {street[0]["id"]: True} if street else {}
    out = []
    for w in ws:
        L = float(w["length"])
        if L < 0.3:
            continue
        x0s, x1s = C["ext"].get(w["id"], (0.0, L))
        if w["regent_st"]:
            names = sp["shops"] if w["id"] in named else [""]
            lay, floors, fh, xs, low = _layout(w, sp, names, sp["fas"])
            H = max(w["eave_z"] - w["ground_z"], floors[-1] + 2.0)
            P = F.wall_facade(L, H, lay, x0s, x1s)
            for e in lay["elements"]:
                if e["type"] == "shopfront" and e.get("fascia_text") and \
                        min(e["x1"], x1s - 0.05) - max(e["x0"], x0s + 0.05) >= 1.0:
                    lettering(P, dict(e, x0=max(e["x0"], x0s + 0.05), x1=min(e["x1"], x1s - 0.05)), H)
            if not low:
                gutter(P, H, x0s, x1s)
            if L >= 3.0 and not low:
                chimneys(P, w, H, L)
            _ops(w, lay, P, L)
            ELEMENTS[w["id"]] = {k: P.counts.get(k, 0) for k in ("window", "door", "shopfront", "dormer")}
        else:
            H = w["eave_z"] - w["ground_z"]
            P = F.wall_facade(L, H, _style_layout(w), x0s, x1s)
        p0 = np.asarray(w["p0"], float)
        d = (np.asarray(w["p1"], float) - p0) / L
        it = frame_world(P, p0, d, "regentst:" + w["id"], z0=w["ground_z"])
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
        print(oid, SPEC[oid]["no"], n, [w["id"] for w in _CACHE["by"].get(oid, []) if w["regent_st"]])
    print("total", tot, "buildings", len(SPEC))
    print("street walls with ELEMENTS", len(ELEMENTS), sum(sum(v.values()) for v in ELEMENTS.values()), "openings")
