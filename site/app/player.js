// First-person player: input (keyboard + mouse, or touch joystick + drag) and walking physics.
import { STEP } from './collision.js';

const WALK = 2.5, RUN = 6, TURN = 1.8, GRAVITY = 9.81, EYE = 1.6, SUBSTEP = 0.15;

export class Player {
  constructor(world, canvas) {
    this.world = world;
    this.x = 0; this.y = 0; this.z = 0;   // feet, collision frame
    this.yaw = 0; this.pitch = 0;          // yaw 0 = facing north, positive = turning left
    this.vz = 0; this.grounded = false; this.pendingPlace = null;
    this.keys = new Set(); this.joy = { x: 0, y: 0 };
    this.canPlace = () => true; // set by the app: are the tiles around a teleport target loaded?
    this.initInput(canvas);
  }

  get eye() { return this.z + EYE; }
  get heading() { return -this.yaw; } // compass heading (radians clockwise from north)

  // Put the player at (x, y); feet are placed once collision there is loaded. With z: the walkable
  // surface at or below z + STEP; without z: the nearest open walkable ground (searching outwards).
  teleport(x, y, z = null, lookAt = null) {
    this.x = x; this.y = y; if (z != null) this.z = z;
    this.vz = 0; this.grounded = false;
    this.pendingPlace = { x, y, z, lookAt };
  }

  tryPlace() {
    const p = this.pendingPlace, w = this.world;
    if (!w.covered(p.x, p.y) || (p.z == null && !this.canPlace(p.x, p.y))) return false;
    if (p.z != null) {
      const g = w.standAt(p.x, p.y, p.z) ?? w.standAt(p.x, p.y, 1e4);
      if (g == null) return false;
      this.x = p.x; this.y = p.y; this.z = g;
    } else {
      // Landmark centres are usually inside buildings: look for open ground about 30 m away
      // (rings at 30, 24, 36, 18, ... m) with no wall in the way for the first part of the view line.
      const radii = [30]; for (let k = 6; k <= 120; k += 6) { if (30 - k >= 0) radii.push(30 - k); radii.push(30 + k); }
      let found = null;
      for (const r of radii) {
        const n = r === 0 ? 1 : Math.ceil(2 * Math.PI * r / 4);
        for (let i = 0; i < n && !found; i++) {
          const a = i / n * 2 * Math.PI, ux = Math.cos(a), uy = Math.sin(a), x = p.x + r * ux, y = p.y + r * uy;
          const s = w.support(x, y, 1e4);
          if (!s || s.kind !== 1 || s.surface === 9) continue;
          const g = w.standAt(x, y, s.z);
          if (g == null) continue;
          let clear = true;
          for (let d = 2; d < r - 15 && clear; d += 2) clear = !w.blocked(x - ux * d, y - uy * d, g, 0.05);
          if (clear) found = [x, y, g];
        }
        if (found) break;
      }
      if (!found) return false;
      [this.x, this.y, this.z] = found;
    }
    if (p.lookAt) this.yaw = -Math.atan2(p.lookAt[0] - this.x, p.lookAt[1] - this.y);
    else this.faceOpen();
    this.pendingPlace = null; this.grounded = true;
    return true;
  }

  // Face the direction with the longest walkable straight line (up to 80 m) from here.
  faceOpen() {
    let best = 0;
    for (let a = 0; a < 24; a++) {
      const yaw = a / 24 * 2 * Math.PI, sx = -Math.sin(yaw), sy = Math.cos(yaw);
      let d = 0, z = this.z;
      for (; d < 80; d += 1) {
        const g = this.world.standAt(this.x + sx * (d + 1), this.y + sy * (d + 1), z);
        if (g == null) break; z = g;
      }
      if (d > best) { best = d; this.yaw = yaw; }
    }
  }

