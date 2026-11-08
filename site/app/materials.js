// Surface materials (session 10): CC0 Poly Haven textures (site/tex, scripts/fetch_textures.py) applied in world
// space, so the GLBs need no UVs. Walls: gault brick or limestone ashlar (picked per building from its colour tone)
// plus a procedural window grid; roofs: tiles; ground: blended by the surface class encoded in the vertex colour.
// The texture is used as detail (texture / its mean) on top of the vertex colour, so the established palette stays.
import * as THREE from 'three';

const Q = new URLSearchParams(location.search);
// ?mat=0 turns textures off (session 9 look). ?win=1 adds a procedural window grid: off by default, it lowered
// photo_match on the 50-view check (textures alone 9.42, with windows 8.77; no textures 7.75)
export const MAT = Q.get('mat') !== '0';
const WIN = Q.get('win') === '1';
const GK = parseFloat(Q.get('gk') || '1').toFixed(3);   // ground albedo factor
const SLOTS = ['brick', 'ashlar', 'roof', 'road', 'pave', 'grass', 'court', 'earth'];

window.__texReady = !MAT;
const uniforms = {}, sizes = {};
let pending = 0;
if (MAT) {
  const base = new URL('../tex/', import.meta.url).href;
  const meta = await fetch(base + 'textures.json').then(r => r.json()).catch(() => ({}));
  const loader = new THREE.TextureLoader();
  for (const s of SLOTS) {
    pending++;
    const t = loader.load(base + s + '.jpg', () => { if (--pending === 0) window.__texReady = true; },
      undefined, () => { console.warn('texture failed', s); if (--pending === 0) window.__texReady = true; });
    t.wrapS = t.wrapT = THREE.RepeatWrapping; t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 8;
    uniforms['t_' + s] = { value: t };
    sizes[s] = (meta[s]?.size_m || 2).toFixed(3);
  }
}

const common = `
varying vec3 vWP; varying vec3 vWN;
${SLOTS.map(s => `uniform sampler2D t_${s};`).join('\n')}
vec3 detail(sampler2D t, vec2 uv) {   // texture divided by its mean (top mip): ~1 on average, keeps the vertex colour
  vec3 m = textureLod(t, vec2(0.5), 12.0).rgb + 1e-3;
  return texture2D(t, uv).rgb / m;
}
float h21(vec3 c) { return fract(sin(dot(c, vec3(12.9898, 78.233, 37.719))) * 43758.5453); }
`;

