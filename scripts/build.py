"""Build the browser world into site/: manifest.json, tiles/*.glb, collision/*.col (see FORMAT.md).

v1 ("complete and simple"):
  - ground: EA LiDAR DTM sampled on a 2 m grid per 250 m tile, each triangle classed from OSM
    (roads, footways, grass, water, squares, under-building); water is non-walkable.
  - buildings: every OSM building extruded from its lowest ground to median DTM + LiDAR P95 height,
    flat roof, solid walls. Walkable OSM ways that cross a building get a 2.6 m wide, ~3.5 m high
    passage cut through it (gate arches, building passages, arcades).
  - bridges: walkable ways tagged bridge=* get a deck interpolated between the ground at their ends.

Usage: .venv/bin/python -I scripts/build.py [--out site]
"""
import json
import math
import os
import struct
import sys
import time

import mapbox_earcut as earcut
import numpy as np
import rasterio
from pyproj import Transformer
from rasterio.features import geometry_mask, rasterize
from rasterio.windows import from_bounds
from scipy.ndimage import map_coordinates
from shapely import STRtree
from shapely.geometry import LineString, MultiPolygon, Point, Polygon, box, mapping
from shapely.ops import polygonize, unary_union

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
RAW = os.path.join(ROOT, "data/raw/osm/cambridge_overpass.json")
OUT = os.path.join(ROOT, sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else "site")
E0, N0 = 545000.0, 258400.0
TILE = 250.0
EXT = 1000.0          # world extent: [-EXT, EXT) in x and y (matches the LiDAR mosaic)
GSTEP = 2.0           # ground grid spacing (m)
PASS_W = 1.3          # half width of a cut passage (m)
PASS_H = 3.5          # passage clear height above median ground (m)

WALK = {"footway", "pedestrian", "path", "steps", "living_street", "residential", "service",
        "unclassified", "tertiary", "secondary", "primary", "cycleway", "track"}
ROAD_HALF = {"primary": 4.5, "secondary": 4.0, "tertiary": 3.5, "unclassified": 3.0, "residential": 3.0,
             "living_street": 2.5, "service": 2.0, "pedestrian": 3.0, "track": 1.5}
# surface classes (FORMAT.md)
S_ROAD, S_PAVE, S_GRASS, S_WATER, S_COURT, S_EARTH, S_STEPS, S_BRIDGE, S_UNDER = 1, 2, 3, 4, 5, 6, 7, 8, 9
COLORS = {S_ROAD: (0.32, 0.32, 0.34), S_PAVE: (0.62, 0.60, 0.56), S_GRASS: (0.33, 0.52, 0.24),
          S_WATER: (0.22, 0.36, 0.42), S_COURT: (0.66, 0.62, 0.55), S_EARTH: (0.50, 0.42, 0.31),
          S_STEPS: (0.60, 0.58, 0.54), S_BRIDGE: (0.55, 0.50, 0.45), S_UNDER: (0.5, 0.5, 0.5)}
GRASS = {"grass", "meadow", "recreation_ground", "village_green", "park", "garden", "pitch", "common",
         "grassland", "scrub", "wood", "forest", "cemetery", "allotments", "playground", "golf_course",
         "heath", "orchard", "nature_reserve"}
PAVED = {"square", "parking", "marketplace", "pedestrian", "plaza"}


def log(*a):
    print(f"[{time.strftime('%H:%M:%S')}]", *a, flush=True)


# ---------------------------------------------------------------- OSM
def load_osm():
    els = json.load(open(RAW))["elements"]
    tr = Transformer.from_crs(4326, 27700, always_xy=True)
    nids = [e["id"] for e in els if e["type"] == "node"]
    lon = np.array([e["lon"] for e in els if e["type"] == "node"])
    lat = np.array([e["lat"] for e in els if e["type"] == "node"])
    E, N = tr.transform(lon, lat)
    nodes = dict(zip(nids, zip(E, N)))
    ways = {e["id"]: e for e in els if e["type"] == "way"}
    rels = [e for e in els if e["type"] == "relation"]
    pnodes = [e for e in els if e["type"] == "node" and e.get("tags")]
    return nodes, ways, rels, pnodes


def coords(w, nodes):
    c = [nodes.get(n) for n in w["nodes"]]
    return None if any(p is None for p in c) else c


