// Mobs (session 40): mob types, procedural low-poly models + animation, AI, telegraphed attacks, encounters, boss.
// Frames: collision x east, y north, z up; three.js position = (x, z, -y). Models face local +Z (yaw = atan2(dx, -dy)).
// Encounter data lives in encounters.json (read by tooling too). Honours mob.slowUntil / mob.stunUntil / mob.damageTaken.
import * as THREE from 'three';

export const ENCOUNTERS = [];
const SPAWN_R = 120, DESPAWN_R = 200, RESPAWN_S = 90, MAX_LIVE = 24;
const TAU = Math.PI * 2;
const rnd = (a, b) => a + Math.random() * (b - a);

// ---------- shared geometry / materials (one copy for every instance)
const G = {
  box: new THREE.BoxGeometry(1, 1, 1),
  ico: new THREE.IcosahedronGeometry(0.5, 0),
  ico1: new THREE.IcosahedronGeometry(0.5, 1),
  oct: new THREE.OctahedronGeometry(0.5, 0),
  cyl: new THREE.CylinderGeometry(0.5, 0.5, 1, 8),
  cone: new THREE.ConeGeometry(0.5, 1, 6),
  bell: new THREE.CylinderGeometry(0.35, 0.9, 1.4, 10, 1, true),
  torus: new THREE.TorusGeometry(0.5, 0.12, 5, 12),
  wing: (() => { const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.Float32BufferAttribute([0, 0, 0, 1.4, 0.3, -0.2, 1.1, -0.4, -0.3, 0, 0, 0, 1.1, -0.4, -0.3, 0.4, -0.5, -0.1], 3)); g.computeVertexNormals(); return g; })(),
  ring: new THREE.RingGeometry(0.92, 1, 40).rotateX(-Math.PI / 2),
  disc: new THREE.CircleGeometry(1, 40).rotateX(-Math.PI / 2),
  rect: new THREE.PlaneGeometry(1, 1).rotateX(-Math.PI / 2).translate(0, 0, 0.5),   // unit strip along +Z from origin
  shard: new THREE.TetrahedronGeometry(0.18, 0),
  bolt: new THREE.IcosahedronGeometry(0.28, 0),
};
const BASE = {
  stone: new THREE.MeshStandardMaterial({ color: 0x8d8a80, roughness: 0.95, flatShading: true }),
  darkstone: new THREE.MeshStandardMaterial({ color: 0x5c5a55, roughness: 0.95, flatShading: true }),
  marble: new THREE.MeshStandardMaterial({ color: 0xd8d4c8, roughness: 0.7, flatShading: true }),
  ink: new THREE.MeshStandardMaterial({ color: 0x1a1730, roughness: 0.4, metalness: 0.2, flatShading: true }),
  parchment: new THREE.MeshStandardMaterial({ color: 0xd9c79a, roughness: 0.9, flatShading: true, side: THREE.DoubleSide }),
  brass: new THREE.MeshStandardMaterial({ color: 0xb58a3c, roughness: 0.35, metalness: 0.85, flatShading: true }),
  copper: new THREE.MeshStandardMaterial({ color: 0x9a5a35, roughness: 0.45, metalness: 0.7, flatShading: true }),
  iron: new THREE.MeshStandardMaterial({ color: 0x3b3d42, roughness: 0.6, metalness: 0.6, flatShading: true }),
  wisp: new THREE.MeshStandardMaterial({ color: 0x9fe8ff, emissive: 0x58c8ff, emissiveIntensity: 1.6, transparent: true, opacity: 0.8, flatShading: true }),
  eye: new THREE.MeshStandardMaterial({ color: 0xffb040, emissive: 0xff8a00, emissiveIntensity: 2 }),
  eyeBlue: new THREE.MeshStandardMaterial({ color: 0x80d0ff, emissive: 0x40a0ff, emissiveIntensity: 2 }),
  wingMat: new THREE.MeshStandardMaterial({ color: 0x6f6c66, roughness: 1, flatShading: true, side: THREE.DoubleSide }),
};
const decalMat = (c) => new THREE.MeshBasicMaterial({ color: c, transparent: true, opacity: 0.5, depthWrite: false, side: THREE.DoubleSide, polygonOffset: true, polygonOffsetFactor: -4 });
const boltMats = {};
const boltMat = c => boltMats[c] ||= new THREE.MeshBasicMaterial({ color: c });

// ---------- model builders: return {group, parts}; `m(name)` gives a per-instance material clone (for flash/glow)
function mesh(geo, mat, sx, sy, sz, x = 0, y = 0, z = 0, parent) {
  const o = new THREE.Mesh(geo, mat); o.scale.set(sx, sy, sz); o.position.set(x, y, z); o.castShadow = true; parent?.add(o); return o;
}
function pivot(parent, x = 0, y = 0, z = 0) { const g = new THREE.Group(); g.position.set(x, y, z); parent.add(g); return g; }

