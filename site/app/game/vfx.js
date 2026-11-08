// Spell VFX (session 40): one additive particle system plus small pools of sprites, rings, beams, lightning lines,
// spikes and domes. Everything is allocated once at install; spawning reuses pool slots, so casting allocates nothing.
// All positions are given in the collision frame (x east, y north, z up) and converted to three.js (x, z, -y).
export function createVfx(game) {
  const THREE = game.THREE, root = new THREE.Group(); root.name = 'vfx'; game.root.add(root);
  const col = new THREE.Color();

  // ---- glow texture (radial gradient, generated)
  const cv = document.createElement('canvas'); cv.width = cv.height = 64;
  const g2 = cv.getContext('2d'), gr = g2.createRadialGradient(32, 32, 0, 32, 32, 32);
  gr.addColorStop(0, 'rgba(255,255,255,1)'); gr.addColorStop(0.25, 'rgba(255,255,255,0.7)'); gr.addColorStop(1, 'rgba(255,255,255,0)');
  g2.fillStyle = gr; g2.fillRect(0, 0, 64, 64);
  const glow = new THREE.CanvasTexture(cv);

  // ---- particles
  const N = 2400;
  const pos = new Float32Array(N * 3), clr = new Float32Array(N * 3), size = new Float32Array(N);
  const vel = new Float32Array(N * 3), base = new Float32Array(N * 3), life = new Float32Array(N), max = new Float32Array(N),
        grav = new Float32Array(N), drag = new Float32Array(N), size0 = new Float32Array(N);
  const geo = new THREE.BufferGeometry();
  const aPos = new THREE.BufferAttribute(pos, 3), aClr = new THREE.BufferAttribute(clr, 3), aSize = new THREE.BufferAttribute(size, 1);
  aPos.setUsage(THREE.DynamicDrawUsage); aClr.setUsage(THREE.DynamicDrawUsage); aSize.setUsage(THREE.DynamicDrawUsage);
  geo.setAttribute('position', aPos); geo.setAttribute('color', aClr); geo.setAttribute('size', aSize);
  const pmat = new THREE.ShaderMaterial({
    uniforms: { map: { value: glow }, scale: { value: 600 } },
    vertexShader: `attribute float size; varying vec3 vC;
      void main(){ vC = color; vec4 mv = modelViewMatrix * vec4(position,1.0); gl_Position = projectionMatrix * mv;
      gl_PointSize = size * 600.0 / max(0.1, -mv.z); }`,
    fragmentShader: `uniform sampler2D map; varying vec3 vC;
      void main(){ vec4 t = texture2D(map, gl_PointCoord); gl_FragColor = vec4(vC * t.a, t.a); }`,
    vertexColors: true, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
  });
  const points = new THREE.Points(geo, pmat); points.frustumCulled = false; points.renderOrder = 10; root.add(points);
  let cursor = 0, alive = 0;

  // burst(x,y,z,n,{color, speed, size, life, grav, drag, up, dx,dy,dz, cone, jitter})
  function burst(x, y, z, n, o = {}) {
    col.set(o.color ?? 0xffaa44);
    const sp = o.speed ?? 4, sz = o.size ?? 0.4, lf = o.life ?? 0.6, jit = o.jitter ?? 0.2;
    for (let k = 0; k < n; k++) {
      const i = cursor; cursor = (cursor + 1) % N; const j = i * 3;
      pos[j] = x + (Math.random() - 0.5) * jit; pos[j + 1] = z + (Math.random() - 0.5) * jit; pos[j + 2] = -(y + (Math.random() - 0.5) * jit);
      let vx = Math.random() * 2 - 1, vy = Math.random() * 2 - 1, vz = Math.random() * 2 - 1;
      const l = Math.hypot(vx, vy, vz) || 1; const s = sp * (0.4 + Math.random() * 0.6) / l;
      vx *= s; vy *= s; vz *= s;
      if (o.dx !== undefined) { const c = o.cone ?? 0.3; vx = vx * c + o.dx * sp; vy = vy * c + o.dy * sp; vz = vz * c + (o.dz ?? 0) * sp; }
      vz += o.up ?? 0;
      vel[j] = vx; vel[j + 1] = vz; vel[j + 2] = -vy;
      const v = 0.75 + Math.random() * 0.25;
      base[j] = col.r * v; base[j + 1] = col.g * v; base[j + 2] = col.b * v;
      max[i] = life[i] = lf * (0.6 + Math.random() * 0.4);
      size0[i] = sz * (0.6 + Math.random() * 0.8); grav[i] = o.grav ?? 0; drag[i] = o.drag ?? 1.5;
    }
    alive = N;
  }

  // ---- pooled objects
  const fx = [];   // active: {obj, t, dur, kind, ...}
  function pool(n, make) { const a = []; for (let i = 0; i < n; i++) { const o = make(); o.visible = false; root.add(o); a.push(o); } return a; }
  const take = p => { for (const o of p) if (!o.visible) { o.visible = true; return o; } return null; };
  const addMat = () => ({ transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, fog: false });
  const sprites = pool(64, () => new THREE.Sprite(new THREE.SpriteMaterial({ map: glow, ...addMat() })));
  const ringGeo = new THREE.RingGeometry(0.88, 1, 48); ringGeo.rotateX(-Math.PI / 2);
  const rings = pool(24, () => new THREE.Mesh(ringGeo, new THREE.MeshBasicMaterial({ side: THREE.DoubleSide, ...addMat() })));
  const discGeo = new THREE.CircleGeometry(1, 40); discGeo.rotateX(-Math.PI / 2);
  const discs = pool(12, () => new THREE.Mesh(discGeo, new THREE.MeshBasicMaterial({ side: THREE.DoubleSide, ...addMat() })));
  const beamGeo = new THREE.CylinderGeometry(1, 1, 1, 8, 1, true); beamGeo.translate(0, 0.5, 0);
  const beams = pool(24, () => new THREE.Mesh(beamGeo, new THREE.MeshBasicMaterial({ ...addMat() })));
  const spikeGeo = new THREE.ConeGeometry(0.35, 1, 5); spikeGeo.translate(0, 0.5, 0);
  const spikes = pool(48, () => new THREE.Mesh(spikeGeo, new THREE.MeshLambertMaterial({ color: 0x8a7458, transparent: true })));
  const domeGeo = new THREE.SphereGeometry(1, 24, 16);
  const domes = pool(4, () => new THREE.Mesh(domeGeo, new THREE.MeshBasicMaterial({ ...addMat(), opacity: 0.25 })));
  const SEG = 14;
  const bolts = pool(16, () => {
    const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(SEG * 3), 3));
    const l = new THREE.Line(g, new THREE.LineBasicMaterial({ ...addMat() })); l.frustumCulled = false; return l;
  });
  const up = new THREE.Vector3(0, 1, 0), tv = new THREE.Vector3();

  const fxRec = [];   // record pool for fx entries (avoid allocations)
  function rec(obj, dur, kind) {
    const r = fxRec.pop() || {}; r.obj = obj; r.t = 0; r.dur = dur; r.kind = kind; r.follow = null; fx.push(r); return r;
  }

  // glow sprite at a point; returns the sprite so the caller can move it (dur Infinity = until release())
  function orb(x, y, z, color, scale = 1, dur = Infinity) {
    const s = take(sprites); if (!s) return null;
    s.material.color.set(color); s.material.opacity = 1; s.scale.setScalar(scale); s.position.set(x, z, -y);
    rec(s, dur, 'orb').s0 = scale; return s;
  }
  function release(obj) { if (obj) obj.visible = false; }
  function ring(x, y, z, color, r0, r1, dur = 0.5) {
    const m = take(rings); if (!m) return;
    m.material.color.set(color); m.material.opacity = 1; m.position.set(x, z + 0.15, -y); m.scale.setScalar(r0);
    const e = rec(m, dur, 'ring'); e.r0 = r0; e.r1 = r1;
  }
  function disc(x, y, z, color, r, dur = 1, opacity = 0.35) {
    const m = take(discs); if (!m) return;
    m.material.color.set(color); m.material.opacity = opacity; m.position.set(x, z + 0.1, -y); m.scale.setScalar(r);
    const e = rec(m, dur, 'disc'); e.o0 = opacity;
  }
  function beam(x0, y0, z0, x1, y1, z1, color, width = 0.1, dur = 0.2) {
    const m = take(beams); if (!m) return;
    m.material.color.set(color); m.material.opacity = 1;
    m.position.set(x0, z0, -y0); tv.set(x1 - x0, z1 - z0, -(y1 - y0)); const L = tv.length() || 0.01;
    m.quaternion.setFromUnitVectors(up, tv.multiplyScalar(1 / L)); m.scale.set(width, L, width);
    const e = rec(m, dur, 'beam'); e.w = width;
  }
  function lightning(x0, y0, z0, x1, y1, z1, color = 0xcfe8ff, dur = 0.18, jag = 0.6) {
    const l = take(bolts); if (!l) return;
    const a = l.geometry.attributes.position.array;
    for (let i = 0; i < SEG; i++) {
      const t = i / (SEG - 1), j = (i === 0 || i === SEG - 1) ? 0 : jag;
      a[i * 3] = x0 + (x1 - x0) * t + (Math.random() - 0.5) * j;
      a[i * 3 + 1] = z0 + (z1 - z0) * t + (Math.random() - 0.5) * j;
      a[i * 3 + 2] = -(y0 + (y1 - y0) * t + (Math.random() - 0.5) * j);
    }
    l.geometry.attributes.position.needsUpdate = true;
    l.material.color.set(color); l.material.opacity = 1; rec(l, dur, 'bolt');
    beam(x0, y0, z0, x1, y1, z1, color, 0.05, dur * 0.7);
  }
  function spike(x, y, z, h = 1.6, dur = 1.2, color = 0x8a7458) {
    const m = take(spikes); if (!m) return;
    m.material.color.set(color); m.material.opacity = 1; m.position.set(x, z - 0.2, -y);
    m.rotation.set((Math.random() - 0.5) * 0.5, Math.random() * 6, (Math.random() - 0.5) * 0.5); m.scale.set(1, 0.01, 1);
    const e = rec(m, dur, 'spike'); e.h = h;
  }
  // dome following the player while fn() is true
  function dome(color, r, until) {
    const m = take(domes); if (!m) return;
    m.material.color.set(color); m.scale.setScalar(r); const e = rec(m, Infinity, 'dome'); e.until = until; e.r = r;
  }

  function update(dt) {
    // particles
    if (alive) {
      let any = 0;
      for (let i = 0; i < N; i++) {
        if (life[i] <= 0) { if (size[i] !== 0) size[i] = 0; continue; }
        any = 1; life[i] -= dt; const j = i * 3, k = Math.max(0, life[i] / max[i]);
        const d = Math.max(0, 1 - drag[i] * dt);
        vel[j] *= d; vel[j + 1] = vel[j + 1] * d - grav[i] * dt; vel[j + 2] *= d;
        pos[j] += vel[j] * dt; pos[j + 1] += vel[j + 1] * dt; pos[j + 2] += vel[j + 2] * dt;
        clr[j] = base[j] * k; clr[j + 1] = base[j + 1] * k; clr[j + 2] = base[j + 2] * k;
        size[i] = size0[i] * (0.4 + 0.6 * k);
      }
      aPos.needsUpdate = aClr.needsUpdate = aSize.needsUpdate = true;
      if (!any) alive = 0;
    }
    const p = game.player;
    for (let i = fx.length - 1; i >= 0; i--) {
      const e = fx[i], o = e.obj; e.t += dt;
      const k = e.dur === Infinity ? 0 : e.t / e.dur;
      if (!o.visible || k >= 1 || (e.kind === 'dome' && !e.until())) {
        o.visible = false; fx[i] = fx[fx.length - 1]; fx.pop(); fxRec.push(e); continue;
      }
      switch (e.kind) {
        case 'orb': if (e.dur !== Infinity) { o.material.opacity = 1 - k; o.scale.setScalar(e.s0 * (1 + k)); } break;
        case 'ring': o.scale.setScalar(e.r0 + (e.r1 - e.r0) * Math.sqrt(k)); o.material.opacity = 1 - k; break;
        case 'disc': o.material.opacity = e.o0 * (k < 0.8 ? 1 : (1 - k) / 0.2) * (0.8 + 0.2 * Math.sin(e.t * 12)); break;
        case 'beam': o.material.opacity = 1 - k; o.scale.x = o.scale.z = e.w * (1 - k * 0.7); break;
        case 'bolt': o.material.opacity = (1 - k) * (Math.random() > 0.3 ? 1 : 0.3); break;
        case 'spike': { const g = Math.min(1, e.t / 0.12), f = k > 0.75 ? (1 - k) / 0.25 : 1; o.scale.set(1, e.h * g * f + 0.01, 1); break; }
        case 'dome': o.position.set(p.x, p.z + 1, -p.y); o.material.opacity = 0.18 + 0.06 * Math.sin(e.t * 6); o.rotation.y += dt; break;
      }
    }
  }
  function dispose() {
    game.root.remove(root);
    root.traverse(o => { o.geometry?.dispose?.(); o.material?.dispose?.(); });
    glow.dispose();
  }
  return { burst, orb, release, ring, disc, beam, lightning, spike, dome, update, dispose, glow, root };
}
