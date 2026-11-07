"""photo_match_score: mean DINOv2 (ViT-S/14) CLS cosine similarity between each benchmark photo and the render
from the same pose, times 100.

    .venv/bin/python -I scripts/photo_score.py <photos_dir> <renders_dir> [--out result.json]

Pairs files by stem (photos/<id>.jpg ~ renders/<id>.png). Model: facebook/dinov2-small (Apache-2.0), run
locally on CPU/MPS. Images are resized (short side 224) and centre-cropped to 224x224, the model's standard eval
transform.
"""
import json
import os
import sys

import torch
from PIL import Image
from transformers import AutoImageProcessor, AutoModel

MODEL = "facebook/dinov2-small"


def main():
    args = sys.argv[1:]
    out = args[args.index("--out") + 1] if "--out" in args else None
    photos, renders = args[0], args[1]
    stems = {os.path.splitext(f)[0]: f for f in os.listdir(photos) if not f.startswith(".")}
    pairs = []
    for f in sorted(os.listdir(renders)):
        s = os.path.splitext(f)[0]
        if s in stems:
            pairs.append((s, os.path.join(photos, stems[s]), os.path.join(renders, f)))
    if not pairs:
        sys.exit("no photo/render pairs")
    dev = "mps" if torch.backends.mps.is_available() else "cpu"
    proc = AutoImageProcessor.from_pretrained(MODEL)
    model = AutoModel.from_pretrained(MODEL).to(dev).eval()

    def embed(paths):
        ims = [Image.open(p).convert("RGB") for p in paths]
        with torch.no_grad():
            x = proc(images=ims, return_tensors="pt")["pixel_values"].to(dev)
            e = model(pixel_values=x).pooler_output
        return torch.nn.functional.normalize(e.float(), dim=-1).cpu()

    per = {}
    for i in range(0, len(pairs), 16):
        b = pairs[i:i + 16]
        a, r = embed([p for _, p, _ in b]), embed([q for _, _, q in b])
        for (s, _, _), c in zip(b, (a * r).sum(-1).tolist()):
            per[s] = round(c * 100, 2)
    res = {"photo_match_score": round(sum(per.values()) / len(per), 2), "n": len(per), "per_view": per}
    if out:
        json.dump(res, open(out, "w"), indent=1)
    print(json.dumps({k: res[k] for k in ("photo_match_score", "n")}))


if __name__ == "__main__":
    main()
