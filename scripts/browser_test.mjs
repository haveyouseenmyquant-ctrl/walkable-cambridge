#!/usr/bin/env node
// Headless-browser test of the viewer. Prints {"load_seconds": x, "site_errors": n}.
//
//   node scripts/browser_test.mjs [site_dir_or_url] [--walk-seconds N] [--screenshot file.png (taken at spawn)] [--headful]
//
// Serves a local directory (default: site/) with a tiny static server, or opens a URL. Uses the
// installed Google Chrome via puppeteer-core (npm install in tools/). load_seconds = navigation
// start -> window.__walkReady. site_errors = console errors + page errors + failed requests
// (HTTP >= 400 or network failure) during load and a scripted walk (hold W, turn periodically).
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const puppeteer = createRequire(path.join(ROOT, 'tools/'))('puppeteer-core');

const argv = process.argv.slice(2);
const opt = (name, def) => { const i = argv.indexOf(name); return i < 0 ? def : argv.splice(i, 2)[1]; };
const WALK_S = Number(opt('--walk-seconds', 60));
const SHOT = opt('--screenshot', null);
const MOVES_SHOT = opt('--moves-shots', null); // directory for 3rd-person / broom screenshots
const MOVES = !(argv.includes('--no-moves') && argv.splice(argv.indexOf('--no-moves'), 1));
const HEADFUL = argv.includes('--headful') && argv.splice(argv.indexOf('--headful'), 1);
const SRC = argv[0] || path.join(ROOT, 'site');
const LOAD_TIMEOUT = 45000;
// WC_GPU=1: render on the Mac's GPU (ANGLE Metal) at 1920x1080 and also report fps_median over the walk
const GPU = !!process.env.WC_GPU;
const CHROME = process.env.CHROME_PATH || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const log = (...a) => console.error('[browser_test]', ...a);

const MIME = { '.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript', '.css': 'text/css',
  '.json': 'application/json', '.glb': 'model/gltf-binary', '.svg': 'image/svg+xml', '.png': 'image/png',
  '.jpg': 'image/jpeg', '.wasm': 'application/wasm', '.col': 'application/octet-stream' };

function serve(dir) {
  const server = http.createServer((req, res) => {
    let p = decodeURIComponent(new URL(req.url, 'http://x').pathname);
    if (p.endsWith('/')) p += 'index.html';
    const f = path.join(dir, path.normalize(p));
    if (!f.startsWith(path.resolve(dir)) || !fs.existsSync(f) || !fs.statSync(f).isFile()) { res.writeHead(404); return res.end(); }
    const body = fs.readFileSync(f);
    res.writeHead(200, { 'Content-Type': MIME[path.extname(f)] || 'application/octet-stream', 'Content-Length': body.length });
    res.end(body);
  });
  return new Promise(ok => server.listen(0, '127.0.0.1', () => ok(server)));
}

const sleep = ms => new Promise(r => setTimeout(r, ms));