const MODELS = {
  gargoyle(m) {
    const g = new THREE.Group(), p = {};
    p.body = pivot(g, 0, 0.9, 0);
    mesh(G.ico, m('stone'), 0.9, 1.0, 1.1, 0, 0, 0, p.body);
    p.head = pivot(p.body, 0, 0.45, 0.45);
    mesh(G.box, m('stone'), 0.5, 0.42, 0.55, 0, 0, 0, p.head);
    mesh(G.cone, m('darkstone'), 0.12, 0.35, 0.12, -0.18, 0.32, -0.05, p.head);
    mesh(G.cone, m('darkstone'), 0.12, 0.35, 0.12, 0.18, 0.32, -0.05, p.head);
    mesh(G.box, BASE.eye, 0.1, 0.06, 0.05, -0.12, 0.05, 0.28, p.head); mesh(G.box, BASE.eye, 0.1, 0.06, 0.05, 0.12, 0.05, 0.28, p.head);
    mesh(G.box, m('darkstone'), 0.4, 0.12, 0.3, 0, -0.17, 0.2, p.head);  // jaw
    p.wl = pivot(p.body, -0.3, 0.25, -0.1); mesh(G.wing, BASE.wingMat, -1.1, 1.1, 1.1, 0, 0, 0, p.wl);
    p.wr = pivot(p.body, 0.3, 0.25, -0.1); mesh(G.wing, BASE.wingMat, 1.1, 1.1, 1.1, 0, 0, 0, p.wr);
    p.legL = mesh(G.box, m('darkstone'), 0.2, 0.5, 0.25, -0.25, -0.55, 0.1, p.body);
    p.legR = mesh(G.box, m('darkstone'), 0.2, 0.5, 0.25, 0.25, -0.55, 0.1, p.body);
    mesh(G.cone, m('darkstone'), 0.12, 0.8, 0.12, 0, -0.2, -0.65, p.body).rotation.x = -1.9;   // tail
    return { group: g, parts: p };
  },
  wisp(m) {
    const g = new THREE.Group(), p = {};
    p.body = pivot(g, 0, 0, 0);
    p.core = mesh(G.ico1, m('wisp'), 0.55, 0.55, 0.55, 0, 0, 0, p.body);
    p.halo = mesh(G.torus, BASE.wisp, 0.9, 0.9, 0.9, 0, 0, 0, p.body);
    p.motes = [];
    for (let i = 0; i < 3; i++) p.motes.push(mesh(G.oct, BASE.wisp, 0.18, 0.18, 0.18, 0, 0, 0, p.body));
    p.tail = mesh(G.cone, m('wisp'), 0.3, 0.8, 0.3, 0, -0.55, 0, p.body); p.tail.rotation.x = Math.PI;
    return { group: g, parts: p };
  },
  statue(m) {   // a robed scholar in Portland stone on a plinth stub
    const g = new THREE.Group(), p = {};
    p.body = pivot(g, 0, 0, 0);
    mesh(G.box, m('darkstone'), 1.1, 0.35, 1.1, 0, 0.17, 0, p.body);                 // plinth stub
    p.torso = pivot(p.body, 0, 0.35, 0);
    mesh(G.cyl, m('marble'), 0.9, 1.7, 0.75, 0, 0.85, 0, p.torso);                     // robe
    mesh(G.box, m('marble'), 1.15, 0.35, 0.6, 0, 1.75, 0, p.torso);                     // shoulders / gown yoke
    p.head = mesh(G.ico, m('marble'), 0.5, 0.58, 0.5, 0, 2.2, 0, p.torso);
    mesh(G.box, m('darkstone'), 0.7, 0.07, 0.7, 0, 2.52, 0, p.torso);                   // mortarboard
    mesh(G.box, BASE.eye, 0.08, 0.05, 0.04, -0.1, 2.24, 0.24, p.torso); mesh(G.box, BASE.eye, 0.08, 0.05, 0.04, 0.1, 2.24, 0.24, p.torso);
    p.armL = pivot(p.torso, -0.62, 1.7, 0); mesh(G.box, m('marble'), 0.3, 1.1, 0.3, 0, -0.5, 0, p.armL);
    p.armR = pivot(p.torso, 0.62, 1.7, 0); mesh(G.box, m('marble'), 0.3, 1.1, 0.3, 0, -0.5, 0, p.armR);
    mesh(G.box, m('darkstone'), 0.55, 0.7, 0.18, 0, -1.15, 0.1, p.armR);                // stone tome
    return { group: g, parts: p };
  },
  ink_imp(m) {   // a blot of library ink with a quill horn and paper-scrap wings
    const g = new THREE.Group(), p = {};
    p.body = pivot(g, 0, 0.45, 0);
    p.blob = mesh(G.ico1, m('ink'), 0.65, 0.55, 0.65, 0, 0, 0, p.body);
    mesh(G.cone, m('parchment'), 0.08, 0.55, 0.08, 0, 0.42, 0.05, p.body).rotation.x = 0.4;   // quill horn
    mesh(G.box, BASE.eyeBlue, 0.09, 0.09, 0.04, -0.12, 0.08, 0.3, p.body); mesh(G.box, BASE.eyeBlue, 0.09, 0.09, 0.04, 0.12, 0.08, 0.3, p.body);
    p.wl = pivot(p.body, -0.25, 0.15, -0.1); mesh(G.box, BASE.parchment, 0.45, 0.02, 0.3, -0.22, 0, 0, p.wl);
    p.wr = pivot(p.body, 0.25, 0.15, -0.1); mesh(G.box, BASE.parchment, 0.45, 0.02, 0.3, 0.22, 0, 0, p.wr);
    p.legL = mesh(G.cone, m('ink'), 0.12, 0.3, 0.12, -0.15, -0.35, 0, p.body); p.legL.rotation.x = Math.PI;
    p.legR = mesh(G.cone, m('ink'), 0.12, 0.3, 0.12, 0.15, -0.35, 0, p.body); p.legR.rotation.x = Math.PI;
    return { group: g, parts: p };
  },
  automaton(m) {   // a brass clockwork porter: barrel body, gear on the chest, piston legs
    const g = new THREE.Group(), p = {};
    p.body = pivot(g, 0, 0, 0);
    p.torso = pivot(p.body, 0, 1.15, 0);
    mesh(G.cyl, m('brass'), 0.95, 1.0, 0.8, 0, 0, 0, p.torso);
    p.gear = mesh(G.torus, m('copper'), 0.55, 0.55, 0.9, 0, 0.05, 0.42, p.torso);
    p.head = pivot(p.torso, 0, 0.7, 0);
    mesh(G.box, m('copper'), 0.5, 0.38, 0.45, 0, 0, 0, p.head);
    mesh(G.box, BASE.eye, 0.36, 0.06, 0.04, 0, 0.03, 0.23, p.head);
    mesh(G.cyl, m('iron'), 0.06, 0.4, 0.06, 0, 0.35, 0, p.head);                       // key / chimney
    p.armL = pivot(p.torso, -0.6, 0.3, 0); mesh(G.box, m('iron'), 0.22, 0.9, 0.22, 0, -0.45, 0, p.armL);
    p.armR = pivot(p.torso, 0.6, 0.3, 0); mesh(G.box, m('iron'), 0.22, 0.9, 0.22, 0, -0.45, 0, p.armR);
    p.legL = pivot(p.body, -0.25, 0.65, 0); mesh(G.cyl, m('iron'), 0.18, 0.65, 0.18, 0, -0.33, 0, p.legL);
    p.legR = pivot(p.body, 0.25, 0.65, 0); mesh(G.cyl, m('iron'), 0.18, 0.65, 0.18, 0, -0.33, 0, p.legR);
    return { group: g, parts: p };
  },
  bellwarden(m) {   // boss: a bronze bell for a body, carried on stone-and-iron legs, with clapper arms and a lantern crown
    const g = new THREE.Group(), p = {};
    p.body = pivot(g, 0, 0, 0);
    p.legL = pivot(p.body, -0.9, 1.6, 0); mesh(G.box, m('darkstone'), 0.6, 1.6, 0.7, 0, -0.8, 0, p.legL);
    p.legR = pivot(p.body, 0.9, 1.6, 0); mesh(G.box, m('darkstone'), 0.6, 1.6, 0.7, 0, -0.8, 0, p.legR);
    p.torso = pivot(p.body, 0, 2.0, 0);
    p.bell = mesh(G.bell, m('brass'), 1.9, 1.9, 1.9, 0, 1.2, 0, p.torso);
    mesh(G.cyl, m('brass'), 0.7, 0.4, 0.7, 0, 2.6, 0, p.torso);                        // crown of the bell
    mesh(G.torus, m('copper'), 1.75, 1.75, 1.75, 0, -0.05, 0, p.torso).rotation.x = Math.PI / 2;   // lip
    p.clapper = mesh(G.ico, m('iron'), 0.9, 0.9, 0.9, 0, 0.3, 0, p.torso);
    p.eye = mesh(G.ico, m('eyeglow'), 0.5, 0.5, 0.5, 0, 1.5, 0.95, p.torso);
    p.armL = pivot(p.torso, -1.6, 1.6, 0); mesh(G.box, m('iron'), 0.45, 2.0, 0.45, 0, -1.0, 0, p.armL); mesh(G.ico, m('iron'), 0.9, 0.9, 0.9, 0, -2.1, 0, p.armL);
    p.armR = pivot(p.torso, 1.6, 1.6, 0); mesh(G.box, m('iron'), 0.45, 2.0, 0.45, 0, -1.0, 0, p.armR); mesh(G.ico, m('iron'), 0.9, 0.9, 0.9, 0, -2.1, 0, p.armR);
    p.lantern = mesh(G.oct, BASE.eye, 0.5, 0.7, 0.5, 0, 3.3, 0, p.torso);
    return { group: g, parts: p };
  },
};
BASE.eyeglow = new THREE.MeshStandardMaterial({ color: 0xffc060, emissive: 0xff7a00, emissiveIntensity: 2.5 });

