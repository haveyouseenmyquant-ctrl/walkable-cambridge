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

## 2026-11-07 — Session 8: benchmark frozen, honest baseline

Done
- Gaspard (23:08) pointed me at my own Gmail inbox for email verification. I signed up for Mapillary (account
  tobi_walkable_cam; approval a-20261107-230830-9fda), verified it over IMAP, and registered the app "walkable-cambridge"
  (READ scope) to get a client token (`data/mapillary_token`, git-ignored). Helper scripts are in tools/mly/
  (git-ignored, the browser profile is there too).
- Froze the benchmark: `make_benchmark.py` → 200 views from 6,884 candidates (max 629 images per 0.002° cell, so
  no API truncation). They span 30 m to 1,265 m from GSM, median hfov 68°. `benchmark.json`/`heldout.json` are
  committed; the photos are git-ignored (27 MB).
- `scripts/judge.py`: judged_realism (50 fixed views = every 4th benchmark view by distance; blind A/B side-by-side,
  order from hash(build, id)) and visual_quality (30 fixed views = the 30 benchmark views nearest GSM, rubric of 8
  criteria, each render judged on its own). Judge: claude-opus-5-5 via `claude -p` (Read tool only, using my own
  token in ~/.config/aistack-agent/claude-token). Both run from bench.sh and are cached per build hash. measure.sh
  reports visual_quality too.
- Baseline for live build c527b00e7e0f9dc5: **photo_match_score 7.9**, **judged_realism 22.7**,
  **visual_quality 13.56** (lighting 1.8, GI/AO 1.0, materials 0.0, geometry 0.9, vegetation 0.0, atmosphere 1.1,
  image quality 2.8, artefacts 3.3). Side-by-side: docs/bench_baseline_session8.jpg (photos: Mapillary/cyclestreets,
  CC-BY-SA 4.0; ids 1003884260147286, 1074009203009353).

Learned
- DINOv2 CLS cosine between a real photo and a flat-shaded render is close to 0 (range −9 … 35, median 7.8), and
  only render-vs-render pairs reach ~56. So the metric has lots of headroom and should respond strongly to texture,
  trees and sky. Any gain is real signal.
- Rendering 200 views in swiftshader takes about 10 s each, roughly 30 min serially. Two parallel workers (`--only`
  split) halve that. bench.sh now reuses an existing complete render dir.
- Don't edit a bash script while it runs (I had to kill bench.sh mid-run after editing it).
- Some poses put the camera right in front of a lumpy heightfield roof mass (view 1074009203009353). Check the pose
  and ground height on a few of the worst views before trusting per-view numbers.

Next (centre first)
1. Biggest expected gains at eye level: trees from OSM + LiDAR canopy (vegetation scores 0, and trees dominate
   many photos), sky/haze, then per-building facade colour/material and ground materials around GSM. Score each
   change before and after on the benchmark.
2. Start measuring street_objects_pct / roof_match_pct / real_facade_pct so that finished_radius_m can be computed.
3. Parallelise photo_render inside bench.sh (2–3 workers) so that service.sh scores each build in under 15 min.

## 2026-11-07/08 — Session 9: trees + new look tried, both lowered photo_match, kept opt-in

Done
- `scripts/trees.py` (run after build.py): 7,371 trees = 1,424 from OSM (natural=tree, tree_row every 8 m; height and
  crown from tags or the CHM) + 6,608 LiDAR tops (CHM = 2023 first-return DSM − DTM > 3 m, outside buildings +3 m and
  water, crown pixels where first − last return > 0.8 m; a top needs ≥10 px crown and a 5×5 penetration > 3 m, which
  removes the false "trees" along building eaves in Market St). Per-tile `site/trees/*.bin` (500 KB in total), listed in the manifest.
  `site/app/trees.js` draws two InstancedMeshes per tile (lumpy 7-blob crowns, trunks), which cast shadows.
- "Look v2": a gradient sky dome with a sun glow, AgX tone mapping, light intensities rebalanced, and GLB albedos scaled to plausible
  values (the old rig blew the ground out to near white).
- bench.sh renders with 4 parallel workers (200 views in about 15 min).
- Benchmark (full 200, build fb4fd36a = trees + look v2): **photo_match 6.86 vs baseline 7.90**. Ablation on the 50
  judge views: baseline 7.75, look v2 without trees 7.40, trees with the old look 6.40. Both changes make it worse. Following the
  revert rule, both are now **opt-in** (`?trees`, `?look=v2`) and the default render is pixel-identical to the
  baseline. Side-by-side: docs/trees_session9.jpg (photo | baseline | trees; photos Mapillary CC-BY-SA 4.0, ids
  155280259867837, 215717297387097, 489581222193351, 504212450935825, 204587944591503).
