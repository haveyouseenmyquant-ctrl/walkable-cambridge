// Real photo facades (scripts/facades.py): per tile, float32 quads of 4 corners [x, y, z, u, v] in the collision
// frame (x east, y north, z up) and one RGBA WebP atlas (sky transparent) of wall pieces rectified from non-held-out Mapillary photos.
// Unlit: the photos already carry real light and shade. Drawn 4 cm proud of the wall.
import * as THREE from 'three';

export function makeFacades(buf, tex) {
  const a = new Float32Array(buf), nq = a.length / 20 | 0;
  const pos = new Float32Array(nq * 12), uv = new Float32Array(nq * 8), idx = new Uint32Array(nq * 6);
  for (let q = 0; q < nq; q++) {
    for (let k = 0; k < 4; k++) {
      const r = a.subarray(q * 20 + k * 5, q * 20 + k * 5 + 5);
      pos.set([r[0], r[2], -r[1]], (q * 4 + k) * 3); uv.set([r[3], r[4]], (q * 4 + k) * 2);
    }
    const o = q * 4; idx.set([o, o + 1, o + 2, o, o + 2, o + 3], q * 6);
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  g.setAttribute('uv', new THREE.BufferAttribute(uv, 2));
  g.setIndex(new THREE.BufferAttribute(idx, 1));
  g.computeBoundingSphere(); g.computeVertexNormals();   // normals only for the ?post=ao normal pass
  tex.colorSpace = THREE.SRGBColorSpace; tex.anisotropy = 8; tex.flipY = true;
  const m = new THREE.MeshBasicMaterial({ map: tex, alphaTest: 0.5, polygonOffset: true, polygonOffsetFactor: -1, polygonOffsetUnits: -2 });
  const mesh = new THREE.Mesh(g, m);
  mesh.userData.ownMat = true; mesh.name = 'facades';
  return mesh;
}
