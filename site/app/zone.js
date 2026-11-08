// Detailed zones (session 30): real 3D facade geometry (scripts/zone_build.py) for the Market Square zone.
// site/zone/zone.json {glb, centre, radius, stats} is optional (404 = no zone). The GLB holds one node per building
// ("f:<osm_id>": a facade skin 0.25 m outside the tile wall with real openings, reveals, sills, cornices...) plus
// street-prop nodes; vertex colours, plain Lambert (no brick/ashlar detail texture: the parts carry their own colour).
// ?zone=0 disables it. window.__zoneReady turns true once loaded (or absent / failed).
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { MeshoptDecoder } from '../vendor/meshoptimizer/meshopt_decoder.module.js';

const zoneMat = new THREE.MeshLambertMaterial({ color: 0xffffff, vertexColors: true });

export async function loadZone(base, scene) {
  window.__zoneReady = false;
  try {
    if (new URLSearchParams(location.search).get('zone') === '0') return null;
    const r = await fetch(base + 'zone/zone.json');
    if (!r.ok) return null;
    const zone = await r.json();
    const gltf = await new GLTFLoader().setMeshoptDecoder(MeshoptDecoder).loadAsync(base + zone.glb);
    const root = gltf.scene;
    root.name = 'zone';
    root.traverse(o => {
      if (!o.isMesh) return;
      o.material?.dispose?.();
      o.material = zoneMat;
      o.castShadow = true; o.receiveShadow = true;
      o.matrixAutoUpdate = false; o.updateMatrix();
    });
    scene.add(root);
    zone.root = root;
    return zone;
  } catch (e) {
    console.warn('zone failed', e);
    return null;
  } finally {
    window.__zoneReady = true;
  }
}