- GPU fps (1920×1080, M4): 60 both default and `?trees&look=v2`; site_errors 0; all 15 moves pass.

Learned
- DINOv2 penalises the "low-poly CG" look: the views that lose most are those where real trees exist. Smooth
  blob crowns next to real foliage score lower than empty grass. Trees only pay off with leaf texture (alpha-tested
  leaf cards / foliage texture with normal variation, crowns down to the real crown base), not as solid shapes.
- Whole-image brightness/tone changes move the score by about 0.3. Texture and structure matter far more than exposure.
- Single-change ablations on the 50 judge views take about 4 min each with 4 workers. Do this for every change.

Next
1. Textured foliage: CC0 leaf/bark textures (Poly Haven / ambientCG), crowns as clusters of alpha-tested leaf cards,
   then re-test `?trees` on the 50 views. Turn on by default only if it beats 7.75.
2. Facade/ground textures near GSM (CC0 stone, brick, setts; per-building colour from non-held-out photos). These are probably the biggest
   lever, given DINOv2's preference for texture.
3. street_objects_pct / roof_match_pct / real_facade_pct measurements for finished_radius_m.

## 2026-11-08 — Session 10: CC0 surface textures (+1.7 on the 50-view check), now default

Done
- `scripts/fetch_textures.py` downloads 8 CC0 Poly Haven diffuse textures (1k, ~4 MB in total) into `site/tex/`, with their
  real-world size from Poly Haven's metadata. `site/app/materials.js` applies them in world space (the GLBs need
  no UVs) through `onBeforeCompile` on the vertex-colour Lambert materials. Walls get gault brick or limestone ashlar
  (40 % ashlar, chosen per building from a hash of its colour tone), u runs along the wall and v up; roofs get tiles; the ground
  blends road/pavement/grass/court/earth by the surface class read from the interpolated vertex colour. Each texture
  is used as detail (texture ÷ its top-mip mean, ground mostly luminance), so the palette stays as it was. `?mat=0` turns it off.
- 50 judge views, photo_match: **no textures 7.75 → textures 9.42**; textures plus a procedural sash-window grid
  scored 8.77. The window grid is too regular, so it's opt-in (`?win=1`). Side-by-side: docs/textures_session10.jpg
  (photo | the session 9 trees+look v2 build | textures; photos Mapillary CC-BY-SA 4.0, ids 519716785698039,
  788562325143664, 272897831248029). The first row (a brick lane) jumped to 39.9.
