# Journal

## 2026-11-07 — Session 1: data, targets, KPI harness

Done
- `area.geojson`: fixed study area (52.1975–52.2125 N, 0.1080–0.1330 E).
- OSM extract via Overpass (bbox + ~200 m margin, recursive, 67 MB, git-ignored):
  `[out:json];(nwr(52.1945,0.1030,52.2155,0.1380););(._;>;);out meta;`
- EA LiDAR 1 m DTM/DSM (2022 composite + NLP 2023) and OS OpenMap Local / Open Roads / Terrain 50 downloaded by a subagent; clipped mosaics in `data/lidar/`. No sub-metre LiDAR exists here. Details in DATA.md and data/SOURCES_lidar_os.md.
- `scripts/osm_targets.py` → `data/derived/osm_targets.json` (committed; frozen denominators):
  118.38 km of walkable ways (2,965 ways, 23,984 samples at 5 m), 2,091 buildings with centre in the area
  (2,044 ways, 22 relations, 25 nodes).
- `FORMAT.md`: build contract: `site/manifest.json`, per-tile GLB (each building is a node `b:<osm_id>`) and `.col`
  collision files (triangles + kind + surface class), in a BNG-offset frame.
- `scripts/kpi.py` + `measure.sh`: rasterise the collision files to a 0.5 m walk grid, block cells where solids cross
  the body column, connect 4-neighbours with steps ≤ 0.45 m, flood from spawn, then score the OSM samples (1 m snap).
  Also scores ground cells, buildings (GLB JSON chunk only, HTTP Range when remote), heights vs LiDAR P95 (cached), and landmarks.
- Self-test `scripts/make_test_build.py` (flat ground, water strip, Lion Yard box): gives the expected results
  (53 % walkable, 100 % ground, 1 building), and it caught a spawn placed inside a building. It runs in about 5 s.
- `landmarks/landmarks.json`: fixed list of 25 landmarks with OSM IDs.
- Private repo: github.com/haveyouseenmyquant-ctrl/walkable-cambridge.

KPIs now: all 0 (no build yet). height_accuracy_pct, load_seconds and site_errors are left out until there is a build or site.

Learned
- EA survey search API wants WGS84 GeoJSON; downloads are plain GETs per 5 km tile. Only 1 m here.
- The 2022 composite DSM gives King's Chapel P95 nDSM 28.4 m, which looks right. NLP 2023 reads that roof about 4 m higher and has holes, so use the composite.
- 2,091 buildings is fewer than expected because college ranges are mapped as large single polygons.

Next (session 2)
- Pipeline: DTM ground mesh (tiles of about 250 m) with OSM surface classes, so ground coverage counts; extrude every
  building footprint to its LiDAR P95 (median DTM base) with solid walls; give node buildings a default box.
  Export GLB (meshopt) + `.col` + manifest into `site/`. Pick a spawn on Market Square.
- Watch for: OSM footways that run through building polygons (passages, arches). The harness will count them as
  blocked, so the pipeline needs openings for tunnel=building_passage / covered=yes ways.
- Then session 3: the three.js viewer and a headless Chrome test for load_seconds/site_errors.
