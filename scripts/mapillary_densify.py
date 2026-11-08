#!/usr/bin/env python3
"""Re-list Mapillary images over the study area in fine bbox cells and merge them into data/raw/mapillary_list.json.

The graph API silently returns only a sample of the images in a large bbox: the 0.002 deg cells of make_benchmark.py
missed most of them (a 0.0005 deg cell on King's Parade: 24 images from the API, 5 in the list). 0.0005 deg cells
returned the same set as 0.00025 and 0.000125 deg cells in a spot check, so that is the step used here.

  .venv/bin/python -I scripts/mapillary_densify.py [--step 0.0005] [--workers 8]

The benchmark (data/benchmark/benchmark.json) is frozen and unaffected; facades.py keeps excluding the held-out photos
and their sequence neighbours. The old list is kept as mapillary_list.json.bak.
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from make_benchmark import FIELDS, S, W, N, E, token  # noqa: E402

STEP = float(sys.argv[sys.argv.index("--step") + 1]) if "--step" in sys.argv else 0.0005
WORKERS = int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else 8


def get(url):
    for i in range(6):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "walkable-cambridge"}), timeout=60) as r:
                return json.loads(r.read())["data"]
        except Exception as e:  # rate limits / timeouts: back off
            print("retry", i, e, file=sys.stderr)
            time.sleep(5 * (i + 1))
    raise RuntimeError(url)


def main():
    tok = token()
    path = os.path.join(ROOT, "data/raw/mapillary_list.json")
    old = json.load(open(path))
    imgs = {x["id"]: x for x in old}
    cells = [(lo, la) for la in np.arange(S, N, STEP) for lo in np.arange(W, E, STEP)]

    def one(c):
        lo, la = c
        bbox = f"{lo:.5f},{la:.5f},{min(lo + STEP, E):.5f},{min(la + STEP, N):.5f}"
        return get("https://graph.mapillary.com/images?" + urllib.parse.urlencode(
            {"access_token": tok, "fields": FIELDS, "bbox": bbox, "limit": 2000}))

    t0 = time.time()
    with ThreadPoolExecutor(WORKERS) as ex:
        for i, d in enumerate(ex.map(one, cells)):
            for im in d:
                imgs.setdefault(im["id"], im)
            if i % 200 == 0:
                print(f"{i}/{len(cells)} cells, {len(imgs)} images, {time.time() - t0:.0f}s", file=sys.stderr)
    if not os.path.exists(path + ".bak"):
        os.rename(path, path + ".bak")
    json.dump(list(imgs.values()), open(path, "w"))
    print(f"{len(old)} -> {len(imgs)} images ({len(cells)} cells, {time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
