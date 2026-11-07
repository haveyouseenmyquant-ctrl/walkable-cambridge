#!/usr/bin/env python
"""Reproduce the EA LiDAR + OS OpenData downloads for Walkable Cambridge.

No API keys / accounts needed. All data OGL v3.
Usage (from project root):
    .venv/bin/python -I scripts/download_lidar_os.py [--skip-os] [--skip-nlp] [--no-mosaic]

Downloads are written to data/raw/lidar/<name>/<name>.zip and data/raw/os/<product>/.
Archives are only unzipped (never executed); then scripts/mosaic_lidar.py builds
data/lidar/{dtm,dsm}_1m.tif clipped to E 544000-546000, N 257400-259400.
"""
import argparse
import json
import subprocess
import sys
import zipfile
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
RAW_LIDAR = ROOT / "data/raw/lidar"
RAW_OS = ROOT / "data/raw/os"
OUT = ROOT / "data/lidar"

# Search polygon (lon/lat, WGS84) = margin bbox E544000-546000 N257400-259400
SEARCH_URL = "https://environment.data.gov.uk/backend/catalog/api/tiles/collections/survey/search"
SEARCH_POLY = {"type": "Polygon", "coordinates": [[[0.1054, 52.1955], [0.1356, 52.1955],
               [0.1356, 52.2141], [0.1054, 52.2141], [0.1054, 52.1955]]]}
TILE_URL = "https://environment.data.gov.uk/tiles/collections/survey/{product}/{year}/{res}/{tile}"
TILES = {"TL4055": "TL45nw", "TL4555": "TL45ne"}  # EA 5 km tiles covering the bbox
LIDAR = [  # (product id, year, resolution m)
    ("lidar_composite_dtm", 2022, 1),
    ("lidar_composite_first_return_dsm", 2022, 1),
]
NLP = [
    ("national_lidar_programme_dtm", 2023, 1),
    ("national_lidar_programme_dsm", 2023, 1),
    ("national_lidar_programme_first_return_dsm", 2023, 1),
]
OS_API = "https://api.os.uk/downloads/v1/products/{pid}/downloads"
OS_PRODUCTS = [  # (product id, area, format, subformat)
    ("OpenMapLocal", "TL", "ESRI® Shapefile", None),  # GeoPackage only offered for GB (3.5 GB)
    ("OpenRoads", "GB", "GeoPackage", None),
    ("Terrain50", "GB", "ASCII Grid and GML (Grid)", None),
    # OpenZoomstack skipped: GPKG 4.3 GB / MBTiles 2.85 GB, GB-only.
]


def fetch(url, dest, method="GET"):
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        print(f"exists: {dest}")
        return
    print(f"GET {url}\n -> {dest}")
    with requests.request(method, url, stream=True, timeout=600, allow_redirects=True) as r:
        r.raise_for_status()
        tmp = dest.with_suffix(dest.suffix + ".part")
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
        tmp.rename(dest)
    print(f"   {dest.stat().st_size:,} bytes")


def lidar(products):
    avail = requests.post(SEARCH_URL, data=json.dumps(SEARCH_POLY), timeout=120,
                          headers={"Content-Type": "application/geo+json"}).json()
    labels = {r["label"] for r in avail["results"]}
    for product, year, res in products:
        for tile, lab in TILES.items():
            if f"{product}-{year}-{res}m-{lab}" not in labels:
                print(f"NOT AVAILABLE: {product} {year} {res}m {lab}")
                continue
            name = f"{product}_{year}_{res}m_{lab}"
            z = RAW_LIDAR / name / f"{name}.zip"
            fetch(TILE_URL.format(product=product, year=year, res=res, tile=tile), z)
            ex = z.parent / "extracted"
            if not ex.exists():
                with zipfile.ZipFile(z) as zf:
                    for m in zf.namelist():  # guard against path traversal
                        if m.startswith("/") or ".." in Path(m).parts:
                            raise SystemExit(f"unsafe member {m} in {z}")
                    zf.extractall(ex)


def os_data():
    for pid, area, fmt, sub in OS_PRODUCTS:
        meta = requests.get(OS_API.format(pid=pid), timeout=60).json()
        for d in meta:
            if d["area"] == area and d["format"] == fmt and d.get("subformat") == sub:
                fetch(d["url"], RAW_OS / pid / d["fileName"])
                break
        else:
            print(f"no match for {pid} {area} {fmt}")


def mosaic(pattern, out):
    tiles = sorted(str(p) for p in RAW_LIDAR.glob(pattern))
    if tiles:
        OUT.mkdir(parents=True, exist_ok=True)
        subprocess.run([sys.executable, "-I", str(ROOT / "scripts/mosaic_lidar.py"),
                        str(OUT / out), *tiles], check=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-os", action="store_true")
    ap.add_argument("--skip-nlp", action="store_true")
    ap.add_argument("--no-mosaic", action="store_true")
    a = ap.parse_args()
    lidar(LIDAR + ([] if a.skip_nlp else NLP))
    if not a.skip_os:
        os_data()
    if not a.no_mosaic:
        mosaic("lidar_composite_dtm_2022_1m_*/extracted/*.tif", "dtm_1m.tif")
        mosaic("lidar_composite_first_return_dsm_2022_1m_*/extracted/*.tif", "dsm_1m.tif")
        if not a.skip_nlp:
            mosaic("national_lidar_programme_dtm_2023_1m_*/extracted/*.tif", "nlp2023_dtm_1m.tif")
            mosaic("national_lidar_programme_dsm_2023_1m_*/extracted/*.tif", "nlp2023_dsm_1m.tif")
            mosaic("national_lidar_programme_first_return_dsm_2023_1m_*/extracted/*.tif",
                   "nlp2023_first_return_dsm_1m.tif")
