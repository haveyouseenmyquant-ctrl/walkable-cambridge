// Trees (scripts/trees.py): per tile, float32 records [x, y, z_ground, height, crown_r, seed] in the collision frame.
// Drawn as two InstancedMeshes per tile: trunks and lumpy crowns (a cluster of blobs, normals pointing out of the
// crown so the foliage shades softly; darker underneath as cheap ambient occlusion).
// Session 18: the crown is a darker, slightly smaller blob core wrapped in alpha-tested leaf cards (a procedural
// leaf-cluster texture drawn once on a canvas), so the silhouette breaks up into leaves. ?foliage=0: blobs only.
import * as THREE from 'three';

const FOLIAGE = new URLSearchParams(location.search).get('foliage') !== '0';

function leafTexture() {
  const S = 256, cv = document.createElement('canvas'); cv.width = cv.height = S;
  const g = cv.getContext('2d'), rnd = mulberry(5);
  for (let i = 0; i < 1400; i++) {
    // denser towards the middle of the card so the card edges don't show
    const a = rnd() * Math.PI * 2, r = Math.sqrt(rnd()) * S * 0.47;
    if (rnd() > 1.15 - r / (S * 0.47)) continue;
    const x = S / 2 + Math.cos(a) * r, y = S / 2 + Math.sin(a) * r, l = 5 + rnd() * 6;
    const lum = 0.55 + 0.45 * rnd() * (1 - 0.4 * y / S);   // lighter leaves towards the top of the card
    g.fillStyle = `rgb(${(95 + 60 * rnd()) * lum | 0},${(140 + 50 * rnd()) * lum | 0},${(60 + 30 * rnd()) * lum | 0})`;
    g.beginPath(); g.ellipse(x, y, l, l * 0.45, rnd() * Math.PI, 0, Math.PI * 2); g.fill();
  }
  const t = new THREE.CanvasTexture(cv);
  t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 4;
  return t;
}

function cardGeometry(n) {
  const rnd = mulberry(23), pos = [], nor = [], col = [], uv = [], idx = [];
  const v = new THREE.Vector3(), q = new THREE.Quaternion(), e = new THREE.Euler();
  for (let i = 0; i < n; i++) {
    // card centres near the crown surface (unit sphere), random orientation
    v.set(rnd() * 2 - 1, rnd() * 2 - 1, rnd() * 2 - 1); if (v.lengthSq() > 1 || v.lengthSq() < 1e-3) { i--; continue; }
    v.normalize().multiplyScalar(0.62 + 0.4 * rnd());
    const c = v.clone(), sz = 0.42 + 0.2 * rnd();
    q.setFromEuler(e.set(rnd() * 6.28, rnd() * 6.28, rnd() * 6.28));
    const b = pos.length / 3;
    for (const [du, dv] of [[-1, -1], [1, -1], [1, 1], [-1, 1]]) {
      const p = new THREE.Vector3(du * sz, dv * sz, 0).applyQuaternion(q).add(c);
      pos.push(p.x, p.y, p.z);
      const nn = new THREE.Vector3(p.x, p.y * 0.8 + 0.25, p.z).normalize(); nor.push(nn.x, nn.y, nn.z);
      const ao = 0.6 + 0.5 * Math.min(1, Math.max(0, (p.y + 0.9) / 1.7)); col.push(ao, ao, ao);
      uv.push((du + 1) / 2, (dv + 1) / 2);
    }
    idx.push(b, b + 1, b + 2, b, b + 2, b + 3);
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  g.setAttribute('normal', new THREE.Float32BufferAttribute(nor, 3));
  g.setAttribute('color', new THREE.Float32BufferAttribute(col, 3));
  g.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2));
  g.setIndex(idx);
  return g;
}

