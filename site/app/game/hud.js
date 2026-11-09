// Game HUD (session 40): HP/mana/XP bars, spell bar with cooldown sweeps, floating damage numbers, crosshair,
// low-HP vignette, hit flash, death screen, class select (first start) and the talent overlay (T).
// Plain DOM under #game-hud; everything is removed on dispose and hidden by body.explore.
import * as sfx from './sfx.js';

const SPAWN = [-108.1, 93.97];
const TYPE_COLOR = { fire: '#ffb060', storm: '#bfe6ff', stone: '#e8cf9a', hex: '#d9a0ff', physical: '#ffffff' };

export function install(game) {
  const THREE = game.THREE, el = (tag, cls, parent, html) => { const e = document.createElement(tag); if (cls) e.className = cls; if (html != null) e.innerHTML = html; parent?.appendChild(e); return e; };
  const root = el('div', null, document.body); root.id = 'game-hud';
  const offs = [];
  const listen = (t, ev, fn) => { t.addEventListener(ev, fn); offs.push(() => t.removeEventListener(ev, fn)); };

  // ---- static parts
  el('div', 'gh-crosshair', root);
  const vignette = el('div', 'gh-vignette', root), flash = el('div', 'gh-flash', root);
  const bars = el('div', 'gh-bars', root);
  const bar = (cls, label) => { const b = el('div', 'gh-bar ' + cls, bars); const f = el('div', 'gh-fill', b); const t = el('span', 'gh-txt', b, label); return { f, t }; };
  const hpB = bar('gh-hp', ''), shB = { f: el('div', 'gh-shield', hpB.f.parentNode) }, mnB = bar('gh-mana', ''), xpB = bar('gh-xp', '');
  const spellbar = el('div', 'gh-spells', root);
  const slots = [];
  for (let i = 0; i < 6; i++) {
    const s = el('div', 'gh-slot', spellbar);
    slots.push({ s, glyph: el('div', 'gh-glyph', s), sweep: el('div', 'gh-sweep', s), cdt: el('div', 'gh-cdt', s), key: el('div', 'gh-key', s, String(i + 1)), name: '' });
  }
  const clsTag = el('div', 'gh-cls', root);
  const toasts = el('div', 'gh-toasts', root);
  const nums = el('div', 'gh-nums', root);

  // ---- toast
  // session 46: toasts and loot toasts live on the game clock (not setTimeout / CSS animations), so a stepped or
  // hitching sim still shows them for their full duration and a screenshot never catches one mid fade-in.
  const timed = [];   // {t, at, until, slide}
  const gameNow = () => game.time ?? performance.now() / 1000;
  function track(t, s, slide = 0) { const now = gameNow(); timed.push({ t, at: now, until: now + s, slide }); }
  offs.push(game.on('tick', () => { const now = gameNow();
    for (let i = timed.length - 1; i >= 0; i--) { const o = timed[i], left = o.until - now, age = now - o.at;
      if (left <= 0 || !o.t.isConnected || age < -1) { o.t.remove(); timed.splice(i, 1); continue; }
      const op = Math.min(1, left / 0.5), sl = o.slide ? Math.max(0, 1 - age / 0.15) * o.slide : 0;
      o.t.style.opacity = op.toFixed(2); o.t.style.transform = sl || op < 1 ? `translateX(${(sl + (1 - op) * 30).toFixed(0)}px)` : ''; } }));
  function toast(text, ms = 2200) {
    const t = el('div', 'gh-toast', toasts); t.textContent = text;
    track(t, Math.min(2.2, Math.max(1.4, ms / 1000)));   // session 48: brief (was >= 3 s), 3 at most
    while (toasts.children.length > 3) toasts.firstChild.remove();
    return t;
  }
  // loot toast: rarity tag, item name in its rarity colour, slot note and an effect line; lingers 4-6 s of game time
  const lootBox = el('div', 'gh-loots', root);
  function loot(name, rarity, color, note = '', effect = '') {
    const big = rarity === 'epic' || rarity === 'legendary';
    const t = el('div', 'gh-loot' + (big ? ' big' : ''), lootBox);
    t.style.setProperty('--rc', color);
    const head = el('div', 'gh-loot-h', t);
    el('span', 'gh-loot-r', head).textContent = rarity; el('span', 'gh-loot-n', head).textContent = name;
    if (note) el('span', 'gh-loot-d', head).textContent = note;
    if (effect) el('div', 'gh-loot-e', t).textContent = effect.length > 60 ? effect.slice(0, 58) + '…' : effect;
    track(t, big ? 3.2 : 2.4, 0);   // session 48: brief side-panel toasts (were 4.5-6 s) so they never sit over a fight
    while (lootBox.children.length > 2) lootBox.firstChild.remove();
    return t;
  }
  const css = el('style', null, document.head);
  css.textContent = `#game-hud .gh-loots{position:absolute;right:14px;top:58%;display:flex;flex-direction:column;align-items:flex-end;gap:6px;pointer-events:none}
#game-hud .gh-loot{--rc:#ccc;display:flex;flex-direction:column;align-items:flex-end;gap:3px;max-width:240px;padding:3px 9px;background:linear-gradient(90deg,rgba(10,10,16,.45),rgba(10,10,16,.8));border-right:3px solid var(--rc);border-radius:4px 2px 2px 4px;box-shadow:inset -24px 0 24px -20px var(--rc);font:700 12px/1.2 system-ui,sans-serif;color:var(--rc);text-shadow:0 0 4px rgba(0,0,0,.9)}
#game-hud .gh-loot-h{display:flex;align-items:baseline;gap:8px}
#game-hud .gh-loot-e{font:400 10px/1.2 system-ui,sans-serif;color:#d8d8e4;text-shadow:none;text-align:right}
#game-hud .gh-loot.big{font-size:14px;box-shadow:0 0 10px -2px var(--rc),inset -30px 0 30px -20px var(--rc);border-right-width:4px}
#game-hud .gh-toasts{left:18px;top:34%;transform:none;align-items:flex-start}
#game-hud .gh-toast{font-size:12px;padding:3px 9px;background:rgba(0,0,0,.45)}
#game-hud .gh-num{font:900 24px/1 system-ui,sans-serif;letter-spacing:-.02em;-webkit-text-stroke:1px rgba(0,0,0,.85);text-shadow:0 2px 0 #000,0 0 6px rgba(0,0,0,.8)}
#game-hud .gh-num.big{font-size:30px}
#game-hud .gh-num.crit{font-size:40px;color:#ffe14a !important;-webkit-text-stroke:1.5px #5a1800;text-shadow:0 0 10px #ff7a00,0 3px 0 #3a1000}
#game-hud .gh-num.crit::before{content:'CRIT ';font-size:15px;letter-spacing:.08em;vertical-align:middle;color:#fff6c8}
#game-hud .gh-num.taken{font-size:20px;color:#ff5050 !important}
#game-hud .gh-loot-r{font:500 10px/1 system-ui,sans-serif;text-transform:uppercase;letter-spacing:.12em;opacity:.8}
#game-hud .gh-loot-d{font:400 11px/1 system-ui,sans-serif;color:#aab}
#game-hud .gh-loot.out{opacity:0;transform:translateX(30px)}
@keyframes gh-loot-in{from{opacity:0;transform:translateX(40px) scale(.9)}to{opacity:1;transform:none}}
body.explore #game-hud .gh-loots{display:none}`;
  offs.push(() => css.remove());

  // ---- spell bar content
  function fillSpells() {
    const c = game.caster; if (!c) return;
    const def = c.classes[c.cls];
    clsTag.textContent = def ? `${def.name} · Lv ${game.stats.level}` : '';
    clsTag.style.color = def?.color || '';
    c.spells.forEach((sp, i) => {
      const s = slots[i]; s.glyph.textContent = sp.glyph; s.s.title = `${sp.name} (${sp.mana} mana, ${sp.cd.toFixed(1)} s)${sp.ult ? ' · ultimate' : ''}`;
      s.glyph.style.color = '#' + sp.color.toString(16).padStart(6, '0'); s.s.classList.toggle('ult', !!sp.ult);
    });
  }
  offs.push(game.on('spellsChanged', fillSpells), game.on('levelup', ({ level }) => { toast(`Level ${level}!` + ([2, 4, 6].includes(level) ? ' New talent (T)' : '')); fillSpells(); }));
  offs.push(game.on('cast', ({ slot }) => { const s = slots[slot]; if (s) { s.s.classList.remove('pulse'); void s.s.offsetWidth; s.s.classList.add('pulse'); } }));

  // ---- floating damage numbers (pooled)
  const POOL = 72, pool = [], v = new THREE.Vector3();   // session 48: bigger pool, bigger numbers (CSS above)
  for (let i = 0; i < POOL; i++) { const d = el('div', 'gh-num', nums); d.style.display = 'none'; pool.push({ d, t: 0, life: 0, x: 0, y: 0, z: 0, dx: 0 }); }
  let pi = 0;
  // ---- per-hit feedback: impact flash + sparks at the hit point, an impact sound on every hit, hit-stop on big ones
  sfx.setClock(() => game.time); offs.push(() => sfx.setClock(null));
  const SPARK = { fire: 0xff8a30, storm: 0xa8dcff, stone: 0xe0b878, hex: 0xc070ff, physical: 0xfff0d8 };
  offs.push(game.on('hit', ({ target, amount, crit, type, noProc }) => {
    if (!target || target === game.player || amount == null || typeof target.hp !== 'number') return;
    const big = crit || amount >= 0.2 * (target.maxHp || 1e9) || amount >= 60;
    const p = game.player, dx = p.x - target.x, dy = p.y - target.y, L = Math.hypot(dx, dy) || 1, r = (target.radius ?? 0.5) * 0.9;
    const h = (target.height ?? 1.6) * 0.55;
    game.vfx?.impact?.(target.x + dx / L * r, target.y + dy / L * r, (target.z ?? p.z) + h, SPARK[type] ?? SPARK.physical, noProc ? 0.6 : big ? 2 : 1, dx, dy);
    const pitch = 0.85 + Math.random() * 0.3;
    sfx.play('hit_' + (SPARK[type] ? type : 'physical'), noProc ? 0.45 : 0.8, pitch);
    if (big && !noProc) { sfx.play('crit', 0.7, pitch); game.hitStop?.(crit ? 0.085 : 0.06, 0.05); }
  }));
  offs.push(game.on('kill', ({ mob }) => { if (mob) sfx.play('kill', mob.boss ? 1.2 : 0.6, 0.9 + Math.random() * 0.2); }));
  offs.push(game.on('hit', ({ target, amount, crit, type }) => {
    if (!target || target === game.player || amount == null) return;
    const n = pool[pi]; pi = (pi + 1) % POOL;
    // session 48: numbers fan out (no stacking on one spot), linger longer and pop; crits get a CRIT tag + gold
    const big = !crit && (amount >= 0.12 * (target.maxHp || 1e9) || amount >= 40);
    n.x = target.x + (Math.random() - 0.5) * 0.6; n.y = target.y + (Math.random() - 0.5) * 0.6; n.z = target.z + (target.height ?? 1.6) * (0.75 + Math.random() * 0.4) + 0.2;
    n.t = 0; n.life = crit ? 1.5 : 1.15; n.dx = (Math.random() - 0.5) * 90; n.pop = crit ? 1.1 : big ? 0.7 : 0.45;
    n.d.textContent = Math.round(amount); n.d.className = 'gh-num' + (crit ? ' crit' : big ? ' big' : '');
    n.d.style.color = TYPE_COLOR[type] || '#fff'; n.d.style.display = '';
  }));
  function updateNums(dt) {
    const cam = game.camera, W = innerWidth, H = innerHeight;
    for (const n of pool) {
      if (n.life <= 0) continue;
      n.t += dt;
      if (n.t >= n.life) { n.life = 0; n.d.style.display = 'none'; continue; }
      v.set(n.x, n.z + n.t * 1.2, -n.y).project(cam);
      if (v.z > 1 || v.z < -1) { n.d.style.opacity = 0; continue; }
      const k = n.t / n.life;
      n.d.style.opacity = k < 0.7 ? 1 : (1 - k) / 0.3;
      n.d.style.transform = `translate(${(v.x * 0.5 + 0.5) * W + n.dx * Math.sqrt(k)}px, ${(-v.y * 0.5 + 0.5) * H}px) translate(-50%,-50%) scale(${1 + (1 - Math.min(1, n.t * 7)) * (n.pop ?? 0.5)})`;
    }
  }

  // ---- hit flash, death
  offs.push(game.on('playerHit', ({ amount }) => {
    flash.classList.remove('on'); void flash.offsetWidth; flash.classList.add(amount > 0 ? 'on' : 'on-shield');
    setTimeout(() => flash.classList.remove('on', 'on-shield'), 180);
    if (amount > 0) sfx.play('hurt');
  }));
  const death = el('div', 'gh-overlay gh-death', root, '<h1>You have fallen</h1><p>The city keeps its secrets a while longer.</p>');
  death.hidden = true;
  const rise = el('button', 'gh-btn', death, 'Rise again');
  rise.onclick = respawn;
  function respawn() {
    const s = game.stats; s.hp = s.maxHp; s.mana = s.maxMana; game.shield = 0;
    game.invulnUntil = game.time + 3; game.paused = false;
    game.player.teleport(SPAWN[0], SPAWN[1]);
    death.hidden = true; toast('You rise again');
    game.emit('respawn', {});
  }
  offs.push(game.on('playerDeath', () => { death.hidden = false; game.paused = true; sfx.play('death'); document.exitPointerLock?.(); }));

  // ---- class select
  const pick = el('div', 'gh-overlay gh-pick', root, '<h1>Choose your path</h1>'); pick.hidden = true;
  const cards = el('div', 'gh-cards', pick);
  function openPick() {
    const c = game.caster; if (!c) return;
    cards.innerHTML = '';
    for (const [id, def] of Object.entries(c.classes)) {
      const card = el('button', 'gh-card', cards, `<h2 style="color:${def.color}">${def.name}</h2><p>${def.blurb}</p><ul>${def.spells.map(s => `<li><b>${s.glyph}</b> ${s.name}${s.ult ? ' <i>(ultimate)</i>' : ''}</li>`).join('')}</ul>`);
      card.onclick = () => { c.setClass(id); game.save.cls = id; game.persist(); pick.hidden = true; game.paused = false; fillSpells(); toast(`You walk the path of the ${def.name}`); sfx.init(); };
    }
    pick.hidden = false; game.paused = true; document.exitPointerLock?.();
  }

  // ---- talents (T)
  const tal = el('div', 'gh-overlay gh-talents', root); tal.hidden = true;
  function drawTalents() {
    const c = game.caster; if (!c) return;
    const def = c.classes[c.cls], lv = game.stats.level;
    tal.innerHTML = `<h1 style="color:${def.color}">${def.name} talents</h1><p>One choice per tier; tiers unlock at levels ${c.talentLevels.join(', ')}. You can change your mind at any time.</p>`;
    c.talents.forEach((tier, t) => {
      const row = el('div', 'gh-tier', tal); const locked = lv < c.talentLevels[t];
      el('div', 'gh-tier-lv', row, `Lv ${c.talentLevels[t]}`);
      tier.forEach((o, k) => {
        const b = el('button', 'gh-talent' + (c.picks[t] === k ? ' on' : '') + (locked ? ' locked' : ''), row, `<b>${o.name}</b><span>${o.desc}</span>`);
        b.disabled = locked; b.onclick = () => { c.pickTalent(t, k); drawTalents(); fillSpells(); };
      });
    });
    el('p', 'gh-hint', tal, 'Press T or Esc to close');
  }
  function toggleTalents(on = tal.hidden) {
    if (!pick.hidden || !death.hidden) return;
    tal.hidden = !on; game.paused = on;
    if (on) { drawTalents(); document.exitPointerLock?.(); }
  }
  listen(window, 'keydown', e => {
    if (e.target instanceof HTMLInputElement || window.__explore) return;
    if (e.code === 'KeyT') toggleTalents();
    else if (e.code === 'Escape' && !tal.hidden) toggleTalents(false);
  });

  offs.push(game.on('ready', () => {
    fillSpells();
    if (!game.save.cls && !new URLSearchParams(location.search).has('nopick')) openPick();
  }));

  // ---- per-frame
  let barT = 0;
  game.add({
    update(dt) {
      updateNums(dt);
      if ((barT -= dt) > 0) return; barT = 1 / 30;
      const s = game.stats;
      hpB.f.style.width = (100 * s.hp / s.maxHp).toFixed(1) + '%'; hpB.t.textContent = `${Math.ceil(s.hp)} / ${s.maxHp}`;
      shB.f.style.width = (100 * Math.min(1, (game.shield || 0) / s.maxHp)).toFixed(1) + '%';
      mnB.f.style.width = (100 * s.mana / s.maxMana).toFixed(1) + '%'; mnB.t.textContent = `${Math.floor(s.mana)} / ${s.maxMana}`;
      const need = game.xpToNext(); xpB.f.style.width = (100 * s.xp / need).toFixed(1) + '%'; xpB.t.textContent = `Lv ${s.level} · ${Math.floor(s.xp)} / ${need} xp`;
      const low = s.hp / s.maxHp; vignette.style.opacity = low < 0.35 ? ((0.35 - low) / 0.35 * (0.75 + 0.25 * Math.sin(game.time * 6))).toFixed(2) : 0;
      const c = game.caster;
      if (c) for (let i = 0; i < 6; i++) {
        const sp = c.spells[i], sl = slots[i]; if (!sp) continue;
        const rem = Math.max(0, sp.readyAt - game.time), f = sp.cdTotal ? rem / sp.cdTotal : 0;
        sl.sweep.style.setProperty('--cd', (f * 360).toFixed(0) + 'deg');
        sl.cdt.textContent = rem > 0.05 ? (rem >= 10 ? rem.toFixed(0) : rem.toFixed(1)) : '';
        sl.s.classList.toggle('nomana', s.mana < sp.mana);
      }
    },
    dispose() { for (const f of offs) f(); root.remove(); },
  });

  game.hud = { toast, loot, openPick, toggleTalents, respawn, root };
}
