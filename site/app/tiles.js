// Tile streaming: loads GLB + .col for tiles within LOAD_R of the player, unloads beyond UNLOAD_R.
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { MeshoptDecoder } from '../vendor/meshoptimizer/meshopt_decoder.module.js';
import { parseCol, ColTile } from './collision.js';
import { makeTrees } from './trees.js';
import { makeObjects } from './objects.js';
import { makeFacades } from './facades.js';
import { buildingVcolMat, groundVcolMat } from './materials.js';

const DEBUG = /debug/.test(location.search);
const Q = new URLSearchParams(location.search);
// Layers: manifest.layers gives the defaults (scripts/street_objects.py, facades.py), ?trees= / ?objects= / ?facades=0|1 override.
// Trees lowered photo_match on flat shading (session 9) but were neutral once surfaces were textured (session 11).
const LOOK2 = Q.get('look') === 'v2';
const layerOn = (man, k) => Q.has(k) ? Q.get(k) !== '0' : !!man.layers?.[k];
const LOAD_R = 400, UNLOAD_R = 550, MAX_JOBS = 4;

// Surface class colours (FORMAT.md) for the collision fallback mesh and the minimap.
export const SURFACE_COLORS = {
  0: '#9a958c', 1: '#5d5f63', 2: '#b9b2a6', 3: '#6f9a55', 4: '#4f7fa8', 5: '#c8bca6',
  6: '#a08a66', 7: '#bfb6a6', 8: '#9c8f7c', 9: '#8d877d', 255: '#8a8a80',
};

const buildingMat = new THREE.MeshLambertMaterial({ color: /look=v2/.test(location.search) ? 0xb8ad9c : 0xd9cfbf });
const groundMat = new THREE.MeshLambertMaterial({ color: 0x8d9a7c });
const vcolMat = new THREE.MeshLambertMaterial({ color: 0xffffff, vertexColors: true });

function distToBounds([x0, y0, x1, y1], x, y) {
  return Math.hypot(Math.max(x0 - x, 0, x - x1), Math.max(y0 - y, 0, y - y1));
}

export class TileManager {
  constructor(base, manifest, scene, world, { onCollision, onUnload } = {}) {
    this.base = base; this.scene = scene; this.world = world;
    this.onCollision = onCollision; this.onUnload = onUnload;
    this.tiles = manifest.tiles.map(m => ({ m, state: 'idle', group: null, col: null, gen: 0 }));
    this.jobs = 0;
    this.trees = layerOn(manifest, 'trees'); this.objects = layerOn(manifest, 'objects');
    this.facades = layerOn(manifest, 'facades'); this.texLoader = new THREE.TextureLoader();
    this.loader = new GLTFLoader().setMeshoptDecoder(MeshoptDecoder);
  }

  tileAt(x, y) {
    return this.tiles.find(t => { const [x0, y0, x1, y1] = t.m.bounds; return x >= x0 && x <= x1 && y >= y0 && y <= y1; });
  }

  // Ready = the tile under (x, y) has both its collision and visuals loaded.
  readyAt(x, y) { const t = this.tileAt(x, y); return !!(t && t.state === 'loaded'); }

  // All tiles within r of (x, y) have finished loading (or failed).
  settled(x, y, r = 150) {
    return this.tiles.every(t => distToBounds(t.m.bounds, x, y) > r || t.state === 'loaded' || t.state === 'failed');
  }

  update(x, y) {
    const near = [];
    for (const t of this.tiles) {
      const d = distToBounds(t.m.bounds, x, y);
      if (d > UNLOAD_R && t.state !== 'idle') this.unload(t);
      else if (d <= LOAD_R && t.state === 'idle') near.push([d, t]);
    }
    near.sort((a, b) => a[0] - b[0]);
    for (const [, t] of near) { if (this.jobs >= MAX_JOBS) break; this.load(t); }
  }

