"""Street lamps and bollards on King's Parade, Senate House Hill, Bene't Street and Market Hill (session 39).

    .venv/bin/python -I scripts/zone_props_streetlights.py      # prints a summary (objects by kind, triangles)

build() -> list of {"name", "tris" (k,3,3) collision-frame triangles, "col", "mat"} -- merged into
site/zone/market_square.glb by scripts/zone_build.py (loads every scripts/zone_props*.py). Render only.

OSM maps almost no lamps or bollards here. Positions come from:
- Mapillary map features (object--street-light point detections, triangulated by Mapillary from its CC BY-SA
  imagery; graph.mapillary.com/map_features, queried 2026-11-08). Accuracy is poor (several metres), so each is
  snapped to the nearby kerb line (road_half from build.py + 0.5 m) of the street it belongs to.
- Non-held-out Mapillary reference photos in data/raw/mapillary_ref (CC BY-SA 4.0):
  189066929702180 (2015, east footway of King's Parade at No. 22 looking S): tall slim pale-grey lamp columns
  with small lantern tops and banner brackets stand at the EAST footway kerb, roughly 20 m apart; a black bollard
  stands at the WEST kerb in front of King's.
  541914280138693 (2020, Senate House Hill looking S): a curved line of ~12 black cast-iron cap-top bollards along
  the WEST kerb from the Senate House railings to the start of King's Parade, ~2.5 m apart; two more on the east
  footway corner by St Mary's Passage / 22 King's Parade.
  NB: in these photos the King's Parade bollard line is on the west (King's College) kerb, not the east one.
- Distances read from those photos by pinhole back-projection (fov ~65 deg, eye 1.5 m): +-2 m across, +-4 m along.
Not duplicated: OSM barrier=bollard / highway=street_lamp nodes from street_objects.py (anything within 1.5 m of
one is dropped) and zone_props_furniture.PHOTO_LAMPS (Market Hill detections within 12 m of one are not used).
Models: bollard() from zone_props_furniture (black cast-iron, cap); Market Hill lamps use its twin_lamp();
King's Parade / Bene't St columns get their own kp_lamp() (pale grey ~8 m column, top lantern, banner arms).
Ground: zone_props.Ground (DTM 3x3 median).
"""
import json
import math
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from zone_props import E0, N0, Ground  # noqa: E402
from zone_props_furniture import Mesh, bollard, twin_lamp, PHOTO_LAMPS  # noqa: E402

GREY = (0.40, 0.42, 0.43)        # King's Parade columns read pale/mid grey in 189066929702180 (sunlit)
LIT = (0.93, 0.90, 0.78)

# King's Parade centreline (OSM way 3993048, collision frame) -- the kerbs module puts its kerbs at road_half 2.5 m.
KP = [(-195.4, -114.2), (-195.2, -96.9), (-194.9, -76.5), (-194.3, -61.2), (-193.4, -49.3), (-193.1, -45.2),
      (-191.9, -26.5), (-184.4, 32.7), (-182.7, 45.1), (-183.4, 67.3)]   # + Senate House Hill (way 4615503)
BENET = [(-100.2, -59.8), (-105.1, -67.8), (-128.4, -81.3), (-134.7, -84.9), (-147.8, -92.5), (-155.9, -96.7),
         (-168.2, -103.2), (-181.5, -109.5), (-195.4, -114.2)]   # OSM way 3993043

# lamps: (street, y or x along, side offset from the centreline in m: + = east/left of travel direction north)
KP_LAMPS_Y = [13.0, -9.0, -30.0, -50.0, -70.0, -90.0]
#  13, -9: read from 189066929702180 (first column ~12 m ahead, second ~34 m) -- +-4 m along;
#  -16.5 / 0.2 Mapillary map features 466714004428958 / 466681921098833 agree within ~5 m; further south the
#  ~20 m spacing is continued to Bene't Street (low confidence on exact spots; columns do line the east kerb).
BENET_LAMPS = [(-169.7, -96.6), (-144.5, -84.4)]   # Mapillary map features 2020 (raw, before kerb snapping)
#  (-134.2,-79.3) dropped: 11 m from the second, likely the same column seen from a different sequence.
MH_LAMPS = [(-118.5, 32.4, 1), (-122.9, 49.5, 2)]   # Market Hill west side, south part: map features
#  750565015608327, 750485985616230 (2017). Not snapped (square edge, no carriageway kerb). +-3 m.
# bollards (collision frame): west kerb of Senate House Hill -> King's Parade north end (541914280138693),
# generated along the centreline at -4.0 m (west) every 2.5 m for y 34..66.5; low confidence on the exact count.
SHH_BOLLARD_Y = (34.0, 66.5, 2.5)
KP_WEST_BOLLARD_Y = (-60.0, 30.0, 8.0)   # sparse line along King's lawn kerb (189066929702180); +-3 m along
EXTRA_BOLLARDS = [(-180.8, 54.8), (-180.6, 49.7)]   # east corner by St Mary's Passage (541914280138693), +-2 m


