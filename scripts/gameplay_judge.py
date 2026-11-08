"""gameplay_judged: Claude judge over the scripted 60 s combat clips of one build (scripts/gameplay_clip.mjs).

    .venv/bin/python -I scripts/gameplay_judge.py <clips_dir> [-f] [--hash <build_hash>] [--site site]

For each class directory in <clips_dir> (12 frames frame_01..12.jpg + events.json): the frames are tiled into one
4x3 contact sheet (time order, left to right, top to bottom, each labelled with its clip time), the event log is
summarised into the prompt, and the judge scores 0-10 on the fixed rubric below. Class score = mean of the rubric
items; KPI = mean over classes x 10 (1 decimal). Cached in data/benchmark/scores/<hash>_gameplay.json
(hash = scripts/build_hash.py site); skipped if cached unless -f.

The judge is the local `claude` CLI (claude -p, Read tool only), model JUDGE_MODEL (same setup as judge.py).
"""
import json
import os
import re
import subprocess
import sys
import tempfile
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCORES = os.path.join(ROOT, "data/benchmark/scores")
JUDGE_MODEL = "claude-opus-5-5"
CLAUDE = os.path.expanduser("~/.local/bin/claude")
ENV = dict(os.environ)
_tok = os.path.expanduser("~/.config/aistack-agent/claude-token")   # this agent's own Claude login
if os.path.exists(_tok) and "CLAUDE_CODE_OAUTH_TOKEN" not in ENV:
    ENV["CLAUDE_CODE_OAUTH_TOKEN"] = open(_tok).read().strip()
RUBRIC = ["readability_telegraphs", "spell_vfx", "enemy_animation_variety", "hit_feedback", "ui_hud_clarity",
          "loot_excitement", "polished_arpg_feel"]

PROMPT = """You are a strict judge of action-RPG game feel and presentation. Read the image file {path} . It is a
contact sheet of 12 screenshots taken evenly over a 60-second scripted combat clip from a browser action RPG
(the player is a wizard of the "{cls}" class, first-person view, fighting monsters in a town square). Frames run
left to right, top to bottom; each is labelled with its clip time. Below is a summary of the game's event log for
the same clip (sound cannot be shown, so the log reports how many sound voices were triggered).

{log}

Score the clip 0-10 on each criterion, where 10 = a current polished commercial action RPG (Diablo IV, Path of
Exile 2, Hades level) and 0 = no attempt. Judge only what the frames and the log show; do not give credit for
features you cannot see evidence of.
- readability_telegraphs: can you tell what is happening in combat; are enemy attacks telegraphed (wind-ups, ground markers)
- spell_vfx: quality, distinctiveness and impact of the spell visual effects
- enemy_animation_variety: enemy models, animation and variety of enemy types
- hit_feedback: impact on hit: hit flashes, hit-stop, knockback, sound, floating damage numbers, crits
- ui_hud_clarity: clarity and polish of the UI and HUD (health/mana, spell bar, cooldowns, target info)
- loot_excitement: visibility and excitement of loot drops and pickups (beams, rarity colours, toasts)
- polished_arpg_feel: overall, how much this feels like a polished action RPG
Reply with only a JSON object with exactly these keys and number values, plus "overall" (0-10) and "reason"
(two or three short sentences on the biggest strengths and weaknesses): {keys}"""


