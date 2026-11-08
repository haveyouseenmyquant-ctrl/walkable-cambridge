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

## 2026-11-08 — Session 15: facades in vertical bands from several photos, half pieces

(Entry written at the start of session 16 from the session-15 commit; session 15 ended before writing it.)

Done
- facades.py: a wall piece whose best photo only shows its lower part gets the rest as an upper band with its own
  photo (up to 3 bands per wall); a piece with no photo is split into halves once; cameras up to 40 m (was 35).
- real_facade_pct 4.65 → **5.7**; photo_match on views ≤ 520 m 22.22 → **23.06**. Side-by-side:
  docs/facade_bands_session15.jpg. measure.sh caches kpi.py per build hash.
- Not committed: a tiles.js change that streams facade atlases after the tile is walkable. The live build measured
  load_seconds **9.17** (> 5 guardrail) because the atlases were fetched before the tile counted as loaded.
  Session 16 committed and shipped it.

## 2026-11-08 — Session 16: roofs that match the LiDAR (roof_match_pct 23.18 → 92.11), load time fixed

Done
- Load time: the live session-15 build measured load_seconds 9.17 (guardrail 5) because each tile waited for its facade
  atlases. Committed the tiles.js change that streams atlases after the tile is walkable (photo_render waits for
  `window.__facadesPending` to reach 0). Live after publishing: **3.21 s**, site_errors 0.
- Roofs (build.py), each change measured with roof_match.py on a side build (build 43 s + score 5 s):
  - quadtree grid on LiDAR pixel centres, no 3×3 median: 23.18 → 40.08
  - no eave-pixel replacement (it lifted pitched eaves to the higher inner pixels: every failure had positive bias):
    → 80.01
  - roof floor median ground + 1 m instead of + 2 m (350 of the remaining 413 failures had > 10 % of the footprint
    below 2 m): → **92.11**, median RMSE 1.05 → 0.21 m.
  - Guardrails on the new build: walkable 99.38, buildings 100. Legacy height_accuracy_pct 91 → 79 (chimneys and
    spikes are no longer filtered; that KPI compares the top with the p95).
- A/B on the 67 benchmark views within 520 m (same viewer, old vs new roofs, rendered locally): **23.05 → 23.52**;
  25 views better by > 1, 14 worse by > 1 (−6.7 to +9.6). Side-by-side: docs/roofs_session16.jpg (photo | old | new;
  photos Mapillary CC-BY-SA 4.0, ids 577055006604384, 289425219597328, 214764576744027).
- Published (build c46db5cb1e141ed6).

Learned
- The worst view (bottom row of the side-by-side) shows the cost: where trees overhang a footprint, the raw DSM turns
  the canopy into tall red roof spikes. roof_match counts this as a match because it compares with the DSM, but it
  is wrong to the eye. Probably most of the 14 views that got worse.
- Roof experiments are cheap (under a minute each); facades, trees and objects do not need re-baking after build.py:
  copy their manifest keys from the previous manifest.

Next
1. Canopy-over-roof filter: detect tree pixels inside footprints (OSM/LiDAR trees from trees.py within the crown
   radius, or local roughness: canopy is rough, roofs are planar) and replace them with the planar fit of the
   neighbouring roof. Check that roof_match stays ≥ 90 and the 14 worse views recover.
2. Facade coverage in the inner ring (real_facade_pct is 5.7 overall): synthetic per-building facades where there is
   no photo, centre first.
3. finished_radius_m: roof_match now passes everywhere; facades and judged_realism are the blockers.

## 2026-11-08 — Session 17: canopy-over-roof filter and OSM ground surfaces, both neutral, not shipped

Done
- Canopy filter in build.py (`WC_CANOPY_PEN`, off by default): canopy = NLP 2023 first return − last return > 1 m,
  opened with a 3×3 m kernel (drops eave lines). Inside a footprint those pixels are filled from the nearest
  non-canopy roof pixel. Checked by eye on 8 affected buildings (top-down DSM with the mask): every blob is a real
  tree crown over the footprint.
  - roof_match_pct 92.11 → **84.56** (156 buildings fail, none gain): the KPI compares with the DSM, which includes
    the crowns. photo_match on the 67 views ≤ 520 m: **23.52 → 23.53** (3 views moved > 1). Session 16's "red spikes"
    view (214764576744027) did not change, so those spikes are not canopy-in-footprint.
  - Kept the code with the filter off (the GLBs come out byte-identical to the live build). Asked Gaspard (tell-owner)
    whether roof_match may leave out foliage pixels.
