"""Write a synthetic build to data/testbuild/ to sanity-check the KPI harness.

Flat walkable ground at 10 m everywhere, except a 50 m-wide north-south strip of water
(non-walkable) at x = -200..-150 that cuts off the west of the area, and one real OSM
building extruded 15 m with solid walls. Expected: ground ~100 %, walkable < 100 %
(points west of the water and inside the building are lost), buildings = 1 / total.
"""
import json
import os
import struct

import numpy as np
from shapely.geometry import shape

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data/testbuild")
E0, N0 = 545000.0, 258400.0


def write_col(path, verts, tris, kind, surf):
    with open(path, "wb") as f:
        f.write(b"WCOL" + struct.pack("<III", 1, len(verts), len(tris)))
        f.write(np.asarray(verts, "<f4").tobytes())
        f.write(np.asarray(tris, "<u4").tobytes())
        f.write(np.asarray(kind, "u1").tobytes())
        f.write(np.asarray(surf, "u1").tobytes())


def write_glb(path, meshes):
    """meshes: list of (node_name, positions (n,3) glTF Y-up, indices (m,))"""
    bin_ = b""
    js = {"asset": {"version": "2.0"}, "scenes": [{"nodes": list(range(len(meshes)))}], "scene": 0,
          "nodes": [], "meshes": [], "accessors": [], "bufferViews": [], "buffers": []}
    for name, pos, idx in meshes:
        pos = np.asarray(pos, "<f4"); idx = np.asarray(idx, "<u4")
        for arr, target in ((pos, 34962), (idx, 34963)):
            js["bufferViews"].append({"buffer": 0, "byteOffset": len(bin_), "byteLength": arr.nbytes, "target": target})
            bin_ += arr.tobytes()
            bin_ += b"\0" * (-len(bin_) % 4)
        nb = len(js["bufferViews"])
        js["accessors"].append({"bufferView": nb - 2, "componentType": 5126, "count": len(pos), "type": "VEC3",
                                "min": pos.min(0).tolist(), "max": pos.max(0).tolist()})
        js["accessors"].append({"bufferView": nb - 1, "componentType": 5125, "count": len(idx), "type": "SCALAR"})
        na = len(js["accessors"])
        js["meshes"].append({"primitives": [{"attributes": {"POSITION": na - 2}, "indices": na - 1}]})
        js["nodes"].append({"name": name, "mesh": len(js["meshes"]) - 1})
    js["buffers"].append({"byteLength": len(bin_)})
    j = json.dumps(js).encode(); j += b" " * (-len(j) % 4)
    with open(path, "wb") as f:
        f.write(struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(j) + 8 + len(bin_)))
        f.write(struct.pack("<II", len(j), 0x4E4F534A) + j)
        f.write(struct.pack("<II", len(bin_), 0x004E4942) + bin_)


def main():
    tg = json.load(open(os.path.join(ROOT, "data/derived/osm_targets.json")))
    os.makedirs(os.path.join(OUT, "tiles"), exist_ok=True)
    os.makedirs(os.path.join(OUT, "collision"), exist_ok=True)
    verts, tris, kind, surf = [], [], [], []
    step = 10.0
    for x in np.arange(-1100, 1100, step):
        for y in np.arange(-1100, 1100, step):
            b = len(verts)
            verts += [(x, y, 10), (x + step, y, 10), (x + step, y + step, 10), (x, y + step, 10)]
            tris += [(b, b + 1, b + 2), (b, b + 2, b + 3)]
            water = -200 <= x < -150
            kind += [2 if water else 1] * 2
            surf += [4 if water else 1] * 2
    # one real building: the largest polygon footprint
    bld = max((b for b in tg["buildings"] if b["footprint"] and b["footprint"]["type"] == "Polygon"),
              key=lambda b: shape(b["footprint"]).area)
    ring = np.array(shape(bld["footprint"]).exterior.coords)[:-1] - [E0, N0]
    gl_pos, gl_idx = [], []
    for i in range(len(ring)):
        a, c = ring[i], ring[(i + 1) % len(ring)]
        b = len(verts)
        verts += [(a[0], a[1], 10), (c[0], c[1], 10), (c[0], c[1], 25), (a[0], a[1], 25)]
        tris += [(b, b + 1, b + 2), (b, b + 2, b + 3)]
        kind += [0, 0]; surf += [0, 0]
        g = len(gl_pos)
        gl_pos += [(a[0], 10, -a[1]), (c[0], 10, -c[1]), (c[0], 25, -c[1]), (a[0], 25, -a[1])]
        gl_idx += [g, g + 1, g + 2, g, g + 2, g + 3]
    write_col(os.path.join(OUT, "collision/t0.col"), verts, tris, kind, surf)
    write_glb(os.path.join(OUT, "tiles/t0.glb"), [("b:" + bld["osm_id"], gl_pos, gl_idx)])
    man = {"version": 1, "origin": {"crs": "EPSG:27700", "e0": E0, "n0": N0},
           "spawn": {"x": 300.0, "y": 0.0, "z": 11.7},
           "tiles": [{"id": "t0", "bounds": [-1100, -1100, 1100, 1100], "glb": "tiles/t0.glb", "collision": "collision/t0.col"}],
           "buildings": [{"osm_id": bld["osm_id"], "tile": "t0", "node": "b:" + bld["osm_id"], "detailed": False}],
           "landmarks": []}
    json.dump(man, open(os.path.join(OUT, "manifest.json"), "w"), indent=1)
    print("test build written; building", bld["osm_id"], bld.get("name"), "area", round(shape(bld["footprint"]).area))


if __name__ == "__main__":
    main()