// ---------- attack definitions
// kinds: ring (circle around the mob or a target point), line (strip from the mob towards the aim), bolt (projectile),
// charge (mob dashes along the line), leap (mob jumps to the target point and slams), nova (radial bolts), cascade (rings on the player).
// Each: {name, kind, range, windup, cd, dmg, r?, len?, w?, speed?, n?}
const A = (o) => ({ cd: 3, windup: 0.8, recover: 0.5, ...o });

const D = (o) => ({ hp: 60, speed: 3, radius: 0.5, xp: 15, aggro: 18, leash: 40, flying: false, hover: 0, scale: 1, color: 0xff5040, ...o });
export const MOB_TYPES = [
  D({ id: 'gargoyle', name: 'Rooftop Gargoyle', hp: 70, speed: 4.2, radius: 0.6, xp: 22, flying: true, hover: 3.5, color: 0xff8a20,
      loot: [{ rarity: 'common', chance: 0.6 }, { rarity: 'uncommon', chance: 0.25 }, { rarity: 'rare', chance: 0.06 }],
      attacks: [A({ name: 'Swoop', kind: 'charge', range: 11, len: 12, w: 1.8, windup: 0.9, cd: 4, dmg: 14, speed: 18 }),
                A({ name: 'Rake', kind: 'ring', range: 2.4, r: 2.2, windup: 0.6, cd: 2, dmg: 8, onTarget: false })] }),
  D({ id: 'wisp', name: "Will-o'-the-Cam", hp: 40, speed: 3.2, radius: 0.45, xp: 18, flying: true, hover: 1.6, keepAway: 7, color: 0x58c8ff,
      loot: [{ rarity: 'common', chance: 0.5 }, { rarity: 'uncommon', chance: 0.3 }, { rarity: 'rare', chance: 0.08 }],
      attacks: [A({ name: 'Marsh Bolt', kind: 'bolt', range: 14, windup: 0.7, cd: 2.2, dmg: 9, speed: 13 }),
                A({ name: 'Flicker Nova', kind: 'ring', range: 3.5, r: 3.5, windup: 1.0, cd: 5, dmg: 12 })] }),
  D({ id: 'statue', name: 'Wakened Founder Statue', hp: 160, speed: 1.6, radius: 0.8, xp: 35, color: 0xffd080, knockResist: 0.8,
      loot: [{ rarity: 'common', chance: 0.7 }, { rarity: 'uncommon', chance: 0.4 }, { rarity: 'rare', chance: 0.12 }, { rarity: 'epic', chance: 0.02 }],
      attacks: [A({ name: 'Tome Slam', kind: 'ring', range: 3.2, r: 3.6, windup: 1.3, cd: 3.5, dmg: 24, recover: 0.9 }),
                A({ name: 'Plinth Leap', kind: 'leap', range: 10, minRange: 4, r: 3, windup: 1.2, cd: 7, dmg: 20, recover: 1 })] }),
  D({ id: 'ink_imp', name: 'Library Ink Imp', hp: 28, speed: 5.6, radius: 0.35, xp: 10, scale: 0.9, color: 0x6060ff,
      loot: [{ rarity: 'common', chance: 0.45 }, { rarity: 'uncommon', chance: 0.12 }],
      attacks: [A({ name: 'Nib Bite', kind: 'line', range: 1.8, len: 2.2, w: 1.2, windup: 0.35, cd: 1.1, dmg: 5, recover: 0.25 }),
                A({ name: 'Ink Spit', kind: 'bolt', range: 9, minRange: 3, windup: 0.5, cd: 3, dmg: 6, speed: 11, color: 0x30206a })] }),
  D({ id: 'automaton', name: 'Clockwork Porter', hp: 95, speed: 2.8, radius: 0.6, xp: 26, color: 0xffb040,
      loot: [{ rarity: 'common', chance: 0.6 }, { rarity: 'uncommon', chance: 0.3 }, { rarity: 'rare', chance: 0.1 }],
      attacks: [A({ name: 'Wound-Spring Charge', kind: 'charge', range: 12, minRange: 3, len: 13, w: 1.6, windup: 1.0, cd: 5, dmg: 18, speed: 16 }),
                A({ name: 'Gear Whirl', kind: 'ring', range: 2.6, r: 2.8, windup: 0.7, cd: 2.5, dmg: 10 })] }),
  D({ id: 'bellwarden', name: 'The Bellwarden of Market Hill', boss: true, hp: 900, speed: 2.4, radius: 1.6, xp: 400, scale: 1, aggro: 16, leash: 34,
      color: 0xffa020, knockResist: 1,
      loot: [{ rarity: 'uncommon', chance: 1 }, { rarity: 'rare', chance: 0.8 }, { rarity: 'epic', chance: 0.4 }, { rarity: 'legendary', chance: 0.12 }],
      phases: [
        { at: 1.0, attacks: ['toll', 'sweep'] },
        { at: 0.66, attacks: ['toll', 'sweep', 'peal', 'leap'], speed: 1.15 },
        { at: 0.33, attacks: ['toll', 'peal', 'leap', 'cascade', 'sweep'], speed: 1.4, windup: 0.75, cd: 0.7, enrage: true },
      ],
      attacks: [A({ id: 'toll', name: 'Great Toll', kind: 'ring', range: 5, r: 6, windup: 1.4, cd: 4, dmg: 26, recover: 0.8 }),
                A({ id: 'sweep', name: 'Clapper Sweep', kind: 'line', range: 6, len: 7.5, w: 3.2, windup: 1.0, cd: 3, dmg: 20 }),
                A({ id: 'peal', name: 'Peal of Shards', kind: 'nova', range: 18, n: 10, windup: 1.2, cd: 6, dmg: 12, speed: 12 }),
                A({ id: 'leap', name: 'Belfry Drop', kind: 'leap', range: 16, minRange: 6, r: 4.5, windup: 1.3, cd: 8, dmg: 30, recover: 1.2 }),
                A({ id: 'cascade', name: 'Change-Ringing Cascade', kind: 'cascade', range: 22, n: 4, r: 2.6, windup: 1.1, cd: 7, dmg: 18 })] }),
];
const TYPE = Object.fromEntries(MOB_TYPES.map(t => [t.id, t]));

