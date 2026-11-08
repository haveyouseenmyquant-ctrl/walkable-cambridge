// Item definitions (session 40). Every non-starter item has a special effect `fx(c)` that subscribes to game events
// through c.on(...) (auto-unsubscribed on unequip) and a `test(t)` used by window.__itemTest (scripts/test_items.mjs).
// c = effect context: {game, S (item system helpers), on(ev, fn), cleanup(fn)}.  Ids are stable (saved in localStorage).

export const RARITY = {
  common:    { color: '#c8c8c8', hex: 0xc8c8c8, order: 0 },
  uncommon:  { color: '#4fdc5a', hex: 0x4fdc5a, order: 1 },
  rare:      { color: '#3d8bff', hex: 0x3d8bff, order: 2 },
  epic:      { color: '#b04dff', hex: 0xb04dff, order: 3 },
  legendary: { color: '#ffa31a', hex: 0xffa31a, order: 4 },
};
export const SLOTS = ['wand', 'hat', 'robe', 'boots', 'ring', 'amulet', 'broom'];

// starter gear (granted by classes.js): stat-only
const STARTERS = {
  pyromancer: ['Pyromancer', { power: 0.12 }, { maxHp: 10 }, { critChance: 0.03 }],
  stormcaller: ['Stormcaller', { critChance: 0.05 }, { cdr: 0.05 }, { speedMult: 0.05 }],
  warden: ['Warden', { power: 0.05 }, { maxHp: 20 }, { armor: 10 }],
  hexweaver: ['Hexweaver', { power: 0.08 }, { manaRegen: 2 }, { maxMana: 20 }],
};
const defs = {};
for (const [k, [name, ws, hs, rs]] of Object.entries(STARTERS)) {
  defs[`starter_${k}_staff`] = { name: `${name}'s Training Staff`, slot: 'wand', rarity: 'common', starter: true, stats: ws };
  defs[`starter_${k}_hat`] = { name: `${name}'s Fresher Hat`, slot: 'hat', rarity: 'common', starter: true, stats: hs };
  defs[`starter_${k}_robe`] = { name: `${name}'s Matriculation Robe`, slot: 'robe', rarity: 'common', starter: true, stats: rs };
}

const isHit = (c, e) => c.S.isMobHit(e);

