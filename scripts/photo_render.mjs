#!/usr/bin/env node
// Render the viewer from each benchmark camera pose (photo_match_score / judged_realism).
//   node scripts/photo_render.mjs <site_dir_or_url> <views.json> <out_dir> [--width 896] [--only id,id]
// views.json: [{id, x, y, heading (deg, clockwise from grid north), pitch (deg, up +), hfov (deg), w, h}, ...]
// x/y are in the world frame (EPSG:27700 minus manifest origin). The player is teleported to (x, y) so that
// the tiles stream in and the ground height is found; the camera is put at ground + 1.65 m (eye height).
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const puppeteer = createRequire(path.join(ROOT, 'tools/'))('puppeteer-core');
const argv = process.argv.slice(2);
const opt = (name, def) => { const i = argv.indexOf(name); return i < 0 ? def : argv.splice(i, 2)[1]; };
const WIDTH = Number(opt('--width', 896));
const ONLY = opt('--only', null)?.split(',');
const [SRC, VIEWS, OUT] = argv;
const CHROME = process.env.CHROME_PATH || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const EYE = 1.65;
const MIME = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json',
  '.glb': 'model/gltf-binary', '.svg': 'image/svg+xml', '.png': 'image/png', '.jpg': 'image/jpeg', '.col': 'application/octet-stream' };
const sleep = ms => new Promise(r => setTimeout(r, ms));

let base = SRC, server = null;
if (!/^https?:/.test(SRC)) {
  const dir = path.resolve(SRC);
  server = http.createServer((req, res) => {
    let p = decodeURIComponent(new URL(req.url, 'http://x').pathname);
    if (p.endsWith('/')) p += 'index.html';
    const f = path.join(dir, path.normalize(p));
    if (!f.startsWith(dir) || !fs.existsSync(f) || !fs.statSync(f).isFile()) { res.writeHead(404); return res.end(); }
    res.writeHead(200, { 'Content-Type': MIME[path.extname(f)] || 'application/octet-stream' });
    res.end(fs.readFileSync(f));
  });
  await new Promise(ok => server.listen(0, '127.0.0.1', ok));
  base = `http://127.0.0.1:${server.address().port}/`;
}
fs.mkdirSync(OUT, { recursive: true });
// views already rendered in OUT are skipped (a crashed worker can be re-run for the rest)
const views = JSON.parse(fs.readFileSync(VIEWS)).filter(v => (!ONLY || ONLY.includes(String(v.id)))
  && !fs.existsSync(path.join(OUT, `${v.id}.png`)));
const browser = await puppeteer.launch({
  executablePath: CHROME, headless: true,
  args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'],
});
try {
  const page = await browser.newPage();
  if (process.env.WC_DEBUG) { page.on('console', m => console.error('[console]', m.text())); page.on('pageerror', e => console.error('[pageerror]', e.message)); }
  await page.setViewport({ width: WIDTH, height: Math.round(WIDTH * 0.75) });
  await page.goto(base + (base.includes('?') ? '&' : '?') + 'debug' + (process.env.WC_QUERY ? '&' + process.env.WC_QUERY : ''), { waitUntil: 'domcontentloaded' });
  await page.waitForFunction('window.__walkReady === true', { timeout: 60000 });
  await page.waitForFunction('window.__texReady !== false', { timeout: 60000 });
  await page.addStyleTag({ content: 'body *{visibility:hidden!important} #view{visibility:visible!important}' });
  for (const v of views) {
    const h = Math.round(WIDTH * v.h / v.w);
    await page.setViewport({ width: WIDTH, height: h });
    await page.evaluate((x, y) => { window.__cam = null; window.__player.teleport(x, y); }, v.x, v.y);
    await sleep(300);
    await page.waitForFunction('!window.__player.pendingPlace', { timeout: 30000 }).catch(() => {});
    const z = await page.evaluate('window.__player.z');
    const hd = v.heading * Math.PI / 180, pt = (v.pitch || 0) * Math.PI / 180;
    const vfov = 2 * Math.atan(Math.tan(v.hfov * Math.PI / 360) * h / WIDTH) * 180 / Math.PI;
    const pos = [v.x, v.y, z + EYE];
    const at = [v.x + Math.sin(hd) * Math.cos(pt) * 10, v.y + Math.cos(hd) * Math.cos(pt) * 10, z + EYE + Math.sin(pt) * 10];
    await page.evaluate((pos, at, fov) => { window.__cam = { pos, at, fov }; }, pos, at, vfov);
    await sleep(1500);   // neighbouring tiles finish streaming
    await page.waitForFunction('!(window.__facadesPending > 0)', { timeout: 30000 }).catch(() => {});
    await sleep(200);   // a frame with the new atlases
    await page.screenshot({ path: path.join(OUT, `${v.id}.png`) });
    console.error('[render]', v.id, z.toFixed(2));
  }
} finally { await browser.close(); server?.close(); }