// ---------- the system
let NEXT_ID = 1;
class MobSystem {
  constructor(game) {
    this.game = game; this.world = game.world; this.root = new THREE.Group(); this.root.name = 'mobs'; game.root.add(this.root);
    this.fx = [];            // {update(dt) -> bool alive}
    this.projectiles = [];
    this.encounterState = new Map();
    this.encountersEnabled = true;
    this.encT = 0;
  }

  // --- ground helpers
  ground(x, y, feet) {
    if (feet == null) { const s = this.world.support(x, y, 1e4); if (!s || s.kind !== 1) return null; feet = s.z; }
    return this.world.standAt(x, y, feet);
  }
  findSpot(x, y, maxR = 20) {
    for (let r = 0; r <= maxR; r += 1.5) {
      const n = r === 0 ? 1 : Math.ceil(r * 2);
      for (let i = 0; i < n; i++) {
        const a = i / n * TAU + r, px = x + Math.cos(a) * r, py = y + Math.sin(a) * r;
        const z = this.ground(px, py);
        if (z != null) return { x: px, y: py, z };
      }
    }
    return null;
  }

  spawn(typeId, x, y, z, opts = {}) {
    const type = TYPE[typeId]; if (!type) throw new Error('unknown mob type ' + typeId);
    if (z == null) { const s = this.findSpot(x, y, 12); if (s) ({ x, y, z } = s); else z = this.game.groundAt(x, y) ?? this.game.pz; }
    const mats = [];
    const m = (name) => { const c = BASE[name].clone(); mats.push(c); return c; };
    const { group, parts } = MODELS[type.id](m);
    group.scale.setScalar(type.scale);
    this.root.add(group);
    const mob = {
      id: NEXT_ID++, type, name: type.name, boss: !!type.boss, x, y, z, groundZ: z, hp: type.hp, maxHp: type.hp, dead: false,
      radius: type.radius, xp: type.xp, state: 'idle', home: { x, y, z }, yaw: rnd(0, TAU), group, parts, mats,
      attackCd: {}, t: rnd(0, 10), stateT: 0, flashT: 0, glow: 0, phase: 0, encounter: opts.encounter || null,
      patrol: null, idleT: rnd(0.5, 2), hitPlayer: false, damageTaken: 1, slowUntil: 0, stunUntil: 0,
    };
    mob.baseEmissive = mats.map(c => ({ c: c.emissive.clone(), i: c.emissiveIntensity }));
    mob.onHit = (dmg, o) => this.onHit(mob, dmg, o);
    mob.onDeath = () => this.onDeath(mob);
    if (type.flying) mob.z = z + type.hover;
    this.place(mob);
    this.game.mobs.push(mob);
    return mob;
  }

  place(mob) { mob.group.position.set(mob.x, mob.z, -mob.y); mob.group.rotation.y = mob.yaw; }
  remove(mob) {
    this.root.remove(mob.group); for (const c of mob.mats) c.dispose();
    mob.telegraph && this.clearTelegraph(mob);
    const i = this.game.mobs.indexOf(mob); if (i >= 0) this.game.mobs.splice(i, 1);
    mob.removed = true;
  }

  onHit(mob, dmg, o) {
    mob.flashT = 0.14;
    const g = this.game, k = (1 - (mob.type.knockResist ?? 0)) * Math.min(1.2, 0.3 + dmg / 40);
    if (k > 0.02) {
      const dx = mob.x - g.px, dy = mob.y - g.py, d = Math.hypot(dx, dy) || 1;
      const nx = mob.x + dx / d * k, ny = mob.y + dy / d * k;
      if (mob.type.flying) { mob.x = nx; mob.y = ny; }
      else { const z = this.world.standAt(nx, ny, mob.groundZ); if (z != null) { mob.x = nx; mob.y = ny; mob.groundZ = mob.z = z; } }
    }
    if (mob.state === 'idle' || mob.state === 'patrol' || mob.state === 'return') mob.state = 'chase';
    // boss phase changes
    if (mob.type.phases) {
      const f = mob.hp / mob.maxHp;
      let ph = 0; mob.type.phases.forEach((p, i) => { if (f <= p.at) ph = i; });
      if (ph > mob.phase) {
        mob.phase = ph; this.clearTelegraph(mob); mob.state = 'stagger'; mob.stateT = 1.2;
        this.burst(mob.x, mob.y, mob.z + 3, mob.type.color, 18, 6);
        g.emit('bossPhase', { mob, phase: ph, enrage: !!mob.type.phases[ph].enrage });
      }
    }
  }

  onDeath(mob) {
    this.clearTelegraph(mob);
    mob.state = 'dead'; mob.deathT = 0;
    this.burst(mob.x, mob.y, mob.z + 1 * mob.type.scale * (mob.boss ? 2.5 : 1), mob.type.color, mob.boss ? 40 : 16, mob.boss ? 9 : 5, mob.mats[0]?.color);
    const es = mob.encounter && this.encounterState.get(mob.encounter);
    if (es && es.mobs.every(m => m.dead)) { es.clearedAt = this.game.time; }
  }

  // shatter particles: shared shard geometry, one material per burst (faded together)
  burst(x, y, z, color, n, speed, tint) {
    const mat = new THREE.MeshStandardMaterial({ color: tint ? tint.getHex() : color, emissive: color, emissiveIntensity: 0.8, transparent: true, flatShading: true });
    const g = new THREE.Group(); this.root.add(g);
    const parts = [];
    for (let i = 0; i < n; i++) {
      const s = new THREE.Mesh(G.shard, mat); s.position.set(x, z, -y);
      const a = rnd(0, TAU), up = rnd(0.3, 1);
      parts.push({ s, v: new THREE.Vector3(Math.cos(a) * speed * rnd(0.3, 1), up * speed, Math.sin(a) * speed * rnd(0.3, 1)), r: rnd(-8, 8) });
      g.add(s);
    }
    let t = 0;
    this.fx.push({ update: (dt) => {
      t += dt;
      for (const p of parts) { p.v.y -= 12 * dt; p.s.position.addScaledVector(p.v, dt); p.s.rotation.x += p.r * dt; p.s.rotation.z += p.r * dt; }
      mat.opacity = Math.max(0, 1 - t / 1.2);
      if (t > 1.2) { this.root.remove(g); mat.dispose(); return false; }
      return true;
    } });
  }