def way_area(w, nodes):
    c = coords(w, nodes)
    if not c or len(c) < 4 or c[0] != c[-1]:
        return None
    g = Polygon(c)
    return g if g.is_valid else g.buffer(0)


def rel_area(r, ways, nodes):
    outers, inners = [], []
    for m in r.get("members", []):
        if m["type"] == "way" and m["ref"] in ways:
            c = coords(ways[m["ref"]], nodes)
            if c and len(c) >= 2:
                (inners if m.get("role") == "inner" else outers).append(LineString(c))
    polys = list(polygonize(unary_union(outers))) if outers else []
    if not polys:
        return None
    g = unary_union(polys)
    if inners:
        holes = list(polygonize(unary_union(inners)))
        if holes:
            g = g.difference(unary_union(holes))
    return g if g.is_valid else g.buffer(0)


# ---------------------------------------------------------------- glTF / collision writers
def write_col(path, verts, tris, kind, surf):
    with open(path, "wb") as f:
        f.write(b"WCOL" + struct.pack("<III", 1, len(verts), len(tris)))
        f.write(np.asarray(verts, "<f4").tobytes())
        f.write(np.asarray(tris, "<u4").tobytes())
        f.write(np.asarray(kind, "u1").tobytes())
        f.write(np.asarray(surf, "u1").tobytes())


def write_glb(path, meshes):
    """meshes: list of (node_name, pos (n,3) Y-up, nrm (n,3), col (n,3), idx (m,))"""
    chunks, bin_len = [], 0
    js = {"asset": {"version": "2.0", "generator": "walkable-cambridge build.py",
                    "copyright": "© OpenStreetMap contributors; © Environment Agency copyright and/or database right 2022"},
          "scenes": [{"nodes": list(range(len(meshes)))}], "scene": 0, "nodes": [], "meshes": [],
          "materials": [{"pbrMetallicRoughness": {"baseColorFactor": [1, 1, 1, 1], "metallicFactor": 0, "roughnessFactor": 0.9}}],
          "accessors": [], "bufferViews": [], "buffers": []}
    for name, pos, nrm, col, idx in meshes:
        pos = np.asarray(pos, "<f4"); nrm = np.asarray(nrm, "<f4"); col = np.asarray(col, "<f4")
        idx = np.asarray(idx, "<u2" if len(pos) < 65536 else "<u4")
        acc = {}
        for key, arr, target in (("POSITION", pos, 34962), ("NORMAL", nrm, 34962), ("COLOR_0", col, 34962), ("idx", idx, 34963)):
            b = arr.tobytes()
            js["bufferViews"].append({"buffer": 0, "byteOffset": bin_len, "byteLength": len(b), "target": target})
            pad = b"\0" * (-len(b) % 4)
            chunks += [b, pad]; bin_len += len(b) + len(pad)
            a = {"bufferView": len(js["bufferViews"]) - 1, "count": len(arr)}
            if key == "idx":
                a.update(componentType=5123 if arr.dtype == np.dtype("<u2") else 5125, type="SCALAR")
            else:
                a.update(componentType=5126, type="VEC3")
                if key == "POSITION":
                    a.update(min=pos.min(0).tolist(), max=pos.max(0).tolist())
            js["accessors"].append(a)
            acc[key] = len(js["accessors"]) - 1
        js["meshes"].append({"primitives": [{"attributes": {k: acc[k] for k in ("POSITION", "NORMAL", "COLOR_0")},
                                             "indices": acc["idx"], "material": 0}]})
        js["nodes"].append({"name": name, "mesh": len(js["meshes"]) - 1})
    js["buffers"].append({"byteLength": bin_len})
    j = json.dumps(js, separators=(",", ":")).encode(); j += b" " * (-len(j) % 4)
    with open(path, "wb") as f:
        f.write(struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(j) + 8 + bin_len))
        f.write(struct.pack("<II", len(j), 0x4E4F534A) + j)
        f.write(struct.pack("<II", bin_len, 0x004E4942))
        for c in chunks:
            f.write(c)


