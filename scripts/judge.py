"""judged_realism and visual_quality: Claude vision judge over the benchmark renders of one build.

    .venv/bin/python -I scripts/judge.py <build_hash> <renders_dir> [--jobs 6] [--only realism|quality]

judged_realism: the fixed 50 views in data/benchmark/judge_views.json (every 4th benchmark view by distance from
Great St Mary's, frozen with the benchmark). For each, the real photo and the render are put side by side as
"A" and "B" in an order drawn from hash(build, id), and the judge is not told that one is a render. It scores
0-10 how closely the two match in geometry, materials, colours, vegetation, street details and lighting.
KPI = mean x 10. Cached in data/benchmark/scores/<hash>_judge.json.

visual_quality: the fixed 30 views in data/benchmark/quality_views.json (the 30 benchmark views nearest Great St
Mary's, centre outwards). Each render is judged on its own against the fixed rubric below (no reference image).
KPI = mean over views of the mean rubric score x 10. Cached in data/benchmark/scores/<hash>_quality.json.

The judge is the local `claude` CLI (claude -p, Read tool only), model JUDGE_MODEL.
"""
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
B = os.path.join(ROOT, "data/benchmark")
JUDGE_MODEL = "claude-opus-5-5"
CLAUDE = os.path.expanduser("~/.local/bin/claude")
ENV = dict(os.environ)
_tok = os.path.expanduser("~/.config/aistack-agent/claude-token")   # this agent's own Claude login
if os.path.exists(_tok) and "CLAUDE_CODE_OAUTH_TOKEN" not in ENV:
    ENV["CLAUDE_CODE_OAUTH_TOKEN"] = open(_tok).read().strip()
RUBRIC = ["lighting_shadows", "gi_ao", "materials_wear", "geometric_detail", "vegetation", "atmosphere",
          "image_quality", "no_artefacts"]

REALISM_PROMPT = """You are a strict visual judge. Read the image file {path} . It shows two pictures side by side,
labelled A (left) and B (right). They are supposed to show the same place from the same position and viewing
direction. Score from 0 to 10 how closely they match each other, considering: geometry (buildings, street layout,
skyline), materials, colours, vegetation, street details (signs, furniture, vehicles, people) and lighting.
0 = nothing in common, 5 = clearly the same kind of scene with the main shapes matching, 10 = indistinguishable.
Reply with only a JSON object: {{"score": <0-10 number>, "reason": "<one short sentence>"}}"""

QUALITY_PROMPT = """You are a strict judge of real-time 3D rendering quality. Read the image file {path} . It is a
screenshot from a 3D game engine. Score it 0-10 on each criterion, where 10 = the visual quality of a current
AAA console/PC game and 0 = no attempt. Judge this image on its own merits only.
- lighting_shadows: direct lighting and shadow quality
- gi_ao: global illumination, bounce light, ambient occlusion
- materials_wear: material detail, texture resolution, surface wear
- geometric_detail: window recesses, mouldings, cornices, kerbs, small geometry
- vegetation: density and quality of trees, grass, hedges
- atmosphere: sky, haze, volumetric light
- image_quality: anti-aliasing, sharpness, no visible pop-in or shimmer
- no_artefacts: absence of glitches, holes, z-fighting, stretched or missing geometry (10 = none)
Reply with only a JSON object with exactly these keys and number values: {keys}"""


