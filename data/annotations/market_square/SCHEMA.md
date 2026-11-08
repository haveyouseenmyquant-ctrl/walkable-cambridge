# Facade layout annotations (Market Square zone)

One file per building: `data/annotations/market_square/<osm_id with / replaced by _>.json`, e.g. `way_13864148.json`:
```json
{"osm_id": "way/13864148", "sources": ["<mapillary id>", ...], "walls": [ <wall>, ... ]}
```
Each `<wall>` annotates one wall of `walls.json` (same `id`). Wall frame: `x` = metres along the wall from p0 to
p1 (0..length), `z` = metres above the wall's ground_z. Only describe what is really there (from the reference photos).
```json
{"id": "way/13864148:3",
 "storeys": 3, "floor_z": [0, 3.8, 6.9],          // height of each floor level above ground (ground floor first)
 "material": "brick|stone|render|stucco|timber|glass|flint", "wall_colour": "#a8754f", "trim_colour": "#efe9dc",
 "cornice_z": 9.6, "cornice": "none|simple|bracketed|classical", "parapet": false,
 "string_courses": [3.8], "quoins": false, "pilasters": [],          // x positions of pilasters, if any
 "elements": [
   {"type": "window", "style": "sash_georgian|sash_victorian|casement|gothic|modern|oriel|bay",
    "x": 2.1, "w": 1.0, "z": 4.3, "h": 1.7, "panes": [3, 3], "head": "flat|arched|pointed|pediment", "sill": true},
   {"type": "door", "style": "panelled|glazed|arched|gothic", "x": 6.0, "w": 1.0, "h": 2.2, "surround": "none|pilastered|fanlight"},
   {"type": "shopfront", "x0": 0.4, "x1": 5.6, "z1": 3.3, "fascia_text": "Name from OSM", "fascia_colour": "#1b3a2a",
    "text_colour": "#e8d9a0", "door_x": 1.2, "stallriser": 0.5, "awning": false},
   {"type": "dormer", "x": 3.0, "w": 1.2, "h": 1.4}
 ],
 "confidence": "high|medium|low", "notes": "..."}
```
Window `x` is the centre; `z` the sill height above ground; `w`, `h` the opening size.
Never use the held-out photos (data/benchmark/heldout*.json); the reference files in walls.json are already filtered.