class Mesh:
    """Accumulates triangles in the collision frame (x east, y north, z up), with flat normals and colours."""

    def __init__(self):
        self.p, self.n, self.c, self.kind, self.surf = [], [], [], [], []

    def tris(self, P, color, kind, surf=0):
        """P: (k,3,3) triangles, counter-clockwise seen from the outside."""
        P = np.asarray(P, float).reshape(-1, 3, 3)
        if not len(P):
            return
        nr = np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0])
        ln = np.linalg.norm(nr, axis=1, keepdims=True)
        nr = nr / np.maximum(ln, 1e-12)
        self.p.append(P.reshape(-1, 3)); self.n.append(np.repeat(nr, 3, 0))
        self.c.append(np.tile(np.asarray(color, float), (len(P) * 3, 1)))
        self.kind.append(np.full(len(P), kind, np.uint8)); self.surf.append(np.full(len(P), surf, np.uint8))

    def arrays(self):
        if not self.p:
            return None
        return (np.concatenate(self.p), np.concatenate(self.n), np.concatenate(self.c),
                np.concatenate(self.kind), np.concatenate(self.surf))


def to_gl(p):
    return np.stack([p[:, 0], p[:, 2], -p[:, 1]], 1)


def polys_of(g):
    if g is None or g.is_empty:
        return []
    if g.geom_type == "Polygon":
        return [g]
    return [q for q in getattr(g, "geoms", []) if q.geom_type == "Polygon" and q.area > 0.05]


def triangulate(poly):
    """Earcut a shapely polygon (BNG); returns (k,3,2) triangles in local frame, CCW."""
    rings = [np.asarray(poly.exterior.coords)[:-1]] + [np.asarray(r.coords)[:-1] for r in poly.interiors]
    rings = [r for r in rings if len(r) >= 3]
    if not rings:
        return np.zeros((0, 3, 2))
    v = np.concatenate(rings) - [E0, N0]
    ends = np.cumsum([len(r) for r in rings]).astype(np.uint32)
    idx = earcut.triangulate_float64(v, ends).reshape(-1, 3)
    T = v[idx]
    cr = (T[:, 1, 0] - T[:, 0, 0]) * (T[:, 2, 1] - T[:, 0, 1]) - (T[:, 1, 1] - T[:, 0, 1]) * (T[:, 2, 0] - T[:, 0, 0])
    T[cr < 0] = T[cr < 0][:, ::-1]
    return T


def add_prism(m, poly, z0, z1, color, roof_color, top=True, bottom=False):
    """Walls of all rings from z0 to z1 (solid), plus a roof at z1 and optionally an underside at z0."""
    p = poly if poly.exterior.is_ccw else Polygon(poly.exterior.coords[::-1], [r.coords for r in poly.interiors])
    rings = [np.asarray(p.exterior.coords)] + [np.asarray(r.coords)[::-1] if r.is_ccw else np.asarray(r.coords) for r in p.interiors]
    W = []
    for r in rings:
        r = r - [E0, N0]
        a, b = r[:-1], r[1:]
        A0 = np.c_[a, np.full(len(a), z0)]; B0 = np.c_[b, np.full(len(a), z0)]
        A1 = np.c_[a, np.full(len(a), z1)]; B1 = np.c_[b, np.full(len(a), z1)]
        W += [np.stack([A0, B0, B1], 1), np.stack([A0, B1, A1], 1)]
    if W:
        m.tris(np.concatenate(W), color, 0)
    T = triangulate(p)
    if len(T):
        if top:
            m.tris(np.concatenate([T, np.full((len(T), 3, 1), z1)], 2), roof_color, 0)
        if bottom:
            m.tris(np.concatenate([T[:, ::-1], np.full((len(T), 3, 1), z0)], 2), roof_color, 0)


def add_prism_local(m, g, z0, z1, color, roof_color):
    """add_prism for a (Multi)Polygon in the local frame."""
    from shapely.affinity import translate
    for p in polys_of(translate(g, E0, N0)):
        add_prism(m, p, z0, z1, color, roof_color)