  // --- telegraphs: ground decals (ring / filled disc that grows, or a strip)
  decal(kind, x, y, z, color, a) {
    const mat = decalMat(color);
    const grp = new THREE.Group(); grp.position.set(x, z + 0.06, -y); this.root.add(grp);
    if (kind === 'ring') {
      const edge = new THREE.Mesh(G.ring, mat); edge.scale.setScalar(a.r); grp.add(edge);
      const fill = new THREE.Mesh(G.disc, mat); fill.scale.setScalar(0.01); grp.add(fill);
      return { grp, mat, fill, r: a.r, kind };
    }
    const strip = new THREE.Mesh(G.rect, mat); strip.scale.set(a.w, 1, a.len); grp.add(strip);
    const fill = new THREE.Mesh(G.rect, mat); fill.scale.set(a.w * 0.9, 1, 0.01); grp.add(fill);
    grp.rotation.y = a.yaw;
    return { grp, mat, fill, len: a.len, w: a.w, kind };
  }
  setDecal(d, f) {   // f = wind-up progress 0..1
    d.mat.opacity = 0.25 + 0.45 * f;
    if (d.kind === 'ring') d.fill.scale.setScalar(Math.max(0.01, d.r * f));
    else d.fill.scale.set(d.w * 0.9, 1, Math.max(0.01, d.len * f));
  }
  killDecal(d) { this.root.remove(d.grp); d.mat.dispose(); }
  clearTelegraph(mob) { for (const d of mob.telegraph || []) this.killDecal(d); mob.telegraph = null; }

  // --- per-frame
  update(dt) {
    const g = this.game;
    this.encT -= dt; if (this.encT <= 0) { this.encT = 0.5; this.updateEncounters(); }
    for (const mob of [...g.mobs]) this.updateMob(mob, dt);
    for (let i = this.projectiles.length - 1; i >= 0; i--) if (!this.updateProjectile(this.projectiles[i], dt)) this.projectiles.splice(i, 1);
    for (let i = this.fx.length - 1; i >= 0; i--) if (!this.fx[i].update(dt)) this.fx.splice(i, 1);
  }

  updateEncounters() {
    const g = this.game;
    for (const e of ENCOUNTERS) {
      let s = this.encounterState.get(e.id);
      if (!s) { s = { mobs: [], active: false, clearedAt: null, spot: null }; this.encounterState.set(e.id, s); }
      const d = Math.hypot(e.x - g.px, e.y - g.py);
      if (s.active && d > DESPAWN_R) { for (const m of s.mobs) if (!m.removed) this.remove(m); s.mobs = []; s.active = false; continue; }
      if (s.active && s.clearedAt != null && g.time - s.clearedAt > RESPAWN_S && d > 40) { s.active = false; s.mobs = []; s.clearedAt = null; }
      if (!this.encountersEnabled || s.active || d > SPAWN_R || g.mobs.length >= MAX_LIVE) continue;
      if (!this.world.covered(e.x, e.y)) continue;   // tiles not streamed yet
      const placed = [];
      for (let i = 0; i < e.mobs.length; i++) {
        const a = i / e.mobs.length * TAU + rnd(0, 1), rr = e.mobs.length > 1 ? e.r * rnd(0.3, 0.9) : 0;
        const spot = this.findSpot(e.x + Math.cos(a) * rr, e.y + Math.sin(a) * rr, 20);
        if (spot) placed.push([e.mobs[i], spot]);
      }
      if (!placed.length) continue;
      s.active = true; s.clearedAt = null;
      s.mobs = placed.map(([t, p]) => this.spawn(t, p.x, p.y, p.z, { encounter: e.id }));
      s.spot = placed[0][1];
    }
  }

  updateMob(mob, dt) {
    const g = this.game, T = mob.type, P = mob.parts;
    mob.t += dt;
    if (mob.state === 'dead') {   // dissolve: sink, shrink, then remove
      mob.deathT += dt; const f = Math.min(1, mob.deathT / 0.9);
      mob.group.scale.setScalar(T.scale * (1 - f * 0.9)); mob.group.position.y = mob.z - f * 0.5 * T.scale;
      for (const c of mob.mats) { c.transparent = true; c.opacity = 1 - f; }
      if (mob.deathT > 1.0) this.remove(mob);
      return;
    }
    // flash + glow
    mob.flashT = Math.max(0, mob.flashT - dt);
    const glow = mob.state === 'windup' ? 0.4 + 0.6 * Math.min(1, 1 - mob.stateT / mob.windupEff) : 0;
    mob.mats.forEach((c, i) => {
      if (mob.flashT > 0) { c.emissive.setRGB(1, 1, 1); c.emissiveIntensity = 1.2; }
      else if (glow > 0) { c.emissive.setHex(T.color); c.emissiveIntensity = glow * (0.6 + 0.4 * Math.sin(mob.t * 30)); }
      else { c.emissive.copy(mob.baseEmissive[i].c); c.emissiveIntensity = mob.baseEmissive[i].i; }
    });
    const stunned = mob.stunUntil > g.time;
    const speedMul = (mob.slowUntil > g.time ? 0.5 : 1) * (T.phases?.[mob.phase]?.speed ?? 1);
    const dx = g.px - mob.x, dy = g.py - mob.y, dist = Math.hypot(dx, dy), homeD = Math.hypot(mob.x - mob.home.x, mob.y - mob.home.y);
    let moving = 0;
    for (const k in mob.attackCd) mob.attackCd[k] -= dt * (stunned ? 0 : 1);

    if (stunned) {
      if (mob.state === 'windup') { this.clearTelegraph(mob); mob.state = 'chase'; }
    } else switch (mob.state) {
      case 'idle': case 'patrol': {
        if (dist < T.aggro && g.stats.hp > 0 && Math.abs(g.pz - mob.groundZ) < 8) { mob.state = 'chase'; break; }
        if (mob.state === 'idle') { mob.idleT -= dt; if (mob.idleT <= 0) { const a = rnd(0, TAU), r = rnd(2, 7); mob.patrol = { x: mob.home.x + Math.cos(a) * r, y: mob.home.y + Math.sin(a) * r }; mob.state = 'patrol'; } }
        else { moving = this.moveTo(mob, mob.patrol.x, mob.patrol.y, T.speed * 0.4 * speedMul, dt); if (!moving || Math.hypot(mob.patrol.x - mob.x, mob.patrol.y - mob.y) < 0.6) { mob.state = 'idle'; mob.idleT = rnd(1.5, 4); } }
        break;
      }
      case 'chase': {
        if (homeD > T.leash || dist > T.leash * 1.4 || g.stats.hp <= 0) { mob.state = 'return'; break; }
        const atk = this.pickAttack(mob, dist);
        if (atk) { this.beginAttack(mob, atk); break; }
        const keep = T.keepAway ?? 0;
        if (keep && dist < keep - 1) moving = this.moveTo(mob, mob.x - dx, mob.y - dy, T.speed * speedMul, dt);
        else if (dist > Math.max(keep, mob.radius + 1.2)) moving = this.moveTo(mob, g.px, g.py, T.speed * speedMul, dt);
        else mob.yaw = this.turn(mob.yaw, Math.atan2(dx, -dy), dt * 6);
        break;
      }
      case 'return': {
        moving = this.moveTo(mob, mob.home.x, mob.home.y, T.speed * 1.5, dt, true);
        mob.hp = Math.min(mob.maxHp, mob.hp + mob.maxHp * 0.5 * dt);
        if (homeD < 1 || !moving) { mob.hp = mob.maxHp; mob.phase = 0; mob.state = 'idle'; mob.idleT = 1; if (!moving) { mob.x = mob.home.x; mob.y = mob.home.y; mob.groundZ = mob.home.z; } }
        break;
      }
      case 'windup': this.tickWindup(mob, dt); break;
      case 'active': this.tickActive(mob, dt); moving = 2; break;
      case 'recover': case 'stagger': mob.stateT -= dt; if (mob.stateT <= 0) mob.state = 'chase'; break;
    }
    // vertical: flying hover over ground / bob towards player height; walkers stick to their ground
    if (T.flying) {
      const gz = this.game.groundAt(mob.x, mob.y, Math.max(mob.z, g.pz) + 2) ?? mob.groundZ;
      mob.groundZ = gz;
      const swoop = mob.state === 'active' && mob.attack?.kind === 'charge';
      const target = swoop ? g.pz + 0.9 : Math.max(gz, mob.state === 'chase' ? g.pz : gz) + T.hover + Math.sin(mob.t * 2) * 0.25;
      mob.z += (target - mob.z) * Math.min(1, dt * (swoop ? 8 : 2.5));
    } else if (mob.state !== 'active' || mob.attack?.kind !== 'leap') mob.z = mob.groundZ;
    this.animate(mob, dt, moving);
    this.place(mob);
  }

