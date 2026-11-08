"""After build.py --out <dir> into a copy of site/: copy the keys the later steps (trees, facades, objects,
markings) added to site/manifest.json into the new manifest (top level, per tile, per building).
  .venv/bin/python -I scripts/merge_manifest.py <old_manifest> <new_manifest>"""
import json
import sys

o, n = (json.load(open(p)) for p in sys.argv[1:3])
for k in o:
    n.setdefault(k, o[k])
for key, idk in (("tiles", "id"), ("buildings", "osm_id")):
    old = {e[idk]: e for e in o.get(key, [])}
    for e in n.get(key, []):
        for k, v in old.get(e[idk], {}).items():
            e.setdefault(k, v)
json.dump(n, open(sys.argv[2], "w"), separators=(",", ":"))