// Session 36: procedural paving (world space, no textures; cheap enough for phones): herringbone clay paviors
// (class 10, Market Street), granite setts in stretcher courses (class 5, the Market Square, King's Parade) and
// rectangular slabs for pavements (class 2). Patterns fade to their mean colour once a unit is under ~2 px.
const pavingFns = `
float h12(vec2 p) { vec3 p3 = fract(vec3(p.xyx) * 0.1031); p3 += dot(p3, p3.yzx + 33.33); return fract((p3.x + p3.y) * p3.z); }
float vnoise(vec2 p) { vec2 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f);
  return mix(mix(h12(i), h12(i + vec2(1, 0)), f.x), mix(h12(i + vec2(0, 1)), h12(i + vec2(1, 1)), f.x), f.y); }
vec3 lumDetail(vec3 d) { return mix(vec3(dot(d, vec3(0.333))), d, 0.4); }
float joint(float e, float jw, float px) { return 1.0 - smoothstep(jw - 0.5 * px, jw + 0.5 * px, e); }
// 90-degree herringbone of 200 x 100 mm paviors, laid at 45 degrees; linear albedo
vec3 brickPave(vec2 gp, float px) {
  vec2 p = mat2(0.7071, 0.7071, -0.7071, 0.7071) * gp / 0.1;   // units of one brick width
  vec2 c = floor(p);
  float d = mod(c.x - c.y, 4.0);
  vec2 o = d < 0.5 ? c : d < 1.5 ? c - vec2(1, 0) : d < 2.5 ? c - vec2(0, 1) : c;
  vec2 sz = d < 1.5 ? vec2(2, 1) : vec2(1, 2);
  vec2 l = p - o; vec2 e2 = min(l, sz - l); float e = min(e2.x, e2.y) * 0.1;
  float r = h12(o + sz * 7.0), r2 = h12(o * 1.7 + 3.1);
  vec3 col = mix(vec3(0.21, 0.09, 0.08), vec3(0.27, 0.115, 0.09), r);
  col = mix(col, vec3(0.16, 0.075, 0.075), step(0.93, r2));            // a few dark plum bricks
  col *= 0.85 + 0.3 * vnoise(gp * 0.4);                                 // large-scale staining
  vec3 mean = vec3(0.225, 0.095, 0.083);
  col = mix(col, vec3(0.20, 0.17, 0.14), joint(e, 0.005, px) * 0.8);   // sand joints
  return mix(col, mean * (0.85 + 0.3 * vnoise(gp * 0.4)), smoothstep(0.03, 0.08, px));
}
// granite setts ~100 x 140-200 mm in courses with random offsets; returns linear albedo
vec3 settPave(vec2 gp, float px) {
  float row = floor(gp.y / 0.11);
  float L = 0.14 + 0.06 * h12(vec2(row, 7.0));
  float x = gp.x / L + h12(vec2(row, 1.0));
  vec2 id = vec2(floor(x), row);
  float lx = fract(x) * L, ly = fract(gp.y / 0.11) * 0.11;
  float e = min(min(lx, L - lx), min(ly, 0.11 - ly));
  float r = h12(id), r2 = h12(id + 17.0);
  vec3 col = vec3(0.20, 0.195, 0.19) * (0.7 + 0.6 * r);
  col = mix(col, vec3(0.27, 0.20, 0.18), step(0.8, r2) * 0.6);         // pinkish granite
  col *= 0.8 + 0.2 * smoothstep(0.0, 0.025, e);                         // domed tops
  col *= 0.85 + 0.3 * vnoise(gp * 0.5);
  col = mix(col, vec3(0.07, 0.065, 0.06), joint(e, 0.006, px) * 0.85);
  return mix(col, vec3(0.19, 0.18, 0.17) * (0.85 + 0.3 * vnoise(gp * 0.5)), smoothstep(0.03, 0.09, px));
}
// rectangular slabs 600 x 900 mm in offset courses; returns a multiplier on the class colour
vec3 slabPave(vec2 gp, float px) {
  float row = floor(gp.y / 0.6);
  float x = gp.x / 0.9 + 0.5 * mod(row, 2.0) + 0.2 * h12(vec2(row, 3.0));
  vec2 id = vec2(floor(x), row);
  float lx = fract(x) * 0.9, ly = fract(gp.y / 0.6) * 0.6;
  float e = min(min(lx, 0.9 - lx), min(ly, 0.6 - ly));
  float r = h12(id), st = vnoise(gp * 0.35);
  vec3 m = vec3(1.0, 0.97, 0.90) * (0.86 + 0.2 * r) * (0.88 + 0.24 * st);
  m = mix(m, vec3(0.9, 0.88, 0.84), step(0.9, h12(id + 5.0)) * 0.5);   // odd greyer replacement slab
  m *= 1.0 - 0.4 * joint(e, 0.005, px);
  return mix(m, vec3(1.0, 0.97, 0.90) * 0.96 * (0.88 + 0.24 * st), smoothstep(0.15, 0.4, px));
}
`;

const groundFrag = `
  vec2 gp = vec2(vWP.x, -vWP.z);
  float px = length(fwidth(gp));   // metres per pixel
  // surface class weights from the interpolated vertex colour (build.py COLORS)
  vec3 c = vColor.rgb;
  float wr = exp(-dot(c - vec3(0.32, 0.32, 0.34), c - vec3(0.32, 0.32, 0.34)) * 200.0);
  float wp = exp(-dot(c - vec3(0.62, 0.60, 0.56), c - vec3(0.62, 0.60, 0.56)) * 200.0)
           + exp(-dot(c - vec3(0.60, 0.58, 0.54), c - vec3(0.60, 0.58, 0.54)) * 200.0);
  float wg = exp(-dot(c - vec3(0.33, 0.52, 0.24), c - vec3(0.33, 0.52, 0.24)) * 200.0);
  float wc = exp(-dot(c - vec3(0.66, 0.62, 0.55), c - vec3(0.66, 0.62, 0.55)) * 200.0);
  float we = exp(-dot(c - vec3(0.50, 0.42, 0.31), c - vec3(0.50, 0.42, 0.31)) * 200.0)
           + exp(-dot(c - vec3(0.55, 0.50, 0.45), c - vec3(0.55, 0.50, 0.45)) * 200.0);
  float wb = exp(-dot(c - vec3(0.62, 0.60, 0.80), c - vec3(0.62, 0.60, 0.80)) * 200.0);   // key colour only (see build.py)
  float wsum = wr + wp + wg + wc + we + wb;
  if (wsum > 0.02) {
    vec3 base = diffuseColor.rgb, acc = vec3(0.0);
    if (wr > 0.01) acc += wr * base * lumDetail(detail(t_road, gp / ${sizes.road}));
    if (wg > 0.01) acc += wg * base * lumDetail(detail(t_grass, gp / ${sizes.grass}));
    if (we > 0.01) acc += we * base * lumDetail(detail(t_earth, gp / ${sizes.earth}));
    if (wp > 0.01) acc += wp * base * slabPave(gp, px);
    if (wc > 0.01) acc += wc * settPave(gp, px) * 1.05;
    if (wb > 0.01) acc += wb * brickPave(gp, px) * 1.4;
    vec3 col = acc / wsum;
    diffuseColor.rgb = mix(base, col, min(wsum * 8.0, 1.0));
  }
  diffuseColor.rgb *= ${GK};
`;