def ask(prompt, cwd):
    for _ in range(3):
        r = subprocess.run([CLAUDE, "-p", prompt, "--model", JUDGE_MODEL, "--allowedTools", "Read",
                            "--output-format", "text"], capture_output=True, text=True, timeout=900, cwd=cwd, env=ENV)
        m = re.search(r"\{.*\}", r.stdout, re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass
    return None


def contact_sheet(frames, out, cols=4, w=640):
    ims = [Image.open(f).convert("RGB") for f, _ in frames]
    h = round(w * ims[0].height / ims[0].width)
    rows, pad, lab = (len(ims) + cols - 1) // cols, 8, 26
    c = Image.new("RGB", (cols * w + (cols + 1) * pad, rows * (h + lab) + (rows + 1) * pad), "white")
    d = ImageDraw.Draw(c)
    try:
        f = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 20)
    except OSError:
        f = ImageFont.load_default()
    for i, (im, (_, t)) in enumerate(zip(ims, frames)):
        x, y = pad + (i % cols) * (w + pad), pad + (i // cols) * (h + lab + pad)
        d.text((x + 4, y + 2), f"{i + 1}   t = {t:.1f} s", fill="black", font=f)
        c.paste(im.resize((w, h), Image.LANCZOS), (x, y + lab))
    c.save(out, quality=88)


def summarise(ev):
    """Event log -> a compact text summary for the prompt (counts, damage, timeline)."""
    E = ev["events"]
    by = lambda k: [e for e in E if e["ev"] == k]
    casts, hits, kills, ph = by("cast"), by("hit"), by("kill"), by("playerHit")
    frames = ev.get("frames", [])
    lines = [f"Clip length {ev.get('clip_s', 60)} s, class {ev['cls']}."]
    lines.append(f"Casts: {len(casts)} ({', '.join(f'{k} x{v}' for k, v in Counter(e['spell'] for e in casts).most_common())}).")
    if hits:
        crit = sum(1 for e in hits if e.get("crit"))
        dmg = sum(e.get("amount", 0) for e in hits)
        tgt = Counter((e["target"] or {}).get("type", "?") if isinstance(e["target"], dict) else str(e["target"]) for e in hits)
        lines.append(f"Hits on enemies: {len(hits)}, total damage {dmg}, {crit} crits, max hit {max(e.get('amount', 0) for e in hits)}; "
                     f"targets: {', '.join(f'{k} x{v}' for k, v in tgt.most_common())}.")
    else:
        lines.append("Hits on enemies: 0.")
    lines.append(f"Kills: {len(kills)} ({', '.join(f'{k} x{v}' for k, v in Counter((e['mob'] or {}).get('type', '?') for e in kills).most_common())}).")
    lines.append(f"Player hit {len(ph)} times for {sum(e.get('amount', 0) for e in ph)} damage "
                 f"(by {', '.join(f'{k} x{v}' for k, v in Counter(e.get('by') for e in ph).most_common())}); deaths: {len(by('playerDeath'))}.")
    drops, picks = by("drop"), by("pickup")
    drop_s = ", ".join(f"{e.get('item')} [{e.get('rarity')}]" for e in drops) or "none"
    lines.append(f"Loot drops: {len(drops)} ({drop_s}); "
                 f"picked up: {len(picks)}; level-ups: {len(by('levelup'))}; boss phase changes: {len(by('bossPhase'))}.")
    if frames:
        lines.append(f"Sound voices triggered over the clip: {frames[-1].get('sfxVoices', 0)}.")
        lines.append("Per frame (time: player hp, mana, enemies within 30 m [type:state], floating damage numbers on screen):")
        for i, f in enumerate(frames):
            lines.append(f"  {i + 1}. t={f['t']}s hp {f['hp']}/{f['maxHp']} mana {f['mana']} enemies {', '.join(f['liveMobs']) or 'none'}; dmg numbers {f.get('hudNums', 0)}")
    tl = [e for e in E if e["ev"] in ("kill", "drop", "pickup", "levelup", "bossPhase", "playerDeath")][:30]
    if tl:
        lines.append("Key events: " + "; ".join(f"{e['t']}s {e['ev']}" + (f" {e['mob'].get('type')}" if e["ev"] == "kill" and isinstance(e.get("mob"), dict) else "")
                                                + (f" {e.get('item')}" if e["ev"] in ("drop", "pickup") else "") for e in tl) + ".")
    if ev.get("page_errors"):
        lines.append(f"Page errors: {len(ev['page_errors'])}.")
    return "\n".join(lines)


def judge_class(clips, cls, tmp):
    d = os.path.join(clips, cls)
    ev = json.load(open(os.path.join(d, "events.json")))
    frames = [(os.path.join(d, f["file"]), f["t"]) for f in ev["frames"] if os.path.exists(os.path.join(d, f["file"]))]
    if len(frames) < 12:
        return cls, None
    sheet = os.path.join(tmp, f"sheet_{cls}.jpg")
    contact_sheet(frames, sheet)
    keys = json.dumps({**{k: 0 for k in RUBRIC}, "overall": 0, "reason": ""})
    res = ask(PROMPT.format(path=sheet, cls=cls, log=summarise(ev), keys=keys), tmp)
    if not res or not all(k in res for k in RUBRIC):
        return cls, None
    sc = {k: float(res[k]) for k in RUBRIC}
    return cls, {"score": round(sum(sc.values()) / len(RUBRIC), 2), **sc, "overall": res.get("overall"), "reason": res.get("reason", "")}


def main():
    a = sys.argv[1:]
    clips = a[0]
    site = a[a.index("--site") + 1] if "--site" in a else os.path.join(ROOT, "site")
    h = a[a.index("--hash") + 1] if "--hash" in a else subprocess.run(
        [sys.executable, "-I", os.path.join(ROOT, "scripts/build_hash.py"), site], capture_output=True, text=True, check=True).stdout.strip()
    out = os.path.join(SCORES, f"{h}_gameplay.json")
    if os.path.exists(out) and os.path.getsize(out) and "-f" not in a:
        print(open(out).read().strip())
        return
    classes = sorted(c for c in os.listdir(clips) if os.path.exists(os.path.join(clips, c, "events.json")))
    with tempfile.TemporaryDirectory() as tmp, ThreadPoolExecutor(max(1, len(classes))) as ex:
        per = dict(ex.map(lambda c: judge_class(clips, c, tmp), classes))
    ok = {k: v for k, v in per.items() if v}
    if not ok:
        print(json.dumps({"error": "no class judged", "classes": list(per)}))
        sys.exit(1)
    kpi = round(sum(v["score"] for v in ok.values()) / len(ok) * 10, 1)
    res = {"gameplay_judged": kpi, "n": len(ok), "model": JUDGE_MODEL, "hash": h,
           "classes": {k: {kk: vv for kk, vv in v.items() if kk != "reason"} if v else None for k, v in per.items()},
           "by_criterion": {k: round(sum(v[k] for v in ok.values()) / len(ok), 2) for k in RUBRIC},
           "reasons": {k: v["reason"] for k, v in ok.items()}}
    os.makedirs(SCORES, exist_ok=True)
    json.dump(res, open(out, "w"), indent=1)
    print(json.dumps({"gameplay_judged": kpi, "n": len(ok)}))


if __name__ == "__main__":
    main()
