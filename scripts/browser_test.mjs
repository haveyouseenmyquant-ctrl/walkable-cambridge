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
const HEADFUL = argv.includes('--headful') && argv.splice(argv.indexOf('--headful'), 1);
const SRC = argv[0] || path.join(ROOT, 'site');
const LOAD_TIMEOUT = 45000;
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

async function main() {
  let server = null, url = SRC;
  if (!/^https?:\/\//.test(SRC)) {
    server = await serve(path.resolve(SRC));
    url = `http://127.0.0.1:${server.address().port}/`;
  }
  const browser = await puppeteer.launch({
    executablePath: CHROME, headless: !HEADFUL,
    args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--window-size=1280,720', '--no-first-run'],
    defaultViewport: { width: 1280, height: 720 },
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

    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: LOAD_TIMEOUT });
    try {
      await page.waitForFunction('window.__walkReady === true', { polling: 50, timeout: LOAD_TIMEOUT });
      out.load_seconds = Math.round(await page.evaluate('window.__walkReadyAt') / 10) / 100;
    } catch { err(`not ready within ${LOAD_TIMEOUT / 1000}s`); }

    if (SHOT && out.load_seconds != null) { await sleep(1500); await page.screenshot({ path: SHOT }); log('screenshot at spawn', SHOT); }
    if (out.load_seconds != null && WALK_S > 0) {
      const start = await page.evaluate('window.__player.position');
      let dist = 0, prev = start;
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
      const tiles = await page.evaluate('window.__player.loadedTiles');
      log(`walked ${dist.toFixed(1)} m in ${WALK_S}s from (${start.x.toFixed(1)}, ${start.y.toFixed(1)}) to (${prev.x.toFixed(1)}, ${prev.y.toFixed(1)}), ${tiles} tiles loaded`);
    }
  } finally {
    await browser.close();
    server?.close();
  }
  out.site_errors = errors.length;
  for (const e of errors) log(e);
  console.log(JSON.stringify(out));
}

main().catch(e => { console.error(e); console.log(JSON.stringify({ load_seconds: null, site_errors: 1 })); process.exit(1); });
