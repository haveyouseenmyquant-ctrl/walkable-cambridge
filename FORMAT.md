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