const U = {
  // ---------------- wands
  wand_inkwell: { name: 'Inkwell Quill-Wand', slot: 'wand', rarity: 'common', stats: { power: 0.04 },
    desc: 'Kills restore 15 mana.',
    fx(c) { c.on('kill', () => { c.game.stats.mana = Math.min(c.game.stats.maxMana, c.game.stats.mana + 15); c.S.fx.burst(c.S.pp(1.2), 0x4a7dff, 14, 2.5, 0.7); }); },
    test(t) { const m = t.mob(3, 0); t.game.stats.mana = 0; t.game.emit('kill', { mob: m }); return [t.game.stats.mana >= 15, `mana ${t.game.stats.mana}`]; } },
  wand_leechwick: { name: 'Leechwick Wand', slot: 'wand', rarity: 'uncommon', stats: { power: 0.06 },
    desc: 'Hits drain life: heal 10% of damage dealt (min 1).',
    fx(c) { c.on('hit', e => { if (!isHit(c, e)) return; c.game.heal(Math.max(1, e.amount * 0.1)); c.S.fx.stream(c.S.mp(e.target), c.S.pp(1.1), 0x40ff70, 8); }); },
    test(t) { const m = t.mob(3, 0); t.game.stats.hp = 50; t.hit(m, 40); return [t.game.stats.hp > 50, `hp ${t.game.stats.hp.toFixed(1)}`]; } },
  wand_bonfire: { name: 'Bonfire Night Rod', slot: 'wand', rarity: 'rare', stats: { power: 0.08 },
    desc: 'Slain foes explode, dealing 25 fire damage within 4 m.',
    fx(c) { c.on('kill', e => { const m = e.mob; if (!m) return; c.S.fx.ring(m.x, m.y, (m.z ?? c.game.pz) + 0.2, 0xff6a1a, 4, 0.5); c.S.fx.burst(c.S.mp(m), 0xff8a2a, 40, 6, 0.8);
      c.S.aoe(m.x, m.y, 4, 25, 'fire', m); }); },
    test(t) { const a = t.mob(3, 0), b = t.mob(4.5, 1); t.game.emit('kill', { mob: a }); return [b.hp < b.maxHp, `neighbour hp ${b.hp}`]; } },
  wand_puntpole: { name: 'Punt-Pole Staff', slot: 'wand', rarity: 'rare', stats: { power: 0.05, armor: 5 },
    desc: '20% chance on hit to pole-vault a shockwave that stuns the target for 1.2 s.',
    fx(c) { c.on('hit', e => { if (!isHit(c, e) || !c.S.proc(0.2)) return; e.target.stunUntil = c.game.time + 1.2; c.S.fx.ring(e.target.x, e.target.y, (e.target.z ?? 0) + 0.1, 0xfff2a0, 1.6, 0.5); c.S.fx.burst(c.S.mp(e.target, 1.8), 0xfff2a0, 16, 2, 1.2); }); },
    test(t) { const m = t.mob(3, 0); t.force(); t.hit(m, 10); return [m.stunUntil > t.game.time, `stunUntil ${m.stunUntil}`]; } },
  wand_camrod: { name: 'Cam Lightning Rod', slot: 'wand', rarity: 'epic', stats: { power: 0.1, critChance: 0.04 },
    desc: 'Critical hits arc chain lightning to up to 3 nearby foes (60% damage).',
    fx(c) { c.on('hit', e => { if (!isHit(c, e) || !e.crit) return; let from = e.target; const hitSet = new Set([from]);
      for (let i = 0; i < 3; i++) { let best = null, bd = 8; for (const m of c.game.mobs) { if (m.dead || hitSet.has(m)) continue; const d = Math.hypot(m.x - from.x, m.y - from.y); if (d < bd) { bd = d; best = m; } }
        if (!best) break; c.S.fx.bolt(c.S.mp(from), c.S.mp(best), 0x9fdcff); hitSet.add(best);
        c.game.damageMob(best, Math.max(1, e.amount * 0.6 / (c.game.stats.power || 1)), { type: 'storm', crit: false, noProc: true }); from = best; } }); },
    test(t) { const a = t.mob(3, 0), b = t.mob(5, 0), d = t.mob(6, 2); t.hit(a, 30, true); return [b.hp < b.maxHp && d.hp < d.maxHp, `b ${b.hp} d ${d.hp}`]; } },
  wand_eaglewick: { name: 'Wick of the Eagle', slot: 'wand', rarity: 'legendary', stats: { power: 0.15, critChance: 0.05 },
    desc: '30% chance on hit to ignite the target: 8 fire damage per second for 4 s.',
    fx(c) { c.on('hit', e => { if (!isHit(c, e) || !c.S.proc(0.3)) return; c.S.dot(e.target, 8, 4, 0xff5a10); }); },
    test(t) { const m = t.mob(3, 0); t.force(); t.hit(m, 10); t.ticks(15); return [m.hp < m.maxHp, `hp ${m.hp}`]; } },

  // ---------------- hats
  hat_choral: { name: "Choral Scholar's Cap", slot: 'hat', rarity: 'common', stats: { maxMana: 10 },
    desc: 'Casting has a 20% chance to refund 12 mana.',
    fx(c) { c.on('cast', () => { if (!c.S.proc(0.2)) return; c.game.stats.mana = Math.min(c.game.stats.maxMana, c.game.stats.mana + 12); c.S.fx.burst(c.S.pp(1.9), 0x6fa8ff, 18, 1.5, 0.8); }); },
    test(t) { t.force(); t.game.stats.mana = 0; t.game.emit('cast', { spell: 'test', caster: t.game.player }); return [t.game.stats.mana >= 12, `mana ${t.game.stats.mana}`]; } },
  hat_thunderhead: { name: 'Thunderhead Hood', slot: 'hat', rarity: 'uncommon', stats: { critChance: 0.02 },
    desc: 'Every jump releases a static nova: 10 storm damage within 3.5 m.',
    fx(c) { c.on('jump', () => { const p = c.game.player; c.S.fx.ring(p.x, p.y, p.z + 0.1, 0x9fdcff, 3.5, 0.35); c.S.fx.burst(c.S.pp(0.5), 0xbfe8ff, 20, 5, 0.4); c.S.aoe(p.x, p.y, 3.5, 10, 'storm'); }); },
    test(t) { const m = t.mob(2, 0); t.game.emit('jump', {}); return [m.hp < m.maxHp, `hp ${m.hp}`]; } },
  hat_mortarboard: { name: 'Mortarboard of Insight', slot: 'hat', rarity: 'rare', stats: { critMult: 0.1 },
    desc: 'Critical hits grant +4% crit chance for 5 s, stacking 5 times.',
    fx(c) { let stacks = 0, until = 0; const g = c.game;
      const set = n => { g.stats.critChance += (n - stacks) * 0.04; stacks = n; };
      c.on('hit', e => { if (!isHit(c, e) || !e.crit) return; set(Math.min(5, stacks + 1)); until = c.S.t + 5; c.S.fx.burst(c.S.pp(2), 0xffe070, 6 + stacks * 3, 1.2, 0.6); });
      c.on('tick', () => { if (stacks && c.S.t > until) set(0); });
      c.cleanup(() => set(0)); },
    test(t) { const m = t.mob(3, 0), c0 = t.game.stats.critChance; t.hit(m, 10, true); return [t.game.stats.critChance > c0, `crit ${c0.toFixed(2)} -> ${t.game.stats.critChance.toFixed(2)}`]; } },
  hat_proctor: { name: "Proctor's Bicorne", slot: 'hat', rarity: 'legendary', stats: { power: 0.08, maxHp: 15 },
    desc: 'Summons a will-o\'-wisp familiar that orbits you and zaps foes within 12 m (6 damage every 1.1 s).',
    fx(c) { const g = c.game, T = g.THREE;
      const wisp = new T.Group(); wisp.name = 'familiar';
      const core = new T.Mesh(new T.IcosahedronGeometry(0.16, 1), new T.MeshBasicMaterial({ color: 0xbfffe0 }));
      const halo = new T.Mesh(new T.SphereGeometry(0.38, 12, 8), new T.MeshBasicMaterial({ color: 0x40ffb0, transparent: true, opacity: 0.35, blending: T.AdditiveBlending, depthWrite: false }));
      wisp.add(core, halo); g.root.add(wisp); c.S.familiar = wisp;
      let cd = 0, a = 0;
      c.on('tick', ({ dt }) => { const p = g.player; a += dt * 1.8; const fx = p.x + Math.cos(a) * 1.2, fy = p.y + Math.sin(a) * 1.2, fz = p.z + 2 + Math.sin(a * 2.3) * 0.2;
        wisp.position.set(fx, fz, -fy); halo.scale.setScalar(1 + Math.sin(c.S.t * 6) * 0.15);
        if (Math.random() < dt * 8) c.S.fx.burst(wisp.position, 0x40ffb0, 1, 0.3, 0.6);
        if ((cd -= dt) > 0) return; const m = g.nearestMob(fx, fy, 12); if (!m) return; cd = 1.1;
        c.S.fx.bolt(wisp.position, c.S.mp(m), 0x60ffc0); g.damageMob(m, 6, { type: 'hex', crit: false, noProc: true, source: 'familiar' }); });
      c.cleanup(() => { g.root.remove(wisp); core.geometry.dispose(); halo.geometry.dispose(); core.material.dispose(); halo.material.dispose(); c.S.familiar = null; }); },
    test(t) { const m = t.mob(5, 0); t.ticks(25); return [!!t.S.familiar?.parent && m.hp < m.maxHp, `familiar ${!!t.S.familiar} hp ${m.hp}`]; } },

  // ---------------- robes
  robe_botanic: { name: 'Botanic Garden Vestment', slot: 'robe', rarity: 'common', stats: { hpRegen: 0.5 },
    desc: 'Kills heal you for 6.',
    fx(c) { c.on('kill', () => { c.game.heal(6); c.S.fx.burst(c.S.pp(1), 0x6cff4a, 18, 1.8, 0.9); }); },
    test(t) { const m = t.mob(3, 0); t.game.stats.hp = 40; t.game.emit('kill', { mob: m }); return [t.game.stats.hp > 40, `hp ${t.game.stats.hp}`]; } },
  robe_bramble: { name: 'Bramble-Weave Robe', slot: 'robe', rarity: 'uncommon', stats: { armor: 6 },
    desc: 'Thorns: attackers take 60% of the damage they deal (min 4).',
    fx(c) { c.on('playerHit', e => { const g = c.game; let m = e.source && typeof e.source === 'object' && 'hp' in e.source ? e.source : g.nearestMob(g.px, g.py, 6); if (!m || m.dead) return;
      c.S.fx.stream(c.S.pp(1), c.S.mp(m), 0x7aff3a, 10); g.damageMob(m, Math.max(4, (e.amount + (e.absorbed || 0)) * 0.6) / (g.stats.power || 1), { type: 'physical', crit: false, noProc: true }); }); },
    test(t) { const m = t.mob(2, 0); t.game.emit('playerHit', { amount: 10, source: m }); return [m.hp < m.maxHp, `attacker hp ${m.hp}`]; } },
  robe_gownsman: { name: "Gownsman's Aegis", slot: 'robe', rarity: 'rare', stats: { maxHp: 15 },
    desc: 'Dashing grants a 20-point arcane shield (max 40, 3 s cooldown).',
    fx(c) { let ready = 0; c.on('dash', () => { if (c.S.t < ready) return; ready = c.S.t + 3; const g = c.game; g.shield = Math.min(40, (g.shield || 0) + 20); c.S.fx.burst(c.S.pp(1), 0x7ac8ff, 24, 2.5, 0.5); }); },
    test(t) { t.game.shield = 0; t.game.emit('dash', {}); return [t.game.shield > 0, `shield ${t.game.shield}`]; } },
  robe_fenfrost: { name: 'Fen-Frost Gown', slot: 'robe', rarity: 'epic', stats: { maxHp: 20, armor: 5 },
    desc: 'Dropping below 30% health unleashes a frost nova: 15 damage and 60% slow for 3 s within 6 m (20 s cooldown).',
    fx(c) { let ready = 0; c.on('playerHit', () => { const g = c.game; if (g.stats.hp > g.stats.maxHp * 0.3 || g.stats.hp <= 0 || c.S.t < ready) return; ready = c.S.t + 20; const p = g.player;
      c.S.fx.ring(p.x, p.y, p.z + 0.15, 0xaef0ff, 6, 0.7); c.S.fx.burst(c.S.pp(0.6), 0xd8f8ff, 60, 7, 0.9);
      for (const m of g.mobsNear(p.x, p.y, 6)) { m.slowUntil = g.time + 3; m.slowMult = 0.4; } c.S.aoe(p.x, p.y, 6, 15, 'frost'); }); },
    test(t) { const m = t.mob(3, 0); t.game.stats.hp = t.game.stats.maxHp * 0.2; t.game.emit('playerHit', { amount: 5 }); return [m.slowUntil > t.game.time && m.hp < m.maxHp, `slowUntil ${m.slowUntil} hp ${m.hp}`]; } },

  // ---------------- boots
  boots_courier: { name: "Courier's Cobbled Boots", slot: 'boots', rarity: 'uncommon', stats: { speedMult: 0.05 },
    desc: 'Kills grant +35% movement speed for 4 s.',
    fx(c) { let until = -1; c.on('kill', () => { until = c.S.t + 4; c.S.fx.burst(c.S.pp(0.2), 0xfff0a0, 14, 2, 0.5); });
      c.on('tick', ({ dt }) => { if (c.S.t < until) { c.S.boost(0.35, dt); if (Math.random() < dt * 20) c.S.fx.burst(c.S.pp(0.1), 0xfff0a0, 1, 0.5, 0.4); } });
      c.S.courierActive = () => c.S.t < until; },
    test(t) { const m = t.mob(3, 0); t.game.emit('kill', { mob: m }); t.ticks(1); return [t.S.courierActive(), 'speed buff active']; } },
  boots_ember: { name: 'Ember-Tread Boots', slot: 'boots', rarity: 'rare', stats: { power: 0.03 },
    desc: 'Dashing leaves burning ground for 3 s (16 fire damage per second, 2.5 m).',
    fx(c) { c.on('dash', () => { const p = c.game.player; c.S.zone(p.x, p.y, p.z, 2.5, 3, 16, 0xff5a10); }); },
    test(t) { const m = t.mob(0.5, 0); t.game.emit('dash', {}); t.ticks(10); return [m.hp < m.maxHp, `hp ${m.hp}`]; } },
  boots_fenmist: { name: 'Fen-Mist Boots', slot: 'boots', rarity: 'epic', stats: { speedMult: 0.05 },
    desc: 'Press Space in mid-air for a second, misty jump.',
    fx(c) { let used = false; const g = c.game;
      const kd = e => { const p = g.player; if (e.code !== 'Space' || e.repeat || p.flying) return; if (p.grounded) { used = false; return; }
        if (used) return; used = true; p.vz = Math.max(p.vz, 5); c.S.fx.ring(p.x, p.y, p.z, 0xd0f0ff, 1.4, 0.4); c.S.fx.burst(c.S.pp(0), 0xe0f4ff, 26, 2.2, 0.7); };
      c.on('land', () => { used = false; }); addEventListener('keydown', kd); c.cleanup(() => removeEventListener('keydown', kd)); },
    test(t) { const p = t.game.player; p.grounded = false; p.vz = -2; dispatchEvent(new KeyboardEvent('keydown', { code: 'Space' })); const vz = p.vz; dispatchEvent(new KeyboardEvent('keyup', { code: 'Space' })); return [vz > 0, `vz ${vz}`]; } },
  boots_rimestep: { name: 'Rime-Step Sabatons', slot: 'boots', rarity: 'legendary', stats: { armor: 8, speedMult: 0.08 },
    desc: 'Landing sends out a frost shockwave: 12 damage and slow within 4 m.',
    fx(c) { c.on('land', () => { const g = c.game, p = g.player; c.S.fx.ring(p.x, p.y, p.z + 0.1, 0xaef0ff, 4, 0.45); c.S.fx.burst(c.S.pp(0.2), 0xd8f8ff, 30, 4, 0.6);
      for (const m of g.mobsNear(p.x, p.y, 4)) { m.slowUntil = g.time + 2; m.slowMult = 0.5; } c.S.aoe(p.x, p.y, 4, 12, 'frost'); }); },
    test(t) { const m = t.mob(2, 1); t.game.emit('land', {}); return [m.hp < m.maxHp && m.slowUntil > t.game.time, `hp ${m.hp}`]; } },

  // ---------------- rings
  ring_bursar: { name: "Bursar's Band", slot: 'ring', rarity: 'uncommon', stats: { manaRegen: 1 },
    desc: 'Dashing restores 10 mana.',
    fx(c) { c.on('dash', () => { const s = c.game.stats; s.mana = Math.min(s.maxMana, s.mana + 10); c.S.fx.burst(c.S.pp(1), 0x4a7dff, 12, 1.5, 0.5); }); },
    test(t) { t.game.stats.mana = 0; t.game.emit('dash', {}); return [t.game.stats.mana >= 10, `mana ${t.game.stats.mana}`]; } },
  ring_glasshouse: { name: 'Glasshouse Ring', slot: 'ring', rarity: 'rare', stats: { critChance: 0.03 },
    desc: 'Your first hit on an unhurt foe shatters it for +100% bonus damage.',
    fx(c) { c.on('hit', e => { if (!isHit(c, e)) return; const m = e.target; if (m.hp + e.amount < (m.maxHp ?? Infinity)) return;
      c.S.fx.burst(c.S.mp(m), 0xe8fbff, 30, 4, 0.5); c.game.damageMob(m, e.amount / (c.game.stats.power || 1), { type: e.type, crit: false, noProc: true }); }); },
    test(t) { const m = t.mob(3, 0); const d = t.game.damageMob(m, 10, { crit: false }); return [m.hp < m.maxHp - d, `dealt ${d}, hp ${m.hp}`]; } },
  ring_nightporter: { name: 'Signet of the Night Porter', slot: 'ring', rarity: 'epic', stats: { critChance: 0.04 },
    desc: 'Critical hits heal you for 6 and release a swarm of shadow motes.',
    fx(c) { c.on('hit', e => { if (!isHit(c, e) || !e.crit) return; c.game.heal(6); c.S.fx.stream(c.S.mp(e.target), c.S.pp(1.2), 0xff3050, 12); }); },
    test(t) { const m = t.mob(3, 0); t.game.stats.hp = 50; t.hit(m, 10, true); return [t.game.stats.hp > 50, `hp ${t.game.stats.hp}`]; } },
  ring_chapel: { name: 'Echoing Chapel Ring', slot: 'ring', rarity: 'legendary', stats: { power: 0.06, cdr: 0.05 },
    desc: '25% chance on hit for the blow to echo 0.35 s later for full damage.',
    fx(c) { c.on('hit', e => { if (!isHit(c, e) || !c.S.proc(0.25)) return; const m = e.target, amt = e.amount, type = e.type;
      c.S.after(0.35, () => { if (m.dead) return; c.S.fx.ring(m.x, m.y, (m.z ?? 0) + 1, 0xffe8a0, 1.5, 0.4); c.game.damageMob(m, amt / (c.game.stats.power || 1), { type, crit: false, noProc: true }); }); }); },
    test(t) { const m = t.mob(3, 0); t.force(); t.hit(m, 20); t.ticks(6); return [m.hp < m.maxHp, `hp ${m.hp}`]; } },

  // ---------------- amulets
  amu_lodestone: { name: 'Lodestone Pendant', slot: 'amulet', rarity: 'common', stats: { maxHp: 5 },
    desc: 'Loot within 6 m is drawn to you.',
    fx(c) { c.S.magnet = 6; c.cleanup(() => { c.S.magnet = 0; }); },
    test(t) { const p = t.game.player, id = 'ring_bursar', had = t.S.owns(id); t.S.drop(id, p.x + 4, p.y, p.z); t.ticks(30);
      const ok = t.S.owns(id); if (!had) t.S.forget(id); return [ok, ok ? 'pulled + picked up' : 'not picked up']; } },
  amu_kingsparade: { name: "Ward of King's Parade", slot: 'amulet', rarity: 'rare', stats: { armor: 6 },
    desc: 'When struck, 25% chance to become invulnerable for 1.5 s.',
    fx(c) { c.on('playerHit', () => { if (!c.S.proc(0.25)) return; const g = c.game; g.invulnUntil = g.time + 1.5; c.S.fx.ring(g.px, g.py, g.pz + 1, 0xfff6c0, 1.2, 1.5); c.S.fx.burst(c.S.pp(1), 0xfff6c0, 30, 2, 0.8); }); },
    test(t) { t.force(); t.game.emit('playerHit', { amount: 5 }); return [t.game.invulnUntil > t.game.time, `invulnUntil ${t.game.invulnUntil}`]; } },
  amu_phoenix: { name: 'Phoenix-Feather Locket', slot: 'amulet', rarity: 'epic', stats: { maxHp: 10 },
    desc: 'A killing blow instead restores you to 50% health (once every 120 s).',
    fx(c) { let ready = 0; c.on('playerHit', () => { const g = c.game; if (g.stats.hp > 0 || c.S.t < ready) return; ready = c.S.t + 120; g.stats.hp = g.stats.maxHp * 0.5;
      const p = g.player; c.S.fx.ring(p.x, p.y, p.z + 0.1, 0xff8a1a, 5, 0.8); c.S.fx.burst(c.S.pp(1), 0xffb030, 70, 6, 1.1); g.hud?.toast?.('The Phoenix-Feather Locket flares!'); }); },
    test(t) { const g = t.game; g.stats.hp = 3; g.shield = 0; g.invulnUntil = 0; g.damagePlayer(500, 'test'); return [g.stats.hp > 0, `hp ${g.stats.hp}`]; } },
  amu_bell: { name: "Great Bell of St Mary's", slot: 'amulet', rarity: 'legendary', stats: { power: 0.1, maxHp: 10 },
    desc: 'Every 10th hit tolls the bell: a golden shockwave dealing 30 damage within 6 m.',
    fx(c) { let n = 0; c.on('hit', e => { if (!isHit(c, e) || ++n < 10) return; n = 0; const p = c.game.player;
      c.S.fx.ring(p.x, p.y, p.z + 0.3, 0xffd040, 6, 0.6); c.S.fx.ring(p.x, p.y, p.z + 1.2, 0xffe890, 4.5, 0.5); c.S.fx.burst(c.S.pp(1.5), 0xffd040, 40, 6, 0.7); c.S.aoe(p.x, p.y, 6, 30, 'physical'); }); },
    test(t) { const m = t.mob(3, 0); for (let i = 0; i < 10; i++) t.hit(m, 5); return [m.hp < m.maxHp, `hp ${m.hp}`]; } },

  // ---------------- brooms
  broom_feather: { name: 'Feather-Fall Besom', slot: 'broom', rarity: 'uncommon', stats: { hpRegen: 0.3 },
    desc: 'Off the broom, falls are slowed to a gentle glide (max 3.5 m/s descent).',
    fx(c) { c.on('tick', ({ dt }) => { const p = c.game.player; if (p.flying || p.grounded || p.vz >= -3.5) return; p.vz = -3.5; if (Math.random() < dt * 15) c.S.fx.burst(c.S.pp(0), 0xffffff, 1, 0.6, 0.8); }); },
    test(t) { const p = t.game.player; p.grounded = false; p.vz = -10; t.ticks(1); return [p.vz >= -3.5, `vz ${p.vz}`]; } },
  broom_backs: { name: 'Backs Breeze Broom', slot: 'broom', rarity: 'rare', stats: { speedMult: 0.03 },
    desc: 'While flying: +40% speed, trailing wind streaks.',
    fx(c) { c.on('tick', ({ dt }) => { const p = c.game.player; if (!p.flying) return; c.S.boost(0.4, dt, true); if (Math.random() < dt * 25) c.S.fx.burst(c.S.pp(0.8), 0xd8ecff, 1, 0.2, 0.5); }); },
    test(t) { const p = t.game.player; p.mode = 'broom'; p.z += 30; p.vx = 10; p.vy = 0; const x0 = p.x; t.ticks(1); return [p.x > x0 + 0.2, `moved ${(p.x - x0).toFixed(2)} m`]; } },
  broom_comet: { name: 'Comet-Tail Besom', slot: 'broom', rarity: 'epic', stats: { speedMult: 0.05 },
    desc: 'While flying, a comet tail scorches foes you pass within 2.5 m (12 damage, every 0.3 s).',
    fx(c) { let cd = 0; c.on('tick', ({ dt }) => { const g = c.game, p = g.player; if (!p.flying) return; if (Math.random() < dt * 40) c.S.fx.burst(c.S.pp(0.6), 0xffa040, 1, 0.4, 0.7);
      if ((cd -= dt) > 0) return; cd = 0.3; for (const m of g.mobs) { if (m.dead || Math.hypot(m.x - p.x, m.y - p.y) > 2.5 || Math.abs((m.z ?? p.z) - p.z) > 4) continue; c.S.fx.bolt(c.S.pp(0.6), c.S.mp(m), 0xffa040); g.damageMob(m, 12, { type: 'fire', crit: false, noProc: true }); } }); },
    test(t) { const p = t.game.player; p.mode = 'broom'; const m = t.mob(1, 0); t.ticks(8); return [m.hp < m.maxHp, `hp ${m.hp}`]; } },
};
Object.assign(defs, U);
export const ITEMS = defs;
