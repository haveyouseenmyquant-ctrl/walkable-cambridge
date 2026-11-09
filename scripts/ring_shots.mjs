#!/usr/bin/env node
// Eye-level screenshots from given camera poses (session 60): node scripts/ring_shots.mjs [site] --views v.json --out prefix
//   node scripts/landmark_shots.mjs [site_dir] [--only id,id]
// Uses the viewer's window.__cam hook; the player is teleported to the landmark so its tiles stream in.
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const puppeteer = createRequire(path.join(ROOT, 'tools/'))('puppeteer-core');
const argv = process.argv.slice(2);
const oi = argv.indexOf('--only');
const ONLY = oi < 0 ? null : argv.splice(oi, 2)[1].split(',');
const SRC = path.resolve(argv[0] && !argv[0].startsWith('--') ? argv[0] : path.join(ROOT, 'site'));
const CHROME = process.env.CHROME_PATH || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const MIME = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.glb': 'model/gltf-binary' };
const sleep = ms => new Promise(r => setTimeout(r, ms));

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
  args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--window-size=1280,720'],
  defaultViewport: { width: 1280, height: 720 },
});
try {
  const page = await browser.newPage(); page.on('console', m => { if (m.type() === 'error' || m.type() === 'warning') console.error('[page]', m.text()); }); page.on('pageerror', e => console.error('[pageerror]', e.message));
  await page.goto(`http://127.0.0.1:${server.address().port}/?debug&explore`, { waitUntil: 'domcontentloaded' });
  await page.waitForFunction('window.__walkReady === true', { timeout: 180000 });
  // eye-level views: --views JSON [{name, pos:[E,N,z], at:[E,N,z]}], --out prefix
  const vi = argv.indexOf('--views');
  const views = JSON.parse(fs.readFileSync(argv[vi + 1]));
  const pre = argv[argv.indexOf('--out') + 1];
  for (const v of views) {
    await page.evaluate((x, y) => window.__player.teleport(x, y), v.pos[0], v.pos[1]);
    await page.evaluate((pos, at) => { window.__cam = { pos, at }; }, v.pos, v.at);
    await sleep(800);
    await page.waitForFunction('!window.__player.pendingPlace', { timeout: 30000 }).catch(() => {});
    await sleep(3000);
    await page.screenshot({ path: `${pre}_${v.name}.jpg`, quality: 85 });
    console.error('[shots]', v.name);
  }
} finally { await browser.close(); server.close(); }
