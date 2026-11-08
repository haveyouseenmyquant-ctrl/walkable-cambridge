#!/usr/bin/env node
// Headless route bot (playtest KPIs). For every class: load /?debug&nopick in a fresh browser context, pick the class,
// then walk a fixed route through 5 encounters around Market Square / Peas Hill / King's Parade / Senate House Hill
// and finish with the Bellwarden (boss-market). The bot moves only through the real Player (held keys + yaw, so
// collision, steps and walls apply), plans paths on a 1 m grid with world.standAt, casts the class's spells through
// game.caster.cast, walks over kill spots to pick up loot (items.js pickup radius), equips better drops, picks talents
// at level-ups and uses the real death screen button if it dies. The game clock is stepped deterministically
// (player.update + game.update at 20 Hz from page.evaluate), a few seconds of game time per evaluate.
// Classes run in parallel (one browser context each, fresh localStorage); each run reloads the page.
// playable = class data ok (>=6 spells incl. a blink + an ult, >=3 talent choices) and >= half its runs pass.
//   node scripts/playtest.mjs [site_dir] [runs_per_class=5]
// Last stdout line: {playable_classes, playtest_pass_pct, boss_ttk_median_s, boss_ttk_spread_pct, classes, runs, ...}
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const puppeteer = createRequire(path.join(ROOT, 'tools/'))('puppeteer-core');
const SRC = path.resolve(process.argv[2] || path.join(ROOT, 'site'));
const RUNS = +(process.argv[3] || 5);
const CHROME = process.env.CHROME_PATH || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const MIME = { '.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.glb': 'model/gltf-binary' };
const ROUTE = ['market-north', 'market-south', 'peas-hill', 'kings-parade', 'senate-house-hill', 'boss-market'];
const T0 = Date.now();
const log = (...a) => console.error(`[playtest ${((Date.now() - T0) / 1000).toFixed(0)}s]`, ...a);
const median = a => { if (!a.length) return null; const s = [...a].sort((x, y) => x - y), n = s.length; return n % 2 ? s[n >> 1] : (s[n / 2 - 1] + s[n / 2]) / 2; };

const server = http.createServer((req, res) => {
  let p = decodeURIComponent(new URL(req.url, 'http://x').pathname);
  if (p.endsWith('/')) p += 'index.html';
  const f = path.join(SRC, path.normalize(p));
  if (!f.startsWith(SRC) || !fs.existsSync(f) || !fs.statSync(f).isFile()) { res.writeHead(404); return res.end(); }
  res.writeHead(200, { 'Content-Type': MIME[path.extname(f)] || 'application/octet-stream' });
  res.end(fs.readFileSync(f));
});
await new Promise(ok => server.listen(0, '127.0.0.1', ok));
const URL0 = `http://127.0.0.1:${server.address().port}/?debug&nopick`;
const browser = await puppeteer.launch({
  executablePath: CHROME, headless: true, protocolTimeout: 0,
  args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--window-size=480,270'],
  defaultViewport: { width: 480, height: 270 },   // small canvas: swiftshader frames between sim chunks stay cheap
});

