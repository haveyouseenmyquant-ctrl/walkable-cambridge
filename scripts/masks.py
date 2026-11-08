"""Transient-object masks for the facade photos: people, bikes and vehicles must not be baked into walls.

  .venv/bin/python -I scripts/masks.py

For every cached facade photo (data/raw/mapillary_facade/<id>.jpg) writes data/raw/mapillary_masks/<id>.png: 8-bit,
512 px wide, 255 where the photo shows a person, bicycle, motorbike, car, van, bus or truck (dilated a little), else 0.
Model: openmmlab/upernet-convnext-small (MIT; ADE20K semantic segmentation), run locally (MPS if available).
Existing masks are skipped, so it can be rerun after facades.py fetches new photos.
"""
import json
import os
import sys
import time

import numpy as np
import torch
from PIL import Image
from scipy.ndimage import binary_dilation
from transformers import AutoImageProcessor, UperNetForSemanticSegmentation

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "data/raw/mapillary_facade")
DST = os.path.join(ROOT, "data/raw/mapillary_masks")
MODEL = "openmmlab/upernet-convnext-small"
TRANSIENT = {"person", "bicycle", "minibike", "car", "van", "bus", "truck"}
W = 512


def main():
    os.makedirs(DST, exist_ok=True)
    dev = "mps" if torch.backends.mps.is_available() else "cpu"
    proc = AutoImageProcessor.from_pretrained(MODEL)
    model = UperNetForSemanticSegmentation.from_pretrained(MODEL).to(dev).eval()
    ids = [k for k, v in model.config.id2label.items() if v in TRANSIENT]
    # centre first: photos in the order of their nearest facade piece to Great St Mary's (written by facades.py)
    order = os.path.join(ROOT, "data/derived/facade_photo_order.json")
    rank = {k: n for n, k in enumerate(json.load(open(order)))} if os.path.exists(order) else {}
    todo = sorted((f for f in os.listdir(SRC) if f.endswith(".jpg")
                   and not os.path.exists(os.path.join(DST, f[:-4] + ".png"))), key=lambda f: (rank.get(f[:-4], 1e9), f))
    t0, frac = time.time(), []
    for n, f in enumerate(todo):
        im = Image.open(os.path.join(SRC, f)).convert("RGB")
        h = round(im.height * W / im.width)
        # 576 x 384 input: feature maps 18 x 12, divisible by the pyramid pool sizes (MPS needs that)
        small = im.resize((576, 384), Image.BILINEAR)
        x = proc(images=small, do_resize=False, return_tensors="pt")["pixel_values"].to(dev)
        with torch.no_grad():
            lg = model(pixel_values=x).logits
        lab = torch.nn.functional.interpolate(lg, size=(h, W), mode="bilinear").argmax(1)[0].cpu().numpy()
        m = binary_dilation(np.isin(lab, ids), iterations=4)
        frac.append(m.mean())
        Image.fromarray((m * 255).astype(np.uint8)).save(os.path.join(DST, f[:-4] + ".png"))
        if n % 100 == 0:
            print("[masks] %d/%d %.0fs" % (n, len(todo), time.time() - t0), flush=True)
    if frac:
        print("[masks] %d photos, mean masked share %.1f%%, %.0fs" % (len(frac), 100 * np.mean(frac), time.time() - t0))


if __name__ == "__main__":
    sys.exit(main())
