"""Road markings from OSM (session 20): white centre dashes and double yellow kerb lines, per tile.

Writes site/markings/<tile>.bin: float32 records [x0, y0, x1, y1, kind] (collision frame, kind 0 = white centre
dash, 1 = yellow line), one per segment, and manifest tiles["markings"]; manifest.layers.markings = True.
The viewer (site/app/markings.js) drapes them on the ground mesh using the collision data.
Rules (a simplification of UK practice in central Cambridge):
- centre line (4 m dash, 5 m gap, TSRGD diagram 1004 style) on two-way primary/secondary/tertiary/unclassified roads
  and on residential roads tagged lanes >= 2;
- double yellow lines 0.3 m inside each edge of the modelled carriageway (build.py road_half) on primary to
  residential roads, unless OSM says parking:*=lane/street_side or the road is a bus/access-only street;
- no markings within 7 m of a junction (a node shared with another road), so lines don't cross at junctions.
Run after build.py, street_objects.py and facades.py (it only adds keys to the manifest).
"""
import json, os, sys
from collections import Counter
import numpy as np
from shapely.geometry import LineString, Point
from shapely.ops import unary_union

sys.path.insert(0, os.path.dirname(__file__))
import build as B

CENTRE = {"primary", "secondary", "tertiary", "unclassified"}
YELLOW = {"primary", "secondary", "tertiary", "unclassified", "residential"}
DASH, GAP, JUNC = 4.0, 5.0, 7.0


def main():
    nodes, ways, _, _ = B.load_osm()
    roads = [w for w in ways.values() if w.get("tags", {}).get("highway") in YELLOW
             and w["tags"].get("area") != "yes" and w["tags"].get("tunnel", "no") == "no"]
    rw = [w for w in ways.values() if w.get("tags", {}).get("highway") in B.ROAD_HALF]
    use = Counter(n for w in rw for n in set(w["nodes"]))
    inner = {n for w in rw for n in w["nodes"][1:-1]}
    # junction: a node on 3+ road ways, or on 2 where it is inside one of them (two ways that just continue each
    # other share an end node, which is not a junction)
    junc = [Point(nodes[n]) for n, c in use.items() if n in nodes and (c >= 3 or (c == 2 and n in inner))]
    jz = unary_union([p.buffer(JUNC) for p in junc]) if junc else None
    segs = []
    for w in roads:
        t = w["tags"]; hw = t["highway"]
        c = [nodes[n] for n in w["nodes"] if n in nodes]
        if len(c) < 2:
            continue
        ln = LineString(c)
        if jz is not None:
            ln = ln.difference(jz)
        parts = [g for g in getattr(ln, "geoms", [ln]) if g.length > 2]
        oneway = t.get("oneway", "no") in ("yes", "1", "-1")
        lanes = int(t.get("lanes", "0")) if t.get("lanes", "").isdigit() else 0
        centre = not oneway and (hw in CENTRE or lanes >= 2) and lanes != 1
        parking = any(v in ("lane", "street_side", "on_street", "half_on_kerb") for k, v in t.items() if k.startswith("parking"))
        yellow = not parking and t.get("access", "yes") not in ("no", "private", "destination")
        half = B.road_half(t) - 0.3
        for p in parts:
            if centre:
                d = 0.0
                while d + DASH <= p.length:
                    a, b = p.interpolate(d), p.interpolate(d + DASH)
                    segs.append((a.x, a.y, b.x, b.y, 0)); d += DASH + GAP
            if yellow:
                for side in ("left", "right"):
                    for off in (half, half - 0.2):
                        o = p.parallel_offset(off, side, join_style=2)
                        for g in getattr(o, "geoms", [o]):
                            xy = list(g.coords)
                            for (x0, y0), (x1, y1) in zip(xy, xy[1:]):
                                segs.append((x0, y0, x1, y1, 1))
    S = np.array(segs, np.float64)
    S[:, [0, 2]] -= B.E0; S[:, [1, 3]] -= B.N0
    S = S.astype(np.float32)
    man_p = os.path.join(B.OUT, "manifest.json")
    man = json.load(open(man_p))
    os.makedirs(os.path.join(B.OUT, "markings"), exist_ok=True)
    mx, my = (S[:, 0] + S[:, 2]) / 2, (S[:, 1] + S[:, 3]) / 2
    n = 0
    for tile in man["tiles"]:
        x0, y0, x1, y1 = tile["bounds"]
        sel = (mx >= x0) & (mx < x1) & (my >= y0) & (my < y1)
        tile.pop("markings", None)
        if sel.any():
            p = "markings/%s.bin" % tile["id"]
            S[sel].tofile(os.path.join(B.OUT, p)); tile["markings"] = p; n += int(sel.sum())
    man.setdefault("layers", {})["markings"] = True
    json.dump(man, open(man_p, "w"), separators=(",", ":"))
    print("markings: %d segments (%d centre dashes), %.1f km of yellow" % (
        n, int((S[:, 4] == 0).sum()), float(np.hypot(S[:, 2] - S[:, 0], S[:, 3] - S[:, 1])[S[:, 4] == 1].sum()) / 1000))


if __name__ == "__main__":
    main()
