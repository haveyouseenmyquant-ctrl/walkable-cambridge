# Data sources and licences

Only free, openly licensed data that may be redistributed on a public website. Raw downloads live in
`data/raw/` (git-ignored, reproducible with the scripts below).

| Source | What | Licence | Attribution (in-game credits page) |
|---|---|---|---|
| OpenStreetMap via Overpass API (`https://overpass-api.de/api/interpreter`), snapshot 2026-11-07T19:55:51Z, bbox 52.1945,0.1030,52.2155,0.1380 (study area + ~200 m), all nodes/ways/relations with full recursion, `out meta` | Buildings, highways/paths, land use, water, bridges, trees | ODbL 1.0 | © OpenStreetMap contributors (openstreetmap.org/copyright) |
| Environment Agency LIDAR Composite DTM and First Return DSM 2022, 1 m (tiles TL4055, TL4555) | Terrain, building heights | OGL v3 | © Environment Agency copyright and/or database right 2022. All rights reserved. |
| Environment Agency National LiDAR Programme DTM/DSM/First Return DSM 2023, 1 m (same tiles) | Second epoch for checking heights | OGL v3 | © Environment Agency copyright and/or database right 2023. All rights reserved. |
| OS OpenMap Local (2026-10, TL square, shapefile) | Building/road/water polygons as a cross-check | OGL v3 | Contains OS data © Crown copyright and database right 2026 |
| OS Open Roads (2026-10, GB GeoPackage) | Road network cross-check | OGL v3 | Contains OS data © Crown copyright and database right 2026 |
| OS Terrain 50 (2026-07, tile TL45) | Coarse terrain beyond LiDAR coverage | OGL v3 | Contains OS data © Crown copyright and database right 2026 |

No 50 cm or 25 cm EA LiDAR exists for this area (the EA survey search returned only 1 m and 2 m rasters).
OS Open Zoomstack was skipped (4.3 GB GeoPackage; OpenMap Local covers the same features at better detail).

Full download URLs, file sizes, survey dates and checks: `data/SOURCES_lidar_os.md`.
Scripts: OSM is fetched with the Overpass query above (see JOURNAL.md, session 1); LiDAR/OS with
`scripts/download_lidar_os.py`, mosaicked/clipped with `scripts/mosaic_lidar.py` into `data/lidar/`
(1 m, EPSG:27700, E 544000–546000, N 257400–259400).

Textures (future): CC0 only (ambientCG, Poly Haven). Photos from Wikimedia Commons/Mapillary only as visual
references, licence checked and credited per item in this file.