def kp_lamp(m):
    """Slim tapered column ~8 m, base collar, small cylindrical lantern with hood and finial, two banner arms."""
    m.cyl(0, 0, 0.0, 0.6, 0.14, 0.12, n=8, col=GREY)
    m.cyl(0, 0, 0.6, 7.6, 0.085, 0.055, n=8, col=GREY, cap=False)
    m.cyl(0, 0, 7.6, 7.7, 0.09, n=8, col=GREY)
    m.cyl(0, 0, 7.7, 8.15, 0.13, 0.15, n=8, col=LIT, cap=False)             # lantern glass
    m.cyl(0, 0, 8.15, 8.3, 0.19, 0.06, n=8, col=GREY)                      # hood
    m.cyl(0, 0, 8.3, 8.45, 0.025, 0.0, n=4, col=GREY, cap=False)           # finial
    for z in (3.0, 5.6):                                                   # banner brackets (towards the road)
        m.tube((0, -0.05, z), (0, -0.75, z), 0.02, GREY, n=4)


def along(line, y, off):
    """Point on the polyline at northing y (or nearest), offset `off` m to the east of the travel direction (N)."""
    from shapely.geometry import LineString, Point
    ln = LineString(line)
    xs = [p[0] for p in line]
    p = ln.interpolate(ln.project(Point(np.mean(xs), y)))
    best = None
    for a, b in zip(line[:-1], line[1:]):     # segment containing y
        lo, hi = sorted((a[1], b[1]))
        if lo <= y <= hi and hi > lo:
            t = (y - a[1]) / (b[1] - a[1])
            best = (a[0] + t * (b[0] - a[0]), y, b[0] - a[0], b[1] - a[1])
    if best is None:
        return p.x + off, p.y
    x, y, dx, dy = best
    if dy < 0:
        dx, dy = -dx, -dy
    L = math.hypot(dx, dy)
    return x + off * dy / L, y - off * dx / L      # right-hand normal of a northward direction = east


def snap(line, x, y, off):
    """Snap (x, y) to the kerb `off` m from the centreline on its own side."""
    from shapely.geometry import LineString, Point
    ln = LineString(line)
    d = ln.project(Point(x, y))
    a, b = ln.interpolate(max(d - 1, 0)), ln.interpolate(min(d + 1, ln.length))
    c = ln.interpolate(d)
    tx, ty = b.x - a.x, b.y - a.y
    L = math.hypot(tx, ty)
    nx, ny = -ty / L, tx / L
    s = 1 if (x - c.x) * nx + (y - c.y) * ny >= 0 else -1
    return c.x + s * off * nx, c.y + s * off * ny


def items():
    out = []
    for y in KP_LAMPS_Y:
        out.append(("lamp_kp", *along(KP, y, 3.0), {}))
    for x, y in BENET_LAMPS:
        out.append(("lamp_kp", *snap(BENET, x, y, 3.0), {}))
    for x, y, h in MH_LAMPS:
        if all(math.hypot(x - a, y - b) > 12 for a, b, _ in PHOTO_LAMPS):
            out.append(("lamp_twin", x, y, {"heads": h}))
    for lo, hi, st in (SHH_BOLLARD_Y, KP_WEST_BOLLARD_Y):
        for y in np.arange(lo, hi + 1e-6, st):
            out.append(("bollard", *along(KP, float(y), -4.0), {}))
    for x, y in EXTRA_BOLLARDS:
        out.append(("bollard", x, y, {}))
    return out


def build(verbose=False):
    import street_objects as S
    osm = [(E - E0, N - N0) for E, N, k, _ in S.objects_in_area() if k in (1, 3)]
    g = Ground()
    res, counts, tris, skipped = [], {}, {}, 0
    for kind, x, y, t in items():
        if any(math.hypot(x - a, y - b) < 1.5 for a, b in osm):
            skipped += 1
            continue
        m = Mesh()
        m.frame(x, y, g(x, y), math.pi / 2)    # local -v faces west (King's Parade runs ~north)
        if kind == "lamp_kp":
            kp_lamp(m)
        elif kind == "lamp_twin":
            twin_lamp(m, t["heads"])
        else:
            bollard(m, False)
        parts = m.out(f"streetlights:{kind}@{x:.1f},{y:.1f}")
        res += parts
        counts[kind] = counts.get(kind, 0) + 1
        tris[kind] = tris.get(kind, 0) + sum(len(p["tris"]) for p in parts)
    if verbose:
        print(json.dumps({"objects": counts, "tris": tris, "total": sum(tris.values()),
                          "skipped_near_osm": skipped}, indent=1))
    return res


if __name__ == "__main__":
    build(verbose=True)