// ---------------- the in-page bot (installed as window.__bot)
function installBot(route, runIdx) {
  const g = window.__game, P = window.__p, W = window.__world, sys = g.mobSystem, C = g.caster, items = g.items;
  const DT = 0.05;
  const ENC = Object.fromEntries(g.encounters.map(e => [e.id, e]));
  const ev = { kills: [], pickups: 0, equips: 0, deaths: 0, casts: 0, talents: 0, errors: [] };
  const offs = [];
  offs.push(g.on('kill', e => { if (e.mob) ev.kills.push({ x: e.mob.x, y: e.mob.y, boss: !!e.mob.boss, type: e.mob.type?.id, t: g.time }); }));
  offs.push(g.on('pickup', e => {
    ev.pickups++;
    // equip the drop if it beats what is in its slot (give() already equips into empty slots)
    const d = items.defs[e.id], ranks = Object.keys(items.rarities);
    const cur = items.equipped[d.slot], cd = cur && items.defs[cur];
    if (cur !== e.id && (!cd || ranks.indexOf(d.rarity) > ranks.indexOf(cd.rarity))) { if (items.equip(e.id)) ev.equips++; }
    else if (cur === e.id) ev.equips++;
  }));
  offs.push(g.on('cast', () => ev.casts++));
  // boss time-to-kill: from the first damage the boss takes to its death
  offs.push(g.on('hit', e => { if (e.target?.boss && bot.bossStart == null) bot.bossStart = g.time; }));
  offs.push(g.on('playerDeath', () => ev.deaths++));
  offs.push(g.on('levelup', () => {
    for (let t = 0; t < 3; t++) if (C.picks[t] == null && g.stats.level >= C.talentLevels[t]) { if (C.pickTalent(t, (runIdx + t) % 2)) ev.talents++; }
  }));

  // --- A* on a 1 m grid (walkable = world.standAt from the neighbour's feet height, so steps/walls apply)
  function plan(sx, sy, sz, tx, ty, tol = 1.5) {
    const pad = 30, x0 = Math.floor(Math.min(sx, tx) - pad), y0 = Math.floor(Math.min(sy, ty) - pad);
    const nx = Math.ceil(Math.max(sx, tx) + pad) - x0, ny = Math.ceil(Math.max(sy, ty) + pad) - y0, N = nx * ny;
    const zf = new Float32Array(N).fill(NaN), gs = new Float32Array(N).fill(Infinity), from = new Int32Array(N).fill(-1), closed = new Uint8Array(N);
    const ix = x => Math.round(x - x0), iy = y => Math.round(y - y0);
    const s = ix(sx) + iy(sy) * nx; zf[s] = sz; gs[s] = 0;
    const heap = [[Math.hypot(tx - sx, ty - sy), s]];
    const push = (f, i) => { heap.push([f, i]); let k = heap.length - 1; while (k) { const p = (k - 1) >> 1; if (heap[p][0] <= heap[k][0]) break; [heap[p], heap[k]] = [heap[k], heap[p]]; k = p; } };
    const pop = () => { const top = heap[0], last = heap.pop(); if (heap.length) { heap[0] = last; let k = 0; for (;;) { const l = 2 * k + 1, r = l + 1; let m = k; if (l < heap.length && heap[l][0] < heap[m][0]) m = l; if (r < heap.length && heap[r][0] < heap[m][0]) m = r; if (m === k) break; [heap[m], heap[k]] = [heap[k], heap[m]]; k = m; } } return top; };
    let best = s, bestD = Infinity, n = 0;
    while (heap.length && n++ < 60000) {
      const [, i] = pop(); if (closed[i]) continue; closed[i] = 1;
      const cx = i % nx, cy = (i / nx) | 0, wx = cx + x0, wy = cy + y0, d = Math.hypot(tx - wx, ty - wy);
      if (d < bestD) { bestD = d; best = i; }
      if (d <= tol) break;
      for (let a = -1; a <= 1; a++) for (let b = -1; b <= 1; b++) {
        if (!a && !b) continue;
        const qx = cx + a, qy = cy + b; if (qx < 0 || qy < 0 || qx >= nx || qy >= ny) continue;
        const j = qx + qy * nx; if (closed[j]) continue;
        let z = W.standAt(wx + a, wy + b, zf[i]); if (z == null) continue;
        if (a && b && (W.standAt(wx + a / 2, wy + b / 2, zf[i]) == null || W.standAt(wx + a, wy, zf[i]) == null || W.standAt(wx, wy + b, zf[i]) == null)) continue;
        if (W.standAt(wx + a / 2, wy + b / 2, zf[i]) == null) continue;
        const ng = gs[i] + (a && b ? 1.414 : 1); if (ng >= gs[j]) continue;
        gs[j] = ng; from[j] = i; zf[j] = z; push(ng + Math.hypot(tx - qx - x0, ty - qy - y0), j);
      }
    }
    const pts = []; for (let i = best; i >= 0; i = from[i]) pts.push({ x: i % nx + x0, y: ((i / nx) | 0) + y0 });
    pts.reverse(); return { pts, miss: bestD };
  }

  const bot = window.__bot = {
    ev, route, leg: 0, state: 'go', path: null, wp: 0, goal: null, stuckT: 0, lastPos: null, replans: 0,
    engaged: new Map(), loot: [], arriveT: null, bossStart: null, bossTtk: null, fail: null, done: false,
    t0: g.time, maxT: 900, noSpawnT: 0,
    dispose() { for (const f of offs) f(); },
  };
  const live = () => g.mobs.filter(m => !m.dead);
  const hostile = m => !['idle', 'patrol', 'return', 'dead'].includes(m.state);
  const dist = m => Math.hypot(m.x - P.x, m.y - P.y);
  function setGoal(x, y, tol = 1.5) { bot.goal = { x, y, tol }; bot.path = plan(P.x, P.y, P.z, x, y, tol).pts; bot.wp = 0; }
  function steer(dt) {   // hold W (+Shift) toward the next waypoint; returns true when the goal is reached
    const G = bot.goal; if (!G) return true;
    if (Math.hypot(G.x - P.x, G.y - P.y) <= G.tol + 0.3) { bot.path = null; bot.goal = null; return true; }
    if (!bot.path || bot.wp >= bot.path.length) { setGoal(G.x, G.y, G.tol); if (!bot.path.length) return false; }
    let q = bot.path[bot.wp];
    while (Math.hypot(q.x - P.x, q.y - P.y) < 0.9 && bot.wp < bot.path.length - 1) q = bot.path[++bot.wp];
    if (bot.wp >= bot.path.length - 1 && Math.hypot(q.x - P.x, q.y - P.y) < 0.9) { bot.path = null; bot.goal = null; return true; }
    P.yaw = Math.atan2(-(q.x - P.x), q.y - P.y);
    P.keys.add('KeyW'); P.keys.add('ShiftLeft');
    // stuck detection: no progress for 2 s -> jump, then replan
    bot.stuckT += dt;
    if (bot.stuckT > 2) {
      const moved = bot.lastPos ? Math.hypot(P.x - bot.lastPos.x, P.y - bot.lastPos.y) : 9;
      bot.lastPos = { x: P.x, y: P.y }; bot.stuckT = 0;
      if (moved < 0.5) { bot.replans++; P.keys.add('Space'); setGoal(G.x, G.y, G.tol); if (bot.replans > 8) bot.fail = 'softlock: no route progress'; }
      else bot.replans = 0;
    }
    return false;
  }
  function castAt(m) {
    const d = dist(m), sp = C.spells, nearby = live().filter(o => Math.hypot(o.x - m.x, o.y - m.y) < 7).length;
    const order = sp.map((s, i) => [s, i]).sort((a, b) => (b[0].ult - a[0].ult) || ((b[0].dmg || 0) - (a[0].dmg || 0)));
    for (const [s, i] of order) {
      if (g.time < s.readyAt || g.stats.mana < s.mana) continue;
      if (s.kind === 'blink') continue;                                      // movement spell: used for travel
      if (s.ult && !(m.boss || nearby >= 3)) continue;
      if (s.kind === 'shield' && !(m.boss || g.stats.hp < g.stats.maxHp * 0.7) && !s.dmg) continue;
      const reach = s.kind === 'nova' || s.kind === 'shield' ? (s.radius || 5) : (s.range || 10);
      if (d > reach + (m.radius || 0.5)) continue;
      if (C.cast(i, m)) return true;
    }
    return false;
  }
  function blinkForward() {   // travel with the class's movement spell along open straight path segments
    const i = C.spells.findIndex(s => s.kind === 'blink'); const s = C.spells[i];
    if (i < 0 || g.time < s.readyAt || g.stats.mana < s.mana + 30 || !bot.path) return;
    const q = bot.path[Math.min(bot.path.length - 1, bot.wp + Math.round(s.dist || 10))]; if (!q) return;
    const dx = q.x - P.x, dy = q.y - P.y, L = Math.hypot(dx, dy); if (L < (s.dist || 10) * 0.9) return;
    for (let k = 1; k < L; k += 0.5) if (W.standAt(P.x + dx * k / L, P.y + dy * k / L, P.z) == null) return;   // clear line only
    P.yaw = Math.atan2(-dx, dy); C.cast(i);
  }

  bot.step = function (dt) {
    if (bot.done || bot.fail) return;
    if (g.time - bot.t0 > bot.maxT) { bot.fail = 'timeout: route not finished'; return; }
    P.keys.clear();
    // death: use the real "Rise again" button
    if (g.stats.hp <= 0 || g.paused) {
      const btn = document.querySelector('.gh-death button'), shown = btn && !document.querySelector('.gh-death').hidden;
      if (shown) { btn.click(); bot.path = null; bot.state = 'go'; }
      return;
    }
    // engagement bookkeeping: a mob that is fought must die within its time budget
    for (const [m, e] of bot.engaged) {
      if (m.dead) { if (m.boss && bot.bossStart != null && bot.bossTtk == null) bot.bossTtk = g.time - bot.bossStart; bot.engaged.delete(m); continue; }
      if (m.removed) { bot.engaged.delete(m); continue; }
      if (e.hp !== m.hp) { e.hp = m.hp; e.lastDmg = g.time; }
      if (g.time - e.lastDmg > 30) { bot.fail = `stuck mob: ${m.type.id} not damaged for 30 s`; return; }
      if (g.time - e.t > (m.boss ? 360 : 120)) { bot.fail = `stuck mob: ${m.type.id} not killed within ${m.boss ? 360 : 120} s`; return; }
    }
    const encId = route[bot.leg], enc = ENC[encId];
    const es = sys.encounterState.get(encId);
    const encMobs = es?.active ? es.mobs.filter(m => !m.dead && !m.removed) : [];
    // target: the current encounter's mobs once there, otherwise anything hostile within 18 m
    let tgt = null, bd = Infinity;
    for (const m of live()) {
      const d = dist(m), mine = encMobs.includes(m) && Math.hypot(enc.x - P.x, enc.y - P.y) < enc.r + 25;
      if (m.boss && encId !== 'boss-market' && !hostile(m)) continue;
      if ((mine || (hostile(m) && d < 18)) && d < bd) { bd = d; tgt = m; }
    }
    if (tgt) {
      if (!bot.engaged.has(tgt)) bot.engaged.set(tgt, { t: g.time, hp: tgt.hp, lastDmg: g.time });
      const e = bot.engaged.get(tgt);
      P.yaw = Math.atan2(-(tgt.x - P.x), tgt.y - P.y);
      const cast = castAt(tgt);
      const want = tgt.boss ? 9 : 7;
      if (!cast && (bd > want + 3 || g.time - e.lastDmg > 6)) {   // close in (or find a line of sight) along a path
        if (!bot.goal || Math.hypot(bot.goal.x - tgt.x, bot.goal.y - tgt.y) > 3) setGoal(tgt.x, tgt.y, Math.max(2, want - 3));
        steer(dt);
      } else bot.path = null, bot.goal = null;
      return;
    }
    // loot: walk over recent kill spots (drops sit within 0.8 m of the corpse)
    const spot = ev.kills.find(k => !k.looted);
    if (spot) {
      if (!bot.goal || bot.goal.loot !== spot) { setGoal(spot.x, spot.y, 0.4); bot.goal.loot = spot; spot.tries = (spot.tries || 0) + 1; }
      if (steer(dt) || g.time - spot.t > 40) { spot.looted = true; bot.goal = null; }
      return;
    }
    // travel along the route
    if (!enc) { bot.done = true; return; }
    const dEnc = Math.hypot(enc.x - P.x, enc.y - P.y);
    const cleared = es?.active && es.mobs.length && es.mobs.every(m => m.dead);
    if (cleared && dEnc < enc.r + 25) { bot.leg++; bot.goal = null; bot.path = null; bot.noSpawnT = 0; return; }
    if (dEnc < Math.max(4, enc.r * 0.5)) {   // arrived but nothing to fight: wait for the spawn, but not forever
      bot.noSpawnT += dt; if (bot.noSpawnT > 30) bot.fail = `encounter ${encId} never spawned`;
      if (es?.active && encMobs.length) setGoal(encMobs[0].x, encMobs[0].y, 6), steer(dt);
      return;
    }
    if (!bot.goal || bot.goal.enc !== encId) { setGoal(enc.x, enc.y, Math.max(3, enc.r * 0.4)); bot.goal.enc = encId; }
    blinkForward();
    steer(dt);
  };
  bot.chunk = function (gameS = 6, wallMs = 4000) {
    const t0 = performance.now(); let n = 0;
    try {
      while (n * DT < gameS && performance.now() - t0 < wallMs && !bot.done && !bot.fail) { bot.step(DT); P.update(DT); g.update(DT); n++; }
    } catch (e) { bot.fail = 'bot exception: ' + e.message; }
    P.keys.clear();
    return { t: +(g.time - bot.t0).toFixed(1), leg: bot.leg, done: bot.done, fail: bot.fail, hp: Math.round(g.stats.hp), lvl: g.stats.level,
      mobs: g.mobs.filter(m => !m.dead).length, x: +P.x.toFixed(1), y: +P.y.toFixed(1) };
  };
  return true;
}

