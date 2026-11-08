# Build format (contract between pipeline, viewer and KPI harness)

The browser build is a static site rooted at `site/` (local) or the GitHub Pages URL (published,
set in `SITE_URL`). The KPI harness (`scripts/kpi.py`) reads exactly the files the viewer loads.

## Coordinates
- World frame: British National Grid (EPSG:27700) metres minus `manifest.origin` (`e0`, `n0`); heights are metres above Ordnance Datum Newlyn (ODN), same as the EA LiDAR.
- Collision files: `x = E - e0` (east), `y = N - n0` (north), `z` = height (up).
- glTF tiles: standard glTF Y-up: glTF `(x, y, z) = (E - e0, height, -(N - n0))`.

## `manifest.json`
```json
{
  "version": 1,
  "origin": {"crs": "EPSG:27700", "e0": 545000, "n0": 258400},
  "spawn": {"x": 0, "y": 0, "z": 10.0},
  "tiles": [
    {"id": "t_0_0", "bounds": [xmin, ymin, xmax, ymax],
     "glb": "tiles/t_0_0.glb", "collision": "collision/t_0_0.col"}
  ],
  "buildings": [
    {"osm_id": "way/123", "tile": "t_0_0", "node": "b:way/123", "detailed": false}
  ],
  "landmarks": [
    {"id": "kings-college-chapel", "osm_id": "way/...", "detailed": true, "screenshot": "landmarks/kings-college-chapel.png"}
  ]
}
```
- `bounds` are in world-frame x/y (collision axes).
- Every building is its own glTF node named `b:<osm_id>` with a mesh in its tile's GLB. The node may carry a translation (no rotation/scale); the harness reads the mesh's POSITION accessor `max` (mandatory in glTF, also with Draco/meshopt) to get its highest point.

## Collision file (`.col`, little-endian)
```
char[4]  magic "WCOL"
uint32   version (1)
uint32   nverts
uint32   ntris
float32  verts[nverts*3]   (x, y, z world frame, z up)
uint32   tris[ntris*3]
uint8    kind[ntris]       0 = solid (walls, building shells; blocks the player)
                           1 = walkable ground (player can stand on it)
                           2 = non-walkable surface (water etc; counts as ground surface, not walkable)
uint8    surface[ntris]    0 = none/building, 1 = road, 2 = pavement/footway, 3 = grass/green,
                           4 = water, 5 = courtyard/paved area, 6 = earth/track, 7 = steps,
                           8 = bridge deck, 9 = ground under a building,
                           255 = placeholder (does NOT count for ground coverage)
```

## Walkability rules used by the harness
- Ground grid 0.5 m. Each cell takes the highest walkable (kind 1, normal tilt <= 50°) surface under it.
- A cell is blocked if any solid triangle passes through the body column [ground + 0.35 m, ground + 1.8 m] (solid triangles are clipped to that height band using the ground at their vertices, then every cell their XY projection touches is blocked).
- Neighbouring cells (4-connected, so diagonal wall gaps never leak) connect if both are free and their heights differ by <= 0.45 m (a step).
- Reachable = connected to the cell under the spawn point.
- A 5 m OSM sample point counts if a reachable cell lies within 1.0 m of it (tolerance for OSM centreline vs modelled surface).
- Ground coverage: a 5 m cell (centre inside the study area) counts if the 0.5 m cell at its centre is covered by a kind 1 or 2 triangle whose surface is not 0 or 255.
- Building height: modelled top = max POSITION y of the building's mesh (+ node translation y); modelled height = top − median DTM inside the OSM footprint; compared with the 95th percentile of DSM − DTM inside the footprint; within 2 m counts.

## Landmark detail (session 3)
- `manifest.landmarks[]`: `{id, name, osm_id, detailed, style, features[], screenshot, tile, node, x, y, look_z, size, view}`.
  Building landmarks keep their `b:<osm_id>` node (render mesh = detailed model); non-building landmarks
  (bridges) are nodes `lm:<id>`. Collision always uses the plain footprint body, so detail never blocks walkable ways.
- Reference screenshots: `landmarks/<id>.png`, from `node scripts/landmark_shots.mjs` (viewer `?debug` + `window.__cam`).

## Trees and street objects (sessions 9, 11)
- Pipeline order: `build.py` → `trees.py` → `street_objects.py` → `cars.py` (all edit manifest.json in place).
- Parked cars (session 25, `scripts/cars.py`): type 13 records appended to the object bins, on OSM parking lanes
  (`parking:<side>=lane|street_side|half_on_kerb`, older `parking:lane:*`) and `amenity=parking` strips
  (`parking=lane|street_side|layby`); heading = the car's long axis. Not OSM node targets, so not in street_objects_pct.
- `trees/<tile>.bin`: float32 `[x, y, z_ground, height, crown_r, seed]`; `objects/<tile>.bin`: float32
  `[x, y, z_ground, type, heading, seed, n]` (types in `scripts/street_objects.py` TYPES; heading = radians of the
  nearest way's direction, the way lies on local +y; n = bike stands for bicycle_parking).
- `manifest.layers` = viewer defaults `{trees, objects}`; `?trees=0|1`, `?objects=0|1` override.
- street_objects_pct: targets = OSM nodes of the TYPES in the study area plus `natural=tree` nodes
  (data/derived/street_object_targets.json). One counts if a record of the same type (tree layer for trees) lies within
  1 m of it in a layer the build draws by default.

## Road markings (session 20)
- `scripts/markings.py`, run after `facades.py`: `markings/<tile>.bin` float32 `[x0, y0, x1, y1, kind]` segments
  (kind 0 = white centre dash, 1 = yellow kerb line), rules from OSM highway/oneway/lanes/parking tags (see the
  script). The viewer drapes them on the tile's collision ground (`site/app/markings.js`); `?markings=0` hides them.

## Roof match (session 14)
- roof_match_pct (`scripts/roof_match.py`): per OSM target building, the render mesh (`b:<osm_id>`) is rasterised
  top-down on the 1 m LiDAR grid (highest surface over each cell centre; no surface = DTM) and compared with the EA
  DSM on the cells whose centres lie inside the footprint shrunk by 0.5 m (unshrunk if that leaves none). Counts if
  RMSE ≤ 0.75 m. Cached per build hash as `data/benchmark/scores/<hash>_roof.json` (publish.sh, bench.sh); measure.sh
  reads the cache for the live build.
- build.py roofs (session 14): every footprint with ≥ 6 LiDAR pixels gets the DSM roof (eave pixels replaced by the
  nearest inner pixel, 3×3 median), meshed as a quadtree from 8 m down to 1 m cells, split where the roof deviates
  > 0.25 m (RMS) from the cell's two-triangle fit.
- Session 16: the roof is the raw DSM on every footprint pixel (no eave replacement, no 3×3 median: the eroded-pixel
  spread lifted pitched eaves to inner, higher pixels), the quadtree grid sits on the LiDAR pixel centres (1 m cells
  carry the DSM values instead of corner averages), and the roof floor is median ground + 1 m (was + 2 m), so low
  parts of a footprint stay low. roof_match_pct 23.18 → 92.11 (median RMSE 1.05 → 0.21 m). The legacy
  height_accuracy_pct (model top vs LiDAR p95) drops 91 → 79 because chimneys and spikes are no longer filtered.
