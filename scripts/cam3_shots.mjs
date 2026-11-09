#!/usr/bin/env node
// Third-person camera screenshots under the Market Hill stall canopies (session 60): game mode, view 3, a few yaws.
//   WC_SITE=<dir> node scripts/cam3_shots.mjs <out_prefix>
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const puppeteer = createRequire(path.join(ROOT, 'tools/'))('puppeteer-core');
const SRC = path.resolve(process.env.WC_SITE || path.join(ROOT, 'site')), OUT = process.argv[2] || path.join(ROOT, 'docs/screens/cam3');
const MIME = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.glb': 'model/gltf-binary' };
const server = http.createServer((req, res) => {
  let p = decodeURIComponent(new URL(req.url, 'http://x').pathname); if (p.endsWith('/')) p += 'index.html';
  const f = path.join(SRC, path.normalize(p));
  if (!f.startsWith(SRC) || !fs.existsSync(f) || !fs.statSync(f).isFile()) { res.writeHead(404); return res.end(); }
  res.writeHead(200, { 'Content-Type': MIME[path.extname(f)] || 'application/octet-stream' }); res.end(fs.readFileSync(f));
});
await new Promise(ok => server.listen(0, '127.0.0.1', ok));
const browser = await puppeteer.launch({ executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless: true, protocolTimeout: 0,
  args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'], defaultViewport: { width: 960, height: 540 } });
const errors = [], info = [];
try {
  const page = await browser.newPage();
  page.on('pageerror', e => errors.push(String(e))); page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
  await page.goto(`http://127.0.0.1:${server.address().port}/?debug&nopick`, { waitUntil: 'domcontentloaded', timeout: 300000 });
  await page.waitForFunction('window.__walkReady === true && window.__game && window.__game.mobSystem', { timeout: 300000, polling: 500 });
  const SPOTS = [[-100, 62, 0], [-100, 62, 1.6], [-104, 52, 3.1], [-96, 66, -1.6]];
  for (let i = 0; i < SPOTS.length; i++) {
    const r = await page.evaluate(async ([x, y, yaw]) => {
      const P = window.__p; window.__game.paused = true;
      window.__player.teleport(x, y); await new Promise(r => setTimeout(r, 2500));
      P.view = 3; P.yaw = yaw; P.pitch = -0.3; P.camD = null; P.camP = null;
      await new Promise(r => setTimeout(r, 1500));
      return { x: P.x, y: P.y, camD: P.camD, camP: P.camP };
    }, SPOTS[i]);
    info.push(r);
    await page.screenshot({ path: `${OUT}_${i + 1}.jpg`, quality: 70 });
  }
} finally { console.log(JSON.stringify({ errors, info })); await browser.close(); server.close(); }
