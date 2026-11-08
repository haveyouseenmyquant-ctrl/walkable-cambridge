"""Ring encounters, centre outwards (session 41; whole study area + place themes, session 45): greedy cover of the OSM
walkable samples within --radius m of the Market Square centre by encounter zones placed on walkable samples (never
inside or within 1.5 m of a building footprint), so every sample lies within 60 m of one. Each zone's mob pair is themed
by its setting from the raw OSM: riverside (Cam, canals, ponds) -> wraiths/revenants/hags, commons/greens/gardens ->
wisps/hags/moss golems, churches/colleges -> gargoyles/statues/bell bats/griffins, other streets -> town mobs.
Mobs spawn lazily in-game (mobs.js updateEncounters: SPAWN_R 120 m, DESPAWN_R 200 m, MAX_LIVE 24), so the zone count
does not raise the live mob count.
Hand-placed encounters in site/app/game/encounters.json are kept; generated ones ("gen": true) are replaced.
  .venv/bin/python -I scripts/gen_encounters.py [--radius 3000] [--spacing 60] [--dry]"""
import argparse, json, math, os
import numpy as np
from pyproj import Transformer
from shapely import STRtree, points as sh_points
from shapely.geometry import LineString, Polygon, shape

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ap = argparse.ArgumentParser()
ap.add_argument("--radius", type=float, default=3000)   # default: the whole study area
ap.add_argument("--spacing", type=float, default=60)
ap.add_argument("--dry", action="store_true")
a = ap.parse_args()

F = os.path.join(ROOT, "site/app/game/encounters.json")
enc = [e for e in json.load(open(F)) if not e.get("gen")]
o = json.load(open(os.path.join(ROOT, "site/manifest.json")))["origin"]
T = json.load(open(os.path.join(ROOT, "data/derived/osm_targets.json")))
s = np.array([p[:2] for p in T["walk"]["samples"]], float)
s -= [o["e0"], o["n0"]]
C = np.array([-103.0, 57.0])          # Market Square centre in the world frame
s = s[np.hypot(*(s - C).T) <= a.radius]
cov = np.zeros(len(s), bool)
for e in enc:
    cov |= np.hypot(s[:, 0] - e["x"], s[:, 1] - e["y"]) <= 60 + e.get("r", 0)

# --- candidate spawn centres: walkable samples outside buildings (1.5 m margin)
def wpoly(geo):
    g = shape(geo)
    from shapely.affinity import translate
    return translate(g, -o["e0"], -o["n0"])
bld = [wpoly(b["footprint"]).buffer(1.5) for b in T["buildings"] if b.get("footprint")]
tree = STRtree(bld)
pts = sh_points(s)
inside = np.zeros(len(s), bool)
qi, _ = tree.query(pts, predicate="intersects")
inside[np.unique(qi)] = True
ok = ~inside

# --- place themes from the raw OSM (world frame)
tr = Transformer.from_crs("EPSG:4326", "EPSG:27700", always_xy=True)
el = json.load(open(os.path.join(ROOT, "data/raw/osm/cambridge_overpass.json")))["elements"]
nodes = {}
for e in el:
    if e["type"] == "node":
        nodes[e["id"]] = (e["lon"], e["lat"])
nid = list(nodes)
ll = np.array([nodes[i] for i in nid]) if nid else np.zeros((0, 2))
E, N = tr.transform(ll[:, 0], ll[:, 1])
xy = dict(zip(nid, zip(E - o["e0"], N - o["n0"])))
box = (s[:, 0].min() - 200, s[:, 1].min() - 200, s[:, 0].max() + 200, s[:, 1].max() + 200)
def geom(w, area):
    c = [xy[n] for n in w["nodes"] if n in xy]
    if len(c) < 2: return None
    c = np.array(c)
    if c[:, 0].max() < box[0] or c[:, 0].min() > box[2] or c[:, 1].max() < box[1] or c[:, 1].min() > box[3]: return None
    if area and len(c) >= 4 and w["nodes"][0] == w["nodes"][-1]:
        p = Polygon(c)
        return p if p.is_valid else p.buffer(0)
    return LineString(c)
GREEN_TAGS = {("leisure", v) for v in ("park", "common", "garden", "recreation_ground", "nature_reserve", "pitch")} | \
             {("landuse", v) for v in ("grass", "meadow", "village_green", "recreation_ground", "allotments")} | \
             {("natural", v) for v in ("wood", "scrub", "grassland")}
