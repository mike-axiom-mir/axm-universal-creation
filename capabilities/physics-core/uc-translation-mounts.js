'use strict';

const Core = require('./source/axm-physics-core.js');

const VERSION = '0.1.0';
const MOUNT_SCHEMA = 'axm.uc-translation-mount/v0.1';
const STEP_SCHEMA = 'axm.uc-translation-mount-step/v0.1';
const MAX_MOUNTS = 4096;

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function finite(value, fallback) {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

function bounded(value, min, max, fallback) {
  return Math.max(min, Math.min(max, finite(value, fallback)));
}

function iterationCount(value, fallback) {
  return Math.round(bounded(value, 0, 32, fallback));
}

function round(value) {
  return Math.round(value * 1e9) / 1e9;
}

function body(world, id) {
  return (world.bodies || []).find(item => item.id === id) || null;
}

function inverseMass(item) {
  return item && item.enabled && item.type === 'dynamic' ? finite(item.invMass, 0) : 0;
}

function wake(item) {
  if (!item || item.type !== 'dynamic') return;
  item.sleeping = false;
  item.sleepFrames = 0;
}

function vector(input, fallback) {
  input = input || {};
  fallback = fallback || { x: 0, y: 0 };
  return {
    x: bounded(input.x, -1e9, 1e9, fallback.x),
    y: bounded(input.y, -1e9, 1e9, fallback.y)
  };
}

function magnitude(value) {
  return Math.hypot(value.x, value.y);
}

function clampMagnitude(value, maximum) {
  const mag = magnitude(value);
  if (!(mag > maximum) || !(mag > 1e-12)) return { x: value.x, y: value.y };
  const scale = maximum / mag;
  return { x: value.x * scale, y: value.y * scale };
}

function normalizeMount(input, world, index) {
  input = input || {};
  const a = String(input.a || '').trim();
  const b = String(input.b || '').trim();
  if (!a || !b || a === b) throw new Error('translation mount requires distinct a and b body ids');
  const bodyA = body(world, a);
  const bodyB = body(world, b);
  if (!bodyA || !bodyB) throw new Error('translation mount body not found: ' + (!bodyA ? a : b));
  const currentOffset = {
    x: bodyB.position.x - bodyA.position.x,
    y: bodyB.position.y - bodyA.position.y
  };
  return {
    schema: MOUNT_SCHEMA,
    id: String(input.id || ('translation-mount-' + String(index + 1).padStart(3, '0'))),
    a,
    b,
    offset: vector(input.offset, currentOffset),
    positionFactor: bounded(input.positionFactor, 0, 1, 1),
    velocityFactor: bounded(input.velocityFactor, 0, 1, 1),
    slop: bounded(input.slop, 0, 1e6, 1e-6),
    maxCorrection: bounded(input.maxCorrection, 0, 1e9, 1e6),
    maxImpulse: bounded(input.maxImpulse, 0, 1e12, 1e9),
    enabled: input.enabled !== false,
    userData: clone(input.userData || {})
  };
}

function normalizeMounts(mounts, world) {
  const list = Array.isArray(mounts) ? mounts : [];
  if (list.length > MAX_MOUNTS) throw new Error('translation mount limit exceeded');
  const normalized = list.map((mount, index) => normalizeMount(mount, world, index));
  const seen = new Set();
  normalized.forEach(mount => {
    if (seen.has(mount.id)) throw new Error('duplicate translation mount id ' + mount.id);
    seen.add(mount.id);
  });
  return normalized.sort((a, b) => a.id.localeCompare(b.id));
}

function measureMount(world, mount) {
  const a = body(world, mount.a);
  const b = body(world, mount.b);
  if (!a || !b) throw new Error('translation mount body missing for ' + mount.id);
  const currentOffset = {
    x: b.position.x - a.position.x,
    y: b.position.y - a.position.y
  };
  const error = {
    x: currentOffset.x - mount.offset.x,
    y: currentOffset.y - mount.offset.y
  };
  return {
    id: mount.id,
    a: mount.a,
    b: mount.b,
    targetOffset: clone(mount.offset),
    offset: { x: round(currentOffset.x), y: round(currentOffset.y) },
    error: { x: round(error.x), y: round(error.y) },
    errorDistance: round(magnitude(error))
  };
}

function solvePosition(world, mount) {
  if (!mount.enabled) return { id: mount.id, enabled: false, solved: false, correction: { x: 0, y: 0 }, errorBefore: 0, errorAfter: 0 };
  const a = body(world, mount.a);
  const b = body(world, mount.b);
  if (!a || !b) throw new Error('translation mount body missing for ' + mount.id);
  const wa = inverseMass(a);
  const wb = inverseMass(b);
  const inverseTotal = wa + wb;
  const error = {
    x: (b.position.x - a.position.x) - mount.offset.x,
    y: (b.position.y - a.position.y) - mount.offset.y
  };
  const errorBefore = magnitude(error);
  if (!(inverseTotal > 0)) {
    return {
      id: mount.id,
      enabled: true,
      solved: false,
      reason: 'NO_DYNAMIC_MASS',
      correction: { x: 0, y: 0 },
      errorBefore: round(errorBefore),
      errorAfter: round(errorBefore)
    };
  }
  if (errorBefore <= mount.slop) {
    return {
      id: mount.id,
      enabled: true,
      solved: true,
      correction: { x: 0, y: 0 },
      errorBefore: round(errorBefore),
      errorAfter: round(errorBefore)
    };
  }
  wake(a);
  wake(b);
  const correction = clampMagnitude({
    x: error.x * mount.positionFactor,
    y: error.y * mount.positionFactor
  }, mount.maxCorrection);
  if (wa > 0) {
    a.position.x += correction.x * wa / inverseTotal;
    a.position.y += correction.y * wa / inverseTotal;
  }
  if (wb > 0) {
    b.position.x -= correction.x * wb / inverseTotal;
    b.position.y -= correction.y * wb / inverseTotal;
  }
  const afterError = {
    x: (b.position.x - a.position.x) - mount.offset.x,
    y: (b.position.y - a.position.y) - mount.offset.y
  };
  return {
    id: mount.id,
    enabled: true,
    solved: true,
    correction: { x: round(correction.x), y: round(correction.y) },
    errorBefore: round(errorBefore),
    errorAfter: round(magnitude(afterError))
  };
}

function solveVelocity(world, mount) {
  if (!mount.enabled) return { id: mount.id, enabled: false, solved: false, impulse: { x: 0, y: 0 }, relativeSpeedBefore: 0, relativeSpeedAfter: 0 };
  const a = body(world, mount.a);
  const b = body(world, mount.b);
  if (!a || !b) throw new Error('translation mount body missing for ' + mount.id);
  const wa = inverseMass(a);
  const wb = inverseMass(b);
  const inverseTotal = wa + wb;
  const relative = {
    x: b.velocity.x - a.velocity.x,
    y: b.velocity.y - a.velocity.y
  };
  const relativeSpeedBefore = magnitude(relative);
  if (!(inverseTotal > 0)) {
    return {
      id: mount.id,
      enabled: true,
      solved: false,
      reason: 'NO_DYNAMIC_MASS',
      impulse: { x: 0, y: 0 },
      relativeSpeedBefore: round(relativeSpeedBefore),
      relativeSpeedAfter: round(relativeSpeedBefore)
    };
  }
  if (relativeSpeedBefore <= 1e-12) {
    return {
      id: mount.id,
      enabled: true,
      solved: true,
      impulse: { x: 0, y: 0 },
      relativeSpeedBefore: round(relativeSpeedBefore),
      relativeSpeedAfter: round(relativeSpeedBefore)
    };
  }
  wake(a);
  wake(b);
  const impulse = clampMagnitude({
    x: relative.x * mount.velocityFactor / inverseTotal,
    y: relative.y * mount.velocityFactor / inverseTotal
  }, mount.maxImpulse);
  if (wa > 0) {
    a.velocity.x += impulse.x * wa;
    a.velocity.y += impulse.y * wa;
  }
  if (wb > 0) {
    b.velocity.x -= impulse.x * wb;
    b.velocity.y -= impulse.y * wb;
  }
  const after = {
    x: b.velocity.x - a.velocity.x,
    y: b.velocity.y - a.velocity.y
  };
  return {
    id: mount.id,
    enabled: true,
    solved: true,
    impulse: { x: round(impulse.x), y: round(impulse.y) },
    relativeSpeedBefore: round(relativeSpeedBefore),
    relativeSpeedAfter: round(magnitude(after))
  };
}

function solveIterations(world, normalized, positionIterations, velocityIterations) {
  const positionReceipts = [];
  const velocityReceipts = [];
  for (let iteration = 0; iteration < positionIterations; iteration++) {
    normalized.forEach(mount => positionReceipts.push(Object.assign({ iteration: iteration + 1 }, solvePosition(world, mount))));
  }
  for (let iteration = 0; iteration < velocityIterations; iteration++) {
    normalized.forEach(mount => velocityReceipts.push(Object.assign({ iteration: iteration + 1 }, solveVelocity(world, mount))));
  }
  world.bodies.forEach(item => {
    item.position.x = round(item.position.x);
    item.position.y = round(item.position.y);
    item.velocity.x = round(item.velocity.x);
    item.velocity.y = round(item.velocity.y);
  });
  return { positionReceipts, velocityReceipts };
}

function prepareWorld(world, mounts, options) {
  const out = clone(world);
  const normalized = normalizeMounts(mounts, out);
  const positionIterations = iterationCount(options && options.positionIterations, 8);
  const velocityIterations = iterationCount(options && options.velocityIterations, 4);
  const initial = normalized.map(mount => measureMount(out, mount));
  const receipts = solveIterations(out, normalized, positionIterations, velocityIterations);
  const afterPreSolve = normalized.map(mount => measureMount(out, mount));
  return {
    world: out,
    mounts: normalized,
    positionIterations,
    velocityIterations,
    initial,
    afterPreSolve,
    positionReceipts: receipts.positionReceipts,
    velocityReceipts: receipts.velocityReceipts
  };
}

function refreshDiagnostics(world, coreDiagnostics, beforeCoreDiagnostics) {
  const refreshed = Core.measure(
    world,
    coreDiagnostics.substeps,
    coreDiagnostics.maxPenetration,
    coreDiagnostics.broadphasePairs,
    {
      overflowBodies: coreDiagnostics.broadphaseOverflowBodies,
      cellEntries: coreDiagnostics.broadphaseCellEntries,
      occupiedCells: coreDiagnostics.broadphaseOccupiedCells,
      warmStartedContacts: coreDiagnostics.warmStartedContacts,
      warmStartAppliedImpulse: coreDiagnostics.warmStartAppliedImpulse,
      warmStartCorrectionImpulse: coreDiagnostics.warmStartCorrectionImpulse,
      detectedUniqueContacts: coreDiagnostics.detectedUniqueContacts
    }
  );
  refreshed.energyDelta = round(refreshed.totalEnergy - beforeCoreDiagnostics.totalEnergy);
  refreshed.translationMountPostStabilized = true;
  refreshed.contactEvidenceBasis = 'CORE_STAGE_BEFORE_POST_TRANSLATION_MOUNT_STABILIZATION';
  world.diagnostics = refreshed;
  return refreshed;
}

function step(world, mounts, dt, options) {
  const validation = Core.validate(world);
  if (!validation.ok) throw new Error(validation.errors.join('; '));
  options = options || {};
  const prepared = prepareWorld(world, mounts, options);
  const beforeCoreDiagnostics = Core.measure(prepared.world, 0, 0);
  const coreStep = Core.step(prepared.world, dt);
  const afterCore = prepared.mounts.map(mount => measureMount(coreStep.world, mount));
  const maxErrorAfterCoreStep = afterCore.reduce((max, item) => Math.max(max, item.errorDistance), 0);

  const postWorld = clone(coreStep.world);
  const postPositionIterations = iterationCount(options.postPositionIterations, 4);
  const postVelocityIterations = iterationCount(options.postVelocityIterations, 2);
  const postReceipts = solveIterations(postWorld, prepared.mounts, postPositionIterations, postVelocityIterations);
  const after = prepared.mounts.map(mount => measureMount(postWorld, mount));
  const maxErrorAfterStabilization = after.reduce((max, item) => Math.max(max, item.errorDistance), 0);
  const finalDiagnostics = refreshDiagnostics(postWorld, coreStep.diagnostics, beforeCoreDiagnostics);

  return {
    schema: STEP_SCHEMA,
    ok: true,
    world: postWorld,
    mounts: clone(prepared.mounts),
    mountDiagnostics: {
      positionIterations: prepared.positionIterations,
      velocityIterations: prepared.velocityIterations,
      postPositionIterations,
      postVelocityIterations,
      maxErrorAfterCoreStep: round(maxErrorAfterCoreStep),
      maxErrorAfterStabilization: round(maxErrorAfterStabilization),
      initial: prepared.initial,
      afterPreSolve: prepared.afterPreSolve,
      afterCore,
      after,
      positionReceipts: prepared.positionReceipts,
      velocityReceipts: prepared.velocityReceipts,
      postPositionReceipts: postReceipts.positionReceipts,
      postVelocityReceipts: postReceipts.velocityReceipts,
      contactEvidenceBasis: finalDiagnostics.contactEvidenceBasis
    },
    core: {
      diagnostics: clone(coreStep.diagnostics),
      events: clone(coreStep.events),
      worldBeforePostMountStabilization: clone(coreStep.world)
    },
    evidence: [
      prepared.mounts.length + ' translation mount(s) normalized in deterministic id order',
      prepared.positionIterations + ' translation-offset position iteration(s) executed before the core step',
      prepared.velocityIterations + ' relative-velocity iteration(s) executed before the core step',
      'AXM Physics Core v' + Core.VERSION + ' executed collisions and integration from the mounted start state',
      postPositionIterations + ' translation-offset stabilization iteration(s) executed after the core step',
      postVelocityIterations + ' relative-velocity stabilization iteration(s) executed after the core step',
      'Mount error changed from ' + round(maxErrorAfterCoreStep) + ' after core integration to ' + round(maxErrorAfterStabilization) + ' after post-core stabilization',
      'Final state checksum ' + Core.checksum(postWorld)
    ],
    limitations: [
      'Translation mounts preserve a fixed world-axis x/y offset only; they do not rotate anchor offsets with bodies.',
      'No angular inertia, angular response or rotational weld semantics are implemented.',
      'Post-core mount projection can change positions after collision/contact evidence was generated; returned core events and contact geometry therefore describe the core stage before post-mount stabilization.',
      'Connected mounted bodies can still collide unless caller collision filters suppress that pair.',
      'This is game/prototype physics evidence, not scientific validation.'
    ]
  };
}

function simulate(world, mounts, steps, dt, options) {
  let out = clone(world);
  const count = Math.max(1, Math.min(100000, Math.round(finite(steps, 1))));
  let last = null;
  for (let index = 0; index < count; index++) {
    last = step(out, mounts, dt, options);
    out = last.world;
  }
  return {
    schema: 'axm.uc-translation-mount-simulation/v0.1',
    ok: true,
    steps: count,
    world: out,
    mounts: last ? last.mounts : normalizeMounts(mounts, out),
    mountDiagnostics: last ? last.mountDiagnostics : null,
    checksum: Core.checksum(out),
    evidence: (last ? last.evidence : []).concat([count + ' translation-mount step(s) completed'])
  };
}

function validate(world, mounts) {
  const core = Core.validate(world);
  const errors = (core.errors || []).slice();
  let normalized = [];
  if (core.ok) {
    try { normalized = normalizeMounts(mounts, world); }
    catch (error) { errors.push(error.message); }
  }
  return {
    ok: errors.length === 0,
    errors,
    mountCount: normalized.length,
    warnings: [
      'This solver provides translation-only fixed-offset mounts, not rotational weld joints.',
      'Post-core stabilization is additive around the imported v0.3.1 core; core-stage contact evidence is not silently relabeled as post-stabilization contact truth.',
      'The imported donor source remains untouched.'
    ]
  };
}

module.exports = {
  VERSION,
  MOUNT_SCHEMA,
  STEP_SCHEMA,
  MAX_MOUNTS,
  normalizeMount,
  normalizeMounts,
  measureMount,
  prepareWorld,
  step,
  simulate,
  validate
};
