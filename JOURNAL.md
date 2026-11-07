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

## 2026-11-07 — Session 4: movement and broom (Gaspard's request)

Done
- `site/app/player.js` rewritten. On foot: acceleration-based walk/run, jump (4.6 m/s, 0.12 s coyote time,
  0.15 s buffer), crouch (lower eye and body), slide (crouch while running, 0.9 s), dash (Q or double-tap,
  15 m/s for 0.18 s, 1 s cooldown), ledge climb ≤1.5 m (animated), head bump, wading out of water, and V for
  1st/3rd person with a camera that pulls in at walls. Broom (B): flies along the view direction, Space/C up/down,
  Shift boost (28 m/s), hovers when idle, walls block it, terrain and roofs push it up, clamped to the study-area
  quad and 150 m above the floor. Dismounting means falling with your momentum.
- Roofs: the viewer treats upward-facing solid triangles as standable (`support(..., roofs)`) for player movement
  only. The .col files and kpi.py are unchanged, so walkable_coverage still measures ground walking.
- `site/app/avatar.js`: a primitive-built figure (coat, scarf) and broom with walk swing, crouch, jump and seated
  poses. Touch buttons (Jump/Run toggle/Dash/Crouch/Broom/View), standard gamepad mapping, Help overlay (H/?),
  mode badge.
- `browser_test.mjs`: a moves phase before the 60 s walk checks 15 moves (jump, run, slide, crouch, dash, double-tap,
  3rd person, broom mount/up/fly/hover/down/dismount, fall and land, ledge climb). Results go to stderr as
  `{"moves":…}`, so measure.sh's KPI JSON is unchanged. `--moves-shots DIR` saves screenshots. All 15 pass,
  locally and on the live site.
- Published (release world-20261107-2055). Sent Gaspard the key map.

KPIs: walkable 99.2, buildings 100, ground 100, landmarks 25, height 98.98, load 1.99 s, errors 0 (live).

Learned
- The ground world has no 0.6–1.5 m ledges (buildings are ≥2.5 m and the DTM is smooth), so ledge climb only
  matters on stepped roofs. The test's `findLedge` searches from the topmost surface, which includes roofs.
- Landmark collision is still the plain footprint body, so on a landmark roof you stand on the footprint top,
  not on the detailed roof.

Next
- Real Safari check (desktop + iOS) of pointer lock, touch buttons and gamepad.
- Indoor/tunnel walkways (the last 0.8 % walkable), meshopt compression, pitched roofs from LiDAR, textures,
  trees, river surface. Refine landmark recipes against Commons photos.

## 2026-11-07 — Session 5: sealed pockets (walkable 99.2 → 99.96)

