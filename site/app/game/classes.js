// Player classes and spells (session 40): four original casting classes, six spells each (keys 1-6, left mouse = 1
// while the pointer is locked), a 3-tier talent tree per class and a staff held in first-person view.
// Spells are data (CLASSES) run by a few generic kinds (bolt, beam, cone, nova, zone, blink, shield, summon);
// talents are small functions that edit a fresh copy of the class's spell table, so they really change behaviour.
// Mob status fields written here (mobs.js honours them): slowUntil, stunUntil (game.time seconds), damageTaken (mult).
import * as sfx from './sfx.js';
import { createVfx } from './vfx.js';

export const STARTING_GEAR = {
  pyromancer: ['starter_pyromancer_staff', 'starter_pyromancer_robe'],
  stormcaller: ['starter_stormcaller_staff', 'starter_stormcaller_robe'],
  warden: ['starter_warden_staff', 'starter_warden_robe'],
  hexweaver: ['starter_hexweaver_staff', 'starter_hexweaver_robe'],
};

export const CLASSES = {
  pyromancer: {
    name: 'Pyromancer', color: '#ff7a2a', blurb: 'Fire and burst damage. Burns linger, explosions stack.',
    spells: [
      { id: 'ember_bolt', name: 'Ember Bolt', glyph: '✦', kind: 'bolt', type: 'fire', mana: 5, cd: 0.45, dmg: 22, speed: 48, range: 60, splash: 1.2, color: 0xff7a2a, sfx: 'ember', look: 'ember' },
      { id: 'cinder_spray', name: 'Cinder Spray', glyph: '≋', kind: 'cone', type: 'fire', mana: 14, cd: 3, dmg: 14, range: 9, angle: 0.6, burn: { dps: 6, dur: 3 }, color: 0xffa040, sfx: 'spray', look: 'spray' },
      { id: 'fireburst', name: 'Fireburst Orb', glyph: '◉', kind: 'bolt', type: 'fire', mana: 22, cd: 6, dmg: 55, speed: 22, range: 50, splash: 4.5, color: 0xff5010, sfx: 'orb', look: 'orb', size: 1.6 },
      { id: 'flame_step', name: 'Flame Step', glyph: '➚', kind: 'blink', type: 'fire', mana: 15, cd: 5, dist: 11, dmg: 18, radius: 3, color: 0xff9a30, sfx: 'flamestep', look: 'flamestep' },
      { id: 'kindle_ring', name: 'Kindle Ring', glyph: '◎', kind: 'nova', type: 'fire', mana: 24, cd: 9, dmg: 30, radius: 5.5, knock: 3, burn: { dps: 5, dur: 3 }, color: 0xff6a00, sfx: 'kindle', look: 'kindle' },
      { id: 'sunfall', name: 'Sunfall', glyph: '☀', kind: 'zone', type: 'fire', mana: 50, cd: 60, dmg: 40, radius: 7, dur: 3, interval: 0.22, tick: 'meteor', splash: 2.5, range: 40, color: 0xffc040, sfx: 'sunfall', look: 'sunfall', ult: true },
    ],
    talents: [
      [{ name: 'Split Embers', desc: 'Ember Bolt fires 3 bolts in a fan', f: S => { S.ember_bolt.count = 3; } },
       { name: 'Searing Core', desc: 'Ember Bolt +40% damage and burns', f: S => { S.ember_bolt.dmg *= 1.4; S.ember_bolt.burn = { dps: 4, dur: 2 }; } }],
      [{ name: 'Wide Blast', desc: 'Fireburst Orb radius +60%', f: S => { S.fireburst.splash *= 1.6; } },
       { name: 'Long Spray', desc: 'Cinder Spray range +50%, burns twice as hot', f: S => { S.cinder_spray.range *= 1.5; S.cinder_spray.burn.dps *= 2; } }],
      [{ name: 'Endless Dawn', desc: 'Sunfall lasts 50% longer', f: S => { S.sunfall.dur *= 1.5; } },
       { name: 'Quick Kindling', desc: 'All Pyromancer cooldowns -20%', f: S => { for (const k in S) S[k].cd *= 0.8; } }],
    ],
  },
  stormcaller: {
    name: 'Stormcaller', color: '#7fd4ff', blurb: 'Lightning and wind. Fast, mobile, chains between foes. Wind Dash goes further on a broom.',
    spells: [
      { id: 'spark_lance', name: 'Spark Lance', glyph: 'ϟ', kind: 'beam', type: 'storm', mana: 5, cd: 0.4, dmg: 18, range: 40, chain: 1, color: 0xbfe6ff, sfx: 'lance', look: 'lance' },
      { id: 'arc_chain', name: 'Arc Chain', glyph: '⚡', kind: 'beam', type: 'storm', mana: 14, cd: 4, dmg: 26, range: 30, chain: 4, chainRange: 8, color: 0x8fb8ff, sfx: 'arc', look: 'arc' },
      { id: 'gale_burst', name: 'Gale Burst', glyph: '༄', kind: 'cone', type: 'storm', mana: 12, cd: 6, dmg: 16, range: 10, angle: 0.8, knock: 5, slow: 2, color: 0xd8fff4, sfx: 'gale', look: 'gale' },
      { id: 'wind_dash', name: 'Wind Dash', glyph: '»', kind: 'blink', type: 'storm', mana: 10, cd: 4, dist: 14, broomMult: 1.6, color: 0xc8f0ff, sfx: 'winddash', look: 'winddash' },
      { id: 'static_field', name: 'Static Field', glyph: '⌁', kind: 'zone', type: 'storm', mana: 22, cd: 12, dmg: 12, radius: 5, dur: 4, interval: 0.5, tick: 'field', slow: 1, range: 30, color: 0x66aaff, sfx: 'static', look: 'static' },
      { id: 'tempest', name: 'Tempest', glyph: '☈', kind: 'zone', type: 'storm', mana: 50, cd: 70, dmg: 45, radius: 12, dur: 5, interval: 0.3, tick: 'strike', follow: true, color: 0xe0f0ff, sfx: 'tempest', look: 'tempest', ult: true },
    ],
    talents: [
      [{ name: 'Forked Lance', desc: 'Spark Lance chains to 2 more foes', f: S => { S.spark_lance.chain += 2; } },
       { name: 'Charged Lance', desc: 'Spark Lance +35% damage', f: S => { S.spark_lance.dmg *= 1.35; } }],
      [{ name: 'Slipstream', desc: 'Wind Dash +60% distance and brief invulnerability', f: S => { S.wind_dash.dist *= 1.6; S.wind_dash.invuln = 0.6; } },
       { name: 'Thunderclap', desc: 'Gale Burst stuns for 1 s', f: S => { S.gale_burst.stun = 1; } }],
      [{ name: 'Eye of the Storm', desc: 'Tempest strikes twice as often', f: S => { S.tempest.interval /= 2; } },
       { name: 'Wide Field', desc: 'Static Field radius +50%, lasts 2 s longer', f: S => { S.static_field.radius *= 1.5; S.static_field.dur += 2; } }],
    ],
  },
  warden: {
    name: 'Stone Warden', color: '#c9a66b', blurb: 'Earth and stone. Shields, stuns and roots; outlasts anything.',
    spells: [
      { id: 'pebble_shot', name: 'Pebble Shot', glyph: '●', kind: 'bolt', type: 'stone', mana: 4, cd: 0.5, dmg: 20, speed: 52, range: 50, splash: 0, grav: 4, color: 0xd8b880, sfx: 'pebble', look: 'pebble' },
      { id: 'granite_skin', name: 'Granite Skin', glyph: '⛨', kind: 'shield', type: 'stone', mana: 18, cd: 12, amount: 40, dur: 8, color: 0xe0c080, sfx: 'granite', look: 'granite' },
      { id: 'quake_stomp', name: 'Quake Stomp', glyph: '⩩', kind: 'nova', type: 'stone', mana: 18, cd: 8, dmg: 25, radius: 6, stun: 1.2, color: 0xb08850, sfx: 'quake', look: 'quake' },
      { id: 'boulder_leap', name: 'Boulder Leap', glyph: '⤴', kind: 'blink', type: 'stone', mana: 14, cd: 7, dist: 10, hop: 7, dmg: 20, radius: 3, stun: 0.8, landing: true, color: 0xc09060, sfx: 'leap', look: 'leap' },
      { id: 'rootbind', name: 'Rootbind Spikes', glyph: '⋀', kind: 'zone', type: 'stone', mana: 20, cd: 10, dmg: 30, radius: 4, dur: 0.01, interval: 1, tick: 'spikes', slow: 4, range: 30, color: 0x9a8a60, sfx: 'spikes', look: 'spikes' },
      { id: 'monolith', name: 'Monolith Ward', glyph: '▲', kind: 'shield', type: 'stone', mana: 50, cd: 75, amount: 120, dur: 10, dmg: 60, radius: 9, stun: 3, color: 0xffd890, sfx: 'monolith', look: 'monolith', ult: true },
    ],
    talents: [
      [{ name: 'Bedrock', desc: 'Granite Skin absorbs 60% more', f: S => { S.granite_skin.amount *= 1.6; } },
       { name: 'Quick Set', desc: 'Granite Skin cooldown -40%', f: S => { S.granite_skin.cd *= 0.6; } }],
      [{ name: 'Fault Line', desc: 'Quake Stomp radius +40%', f: S => { S.quake_stomp.radius *= 1.4; } },
       { name: 'Aftershock', desc: 'Quake Stomp stuns 1 s longer', f: S => { S.quake_stomp.stun += 1; } }],
      [{ name: 'Crater', desc: 'Boulder Leap landing radius x2, +50% damage', f: S => { S.boulder_leap.radius *= 2; S.boulder_leap.dmg *= 1.5; } },
       { name: 'Ancient Ward', desc: 'Monolith Ward cooldown -35%', f: S => { S.monolith.cd *= 0.65; } }],
    ],
  },
  hexweaver: {
    name: 'Hex Weaver', color: '#b070ff', blurb: 'Curses, bound wisps and life drain. Weakens foes, feeds on them.',
    spells: [
      { id: 'hex_dart', name: 'Hex Dart', glyph: '✧', kind: 'bolt', type: 'hex', mana: 5, cd: 0.4, dmg: 16, speed: 40, range: 50, splash: 0, drain: 0.3, color: 0xb070ff, sfx: 'dart', look: 'dart' },
      { id: 'withering_mark', name: 'Withering Mark', glyph: '⍟', kind: 'bolt', type: 'hex', mana: 12, cd: 5, dmg: 10, speed: 34, range: 45, splash: 0, curse: 1.35, curseDur: 8, burn: { dps: 5, dur: 8 }, color: 0x70ff90, sfx: 'mark', look: 'mark' },
      { id: 'soul_siphon', name: 'Soul Siphon', glyph: '♆', kind: 'beam', type: 'hex', mana: 16, cd: 6, dmg: 35, range: 25, chain: 0, drain: 0.5, color: 0xd050ff, sfx: 'siphon', look: 'siphon' },
      { id: 'shade_step', name: 'Shade Step', glyph: '⇢', kind: 'blink', type: 'hex', mana: 12, cd: 5, dist: 12, invuln: 0.5, color: 0x8040c0, sfx: 'shade', look: 'shade' },
      { id: 'bound_wisps', name: 'Bound Wisps', glyph: '❂', kind: 'summon', type: 'hex', mana: 24, cd: 18, dmg: 10, count: 2, dur: 12, interval: 0.8, range: 20, drain: 0.3, color: 0xa0ffd0, sfx: 'wisp', look: 'wisp' },
      { id: 'night_bloom', name: 'Night Bloom', glyph: '✿', kind: 'zone', type: 'hex', mana: 50, cd: 70, dmg: 20, radius: 8, dur: 4, interval: 0.5, tick: 'field', curse: 1.5, curseDur: 6, drain: 0.25, range: 30, color: 0x9030ff, sfx: 'bloom', look: 'bloom', ult: true },
    ],
    talents: [
      [{ name: 'Gluttony', desc: 'Hex Dart drains 60% of damage dealt', f: S => { S.hex_dart.drain = 0.6; } },
       { name: 'Needle Hex', desc: 'Hex Dart pierces through 2 foes', f: S => { S.hex_dart.pierce = 2; } }],
      [{ name: 'Deep Wither', desc: 'Withering Mark curse 1.6x damage taken', f: S => { S.withering_mark.curse = 1.6; } },
       { name: 'Third Wisp', desc: 'Bound Wisps summons 3 wisps', f: S => { S.bound_wisps.count = 3; } }],
      [{ name: 'Overgrowth', desc: 'Night Bloom radius +50%', f: S => { S.night_bloom.radius *= 1.5; } },
       { name: 'Shadow Wake', desc: 'Shade Step leaves a cursing burst where you were', f: S => { Object.assign(S.shade_step, { wake: true, dmg: 15, radius: 3.5, curse: 1.3, curseDur: 5 }); } }],
    ],
  },
};
export const TALENT_LEVELS = [2, 4, 6];

