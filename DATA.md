# Data sources and licences

Only free, openly licensed data that may be redistributed on a public website. Raw downloads live in
`data/raw/` (git-ignored, reproducible with the scripts below).

| Source | What | Licence | Attribution (in-game credits page) |
|---|---|---|---|
| OpenStreetMap via Overpass API (`https://overpass-api.de/api/interpreter`), snapshot 2026-11-07T19:55:51Z, bbox 52.1945,0.1030,52.2155,0.1380 (study area + ~200 m), all nodes/ways/relations with full recursion, `out meta` | Buildings, highways/paths, land use, water, bridges, trees | ODbL 1.0 | © OpenStreetMap contributors (openstreetmap.org/copyright) |
| Environment Agency LIDAR Composite DTM and First Return DSM 2022, 1 m (tiles TL4055, TL4555) | Terrain, building heights | OGL v3 | © Environment Agency copyright and/or database right 2022. All rights reserved. |
| Environment Agency National LiDAR Programme DTM/DSM/First Return DSM 2023, 1 m (same tiles) | Second epoch for checking heights; trees (canopy height = first-return DSM − DTM, scripts/trees.py) | OGL v3 | © Environment Agency copyright and/or database right 2023. All rights reserved. |
| OS OpenMap Local (2026-10, TL square, shapefile) | Building/road/water polygons as a cross-check | OGL v3 | Contains OS data © Crown copyright and database right 2026 |
| OS Open Roads (2026-10, GB GeoPackage) | Road network cross-check | OGL v3 | Contains OS data © Crown copyright and database right 2026 |
| OS Terrain 50 (2026-07, tile TL45) | Coarse terrain beyond LiDAR coverage | OGL v3 | Contains OS data © Crown copyright and database right 2026 |

No 50 cm or 25 cm EA LiDAR exists for this area (the EA survey search returned only 1 m and 2 m rasters).
OS Open Zoomstack was skipped (4.3 GB GeoPackage; OpenMap Local covers the same features at better detail).

Full download URLs, file sizes, survey dates and checks: `data/SOURCES_lidar_os.md`.
Scripts: OSM is fetched with the Overpass query above (see JOURNAL.md, session 1); LiDAR/OS with
`scripts/download_lidar_os.py`, mosaicked/clipped with `scripts/mosaic_lidar.py` into `data/lidar/`
(1 m, EPSG:27700, E 544000–546000, N 257400–259400).

Textures (session 10, `scripts/fetch_textures.py` → `site/tex/`, 1k diffuse JPEGs): Poly Haven, CC0 —
yellow_bricks, white_sandstone_blocks_02, grey_roof_tiles, asphalt_02, pavement_02, sparse_grass,
cobblestone_floor_08, gravel_floor (authors and URLs in `site/tex/textures.json`). Future textures: CC0 only. Photos from Wikimedia Commons/Mapillary only as visual
references, licence checked and credited per item in this file.

