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

const groundFrag = `
  vec2 gp = vec2(vWP.x, -vWP.z);
  // surface class weights from the interpolated vertex colour (build.py COLORS)
  vec3 c = vColor.rgb;
  float wr = exp(-dot(c - vec3(0.32, 0.32, 0.34), c - vec3(0.32, 0.32, 0.34)) * 200.0);
  float wp = exp(-dot(c - vec3(0.62, 0.60, 0.56), c - vec3(0.62, 0.60, 0.56)) * 200.0)
           + exp(-dot(c - vec3(0.60, 0.58, 0.54), c - vec3(0.60, 0.58, 0.54)) * 200.0);
  float wg = exp(-dot(c - vec3(0.33, 0.52, 0.24), c - vec3(0.33, 0.52, 0.24)) * 200.0);
  float wc = exp(-dot(c - vec3(0.66, 0.62, 0.55), c - vec3(0.66, 0.62, 0.55)) * 200.0);
  float we = exp(-dot(c - vec3(0.50, 0.42, 0.31), c - vec3(0.50, 0.42, 0.31)) * 200.0)
           + exp(-dot(c - vec3(0.55, 0.50, 0.45), c - vec3(0.55, 0.50, 0.45)) * 200.0);
  float wsum = wr + wp + wg + wc + we;
  vec3 dt = vec3(1.0);
  if (wsum > 0.02) {
    dt = (wr * detail(t_road, gp / ${sizes.road}) + wp * detail(t_pave, gp / ${sizes.pave})
        + wg * detail(t_grass, gp / ${sizes.grass}) + wc * detail(t_court, gp / ${sizes.court})
        + we * detail(t_earth, gp / ${sizes.earth})) / wsum;
    dt = mix(vec3(dot(dt, vec3(0.333))), dt, 0.4);   // mostly luminance detail: keep the class colour
    dt = mix(vec3(1.0), dt, min(wsum, 1.0));
  }
  diffuseColor.rgb *= dt * ${GK};
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
      .replace('#include <common>', '#include <common>\n' + common)
      .replace('#include <color_fragment>', '#include <color_fragment>\n' + (kind === 'b' ? buildingFrag : groundFrag));
  };
  mat.customProgramCacheKey = () => 'wc_' + kind;
  return mat;
}

export const buildingVcolMat = patch(new THREE.MeshLambertMaterial({ color: 0xffffff, vertexColors: true }), 'b');
export const groundVcolMat = patch(new THREE.MeshLambertMaterial({ color: 0xffffff, vertexColors: true }), 'g');
