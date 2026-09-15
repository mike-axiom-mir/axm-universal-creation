import { deepClone, hashValue } from './hand-runtime.mjs';

const clamp01 = (value) => Math.max(0, Math.min(1, value));
const round6 = (value) => Number(value.toFixed(6));

function mulberry32(seed) {
  let a = seed >>> 0;
  return () => {
    a |= 0;
    a = (a + 0x6D2B79F5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function hand(id, execute, description) {
  return Object.freeze({
    schema: 'axm.hand/v0.1',
    id,
    version: '0.1.0',
    deterministic: true,
    callerNeutral: true,
    network: 'forbidden',
    description,
    execute,
  });
}

export const seedPathHand = hand('fx.electric.seed-path', (state, params) => {
  const next = deepClone(state);
  const source = next.effect.source;
  const target = next.effect.target;
  const segments = Math.max(4, Math.min(64, Number(params.segments ?? 16)));
  const jitter = Math.max(0, Math.min(0.3, Number(params.jitter ?? 0.055)));
  const random = mulberry32((next.effect.seed ?? 1) ^ 0x51A7E11C);
  const dx = target.x - source.x;
  const dy = target.y - source.y;
  const length = Math.max(Math.hypot(dx, dy), 0.000001);
  const nx = -dy / length;
  const ny = dx / length;
  const points = [];

  for (let i = 0; i <= segments; i += 1) {
    const t = i / segments;
    const envelope = Math.sin(Math.PI * t);
    const offset = i === 0 || i === segments ? 0 : (random() * 2 - 1) * jitter * envelope;
    points.push({
      x: round6(clamp01(source.x + dx * t + nx * offset)),
      y: round6(clamp01(source.y + dy * t + ny * offset)),
    });
  }

  next.paths = [{ id: 'trunk', role: 'trunk', points }];
  next.effect.topologyRevision = 1;
  return { state: next, evidence: { generatedPoints: points.length, seed: next.effect.seed } };
}, 'Generate the deterministic editable trunk path for an electric effect.');

export const branchPathHand = hand('fx.electric.branch-paths', (state, params) => {
  const next = deepClone(state);
  const trunk = next.paths?.find((path) => path.role === 'trunk');
  if (!trunk) throw new Error('branch-paths requires a trunk path');
  const branchCount = Math.max(0, Math.min(24, Number(params.branchCount ?? 6)));
  const spread = Math.max(0.01, Math.min(0.4, Number(params.spread ?? 0.11)));
  const random = mulberry32((next.effect.seed ?? 1) ^ 0xB12A4C77);
  const branches = [];

  for (let branchIndex = 0; branchIndex < branchCount; branchIndex += 1) {
    const anchorIndex = 2 + Math.floor(random() * Math.max(1, trunk.points.length - 4));
    const anchor = trunk.points[Math.min(anchorIndex, trunk.points.length - 2)];
    const pointCount = 3 + Math.floor(random() * 4);
    const side = random() < 0.5 ? -1 : 1;
    const reach = spread * (0.55 + random() * 0.8);
    const driftX = (random() * 2 - 1) * reach * 0.55;
    const driftY = side * reach;
    const points = [];
    for (let p = 0; p < pointCount; p += 1) {
      const t = p / (pointCount - 1);
      const wobble = (random() * 2 - 1) * spread * 0.16 * Math.sin(Math.PI * t);
      points.push({
        x: round6(clamp01(anchor.x + driftX * t + wobble)),
        y: round6(clamp01(anchor.y + driftY * t - wobble * 0.35)),
      });
    }
    branches.push({ id: `branch-${branchIndex + 1}`, role: 'branch', parent: 'trunk', anchorIndex, points });
  }

  next.paths = [trunk, ...branches];
  next.effect.topologyRevision = (next.effect.topologyRevision ?? 1) + 1;
  return { state: next, evidence: { branchCount: branches.length, editablePathCount: next.paths.length } };
}, 'Add deterministic editable branches to an existing electric trunk.');

export const energyHand = hand('fx.electric.energy-profile', (state, params) => {
  const next = deepClone(state);
  const branchEnergyScale = Number(next.effect.controls?.branchEnergyScale ?? params.branchEnergyScale ?? 0.58);
  const trunkWidth = Number(params.trunkWidth ?? 1);
  next.paths = next.paths.map((path, index) => {
    const branchFactor = path.role === 'trunk' ? 1 : Math.max(0.15, branchEnergyScale * (1 - (index - 1) * 0.055));
    return {
      ...path,
      energy: round6(branchFactor),
      width: round6(trunkWidth * (path.role === 'trunk' ? 1 : 0.46 + branchFactor * 0.18)),
      phase: round6((((next.effect.seed ?? 1) * 0.0001) + index * 0.173) % 1),
    };
  });
  return { state: next, evidence: { profiledPaths: next.paths.length, branchEnergyScale: round6(branchEnergyScale) } };
}, 'Assign renderer-neutral energy, width, and phase to electric paths.');

export const coreLayerHand = hand('fx.electric.core-layer', (state, params) => {
  const next = deepClone(state);
  next.layers ??= [];
  next.layers.push({
    id: 'electric-core',
    role: 'core-emission',
    module: 'light.neon-edge-glow',
    source: 'paths',
    params: { strength: Number(params.strength ?? 1), radius: Number(params.radius ?? 0.012) },
  });
  return { state: next, evidence: { module: 'light.neon-edge-glow' } };
}, 'Attach the AetherFX neon edge-glow module as an electric core realization intent.');

export const bloomLayerHand = hand('fx.electric.bloom-layer', (state, params) => {
  const next = deepClone(state);
  next.layers ??= [];
  const scale = Number(next.effect.controls?.glowScale ?? 1);
  next.layers.push({
    id: 'electric-bloom',
    role: 'bloom',
    module: 'light.soft-bloom-halo',
    source: 'electric-core',
    params: { strength: round6(Number(params.strength ?? 0.82) * scale), radius: Number(params.radius ?? 0.05) },
  });
  return { state: next, evidence: { module: 'light.soft-bloom-halo', glowScale: round6(scale) } };
}, 'Attach a bloom layer without flattening the canonical path topology.');

export const atmosphereHand = hand('fx.electric.atmosphere-layer', (state, params) => {
  const next = deepClone(state);
  next.layers ??= [];
  next.layers.push({
    id: 'electric-atmosphere',
    role: 'ambient-response',
    module: 'atmosphere.ambient-field',
    source: 'paths',
    params: { amount: Number(params.amount ?? 0.28), falloff: Number(params.falloff ?? 0.7) },
  });
  return { state: next, evidence: { module: 'atmosphere.ambient-field' } };
}, 'Add renderer-neutral ambient response around the electric topology.');

export const pulseHand = hand('fx.electric.pulse-motion', (state, params) => {
  const next = deepClone(state);
  next.layers ??= [];
  next.layers.push({
    id: 'electric-pulse',
    role: 'motion',
    module: 'motion.idle-pulse',
    source: 'electric-core',
    params: { rate: Number(params.rate ?? 2.4), depth: Number(params.depth ?? 0.12) },
  });
  return { state: next, evidence: { module: 'motion.idle-pulse' } };
}, 'Add deterministic pulse intent as a replaceable motion realization layer.');

function pointsToSvg(points) {
  return points.map((point) => `${round6(point.x * 1000)},${round6(point.y * 600)}`).join(' ');
}

export const svgPreviewHand = hand('fx.electric.svg-preview', (state) => {
  const next = deepClone(state);
  const glowScale = Number(next.effect.controls?.glowScale ?? 1);
  const pathMarkup = next.paths.map((path) => {
    const opacity = path.role === 'trunk' ? 1 : Math.max(0.18, path.energy ?? 0.5);
    const width = (path.width ?? 0.5) * (path.role === 'trunk' ? 3.2 : 2.1);
    return `<polyline points="${pointsToSvg(path.points)}" fill="none" stroke="white" stroke-width="${round6(width)}" opacity="${round6(opacity)}" stroke-linecap="round" stroke-linejoin="round"/>`;
  }).join('');
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 600"><defs><filter id="g"><feGaussianBlur stdDeviation="${round6(7 * glowScale)}" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs><rect width="1000" height="600" fill="#05060b"/><g filter="url(#g)">${pathMarkup}</g></svg>`;
  next.realizations ??= {};
  next.realizations.svgPreview = {
    mediaType: 'image/svg+xml',
    derivedFromTopologyHash: hashValue(next.paths),
    content: svg,
  };
  return { state: next, evidence: { bytes: Buffer.byteLength(svg), pathCount: next.paths.length } };
}, 'Create a disposable SVG preview derived from canonical electric path state.');

export const ELECTRIC_HANDS = [
  seedPathHand,
  branchPathHand,
  energyHand,
  coreLayerHand,
  bloomLayerHand,
  atmosphereHand,
  pulseHand,
  svgPreviewHand,
];

export const ELECTRIC_STORM_GRAPH = Object.freeze({
  schema: 'axm.hand-graph/v0.1',
  id: 'fx.electric-storm',
  version: '0.1.0',
  stages: [
    { id: 'seed-topology', hand: 'fx.electric.seed-path', params: { segments: 18, jitter: 0.06 } },
    { id: 'grow-branches', hand: 'fx.electric.branch-paths', params: { branchCount: 7, spread: 0.12 } },
    { id: 'profile-energy', hand: 'fx.electric.energy-profile', params: { trunkWidth: 1 } },
    { id: 'core-light', hand: 'fx.electric.core-layer', params: { strength: 1, radius: 0.012 } },
    { id: 'soft-bloom', hand: 'fx.electric.bloom-layer', params: { strength: 0.82, radius: 0.05 } },
    { id: 'ambient-field', hand: 'fx.electric.atmosphere-layer', params: { amount: 0.28, falloff: 0.7 } },
    { id: 'pulse', hand: 'fx.electric.pulse-motion', params: { rate: 2.4, depth: 0.12 } },
    { id: 'preview', hand: 'fx.electric.svg-preview', params: {} },
  ],
});

export function makeElectricInitialState(seed = 1337) {
  return {
    schema: 'axm.effect-work-state/v0.1',
    effect: {
      kind: 'electric-arc',
      seed,
      source: { x: 0.08, y: 0.54 },
      target: { x: 0.92, y: 0.43 },
      controls: { branchEnergyScale: 0.58, glowScale: 1 },
    },
    paths: [],
    layers: [],
    realizations: {},
  };
}
