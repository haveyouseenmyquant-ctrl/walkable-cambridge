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
- Disk: only ~6.9 GB free after downloads (data/raw is 2.2 GB). Don't unzip OS Open Roads (2.16 GB); read the needed
  layer straight from the zip, or clip it once and delete the raw file. The "2022" LiDAR composite was actually flown in 2018–2019.

## 2026-11-07 — Session 2: first complete world, viewer, live site

Done
- `scripts/build.py` (~6 s): 64 tiles of 250 m covering the LiDAR mosaic (world x/y in [-1000, 1000)).
  - Ground: the DTM on a 2 m grid. Each triangle takes its class from a 1 m OSM class raster: roads buffered by
    type, footways, steps, grass/parks, squares, water (kind 2, not walkable), under-building. Unmapped land
    defaults to "paved/courtyard" (5). That default is a judgement call, and it is why ground_coverage reads 100 %.
  - Buildings: all 3,273 OSM buildings in the extent (3,189 meshed). Each is extruded from its lowest DTM to
    median DTM + the LiDAR nDSM P95 (min 2.5 m, otherwise OSM height/levels), with a flat roof and solid walls.
    Node buildings are 8 m boxes. Walkable ways that cross a building's interior get a 2.6 m wide passage cut up to
    median ground + 3.5 m, with the upper storeys kept above it (241 buildings).
  - Bridges: walkable ways with bridge=* get a deck interpolated between the DTM at the two ends (402 ways).
- Viewer (subagent): `site/index.html` + `site/app/*`, three.js r187 vendored. It streams tiles within 400 m and
  uses the .col files for physics. Also WASD/mouse, touch joystick, minimap, landmark jump list and credits.
  `scripts/browser_test.mjs` uses puppeteer-core with the installed Chrome.
- Published: the repo is now public (approved). Pages deploys from Actions: `scripts/publish.sh` uploads
  `world.tar.gz` as a release asset and dispatches `pages.yml` on main, so the generated binaries stay out of git.
  The site is live at https://haveyouseenmyquant-ctrl.github.io/walkable-cambridge/ and `SITE_URL` is set.
- `service.sh` runs the 60 s browser test hourly, because measure.sh must finish within a minute.
  measure.sh merges that result if it is under 3 h old. kpi.py now downloads remote files in parallel
  (73 s → 17 s).

KPIs (published site): walkable 99.2, buildings 100, ground 100, height 99.71, landmarks 0, load 1.87–2.47 s, errors 0.

Learned
- The github-pages environment only deploys from main, so a release event on a tag is rejected. Use workflow_dispatch.
- Height accuracy is high by construction, since the model uses the same LiDAR P95 as the check. Real roof shapes
  are the next step for realism, not for this KPI.
- The remaining walkable misses (193 samples) are indoor arcades (Grand Arcade, St Andrew's), tunnel/cloister
  ways (layer -1), and upper-level walkways (level 1/2, layer 1). `kpi.py --verbose` writes them to
  data/derived/walk_misses.json.

Next
- Visual pass: pitched roofs from LiDAR (roof shape by fitting the DSM), facade textures (CC0), trees, river surface.
- Landmarks: detailed models plus reference screenshots in landmarks/ (start with King's Chapel, Senate House, Great St Mary's).
- Indoor/arcade/tunnel ways: add covered walkable volumes so they count.
- Compress tiles with meshopt (gltfpack, keep node names, -noq so accessor max stays in metres). The 40 MB world
  is fine for now. Merge per-building draw calls in the viewer if fps is low on laptops.
- Test in Safari for real (only Chrome has been tested).

## 2026-11-07 — Session 3: landmark detail (0 → 25)

Done
- `scripts/detail.py`: procedural landmark models from primitives (prisms, cones, domes, beams, wall panels), with a style
  recipe per landmark in `SPECS`: gothic (LiDAR-detected tower/spire blob, corner turrets, buttresses with pinnacles,
  pointed windows, crenellations, gable/lead roofs), classical (pilasters, storeyed windows, cornice, balustrade,
  pediment, portico columns, dome, cupola/lantern, arcade, curved gables), brick hall, round church (cylinder + cone),
  Trinity gate tower (4 octagonal turrets at the gate node), Gate of Honour (piers, arch, hex cupola, sundials, obelisks),
  bridges (arches + spandrels, parapets, stone balls on Clare, covered tracery gallery on the Bridge of Sighs, timber
  radial/tangent truss on the Mathematical Bridge).
- build.py: the render mesh of a landmark building is the detailed model. Collision still uses the plain footprint body,
  so walkable coverage is unchanged by design. Bridges are `lm:<id>` nodes. Manifest landmarks list features + view params.
- Viewer: `window.__cam` override hook. `scripts/landmark_shots.mjs` writes the 25 reference images to `landmarks/`.
- Published (release world-20261107-2042, Pages deploy ok).

KPIs (published site): walkable 99.2, buildings 100, ground 100, landmarks 25, height 98.98 (was 99.71), load/errors
from the hourly service run (last 2.47 s / 0; a local check gave 1.96 s / 0).

Learned
- Height accuracy fell 0.73 pt because spires, pinnacles and turrets now rise above the footprint's LiDAR P95. That is
  the KPI working as defined (highest point vs P95), not a bug. Don't hide detail in separate nodes to dodge it.
- Detail added ~23 MB (tiles 63 → 86 MB, largest 2.3 MB). Load time is unaffected so far. Meshopt compression is still to do.
- Recipes are generic and driven by the footprint's rotated rectangle and nDSM. Weak spots: the Fitzwilliam portico is
  small and its facade choice is rough, the Trinity Great Gate shot frames the whole range (tower small), the Mathematical
  Bridge truss arches over a flat deck, and front bearings are hand-set guesses that should be checked against photos.

Gaspard's request (21:42): full movement + broom for next session
- On foot: smooth walk/run (Shift), jump (Space) with coyote time + jump buffer, crouch (C/Ctrl) + slide when running,
  dash (Q or double-tap) with cooldown, ledge climb ≤1.5 m, V toggles 1st/3rd person (needs a player model).
- Broom (original design, code-built/CC0, no franchise references): B mount/dismount; W/S forward/back, mouse steer
  and pitch, Space up, C/Ctrl down, Shift boost, hover when idle; collides with buildings, can land on roofs;
  dismount mid-air = fall; clamp to study area and ≤150 m.
- Phones: buttons for jump/run/dash/broom. Gamepad if easy. Help screen on H or ?.
- Headless test exercises every move (site_errors catches breakage). Keep load_seconds, and walkable KPI = walking only.
- When live: tell Gaspard the key map.

Next
- Session 4: the movement/broom request above (top priority, per Gaspard).
- Then: indoor/tunnel walkways (the last 0.8 % walkable), meshopt compression, pitched roofs from LiDAR for all buildings,
  textures, trees, river. Refine landmark recipes against Commons photos.