river, water_small, green, stone, names = [], [], [], [], []
for w in el:
    if w["type"] != "way": continue
    t = w.get("tags", {})
    if t.get("waterway") in ("river", "canal") or t.get("natural") == "water" or t.get("water") in ("river", "pond", "lake"):
        g = geom(w, t.get("natural") == "water")
        if g is not None: river.append(g)
    elif t.get("waterway") in ("stream",):
        g = geom(w, False)
        if g is not None: water_small.append(g)
    if any((k, t.get(k)) in GREEN_TAGS for k in ("leisure", "landuse", "natural")):
        g = geom(w, True)
        if isinstance(g, Polygon) and g.area >= 1500: green.append(g)
    if t.get("amenity") in ("place_of_worship", "university", "college") or t.get("landuse") == "college_court" or \
            t.get("building") in ("church", "chapel", "cathedral", "college", "university"):
        g = geom(w, True)
        if g is not None: stone.append(g)
    if t.get("highway") and t.get("name"):
        g = geom(w, False)
        if g is not None: names.append((g, t["name"]))

def near(geoms, p, d):
    if not geoms: return False
    tr_ = near.cache.setdefault(id(geoms), STRtree(geoms))
    return len(tr_.query(p, predicate="dwithin", distance=d)) > 0
near.cache = {}
name_tree = STRtree([g for g, _ in names]) if names else None
def place_name(p):
    if name_tree is None: return None
    i = name_tree.nearest(p)
    return names[int(i)][1] if names[int(i)][0].distance(p) <= 40 else None

def theme(x, y):
    from shapely.geometry import Point
    p = Point(x, y)
    if near(river, p, 45) or near(water_small, p, 15): return "river", p
    if near(green, p, 8): return "green", p
    if near(stone, p, 25): return "stone", p
    return "town", p

POOLS = {
    "river": [["river_wraith", "wisp"], ["punt_revenant", "bog_hag"], ["river_wraith", "punt_revenant"], ["bog_hag", "wisp"]],
    "green": [["wisp", "bog_hag"], ["bicycle_golem", "wisp"], ["wisp", "crest_griffin"], ["bog_hag", "bicycle_golem"]],
    "stone": [["gargoyle", "statue"], ["bell_bats", "gargoyle"], ["statue", "crest_griffin"], ["gargoyle", "bell_bats"],
              ["crest_griffin", "ink_imp"]],
    "town": [["automaton", "soot_sprite"], ["ink_imp", "bicycle_golem"], ["soot_sprite", "ink_imp"], ["automaton", "bell_bats"],
             ["bicycle_golem", "soot_sprite"], ["ink_imp", "automaton"]],
}
LABEL = {"river": "riverside", "green": "green", "stone": "cloisters", "town": "streets"}
R = 5
out, k, cnt = [], 0, {t: 0 for t in POOLS}
skip = 0
while not cov.all():
    # next uncovered sample nearest the centre: grows rings outwards
    i = np.flatnonzero(~cov)
    j = i[np.argmin(np.hypot(*(s[i] - C).T))]
    # move the zone up to spacing/2 along the street so it covers more new samples; only outside buildings
    d = np.hypot(*(s - s[j]).T)
    cand = np.flatnonzero((d <= a.spacing / 2) & ok)
    if not len(cand):   # sample deep inside a courtyard/passage: widen the search to the 60 m reach
        cand = np.flatnonzero((d <= 60) & ok)
    if not len(cand):
        cov[j] = True; skip += 1; continue
    best, bestn = cand[0], -1
    for c in cand[:: max(1, len(cand) // 30)]:
        n = int(((np.hypot(*(s - s[c]).T) <= 60 + R) & ~cov).sum())
        if n > bestn: best, bestn = c, n
    if bestn <= 0:
        cov[j] = True; skip += 1; continue
    x, y = s[best]
    cov |= np.hypot(*(s - s[best]).T) <= 60 + R
    dist = math.hypot(x - C[0], y - C[1])
    th, p = theme(x, y)
    pool = POOLS[th]
    ring = 1 + int(dist // 150)
    nm = place_name(p)
    out.append({"id": "gen-%03d" % k, "name": "Ring %d %s%s" % (ring, LABEL[th], " - " + nm if nm else ""),
                "x": round(float(x), 1), "y": round(float(y), 1), "r": R, "mobs": pool[cnt[th] % len(pool)],
                "theme": th, "gen": True})
    cnt[th] += 1
    k += 1
if not a.dry:
    with open(F, "w") as f:
        json.dump(enc + out, f, indent=0)
print(json.dumps({"hand": len(enc), "generated": len(out), "radius": a.radius, "themes": cnt, "unreachable_samples": skip}))