  async load(t) {
    t.state = 'loading'; const gen = ++t.gen; this.jobs++;
    try {
      const bin = p => fetch(this.base + p).then(r => { if (!r.ok) throw new Error(`${r.status} ${p}`); return r.arrayBuffer(); });
      const [gltf, buf, tbuf, obuf] = await Promise.all([
        this.loader.loadAsync(this.base + t.m.glb), bin(t.m.collision), this.trees && t.m.trees ? bin(t.m.trees) : null,
        this.objects && t.m.objects ? bin(t.m.objects) : null,
      ]);
      if (gen !== t.gen) return; // unloaded meanwhile
      const t0 = performance.now();
      const col = new ColTile(parseCol(buf));
      t.col = col; this.world.add(t.m.id, col);
      const t1 = performance.now();
      t.group = this.prepare(gltf.scene, col);
      if (tbuf) t.group.add(makeTrees(tbuf));
      if (obuf) t.group.add(makeObjects(obuf));
      this.scene.add(t.group);
      if (this.facades && t.m.facades) this.loadFacades(t, gen, bin);   // after the tile is walkable: atlases are the bulk of the bytes
      t.state = 'loaded';
      const t2 = performance.now();
      this.onCollision?.(t);
      if (DEBUG) console.log(`[tile] ${t.m.id} fetched ${(t0 / 1000).toFixed(2)}s grid ${(t1 - t0) | 0}ms mesh ${(t2 - t1) | 0}ms map ${(performance.now() - t2) | 0}ms`);
    } catch (e) {
      console.warn('tile load failed', t.m.id, e);
      if (gen === t.gen) t.state = 'failed';
    } finally { this.jobs--; }
  }

  // Facade atlas pages stream in after the tile; window.__facadesPending counts pages still loading (photo_render waits on it).
  loadFacades(t, gen, bin) {
    [t.m.facades].flat().forEach((f, k) => {
      window.__facadesPending = (window.__facadesPending || 0) + 1;
      Promise.all([bin(f), this.texLoader.loadAsync(this.base + [t.m.facade_tex].flat()[k])])
        .then(([fb, ft]) => { if (gen === t.gen && t.group) t.group.add(makeFacades(fb, ft)); else ft.dispose(); })
        .catch(e => console.warn('facade page failed', f, e))
        .finally(() => { window.__facadesPending--; });
    });
  }

  unload(t) {
    t.gen++;
    if (t.group) {
      this.scene.remove(t.group);
      t.group.traverse(o => { if (o.isInstancedMesh) o.dispose(); else if (o.isMesh) { o.geometry.dispose(); if (o.userData.ownMat) { o.material.map?.dispose(); o.material.dispose(); } } });
    }
    this.world.remove(t.m.id); this.onUnload?.(t);
    t.group = null; t.col = null; t.state = 'idle';
  }

  // Swap glTF materials for cheap Lambert ones (vertex colours if COLOR_0 present). If the GLB has no
  // ground nodes (only `b:` buildings), draw the collision ground surfaces instead.
  prepare(root, col) {
    let hasGround = false;
    root.traverse(o => {
      if (!o.isMesh) return;
      const isBuilding = isB(o) || isB(o.parent); // GLTFLoader keeps the raw node name in userData.name
      if (!isBuilding) hasGround = true;
      const g = o.geometry, old = o.material;
      if (g.attributes.color && LOOK2) {   // GLB albedos were tuned for an over-bright rig; scale to plausible values
        const c = g.attributes.color.array, k = isBuilding ? 0.75 : 0.42;
        for (let i = 0; i < c.length; i++) c[i] *= k;
        o.material = vcolMat;
      } else if (g.attributes.color) o.material = isBuilding ? buildingVcolMat : groundVcolMat;
      else if (old?.color && old.color.getHex() !== 0xffffff) {
        o.material = new THREE.MeshLambertMaterial({ color: old.color }); o.userData.ownMat = true;
      } else o.material = isBuilding ? buildingMat : groundMat;
      if (old && old !== o.material) old.dispose?.();
      if (!g.attributes.normal) g.computeVertexNormals();
      o.castShadow = isBuilding; o.receiveShadow = true;
      o.matrixAutoUpdate = false; o.updateMatrix();
    });
    if (!hasGround) root.add(groundFromCollision(col));
    return root;
  }
}

const isB = o => /^b:/.test(o?.userData?.name ?? o?.name ?? '');

function groundFromCollision(col) {
  const { verts, tris, kind, surface, nt } = col;
  const pos = [], colr = [], c = new THREE.Color();
  for (let t = 0; t < nt; t++) {
    if (kind[t] === 0) continue;
    c.set(SURFACE_COLORS[surface[t]] || SURFACE_COLORS[0]); // hex is sRGB; Color stores linear
    for (let q = 0; q < 3; q++) {
      const p = tris[t * 3 + q] * 3;
      pos.push(verts[p], verts[p + 2], -verts[p + 1]);
      colr.push(c.r, c.g, c.b);
    }
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  g.setAttribute('color', new THREE.Float32BufferAttribute(colr, 3));
  g.computeVertexNormals();
  const m = new THREE.Mesh(g, vcolMat); m.name = 'ground:collision';
  return m;
}