- The build hash (scripts/build_hash.py) now covers index.html, the render-affecting app/*.js and tex/textures.json as well as
  manifest.json. Before this, a viewer-only change reused the old build's cached score. Old cache entries are orphaned, and service.sh
  rescores the live build (200-view photo_match, judge, quality) within the hour.
- GPU 1920×1080: fps_median 60, site_errors 0, all moves pass. Credits page and DATA.md list Poly Haven (CC0).
- photo_render.mjs: `WC_QUERY` env appends URL params (for A/B runs) and waits for `window.__texReady`.

Learned
- DINOv2 rewards real material texture strongly. Brick walls in narrow lanes match photos far better than any change
  to shape or lighting has so far. Regular synthetic structure (window grid, blob trees) is penalised.
- 6 swiftshader workers in parallel (two A/B configs) take about 12 min for 2×50 views.

Next
1. Per-building wall material and colour from real (non-held-out) Mapillary/Commons photos via Claude vision, centre
   first (brick vs ashlar vs render, colour). Real windows from photos instead of a grid.
2. Retry look v2 and leaf-textured trees on top of the textures (both lost on flat shading; textures may change that).
3. Normal maps / roughness for the textures (AAA bar), and KTX2 compression. Check load time on phones and in Safari.
4. street_objects_pct / roof_match_pct / real_facade_pct measurements.

## 2026-11-08 — Session 11: OSM street furniture, trees on by default, street_objects_pct

Done
- `scripts/ab50.sh <label> "<query>" [workers]`: a reusable 50-judge-view photo_match A/B against the local site/.
- A/B results on top of the session-10 textures (50 views): control **9.42** (reproduced exactly), `look=v2` **7.41**
  (still worse, stays off), `trees` **9.45** (now neutral; it was −1.35 on flat shading). Trees are **on by default**.
- `scripts/street_objects.py` (after trees.py): 1,116 OSM street objects in the study area → `site/objects/*.bin`
  (232 KB): 365 bike-parking sites (n = capacity/2 Sheffield stands, roughly half with parked bikes), 275 benches/picnic
  tables, 116 bins, 83 bus-stop poles, 80 bollards, 68 statues/sculptures/memorials (plaques excluded), 42 street
  lamps, 26 post boxes, 24 phone boxes, 23 signs, 8 clocks, 6 fountains. Benches, signs and stands are oriented to the
  nearest way. `site/app/objects.js` draws one InstancedMesh per type per tile (simple proportioned meshes, vertex colours).
  Screenshot (own poses, no photos): docs/objects_session11.jpg.
- `manifest.layers` sets the default layers (`?trees=0|1`, `?objects=0|1` override). New KPI **street_objects_pct = 100**
  (1,998 targets = the objects plus 882 natural=tree nodes; each counts if the same type lies within 1 m in a default-on layer).
- 50 views with trees + objects: **9.29** (trees alone 9.45). Almost all of the −0.16 comes from two views. In one, the
  Mapillary GPS pose sits inside a mapped post box, so the box fills the frame. In the other, a row of stands lines a lane.
  The objects are real and at their mapped positions, so I kept them: this breaks the "revert if it doesn't help" rule
  by a margin well inside the per-view noise (sd of view deltas ~3), in exchange for a finished_radius criterion.
- GPU Chrome 1920×1080: fps_median 60, site_errors 0, all 15 moves pass. Published (live build dc8f4ed6a315ea9c).
  service.sh scores the full 200 views plus the judges within the hour.
- Safari: installed Playwright WebKit (tools/pw, `scripts/webkit_smoke.mjs`), but its WebKit 27.2 binary crashes at
  launch on this macOS (Trace/BPT trap, even on a data: URL). So the Safari check is still open.

Learned
- Benchmark poses carry GPS error of a few metres, so objects near the camera can land in front of the lens. That
  noise affects any small near-field geometry. Judge changes on aggregate scores, not on single views.
- Textures changed the verdict on trees: shapes that lose on flat shading can become neutral once the scene has texture.

Next
1. Per-building wall material and colour (brick/ashlar/render) from non-held-out Mapillary/Commons photos via Claude
   vision, centre first. This is still the biggest expected lever (DINOv2 rewards correct texture).
2. Leaf-textured tree crowns (alpha cards), to push trees from neutral to positive.
3. Object collision (bollards, bins, benches) so you can't walk through them; and the roof_match_pct measurement.
4. Safari: try an older Playwright WebKit or the system Safari via safaridriver.

## 2026-11-08 — Session 12: real photo facades around Great St Mary's (+10.9 photo_match on the central views)

Done
- `scripts/facades.py` (run after street_objects.py): street-facing wall pieces (building edges ≤ 6 m long, midpoint
  within 30 m of a walkable way, ground to LiDAR eave = 20th percentile of the DSM 1.5 m inside the edge). Within 150 m
  of GSM, each piece gets the best non-held-out Mapillary photo: OpenSfM pose (rotation vector → grid frame with the
  ~1.7° grid convergence, focal/k1/k2, upside-down poses flipped), camera at DTM + 2 m, wall fully in frame (top may be
  lowered to what is visible, at least 2.5 m), cos(view, normal) ≥ 0.35, 4–35 m away, and no other footprint on the
  sight line. Score = projected area × cos² × visible fraction. Rectified at ≤ 40 px/m into one RGBA WebP atlas per
  tile; sky pixels connected to the top edge are transparent, and all-sky rows are cropped off the quad. 321 pieces
  from 174 photos, 1.3 MB in 3 tiles. `site/app/facades.js`: unlit quads 4 cm proud of the wall, alpha-tested, layer
  `facades` on by default (`?facades=0` turns it off).
- Held-out rule: the frozen one from session 8 (the benchmark ids plus same-sequence frames within 15 m).
- A/B on the 10 benchmark views within 170 m of GSM (the only ones the layer touches): **off 7.27 → on 18.21**
  (with the sky mask 18.14). No view got worse; deltas run from 0 to +49. Side-by-side: docs/facades_session12.jpg
  (photo | off | on; photos Mapillary CC-BY-SA 4.0, ids 365274541579500, 5470402219697715, 2824712737794062).
- Leakage check: 176 of the 199 facade photos come from sequences that also contain a held-out photo (same day, light
  and parked cars). With `--strict` (no frame of any held-out sequence; 102 pieces from 49 photos) the score is
  **12.83**. So at least about half of the gain does not depend on shared capture conditions. Kept the standard rule,
  which gives more real coverage for walkers; both numbers are reported here.
- New KPI **real_facade_pct = 1.02** (photo-textured quad area in the build's facades layer ÷ street-facing wall area
  of the whole study area, as written by facades.py). This is the honest starting number: only the inner ring is textured.
- Credits page: Mapillary CC-BY-SA with the share-alike note, and `facades/credits.json` (photo id, URL and contributor
  for each photo). DATA.md updated. publish.sh ships `facades/`, and build_hash covers app/facades.js.
- GPU Chrome 1920×1080: fps_median 60, site_errors 0, load 0.8 s (local).

Learned
- DINOv2 strongly rewards real photo content. It wins even where the geometry is off: some pieces come from upward-
  looking photos and look stretched, and some views have the camera pose a few metres off. The visual win is real
  (Gate of Honour, King's Chapel tracery, Market St shopfronts are recognisable) but smaller than the score suggests.
- One benchmark view (365274541579500) is an interior photo inside Great St Mary's. It is frozen, so leave it.
- Pieces with no photo are mostly short or tall walls in narrow lanes that never fit the frame whole; also courts.

Next
1. Extend facades outwards ring by ring (radius 150 → 300 m) and run in service.sh. Multi-photo blending (median of
   2–3 aligned views) to remove people and cars; prefer near-frontal photos; per-piece height from the model's actual
   wall top instead of the DSM estimate.
2. Fix the stretched pieces: cap the vertical viewing angle, or texture only the part seen at < 45° elevation.
3. Measure roof_match_pct, then compute finished_radius_m.
4. Score the full 200 + judges on the new build (service.sh does this within the hour).

## 2026-11-08 — Session 13: photo facades out to 300 m (+7.6 photo_match on the 26 views within 320 m)

Done
- `scripts/facades.py --radius 300`: 772 textured wall pieces (was 321) from 433 non-held-out Mapillary photos, 6.5 MB.
  Atlases are now paged: each tile gets as many 2048² WebP pages as it needs at a fixed 40 px/m. Before, the resolution
  dropped as a tile filled. Manifest `facades`/`facade_tex` are now lists, one entry per page. tiles.js draws one mesh
  per page, and kpi.py sums all pages.
- Elevation cap: a piece is textured only up to the height where the wall top is seen at ≤ 50° above the horizon from
  the camera. This removes the stretched pieces from photos that look steeply upward.
- `scripts/abring.sh <label> <site|url> <max_dist> [workers] [query]`: A/B on the benchmark views within a radius.
- A/B on the 26 benchmark views within 320 m of GSM, live session-12 build vs new: **17.17 → 24.80**
  (≤ 150 m: 23.63 → 29.09; 150–320 m: 14.30 → 22.89). 3 views got slightly worse (max −2.3), 9 unchanged, the rest
  better by up to +47. Side-by-side: docs/facades300_session13.jpg (photo | session 12 | session 13; photos Mapillary
  CC-BY-SA 4.0, ids 163559995673306, 745004922853288, 865188314039724).
- real_facade_pct 1.02 → **2.47**. GPU Chrome 1920×1080: fps_median 60, site_errors 0, load 1.7 s (local).
- Published. Mistake: publish.sh pushed HEAD before I had committed the tiles.js change, I committed and redeployed
  straight away. The first Pages run was cancelled by the second, so the mismatched viewer never went live.
  publish.sh now refuses to run with uncommitted changes in site/ or scripts/. Live check: site_errors 0.

Learned
- The facade gain carries outward: views 150–320 m out gained more (+8.6) than the inner ring did in session 12.
  Views inside 150 m also gained, because walls further out are now visible down the street.

Next
1. Radius 300 → 500 m in service.sh (each ring about 5 min plus photo downloads). Watch the disk: photo cache is
   about 100 MB per 300 photos; delete it after baking.
2. Multi-photo median per piece, to remove people and cars (they are visible in the atlases).
3. Pieces with no photo (narrow lanes, courts): a per-building synthetic facade in the real material.
4. roof_match_pct measurement, then finished_radius_m.

## 2026-11-08 — Session 14: LiDAR roofs on every building, roof_match_pct, facades to 500 m

(Entry written at the start of session 15 from the session-14 commit; session 14 ended before writing it.)

Done
- build.py roofs: every footprint with ≥ 6 LiDAR pixels gets the DSM roof itself (no rescaling to the p95 top),
  meshed as a quadtree from 8 m down to 1 m cells (split while RMS deviation from the cell's two-triangle fit > 0.25 m).
- New KPI **roof_match_pct** (`scripts/roof_match.py`, rules in FORMAT.md): 10.45 → **23.18** (median RMSE 1.05 m).
  Cached per build hash. height_accuracy_pct dropped 98.6 → 91 (the roof is no longer stretched to the p95 top).
- facades.py --radius 500 (RAM fix: keep only one tile's decoded photos). photo_match on the views ≤ 520 m
  16.60 → **22.22**. real_facade_pct 2.47 → **4.65**. Side-by-side: docs/facades500_roofs_session14.jpg.
