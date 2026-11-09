"""Write <site>/collision/digest.json: sha256 of every collision tile, so build_hash.py --game (the game KPI cache key)
follows collision changes without fetching 175 MB over the network (session 75)."""
import hashlib
import json
import os
import sys

d = os.path.join(sys.argv[1], "collision")
h = hashlib.sha256()
names = sorted(f for f in os.listdir(d) if f.endswith(".col"))
for f in names:
    h.update(f.encode() + b"\0" + hashlib.sha256(open(os.path.join(d, f), "rb").read()).digest())
out = json.dumps({"tiles": len(names), "sha256": h.hexdigest()})
p = os.path.join(d, "digest.json")
if not os.path.exists(p) or open(p).read() != out:
    open(p, "w").write(out)
print(out)
