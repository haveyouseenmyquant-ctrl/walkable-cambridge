import json, math, os, sys, urllib.request, numpy as np
sys.path.insert(0, 'scripts')
from make_benchmark import pose, ROOT
from pyproj import Proj, Transformer
tf = Transformer.from_crs(4326, 27700, always_xy=True); bng = Proj("EPSG:27700")
held = set(); near = []
for f in ('data/benchmark/heldout.json', 'data/benchmark/heldout_ms.json'):
    h = json.load(open(f)); held |= set(map(str, h['images'])); near += h['sequence_near']
man = json.load(open('site/manifest.json'))['origin']; g = tf.transform(0.1183, 52.2052)
tok = open('data/mapillary_token').read().strip()
cand = []
for im in json.load(open('data/raw/mapillary_list.json')):
    if str(im['id']) in held or im.get('is_pano') or im.get('camera_type') not in (None, 'perspective') or not im.get('computed_geometry'): continue
    lo, la = im['computed_geometry']['coordinates']; e, n = tf.transform(lo, la)
    d = math.hypot(e - g[0], n - g[1])
    if d > 200: continue
    if any(s == im.get('sequence') and math.hypot(e - se, n - sn) < max(r, 30) for s, se, sn, r in near): continue
    hd, pt = pose(im); conv = bng.get_factors(lo, la).meridian_convergence
    w, h = im.get('width') or 4, im.get('height') or 3; f = (im.get('camera_parameters') or [None])[0]
    hfov = math.degrees(2 * math.atan(w / (2 * f * max(w, h)))) if f else 70.0
    if not (40 <= hfov <= 100) or abs(pt) > 15 or not im.get('computed_rotation'): continue
    cand.append(dict(id=str(im['id']), x=round(e - man['e0'], 2), y=round(n - man['n0'], 2), e=e, n=n, heading=round((hd - conv) % 360, 2), pitch=round(pt, 2), hfov=round(hfov, 2), w=w, h=h, seq=im.get('sequence'), dist_gsm_m=round(d, 1)))
print('cand', len(cand))
# farthest-point pick 30, one per seq-50m
P = np.array([[c['e'], c['n']] for c in cand]); ch = [int(np.argmin(((P - g) ** 2).sum(1)))]
dm = np.sqrt(((P - P[ch[0]]) ** 2).sum(1))
while len(ch) < 30:
    i = int(np.argmax(dm)); ch.append(i); dm = np.minimum(dm, np.sqrt(((P - P[i]) ** 2).sum(1)))
os.makedirs('data/benchmark/tuning/photos', exist_ok=True); out = []
for i in ch:
    c = cand[i]
    try:
        u = json.load(urllib.request.urlopen(f"https://graph.mapillary.com/{c['id']}?fields=thumb_1024_url&access_token={tok}", timeout=20))['thumb_1024_url']
        open(f"data/benchmark/tuning/photos/{c['id']}.jpg", 'wb').write(urllib.request.urlopen(u, timeout=30).read())
        out.append(c)
    except Exception as ex: print('skip', c['id'], ex)
json.dump(out, open('data/benchmark/tuning/views.json', 'w'))
print('views', len(out))