  update(dt) {
    dt = Math.min(dt, 0.1);
    if (this.pendingPlace && !this.tryPlace()) return;
    const k = this.keys, w = this.world;
    // turning with arrow keys
    this.yaw += ((k.has('ArrowLeft') ? 1 : 0) - (k.has('ArrowRight') ? 1 : 0)) * TURN * dt;
    let f = (k.has('KeyW') || k.has('ArrowUp') ? 1 : 0) - (k.has('KeyS') || k.has('ArrowDown') ? 1 : 0) - this.joy.y;
    let s = (k.has('KeyD') ? 1 : 0) - (k.has('KeyA') ? 1 : 0) + this.joy.x;
    const len = Math.hypot(f, s);
    if (len > 1) { f /= len; s /= len; }
    const speed = (k.has('ShiftLeft') || k.has('ShiftRight') || Math.hypot(this.joy.x, this.joy.y) > 0.95) ? RUN : WALK;
    // forward = (-sin yaw, cos yaw), right = (cos yaw, sin yaw) in x-east/y-north
    const sy = Math.sin(this.yaw), cy = Math.cos(this.yaw);
    let dx = (-sy * f + cy * s) * speed * dt, dy = (cy * f + sy * s) * speed * dt;
    const n = Math.max(1, Math.ceil(Math.hypot(dx, dy) / SUBSTEP));
    dx /= n; dy /= n;
    for (let i = 0; i < n && (dx || dy); i++) {
      let g = w.standAt(this.x + dx, this.y + dy, this.z);
      if (g != null) { this.x += dx; this.y += dy; }
      else if ((g = w.standAt(this.x + dx, this.y, this.z)) != null) { this.x += dx; dy = 0; }      // slide along x
      else if ((g = w.standAt(this.x, this.y + dy, this.z)) != null) { this.y += dy; dx = 0; }      // slide along y
      else break;
      if (g > this.z) this.z = g;                        // step up
      else if (this.z - g <= STEP && this.grounded) this.z = g; // follow the ground down
    }
    // gravity for larger drops
    const ground = w.support(this.x, this.y, this.z + 0.01);
    if (ground && ground.z < this.z - 1e-3) {
      this.vz -= GRAVITY * dt; this.z = Math.max(ground.z, this.z + this.vz * dt); this.grounded = false;
    }
    if (ground && this.z <= ground.z + 1e-3) { this.z = ground.z; this.vz = 0; this.grounded = true; }
  }

  applyCamera(cam) {
    cam.position.set(this.x, this.eye, -this.y);
    cam.rotation.set(this.pitch, this.yaw, 0, 'YXZ');
  }

  look(dx, dy) {
    this.yaw -= dx; this.pitch = Math.max(-1.45, Math.min(1.45, this.pitch - dy));
  }

  initInput(canvas) {
    const typing = e => e.target instanceof HTMLInputElement;
    addEventListener('keydown', e => {
      if (typing(e)) return;
      this.keys.add(e.code);
      if (e.code.startsWith('Arrow') || e.code === 'Space') e.preventDefault();
    });
    addEventListener('keyup', e => this.keys.delete(e.code));
    addEventListener('blur', () => this.keys.clear());

    const touch = matchMedia('(pointer: coarse)').matches || 'ontouchstart' in window;
    if (!touch) {
      canvas.addEventListener('click', () => { const r = canvas.requestPointerLock?.(); r?.catch?.(() => {}); });
      addEventListener('mousemove', e => {
        if (document.pointerLockElement === canvas) this.look(e.movementX * 0.0022, e.movementY * 0.0022);
      });
    }
    // drag-to-look (touch, or mouse without pointer lock)
    let drag = null;
    canvas.addEventListener('pointerdown', e => { if (e.pointerType === 'touch') { drag = { id: e.pointerId, x: e.clientX, y: e.clientY }; } });
    canvas.addEventListener('pointermove', e => {
      if (!drag || e.pointerId !== drag.id) return;
      this.look((e.clientX - drag.x) * 0.005, (e.clientY - drag.y) * 0.005);
      drag.x = e.clientX; drag.y = e.clientY;
    });
    const end = e => { if (drag && e.pointerId === drag.id) drag = null; };
    canvas.addEventListener('pointerup', end); canvas.addEventListener('pointercancel', end);

    // virtual joystick
    const pad = document.getElementById('joystick'), knob = document.getElementById('knob');
    if (!pad) return;
    if (touch) pad.hidden = false;
    let jid = null;
    const move = e => {
      const r = pad.getBoundingClientRect(), R = r.width / 2;
      let x = (e.clientX - r.left - R) / R, y = (e.clientY - r.top - R) / R;
      const l = Math.hypot(x, y); if (l > 1) { x /= l; y /= l; }
      this.joy.x = x; this.joy.y = y;
      knob.style.transform = `translate(${x * R * 0.6}px, ${y * R * 0.6}px)`;
    };
    pad.addEventListener('pointerdown', e => { jid = e.pointerId; pad.setPointerCapture(jid); move(e); e.preventDefault(); });
    pad.addEventListener('pointermove', e => { if (e.pointerId === jid) move(e); });
    const stop = e => { if (e.pointerId !== jid) return; jid = null; this.joy.x = this.joy.y = 0; knob.style.transform = ''; };
    pad.addEventListener('pointerup', stop); pad.addEventListener('pointercancel', stop);
  }
}
