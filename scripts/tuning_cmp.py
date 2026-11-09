import sys, os, json, numpy as np
from PIL import Image
V = json.load(open('data/benchmark/tuning/views.json')); P = 'data/benchmark/tuning/photos'
def load(f, size=(256, 192)):
    return np.asarray(Image.open(f).convert('RGB').resize(size), dtype=np.float32) / 255
def L(im): return im @ np.array([0.2126, 0.7152, 0.0722], np.float32)
for lab in sys.argv[1:]:
    R = f'/tmp/wc_exp/r_{lab}'; dm, w1, ph, rd, dmid = [], [], [], [], []
    for v in V:
        rf = os.path.join(R, v['id'] + '.png'); pf = os.path.join(P, v['id'] + '.jpg')
        if not os.path.exists(rf): continue
        p, r = load(pf), load(rf)
        # below-horizon half (buildings + ground), skip sky which differs by weather
        lp, lr = L(p[96:]), L(r[96:])
        dm.append(lr.mean() - lp.mean()); rd.append(lr.mean()); ph.append(lp.mean())
        q = np.linspace(2, 98, 25); w1.append(np.abs(np.percentile(lp, q) - np.percentile(lr, q)).mean())
        # middle band (facades at eye level) mean
        dmid.append(L(r[60:140]).mean() - L(p[60:140]).mean())
    dm = np.array(dm)
    print(f"{lab}: n={len(dm)} render_mean={np.mean(rd):.3f} photo_mean={np.mean(ph):.3f} mean_diff={dm.mean():+.3f} |diff|={np.abs(dm).mean():.3f} median_diff={np.median(dm):+.3f} quantileW1={np.mean(w1):.3f} midband_diff={np.mean(dmid):+.3f}")