Facade annotation references (session 33, `data/raw/commons_ref/`, git-ignored): 16 Wikimedia Commons / Geograph
photos (CC BY-SA 2.0/4.0) of Petty Cury, Lion Yard and St Edward King and Martyr, used only as visual references for
the layout annotations in `data/annotations/market_square/` (file name, licence and author are listed in each
annotation's `sources`). No pixels from them are in the world.
Added in session 34 (same terms, licence checked via the Commons API): St Mary's Passage: "1 St Mary's Passage" and
"3 St Mary's Passage, Cambridge" (Smb1001, CC BY-SA 4.0), geograph 4994976 Cambridge Satchel Company (Hugh Venables),
6497174 Cuckoo and 7561311 Sahara (Mr Ignavy), 6094985 (John Sutton), 6887870 Ryder & Amies (Colin Smith); Petty Cury:
"Petty Cury, Cambridge" (Magnus Manske, CC BY-SA 3.0), geograph 1944505/1944508 (Stacey Harris), 4040570, 4332543,
5322026, 5897664, 5231641 (N Chadwick), 4350366 (Hugh Venables), 4353388 (Fernweh); Guildhall Street (Magnus Manske,
CC BY-SA 4.0), geograph 6095002 (John Sutton); Market Street: "Market Street, Cambridge" and "1, Market Street"
(Magnus Manske, CC BY-SA 3.0), geograph 4171681/4350410 (Hugh Venables); "St Edward's Passage, Cambridge, looking
toward Peas Hill (cropped)" (CC BY 1.0) and "3-4 St Edward's Passage" (Smb1001, CC BY-SA 4.0). Geograph photos are
CC BY-SA 2.0.
Bespoke models (session 34, references for shape/proportion/colour only, credited in the module docstrings):
`scripts/zone_bespoke_caius.py`: Commons "Trinity Street – View SSW along Gonville & Caius…", "King's Parade – View
West into Senate House Passage…", "King's Parade – View North into Trinity Street…", "Market Hill – View NNW into Rose
Crescent" (Txllxt TxllxT, CC BY-SA 4.0), "1125528 … St Michael's Court" (Tilman2007, CC BY-SA 4.0);
`scripts/zone_bespoke_churches.py`: geograph 3803723 St Michael, Trinity Street (N Chadwick, CC BY-SA 2.0), Commons
St Michael's view east from the churchyard (Txllxt TxllxT, CC BY-SA 4.0), plus the St Edward's photos above.
`scripts/zone_bespoke_kings.py` (session 35, King's College gatehouse and screen): Commons "King's Parade – View WSW on
King's College Gatehouse 1828…", "King's Parade – View NW on Neo Gothic Gatehouse 1828…", "King's College – King's
Parade – View South along Gatehouse & Screen 1828…" (Txllxt TxllxT, CC BY-SA 4.0).
Market stalls / street furniture (session 34, `scripts/zone_props.py`, `scripts/zone_props_furniture.py`; same terms, licence checked via the Commons API): "Cambridge Market stalls at lunchtime" (Jonosunde, CC BY-SA 4.0), geograph 5652394 "Looking over the market stalls in Cambridge" (Richard Humphrey), 1133717 "Empty market stalls", 703624 "Cambridge Market" and 972242 "A vital part of Cambridge" (Sebastian Ballard), all CC BY-SA 2.0. Used only to read the stall look (white canvas with red/blue/green/yellow stripes down the slope, scalloped hems, scaffold frames, striped counter cloths, red side sheets); no pixels from them are in the world.

## Held-out benchmark (session 8)
- 200 Mapillary photos (CC-BY-SA 4.0, contributors credited per photo in `data/benchmark/benchmark.json`),
  picked once on 2026-11-07 by `scripts/make_benchmark.py` from 6,884 candidates in the study area. Frozen. These
  images, and any image in the same sequence within 15 m of one (`data/benchmark/heldout.json`), must never be used to
  build the world. The thumbnails are kept locally only (git-ignored) and are not part of the published site.
- Mapillary API: free client token for the app "walkable-cambridge" (account tobi_walkable_cam), kept in
  `data/mapillary_token` (git-ignored).
- Scoring: DINOv2 ViT-S/14 (facebook/dinov2-small, Apache-2.0), run locally. judged_realism / visual_quality: a Claude
  vision judge (claude-opus-5-5 via the local `claude` CLI), `scripts/judge.py`; fixed view lists in
  `data/benchmark/judge_views.json` (50) and `quality_views.json` (30).
- Facade photo masks (session 24, `scripts/masks.py`): UperNet ConvNeXt-small semantic segmentation
  (openmmlab/upernet-convnext-small, MIT licence, trained on ADE20K), run locally, finds people, bikes and vehicles in
  the facade photos so they are not baked into walls. Only the masks are used; nothing of the model ships.

Photo facades (session 12, `scripts/facades.py` → `site/facades/`, release asset only): wall pieces rectified from
Mapillary street-level photos (CC-BY-SA 4.0) through their SfM camera poses. The atlases are adaptations and are shared
under CC-BY-SA 4.0. Photo ids, URLs and contributors are in `site/facades/credits.json`, which the credits page links to.
Never used: the 200 held-out benchmark photos, or frames of the same sequence within 15 m of one (heldout.json
`sequence_near`). `--strict` also skips every frame of a held-out sequence. Downloaded 2048 px thumbnails are cached in
`data/raw/mapillary_facade/` (git-ignored, ~100 MB).
