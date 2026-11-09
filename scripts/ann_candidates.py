"""Photo candidates for ring-1 facade annotation (session 54).

For a wall id from data/annotations/ring1/walls.json, list non-held-out Mapillary frames (data/raw/mapillary_list.json)
within 45 m whose compass angle faces the wall midpoint and whose sight line crosses no other footprint wall.
It excludes ids in data/benchmark/*.json and frames of a held-out sequence within 20 m of a held-out frame.
Score = 1.5*|cos(view, wall)| + d/45 + angle_off/60 (lower is better: frontal, close, centred).
Mapillary poses are often off by several metres, so check every photo by eye before using it.

Usage:
  .venv/bin/python -I scripts/ann_candidates.py way/123:4 way/567:0     # top 3 candidates, downloaded to /tmp/ann_cand/
  .venv/bin/python -I scripts/ann_candidates.py rank data/derived/s53/worklist_west.json   # unannotated walls with a good photo
"""
import glob, json, sys, math, os, urllib.request
from pyproj import Transformer
R=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))+'/'
tr=Transformer.from_crs(4326,27700,always_xy=True)
held=set(); seqpos=[]
for f in ['benchmark.json','heldout_ms.json','heldout.json','judge_views.json','market_square.json']:
    d=json.load(open(R+'data/benchmark/'+f))
    if isinstance(d,dict): d=d.get('views') or d.get('photos') or list(d.values())
    for v in d:
        if isinstance(v,dict) and 'id' in v:
            held.add(str(v['id']))
            if 'seq' in v and 'x' in v: seqpos.append((v['seq'],v['x'],v['y']))
M=json.load(open(R+'data/raw/mapillary_list.json'))
WL=json.load(open(R+'data/annotations/ring1/walls.json'))['walls']
walls={w['id']:w for w in WL}
import numpy as np
SEG=np.array([w['p0']+w['p1'] for w in WL]); SID=[w['id'] for w in WL]
def occluded(x,y,mx,my,wid):
    # shorten the ray 1 m before the wall
    d=math.hypot(mx-x,my-y); ex,ey=x+(mx-x)*(d-1)/d, y+(my-y)*(d-1)/d
    ax,ay,bx,by=SEG[:,0],SEG[:,1],SEG[:,2],SEG[:,3]
    def cr(px,py,qx,qy,rx,ry): return (qx-px)*(ry-py)-(qy-py)*(rx-px)
    d1=cr(x,y,ex,ey,ax,ay); d2=cr(x,y,ex,ey,bx,by); d3=cr(ax,ay,bx,by,x,y); d4=cr(ax,ay,bx,by,ex,ey)
    hit=(d1*d2<0)&(d3*d4<0)
    return int(hit.sum())
tok=open(R+'data/mapillary_token').read().strip()
def cands(wid,maxd=45,n=6):
    w=walls[wid]; (x0,y0),(x1,y1)=w['p0'],w['p1']; mx,my=(x0+x1)/2,(y0+y1)/2
    L=math.hypot(x1-x0,y1-y0); tx,ty=(x1-x0)/L,(y1-y0)/L
    out=[]
    for m in M:
        if str(m['id']) in held or m.get('is_pano'): continue
        lon,lat=m['computed_geometry']['coordinates']; e,nn=tr.transform(lon,lat); x,y=e-545000,nn-258400
        if any(s==m.get('sequence') and math.hypot(x-sx,y-sy)<20 for s,sx,sy in seqpos): continue
        d=math.hypot(x-mx,y-my)
        if d>maxd or d<4: continue
        brg=math.degrees(math.atan2(mx-x,my-y))%360; a=m['computed_compass_angle']
        off=abs((a-brg+180)%360-180)
        if off>35: continue
        # perpendicular-ness: angle between view ray and wall normal
        rx,ry=(mx-x)/d,(my-y)/d; perp=abs(rx*tx+ry*ty)
        if occluded(x,y,mx,my,wid): continue
        out.append((perp*1.5+d/45+off/60,m['id'],round(d),round(off),round(perp,2),m.get('captured_at')))
    out.sort(); return w,out[:n]
def fetch(i):
    os.makedirs('/tmp/ann_cand',exist_ok=True); p=f'/tmp/ann_cand/{i}.jpg'
    if os.path.exists(p): return p
    u=json.load(urllib.request.urlopen(f'https://graph.mapillary.com/{i}?fields=thumb_1024_url&access_token={tok}',timeout=20))['thumb_1024_url']
    open(p,'wb').write(urllib.request.urlopen(u,timeout=30).read()); return p
def rank(worklist):
    """Unannotated walls of a worklist that have at least one good facing photo, best first."""
    have=set()
    for f in glob.glob(R+'data/annotations/ring1/*.json'):
        if f.endswith('walls.json'): continue
        for w in json.load(open(f)).get('walls',[]): have.add(w['id'])
    d=json.load(open(worklist))
    rows=[]
    for w in d:
        if w['id'] in have: continue
        ww,c=cands(w['id'],maxd=40,n=3)
        good=[k for k in c if k[4]<0.45 and k[2]<35]
        if good: rows.append((good[0][0],w['id'],w['name'],w['street'],w['length'],[k[1] for k in good[:2]]))
    rows.sort()
    for r in rows: print(r)

if __name__=='__main__':
    if sys.argv[1]=='rank': rank(sys.argv[2]); sys.exit()
    for wid in sys.argv[1:]:
        w,c=cands(wid)
        print(wid,w['tags'].get('name'),'len',w['length'],'h',w['height'],'eave',w['eave_z'],'p0',w['p0'],'p1',w['p1'])
        for k in c[:3]:
            try: print('  ',k, fetch(k[1]))
            except Exception as ex: print('  ',k,'ERR',ex)
