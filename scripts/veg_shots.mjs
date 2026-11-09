#!/usr/bin/env node
// Eye-level vegetation screenshots (session 46): docs/screens/<prefix>_<spot>.png
//   node scripts/veg_shots.mjs <prefix> [site_dir] [extra query, e.g. quality=low]
// GPU (ANGLE Metal) at 1280x720; uses the ?debug window.__cam / __world hooks; exploration mode (no game layer).
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const puppeteer = createRequire(path.join(ROOT, 'tools/'))('puppeteer-core');
const [PREFIX = 'veg', srcArg, extra = ''] = process.argv.slice(2);
const SRC = path.resolve(srcArg || path.join(ROOT, 'site'));
const CHROME = process.env.CHROME_PATH || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const MIME = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.glb': 'model/gltf-binary' };
const sleep = ms => new Promise(r => setTimeout(r, ms));
// [name, eye x, eye y, look-at x, look-at y, look-at height above eye ground]
const SPOTS = [
  ['senate', -188, 62, -225, 92, 1.0],      // Senate House lawn from King's Parade
  ['kingsparade', -186, 40, -250, 0, 3.0],  // King's front lawn + Parade trees
  ['market', -118, 52, -152, 62, 5.0],      // from Market Square west towards Great St Mary's
  ['backs', -420, 0, -300, -10, 4.0],       // the Backs lawn towards King's Chapel
];
const server = http.createServer((req, res) => {
  let p = decodeURIComponent(new URL(req.url, 'http://x').pathname);
  if (p.endsWith('/')) p += 'index.html';
  const f = path.join(SRC, path.normalize(p));
  if (!f.startsWith(SRC) || !fs.existsSync(f) || !fs.statSync(f).isFile()) { res.writeHead(404); return res.end(); }
  res.writeHead(200, { 'Content-Type': MIME[path.extname(f)] || 'application/octet-stream' });
  res.end(fs.readFileSync(f));
});
await new Promise(ok => server.listen(0, '127.0.0.1', ok));
const browser = await puppeteer.launch({
  executablePath: CHROME, headless: true,
  args: ['--use-angle=metal', '--ignore-gpu-blocklist', '--enable-gpu', '--window-size=1280,720'],
  defaultViewport: { width: 1280, height: 720 },
});
const errors = [];
try {
  const page = await browser.newPage();
  page.on('pageerror', e => errors.push(String(e)));
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
  await page.goto(`http://127.0.0.1:${server.address().port}/?debug&explore${extra ? '&' + extra : ''}`, { waitUntil: 'domcontentloaded' });
  await page.waitForFunction('window.__walkReady === true', { timeout: 90000 });
  await page.addStyleTag({ content: '#help,#minimap,#status,.hud{display:none!important}' });
  for (const [name, x, y, ax, ay, dz] of SPOTS) {
    await page.evaluate((x, y) => window.__player.teleport(x, y), x, y);
    await sleep(800);
    await page.waitForFunction('!window.__player.pendingPlace && window.__player.settled(150)', { timeout: 60000 }).catch(() => {});
    await page.evaluate((x, y, ax, ay, dz) => {
      const s = window.__world.support(x, y, 1e4), z = (s ? s.z : 9) + 1.65;
      window.__cam = { pos: [x, y, z], at: [ax, ay, z + dz - 1.0], fov: 70 };
    }, x, y, ax, ay, dz);
    await sleep(3000);
    const out = path.join(ROOT, 'docs/screens', `${PREFIX}_${name}.png`);
    await page.screenshot({ path: out });
    console.error('[veg]', out);
  }
} finally { await browser.close(); server.close(); }
console.log(JSON.stringify({ errors }));
