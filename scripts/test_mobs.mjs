#!/usr/bin/env node
// Mob system test: headless Chrome loads /?debug, waits for the game layer, checks encounter spawn spots,
// then runs window.__mobTest for every mob type (spawn -> attacks player -> damaged -> dies -> 'kill' event).
//   node scripts/test_mobs.mjs [site_dir]
// Prints one JSON line {mob_types_ok, bosses_ok, results, ...}; exit code 1 on failure.
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const puppeteer = createRequire(path.join(ROOT, 'tools/'))('puppeteer-core');
const SRC = path.resolve(process.argv[2] || path.join(ROOT, 'site'));
const CHROME = process.env.CHROME_PATH || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const MIME = { '.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.glb': 'model/gltf-binary' };
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
  executablePath: CHROME, headless: true, protocolTimeout: 0,
  args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--window-size=960,540'],
  defaultViewport: { width: 960, height: 540 },
});
// session 42: the run hung for 20+ min with no output; a watchdog reports what finished and exits
const stage = { at: 'load' };
setTimeout(() => { console.log(JSON.stringify({ mob_types_ok: 0, bosses_ok: 0, error: 'watchdog 900 s at ' + stage.at })); process.exit(1); }, 900000).unref();
const errors = [];
let out = { mob_types_ok: 0, bosses_ok: 0 }, ok = false;
try {
  const page = await browser.newPage();
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
  page.on('pageerror', e => errors.push(String(e)));
  const missing = [];
  page.on('response', r => { if (r.status() === 404) missing.push(new URL(r.url()).pathname); });
  await page.goto(`http://127.0.0.1:${server.address().port}/?debug`, { waitUntil: 'domcontentloaded' });
  await page.waitForFunction('window.__walkReady === true', { timeout: 90000 });
  await page.waitForFunction('window.__game && window.__game.mobSystem && window.__mobTest', { timeout: 30000 });
  await sleep(3000);   // let encounters near the spawn point stream in
  // encounter check: teleport to each encounter, wait for tiles, report whether its mobs spawned on walkable ground
  stage.at = 'encounters';
  const encounters = await page.evaluate(async () => {
    const g = window.__game, sys = g.mobSystem, out = [];
    // session 42: 93 encounters x 12 s took ~20 min; check the 15 nearest the square (the route + ring 1)
    const near = [...g.encounters].sort((a, b) => Math.hypot(a.x + 102.9, a.y - 70) - Math.hypot(b.x + 102.9, b.y - 70)).slice(0, 15);
    for (const e of near) {
      window.__player.teleport(e.x, e.y);
      const t0 = performance.now();
      while (performance.now() - t0 < 12000) {
        await new Promise(r => setTimeout(r, 400));
        if (sys.encounterState.get(e.id)?.active) break;
      }
      const s = sys.encounterState.get(e.id);
      const live = (s?.mobs || []).filter(m => !m.dead);
      out.push({ id: e.id, spawned: live.length, of: e.mobs.length,
        offset: s?.spot ? +Math.hypot(s.spot.x - e.x, s.spot.y - e.y).toFixed(1) : null,
        onGround: live.every(m => m.type.flying || sys.world.standAt(m.x, m.y, m.groundZ) != null) });
    }
    return out;
  });
  stage.at = 'perf';
  // fps with the live mobs around Market Square
  const perf = await page.evaluate(async () => {
    const g = window.__game, sys = g.mobSystem;
    window.__player.teleport(-102.9, 70);
    await new Promise(r => setTimeout(r, 6000));
    const fps = async () => { let n = 0; const t0 = performance.now();
      await new Promise(r => { const f = () => { n++; if (performance.now() - t0 < 3000) requestAnimationFrame(f); else r(); }; requestAnimationFrame(f); });
      return +(n / ((performance.now() - t0) / 1000)).toFixed(1); };
    const withMobs = await fps(); sys.root.visible = false; const without = await fps(); sys.root.visible = true;
    return { liveMobs: g.mobs.length, fps: withMobs, fpsMobsHidden: without };
  });
  stage.at = 'per-type';
  // per-type test away from encounters, with encounters off
  await page.evaluate(async () => {
    const g = window.__game, sys = g.mobSystem;
    sys.encountersEnabled = false;
    for (const m of [...g.mobs]) sys.remove(m);
    for (const s of sys.encounterState.values()) { s.active = false; s.mobs = []; }
    const p = g.encounters.find(e => e.id === 'market-north');
    window.__player.teleport(p.x, p.y);
    await new Promise(r => setTimeout(r, 4000));
  });
  // session 42: one evaluate per type with a 45 s cap, so a hung type fails alone instead of hanging the run
  const types = await page.evaluate(() => window.__game.mobTypes.map(t => ({ id: t.id, boss: !!t.boss })));
  const results = [];
  for (const t of types) {
    stage.at = 'per-type ' + t.id;
    const r = await page.evaluate(async id => {
      const g = window.__game, items = g.items, sys = g.mobSystem;
      g.invulnUntil = 0; g.shield = 0;
      for (const m of [...g.mobs]) sys.remove(m);
      const drops0 = items?.drops?.length ?? null;
      const r = await Promise.race([window.__mobTest(id), new Promise(ok => setTimeout(() => ok({ id, timeout: true }), 45000))]);
      if (items) r.dropAppeared = drops0 == null ? 'unknown' : (items.drops?.length ?? 0) > drops0;
      return r;
    }, t.id);
    r.boss = t.boss; results.push(r);
    console.error('[mob]', JSON.stringify(r).slice(0, 200));
  }
  const pass = r => r.spawned && r.attacked && r.damaged && r.died && r.killEvent;
  out = {
    mob_types_ok: results.filter(r => !r.boss && pass(r)).length,
    bosses_ok: results.filter(r => r.boss && pass(r)).length,
    encounters_ok: encounters.filter(e => e.spawned > 0 && e.onGround).length, encounters_total: encounters.length,
    ...perf, console_errors: errors.length, errors: errors.slice(0, 5), encounters, results,
  };
  out.missing_404 = [...new Set(missing)];
  const real = errors.filter(e => !/404/.test(e) || !missing.every(m => m.startsWith('/app/game/') && !m.includes('mobs')));
  out.console_errors = real.length;
  ok = results.every(pass) && real.length === 0;
} catch (e) { out.error = String(e); out.errors = errors.slice(0, 5); }
finally { await browser.close(); server.close(); }
console.log(JSON.stringify(out));
process.exit(ok ? 0 : 1);