def ask(prompt, cwd):
    for _ in range(3):
        r = subprocess.run([CLAUDE, "-p", prompt, "--model", JUDGE_MODEL, "--allowedTools", "Read",
                            "--output-format", "text"], capture_output=True, text=True, timeout=600, cwd=cwd, env=ENV)
        m = re.search(r"\{.*\}", r.stdout, re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass
    return None


def side_by_side(photo, render, swap, out):
    a, b = Image.open(photo).convert("RGB"), Image.open(render).convert("RGB")
    h = 640
    a, b = [im.resize((round(im.width * h / im.height), h), Image.LANCZOS) for im in (a, b)]
    if swap:
        a, b = b, a
    pad = 40
    c = Image.new("RGB", (a.width + b.width + 3 * 16, h + pad + 16), "white")
    c.paste(a, (16, pad)); c.paste(b, (a.width + 32, pad))
    d = ImageDraw.Draw(c)
    try:
        f = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 28)
    except OSError:
        f = ImageFont.load_default()
    d.text((16 + a.width // 2 - 8, 4), "A", fill="black", font=f)
    d.text((a.width + 32 + b.width // 2 - 8, 4), "B", fill="black", font=f)
    c.save(out, quality=90)


def realism(h, renders, jobs, tmp):
    views = json.load(open(os.path.join(B, "judge_views.json")))
    def one(vid):
        r = os.path.join(renders, f"{vid}.png")
        if not os.path.exists(r):
            return vid, None
        swap = int(hashlib.sha256(f"{h}:{vid}".encode()).hexdigest(), 16) % 2 == 1
        p = os.path.join(tmp, f"pair_{vid}.jpg")
        side_by_side(os.path.join(B, "photos", f"{vid}.jpg"), r, swap, p)
        res = ask(REALISM_PROMPT.format(path=p), tmp)
        return vid, (dict(res, render_side="A" if swap else "B") if res and "score" in res else None)
    with ThreadPoolExecutor(jobs) as ex:
        per = dict(ex.map(one, views))
    ok = {k: v for k, v in per.items() if v}
    mean = sum(float(v["score"]) for v in ok.values()) / max(1, len(ok))
    out = {"judged_realism": round(mean * 10, 2), "n": len(ok), "model": JUDGE_MODEL, "per_view": per}
    json.dump(out, open(os.path.join(B, "scores", f"{h}_judge.json"), "w"), indent=1)
    return {"judged_realism": out["judged_realism"], "n": len(ok)}


MARKET_PROMPT = """You are a strict visual judge. Read the image file {path} . It shows two pictures side by side,
labelled A (left) and B (right), supposed to show the same place (Cambridge Market Square area) from the same
position and viewing direction. Score from 0 to 10 how well the two show the same 3D scene, considering: building
shapes and proportions, window and door layout, mouldings and depth, rooflines, materials and colours, market
stalls, street furniture and lighting. 0 = nothing in common, 5 = clearly the same place with the main shapes
matching, 10 = indistinguishable.
Reply with only a JSON object: {{"score": <0-10 number>, "reason": "<one short sentence>"}}"""


def market(h, renders, jobs, tmp):
    """market_square_realism: the 40 frozen Market Square photos (market_square.json), blind A/B like realism()."""
    views = [v["id"] for v in json.load(open(os.path.join(B, "market_square.json")))]
    def one(vid):
        r = os.path.join(renders, f"{vid}.png")
        if not os.path.exists(r):
            return vid, None
        swap = int(hashlib.sha256(f"{h}:ms:{vid}".encode()).hexdigest(), 16) % 2 == 1
        p = os.path.join(tmp, f"ms_{vid}.jpg")
        side_by_side(os.path.join(B, "photos_ms", f"{vid}.jpg"), r, swap, p)
        res = ask(MARKET_PROMPT.format(path=p), tmp)
        return vid, (dict(res, render_side="A" if swap else "B") if res and "score" in res else None)
    with ThreadPoolExecutor(jobs) as ex:
        per = dict(ex.map(one, views))
    ok = {k: v for k, v in per.items() if v}
    mean = sum(float(v["score"]) for v in ok.values()) / max(1, len(ok))
    out = {"market_square_realism": round(mean * 10, 2), "n": len(ok), "model": JUDGE_MODEL, "per_view": per}
    json.dump(out, open(os.path.join(B, "scores", f"{h}_msjudge.json"), "w"), indent=1)
    return {"market_square_realism": out["market_square_realism"], "n": len(ok)}


def quality(h, renders, jobs, tmp):
    views = json.load(open(os.path.join(B, "quality_views.json")))
    keys = json.dumps({k: 0 for k in RUBRIC})
    def one(vid):
        r = os.path.join(renders, f"{vid}.png")
        if not os.path.exists(r):
            return vid, None
        p = os.path.join(tmp, f"shot_{vid}.png")
        Image.open(r).save(p)
        res = ask(QUALITY_PROMPT.format(path=p, keys=keys), tmp)
        if not res or not all(k in res for k in RUBRIC):
            return vid, None
        return vid, {k: float(res[k]) for k in RUBRIC}
    with ThreadPoolExecutor(jobs) as ex:
        per = dict(ex.map(one, views))
    ok = [v for v in per.values() if v]
    mean = sum(sum(v.values()) / len(RUBRIC) for v in ok) / max(1, len(ok))
    by = {k: round(sum(v[k] for v in ok) / max(1, len(ok)), 2) for k in RUBRIC}
    out = {"visual_quality": round(mean * 10, 2), "n": len(ok), "model": JUDGE_MODEL, "by_criterion": by, "per_view": per}
    json.dump(out, open(os.path.join(B, "scores", f"{h}_quality.json"), "w"), indent=1)
    return {"visual_quality": out["visual_quality"], "n": len(ok), "by_criterion": by}


def freeze_views():
    bench = json.load(open(os.path.join(B, "benchmark.json")))   # sorted by distance from GSM
    for name, ids in (("judge_views.json", [v["id"] for v in bench[::4]][:50]),
                      ("quality_views.json", [v["id"] for v in bench[:30]])):
        p = os.path.join(B, name)
        if not os.path.exists(p):
            json.dump(ids, open(p, "w"))


def main():
    a = sys.argv[1:]
    h, renders = a[0], a[1]
    jobs = int(a[a.index("--jobs") + 1]) if "--jobs" in a else 6
    only = a[a.index("--only") + 1] if "--only" in a else None
    freeze_views()
    os.makedirs(os.path.join(B, "scores"), exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        if only in (None, "realism"):
            print(json.dumps(realism(h, renders, jobs, tmp)))
        if only == "market":
            print(json.dumps(market(h, renders, jobs, tmp)))
        if only in (None, "quality"):
            print(json.dumps(quality(h, renders, jobs, tmp)))


if __name__ == "__main__":
    main()
