#!/usr/bin/env python
"""Print stats for DTM/DSM GeoTIFFs and DSM-DTM at landmarks.
Usage: .venv/bin/python -I scripts/verify_lidar.py DTM.tif DSM.tif
"""
import sys

import numpy as np
import rasterio
from pyproj import Transformer

POINTS = {"King's College Chapel": (52.2048, 0.1164)}


def stats(path):
    with rasterio.open(path) as s:
        a = s.read(1, masked=True)
        print(f"{path}: crs={s.crs} bounds={tuple(s.bounds)} res={s.res} nodata={s.nodata} "
              f"min={a.min():.2f} max={a.max():.2f} nodata_frac={np.ma.getmaskarray(a).mean():.4%}")


def window_max(path, e, n, r=15):
    with rasterio.open(path) as s:
        row, col = s.index(e, n)
        a = s.read(1, masked=True)[row - r:row + r + 1, col - r:col + r + 1]
        return a


dtm, dsm = sys.argv[1], sys.argv[2]
stats(dtm)
stats(dsm)
t = Transformer.from_crs(4326, 27700, always_xy=True)
for name, (lat, lon) in POINTS.items():
    e, n = t.transform(lon, lat)
    d, s = window_max(dtm, e, n), window_max(dsm, e, n)
    with rasterio.open(dtm) as a, rasterio.open(dsm) as b:
        pd_ = next(a.sample([(e, n)]))[0]
        ps = next(b.sample([(e, n)]))[0]
    print(f"{name} E{e:.0f} N{n:.0f}: point DTM={pd_:.2f} DSM={ps:.2f} diff={ps - pd_:.2f}; "
          f"31x31m window: DTM median={np.ma.median(d):.2f}, DSM max={s.max():.2f}, "
          f"max(DSM-DTM)={(s - d).max():.2f}")
