# Walkable Cambridge

A first-person, walkable 3D model of Cambridge city centre in the browser, built only from open data
(OpenStreetMap, Environment Agency LiDAR, OS OpenData, CC0 textures). Built by Tobi, an AI agent
operated by Gaspard Oliviers.

- Study area: `area.geojson` (52.1975–52.2125 N, 0.1080–0.1330 E; fixed).
- Data sources and licences: `DATA.md`.
- Build format (manifest, tiles, collision): `FORMAT.md`.
- KPIs: `./measure.sh` (uses `scripts/kpi.py`; OSM targets from `scripts/osm_targets.py`).
- Fixed landmark list: `landmarks/landmarks.json`.
- Harness self-test: `.venv/bin/python -I scripts/make_test_build.py && .venv/bin/python -I scripts/kpi.py data/testbuild --verbose`.
