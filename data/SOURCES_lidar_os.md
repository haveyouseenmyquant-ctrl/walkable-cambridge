# Sources: EA LiDAR and OS OpenData

All files downloaded **2026-11-07**, with no login or API key. Licence for every file: **Open Government Licence v3.0** (https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/).
Reproduce with `.venv/bin/python -I scripts/download_lidar_os.py`. Mosaic/clip: `scripts/mosaic_lidar.py`. Checks: `scripts/verify_lidar.py`.

Study-area margin bbox (EPSG:27700): E 544000–546000, N 257400–259400. It sits entirely inside two EA 5 km tiles, **TL45nw** (EA id TL4055, E540000–545000 N255000–260000) and **TL45ne** (TL4555, E545000–550000 N255000–260000).

## Required attribution

- EA LiDAR: "© Environment Agency copyright and/or database right 2022. All rights reserved." (composite 2022). For the NLP 2023 files use 2023.
- OS: "Contains OS data © Crown copyright and database right 2026"

## Environment Agency LiDAR

Tile search API used (POST, GeoJSON polygon in lon/lat WGS84; BNG coordinates are rejected):
`https://environment.data.gov.uk/backend/catalog/api/tiles/collections/survey/search`
Download pattern (plain GET, which returns a zip): `https://environment.data.gov.uk/tiles/collections/survey/{product}/{year}/{res}/{tileid}`

No 50 cm or 25 cm products exist for this area (the search returned only 1 m and 2 m rasters), so there are no `*_50cm.tif` outputs.

### Raw archives (data/raw/lidar/<name>/<name>.zip, extracted to ./extracted/)

| Product | Version / survey dates | Res | Tile | URL | Size (bytes) |
|---|---|---|---|---|---|
| LIDAR Composite DTM | 2022 composite; built from NLP flights 2019-12-11 (P_10771) + 2018-11/12 (P_10785, TL45ne only) | 1 m | TL45nw | https://environment.data.gov.uk/tiles/collections/survey/lidar_composite_dtm/2022/1/TL4055 | 62,323,941 |
| LIDAR Composite DTM | same | 1 m | TL45ne | https://environment.data.gov.uk/tiles/collections/survey/lidar_composite_dtm/2022/1/TL4555 | 62,150,927 |
| LIDAR Composite First Return DSM | same | 1 m | TL45nw | https://environment.data.gov.uk/tiles/collections/survey/lidar_composite_first_return_dsm/2022/1/TL4055 | 66,645,164 |
| LIDAR Composite First Return DSM | same | 1 m | TL45ne | https://environment.data.gov.uk/tiles/collections/survey/lidar_composite_first_return_dsm/2022/1/TL4555 | 70,581,602 |
| National LiDAR Programme DTM | 2023, flown 2023-02-13 (P_12744) | 1 m | TL45nw | https://environment.data.gov.uk/tiles/collections/survey/national_lidar_programme_dtm/2023/1/TL4055 | 62,824,921 |
| National LiDAR Programme DTM | 2023 | 1 m | TL45ne | https://environment.data.gov.uk/tiles/collections/survey/national_lidar_programme_dtm/2023/1/TL4555 | 63,073,189 |
| National LiDAR Programme DSM | 2023 | 1 m | TL45nw | https://environment.data.gov.uk/tiles/collections/survey/national_lidar_programme_dsm/2023/1/TL4055 | 64,590,036 |
| National LiDAR Programme DSM | 2023 | 1 m | TL45ne | https://environment.data.gov.uk/tiles/collections/survey/national_lidar_programme_dsm/2023/1/TL4555 | 67,211,610 |
| National LiDAR Programme First Return DSM | 2023 | 1 m | TL45nw | https://environment.data.gov.uk/tiles/collections/survey/national_lidar_programme_first_return_dsm/2023/1/TL4055 | 66,701,377 |
| National LiDAR Programme First Return DSM | 2023 | 1 m | TL45ne | https://environment.data.gov.uk/tiles/collections/survey/national_lidar_programme_first_return_dsm/2023/1/TL4555 | 69,371,863 |

Source tiles: float32 GeoTIFF, EPSG:27700, heights in metres ODN, nodata −3.4028235e38.

### Derived products (data/lidar/), 2000×2000 px, 1 m, EPSG:27700, bounds (544000, 257400, 546000, 259400), float32, nodata −9999, deflate

| File | From | Size | Min/max (m) | Nodata | King's Chapel DSM−DTM |
|---|---|---|---|---|---|
| dtm_1m.tif | Composite DTM 2022 | 9,035,665 | 3.50 / 32.50 | 0 % | — |
| dsm_1m.tif | Composite First Return DSM 2022 | 10,833,811 | 3.53 / 68.55 | 0 % | 27.3 m at point (99th pct of roof 28.5 m) |
| nlp2023_dtm_1m.tif | NLP DTM 2023 | 9,133,180 | −0.20 / 32.52 | 0 % | — |
| nlp2023_dsm_1m.tif | NLP DSM 2023 | 10,433,437 | −11.75 / 70.59 | 1.34 % | 31.3 m |
| nlp2023_first_return_dsm_1m.tif | NLP First Return DSM 2023 | 10,834,871 | −0.20 / 75.18 | 1.34 % | 31.3 m |

Notes: the composite is gap-filled (no holes). The NLP 2023 rasters are not gap-filled: they have holes (probably water and glass) and some low outliers. The chapel roof reads about 4 m higher in 2023 than in 2019, while the median difference over the whole area is about 0. That could be temporary works on the roof at survey time, and it has not been checked.

## Ordnance Survey OpenData (OS Downloads API, https://api.os.uk/downloads/v1/products)

| Product | Version | Area/format | File | URL | Size (bytes) |
|---|---|---|---|---|---|
| OS OpenMap – Local | 2026-10 | TL 100 km square, ESRI Shapefile (GeoPackage is offered for GB only, 3.48 GB) | raw/os/OpenMapLocal/opmplc_essh_tl.zip (335 MB unzipped, not extracted) | https://api.os.uk/downloads/v1/products/OpenMapLocal/downloads?area=TL&format=ESRI%C2%AE+Shapefile&redirect | 110,082,154 |
| OS Open Roads | 2026-10 | GB, GeoPackage (GB only) | raw/os/OpenRoads/oproad_gpkg_gb.zip (not extracted) | https://api.os.uk/downloads/v1/products/OpenRoads/downloads?area=GB&format=GeoPackage&redirect | 1,010,630,367 |
| OS Terrain 50 | 2026-07 | GB, ASCII Grid + GML (Grid), 50 m | raw/os/Terrain50/terr50_gagg_gb.zip; the TL45 tile (10 km) was extracted to raw/os/Terrain50/tl45/ | https://api.os.uk/downloads/v1/products/Terrain50/downloads?area=GB&format=ASCII+Grid+and+GML+%28Grid%29&redirect | 161,706,566 (TL45 inner zip 52,205) |
| OS Open Zoomstack | 2026-06 | **skipped** | — | GPKG 4,301,453,983 B; MBTiles 2,852,712,448 B (GB only) | — |

Zoomstack was skipped because the GeoPackage is 4.3 GB, over the ~3 GB limit. The MBTiles version (2.85 GB) is only vector tiles, and the disk had only ~9 GB free. OpenMap Local already covers the same features at better detail.