const classResults = {}, runs = [];
let pageErrorsTotal = 0;
try {
  const ctx0 = await browser.createBrowserContext();
  const probe = await ctx0.newPage();
  await probe.goto(URL0, { waitUntil: 'domcontentloaded' });
  await probe.waitForFunction('window.__walkReady === true', { timeout: 120000 });
  await probe.waitForFunction('window.__game && window.__game.caster && window.__game.mobSystem && window.__game.items', { timeout: 30000 });
  const classData = await probe.evaluate(() => Object.fromEntries(Object.entries(window.__game.caster.classes).map(([id, c]) => [id, {
    spells: c.spells.length, movement: c.spells.some(s => s.kind === 'blink'), ultimate: c.spells.some(s => s.ult),
    talentChoices: (c.talents || []).reduce((n, t) => n + t.length, 0), talentTiers: (c.talents || []).length }])));
  await ctx0.close();
  log('classes', JSON.stringify(classData));
  await Promise.all(Object.keys(classData).map(async cls => {
    const res = classResults[cls] = { ...classData[cls], runs: [] };
    const ctx = await browser.createBrowserContext();   // fresh localStorage per class
    const page = await ctx.newPage();
    const errors = [];
    page.on('pageerror', e => errors.push('pageerror: ' + (e.stack || e.message).split('\n').slice(0, 2).join(' | ')));
    page.on('console', m => { const t = m.text(); if (m.type() === 'error' && !/404|Failed to load resource/.test(t)) errors.push(t);
      if (m.type() === 'warning' && /^\[(game|classes|items|mobs)\]/.test(t)) errors.push(t); });
    for (let r = 0, retried = 0; r < RUNS; r++) {
      const e0 = errors.length, w0 = Date.now();
      let rec = { cls, run: r };
      try {
        await page.evaluate(() => { try { localStorage.clear(); } catch {} });
        await page.goto(URL0, { waitUntil: 'domcontentloaded' });
        await page.waitForFunction('window.__walkReady === true', { timeout: 120000 });
        await page.waitForFunction('window.__game && window.__game.caster && window.__game.mobSystem && window.__game.items', { timeout: 120000 });
        await page.evaluate(c => { const g = window.__game; g.caster.setClass(c); g.save.cls = c; g.persist(); g.paused = false; }, cls);
        // wait for the tiles along the route to stream in around the start
        await page.evaluate(() => window.__player.teleport(-108.1, 93.97));
        await page.waitForFunction('!window.__player.pendingPlace && window.__player.settled(160)', { timeout: 120000, polling: 500 });
        await page.evaluate(installBot, ROUTE, r);
        let st;
        for (let k = 0; k < 400; k++) {
          st = await page.evaluate(() => window.__bot.chunk(6, 4000));
          if (st.done || st.fail || errors.length > e0) break;
          if (k % 10 === 9) log(cls, r, JSON.stringify(st));
        }
        const ev = await page.evaluate(() => { const b = window.__bot; b.dispose(); const e = b.ev;
          return { bossTtk: b.bossTtk, kills: e.kills.length, bossKilled: e.kills.some(k => k.boss), pickups: e.pickups, equips: e.equips,
            deaths: e.deaths, casts: e.casts, talents: e.talents, equipped: Object.keys(window.__game.items.equipped).length }; });
        const perr = errors.slice(e0);
        rec = { ...rec, ...ev, gameS: st.t, fail: st.fail || (perr.length ? 'page error: ' + perr[0] : null) || (!st.done ? 'not finished' : null) || (!ev.bossKilled ? 'boss not killed' : null) };
      } catch (e) {
        rec.fail = 'harness: ' + e.message;
        // a page that did not load in time under CPU contention is a harness problem, not a game failure: retry once
        if (!retried++ && !/bot|stuck|softlock/.test(e.message)) { log(cls, r, 'harness retry:', e.message); r--; continue; }
      }
      retried = 0;
      rec.pass = !rec.fail; rec.wallS = +((Date.now() - w0) / 1000).toFixed(0);
      pageErrorsTotal += errors.length - e0;
      res.runs.push(rec); runs.push(rec);
      log(cls, r, rec.pass ? 'PASS' : 'FAIL ' + rec.fail, `boss ${rec.bossTtk?.toFixed?.(1)}s game ${rec.gameS}s wall ${rec.wallS}s kills ${rec.kills} pickups ${rec.pickups} deaths ${rec.deaths}`);
    }
    await ctx.close();
  }));
} catch (e) { log('fatal', e.stack || e.message); }
finally { await browser.close(); server.close(); }