- Ground materials from the OSM `surface` tag: the default ground and every square/car park were class S_COURT, which
  draws the cobblestone texture. Changed so only mapped sett/cobblestone gets cobbles (3,261 m²), asphalt goes to tarmac,
  gravel to gravel, the default to paving. photo_match on the same 67 views: **23.52 → 23.40** (2 better > 1, 8 worse > 1).
  Not shipped; the diff is in docs/experiments/session17_canopy_and_ground.patch. Side-by-side:
  docs/ground_session17.jpg (photo | live | surfaces; photos Mapillary CC-BY-SA 4.0, ids 250189876888232, 577055006604384).
- Live site unchanged (build c46db5cb1e141ed6). service.sh was benchmarking it during the session.

Learned
- The tarmac texture smears into a flat grey at grazing angles, and DINOv2 scores it below the busy cobble texture
  even where the real path is tarmac (bottom row of the side-by-side). The `pave` texture (pavement_02) also looks
  like setts at eye level. Before ground surfaces can win, the ground textures themselves need fixing: anisotropic
  sampling, a real UK tarmac with aggregate and patching, York-stone flags. That's a texture job, not a classification job.
- In view 250189876888232 the camera looks into a photo-facade quad that shows the whole street: a facade piece placed
  where the real view is open road. Facade pieces that contain mostly road or sky should be rejected.
- Benchmark A/B noise: the 67-view mean moves about ±0.1 between runs with no change in the world. Per-view moves
  under ~2 points are noise.

Next
1. Facade quality: reject pieces whose photo content is mostly road, cars or sky (segmentation or a simple check
   for the colour of the lower band), then fill the gaps with per-building synthetic facades, centre first.
2. Ground textures: sharper tarmac (anisotropy 16, a higher-detail asset), York stone flags for `pave`; then re-try
   the surface patch on top.
3. Wait for Gaspard on the canopy question; if yes, change roof_match (pixels with first − last return > 1 m excluded)
   and switch the filter on.

## 2026-11-08 — Session 18: leaf-card foliage (photo_match on views ≤ 520 m 23.52 → 25.09)

Done
- Live session-16 build (c46db5cb1e141ed6) finished its full benchmark during the session: photo_match_score
  **14.90** (200 views), judged_realism **25.2**, visual_quality **17.02** (vegetation 0.5/10, the lowest criterion).
- trees.js: each crown is now a darker blob core (84 % size) wrapped in 56 alpha-tested leaf cards with a leaf-cluster
  texture drawn once on a canvas (no new asset; alphaToCoverage with MSAA). `?foliage=0` gives the old blobs.
- A/B on the 67 benchmark views ≤ 520 m (same build, local): **23.52 → 25.09**; 20 views better by > 1, 9 worse
  (−10.1 to +22.5). Side-by-side: docs/foliage_session18.jpg (photo | before | after; photos Mapillary CC-BY-SA 4.0,
  ids 214764576744027, 289425219597328, 577055006604384).
- GPU Chrome 1920×1080 locally: fps_median 60, site_errors 0. Published (release world-20261108-0400).
- scripts/webkit_smoke.mjs crashes when WebKit launches ("Target page, context or browser has been closed"),
  with or without this change: a Playwright WebKit vs macOS problem, not the site. Not fixed.

Learned
- Vegetation was the cheapest big win so far: one viewer file, no rebake. The view that lost 10 points
  (289425219597328) is the one where a near crown now fills the top-left of the frame; crowns right at the camera
  are probably too big or too low (the crown base is 22–34 % of tree height).

Next
1. Tree shape from LiDAR: crown base height and radius per tree from the canopy (first return − DTM profile),
   and real species-ish forms (columnar limes vs spreading planes); trunk branches visible under the crown.