  turn(a, b, k) { let d = ((b - a + Math.PI) % TAU + TAU) % TAU - Math.PI; return a + Math.max(-k, Math.min(k, d)); }

  // steer towards (tx, ty); walkers slide along walls by trying deflected headings. Returns 1 if moved.
  moveTo(mob, tx, ty, speed, dt, ignoreGround = false) {
    const dx = tx - mob.x, dy = ty - mob.y, d = Math.hypot(dx, dy);
    if (d < 0.05) return 0;
    const step = Math.min(d, speed * dt), base = Math.atan2(dy, dx);
    for (const off of [0, 0.5, -0.5, 1.0, -1.0, 1.5, -1.5]) {
      const a = base + off, nx = mob.x + Math.cos(a) * step, ny = mob.y + Math.sin(a) * step;
      if (mob.type.flying) { mob.x = nx; mob.y = ny; }
      else {
        const z = this.world.standAt(nx, ny, mob.groundZ);
        if (z == null || Math.abs(z - mob.groundZ) > 0.6) continue;
        mob.x = nx; mob.y = ny; mob.groundZ = z;
      }
      mob.yaw = this.turn(mob.yaw, Math.atan2(Math.cos(a), -Math.sin(a)), dt * 8);
      return 1;
    }
    return 0;
  }

  attacksFor(mob) {
    const T = mob.type;
    if (!T.phases) return T.attacks;
    const ids = T.phases[mob.phase].attacks; return T.attacks.filter(a => ids.includes(a.id));
  }
  pickAttack(mob, dist) {
    const ok = this.attacksFor(mob).filter(a => (mob.attackCd[a.name] ?? 0) <= 0 && dist <= a.range && dist >= (a.minRange ?? 0));
    if (!ok.length) return null;
    return ok[Math.floor(Math.random() * ok.length)];
  }

  beginAttack(mob, a) {
    const g = this.game, ph = mob.type.phases?.[mob.phase];
    mob.attack = a; mob.windupEff = a.windup * (ph?.windup ?? 1);
    mob.state = 'windup'; mob.stateT = mob.windupEff; mob.hitPlayer = false;
    mob.attackCd[a.name] = a.cd * (ph?.cd ?? 1);
    const dx = g.px - mob.x, dy = g.py - mob.y;
    const yaw = Math.atan2(dx, -dy); mob.yaw = yaw;
    mob.aim = { x: g.px, y: g.py, z: g.pz, yaw, dir: { x: dx / (Math.hypot(dx, dy) || 1), y: dy / (Math.hypot(dx, dy) || 1) } };
    const gz = mob.type.flying ? (mob.groundZ ?? g.pz) : mob.z, col = mob.boss ? 0xff3010 : 0xff5030;
    const t = [];
    if (a.kind === 'ring') t.push(this.decal('ring', mob.x, mob.y, gz, col, { r: a.r }));
    else if (a.kind === 'leap') t.push(this.decal('ring', g.px, g.py, g.pz, col, { r: a.r }));
    else if (a.kind === 'line' || a.kind === 'charge') t.push(this.decal('line', mob.x, mob.y, gz, col, { w: a.w, len: a.len, yaw }));
    else if (a.kind === 'bolt') t.push(this.decal('line', mob.x, mob.y, Math.min(gz, g.pz), a.color ?? 0x58c8ff, { w: 0.35, len: Math.hypot(dx, dy), yaw }));
    else if (a.kind === 'nova') for (let i = 0; i < a.n; i++) t.push(this.decal('line', mob.x, mob.y, gz, col, { w: 0.6, len: a.range, yaw: yaw + i / a.n * TAU }));
    else if (a.kind === 'cascade') {
      mob.aim.points = [{ x: g.px, y: g.py, z: g.pz }];
      for (let i = 1; i < a.n; i++) { const p = this.findSpot(g.px + rnd(-6, 6), g.py + rnd(-6, 6), 3); if (p) mob.aim.points.push(p); }
      for (const p of mob.aim.points) t.push(this.decal('ring', p.x, p.y, p.z, col, { r: a.r }));
    }
    mob.telegraph = t;
  }