const out = { classes: {} };
const meds = [];
for (const [cls, r] of Object.entries(classResults)) {
  const passN = r.runs.filter(x => x.pass).length;
  const dataOk = r.spells >= 6 && r.movement && r.ultimate && r.talentChoices >= 3;
  const ttk = median(r.runs.filter(x => x.pass && x.bossTtk != null).map(x => x.bossTtk));
  if (ttk != null) meds.push(ttk);
  out.classes[cls] = { pass: `${passN}/${r.runs.length}`, data_ok: dataOk, playable: dataOk && passN > 0 && passN >= r.runs.length / 2,
    boss_ttk_median_s: ttk == null ? null : +ttk.toFixed(1), fails: [...new Set(r.runs.filter(x => !x.pass).map(x => x.fail))] };
}
const all = median(meds);
const result = {
  playable_classes: Object.values(out.classes).filter(c => c.playable).length,
  playtest_pass_pct: runs.length ? +(100 * runs.filter(x => x.pass).length / runs.length).toFixed(1) : 0,
  boss_ttk_median_s: all == null ? null : +all.toFixed(1),
  boss_ttk_spread_pct: all ? +(100 * Math.max(...meds.map(m => Math.abs(m - all))) / all).toFixed(1) : null,
  runs_total: runs.length, page_errors: pageErrorsTotal, wall_s: +((Date.now() - T0) / 1000).toFixed(0),
  ...out,
};
console.log(JSON.stringify(result));
process.exit(runs.length && runs.every(x => x.pass) ? 0 : 1);