// Exercise every move once and check it had an effect. Returns {name: true/false/"skipped"}; failures are
// reported on stderr (they are not console errors, so they do not change site_errors).
async function testMoves(page) {
  const P = 'window.__player', get = expr => page.evaluate(`${P}.${expr}`), kb = page.keyboard;
  const res = {};
  const track = async (ms, expr) => { const v = []; const t = Date.now(); while (Date.now() - t < ms) { v.push(await get(expr)); await sleep(40); } return v; };
  const home = await page.evaluate(`({...${P}.position, yaw: ${P}.yaw})`);
  const reset = async () => { await page.evaluate(`${P}.place(${home.x}, ${home.y}, ${home.z}, ${home.yaw})`); await sleep(200); };
  const shot = async name => { if (MOVES_SHOT) { fs.mkdirSync(MOVES_SHOT, { recursive: true }); await page.screenshot({ path: path.join(MOVES_SHOT, name + '.png') }); } };
  // jump (first let the player settle: neighbouring tiles may still be loading)
  for (let i = 0, zp = NaN; i < 30; i++) { const z = await get('z'); if (Math.abs(z - zp) < 0.005) break; zp = z; await sleep(150); }
  const z0 = await get('z');
  await kb.down('Space'); await sleep(60); await kb.up('Space');
  const jz = await track(1400, 'z');
  res.jump = Math.max(...jz) - z0 > 0.6 && Math.abs(jz.at(-1) - z0) < 0.3;
  if (!res.jump) console.error('[browser_test] jump trace', z0, jz.map(v => v.toFixed(2)).join(' '));
  // run
  await kb.down('ShiftLeft'); await kb.down('KeyW');
  const rs = await track(800, 'speed');
  res.run = Math.max(...rs) > 5;
  // slide (crouch while running)
  await kb.down('KeyC'); const sl = await track(300, 'sliding'); await kb.up('KeyC');
  res.slide = sl.some(Boolean);
  await kb.up('KeyW'); await kb.up('ShiftLeft'); await reset();
  // crouch (hold)
  const eye0 = await get('eye');
  await kb.down('KeyC'); await sleep(400); const ce = await get('eye'), cr = await get('crouching'); await kb.up('KeyC');
  res.crouch = cr && eye0 - ce > 0.4;
  await sleep(300);
  // dash (Q) and double-tap
  await kb.press('KeyQ'); const ds = await track(200, 'speed');
  res.dash = Math.max(...ds) > 10;
  await reset(); await sleep(1100);
  await kb.press('KeyW'); await sleep(60); await kb.press('KeyW'); const ds2 = await track(200, 'speed');
  res.dash_doubletap = Math.max(...ds2) > 10;
  await reset();
  // third person view
  await kb.press('KeyV'); await sleep(500); res.third_person = (await get('view')) === 3; await shot('third_person');
  // broom: mount, climb, fly with boost, descend, dismount in the air -> fall and land
  await kb.press('KeyB'); await sleep(200); res.broom_mount = (await get('mode')) === 'broom';
  const bz0 = await get('z');
  await kb.down('Space'); await sleep(2000); await kb.up('Space');
  const bz1 = await get('z'); res.broom_up = bz1 - bz0 > 5;
  await page.evaluate(`${P}.pitch = 0`);
  const bp0 = await get('position');
  await kb.down('ShiftLeft'); await kb.down('KeyW'); await sleep(1500); await kb.up('KeyW'); await kb.up('ShiftLeft');
  const bp1 = await get('position'); res.broom_fly = Math.hypot(bp1.x - bp0.x, bp1.y - bp0.y) > 15; await shot('broom');
  await sleep(1200); const hz0 = await get('z'); await sleep(800); res.broom_hover = Math.abs((await get('z')) - hz0) < 0.3;
  await kb.down('KeyC'); await sleep(700); await kb.up('KeyC'); res.broom_down = (await get('z')) < hz0 - 1;
  await kb.press('KeyB'); await sleep(100); res.broom_dismount = (await get('mode')) === 'walk';
  const fz = await track(3000, 'grounded'); res.fall_and_land = fz.at(-1) === true;
  await kb.press('KeyV'); await sleep(100);
  await reset();
  // ledge climb at the nearest ledge 0.6-1.5 m high (if the map has one nearby)
  const L = await page.evaluate(`${P}.findLedge(150)`);
  if (!L) res.ledge_climb = 'skipped';
  else {
    await page.evaluate(`${P}.place(${L.x}, ${L.y}, ${L.z}, ${L.yaw})`); await sleep(200);
    await kb.down('KeyW'); const lz = await track(1200, 'z'); await kb.up('KeyW');
    res.ledge_climb = Math.max(...lz) - L.z > 0.55;
  }
  await reset();
  const failed = Object.entries(res).filter(([, v]) => v === false).map(([k]) => k);
  log('moves', JSON.stringify(res), failed.length ? `FAILED: ${failed.join(', ')}` : 'all ok');
  return res;
}