  tickWindup(mob, dt) {
    const a = mob.attack;
    mob.stateT -= dt;
    const f = 1 - Math.max(0, mob.stateT) / mob.windupEff;
    for (const d of mob.telegraph || []) this.setDecal(d, f);
    if (mob.stateT > 0) return;
    const g = this.game;
    this.clearTelegraph(mob);
    if (a.kind === 'ring') {
      this.burst(mob.x, mob.y, mob.type.flying ? mob.groundZ : mob.z, mob.type.color, 8, 4);
      if (Math.hypot(g.px - mob.x, g.py - mob.y) <= a.r + 0.3) this.hit(mob, a.dmg);
      this.recover(mob);
    } else if (a.kind === 'line') {
      if (this.inStrip(mob.x, mob.y, mob.aim.dir, a.len, a.w, g.px, g.py)) this.hit(mob, a.dmg);
      this.recover(mob);
    } else if (a.kind === 'bolt') {
      this.shoot(mob, mob.aim.dir, a);
      this.recover(mob);
    } else if (a.kind === 'nova') {
      for (let i = 0; i < a.n; i++) { const yy = mob.aim.yaw + i / a.n * TAU; this.shoot(mob, { x: Math.sin(yy), y: -Math.cos(yy) }, a); }
      this.recover(mob);
    } else if (a.kind === 'cascade') {
      for (const p of mob.aim.points) { this.burst(p.x, p.y, p.z, mob.type.color, 6, 4); if (Math.hypot(g.px - p.x, g.py - p.y) <= a.r + 0.3) { this.hit(mob, a.dmg); break; } }
      this.recover(mob);
    } else if (a.kind === 'charge') {
      mob.state = 'active'; mob.stateT = a.len / a.speed; mob.charge = { x: mob.x, y: mob.y, left: a.len };
    } else if (a.kind === 'leap') {
      mob.state = 'active'; mob.stateT = 0.6; mob.leap = { x0: mob.x, y0: mob.y, z0: mob.z, t: 0 };
    }
  }

  tickActive(mob, dt) {
    const a = mob.attack, g = this.game;
    if (a.kind === 'charge') {
      const step = a.speed * dt; let moved = false;
      const nx = mob.x + mob.aim.dir.x * step, ny = mob.y + mob.aim.dir.y * step;
      if (mob.type.flying) { mob.x = nx; mob.y = ny; moved = true; }
      else { const z = this.world.standAt(nx, ny, mob.groundZ); if (z != null && Math.abs(z - mob.groundZ) < 0.6) { mob.x = nx; mob.y = ny; mob.groundZ = mob.z = z; moved = true; } }
      mob.charge.left -= step;
      if (!mob.hitPlayer && Math.hypot(g.px - mob.x, g.py - mob.y) < a.w / 2 + mob.radius && (!mob.type.flying || Math.abs(g.pz + 1 - mob.z) < 2.5)) { mob.hitPlayer = true; this.hit(mob, a.dmg); }
      if (!moved || mob.charge.left <= 0) this.recover(mob);
    } else if (a.kind === 'leap') {
      const L = mob.leap; L.t += dt; const f = Math.min(1, L.t / 0.6);
      const tz = mob.aim.z;
      const nx = L.x0 + (mob.aim.x - L.x0) * f, ny = L.y0 + (mob.aim.y - L.y0) * f;
      mob.x = nx; mob.y = ny; mob.z = L.z0 + (tz - L.z0) * f + Math.sin(f * Math.PI) * 4;
      if (f >= 1) {
        const z = this.ground(mob.x, mob.y, tz);
        if (z == null) { const s = this.findSpot(mob.x, mob.y, 4); if (s) { mob.x = s.x; mob.y = s.y; mob.groundZ = mob.z = s.z; } else { mob.x = L.x0; mob.y = L.y0; mob.groundZ = mob.z = L.z0; } }
        else mob.groundZ = mob.z = z;
        this.burst(mob.x, mob.y, mob.z, mob.type.color, 12, 5);
        if (Math.hypot(g.px - mob.aim.x, g.py - mob.aim.y) <= a.r + 0.3) this.hit(mob, a.dmg);
        this.recover(mob);
      }
    }
  }
  recover(mob) { mob.state = 'recover'; mob.stateT = mob.attack.recover; }
  inStrip(x, y, dir, len, w, px, py) {
    const rx = px - x, ry = py - y, along = rx * dir.x + ry * dir.y, perp = Math.abs(rx * dir.y - ry * dir.x);
    return along >= -0.5 && along <= len && perp <= w / 2 + 0.3;
  }
  hit(mob, dmg) { this.game.damagePlayer(dmg, mob); mob.lastHitPlayerAt = this.game.time; }

  shoot(mob, dir, a) {
    const m = new THREE.Mesh(G.bolt, boltMat(a.color ?? (mob.boss ? 0xffa030 : 0x9fe8ff)));
    const z = mob.z + (mob.type.flying ? 0 : 1.2 * mob.type.scale * (mob.boss ? 2 : 1));
    this.root.add(m);
    const g = this.game, tz = mob.aim.z + 1;
    this.projectiles.push({ mob, m, x: mob.x, y: mob.y, z, vx: dir.x * a.speed, vy: dir.y * a.speed, vz: mob.boss ? 0 : (tz - z) / (Math.hypot(g.px - mob.x, g.py - mob.y) / a.speed + 1e-3), dmg: a.dmg, life: (a.range + 4) / a.speed });
  }
  updateProjectile(p, dt) {
    const g = this.game;
    p.life -= dt; p.x += p.vx * dt; p.y += p.vy * dt; p.z += p.vz * dt;
    p.m.position.set(p.x, p.z, -p.y); p.m.rotation.x += dt * 9;
    if (Math.hypot(g.px - p.x, g.py - p.y) < 0.75 && p.z > g.pz - 0.3 && p.z < g.pz + 2.2) { this.hit(p.mob, p.dmg); p.life = 0; this.burst(p.x, p.y, p.z, 0x9fe8ff, 5, 3); }
    if (p.life <= 0) { this.root.remove(p.m); return false; }
    return true;
  }

