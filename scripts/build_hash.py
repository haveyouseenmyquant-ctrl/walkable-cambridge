"""Print the build hash (sha256, first 16 hex) of a site dir or URL: manifest.json plus the viewer files that
change what is rendered (session 10: viewer-only changes such as materials must get their own score; session 32: + the zone loader and zone.json; session 42: + app/game/*)."""
import hashlib
import sys
import urllib.error
import urllib.request

FILES = ["manifest.json", "index.html", "app/main.js", "app/tiles.js", "app/materials.js", "app/trees.js", "app/objects.js", "app/facades.js", "app/zone.js", "zone/zone.json", "cityfac/index.json",
         "tex/textures.json",
         # session 42: the game layer, so game KPI caches (<hash>_game.json, _gameplay.json) follow game changes
         "app/game/classes.js", "app/game/core.js", "app/game/encounters.json", "app/game/hud.js", "app/game/index.js", "app/game/itemdefs.js", "app/game/items.js", "app/game/mobs.js", "app/game/sfx.js", "app/game/vfx.js",
         # session 73: the wizard model and the remaining viewer modules (a wizard.js-only change kept the old cache)
         "app/game/wizard.js", "app/avatar.js", "app/player.js", "app/grass.js", "app/markings.js", "app/collision.js"]
src = sys.argv[1].rstrip("/")
h = hashlib.sha256()
for f in FILES:
    try:
        if src.startswith("http"):
            data = urllib.request.urlopen(urllib.request.Request(f"{src}/{f}", headers={"User-Agent": "walkable-cambridge-kpi"}), timeout=30).read()
        else:
            data = open(f"{src}/{f}", "rb").read()
    except (FileNotFoundError, urllib.error.HTTPError) as e:
        if f == "manifest.json":
            raise
        data = b""
    h.update(f.encode() + b"\0" + hashlib.sha256(data).digest())
print(h.hexdigest()[:16])
