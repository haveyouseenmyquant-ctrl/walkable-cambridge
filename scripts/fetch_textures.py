#!/usr/bin/env python3
"""Download the CC0 Poly Haven diffuse textures the viewer uses (site/tex/<slot>.jpg, 1k, re-encoded) and
write site/tex/textures.json with each texture's real-world size in metres (from Poly Haven's dimensions, mm)."""
import json, os, subprocess, sys, urllib.request
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "site", "tex")
SLOTS = {  # slot -> Poly Haven asset (all CC0)
    "brick": "yellow_bricks", "ashlar": "white_sandstone_blocks_02", "roof": "grey_roof_tiles",
    "road": "asphalt_02", "pave": "pavement_02", "grass": "sparse_grass", "court": "cobblestone_floor_08",
    "earth": "gravel_floor",
}
os.makedirs(OUT, exist_ok=True)
meta = {}
get = lambda u: json.load(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "walkable-cambridge"})))
for slot, asset in SLOTS.items():
    info, files = get(f"https://api.polyhaven.com/info/{asset}"), get(f"https://api.polyhaven.com/files/{asset}")
    url = files["Diffuse"]["1k"]["jpg"]["url"]
    dst = os.path.join(OUT, slot + ".jpg")
    if not os.path.exists(dst):
        tmp = dst + ".dl"
        urllib.request.urlretrieve(url, tmp)
        subprocess.run(["sips", "-s", "format", "jpeg", "-s", "formatOptions", "75", "-Z", "1024", tmp, "--out", dst],
                       check=True, capture_output=True)
        os.remove(tmp)
    meta[slot] = {"asset": asset, "size_m": info["dimensions"][0] / 1000, "authors": list(info["authors"]),
                  "licence": "CC0", "url": f"https://polyhaven.com/a/{asset}"}
    print(slot, asset, meta[slot]["size_m"], os.path.getsize(dst) // 1024, "KB")
json.dump(meta, open(os.path.join(OUT, "textures.json"), "w"), indent=1)