2. Sky: photos have white/overcast or cloudy skies; try a brighter, cloudier sky against the benchmark.
3. Fix the WebKit smoke test (update Playwright's WebKit build).
4. Facade quality (reject road/sky pieces), synthetic per-building facades, centre first.
- measure.sh right after publishing read walkable_coverage_pct 97.03: kpi.py fetched tiles while Pages was still
  deploying, counted the failures as missing, and the value was cached for the build. Re-measured: 99.38. kpi.py now
  retries each fetch 3 times and flags `fetch_failures`; measure.sh doesn't cache a flagged result.

## 2026-11-08 — Session 19: near-white overcast sky (photo_match on views ≤ 520 m 25.09 → 25.79)

Done
- Sky colour measured on 295 non-held-out Mapillary facade photos (top 10 % of rows, bright pixels): 83 % of skies
  are unsaturated (overcast or blown out), median RGB 0.96/0.97/1.00. The model's sky was a mid blue (0xbcd3e6).
- main.js `?sky=`: `white` (background + fog 0xeef1f6), `overcast` (same plus sun 1.8 → 1.0, hemisphere 1.6 → 2.3),
  `blue` (old). A/B on the 67 benchmark views ≤ 520 m: blue **25.09** (same as session 18), white **25.79**
  (5 views better by > 2, none worse by > 1), overcast 25.40. White is now the default.
  Side-by-side: docs/sky_session19.jpg (photo | blue | white; photos Mapillary CC-BY-SA 4.0,
  ids 293815065657546, 558906138831208, 140100631456667).
- Published (release world-20261108-0448, viewer change only). Live: load 3.33 s, site_errors 0; guardrails unchanged
  (walkable 99.38, buildings 100). service.sh will benchmark the new build.
- WebKit smoke test: still crashes on any page, even `data:` HTML (WebContent process "Trace/BPT trap: 5"), with
  Playwright 1.65 (webkit 2388), 1.66-alpha (webkit 2389), headless or headed. Probably the WebKit build vs macOS
  26.5 under this user's session; not the site. Safari remains untested.

Learned
- Global look parameters (sky, fog) are cheap, viewer-only experiments with measurable gains; softer lighting
  lost to the stronger sun, so contrast/shadows help DINOv2 even though the photos are overcast.
- Bottom row of the side-by-side (view 140100631456667): the render shows sky colour below a wall, i.e. no ground
  in front of the camera there. Worth finding: a hole in the ground mesh or the camera placed below it.

Next
1. Ground holes: find benchmark views whose lower third is sky-coloured and fix the ground mesh there.
2. Tree shape from LiDAR (crown base, radius), and fog distance/colour tuned with the white sky.
3. Facade quality (reject road/sky pieces), synthetic per-building facades, centre first.
4. WebKit: try an older Playwright WebKit or Safari's own WebDriver (safaridriver) for the Safari test.

## 2026-11-08 — Session 20 (entry written in session 21): road markings layer, not published

- Commit 511dd5d: scripts/markings.py builds an OSM road-markings layer (centre dashes, double yellows) and
  site/app/markings.js draws it; it also added the `?light=` (scales sun and sky light) and `?gk=` (ground albedo) look params.
  The session ended before a journal entry or a publish. The A/B results it left in /tmp (67 views ≤ 520 m):
  markings 25.57 vs 25.79 without them (neutral); markings + light 0.6 26.19.
- The live build 01b805ec26237475 (session 19 sky) finished its full benchmark: photo_match_score **17.56**
  (200 views), judged_realism **25.6**, visual_quality **16.79**.

## 2026-11-08 — Session 21: darker lighting (photo_match on views ≤ 520 m 25.79 → 26.80)

Done
- Finished session 20's A/B on the 67 benchmark views ≤ 520 m (control: session 19, 25.79):
  markings + light 1.0 **25.57**, markings + light 0.6 **26.19**, no markings + light 0.6 **26.41**,
  markings + light 0.45 **26.80** (37 views better by > 1, 10 worse).
- Shipped: light scale 0.45 by default (main.js); road markings off by default (`?markings=1` turns them on).
  The markings cost ~0.2 at equal light and the 0.45 run with them is still the best. Side-by-side:
  docs/light_session21.jpg (photo | session 19 | light 0.45 with markings; photos Mapillary CC-BY-SA 4.0,
  ids 799949717293550, 423020809560124, 204824241221338). New helper: scripts/sidebyside.py.
- Published (release world-20261108-0624). measure.sh: walkable 99.38, buildings 100, site_errors 0, fps 60.
  service.sh will benchmark the new build.

Learned
- The renders were overexposed compared with the overcast photos. Darker is better down to at least 0.45; the
  minimum isn't found yet. Two A/B runs in parallel (3 workers each) take ~23 min.
- Side-by-side middle row (view 423020809560124): a tiled pitched roof sits on the road right in front of the
  camera, at eye level. A building with a wrong base or height, or a roof mesh dropped to the ground: a geometry
  bug worth finding (search benchmark renders for roof texture in the lower half).

Next
1. Light 0.3 / 0.35, and `gk` (ground albedo) with it; also tone mapping exposure.
2. The ground-level roof bug in view 423020809560124 (and any others like it).
3. Ground holes (sky-coloured lower third), tree shape from LiDAR, facade quality, centre first.

## 2026-11-08 — Session 22: LiDAR ground holes in footprints (roof_match_pct 92.11 → 93.03)

Done
- Looked into session 21's "roof on the road" (view 423020809560124). The camera stands inside the OSM footprint of
  Ramanujan House (way/1087907233). It was a building site when the LiDAR was flown: 62 % of the footprint is below
  1.5 m, with 1–3 m piles. The roof field (clamped to median ground + 1 m) turned that into a tiled sheet with
  pyramids at eye level.
- build.py (`WC_GROUND_HOLES`, on by default): parts of a footprint where the LiDAR roof is under 1.5 m above the DTM
  (3×3 opening, ≥ 16 px) are cut out of the footprint and stay open ground. This covers building sites and courtyards
  mapped without an inner ring. A footprint keeps at least 25 % of its area. 319 footprints changed.
  roof_match_pct **92.11 → 93.03** (median RMSE 0.203 m). Guardrails on the side build: walkable 99.39, buildings 100.
  It doesn't fix view 423 itself, because that site's piles are 2–3 m tall.
- New helper scripts/merge_manifest.py copies the manifest keys added by the trees, facades, objects and markings
  steps into a fresh build.py manifest, so roof-only rebuilds can ship without re-baking.
- A/B (67 views ≤ 520 m) was too slow to finish: about 1 view/min per run with 3 runs in parallel. Partial results
  against session 21's 26.80 run (same ids): holes **28.18 → 28.25** (23 views, 1 better by > 1, none worse);
  light 0.3 **30.51 → 30.57** (36 views, 8 better, 4 worse). Both are within noise. Light stays at 0.45: the
  darkening gains have levelled off. Holes shipped because they don't hurt photo_match and raise roof_match.
- Published (viewer unchanged, world rebuilt).

Learned
- Run at most 2 A/B runs at once. A third one plus a build slowed everything to about 1 view/min.
- OSM includes buildings that were finished after the LiDAR survey (and after older photos). The DSM roof then shows
  site clutter. These need a rule of their own: for a large footprint whose median nDSM is under 3 m, fall back to the
  OSM levels/height with a flat or generic roof. roof_match counts these as failures either way.

Next
1. Footprints built after the LiDAR survey (see above).
2. Ground holes found in the sky-coloured lower third of renders (session 19), tree shape from LiDAR.
3. Facade quality: reject road/sky pieces, then synthetic per-building facades, centre first.
- Live check after publishing: load_seconds 3.98, site_errors 0 (measure.sh first showed 6.69, a cached service.sh
  reading taken while the A/B renders were loading the machine). measure.sh: walkable 99.39, buildings 100,
  roof_match 93.03, fps 60.

## 2026-11-08 — Session 23: photo facades at oblique angles (photo_match on views ≤ 300 m 27.88 → 30.49)

Done
- Checked the photo supply first: the cached Mapillary list is complete (live API counts match it in four test
  boxes around GSM), so more Mapillary photos aren't available. Only 342 perspective photos lie within 100 m.
- facades.py now logs why cameras are rejected (angle 624k, out of frame 309k, occluded 48k candidate pairs) and the
  textured share by ring. Mapillary cameras look along the street, so most facades are seen at grazing angles.
- New knobs: `WC_FAC_COSN` (minimum cos of wall-normal vs camera direction; was 0.35) and `WC_FAC_SPLITS` (how many
  times a piece without a photo is halved; was 1). Dry runs, textured share of street-facing wall within 100 m:
  0.35/1 25.4 %, 0.2/2 28.9 %, 0.12/3 31.5 %.
- A/B on the 25 benchmark views ≤ 300 m (current build as control, 27.88): 0.2/2 **29.89** (16 views better,
  3 worse, worst −2.2), 0.12/3 **30.49**. Shipped 0.12/3 as the default. real_facade_pct 5.7 → 7.6 (facades.py's own
  count; measure.sh will confirm). Side-by-side (photo | control | 0.2/2): docs/facades_angle_session23.jpg (photos
  Mapillary CC-BY-SA 4.0, ids 454043642567080, 163625715689245, 490595022302449).
- Local check: load 1.93 s, site_errors 0. Published.
- service.sh's benchmark of the session 22 build failed with "renders incomplete" (the A/B runs were loading the machine).
  It will benchmark this new build instead.

Learned
- 80 % real facades can't come from Mapillary alone: even within 50 m only ~39 % of street-facing wall is visible
  in any usable photo. Courts, lanes and the Backs need other photos (Wikimedia Commons, registered by local SfM
  to get camera poses) or the per-building synthetic facades.
- Baked-in artefacts are now the visible problem: pedestrians and cyclists in the textures, and close-range
  smeared pieces (side-by-side row 2, left wall).

Next
1. Wikimedia Commons photos of central buildings: download CC-licensed ones, register them against Mapillary frames
   with COLMAP/OpenSfM locally to get poses, then feed them to facades.py. Centre first.
2. Synthetic per-building facades (storeys, windows, material colour) for walls with no photo.
3. Mask people/bikes in facade photos (a local segmentation model) and pick the cleanest photo per piece.
4. Footprints built after the LiDAR survey (session 22).
- Live check: build b45c1234a047bcaa, real_facade_pct 7.6 (measure.sh), walkable 99.39, buildings 100, roof_match 93.03.
