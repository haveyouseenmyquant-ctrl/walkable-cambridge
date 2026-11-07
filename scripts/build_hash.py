"""Print the build hash (sha256 of manifest.json, first 16 hex) of a site dir or URL."""
import hashlib
import sys
import urllib.request

src = sys.argv[1]
if src.startswith("http"):
    data = urllib.request.urlopen(urllib.request.Request(src.rstrip("/") + "/manifest.json", headers={"User-Agent": "walkable-cambridge-kpi"}), timeout=30).read()
else:
    data = open(src.rstrip("/") + "/manifest.json", "rb").read()
print(hashlib.sha256(data).hexdigest()[:16])
