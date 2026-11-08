"""Per-ring report of the 200-view held-out benchmark (Gaspard, 8 Nov 2026, direction 2d).

Groups the cached per-view scores of a build (photo match: data/benchmark/scores/<hash>.json, judged realism:
<hash>_judge.json, 50 views) by distance from the Market Square centre (52.2053N, 0.1190E) in 150 m rings:
ring 0 = 0-90 m (the zone), ring 1 = 90-240 m, ring 2 = 240-390 m, ... Read-only: it never renders or scores.
Usage: ring_report.py <build_hash> [<build_hash> ...]   prints one JSON object per hash.
"""
import json
import math
import os
import sys

from pyproj import Transformer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SQ = Transformer.from_crs(4326, 27700, always_xy=True).transform(0.1190, 52.2053)


def ring(e, n):
    d = math.hypot(e - SQ[0], n - SQ[1])
    return 0 if d < 90 else 1 + int((d - 90) // 150)


def report(h):
    views = {v["id"]: v for v in json.load(open(os.path.join(ROOT, "data/benchmark/benchmark.json")))}
    out = {"build": h}
    for key, suf, val in (("photo_match", "", lambda x: x), ("judged_realism", "_judge", lambda x: x["score"] * 10)):
        f = os.path.join(ROOT, "data/benchmark/scores/%s%s.json" % (h, suf))
        if not os.path.exists(f):
            continue
        g = {}
        for vid, x in json.load(open(f))["per_view"].items():
            if vid in views:
                g.setdefault(ring(views[vid]["e"], views[vid]["n"]), []).append(val(x))
        out[key] = {"ring%d" % r: {"n": len(s), "mean": round(sum(s) / len(s), 2)} for r, s in sorted(g.items())}
    return out


if __name__ == "__main__":
    for h in sys.argv[1:]:
        print(json.dumps(report(h)))