  // --- procedural animation per type
  animate(mob, dt, moving) {
    const P = mob.parts, t = mob.t, st = mob.state, wf = st === 'windup' ? 1 - mob.stateT / mob.windupEff : 0;
    const walk = moving ? Math.sin(t * (mob.type.speed * 2.5)) : 0;
    switch (mob.type.id) {
      case 'gargoyle': {
        const flap = Math.sin(t * (st === 'active' ? 4 : 9)) * (st === 'active' ? 0.2 : 0.6);
        P.wl.rotation.z = flap + (st === 'windup' ? 0.9 * wf : 0); P.wr.rotation.z = -P.wl.rotation.z;
        P.body.rotation.x = st === 'active' ? 0.7 : st === 'windup' ? -0.4 * wf : 0.1;
        P.head.rotation.x = Math.sin(t * 1.3) * 0.15;
        break;
      }
      case 'wisp': {
        P.halo.rotation.x = t * 1.7; P.halo.rotation.y = t * 1.1;
        P.motes.forEach((o, i) => { const a = t * 2.4 + i * TAU / 3; o.position.set(Math.cos(a) * 0.8, Math.sin(t * 3 + i) * 0.3, Math.sin(a) * 0.8); });
        const s = 1 + Math.sin(t * 5) * 0.08 + wf * 0.5; P.core.scale.setScalar(0.55 * s);
        P.tail.rotation.z = Math.sin(t * 3) * 0.3;
        break;
      }
      case 'statue': {
        P.armL.rotation.x = walk * 0.3; P.armR.rotation.x = st === 'windup' ? -2.6 * wf : -walk * 0.3;
        if (st === 'recover' && mob.attack?.kind === 'ring') P.armR.rotation.x = 0.4;
        P.torso.rotation.z = walk * 0.06; P.body.position.y = moving ? Math.abs(walk) * 0.08 : 0;
        P.torso.rotation.x = st === 'windup' ? -0.2 * wf : st === 'recover' ? 0.25 : 0;
        break;
      }
      case 'ink_imp': {
        P.wl.rotation.z = Math.sin(t * 22) * 0.7; P.wr.rotation.z = -P.wl.rotation.z;
        P.body.position.y = 0.45 + Math.abs(Math.sin(t * (moving ? 14 : 4))) * (moving ? 0.25 : 0.06);
        P.blob.scale.set(0.65 + wf * 0.2, 0.55 - wf * 0.15, 0.65 + wf * 0.2);
        P.legL.rotation.z = walk * 0.5; P.legR.rotation.z = -walk * 0.5;
        break;
      }
      case 'automaton': {
        P.gear.rotation.z += dt * (st === 'windup' ? 25 : st === 'active' ? 40 : 2);
        P.legL.rotation.x = walk * 0.5 + (st === 'active' ? Math.sin(t * 30) * 0.7 : 0); P.legR.rotation.x = -P.legL.rotation.x;
        P.armL.rotation.x = -walk * 0.4; P.armR.rotation.x = walk * 0.4;
        P.torso.rotation.x = st === 'windup' ? 0.35 * wf : st === 'active' ? 0.4 : 0;
        if (st === 'windup' && mob.attack.kind === 'ring') { P.armL.rotation.z = -1.3 * wf; P.armR.rotation.z = 1.3 * wf; P.torso.rotation.y = wf * 6; }
        else { P.armL.rotation.z = P.armR.rotation.z = 0; P.torso.rotation.y = 0; }
        P.head.rotation.y = Math.sin(t * 0.8) * 0.4;
        break;
      }
      case 'bellwarden': {
        const enr = mob.type.phases[mob.phase].enrage;
        P.legL.rotation.x = walk * 0.35; P.legR.rotation.x = -walk * 0.35;
        P.torso.rotation.z = Math.sin(t * 1.2) * 0.05 + walk * 0.05;
        P.clapper.position.x = Math.sin(t * (enr ? 6 : 2)) * 0.4;
        const k = mob.attack?.kind;
        P.armL.rotation.x = P.armR.rotation.x = 0; P.armL.rotation.z = -0.15; P.armR.rotation.z = 0.15;
        if (st === 'windup') {
          if (k === 'ring' || k === 'leap') { P.armL.rotation.z = -2.6 * wf; P.armR.rotation.z = 2.6 * wf; }
          else if (k === 'line') { P.armR.rotation.x = -2.2 * wf; }
          else { P.torso.rotation.y = wf * 2; }
        }
        if (st === 'stagger') P.torso.rotation.x = Math.sin(t * 25) * 0.1;
        P.lantern.rotation.y = t * 2;
        P.eye.material.emissive.setHex(enr ? 0xff2000 : 0xff7a00);
        break;
      }
    }
  }

  dispose() {
    for (const m of [...this.game.mobs]) this.remove(m);
    for (const p of this.projectiles) this.root.remove(p.m);
    this.game.root.remove(this.root);
  }
}

export async function loadEncounters() {
  if (ENCOUNTERS.length) return ENCOUNTERS;
  const r = await fetch(new URL('./encounters.json', import.meta.url));
  ENCOUNTERS.push(...await r.json());
  return ENCOUNTERS;
}

export function install(game) {
  const sys = game.add(new MobSystem(game));
  game.mobSystem = sys; game.mobTypes = MOB_TYPES; game.encounters = ENCOUNTERS;
  loadEncounters().catch(e => console.warn('[mobs] encounters.json not loaded', e));

  // test hook: spawn near the player, let it hit the player, kill it, confirm the 'kill' event
  // waits are in game time (headless swiftshader can run at a few fps; game dt is capped at 0.1 s per frame)
  window.__mobTest = async (typeId, { timeout = 15, wallTimeout = 120000 } = {}) => {
    const res = { type: typeId, spawned: false, attacked: false, damaged: false, died: false, killEvent: false, removed: false };
    const sleep = ms => new Promise(r => setTimeout(r, ms));
    const s = game.stats, hp0 = s.hp;
    const until = async (cond, gameS) => { const g0 = game.time, w0 = performance.now(); while (!cond() && game.time - g0 < gameS && performance.now() - w0 < wallTimeout) await sleep(50); };
    const spot = sys.findSpot(game.px + 3, game.py, 8) || { x: game.px + 3, y: game.py, z: game.pz };
    const mob = sys.spawn(typeId, spot.x, spot.y, spot.z);
    res.spawned = game.mobs.includes(mob); res.spot = spot;
    mob.state = 'chase'; for (const a of mob.type.attacks) mob.attackCd[a.name] = 0;
    const offHit = game.on('playerHit', e => { if (e.source === mob) { res.attacked = true; res.attackDamage = (res.attackDamage || 0) + e.amount; } });
    let killed = null; const offKill = game.on('kill', e => { if (e.mob === mob) killed = e; });
    const g0 = game.time;
    await until(() => { s.hp = s.maxHp; return res.attacked; }, timeout);
    res.attackGameS = +(game.time - g0).toFixed(2);
    s.hp = s.maxHp;
    const hp1 = mob.hp;
    const phases = new Set([mob.phase]);
    for (let i = 0; i < 400 && !mob.dead; i++) { game.damageMob(mob, Math.ceil(mob.maxHp / 12), { crit: false, type: 'physical' }); phases.add(mob.phase); const t1 = game.time; await until(() => game.time - t1 > 0.15, 1); }
    res.damaged = mob.hp < hp1 || mob.dead; res.died = mob.dead; res.killEvent = !!killed; res.phases = [...phases];
    await until(() => !game.mobs.includes(mob), 3);
    res.removed = !game.mobs.includes(mob);
    offHit(); offKill(); s.hp = Math.max(hp0, s.maxHp);
    return res;
  };
}
