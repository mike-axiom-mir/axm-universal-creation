'use strict';

const U = require('./foundation-utils');

const MASK_SCHEMA = 'axm.precision-mask/v1';
const BRUSH_SCHEMA = 'axm.precision-brush-plan/v1';
const EFFECT_SCHEMA = 'axm.precision-effect-graph/v1';
const CATALOG_SCHEMA = 'axm.creative-microtool-catalog/v1';
const MAX_PIXELS = 16777216;

function int(value, min, max, label) {
  const number = Math.floor(U.finite(value, label));
  U.ensure(number >= min && number <= max, (label || 'integer') + ' outside ' + min + '..' + max);
  return number;
}
function clamp(value, min, max) { return Math.max(min, Math.min(max, value)); }
function bytes(value, expected, label) {
  const result = Buffer.isBuffer(value) ? Buffer.from(value) : typeof value === 'string' ? Buffer.from(value, 'base64') : Buffer.from(value || []);
  U.ensure(result.length === expected, (label || 'buffer') + ' must contain exactly ' + expected + ' bytes');
  return result;
}
function mask(width, height, alpha, meta) {
  width = int(width, 1, 16384, 'mask width');
  height = int(height, 1, 16384, 'mask height');
  U.ensure(width * height <= MAX_PIXELS, 'mask pixel budget exceeded');
  alpha = bytes(alpha, width * height, 'mask alpha');
  const result = { schema: MASK_SCHEMA, version: '1.0.0', width, height, alpha_base64: alpha.toString('base64'), meta: U.clone(meta || {}) };
  result.digest = U.sha256({ width, height, alpha: result.alpha_base64, meta: result.meta });
  return result;
}
function decodeMask(value) {
  U.ensure(value && value.schema === MASK_SCHEMA, 'precision mask required');
  return { width: value.width, height: value.height, alpha: bytes(value.alpha_base64, value.width * value.height, 'mask alpha') };
}
function pointInPolygon(x, y, points) {
  let inside = false;
  for (let i = 0, j = points.length - 1; i < points.length; j = i++) {
    const xi = points[i].x, yi = points[i].y, xj = points[j].x, yj = points[j].y;
    const crossed = ((yi > y) !== (yj > y)) && x < (xj - xi) * (y - yi) / ((yj - yi) || Number.EPSILON) + xi;
    if (crossed) inside = !inside;
  }
  return inside;
}
function shapeMask(spec) {
  spec = U.clone(spec || {});
  const width = int(spec.width, 1, 16384, 'shape mask width');
  const height = int(spec.height, 1, 16384, 'shape mask height');
  U.ensure(width * height <= MAX_PIXELS, 'shape mask pixel budget exceeded');
  const kind = U.text(spec.kind, 30, 'shape kind');
  const feather = clamp(U.finite(spec.edge_softness == null ? 0 : spec.edge_softness, 'edge softness'), 0, 1);
  const alpha = Buffer.alloc(width * height);
  const set = (x, y, value) => { if (x >= 0 && y >= 0 && x < width && y < height) alpha[y * width + x] = clamp(Math.round(value), 0, 255); };
  if (kind === 'rectangle') {
    const x = U.finite(spec.x, 'rectangle x'), y = U.finite(spec.y, 'rectangle y'), w = U.finite(spec.rect_width, 'rectangle width'), h = U.finite(spec.rect_height, 'rectangle height');
    U.ensure(w > 0 && h > 0, 'rectangle dimensions must be positive');
    for (let py = 0; py < height; py += 1) for (let px = 0; px < width; px += 1) {
      const dx = Math.min(px + 0.5 - x, x + w - (px + 0.5)); const dy = Math.min(py + 0.5 - y, y + h - (py + 0.5));
      if (dx >= 0 && dy >= 0) set(px, py, feather ? 255 * clamp(Math.min(dx, dy) / Math.max(1, feather * Math.min(w, h) * 0.5), 0, 1) : 255);
    }
  } else if (kind === 'ellipse') {
    const cx = U.finite(spec.cx, 'ellipse cx'), cy = U.finite(spec.cy, 'ellipse cy'), rx = U.finite(spec.rx, 'ellipse rx'), ry = U.finite(spec.ry, 'ellipse ry');
    U.ensure(rx > 0 && ry > 0, 'ellipse radii must be positive');
    for (let py = 0; py < height; py += 1) for (let px = 0; px < width; px += 1) {
      const d = Math.sqrt(((px + 0.5 - cx) / rx) ** 2 + ((py + 0.5 - cy) / ry) ** 2);
      if (d <= 1) set(px, py, feather ? 255 * clamp((1 - d) / Math.max(1e-6, feather), 0, 1) : 255);
    }
  } else if (kind === 'polygon') {
    const points = U.boundedArray(spec.points, 3, 10000, 'polygon points').map((item) => ({ x: U.finite(item.x, 'polygon x'), y: U.finite(item.y, 'polygon y') }));
    for (let py = 0; py < height; py += 1) for (let px = 0; px < width; px += 1) if (pointInPolygon(px + 0.5, py + 0.5, points)) set(px, py, 255);
  } else throw new Error('unsupported shape mask kind: ' + kind);
  return mask(width, height, alpha, { source: 'shape', kind, edge_softness: feather });
}
function combineMasks(a, b, operation) {
  const left = decodeMask(a), right = decodeMask(b);
  U.ensure(left.width === right.width && left.height === right.height, 'mask dimensions must match');
  operation = U.text(operation, 20, 'mask operation');
  U.ensure(['union', 'intersection', 'subtract', 'xor', 'multiply'].includes(operation), 'unsupported mask operation');
  const out = Buffer.alloc(left.alpha.length);
  for (let i = 0; i < out.length; i += 1) {
    const x = left.alpha[i], y = right.alpha[i];
    if (operation === 'union') out[i] = Math.max(x, y);
    else if (operation === 'intersection') out[i] = Math.min(x, y);
    else if (operation === 'subtract') out[i] = Math.max(0, x - y);
    else if (operation === 'xor') out[i] = Math.abs(x - y);
    else out[i] = Math.round(x * y / 255);
  }
  return mask(left.width, left.height, out, { source: 'combine', operation, left_digest: a.digest, right_digest: b.digest });
}
function invertMask(value) {
  const decoded = decodeMask(value); const out = Buffer.alloc(decoded.alpha.length);
  for (let i = 0; i < out.length; i += 1) out[i] = 255 - decoded.alpha[i];
  return mask(decoded.width, decoded.height, out, { source: 'invert', input_digest: value.digest });
}
function thresholdMask(value, threshold) {
  const decoded = decodeMask(value); threshold = clamp(U.finite(threshold, 'mask threshold'), 0, 1) * 255; const out = Buffer.alloc(decoded.alpha.length);
  for (let i = 0; i < out.length; i += 1) out[i] = decoded.alpha[i] >= threshold ? 255 : 0;
  return mask(decoded.width, decoded.height, out, { source: 'threshold', threshold: threshold / 255, input_digest: value.digest });
}
function morphOnce(alpha, width, height, radius, grow) {
  const out = Buffer.alloc(alpha.length); const r = radius;
  for (let y = 0; y < height; y += 1) for (let x = 0; x < width; x += 1) {
    let best = grow ? 0 : 255;
    for (let oy = -r; oy <= r; oy += 1) for (let ox = -r; ox <= r; ox += 1) {
      if (ox * ox + oy * oy > r * r) continue;
      const px = x + ox, py = y + oy; const sample = px < 0 || py < 0 || px >= width || py >= height ? (grow ? 0 : 255) : alpha[py * width + px];
      best = grow ? Math.max(best, sample) : Math.min(best, sample);
    }
    out[y * width + x] = best;
  }
  return out;
}
function morphology(value, operation, radius) {
  const decoded = decodeMask(value); operation = U.text(operation, 20, 'morphology operation'); radius = int(radius, 1, 32, 'morphology radius');
  U.ensure(['grow', 'shrink', 'open', 'close'].includes(operation), 'unsupported morphology operation');
  let out;
  if (operation === 'grow') out = morphOnce(decoded.alpha, decoded.width, decoded.height, radius, true);
  else if (operation === 'shrink') out = morphOnce(decoded.alpha, decoded.width, decoded.height, radius, false);
  else if (operation === 'open') out = morphOnce(morphOnce(decoded.alpha, decoded.width, decoded.height, radius, false), decoded.width, decoded.height, radius, true);
  else out = morphOnce(morphOnce(decoded.alpha, decoded.width, decoded.height, radius, true), decoded.width, decoded.height, radius, false);
  return mask(decoded.width, decoded.height, out, { source: 'morphology', operation, radius, input_digest: value.digest });
}
function boxBlur(alpha, width, height, radius) {
  const horizontal = new Float64Array(alpha.length); const out = Buffer.alloc(alpha.length); const span = radius * 2 + 1;
  for (let y = 0; y < height; y += 1) {
    let sum = 0;
    for (let x = -radius; x <= radius; x += 1) sum += alpha[y * width + clamp(x, 0, width - 1)];
    for (let x = 0; x < width; x += 1) {
      horizontal[y * width + x] = sum / span;
      sum += alpha[y * width + clamp(x + radius + 1, 0, width - 1)] - alpha[y * width + clamp(x - radius, 0, width - 1)];
    }
  }
  for (let x = 0; x < width; x += 1) {
    let sum = 0;
    for (let y = -radius; y <= radius; y += 1) sum += horizontal[clamp(y, 0, height - 1) * width + x];
    for (let y = 0; y < height; y += 1) {
      out[y * width + x] = clamp(Math.round(sum / span), 0, 255);
      sum += horizontal[clamp(y + radius + 1, 0, height - 1) * width + x] - horizontal[clamp(y - radius, 0, height - 1) * width + x];
    }
  }
  return out;
}
function featherMask(value, radius, passes) {
  const decoded = decodeMask(value); radius = int(radius, 1, 128, 'feather radius'); passes = int(passes == null ? 3 : passes, 1, 6, 'feather passes');
  let out = Buffer.from(decoded.alpha); for (let i = 0; i < passes; i += 1) out = boxBlur(out, decoded.width, decoded.height, radius);
  return mask(decoded.width, decoded.height, out, { source: 'feather', radius, passes, input_digest: value.digest });
}
function response(value, curve) {
  value = clamp(value, 0, 1); curve = curve || {};
  const gamma = U.finite(curve.gamma == null ? 1 : curve.gamma, 'response gamma'); U.ensure(gamma > 0 && gamma <= 16, 'response gamma outside 0..16');
  const min = U.finite(curve.min == null ? 0 : curve.min, 'response min'); const max = U.finite(curve.max == null ? 1 : curve.max, 'response max');
  U.ensure(max >= min, 'response max below min'); return min + (max - min) * Math.pow(value, gamma);
}
function seeded(seed) { let state = Number.parseInt(U.sha256(seed).slice(0, 8), 16) >>> 0; return () => { state = (Math.imul(state, 1664525) + 1013904223) >>> 0; return state / 4294967296; }; }
function brushPlan(spec) {
  spec = U.clone(spec || {}); const samples = U.boundedArray(spec.samples, 2, 100000, 'brush samples').map((item, index) => ({ x: U.finite(item.x, 'brush x'), y: U.finite(item.y, 'brush y'), pressure: clamp(U.finite(item.pressure == null ? 1 : item.pressure, 'brush pressure'), 0, 1), tilt: clamp(U.finite(item.tilt == null ? 0 : item.tilt, 'brush tilt'), -1, 1), rotation: U.finite(item.rotation == null ? 0 : item.rotation, 'brush rotation'), time_ms: U.finite(item.time_ms == null ? index : item.time_ms, 'brush time') }));
  U.ensure(samples.every((item, index) => index === 0 || item.time_ms >= samples[index - 1].time_ms), 'brush timestamps must be monotonic');
  const base = { size: U.finite(spec.size == null ? 10 : spec.size, 'brush size'), opacity: U.finite(spec.opacity == null ? 1 : spec.opacity, 'brush opacity'), flow: U.finite(spec.flow == null ? 1 : spec.flow, 'brush flow'), spacing: U.finite(spec.spacing == null ? 0.2 : spec.spacing, 'brush spacing'), hardness: U.finite(spec.hardness == null ? 1 : spec.hardness, 'brush hardness'), angle: U.finite(spec.angle == null ? 0 : spec.angle, 'brush angle'), scatter: U.finite(spec.scatter == null ? 0 : spec.scatter, 'brush scatter') };
  U.ensure(base.size > 0 && base.size <= 4096 && base.opacity >= 0 && base.opacity <= 1 && base.flow >= 0 && base.flow <= 1 && base.spacing > 0 && base.spacing <= 10 && base.hardness >= 0 && base.hardness <= 1 && base.scatter >= 0 && base.scatter <= 10, 'brush base properties invalid');
  const maps = U.clone(spec.dynamics || {}); const random = seeded(spec.seed || 'axm-precision-brush'); const dabs = [];
  let carried = 0;
  for (let i = 1; i < samples.length; i += 1) {
    const a = samples[i - 1], b = samples[i]; const dx = b.x - a.x, dy = b.y - a.y, distance = Math.hypot(dx, dy); const dt = Math.max(1, b.time_ms - a.time_ms); const velocity = clamp(distance / dt / Math.max(1e-9, U.finite(spec.velocity_scale == null ? 1 : spec.velocity_scale, 'velocity scale')), 0, 1); const direction = (Math.atan2(dy, dx) + Math.PI) / (2 * Math.PI); const elapsed = (b.time_ms - samples[0].time_ms) / Math.max(1, samples[samples.length - 1].time_ms - samples[0].time_ms); const source = { pressure: b.pressure, tilt: Math.abs(b.tilt), velocity, direction, elapsed, random: random() };
    const dyn = (name, fallback) => { const mapping = maps[name]; if (!mapping) return fallback; const sensor = U.text(mapping.sensor || 'pressure', 20, name + ' sensor'); U.ensure(Object.prototype.hasOwnProperty.call(source, sensor), 'unsupported brush sensor: ' + sensor); return response(source[sensor], mapping); };
    const size = base.size * dyn('size', 1); const spacing = Math.max(0.25, size * base.spacing * dyn('spacing', 1)); carried += distance;
    const count = Math.floor(carried / spacing); if (!count) continue;
    for (let n = 0; n < count; n += 1) {
      const t = clamp(((n + 1) * spacing - (carried - distance)) / Math.max(distance, 1e-9), 0, 1); const jitter = (random() - 0.5) * 2 * base.scatter * size * dyn('scatter', 1); const nx = distance ? -dy / distance : 0, ny = distance ? dx / distance : 0;
      dabs.push({ x: a.x + dx * t + nx * jitter, y: a.y + dy * t + ny * jitter, size, opacity: clamp(base.opacity * dyn('opacity', 1), 0, 1), flow: clamp(base.flow * dyn('flow', 1), 0, 1), hardness: clamp(base.hardness * dyn('hardness', 1), 0, 1), angle: base.angle + dyn('angle', 0) + b.rotation, sensor_snapshot: source });
    }
    carried -= count * spacing;
  }
  const plan = { schema: BRUSH_SCHEMA, version: '1.0.0', id: U.text(spec.id || 'brush-plan', 100, 'brush plan id'), operator: U.text(spec.operator || 'paint', 40, 'brush operator'), base, dynamics: maps, dab_count: dabs.length, dabs, samples_digest: U.sha256(samples), source_retained: true };
  plan.digest = U.sha256(plan); return plan;
}
function effectGraph(spec) {
  spec = U.clone(spec || {}); const nodes = U.boundedArray(spec.nodes, 1, 10000, 'effect nodes').map((node) => ({ id: U.text(node.id, 100, 'effect node id'), op: U.text(node.op, 80, 'effect op'), inputs: U.clone(node.inputs || []), params: U.clone(node.params || {}), mask_id: node.mask_id == null ? null : U.text(node.mask_id, 100, 'effect mask id'), enabled: node.enabled !== false }));
  U.ensure(new Set(nodes.map((node) => node.id)).size === nodes.length, 'effect node ids must be unique'); const byId = new Map(nodes.map((node) => [node.id, node]));
  const indegree = new Map(nodes.map((node) => [node.id, 0])); const outgoing = new Map(nodes.map((node) => [node.id, []]));
  nodes.forEach((node) => U.boundedArray(node.inputs, 0, 128, 'effect inputs').forEach((input) => { const id = U.text(input, 100, 'effect input id'); U.ensure(byId.has(id), 'effect input missing: ' + id); indegree.set(node.id, indegree.get(node.id) + 1); outgoing.get(id).push(node.id); }));
  const queue = nodes.filter((node) => indegree.get(node.id) === 0).map((node) => node.id).sort(); const order = [];
  while (queue.length) { const id = queue.shift(); order.push(id); for (const target of outgoing.get(id).slice().sort()) { indegree.set(target, indegree.get(target) - 1); if (indegree.get(target) === 0) { queue.push(target); queue.sort(); } } }
  U.ensure(order.length === nodes.length, 'effect graph contains a cycle');
  const graph = { schema: EFFECT_SCHEMA, version: '1.0.0', id: U.text(spec.id || 'effect-graph', 100, 'effect graph id'), nodes, order, outputs: U.boundedArray(spec.outputs || [order[order.length - 1]], 1, nodes.length, 'effect outputs') };
  graph.outputs.forEach((id) => U.ensure(byId.has(id), 'effect output missing: ' + id)); graph.digest = U.sha256(graph); return graph;
}
const MICROTOOLS = Object.freeze({
  selection: ['rectangle','ellipse','polygon','lasso','path','contiguous-colour','colour-range','luminance','alpha','channel','edge','union','intersection','subtract','xor','invert','feather','grow','shrink','border','threshold','dilate','erode','open','close','distance-field'],
  brush: ['paint','erase','replace-colour','blend','smudge','clone','heal','blur','sharpen','dodge','burn','saturate','desaturate','filter-brush','normal-paint','height-paint','material-channel-paint','size-dynamics','opacity-dynamics','flow-dynamics','hardness-dynamics','angle-dynamics','spacing-dynamics','scatter-dynamics','pressure','tilt','rotation','velocity','direction','elapsed','random'],
  colour: ['brightness','contrast','levels','curves','exposure','gamma','vibrance','saturation','hue','colour-balance','white-balance','selective-colour','channel-mixer','lut','gradient-map','shadows-highlights','local-contrast','tone-map','dehaze','grayscale','invert','threshold','posterize','tint'],
  transform: ['move','scale','rotate','skew','shear','crop','resize','perspective','homography','warp-grid','cage','puppet','liquify-push','liquify-twirl','liquify-bloat','liquify-pucker','displacement'],
  filter: ['gaussian-blur','box-blur','median-blur','bilateral-blur','guided-blur','motion-blur','radial-blur','lens-blur','unsharp-mask','high-pass','deconvolution','convolution','edge-detect','morphology','denoise','grain','noise','pixelate','fft','wavelet','bump','normal','seamless-tile'],
  vector: ['move-node','split-node','join-node','convert-node','cubic','quadratic','arc','multi-subpath','union','intersection','difference','xor','offset','inset','simplify','smooth','variable-stroke','gradient','mesh-gradient','pattern','clone','symbol','path-effect'],
  pixel: ['indexed-palette','palette-remap','dither-ordered','dither-error-diffusion','pixel-perfect-stroke','cel','linked-cel','tag','tile','tilemap','spritesheet'],
  material: ['channel-stack','base-colour','roughness','metallic','normal','height','emissive','opacity','ao','curvature','generator','anchor-point','smart-mask','smart-material','uv-projection','planar-projection','triplanar-projection','decal','wear','dust','scratch','fingerprint'],
  retouch: ['clone','heal','spot-heal','patch','perspective-clone','inpaint','content-aware-fill','content-aware-move','red-eye','dust-scratch','frequency-separation','wavelet-separation'],
  typography: ['glyph-outline','bearing','kerning-pair','kerning-class','ligature','opentype-feature','variable-axis','hinting','text-path','paragraph-layout','rtl','shaping','pagination'],
  audio: ['waveform-select','spectral-select','trim','fade','envelope','eq','compress','limit','gate','noise-reduce','repair','pitch-shift','time-stretch','normalize','loudness'],
});
function creativeMicrotoolCatalog() {
  const families = Object.fromEntries(Object.entries(MICROTOOLS).map(([family, tools]) => [family, { count: tools.length, tools }]));
  const total = Object.values(families).reduce((sum, family) => sum + family.count, 0);
  const foundation_executable = [
    'selection.rectangle','selection.ellipse','selection.polygon','selection.union','selection.intersection','selection.subtract','selection.xor','selection.invert','selection.threshold','selection.feather','selection.grow','selection.shrink','selection.open','selection.close',
    'brush.plan-dabs','brush.pressure-dynamics','brush.tilt-dynamics','brush.rotation-dynamics','brush.velocity-dynamics','brush.direction-dynamics','brush.elapsed-dynamics','brush.random-dynamics',
    'effects.compile-dag'
  ];
  const catalog = { schema: CATALOG_SCHEMA, version: '1.0.0', principle: 'rebuild concepts as deterministic composable AXM primitives, never copy product UI or branding', truth_boundary: 'family tool names are influence-derived targets; only foundation_executable entries are implemented by this module', foundation_executable, families, total };
  catalog.digest = U.sha256(catalog); return catalog;
}
module.exports = { MASK_SCHEMA, BRUSH_SCHEMA, EFFECT_SCHEMA, CATALOG_SCHEMA, mask, decodeMask, shapeMask, combineMasks, invertMask, thresholdMask, morphology, featherMask, brushPlan, effectGraph, creativeMicrotoolCatalog };