def build_landmarks(bdata, ways, nodes, DTM, DSM, tf, dtm_at):
    """Procedural landmark detail (scripts/detail.py). Sets bd['lm'] for buildings; returns extra
    non-building landmark meshes (bridges) as dicts and the manifest landmark entries."""
    import detail as D
    from shapely.affinity import translate
    lms = json.load(open(os.path.join(ROOT, "landmarks/landmarks.json")))["landmarks"]
    by_oid = {bd["oid"]: bd for bd in bdata}
    extra, entries = [], []
    for l in lms:
        sp = D.SPECS.get(l["id"])
        bd = by_oid.get(l["osm_id"])
        e = dict(id=l["id"], name=l["name"], osm_id=l["osm_id"], detailed=False)
        if sp is None:
            entries.append(e); continue
        solid, deco = Mesh(), Mesh()
        if bd is not None:
            g = bd["g"]; dmed, base, top = bd["dmed"], bd["base"], bd["top"]
        else:
            kind, i = l["osm_id"].split("/")
            g = way_area(ways[int(i)], nodes) if kind == "way" and int(i) in ways else None
            if g is None:
                entries.append(e); continue
            c = g.centroid
            dmed = float(dtm_at([c.x], [c.y])[0]); base = dmed - 0.3; top = dmed + 3
        gl = translate(g, -E0, -N0)
        if gl.geom_type != "Polygon":
            gl = max(gl.geoms, key=lambda q: q.area)
        ctx = D.Ctx(gl, dmed, base, top, DTM, DSM, tf, E0, N0)
        ctx.wall = sp["wall"]
        st = sp["style"]
        if st == "gothic":
            res = D.gothic(solid, deco, ctx, sp)
        elif st == "classical":
            res = D.classical(solid, deco, ctx, sp)
        elif st == "brick_hall":
            res = D.brick_hall(solid, deco, ctx, sp)
        elif st == "round":
            res = D.round_church(solid, deco, ctx, sp)
        elif st == "gate":
            res = D.gate(solid, deco, ctx, sp)
        elif st == "gate_tower":
            gn = nodes.get(443675369)
            res = D.gate_tower(deco, deco, ctx, sp, None if gn is None else (gn[0] - E0, gn[1] - N0))
        elif st == "bridge":
            ends = [ctx.c + ctx.u * s * (ctx.L + 3.0) for s in (-1, 1)]
            dz = float(max(dtm_at([q[0] + E0 for q in ends], [q[1] + N0 for q in ends]))) + 0.05
            res = D.bridge(deco, deco, ctx, sp, dz)
        else:
            res = None
        if res is None:
            entries.append(e); continue
        feats = [f for f in res["features"] if f]
        e.update(detailed=True, style=st, features=feats, screenshot=f"landmarks/{l['id']}.png",
                 x=round(ctx.c[0], 1), y=round(ctx.c[1], 1), look_z=round(dmed, 1),
                 size=round(float(ctx.L), 1), view=sp.get("front", 150))
        entries.append(e)
        lm = dict(solid=solid.arrays(), deco=deco.arrays(), keep_body=st in ("gate_tower",) or bd is None)
        if bd is not None:
            bd["lm"] = lm
        else:
            extra.append(dict(id=l["id"], cx=ctx.c[0], cy=ctx.c[1], lm=lm))
    log(sum(e["detailed"] for e in entries), "landmarks detailed")
    return extra, entries


