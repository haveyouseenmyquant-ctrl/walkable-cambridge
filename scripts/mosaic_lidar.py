#!/usr/bin/env python
"""Merge + clip EA LiDAR GeoTIFF tiles to the study-area margin bbox (EPSG:27700).

Usage: .venv/bin/python -I scripts/mosaic_lidar.py OUT.tif TILE1.tif [TILE2.tif ...]
Run with -I so nothing is imported from the data directories.
"""
import sys

import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.merge import merge

BBOX = (544000, 257400, 546000, 259400)  # W, S, E, N  (BNG metres)
NODATA = -9999.0


def main(out, tiles):
    srcs = [rasterio.open(t) for t in tiles]
    for s in srcs:
        if s.crs and s.crs.to_epsg() not in (27700, None):
            raise SystemExit(f"{s.name}: unexpected CRS {s.crs}")
    res = srcs[0].res
    arr, transform = merge(srcs, bounds=BBOX, res=res, nodata=NODATA, dtype="float32")
    arr = arr.astype("float32")
    for s in srcs:  # make sure any source nodata (e.g. -3.4e38) becomes NODATA
        if s.nodata is not None and s.nodata != NODATA:
            arr[arr == np.float32(s.nodata)] = NODATA
    arr[~np.isfinite(arr)] = NODATA
    arr[arr < -1000] = NODATA
    profile = dict(driver="GTiff", height=arr.shape[1], width=arr.shape[2], count=1,
                   dtype="float32", crs=CRS.from_epsg(27700), transform=transform,
                   nodata=NODATA, compress="deflate", predictor=3, tiled=True,
                   blockxsize=256, blockysize=256)
    with rasterio.open(out, "w", **profile) as dst:
        dst.write(arr)
    print(f"wrote {out} shape={arr.shape[1:]} res={res}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
