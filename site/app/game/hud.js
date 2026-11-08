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
  function toast(text, ms = 2200) {
    const t = el('div', 'gh-toast', toasts); t.textContent = text;
    setTimeout(() => t.classList.add('out'), ms); setTimeout(() => t.remove(), ms + 500);
    while (toasts.children.length > 4) toasts.firstChild.remove();
  }

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
  const POOL = 40, pool = [], v = new THREE.Vector3();
  for (let i = 0; i < POOL; i++) { const d = el('div', 'gh-num', nums); d.style.display = 'none'; pool.push({ d, t: 0, life: 0, x: 0, y: 0, z: 0, dx: 0 }); }
  let pi = 0;
  offs.push(game.on('hit', ({ target, amount, crit, type }) => {
    if (!target || target === game.player || amount == null) return;
    const n = pool[pi]; pi = (pi + 1) % POOL;
    n.x = target.x; n.y = target.y; n.z = target.z + (target.height ?? 1.6) + 0.2; n.t = 0; n.life = crit ? 1.2 : 0.9; n.dx = (Math.random() - 0.5) * 40;
    n.d.textContent = crit ? amount + '!' : amount; n.d.className = 'gh-num' + (crit ? ' crit' : '');
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
      n.d.style.transform = `translate(${(v.x * 0.5 + 0.5) * W + n.dx * k}px, ${(-v.y * 0.5 + 0.5) * H}px) translate(-50%,-50%) scale(${1 + (1 - Math.min(1, n.t * 6)) * 0.6})`;
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

  game.hud = { toast, openPick, toggleTalents, respawn, root };
}