# ---------------------------------------------------------------- main
def main():
    t0 = time.time()
    nodes, ways, rels, pnodes = load_osm()
    log("osm loaded", len(nodes), "nodes", len(ways), "ways")
    world = box(E0 - EXT, N0 - EXT, E0 + EXT, N0 + EXT)

    # ---- classify OSM features
    buildings, water, grass, paved = [], [], [], []
    road_lines, walk_lines, bridges = [], [], []
    for w in ways.values():
        t = w.get("tags", {})
        if not t:
            continue
        hw = t.get("highway")
        if hw:
            c = coords(w, nodes)
            if c and len(c) >= 2:
                ln = LineString(c)
                if hw in WALK and t.get("foot") != "no":
                    walk_lines.append((ln, t))
                    if t.get("bridge", "no") != "no" and t.get("layer", "1") not in ("-1", "-2"):
                        bridges.append((ln, t))
                if hw in ROAD_HALF or hw in WALK:
                    road_lines.append((ln, t))
            if t.get("area") == "yes" or t.get("area:highway"):
                g = way_area(w, nodes)
                if g is not None:
                    paved.append(g)
        g = None
        if "building" in t and t["building"] != "no":
            g = way_area(w, nodes)
            if g is None:
                c = coords(w, nodes)
                if c and len(c) >= 2:
                    g = LineString(c).buffer(0.75)
            if g is not None and g.area > 0.5:
                buildings.append((f"way/{w['id']}", g, t))
            continue
        if t.get("natural") == "water" or t.get("waterway") == "riverbank" or t.get("water"):
            g = way_area(w, nodes)
            if g is not None:
                water.append(g)
        elif t.get("landuse") in GRASS or t.get("leisure") in GRASS or t.get("natural") in GRASS:
            g = way_area(w, nodes)
            if g is not None:
                grass.append(g)
        elif t.get("place") == "square" or t.get("amenity") in PAVED:
            g = way_area(w, nodes)
            if g is not None:
                paved.append(g)
    for r in rels:
        t = r.get("tags", {})
        if t.get("type") not in ("multipolygon", "building", None):
            continue
        if "building" in t and t["building"] != "no":
            g = rel_area(r, ways, nodes)
            if g is not None and g.area > 0.5:
                buildings.append((f"relation/{r['id']}", g, t))
        elif t.get("natural") == "water" or t.get("waterway") == "riverbank" or t.get("water"):
            g = rel_area(r, ways, nodes)
            if g is not None:
                water.append(g)
        elif t.get("landuse") in GRASS or t.get("leisure") in GRASS or t.get("natural") in GRASS:
            g = rel_area(r, ways, nodes)
            if g is not None:
                grass.append(g)
        elif t.get("place") == "square" or t.get("amenity") in PAVED or t.get("highway") == "pedestrian":
            g = rel_area(r, ways, nodes)
            if g is not None:
                paved.append(g)
    for n in pnodes:
        t = n["tags"]
        if "building" in t and t["building"] != "no":
            buildings.append((f"node/{n['id']}", Point(nodes[n["id"]]).buffer(4.0, cap_style=3), t))
    buildings = [b for b in buildings if b[1].intersects(world)]
    log(len(buildings), "buildings,", len(walk_lines), "walk ways,", len(bridges), "bridges,", len(water), "water,", len(grass), "grass")

    # ---- LiDAR
    dtm_r = rasterio.open(os.path.join(ROOT, "data/lidar/dtm_1m.tif"))
    dsm_r = rasterio.open(os.path.join(ROOT, "data/lidar/dsm_1m.tif"))
    DTM = dtm_r.read(1).astype("f8")
    DSM = dsm_r.read(1).astype("f8")
    tf = dtm_r.transform
    LEFT, TOP = tf.c, tf.f

    def dtm_at(E, N):
        return map_coordinates(DTM, [TOP - np.asarray(N) - 0.5, np.asarray(E) - LEFT - 0.5], order=1, mode="nearest")

    # ---- surface class raster (1 m, same grid as the DTM); later layers win
    shp = DTM.shape
    cls = np.full(shp, S_COURT, np.uint8)   # default: paved urban ground (yards, forecourts)

    def burn(geoms, val):
        geoms = [mapping(g) for g in geoms if g is not None and not g.is_empty]
        if geoms:
            rasterize([(g, val) for g in geoms], out=cls, transform=tf, all_touched=False)

    burn(grass, S_GRASS)
    burn(paved, S_COURT)
    burn([ln.buffer(ROAD_HALF[t["highway"]]) for ln, t in road_lines if t["highway"] in ROAD_HALF and t["highway"] not in ("pedestrian", "track")], S_ROAD)
    burn([ln.buffer(ROAD_HALF[t["highway"]]) for ln, t in road_lines if t["highway"] in ("pedestrian",)], S_PAVE)
    burn([ln.buffer(1.0) for ln, t in walk_lines if t["highway"] in ("footway", "cycleway", "path", "track")
          and t.get("surface") in ("dirt", "earth", "ground", "grass", "gravel", "fine_gravel", "compacted", "unpaved")], S_EARTH)
    burn([ln.buffer(1.0) for ln, t in walk_lines if t["highway"] in ("footway", "cycleway", "path")
          and t.get("surface") not in ("dirt", "earth", "ground", "grass", "gravel", "fine_gravel", "compacted", "unpaved")], S_PAVE)
    burn([ln.buffer(1.0) for ln, t in walk_lines if t["highway"] == "steps"], S_STEPS)
    burn(water, S_WATER)
    # connector repairs (scripts/connectors.py): unmapped doors/culverts into sealed walkable pockets
    cpath = os.path.join(ROOT, "data/derived/connectors.json")
    conns = [LineString(c["line"]) for c in json.load(open(cpath))["connectors"]] if os.path.exists(cpath) else []
    conn_bufs = [ln.buffer(PASS_W) for ln in conns]
    burn(conn_bufs, S_PAVE)
    burn([g for _, g, _ in buildings], S_UNDER)
    log("class raster done", np.bincount(cls.ravel(), minlength=10).tolist())

    # ---- building heights and passages
    tree = STRtree([ln for ln, _ in walk_lines])
    walk_geoms = [ln for ln, _ in walk_lines]
    bdata = []
    rng = np.random.default_rng(1)
    for oid, g, t in buildings:
        x0, y0, x1, y1 = g.bounds
        win = from_bounds(x0 - 1, y0 - 1, x1 + 1, y1 + 1, tf).round_offsets().round_lengths()
        r0, c0 = int(win.row_off), int(win.col_off)
        r0c, c0c = max(r0, 0), max(c0, 0)
        r1, c1 = min(r0 + int(win.height), shp[0]), min(c0 + int(win.width), shp[1])
        dmed = dmin = p95 = None
        if r1 > r0c and c1 > c0c:
            a = DTM[r0c:r1, c0c:c1]; s = DSM[r0c:r1, c0c:c1]
            wtf = rasterio.transform.from_origin(LEFT + c0c, TOP - r0c, 1, 1)
            m = geometry_mask([mapping(g)], a.shape, wtf, invert=True)
            if m.sum() == 0:
                m = geometry_mask([mapping(g)], a.shape, wtf, invert=True, all_touched=True)
            if m.sum():
                dmed, dmin = float(np.median(a[m])), float(a[m].min())
                p95 = float(np.percentile(s[m] - a[m], 95))
        if dmed is None:
            c = g.centroid
            dmed = dmin = float(dtm_at([c.x], [c.y])[0])
        h = p95
        if h is None or h < 2.5:
            try:
                h = float(str(t.get("height", "")).split()[0])
            except (ValueError, IndexError):
                lv = t.get("building:levels")
                h = 3.0 * float(lv) + 1.0 if lv and lv.replace(".", "").isdigit() else max(h or 0, 3.0)
            h = max(h, 2.5)
        top = dmed + h
        base = dmin - 0.3
        # passages for walkable ways that cross the building interior
        cuts = []
        inner = g.buffer(-0.3)
        if not inner.is_empty:
            for i in tree.query(g, predicate="intersects"):
                seg = walk_geoms[i].intersection(inner)
                if seg.length > 0.3:
                    cuts.append(seg.buffer(PASS_W))
        for cb in conn_bufs:
            if cb.intersects(g):
                cuts.append(cb.intersection(g))
        cut = unary_union(cuts) if cuts else None
        zcut = None
        if cut is not None and not cut.is_empty:   # passage ceiling clears the highest ground in the cut
            bx0, by0, bx1, by1 = cut.bounds
            gx, gy = np.meshgrid(np.arange(bx0, bx1 + 1, 1.0), np.arange(by0, by1 + 1, 1.0))
            zcut = float(dtm_at(gx.ravel(), gy.ravel()).max())
        c = g.representative_point()
        bdata.append(dict(oid=oid, g=g, t=t, top=top, base=base, dmed=dmed, cut=cut, zcut=zcut, cx=c.x - E0, cy=c.y - N0,
                          tone=rng.uniform(-0.06, 0.06)))
    log("building heights done", sum(b["cut"] is not None for b in bdata), "with passages")

    lm_extra, lm_entries = build_landmarks(bdata, ways, nodes, DTM, DSM, tf, dtm_at)

    # ---- spawn: Market Square (Market Hill), nearest walkable way point
    sp_e, sp_n = Transformer.from_crs(4326, 27700, always_xy=True).transform(0.11894, 52.20563)
    best = min(walk_geoms, key=lambda ln: ln.distance(Point(sp_e, sp_n)))
    q = best.interpolate(best.project(Point(sp_e, sp_n)))
    spawn = {"x": round(q.x - E0, 2), "y": round(q.y - N0, 2), "z": round(float(dtm_at([q.x], [q.y])[0]), 2)}

    # ---- tiles
    os.makedirs(os.path.join(OUT, "tiles"), exist_ok=True)
    os.makedirs(os.path.join(OUT, "collision"), exist_ok=True)
    tiles, man_b = [], []
    nt = int(2 * EXT / TILE)
    for ty in range(nt):
        for tx in range(nt):
            tid = f"t_{tx}_{ty}"
            bx0, by0 = -EXT + tx * TILE, -EXT + ty * TILE
            bx1, by1 = bx0 + TILE, by0 + TILE
            # ground grid
            xs = np.arange(bx0, bx1 + 1e-6, GSTEP); ys = np.arange(by0, by1 + 1e-6, GSTEP)
            X, Y = np.meshgrid(xs, ys)
            Z = dtm_at((X + E0).ravel(), (Y + N0).ravel()).reshape(X.shape)
            nx, ny = len(xs), len(ys)
            ids = np.arange(nx * ny).reshape(ny, nx)
            a, b, c, d = ids[:-1, :-1].ravel(), ids[:-1, 1:].ravel(), ids[1:, 1:].ravel(), ids[1:, :-1].ravel()
            gtri = np.concatenate([np.stack([a, b, c], 1), np.stack([a, c, d], 1)])
            V = np.stack([X.ravel(), Y.ravel(), Z.ravel()], 1)
            cen = V[gtri].mean(1)
            ci = np.clip((TOP - (cen[:, 1] + N0)).astype(int), 0, shp[0] - 1)
            cj = np.clip((cen[:, 0] + E0 - LEFT).astype(int), 0, shp[1] - 1)
            gsurf = cls[ci, cj]
            gkind = np.where(gsurf == S_WATER, 2, 1).astype(np.uint8)
            # vertex colours from the class at each vertex; normals from the DTM gradient
            vi = np.clip((TOP - (V[:, 1] + N0)).astype(int), 0, shp[0] - 1)
            vj = np.clip((V[:, 0] + E0 - LEFT).astype(int), 0, shp[1] - 1)
            lut = np.array([COLORS.get(k, (0.5, 0.5, 0.5)) for k in range(256)])
            vcol = lut[cls[vi, vj]]
            gy, gx = np.gradient(Z, GSTEP)
            vn = np.stack([-gx.ravel(), -gy.ravel(), np.ones(nx * ny)], 1)
            vn /= np.linalg.norm(vn, axis=1, keepdims=True)

            m = Mesh()
            col_parts = []
            glb_meshes = [("ground", to_gl(V), to_gl(vn), vcol, gtri.ravel())]
            # bridges whose midpoint is in this tile
            for ln, t in bridges:
                mp = ln.interpolate(0.5, normalized=True)
                if not (bx0 <= mp.x - E0 < bx1 and by0 <= mp.y - N0 < by1):
                    continue
                L = ln.length
                n = max(2, int(math.ceil(L / 1.0)) + 1)
                pts = np.array([ln.interpolate(s).coords[0] for s in np.linspace(0, L, n)]) - [E0, N0]
                za, zb = dtm_at([pts[0, 0] + E0, pts[-1, 0] + E0], [pts[0, 1] + N0, pts[-1, 1] + N0])
                zz = np.linspace(za, zb, n) + 0.05
                try:
                    half = max(1.2, float(str(t.get("width", "")).split()[0]) / 2)
                except (ValueError, IndexError):
                    half = ROAD_HALF.get(t["highway"], 1.5)
                tg = np.gradient(pts, axis=0); tg /= np.maximum(np.linalg.norm(tg, axis=1, keepdims=True), 1e-9)
                nr = np.stack([-tg[:, 1], tg[:, 0]], 1) * half
                Lp = np.c_[pts + nr, zz]; Rp = np.c_[pts - nr, zz]
                T = np.concatenate([np.stack([Rp[:-1], Rp[1:], Lp[1:]], 1), np.stack([Rp[:-1], Lp[1:], Lp[:-1]], 1)])
                m.tris(T, COLORS[S_BRIDGE], 1, S_BRIDGE)
                # underside so it shows from below
                m.tris(np.concatenate([T[:, ::-1]]) - [0, 0, 0.3], COLORS[S_BRIDGE], 1, S_BRIDGE)
            bridge_arr = m.arrays()
            if bridge_arr is not None:
                p, nrm, colr, k, s = bridge_arr
                glb_meshes.append(("bridges", to_gl(p), to_gl(nrm), colr, np.arange(len(p))))
                col_parts.append((p, k, s))
            # buildings whose representative point is in this tile
            for bd in bdata:
                if not (bx0 <= bd["cx"] < bx1 and by0 <= bd["cy"] < by1):
                    continue
                bm = Mesh()
                tone = bd["tone"]
                wall = np.clip(np.array([0.78, 0.72, 0.60]) + tone, 0, 1)
                roof = np.clip(np.array([0.45, 0.40, 0.38]) + tone, 0, 1)
                g, cut, z0, z1 = bd["g"], bd["cut"], bd["base"], bd["top"]
                zp = max(bd["dmed"] + PASS_H, (bd["zcut"] or -1e9) + 2.6)
                if cut is None:
                    for p in polys_of(g):
                        add_prism(bm, p, z0, z1, wall, roof)
                else:
                    low = g.difference(cut)
                    if z1 - zp > 1.0:
                        for p in polys_of(low):
                            add_prism(bm, p, z0, zp, wall, roof, top=False)
                        for p in polys_of(g):
                            add_prism(bm, p, zp, z1, wall, roof, bottom=True)
                    else:
                        for p in polys_of(low):
                            add_prism(bm, p, z0, z1, wall, roof)
                arr = bm.arrays()
                if arr is None:
                    continue
                p, nrm, colr, k, s = arr
                node = "b:" + bd["oid"]
                col_parts.append((p, k, s))   # collision keeps the plain body (passages, walls)
                lm = bd.get("lm")
                if lm:
                    parts = ([arr] if lm["keep_body"] or bd["cut"] is not None else []) + [a for a in (lm["solid"], lm["deco"]) if a is not None]
                    p, nrm, colr = (np.concatenate([a[i] for a in parts]) for i in range(3))
                glb_meshes.append((node, to_gl(p), to_gl(nrm), colr, np.arange(len(p))))
                man_b.append({"osm_id": bd["oid"], "tile": tid, "node": node, "detailed": bool(lm),
                              "name": bd["t"].get("name"), "height": round(z1 - bd["dmed"], 1)})
            for ex in lm_extra:
                if bx0 <= ex["cx"] < bx1 and by0 <= ex["cy"] < by1:
                    parts = [a for a in (ex["lm"]["solid"], ex["lm"]["deco"]) if a is not None]
                    p, nrm, colr = (np.concatenate([a[i] for a in parts]) for i in range(3))
                    glb_meshes.append(("lm:" + ex["id"], to_gl(p), to_gl(nrm), colr, np.arange(len(p))))
                    for e in lm_entries:
                        if e["id"] == ex["id"]:
                            e["tile"], e["node"] = tid, "lm:" + ex["id"]
            # collision: ground (indexed) + everything else (unindexed)
            cv, ct, ck, cs = [V], [gtri], [gkind], [gsurf]
            off = len(V)
            for p, k, s in col_parts:
                cv.append(p); ct.append(np.arange(len(p)).reshape(-1, 3) + off); ck.append(k); cs.append(s)
                off += len(p)
            write_col(os.path.join(OUT, "collision", tid + ".col"), np.concatenate(cv), np.concatenate(ct),
                      np.concatenate(ck), np.concatenate(cs))
            write_glb(os.path.join(OUT, "tiles", tid + ".glb"), glb_meshes)
            tiles.append({"id": tid, "bounds": [bx0, by0, bx1, by1], "glb": f"tiles/{tid}.glb", "collision": f"collision/{tid}.col"})
        log("tile row", ty, "done")

    for e in lm_entries:   # landmarks that are buildings: tile/node from the building entry
        for b in man_b:
            if b["osm_id"] == e["osm_id"] and "node" not in e:
                e["tile"], e["node"] = b["tile"], b["node"]
    json.dump({"landmarks": lm_entries}, open(os.path.join(OUT, "landmarks.json"), "w"), indent=1)

    man = {"version": 1, "origin": {"crs": "EPSG:27700", "e0": E0, "n0": N0}, "spawn": spawn,
           "built": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "tiles": tiles, "buildings": man_b,
           "landmarks": lm_entries}
    json.dump(man, open(os.path.join(OUT, "manifest.json"), "w"), separators=(",", ":"))
    log(f"done: {len(tiles)} tiles, {len(man_b)} buildings, spawn {spawn}, {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
