// Walkable Cambridge viewer: scene setup, tile streaming, player loop, UI.
import * as THREE from 'three';
import { CollisionWorld } from './collision.js';
import { TileManager } from './tiles.js';
import { Player } from './player.js';
import { Minimap, renderTileMap, initLandmarks, mergeLandmarks, initOverlays } from './ui.js';

const BASE = new URL('./', location.href).href;
const SKY = 0xbcd3e6;
const $ = id => document.getElementById(id);
const status = msg => { $('status').textContent = msg; };

async function getJSON(path, optional = false) {
  const r = await fetch(BASE + path);
  if (!r.ok) { if (optional) return null; throw new Error(`${path}: HTTP ${r.status}`); }
  return r.json();
}

async function main() {
  const canvas = $('view');
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, powerPreference: 'high-performance' });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(SKY);
  scene.fog = new THREE.Fog(SKY, 120, 420);
  const camera = new THREE.PerspectiveCamera(70, 1, 0.2, 600);
  scene.add(new THREE.HemisphereLight(0xdfeaf5, 0x6b6450, 1.6));
  const sun = new THREE.DirectionalLight(0xfff1dc, 1.8);
  sun.position.set(-0.5, 0.8, 0.35); scene.add(sun); // from the south-west-ish, high

  const resize = () => {
    renderer.setSize(innerWidth, innerHeight, false);
    camera.aspect = innerWidth / innerHeight; camera.updateProjectionMatrix();
  };
  addEventListener('resize', resize); resize();

  initOverlays();
  status('Loading manifest…');
  const manifest = await getJSON('manifest.json');
  const world = new CollisionWorld();
  const player = new Player(world, canvas);
  const minimap = new Minimap($('minimap'));
  const tiles = new TileManager(BASE, manifest, scene, world, {
    onCollision: t => minimap.add(t.m.id, renderTileMap(t.col)),
    onUnload: t => minimap.remove(t.m.id),
  });

  player.canPlace = (x, y) => tiles.settled(x, y);
  const sp = manifest.spawn;
  player.teleport(sp.x, sp.y, sp.z);

  const lmFile = await getJSON('landmarks.json', true).catch(() => null);
  const landmarks = mergeLandmarks(manifest.landmarks, lmFile?.landmarks || []);
  initLandmarks($('landmark-list'), landmarks, lm => {
    player.teleport(lm.x, lm.y, null, [lm.x, lm.y]);
    $('landmarks').hidden = true;
  });

  if (/debug/.test(location.search)) Object.assign(window, { __scene: scene, __THREE: THREE, __world: world, __p: player });
  // scripted-test hooks
  window.__player = {
    get position() { return { x: player.x, y: player.y, z: player.z }; },
    get heading() { return player.heading; },
    get loadedTiles() { return tiles.tiles.filter(t => t.state === 'loaded').length; },
    teleport: (x, y, z) => player.teleport(x, y, z ?? null),
  };

  status('Loading tiles…');
  let last = performance.now(), streamT = 0, ready = false, hudT = 0;
  renderer.setAnimationLoop(now => {
    const dt = (now - last) / 1000; last = now;
    streamT -= dt;
    if (streamT <= 0) { tiles.update(player.x, player.y); streamT = 0.25; }
    player.update(dt);
    const fc = window.__cam;   // debug/screenshot hook: {pos:[x,y,z], at:[x,y,z]} in the collision frame
    if (fc) { camera.position.set(fc.pos[0], fc.pos[2], -fc.pos[1]); camera.lookAt(fc.at[0], fc.at[2], -fc.at[1]); }
    else player.applyCamera(camera);
    renderer.render(scene, camera);
    if (!ready && !player.pendingPlace && tiles.readyAt(player.x, player.y)) {
      ready = true; window.__walkReadyAt = performance.now(); window.__walkReady = true;
      console.log(`[walkable] ready ${(performance.now() / 1000).toFixed(2)}s`);
      status('');
      $('help').hidden = false;
    }
    if ((hudT -= dt) <= 0) {
      hudT = 0.1;
      minimap.draw(player.x, player.y, player.heading);
      if (player.pendingPlace && ready) status('Loading…'); else if (ready) status('');
    }
  });
}

main().catch(e => { console.error(e); status('Failed to load: ' + e.message); });