function crownGeometry(lumps, detail) {
  const parts = [], rnd = mulberry(11);
  for (let i = 0; i < lumps; i++) {
    const a = i / lumps * Math.PI * 2 + rnd() * 0.6, up = i === 0 ? 0.45 : (rnd() - 0.4) * 0.6;
    const d = i === 0 ? 0 : 0.42 + rnd() * 0.12, s = i === 0 ? 0.62 : 0.48 + rnd() * 0.12;
    const g = new THREE.IcosahedronGeometry(s, detail);
    g.translate(Math.cos(a) * d, up, Math.sin(a) * d);
    parts.push(g);
  }
  const pos = [], nor = [], col = [];
  for (const g of parts) {
    const p = g.attributes.position;
    for (let i = 0; i < p.count; i++) {
      let x = p.getX(i), y = p.getY(i), z = p.getZ(i);
      const j = 1 + 0.1 * Math.sin(x * 9.1 + y * 7.3) * Math.cos(z * 8.7 - y * 5.1);   // leafy jitter
      x *= j; y *= j; z *= j;
      pos.push(x, y, z);
      const n = new THREE.Vector3(x, y * 0.8 + 0.25, z).normalize();
      nor.push(n.x, n.y, n.z);
      const ao = 0.55 + 0.45 * Math.min(1, Math.max(0, (y + 0.9) / 1.6));
      col.push(ao, ao, ao);
    }
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  g.setAttribute('normal', new THREE.Float32BufferAttribute(nor, 3));
  g.setAttribute('color', new THREE.Float32BufferAttribute(col, 3));
  return g;
}

function mulberry(a) {
  return () => { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; };
}

const CROWN = crownGeometry(7, 1);
const TRUNK = new THREE.CylinderGeometry(0.7, 1, 1, 6, 1, true).translate(0, 0.5, 0);
const crownMat = new THREE.MeshLambertMaterial({ vertexColors: true });
const trunkMat = new THREE.MeshLambertMaterial({ color: 0x5a4a3c });
const CARDS = FOLIAGE ? cardGeometry(56) : null;
const cardMat = FOLIAGE ? new THREE.MeshLambertMaterial({ map: leafTexture(), vertexColors: true, alphaTest: 0.5,
  side: THREE.DoubleSide, alphaToCoverage: true }) : null;
const GREENS = [0x4d6b32, 0x5b7a38, 0x3f5d2c, 0x667f3e, 0x56703a, 0x48663a].map(c => new THREE.Color(c));

export function makeTrees(buf) {
  const a = new Float32Array(buf), n = a.length / 6 | 0;
  const crowns = new THREE.InstancedMesh(CROWN, crownMat, n), trunks = new THREE.InstancedMesh(TRUNK, trunkMat, n);
  const cards = FOLIAGE ? new THREE.InstancedMesh(CARDS, cardMat, n) : null;
  const m = new THREE.Matrix4(), q = new THREE.Quaternion(), s = new THREE.Vector3(), p = new THREE.Vector3(), Y = new THREE.Vector3(0, 1, 0);
  const c = new THREE.Color();
  for (let i = 0; i < n; i++) {
    const [x, y, zg, h, r, seed] = a.subarray(i * 6, i * 6 + 6);
    const base = h * (0.22 + 0.12 * seed), cv = (h - base) / 2;   // crown from base to the top
    q.setFromAxisAngle(Y, seed * 6.283);
    p.set(x, zg + base + cv, -y); s.set(r, cv * 1.05, r * (0.9 + 0.2 * seed));
    c.copy(GREENS[(seed * 997 | 0) % GREENS.length]).multiplyScalar(0.85 + 0.3 * ((seed * 131) % 1));
    if (cards) {
      cards.setMatrixAt(i, m.compose(p, q, s)); cards.setColorAt(i, c);   // texture is green: tint stays near white
      cards.instanceColor.setXYZ(i, 0.75 + 0.5 * c.r / (c.g || 1), 0.95 + 0.1 * seed, 0.8 + 0.4 * c.b / (c.g || 1));
      s.multiplyScalar(0.84); c.multiplyScalar(0.72);
    }
    crowns.setMatrixAt(i, m.compose(p, q, s));
    crowns.setColorAt(i, c);
    const tr = 0.12 + h * 0.012;
    p.set(x, zg - 0.2, -y); s.set(tr, base + cv, tr);
    trunks.setMatrixAt(i, m.compose(p, q, s));
  }
  const g = new THREE.Group(); g.name = 'trees';
  for (const o of cards ? [crowns, cards, trunks] : [crowns, trunks]) {
    o.castShadow = true; o.receiveShadow = true; o.computeBoundingSphere(); o.userData.ownMat = false;
    o.matrixAutoUpdate = false; g.add(o);
  }
  return g;
}