export function install(game) {
  const THREE = game.THREE, p = game.player, world = game.world;
  const vfx = createVfx(game); game.vfx = vfx;
  const offs = [];   // listener removers, run on dispose
  const listen = (t, ev, fn, o) => { t.addEventListener(ev, fn, o); offs.push(() => t.removeEventListener(ev, fn, o)); };

  // ---------- spells table (class defs + talents) ----------
  const caster = game.caster = {
    cls: null, spells: [], classes: CLASSES, talentLevels: TALENT_LEVELS,
    get talents() { return CLASSES[this.cls]?.talents || []; },
    get picks() { return (game.save.talents ||= {})[this.cls] ||= [null, null, null]; },
    setClass, cast, pickTalent, rebuild,
    remaining(i) { const s = this.spells[i]; return s ? Math.max(0, s.readyAt - game.time) : 0; },
  };
  function rebuild() {
    const def = CLASSES[caster.cls]; if (!def) return;
    const old = caster.spells, S = {};
    const list = def.spells.map((d, i) => {
      const s = structuredClone(d); s.slot = i; s.key = String(i + 1);
      s.readyAt = old[i]?.id === s.id ? old[i].readyAt : 0; s.cdTotal = old[i]?.id === s.id ? old[i].cdTotal : s.cd;
      S[s.id] = s; return s;
    });
    const picks = caster.picks;
    def.talents.forEach((tier, t) => { const c = picks[t]; if (c != null && game.stats.level >= TALENT_LEVELS[t]) tier[c]?.f(S); });
    caster.spells = list;
    game.emit('spellsChanged', { cls: caster.cls });
  }
  function setClass(cls) {
    if (!CLASSES[cls]) return false;
    caster.cls = cls; caster.spells = [];
    if (game.save.cls !== cls) { game.save.cls = cls; game.persist(); }
    rebuild(); giveGear();
    return true;
  }
  function pickTalent(tier, choice) {
    if (game.stats.level < TALENT_LEVELS[tier]) return false;
    caster.picks[tier] = choice; game.persist(); rebuild(); return true;
  }
  function giveGear() {
    if (!game.items?.give || !caster.cls) return;
    const given = (game.save.gearGiven ||= {});
    if (given[caster.cls]) return;
    for (const id of STARTING_GEAR[caster.cls]) { try { game.items.give(id); } catch (e) { console.warn('[classes] give', id, e.message); } }
    given[caster.cls] = true; game.persist();
  }
  offs.push(game.on('ready', giveGear));
  offs.push(game.on('levelup', () => { rebuild(); sfx.play('levelup'); }));
  setClass(game.save.cls && CLASSES[game.save.cls] ? game.save.cls : 'pyromancer');
  if (!game.save.cls) { delete game.save.cls; game.persist(); }   // still let the HUD offer the class choice

  // ---------- aiming ----------
  const A = { x: 0, y: 0, z: 0, dx: 0, dy: 1, dz: 0, hx: 0, hy: 1 };   // origin + unit direction + horizontal facing
  const mobH = m => m.height ?? 1.6;
  function aim(target) {
    const f = game.facing();
    A.x = p.x + f.x * 0.4; A.y = p.y + f.y * 0.4; A.z = p.eye - 0.25;
    if (target && !target.dead) {
      let dx = target.x - A.x, dy = target.y - A.y, dz = target.z + mobH(target) * 0.5 - A.z; const l = Math.hypot(dx, dy, dz) || 1;
      A.dx = dx / l; A.dy = dy / l; A.dz = dz / l;
      const h = Math.hypot(dx, dy) || 1; A.hx = dx / h; A.hy = dy / h;
    } else {
      const cp = Math.cos(p.pitch), sp = Math.sin(p.pitch);
      A.dx = f.x * cp; A.dy = f.y * cp; A.dz = sp; A.hx = f.x; A.hy = f.y;
    }
  }
  // first wall/ground hit along the aim ray, up to range (cast-time only)
  const P = { x: 0, y: 0, z: 0, d: 0 };
  function rayPoint(range) {
    let d = 0.5;
    for (; d <= range; d += 0.5) {
      const x = A.x + A.dx * d, y = A.y + A.dy * d, z = A.z + A.dz * d, g = game.groundAt(x, y, z);
      if ((g != null && z <= g + 0.05) || world.blocked(x, y, z - 0.3, 0.15, 0, 0.6)) { d -= 0.5; break; }
    }
    d = Math.max(0, Math.min(d, range));
    P.x = A.x + A.dx * d; P.y = A.y + A.dy * d; P.z = A.z + A.dz * d; P.d = d; return P;
  }
  const groundZ = (x, y, z) => game.groundAt(x, y, z + 1) ?? p.z;

  // ---------- hit effects / statuses ----------
  const dots = [], cursed = new Set();
  function hit(m, sp, mult = 1, ox, oy) {
    if (!m || m.dead) return 0;
    const dealt = game.damageMob(m, (sp.dmg || 0) * mult, { type: sp.type, spell: sp.id, source: 'player' });
    status(m, sp, ox, oy);
    if (sp.drain && dealt) game.heal(dealt * sp.drain);
    return dealt;
  }
  function status(m, sp, ox, oy) {
    if (m.dead) return;
    const t = game.time;
    if (sp.slow) m.slowUntil = Math.max(m.slowUntil || 0, t + sp.slow);
    if (sp.stun) m.stunUntil = Math.max(m.stunUntil || 0, t + sp.stun);
    if (sp.curse) { m.damageTaken = Math.max(m.damageTaken ?? 1, sp.curse); m._curseUntil = t + (sp.curseDur || 5); cursed.add(m); }
    if (sp.burn) {
      let d = dots.find(d => d.m === m && d.sp === sp.id);
      if (!d) { d = { m, sp: sp.id, type: sp.type, next: t + 0.5 }; dots.push(d); }
      d.dps = sp.burn.dps; d.until = t + sp.burn.dur; d.drain = sp.drain || 0;
    }
    if (sp.knock && ox != null) {
      const dx = m.x - ox, dy = m.y - oy, l = Math.hypot(dx, dy) || 1;
      for (let k = sp.knock; k > 0.4; k *= 0.5) {
        const nx = m.x + dx / l * k, ny = m.y + dy / l * k;
        const g = world.standAt(nx, ny, m.z);
        if (g != null) { m.x = nx; m.y = ny; m.z = g; break; }
      }
    }
  }
  function aoe(x, y, z, r, sp, mult = 1, vert = 4) {
    let n = 0;
    for (const m of game.mobsNear(x, y, r)) if (Math.abs(m.z + mobH(m) * 0.5 - z) < vert + mobH(m)) { hit(m, sp, mult, x, y); n++; }
    return n;
  }

  // ---------- per-spell looks (cast + impact VFX) ----------
  const LOOK = {
    ember: { trail: (x, y, z) => vfx.burst(x, y, z, 2, { color: 0xff8a30, speed: 1, size: 0.35, life: 0.35, up: 1 }),
             impact: (x, y, z) => { vfx.burst(x, y, z, 26, { color: 0xffa040, speed: 6, size: 0.45, life: 0.5, grav: 4 }); vfx.orb(x, y, z, 0xff8030, 1.4, 0.25); } },
    orb: { trail: (x, y, z) => vfx.burst(x, y, z, 5, { color: 0xff5010, speed: 1.5, size: 0.7, life: 0.6, up: 1.5 }),
           impact: (x, y, z, sp) => { sfx.play('boom'); vfx.burst(x, y, z, 90, { color: 0xff6a10, speed: 12, size: 0.9, life: 0.9, drag: 2.5 }); vfx.burst(x, y, z, 40, { color: 0xffe080, speed: 5, size: 0.6, life: 0.5 }); vfx.ring(x, y, groundZ(x, y, z), 0xff7020, 0.5, sp.splash, 0.5); vfx.orb(x, y, z, 0xffb050, sp.splash * 1.2, 0.35); } },
    pebble: { trail: (x, y, z) => vfx.burst(x, y, z, 1, { color: 0xb09070, speed: 0.5, size: 0.2, life: 0.3 }),
              impact: (x, y, z) => vfx.burst(x, y, z, 18, { color: 0xc8a878, speed: 5, size: 0.3, life: 0.6, grav: 12 }) },
    dart: { trail: (x, y, z) => vfx.burst(x, y, z, 2, { color: 0xb070ff, speed: 0.6, size: 0.3, life: 0.4 }),
            impact: (x, y, z) => { vfx.burst(x, y, z, 20, { color: 0xc080ff, speed: 4, size: 0.4, life: 0.5, drag: 3 }); vfx.orb(x, y, z, 0x9050ff, 1, 0.2); } },
    mark: { trail: (x, y, z) => vfx.burst(x, y, z, 3, { color: 0x60ff80, speed: 0.8, size: 0.35, life: 0.5, up: -0.5 }),
            impact: (x, y, z) => { vfx.burst(x, y, z, 30, { color: 0x50ff70, speed: 3, size: 0.45, life: 0.9, up: 1.5, drag: 2 }); vfx.ring(x, y, groundZ(x, y, z), 0x60ff90, 0.3, 1.6, 0.6); } },
  };

  // ---------- projectiles ----------
  const projs = [], projPool = [];
  function fireBolt(sp, dirx, diry, dirz) {
    const b = projPool.pop() || { hits: new Set() };
    Object.assign(b, { sp, x: A.x, y: A.y, z: A.z, dx: dirx, dy: diry, dz: dirz, trav: 0, vz: 0, pierce: sp.pierce || 0 });
    b.hits.clear();
    b.orb = vfx.orb(b.x, b.y, b.z, sp.color, (sp.size || 0.6));
    projs.push(b);
  }
  function explode(b) {
    const sp = b.sp, look = LOOK[sp.look];
    look?.impact(b.x, b.y, b.z, sp);
    if (sp.splash > 0) aoe(b.x, b.y, b.z, sp.splash, sp, 1, sp.splash);
  }
  function stepProjs(dt) {
    for (let i = projs.length - 1; i >= 0; i--) {
      const b = projs[i], sp = b.sp; let done = false;
      const n = Math.max(1, Math.ceil(sp.speed * dt / 1.2)), h = sp.speed * dt / n;
      for (let s = 0; s < n && !done; s++) {
        if (sp.grav) b.vz -= sp.grav * dt / n;
        b.x += b.dx * h; b.y += b.dy * h; b.z += b.dz * h + b.vz * dt / n; b.trav += h;
        for (const m of game.mobs) {
          if (m.dead || b.hits.has(m)) continue;
          const r = (m.radius || 0.5) + 0.35, cz = m.z + mobH(m) * 0.5;
          const dx = m.x - b.x, dy = m.y - b.y, dz = cz - b.z;
          if (dx * dx + dy * dy < r * r && Math.abs(dz) < mobH(m) * 0.5 + 0.35) {
            b.hits.add(m);
            if (!(sp.splash > 0)) hit(m, sp, 1, b.x, b.y);
            if (b.pierce-- <= 0) { done = true; break; } else LOOK[sp.look]?.impact(b.x, b.y, b.z, sp);
          }
        }
        if (!done) {
          const g = game.groundAt(b.x, b.y, b.z);
          if (b.trav >= sp.range || (g != null && b.z <= g) || world.blocked(b.x, b.y, b.z - 0.2, 0.1, 0, 0.4)) done = true;
        }
      }
      if (done) { explode(b); vfx.release(b.orb); projs[i] = projs[projs.length - 1]; projs.pop(); projPool.push(b); continue; }
      b.orb?.position.set(b.x, b.z, -b.y);
      LOOK[sp.look]?.trail(b.x, b.y, b.z);
    }
  }

  // ---------- zones, summons, delayed events ----------
  const zones = [], wisps = [], later = [];
  const after = (s, fn) => later.push({ at: game.time + s, fn });
  function zoneTick(z) {
    const sp = z.sp;
    if (sp.follow) { z.x = p.x; z.y = p.y; z.z = p.z; }
    if (sp.tick === 'field') {
      aoe(z.x, z.y, z.z + 1, sp.radius, sp, 1);
      const a = Math.random() * 6.283, r = Math.random() * sp.radius;
      if (sp.type === 'storm') { const x = z.x + Math.cos(a) * r, y = z.y + Math.sin(a) * r; vfx.lightning(x, y, z.z + 0.1, x + (Math.random() - 0.5) * 2, y + (Math.random() - 0.5) * 2, z.z + 1.5, 0x88bbff, 0.15, 0.5); }
      else vfx.burst(z.x, z.y, z.z + 0.3, 30, { color: 0x9030ff, speed: 3, size: 0.6, life: 1, up: 2.5, jitter: sp.radius * 1.4 });
    } else if (sp.tick === 'meteor') {
      const a = Math.random() * 6.283, r = Math.sqrt(Math.random()) * sp.radius, x = z.x + Math.cos(a) * r, y = z.y + Math.sin(a) * r, gz = groundZ(x, y, z.z + 5);
      vfx.beam(x + 3, y + 3, gz + 25, x, y, gz, 0xffa030, 0.35, 0.35);
      vfx.orb(x, y, gz + 0.5, 0xffc060, 3, 0.35);
      after(0.15, () => { vfx.burst(x, y, gz + 0.3, 40, { color: 0xff7020, speed: 9, size: 0.7, life: 0.7, grav: 5 }); vfx.ring(x, y, gz, 0xffa040, 0.3, sp.splash, 0.4); aoe(x, y, gz + 1, sp.splash, sp); sfx.play('boom', 0.6); });
    } else if (sp.tick === 'strike') {
      let m = null, bd = 1e9;
      for (const c of game.mobsNear(z.x, z.y, sp.radius)) { const d = (c._struck || 0) + Math.random(); if (d < bd) { bd = d; m = c; } }
      let x, y, gz;
      if (m) { x = m.x; y = m.y; gz = m.z; m._struck = (m._struck || 0) + 1; }
      else { const a = Math.random() * 6.283, r = Math.random() * sp.radius; x = z.x + Math.cos(a) * r; y = z.y + Math.sin(a) * r; gz = groundZ(x, y, z.z + 5); }
      vfx.lightning(x + (Math.random() - 0.5) * 4, y + (Math.random() - 0.5) * 4, gz + 22, x, y, gz, 0xe8f4ff, 0.22, 2.2);
      vfx.burst(x, y, gz + 0.2, 25, { color: 0xbfe0ff, speed: 7, size: 0.4, life: 0.4 });
      sfx.play('thunder', 0.6);
      if (m) hit(m, sp); else aoe(x, y, gz + 1, 1.5, sp);
    } else if (sp.tick === 'spikes') {
      for (let k = 0; k < 16; k++) { const a = Math.random() * 6.283, r = Math.sqrt(Math.random()) * sp.radius, x = z.x + Math.cos(a) * r, y = z.y + Math.sin(a) * r; vfx.spike(x, y, groundZ(x, y, z.z), 1 + Math.random() * 1.4, 1.6); }
      vfx.burst(z.x, z.y, z.z + 0.2, 40, { color: 0x9a8060, speed: 4, size: 0.5, life: 0.8, grav: 8, up: 3, jitter: sp.radius });
      aoe(z.x, z.y, z.z + 1, sp.radius, sp);
    }
  }
  function stepWorld(dt) {
    const t = game.time;
    for (let i = zones.length - 1; i >= 0; i--) {
      const z = zones[i];
      if (t >= z.next) { z.next += z.sp.interval; zoneTick(z); }
      if (t >= z.until) { zones[i] = zones[zones.length - 1]; zones.pop(); }
    }
    for (let i = wisps.length - 1; i >= 0; i--) {
      const w = wisps[i]; w.a += dt * 2.2;
      const x = p.x + Math.cos(w.a) * 1.4, y = p.y + Math.sin(w.a) * 1.4, z = p.z + 2 + Math.sin(w.a * 2) * 0.3;
      w.orb.position.set(x, z, -y);
      if (Math.random() < 0.3) vfx.burst(x, y, z, 1, { color: 0xa0ffd0, speed: 0.3, size: 0.25, life: 0.5 });
      if (t >= w.next) {
        w.next = t + w.sp.interval;
        const m = game.nearestMob(x, y, w.sp.range);
        if (m) { vfx.lightning(x, y, z, m.x, m.y, m.z + mobH(m) * 0.5, 0xa0ffd0, 0.15, 0.3); hit(m, w.sp); sfx.play('dart', 0.5); }
      }
      if (t >= w.until) { vfx.release(w.orb); vfx.burst(x, y, z, 12, { color: 0xa0ffd0, speed: 2, size: 0.3, life: 0.4 }); wisps[i] = wisps[wisps.length - 1]; wisps.pop(); }
    }
    for (let i = dots.length - 1; i >= 0; i--) {
      const d = dots[i];
      if (d.m.dead || t > d.until) { dots[i] = dots[dots.length - 1]; dots.pop(); continue; }
      if (t >= d.next) {
        d.next += 0.5;
        const dealt = game.damageMob(d.m, d.dps * 0.5, { type: d.type, spell: d.sp, source: 'player', crit: false, noProc: true });
        if (d.drain && dealt) game.heal(dealt * d.drain);
        vfx.burst(d.m.x, d.m.y, d.m.z + mobH(d.m) * 0.6, 3, { color: d.type === 'fire' ? 0xff7020 : 0x60ff80, speed: 1, size: 0.3, life: 0.5, up: 1.5, jitter: 0.6 });
      }
    }
    for (const m of cursed) if (m.dead || t > m._curseUntil) { m.damageTaken = 1; cursed.delete(m); }
    for (let i = later.length - 1; i >= 0; i--) if (t >= later[i].at) { const e = later[i]; later[i] = later[later.length - 1]; later.pop(); e.fn(); }
    if (game.shield > 0 && t > (game.shieldUntil || 0)) game.shield = 0;
  }

  // ---------- spell kinds ----------
  function blinkTo(dist, flying) {
    const x0 = p.x, y0 = p.y; let x = p.x, y = p.y, z = p.z, moved = 0;
    for (let d = 0.5; d <= dist + 1e-6; d += 0.5) {
      const nx = x0 + A.hx * d, ny = y0 + A.hy * d;
      if (flying) { if (world.blocked(nx, ny, z)) break; x = nx; y = ny; moved = d; continue; }
      const g = world.standAt(nx, ny, z);
      if (g == null || Math.abs(g - z) > 1.2) break;
      x = nx; y = ny; z = g; moved = d;
    }
    p.x = x; p.y = y; if (!flying) p.z = z;
    return moved;
  }
  const KIND = {
    bolt(sp) {
      const n = sp.count || 1;
      for (let k = 0; k < n; k++) {
        const a = (k - (n - 1) / 2) * 0.12, c = Math.cos(a), s = Math.sin(a);
        fireBolt(sp, A.dx * c - A.dy * s, A.dx * s + A.dy * c, A.dz);
      }
      vfx.burst(A.x, A.y, A.z, 10, { color: sp.color, speed: 3, size: 0.3, life: 0.3, dx: A.dx, dy: A.dy, dz: A.dz });
    },
    beam(sp, target) {
      const end = rayPoint(sp.range);
      let first = null, bt = end.d;
      for (const m of game.mobs) {
        if (m.dead) continue;
        const cx = m.x - A.x, cy = m.y - A.y, cz = m.z + mobH(m) * 0.5 - A.z, t = cx * A.dx + cy * A.dy + cz * A.dz;
        if (t < 0 || t > bt + 0.5) continue;
        const ex = cx - A.dx * t, ey = cy - A.dy * t, ez = cz - A.dz * t, r = (m.radius || 0.5) + 0.6;
        if (ex * ex + ey * ey < r * r && Math.abs(ez) < mobH(m) * 0.5 + 0.6) { first = m; bt = t; }
      }
      if (target && !target.dead && !first) first = target;
      const ex = first ? first.x : end.x, ey = first ? first.y : end.y, ez = first ? first.z + mobH(first) * 0.5 : end.z;
      const siphon = sp.look === 'siphon';
      if (siphon) { vfx.beam(A.x, A.y, A.z - 0.1, ex, ey, ez, sp.color, 0.12, 0.4); vfx.burst(ex, ey, ez, 30, { color: 0xff60ff, speed: 3, size: 0.4, life: 0.6, dx: -A.dx, dy: -A.dy, dz: -A.dz, cone: 0.6 }); }
      else vfx.lightning(A.x, A.y, A.z - 0.1, ex, ey, ez, sp.color, sp.look === 'arc' ? 0.3 : 0.15, sp.look === 'arc' ? 1 : 0.4);
      vfx.burst(ex, ey, ez, 14, { color: sp.color, speed: 5, size: 0.3, life: 0.35 });
      if (!first) return;
      hit(first, sp);
      // chain to nearby foes
      let from = first, mult = 1; const done = new Set([first]);
      for (let c = 0; c < (sp.chain || 0); c++) {
        let nx = null, nd = sp.chainRange || 6;
        for (const m of game.mobs) { if (m.dead || done.has(m)) continue; const d = Math.hypot(m.x - from.x, m.y - from.y); if (d < nd) { nd = d; nx = m; } }
        if (!nx) break;
        mult *= 0.8; done.add(nx);
        vfx.lightning(from.x, from.y, from.z + mobH(from) * 0.5, nx.x, nx.y, nx.z + mobH(nx) * 0.5, sp.color, 0.2, 0.7);
        hit(nx, sp, mult); from = nx;
      }
    },
    cone(sp) {
      const cosA = Math.cos(sp.angle);
      for (const m of game.mobsNear(p.x, p.y, sp.range)) {
        const dx = m.x - p.x, dy = m.y - p.y, l = Math.hypot(dx, dy) || 1;
        if ((dx * A.hx + dy * A.hy) / l >= cosA && Math.abs(m.z - p.z) < 4) hit(m, sp, 1, p.x, p.y);
      }
      if (sp.look === 'spray') {
        vfx.burst(A.x, A.y, A.z - 0.2, 110, { color: 0xff8a20, speed: sp.range * 1.3, size: 0.6, life: 0.6, dx: A.hx, dy: A.hy, dz: A.dz * 0.5, cone: 0.55, drag: 2, up: 1 });
        vfx.burst(A.x, A.y, A.z - 0.2, 40, { color: 0xffe080, speed: sp.range, size: 0.35, life: 0.4, dx: A.hx, dy: A.hy, dz: A.dz * 0.5, cone: 0.4 });
      } else {
        vfx.burst(A.x, A.y, A.z - 0.3, 90, { color: 0xd8fff4, speed: sp.range * 1.6, size: 0.5, life: 0.5, dx: A.hx, dy: A.hy, dz: 0, cone: 0.7, drag: 3 });
        vfx.ring(p.x + A.hx * 2, p.y + A.hy * 2, p.z + 0.5, 0xd8fff4, 0.5, 3, 0.35);
      }
    },
    nova(sp) {
      const gz = p.z;
      aoe(p.x, p.y, gz + 1, sp.radius, sp, 1);
      if (sp.look === 'kindle') {
        vfx.ring(p.x, p.y, gz, 0xff6a00, 0.5, sp.radius, 0.5); vfx.ring(p.x, p.y, gz + 0.4, 0xffc040, 0.3, sp.radius * 0.8, 0.6);
        for (let k = 0; k < 24; k++) { const a = k / 24 * 6.283; vfx.burst(p.x + Math.cos(a), p.y + Math.sin(a), gz + 0.5, 4, { color: 0xff7010, speed: sp.radius * 2, size: 0.6, life: 0.5, dx: Math.cos(a), dy: Math.sin(a), dz: 0.1, cone: 0.2, drag: 3, up: 1 }); }
      } else {
        vfx.ring(p.x, p.y, gz, 0xb08850, 0.5, sp.radius, 0.7); vfx.disc(p.x, p.y, gz, 0x806040, sp.radius, 0.5, 0.25);
        for (let k = 0; k < 10; k++) { const a = Math.random() * 6.283, r = 1 + Math.random() * (sp.radius - 1); vfx.spike(p.x + Math.cos(a) * r, p.y + Math.sin(a) * r, gz, 0.6 + Math.random(), 0.8); }
        vfx.burst(p.x, p.y, gz + 0.2, 60, { color: 0xa08060, speed: 6, size: 0.5, life: 0.9, grav: 10, up: 4, jitter: sp.radius });
      }
    },
    zone(sp, target) {
      let x, y, z;
      if (sp.follow) { x = p.x; y = p.y; z = p.z; }
      else if (target && !target.dead) { x = target.x; y = target.y; z = target.z; }
      else { const e = rayPoint(sp.range); x = e.x; y = e.y; z = groundZ(e.x, e.y, e.z); }
      zones.push({ sp, x, y, z, next: game.time + (sp.tick === 'meteor' ? 0.4 : 0), until: game.time + sp.dur + (sp.tick === 'meteor' ? 0.4 : 0) });
      const dur = Math.max(0.6, sp.dur + 0.4);
      if (sp.look === 'sunfall') { vfx.disc(x, y, z, 0xff8020, sp.radius, dur, 0.3); vfx.ring(x, y, z, 0xffc040, sp.radius, sp.radius, dur); vfx.orb(x, y, z + 20, 0xffd080, 10, dur); }
      else if (sp.look === 'static') { vfx.disc(x, y, z, 0x3366ff, sp.radius, dur, 0.25); vfx.ring(x, y, z, 0x88ccff, sp.radius * 0.2, sp.radius, 0.5); }
      else if (sp.look === 'tempest') { vfx.ring(p.x, p.y, p.z, 0xe0f0ff, 1, sp.radius, 0.8); vfx.burst(p.x, p.y, p.z + 3, 120, { color: 0xc0d8ff, speed: 10, size: 0.5, life: 1.2, drag: 1 }); }
      else if (sp.look === 'spikes') vfx.ring(x, y, z, 0x9a8a60, 0.5, sp.radius, 0.4);
      else if (sp.look === 'bloom') { vfx.disc(x, y, z, 0x6020c0, sp.radius, dur, 0.35); vfx.ring(x, y, z, 0xc080ff, 0.5, sp.radius, 0.9); vfx.ring(x, y, z, 0x60ff90, 0.5, sp.radius * 0.7, 1.2); }
    },
    blink(sp) {
      const fly = p.flying, x0 = p.x, y0 = p.y, z0 = p.z;
      const dist = sp.dist * (fly && sp.broomMult ? sp.broomMult : 1);
      if (sp.wake) { vfx.ring(x0, y0, z0, 0x8040c0, 0.5, sp.radius, 0.5); aoe(x0, y0, z0 + 1, sp.radius, sp); }
      const moved = blinkTo(dist, fly);
      if (sp.invuln) game.invulnUntil = Math.max(game.invulnUntil || 0, game.time + sp.invuln);
      if (sp.hop && !fly) { p.vz = sp.hop; p.grounded = false; }
      if (fly && sp.broomMult) game.stats.mana = Math.min(game.stats.maxMana, game.stats.mana + sp.mana * 0.5);   // broom synergy: half refund
      // trail along the path
      const steps = Math.max(2, Math.round(moved));
      for (let k = 0; k <= steps; k++) {
        const t = k / steps, x = x0 + (p.x - x0) * t, y = y0 + (p.y - y0) * t, z = z0 + (p.z - z0) * t + 1;
        vfx.burst(x, y, z, 4, { color: sp.color, speed: 1.2, size: sp.look === 'shade' ? 0.7 : 0.45, life: 0.5, up: sp.look === 'flamestep' ? 2 : 0, jitter: 0.6 });
      }
      if (sp.look === 'winddash') vfx.beam(x0, y0, z0 + 1, p.x, p.y, p.z + 1, 0xc8f0ff, 0.3, 0.3);
      if (sp.look === 'flamestep') { vfx.ring(x0, y0, z0, 0xff9a30, 0.3, sp.radius, 0.4); aoe(x0, y0, z0 + 1, sp.radius, sp); after(0.05, () => { vfx.ring(p.x, p.y, p.z, 0xff6a10, 0.3, sp.radius, 0.4); aoe(p.x, p.y, p.z + 1, sp.radius, sp); }); }
      if (sp.landing) {
        const land = () => {
          vfx.ring(p.x, p.y, p.z, 0xc09060, 0.4, sp.radius, 0.5);
          for (let k = 0; k < 8; k++) { const a = k / 8 * 6.283; vfx.spike(p.x + Math.cos(a) * sp.radius * 0.6, p.y + Math.sin(a) * sp.radius * 0.6, p.z, 0.9, 0.9); }
          vfx.burst(p.x, p.y, p.z + 0.2, 50, { color: 0xa08060, speed: 6, size: 0.5, life: 0.8, grav: 10, up: 3 });
          aoe(p.x, p.y, p.z + 1, sp.radius, sp); sfx.play('quake', 0.7);
        };
        const t0 = game.time, wait = () => (p.grounded && game.time - t0 > 0.15) || game.time - t0 > 2 ? land() : after(0.05, wait);
        after(0.15, wait);
      }
    },
    shield(sp) {
      game.shield = Math.max(game.shield || 0, sp.amount); game.shieldUntil = game.time + sp.dur;
      vfx.dome(sp.color, sp.ult ? 1.8 : 1.4, () => game.shield > 0);
      vfx.burst(p.x, p.y, p.z + 1, 50, { color: sp.color, speed: 3, size: 0.4, life: 0.8, up: 1 });
      if (sp.radius) {   // Monolith Ward: stun nova + a ring of standing stones
        aoe(p.x, p.y, p.z + 1, sp.radius, sp);
        vfx.ring(p.x, p.y, p.z, 0xffd890, 0.5, sp.radius, 0.9);
        for (let k = 0; k < 12; k++) { const a = k / 12 * 6.283; vfx.spike(p.x + Math.cos(a) * sp.radius * 0.5, p.y + Math.sin(a) * sp.radius * 0.5, p.z, 3, 3, 0xa09070); }
      }
    },
    summon(sp) {
      for (let k = 0; k < sp.count; k++) {
        const o = vfx.orb(p.x, p.y, p.z + 2, sp.color, 0.7); if (!o) break;
        wisps.push({ sp, orb: o, a: k / sp.count * 6.283, next: game.time + 0.3 + k * 0.2, until: game.time + sp.dur });
      }
      vfx.burst(p.x, p.y, p.z + 1.5, 40, { color: sp.color, speed: 3, size: 0.4, life: 0.7 });
    },
  };

  // ---------- staff (first-person) ----------
  const staff = new THREE.Group();
  const wood = new THREE.Mesh(new THREE.CylinderGeometry(0.018, 0.026, 1.1, 6), new THREE.MeshBasicMaterial({ color: 0x4a3020, depthTest: false, fog: false }));
  wood.position.y = -0.3; staff.add(wood);
  const tip = new THREE.Sprite(new THREE.SpriteMaterial({ map: vfx.glow, color: 0xffffff, transparent: true, depthTest: false, depthWrite: false, blending: THREE.AdditiveBlending, fog: false }));
  tip.position.y = 0.27; tip.scale.setScalar(0.14); staff.add(tip);
  wood.renderOrder = tip.renderOrder = 999;
  game.root.add(staff);
  const so = new THREE.Vector3(); let thrust = 0, bob = 0;
  function updateStaff(dt) {
    const show = p.view !== 3 && !window.__cam;
    staff.visible = show; if (!show) return;
    thrust = Math.max(0, thrust - dt * 4); bob += dt * (2 + p.speed * 1.5);
    const th = Math.sin(Math.min(1, thrust) * Math.PI);
    so.set(0.28, -0.32 + Math.sin(bob) * 0.012 + th * 0.05, -0.62 - th * 0.18).applyQuaternion(game.camera.quaternion);
    staff.position.copy(game.camera.position).add(so);
    staff.quaternion.copy(game.camera.quaternion); staff.rotateX(-0.35 - th * 0.4); staff.rotateZ(0.12);
    const def = CLASSES[caster.cls];
    if (def) tip.material.color.set(def.color);
    tip.scale.setScalar(0.13 + th * 0.12 + Math.sin(game.time * 5) * 0.01);
  }

  // ---------- casting ----------
  let lastNoMana = -9;
  function cast(i, target) {
    const sp = caster.spells[i];
    if (!sp || game.stats.hp <= 0 || game.paused) return false;
    if (game.time < sp.readyAt) return false;
    if (game.stats.mana < sp.mana) {
      if (game.time - lastNoMana > 1) { lastNoMana = game.time; sfx.play('nomana'); game.hud?.toast?.('Not enough mana'); }
      return false;
    }
    game.stats.mana -= sp.mana;
    sp.cdTotal = sp.cd * (1 - Math.min(0.6, game.stats.cdr || 0)); sp.readyAt = game.time + sp.cdTotal;
    aim(target);
    try { KIND[sp.kind](sp, target); } catch (e) { console.warn('[classes] spell', sp.id, e); }
    sfx.play(sp.sfx); thrust = 1;
    game.emit('cast', { spell: sp.id, caster: 'player', slot: i, cls: caster.cls });
    return true;
  }

  // ---------- input ----------
  const canvas = document.getElementById('view');
  listen(window, 'keydown', e => {
    if (e.target instanceof HTMLInputElement || e.repeat || window.__explore || game.paused) return;
    const m = /^Digit([1-6])$/.exec(e.code);
    if (m) cast(+m[1] - 1);
  });
  listen(window, 'mousedown', e => {
    if (e.button === 0 && canvas && document.pointerLockElement === canvas && !game.paused) cast(0);
  });

  game.add({
    update(dt) { stepProjs(dt); stepWorld(dt); vfx.update(dt); updateStaff(dt); },
    dispose() {
      for (const f of offs) f();
      for (const m of cursed) m.damageTaken = 1;
      staff.traverse(o => { o.geometry?.dispose?.(); o.material?.dispose?.(); });
      vfx.dispose();
    },
  });
}