async function main() {
  let server = null, url = SRC;
  if (!/^https?:\/\//.test(SRC)) {
    server = await serve(path.resolve(SRC));
    url = `http://127.0.0.1:${server.address().port}/`;
  }
  const browser = await puppeteer.launch({
    executablePath: CHROME, headless: !HEADFUL && !GPU,   // headless Chrome throttles rAF to ~15 fps, so GPU runs use a window
    args: [GPU ? '--use-angle=metal' : '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--enable-gpu', '--disable-background-timer-throttling', '--disable-renderer-backgrounding', '--disable-backgrounding-occluded-windows', GPU ? '--window-size=1920,1080' : '--window-size=1280,720', '--no-first-run'],
    defaultViewport: GPU ? { width: 1920, height: 1080, deviceScaleFactor: 1 } : { width: 1280, height: 720 },
  });
  const errors = [], T0 = Date.now();
  const err = msg => errors.push(`+${((Date.now() - T0) / 1000).toFixed(1)}s ${msg}`);
  const out = { load_seconds: null, site_errors: 0 };
  try {
    const page = await browser.newPage();
    page.on('console', m => { if (m.type() === 'error') err(`console: ${m.text()} ${m.location()?.url || ''}`); });
    page.on('pageerror', e => err(`pageerror: ${e.message}`));
    page.on('requestfailed', r => err(`requestfailed: ${r.url()} ${r.failure()?.errorText}`));
    page.on('response', r => { if (r.status() >= 400) err(`HTTP ${r.status()}: ${r.url()}`); });

    await page.goto(url + (process.env.WC_QUERY || ''), { waitUntil: 'domcontentloaded', timeout: LOAD_TIMEOUT });
    try {
      await page.waitForFunction('window.__walkReady === true', { polling: 50, timeout: LOAD_TIMEOUT });
      out.load_seconds = Math.round(await page.evaluate('window.__walkReadyAt') / 10) / 100;
    } catch { err(`not ready within ${LOAD_TIMEOUT / 1000}s`); }

    if (SHOT && out.load_seconds != null) { await sleep(1500); await page.screenshot({ path: SHOT }); log('screenshot at spawn', SHOT); }
    if (out.load_seconds != null && MOVES) out.moves = await testMoves(page);
    if (out.load_seconds != null && WALK_S > 0) {
      const start = await page.evaluate('window.__player.position');
      let dist = 0, prev = start;
      await page.evaluate(() => { const f = window.__frames = []; const tick = t => { f.push(t); requestAnimationFrame(tick); }; requestAnimationFrame(tick); });
      await page.keyboard.down('KeyW');
      const t0 = Date.now();
      // walk forward; turn ~90 degrees when blocked, otherwise drift a little; run half the time
      for (let i = 0; Date.now() - t0 < WALK_S * 1000; i++) {
        await sleep(Math.min(2000, WALK_S * 1000 - (Date.now() - t0)));
        const p = await page.evaluate('window.__player.position');
        const moved = Math.hypot(p.x - prev.x, p.y - prev.y);
        dist += moved; prev = p;
        if (Date.now() - t0 >= WALK_S * 1000) break;
        await page.keyboard[i % 4 < 2 ? 'down' : 'up']('ShiftLeft');
        const turn = (i % 3 === 2) ? 'ArrowRight' : 'ArrowLeft';
        const ms = moved < 1.5 ? 900 : (i % 2 ? 200 : 0);
        if (ms) { await page.keyboard.down(turn); await sleep(ms); await page.keyboard.up(turn); }
      }
      await page.keyboard.up('KeyW'); await page.keyboard.up('ShiftLeft');
      if (GPU) {   // frames per whole second of the walk, median
        const f = await page.evaluate('window.__frames'), per = {};
        for (const t of f) { const k = Math.floor((t - f[0]) / 1000); per[k] = (per[k] || 0) + 1; }
        const c = Object.entries(per).filter(([k]) => +k < Math.floor((f.at(-1) - f[0]) / 1000)).map(([, v]) => v).sort((a, b) => a - b);
        out.fps_median = c.length ? c[Math.floor(c.length / 2)] : null;
      }
      const tiles = await page.evaluate('window.__player.loadedTiles');
      log(`walked ${dist.toFixed(1)} m in ${WALK_S}s from (${start.x.toFixed(1)}, ${start.y.toFixed(1)}) to (${prev.x.toFixed(1)}, ${prev.y.toFixed(1)}), ${tiles} tiles loaded`);
    }
  } finally {
    await browser.close();
    server?.close();
  }
  out.site_errors = errors.length;
  for (const e of errors) log(e);
  const { moves, ...kpis } = out;
  if (moves) console.error(JSON.stringify({ moves }));
  console.log(JSON.stringify(kpis));
}

main().catch(e => { console.error(e); console.log(JSON.stringify({ load_seconds: null, site_errors: 1 })); process.exit(1); });
