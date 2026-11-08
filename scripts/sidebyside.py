"""Side-by-side for the journal: photo | A | B rows for the views that changed most between two A/B runs.
  python -I scripts/sidebyside.py <label_a> <label_b> <out.jpg> [rows=3]
Reads /tmp/wc_ab_<label>.json and /tmp/wc_ab_<label>/<id>.png (scripts/abring.sh)."""
import json, sys
from PIL import Image

a, b, out = sys.argv[1:4]
rows = int(sys.argv[4]) if len(sys.argv) > 4 else 3
pa = json.load(open('/tmp/wc_ab_%s.json' % a))['per_view']
pb = json.load(open('/tmp/wc_ab_%s.json' % b))['per_view']
d = sorted([k for k in pa if k in pb], key=lambda k: pb[k] - pa[k])
ids = d[::-1][:rows - 1] + d[:1]   # biggest gains, then the biggest loss
W, H = 480, 360
sheet = Image.new('RGB', (3 * W, rows * H))
for r, k in enumerate(ids):
    for c, p in enumerate(('data/benchmark/photos/%s.jpg' % k, '/tmp/wc_ab_%s/%s.png' % (a, k), '/tmp/wc_ab_%s/%s.png' % (b, k))):
        sheet.paste(Image.open(p).convert('RGB').resize((W, H)), (c * W, r * H))
    print(k, pa[k], '->', pb[k])
sheet.save(out, quality=85)