const buildingFrag = `
  vec3 n = normalize(vWN);
  if (abs(n.y) < 0.5) {   // wall (or steep roof facet): u runs along the wall, v up
    vec2 tg = normalize(vec2(-n.z, n.x) + 1e-5);
    float u = dot(vWP.xz, tg), v = vWP.y;
    bool stone = h21(floor(vColor.rgb * 255.0)) < 0.4;
    vec3 dt = stone ? detail(t_ashlar, vec2(u, v) / ${sizes.ashlar}) : detail(t_brick, vec2(u, v) / ${sizes.brick});
    diffuseColor.rgb *= dt;
    ${WIN ? `if (abs(n.y) < 0.15) {
    // window grid: 3.2 m storeys, 2.7 m bays; sash windows 1.1 x 1.7 m with a light frame and glazing bars
    vec2 cell = vec2(fract(u / 2.7) * 2.7, fract(v / 3.2) * 3.2);
    vec2 d = abs(cell - vec2(1.35, 1.75)) - vec2(0.55, 0.85);
    float frame = step(max(d.x, d.y), 0.06);
    float glass = step(max(d.x, d.y), 0.0);
    float bars = step(abs(cell.y - 1.75), 0.03) + step(abs(cell.x - 1.35), 0.025);
    vec3 gl = mix(vec3(0.05, 0.06, 0.07), vec3(0.20, 0.24, 0.28), smoothstep(0.9, 2.6, cell.y));
    diffuseColor.rgb = mix(diffuseColor.rgb, vec3(0.75, 0.74, 0.70), frame);
    diffuseColor.rgb = mix(diffuseColor.rgb, gl, glass * (1.0 - min(bars, 1.0))); }` : ''}
  } else {
    diffuseColor.rgb *= detail(t_roof, vec2(vWP.x, -vWP.z) / ${sizes.roof});
  }
`;

// Patch a Lambert material: world position/normal varyings and the per-kind colour shader.
function patch(mat, kind) {
  if (!MAT) return mat;
  mat.onBeforeCompile = sh => {
    Object.assign(sh.uniforms, uniforms);
    sh.vertexShader = sh.vertexShader
      .replace('#include <common>', '#include <common>\nvarying vec3 vWP; varying vec3 vWN;')
      .replace('#include <worldpos_vertex>', `#include <worldpos_vertex>
        vWP = (modelMatrix * vec4(transformed, 1.0)).xyz; vWN = normalize(mat3(modelMatrix) * objectNormal);`);
    sh.fragmentShader = sh.fragmentShader
      .replace('#include <common>', '#include <common>\n' + common + (kind === 'b' ? '' : pavingFns))
      .replace('#include <color_fragment>', '#include <color_fragment>\n' + (kind === 'b' ? buildingFrag : groundFrag));
  };
  mat.customProgramCacheKey = () => 'wc_' + kind;
  return mat;
}

export const buildingVcolMat = patch(new THREE.MeshLambertMaterial({ color: 0xffffff, vertexColors: true }), 'b');
export const groundVcolMat = patch(new THREE.MeshLambertMaterial({ color: 0xffffff, vertexColors: true }), 'g');