Done
- Diagnosed the 193 missed samples (`kpi.py --verbose` now also records whether free ground was near each miss and
  saves the walk grid to `data/derived/walk_grid.npz`, git-ignored). 142 were on free ground that couldn't be
  reached: courts sealed by buildings (Cobble Court, cloisters, tunnel=yes areas), a mill-race island and a culvert
  under the Fen Causeway. 51 were blocked: passage ceilings clipped the walker where the DTM rises inside a building
  (Grand Arcade, St Andrew's Arcade).
- `scripts/connectors.py`: for each unreachable pocket it adds a straight connector (median 5.5 m, max 19.5 m) from the
  missed sample nearest to reachable ground to that ground, extended 1.5 m at both ends. build.py cuts a ground-floor
  passage (2.6 m wide) through every building the connector buffer touches and paves it over water. 94 connectors
  in `data/derived/connectors.json` (committed, so the build is reproducible). They stand in for doors, gates and
  culverts that OSM doesn't map.
- build.py: the passage ceiling is now max(median ground + 3.5, highest DTM in the cut's bbox + 2.6).
- Published (release world-20261107-2111). Local browser test: 15/15 moves, 0 errors, 2.43 s.

KPIs (live): walkable 99.96, buildings 100, ground 100, landmarks 25, height 98.98, load 1.99, errors 0.

Learned
- Run connectors.py → build.py → kpi.py --verbose about 3–4 times. Each pass opens pockets that expose the next
  ones, and it converged at 94 connectors. If you rerun from scratch, start from a build *without* connectors,
  because connectors.py dedupes by start point.
- The 11 samples left are single samples on steps and tunnel ends, mostly on the 2 m step-height edges of
  sunken courts.

Next
- Walkable is effectively done. Following Gaspard's priorities: roof shapes from LiDAR (pitched roofs), then textures, trees,
  river surface, meshopt compression. Check the connector passages visually (they're simple notches).
- Real Safari check.

## 2026-11-07 — Session 6: LiDAR roof shapes; change of direction

Done
- build.py: buildings whose DSM roof isn't flat (q90−q10 ≥ 1.5 m on the footprint eroded by 1 px) get a roof
  heightfield in place of the flat top: the DSM inside the footprint, spread outward (nearest fill), 3×3 median
  (chimneys), sampled on a 3 m grid clipped to the footprint and rescaled so the peak lands on the LiDAR top
  (dmed+P95). Walls come from the roof's boundary edges, so the shell stays closed. Passage buildings get the
  shaped roof on their upper body. Landmarks keep their recipes. 2,691 of 3,189 buildings now have shaped roofs, in
  a tiled-red tone. Screenshot: docs/roofs_session6.png.
- Size: tiles 86→147 MB, collision 46→95 MB (largest tile ~4 MB). A 2 m grid doubled the size and slowed the headless
  test enough to fail jump/run, so I used 3 m. The browser test now waits for the player to settle and tracks a jump
  for 1.4 s.
- KPIs (local): walkable 99.96, buildings 100, ground 100, landmarks 25, height 98.64 (was 98.98; grid vertices
  miss some ridge peaks), load 1.5–2.1 s, errors 0, 15/15 moves.

Learned
- Raw DSM heightfields look lumpy (see the screenshot). Real planes need plane fitting per roof facet (RANSAC on
  the 1 m or 50 cm DSM) or straight-skeleton gables/hips fitted to the DSM. That costs fewer triangles and looks much
  crisper, so it's the next step for roofs.
- Headless swiftshader fps is sensitive to triangle count. With the new fps_median KPI, budget triangles per tile
  and use LOD (far tiles: flat roofs).

Change of direction (Gaspard, 22:19–22:25), taking effect from session 7
- New main KPI photo_match_score: a held-out benchmark of 200 real street-level photos (free, licensed: Mapillary
  CC-BY-SA / Wikimedia Commons), with coverage KPIs kept as guardrails. Step 1: build the benchmark and record an
  honest baseline.
- Remove the 94 invented connector passages (data/derived/connectors.json). Only real, mapped entrances count.
  Walkable will drop to about 99.2 %. Accept that and re-derive from OSM entrances/gates where possible.
- Work from the centre outwards: Great St Mary's (52.2052 N, 0.1183 E) → Market Square, King's Parade, Senate House.
  Finish each ring before moving outward. New KPI finished_radius_m.
- Long-term bar: AAA fidelity (Elden Ring cited for fidelity, not style). Route: WebGPU, PBR, TAA, cascaded
  shadows, AO, baked GI, scanned (CC0) materials, geometric detail, vegetation, quality presets. KPIs visual_quality
  (rubric judge, 30 fixed views) and fps_median (≥50 on the Mac mini). Do this after the baseline.
- Long local jobs (photo matching, baking) can run in service.sh between sessions.

Next (session 7)
1. Read the updated goal and KPI definitions. Build the 200-photo benchmark (licences recorded, camera pose per
   photo, held out) and a photo_match scorer that renders the same view from the build. Record the baseline.
   Add photo_match_score, finished_radius_m, visual_quality and fps_median to measure.sh as defined.
2. Remove the connectors and rebuild. Report the honest walkable number.
3. Centre ring: crisp fitted roofs, facade textures, ground materials, and street furniture around Great St Mary's.
- Published as world-20261107-2133. The first Pages deploy timed out syncing about 240 MB, so pages.yml now has
  `timeout: 1800000`. Live: walkable 99.96, buildings 100, ground 100, landmarks 25, height 98.64, load 2.8–3.1 s
  (was 1.99; bigger tiles), errors 0, all 15 moves pass. Load time and fps are the cost of shaped roofs. Plane-fitted
  roofs should win it back.

## 2026-11-07 — Session 7: benchmark tooling, invented passages removed, sun shadows

Done
- Benchmark pipeline, ready to run except for the photos. `scripts/make_benchmark.py` lists Mapillary images in
  the study area, keeps perspective photos with a computed pose within 4 m of an OSM walkable sample, and picks 200
  by farthest-point sampling seeded at Great St Mary's (at most one per sequence per 50 m). It takes pose from
  `computed_rotation` (heading, pitch), corrects true north to grid north (−1.67°), takes hfov from the focal
  length, downloads the 1024 px thumbnails, and writes `data/benchmark/benchmark.json` and `heldout.json` (ids plus
  same-sequence images within 15 m, which world builders must exclude). It refuses to run again once frozen.
  `scripts/photo_render.mjs` renders the viewer at each pose (ground + 1.65 m, matching vertical fov, UI hidden).
  `scripts/photo_score.py` gives the DINOv2 ViT-S/14 (facebook/dinov2-small, Apache-2.0, local MPS) CLS cosine ×100.
  `scripts/bench.sh` caches `data/benchmark/scores/<build_hash>.json` (build hash = sha256 of manifest.json).
  measure.sh reports the cached value for the live build, and service.sh scores any new build hourly. I tested
  it end to end on 3 dev poses (identical images give 100, different views 56).
- **Blocked: no Mapillary token.** The Graph API needs a client token, and the signup needs email verification
  I can't do. I asked Gaspard (tell-owner) and filed approval request a-20261107-224817-2d90. When the token
  arrives, put it in `data/mapillary_token` (git-ignored) and run make_benchmark.py once, then bench.sh. No
  baseline yet.
- Removed the 94 invented connector passages (moved to `data/derived/connectors_invented_retired.json`, no
  longer built). Honest walkable_coverage: 99.39 % (local), still above the 99 guardrail.
- fps_median: browser_test.mjs with `WC_GPU=1` renders on the M4 (ANGLE Metal) in a 1920×1080 window and
  reports the median frames per second over the walk. Headless Chrome throttles requestAnimationFrame to about 13–17 fps even
  on an empty page, so the GPU run must be windowed. service.sh runs it hourly (with the moves test). Result: 60
  (vsync cap) with shadows.
- Lighting: sun at Cambridge mid-June 14:00 BST (azimuth ~200°, elevation ~58°), 2048 PCF-soft shadow map over a
  240 m box that follows the camera, snapped to texels. `?quality=low` (default on touch devices) turns shadows off.
  Screenshot: docs/shadows_session7.png. Not yet checked against the benchmark (none yet), so it's unverified.
- Human scale: eye 1.65 m, walk 1.4 m/s.

Learned
- Swiftshader can't hold frame rate with shadows (jump and double-tap tests fail on frame time), so moves are now
  checked in the GPU run. Swiftshader still measures load and errors.
- The lumpy LiDAR heightfield roofs are the most visibly wrong thing at eye level near GSM (see the dev renders).

Next
1. Once the token arrives: freeze the benchmark, record the baseline photo_match_score, then add judged_realism
   (Claude vision judge, 50 fixed views, blind A/B order) and the visual_quality rubric (30 views).
2. Centre ring: plane-fitted roofs (RANSAC facets), facade colour/material per building from photos (Commons/Mapillary,
   excluding the held-out set), ground materials on King's Parade and Market Square, OSM street furniture.
3. Start the real_facade_pct / roof_match_pct / street_objects_pct measurements so finished_radius_m can be computed.
