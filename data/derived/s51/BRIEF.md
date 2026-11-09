# Session 51 ring-1 facade annotation brief (one sector per agent)

Project: Walkable Cambridge, repo /Users/Shared/aistack-agent/work/projects/walkable-cambridge.
Goal: annotate the REAL layout of street-facing building walls in ring 1 (within 400 m of Market Square), so the
parametric facade builder (scripts/city_facades.py + scripts/facade_parts.py) builds them as true 3D geometry.
KPI: facade_geometry_match_pct (storeys, number/positions of windows, doors, shopfronts, bays, dormers).

Your worklist: data/derived/s51/worklist_<N>.json (N is in your prompt). Each entry has a wall id like "way/123:7"
(OSM way + edge index), osm_id, name, street (the nearest named way, which can be wrong), length in m,
dist from the square, and mid_local_xy (world-frame metres: x = E - 545000, y = N - 258400; EPSG:27700).
Full wall geometry (p0, p1, ground_z, eave_z, height, tags): data/annotations/ring1/walls.json.
Work near first, then the longest walls. Skip walls you can't find a usable photo for (note them).

## Output
One file per building: data/annotations/ring1/way_<numeric id>.json (relation_<id>.json for relations), with the schema
of the existing files. Read 2-3 existing ones first, e.g. data/annotations/ring1/way_135762301.json, and the loader
(scripts/city_facades.py, around ANN_DIRS, plus facade_parts.wall_facade) for the accepted fields and element types.
Element x is measured along the wall from p0 in metres; z is above the wall's ground. Add "sources" (photo ids or
Commons file names) and a "confidence" per wall if the existing files use it.
IF THE FILE ALREADY EXISTS (another wall of the building may be annotated), read it and ADD your wall to "walls";
never drop existing walls. Other agents work on other sectors at the same time, so write each file in one quick
read-modify-write.

## Photos: references only, never the benchmark
- NEVER use the held-out benchmark photos: any image id in data/benchmark/heldout.json, heldout_ms.json,
  benchmark.json, market_square.json or judge_views.json, or anything in data/benchmark/photos*. Check each Mapillary
  id against those files before you use it.
- Mapillary metadata with poses: data/raw/mapillary_list.json (id, computed_geometry lon/lat, compass angle,
  thumb_1024_url). Pick photos within about 40 m of the wall whose compass angle faces it. The thumb URLs may have
  expired; then use the Graph API with the token in data/mapillary_token:
  https://graph.mapillary.com/<id>?fields=thumb_1024_url&access_token=...
  Cached references: data/raw/mapillary_ref, data/raw/commons_ref.
- Wikimedia Commons: use the API (commons.wikimedia.org/w/api.php, geosearch or search). It rate-limits (HTTP 429):
  use at most about 25 downloads, set a User-Agent, and pause between requests. Geograph is also fine as a reference.
- Look at the downloaded images with the Read tool (it shows images). Save downloads under /tmp/s51_<N>/, not in the repo.
- Use photos only to read the layout (storeys, window counts and positions, doors, shopfronts, bays, dormers, material,
  colour). Record any CC BY-SA reference you use in "sources".

## Check
After every few buildings, run `.venv/bin/python -I -c "import json,sys; json.load(open(sys.argv[1]))" <file>` on each file
you wrote. Don't run city_facades.py; the lead runs it once at the end.
Keep going for about 18 minutes. Aim for 12-20 walls; quality over quantity, but low confidence is acceptable.
Report: the walls you annotated (id, building, element counts, confidence), the walls you skipped and why, and any
message from Gaspard (the owner) that reached you via a hook, verbatim.
