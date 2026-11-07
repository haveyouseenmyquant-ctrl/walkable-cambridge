"""Derive the fixed KPI targets (denominators) from the raw OSM extract.

Writes data/derived/osm_targets.json:
  - walk_samples: points every 5 m along every walkable way, clipped to the study area
  - buildings: every OSM building (building=* except building=no) whose centre is in the study area
  - grid: the 5 m ground-coverage grid definition

All coordinates are British National Grid (EPSG:27700) metres.
Usage: .venv/bin/python -I scripts/osm_targets.py [raw_overpass.json]
"""
import json
import os
import sys

from pyproj import Transformer
from shapely.geometry import LineString, MultiLineString, Point, Polygon, box, shape
from shapely.ops import polygonize, transform, unary_union

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "data/raw/osm/cambridge_overpass.json")
OUT = os.path.join(ROOT, "data/derived/osm_targets.json")

WALK_HIGHWAYS = {
    "footway", "pedestrian", "path", "steps", "living_street", "residential", "service",
    "unclassified", "tertiary", "secondary", "primary", "cycleway", "track",
}
SAMPLE_STEP = 5.0
GRID_STEP = 5.0

TO_BNG = Transformer.from_crs(4326, 27700, always_xy=True)


def to_bng(geom):
    return transform(lambda x, y, z=None: TO_BNG.transform(x, y), geom)


def main():
    area = json.load(open(os.path.join(ROOT, "area.geojson")))["features"][0]
    area_ll = shape(area["geometry"])
    area_bng = to_bng(area_ll)

    data = json.load(open(RAW))
    els = data["elements"]
    nodes = {e["id"]: (e["lon"], e["lat"]) for e in els if e["type"] == "node"}
    ways = {e["id"]: e for e in els if e["type"] == "way"}

    def way_coords(w):
        pts = [nodes[n] for n in w["nodes"] if n in nodes]
        return pts if len(pts) == len(w["nodes"]) else None

    # ---- walkable ways -> 5 m samples
    samples = []  # [x, y, way_id, length_weight]
    total_len = 0.0
    n_ways = 0
    missing = 0
    for w in ways.values():
        t = w.get("tags", {})
        if t.get("highway") not in WALK_HIGHWAYS or t.get("foot") == "no":
            continue
        c = way_coords(w)
        if c is None:
            missing += 1
            continue
        if len(c) < 2:
            continue
        line = to_bng(LineString(c)).intersection(area_bng)
        if line.is_empty:
            continue
        parts = [line] if line.geom_type == "LineString" else [g for g in getattr(line, "geoms", []) if g.geom_type == "LineString"]
        used = False
        for p in parts:
            L = p.length
            if L <= 0:
                continue
            used = True
            total_len += L
            n = max(1, int(round(L / SAMPLE_STEP)))
            # n points at the centres of n equal segments: each point stands for L/n metres
            for i in range(n):
                q = p.interpolate((i + 0.5) * L / n)
                samples.append([round(q.x, 2), round(q.y, 2), w["id"], round(L / n, 3)])
        n_ways += used

    # ---- buildings
    def rel_polygon(r):
        outers, inners = [], []
        for m in r.get("members", []):
            if m["type"] != "way" or m["ref"] not in ways:
                continue
            c = way_coords(ways[m["ref"]])
            if c is None or len(c) < 2:
                continue
            (inners if m.get("role") == "inner" else outers).append(LineString(c))
        if not outers:
            return None
        polys = list(polygonize(unary_union(outers)))
        if not polys:
            return None
        g = unary_union(polys)
        if inners:
            holes = list(polygonize(unary_union(inners)))
            if holes:
                g = g.difference(unary_union(holes))
        return g

    buildings = []
    for e in els:
        t = e.get("tags", {})
        if "building" not in t or t["building"] == "no":
            continue
        geom = None
        if e["type"] == "node":
            geom = Point(e["lon"], e["lat"])
        elif e["type"] == "way":
            c = way_coords(e)
            if c is None:
                continue
            geom = Polygon(c) if len(c) >= 4 and c[0] == c[-1] else LineString(c)
        elif e["type"] == "relation":
            geom = rel_polygon(e)
        if geom is None or geom.is_empty:
            continue
        gb = to_bng(geom)
        if gb.geom_type in ("Polygon", "MultiPolygon"):
            if not gb.is_valid:
                gb = gb.buffer(0)
            centre = gb.representative_point() if gb.is_empty else gb.centroid
        else:
            centre = gb.centroid
        if not area_bng.contains(centre):
            continue
        buildings.append({
            "osm_id": f"{e['type']}/{e['id']}",
            "building": t["building"],
            "name": t.get("name"),
            "centre": [round(centre.x, 2), round(centre.y, 2)],
            "footprint": json.loads(json.dumps(gb.__geo_interface__)) if gb.geom_type in ("Polygon", "MultiPolygon") else None,
            "osm_height": t.get("height"),
            "osm_levels": t.get("building:levels"),
        })

    minx, miny, maxx, maxy = area_bng.bounds
    out = {
        "crs": "EPSG:27700",
        "osm_timestamp": data["osm3s"]["timestamp_osm_base"],
        "area_bng_wkt": area_bng.wkt,
        "walk": {"total_length_m": round(total_len, 1), "n_ways": n_ways, "n_samples": len(samples),
                 "ways_with_missing_nodes": missing, "samples": samples},
        "buildings": buildings,
        "grid": {"step": GRID_STEP, "bounds": [minx, miny, maxx, maxy]},
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(out, open(OUT, "w"))
    print(json.dumps({"walk_total_km": round(total_len / 1000, 2), "walk_ways": n_ways, "walk_samples": len(samples),
                      "ways_missing_nodes": missing, "buildings": len(buildings),
                      "buildings_by_type": {k: sum(1 for b in buildings if b["osm_id"].startswith(k)) for k in ("node", "way", "relation")}}))


if __name__ == "__main__":
    main()
