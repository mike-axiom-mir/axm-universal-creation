'use strict';

const Core = require('./source/axm-physics-core.js');

const VERSION = '0.1.0';
const LIMIT_SCHEMA = 'axm.uc-axis-limit/v0.1';
const STEP_SCHEMA = 'axm.uc-axis-limit-step/v0.1';
const SIMULATION_SCHEMA = 'axm.uc-axis-limit-simulation/v0.1';
const MAX_LIMITS = 4096;
const MAX_OFFSET = 1e9;

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

function axisValue(vector, axis) {
  return finite(vector && vector[axis], 0);
}

function normalizeLimit(input, world, index) {
  input = input || {};
  const a = String(input.a || '').trim();
  const b = String(input.b || '').trim();
  if (!a || !b || a === b) throw new Error('axis limit requires distinct a and b body ids');
  const bodyA = body(world, a);
  const bodyB = body(world, b);
  if (!bodyA || !bodyB) throw new Error('axis limit body not found: ' + (!bodyA ? a : b));

  const axis = String(input.axis || '').trim().toLowerCase();
  if (axis !== 'x' && axis !== 'y') throw new Error('axis limit requires axis "x" or "y"');

  const hasMin = input.minOffset !== undefined && input.minOffset !== null;
  const hasMax = input.maxOffset !== undefined && input.maxOffset !== null;
  if (!hasMin && !hasMax) throw new Error('axis limit requires minOffset and/or maxOffset');

  const minOffset = hasMin ? bounded(input.minOffset, -MAX_OFFSET, MAX_OFFSET, -MAX_OFFSET) : -MAX_OFFSET;
  const maxOffset = hasMax ? bounded(input.maxOffset, -MAX_OFFSET, MAX_OFFSET, MAX_OFFSET) : MAX_OFFSET;
  if (minOffset > maxOffset) throw new Error('axis limit minOffset must be <= maxOffset');

  return {
    schema: LIMIT_SCHEMA,
    id: String(input.id || ('axis-limit-' + String(index + 1).padStart(3, '0'))),
    a,
    b,
    axis,
    minOffset,
    maxOffset,
    positionFactor: bounded(input.positionFactor, 0, 1, 1),
    velocityFactor: bounded(input.velocityFactor, 0, 1, 1),
    slop: bounded(input.slop, 0, 1e6, 1e-6),
    maxCorrection: bounded(input.maxCorrection, 0, MAX_OFFSET, 1e6),
    maxImpulse: bounded(input.maxImpulse, 0, 1e12, 1e9),
    enabled: input.enabled !== false,
    userData: clone(input.userData || {})
  };
}

function normalizeLimits(limits, world) {
  const list = Array.isArray(limits) ? limits : [];
  if (list.length > MAX_LIMITS) throw new Error('axis limit count exceeded');
  const normalized = list.map((limit, index) => normalizeLimit(limit, world, index));
  const seen = new Set();
  normalized.forEach(limit => {
    if (seen.has(limit.id)) throw new Error('duplicate axis limit id ' + limit.id);
    seen.add(limit.id);
  });
  return normalized.sort((left, right) => left.id.localeCompare(right.id));
}

function positionError(offset, limit) {
  if (offset < limit.minOffset) return offset - limit.minOffset;
  if (offset > limit.maxOffset) return offset - limit.maxOffset;
  return 0;
}

function limitState(offset, limit) {
  if (offset < limit.minOffset) return 'BELOW_MIN';
  if (offset > limit.maxOffset) return 'ABOVE_MAX';
  if (Math.abs(offset - limit.minOffset) <= limit.slop) return 'AT_MIN';
  if (Math.abs(offset - limit.maxOffset) <= limit.slop) return 'AT_MAX';
  return 'SLACK';
}

function measureLimit(world, limit) {
  const a = body(world, limit.a);
  const b = body(world, limit.b);
  if (!a || !b) throw new Error('axis limit body missing for ' + limit.id);
  const offset = axisValue(b.position, limit.axis) - axisValue(a.position, limit.axis);
  const error = positionError(offset, limit);
  const orthogonalAxis = limit.axis === 'x' ? 'y' : 'x';
  return {
    id: limit.id,
    a: limit.a,
    b: limit.b,
    enabled: limit.enabled,
    axis: limit.axis,
    minOffset: limit.minOffset,
    maxOffset: limit.maxOffset,
    offset: round(offset),
    error: round(error),
    state: limitState(offset, limit),
    violated: limit.enabled && Math.abs(error) > limit.slop,
    orthogonalOffset: round(axisValue(b.position, orthogonalAxis) - axisValue(a.position, orthogonalAxis))
  };
}

function velocityViolation(world, limit) {
  const a = body(world, limit.a);
  const b = body(world, limit.b);
  if (!a || !b) throw new Error('axis limit body missing for ' + limit.id);
  const offset = axisValue(b.position, limit.axis) - axisValue(a.position, limit.axis);
  const relative = axisValue(b.velocity, limit.axis) - axisValue(a.velocity, limit.axis);
  const atMin = offset <= limit.minOffset + limit.slop;
  const atMax = offset >= limit.maxOffset - limit.slop;
  const minViolation = atMin && relative < -1e-12;
  const maxViolation = atMax && relative > 1e-12;
  return {
    active: limit.enabled && (minViolation || maxViolation),
    boundary: minViolation ? 'MIN' : (maxViolation ? 'MAX' : null),
    relativeSpeed: round(relative)
  };
}

function solvePosition(world, limit) {
  if (!limit.enabled) return { id: limit.id, enabled: false, solved: false, constrained: false, correction: 0, errorBefore: 0, errorAfter: 0 };
  const a = body(world, limit.a);
  const b = body(world, limit.b);
  if (!a || !b) throw new Error('axis limit body missing for ' + limit.id);
  const wa = inverseMass(a);
  const wb = inverseMass(b);
  const inverseTotal = wa + wb;
  const offset = axisValue(b.position, limit.axis) - axisValue(a.position, limit.axis);
  const errorBefore = positionError(offset, limit);

  if (Math.abs(errorBefore) <= limit.slop) {
    return { id: limit.id, enabled: true, solved: true, constrained: false, correction: 0, errorBefore: round(errorBefore), errorAfter: round(errorBefore) };
  }
  if (!(inverseTotal > 0)) {
    return { id: limit.id, enabled: true, solved: false, constrained: true, reason: 'NO_DYNAMIC_MASS', correction: 0, errorBefore: round(errorBefore), errorAfter: round(errorBefore) };
  }

  wake(a);
  wake(b);
  const signedCorrection = Math.max(-limit.maxCorrection, Math.min(limit.maxCorrection, errorBefore * limit.positionFactor));
  if (wa > 0) a.position[limit.axis] += signedCorrection * wa / inverseTotal;
  if (wb > 0) b.position[limit.axis] -= signedCorrection * wb / inverseTotal;
  const afterOffset = axisValue(b.position, limit.axis) - axisValue(a.position, limit.axis);
  const errorAfter = positionError(afterOffset, limit);
  return {
    id: limit.id,
    enabled: true,
    solved: true,
    constrained: true,
    correction: round(signedCorrection),
    errorBefore: round(errorBefore),
    errorAfter: round(errorAfter)
  };
}

function solveVelocity(world, limit) {
  if (!limit.enabled) return { id: limit.id, enabled: false, solved: false, constrained: false, impulse: 0, relativeSpeedBefore: 0, relativeSpeedAfter: 0 };
  const a = body(world, limit.a);
  const b = body(world, limit.b);
  if (!a || !b) throw new Error('axis limit body missing for ' + limit.id);
  const violation = velocityViolation(world, limit);
  if (!violation.active) {
    return {
      id: limit.id,
      enabled: true,
      solved: true,
      constrained: false,
      boundary: null,
      impulse: 0,
      relativeSpeedBefore: violation.relativeSpeed,
      relativeSpeedAfter: violation.relativeSpeed
    };
  }

  const wa = inverseMass(a);
  const wb = inverseMass(b);
  const inverseTotal = wa + wb;
  if (!(inverseTotal > 0)) {
    return {
      id: limit.id,
      enabled: true,
      solved: false,
      constrained: true,
      boundary: violation.boundary,
      reason: 'NO_DYNAMIC_MASS',
      impulse: 0,
      relativeSpeedBefore: violation.relativeSpeed,
      relativeSpeedAfter: violation.relativeSpeed
    };
  }

  wake(a);
  wake(b);
  let impulse = violation.relativeSpeed * limit.velocityFactor / inverseTotal;
  impulse = Math.max(-limit.maxImpulse, Math.min(limit.maxImpulse, impulse));
  if (wa > 0) a.velocity[limit.axis] += impulse * wa;
  if (wb > 0) b.velocity[limit.axis] -= impulse * wb;
  const relativeAfter = axisValue(b.velocity, limit.axis) - axisValue(a.velocity, limit.axis);
  return {
    id: limit.id,
    enabled: true,
    solved: true,
    constrained: true,
    boundary: violation.boundary,
    impulse: round(impulse),
    relativeSpeedBefore: violation.relativeSpeed,
    relativeSpeedAfter: round(relativeAfter)
  };
}

function solveIterations(world, normalized, positionIterations, velocityIterations) {
  const positionReceipts = [];
  const velocityReceipts = [];
  for (let iteration = 0; iteration < positionIterations; iteration++) {
    normalized.forEach(limit => positionReceipts.push(Object.assign({ iteration: iteration + 1 }, solvePosition(world, limit))));
  }
  for (let iteration = 0; iteration < velocityIterations; iteration++) {
    normalized.forEach(limit => velocityReceipts.push(Object.assign({ iteration: iteration + 1 }, solveVelocity(world, limit))));
  }
  world.bodies.forEach(item => {
    item.position.x = round(item.position.x);
    item.position.y = round(item.position.y);
    item.velocity.x = round(item.velocity.x);
    item.velocity.y = round(item.velocity.y);
  });
  return { positionReceipts, velocityReceipts };
}

function prepareWorld(world, limits, options) {
  const out = clone(world);
  const normalized = normalizeLimits(limits, out);
  const positionIterations = iterationCount(options && options.positionIterations, 8);
  const velocityIterations = iterationCount(options && options.velocityIterations, 4);
  const initial = normalized.map(limit => measureLimit(out, limit));
  const receipts = solveIterations(out, normalized, positionIterations, velocityIterations);
  const afterPreSolve = normalized.map(limit => measureLimit(out, limit));
  return {
    world: out,
    limits: normalized,
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
  refreshed.axisLimitPostStabilized = true;
  refreshed.contactEvidenceBasis = 'CORE_STAGE_BEFORE_POST_AXIS_LIMIT_STABILIZATION';
  world.diagnostics = refreshed;
  return refreshed;
}

function maxViolation(items) {
  return round(items.reduce((max, item) => item.enabled ? Math.max(max, Math.abs(item.error)) : max, 0));
}

function step(world, limits, dt, options) {
  const validation = Core.validate(world);
  if (!validation.ok) throw new Error(validation.errors.join('; '));
  options = options || {};
  const prepared = prepareWorld(world, limits, options);
  const beforeCoreDiagnostics = Core.measure(prepared.world, 0, 0);
  const coreStep = Core.step(prepared.world, dt);
  const afterCore = prepared.limits.map(limit => measureLimit(coreStep.world, limit));
  const maxViolationAfterCoreStep = maxViolation(afterCore);

  const postWorld = clone(coreStep.world);
  const postPositionIterations = iterationCount(options.postPositionIterations, 4);
  const postVelocityIterations = iterationCount(options.postVelocityIterations, 2);
  const postReceipts = solveIterations(postWorld, prepared.limits, postPositionIterations, postVelocityIterations);
  const after = prepared.limits.map(limit => measureLimit(postWorld, limit));
  const maxViolationAfterStabilization = maxViolation(after);
  const finalDiagnostics = refreshDiagnostics(postWorld, coreStep.diagnostics, beforeCoreDiagnostics);

  return {
    schema: STEP_SCHEMA,
    ok: true,
    world: postWorld,
    limits: clone(prepared.limits),
    axisLimitDiagnostics: {
      positionIterations: prepared.positionIterations,
      velocityIterations: prepared.velocityIterations,
      postPositionIterations,
      postVelocityIterations,
      maxViolationAfterCoreStep,
      maxViolationAfterStabilization,
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
      worldBeforePostAxisLimitStabilization: clone(coreStep.world)
    },
    evidence: [
      prepared.limits.length + ' world-axis translation limit(s) normalized in deterministic id order',
      prepared.positionIterations + ' bounded axis-limit position iteration(s) executed before the donor-core step',
      prepared.velocityIterations + ' boundary-directed axis-limit velocity iteration(s) executed before the donor-core step',
      'AXM Physics Core v' + Core.VERSION + ' executed collision/integration without donor-source modification',
      postPositionIterations + ' bounded axis-limit position stabilization iteration(s) executed after the donor-core step',
      postVelocityIterations + ' boundary-directed axis-limit velocity stabilization iteration(s) executed after the donor-core step',
      'Maximum enabled axis-limit violation changed from ' + maxViolationAfterCoreStep + ' after core integration to ' + maxViolationAfterStabilization + ' after stabilization',
      'Final state checksum ' + Core.checksum(postWorld)
    ],
    limitations: [
      'Axis limits bound one world-space x or y relative offset only; orthogonal translation intentionally remains free.',
      'The constrained axis does not rotate with either body and this is not a full prismatic/slider joint.',
      'Slack motion inside the allowed interval is intentionally unconstrained; only violated or outward-moving boundaries activate.',
      'No angular inertia, rotating anchors, angular limits or motors are implemented.',
      'Post-core projection can move bodies after collision/contact evidence was generated; returned core events and contact geometry describe the donor-core stage before post-axis-limit stabilization.',
      'The standalone v0.1.0 entrypoint performs its own donor-core step; mixed-family callers must use the shared composer/activity/isolation path rather than chaining wrappers.',
      'This is game/prototype physics evidence, not scientific validation.'
    ]
  };
}

function simulate(world, limits, steps, dt, options) {
  let out = clone(world);
  const count = Math.max(1, Math.min(100000, Math.round(finite(steps, 1))));
  let last = null;
  for (let index = 0; index < count; index++) {
    last = step(out, limits, dt, options || {});
    out = last.world;
  }
  return {
    schema: SIMULATION_SCHEMA,
    ok: true,
    steps: count,
    world: out,
    limits: last ? last.limits : normalizeLimits(limits, out),
    axisLimitDiagnostics: last ? last.axisLimitDiagnostics : null,
    checksum: Core.checksum(out),
    evidence: (last ? last.evidence : []).concat([count + ' axis-limit step(s) completed'])
  };
}

function validate(world, limits) {
  const core = Core.validate(world);
  const errors = (core.errors || []).slice();
  let normalized = [];
  if (core.ok) {
    try { normalized = normalizeLimits(limits, world); }
    catch (error) { errors.push(error.message); }
  }
  return {
    ok: errors.length === 0,
    errors,
    limitCount: normalized.length,
    warnings: [
      'Axis limits bound one world-space x or y relative offset while orthogonal translation remains intentionally unconstrained.',
      'Slack motion inside min/max bounds is intentionally free; this is not a rotational or full prismatic/slider joint.',
      'The donor physics source remains untouched; this standalone v0.1.0 entrypoint is also consumed by the shared composer without a second donor-core step.'
    ]
  };
}

module.exports = {
  VERSION,
  LIMIT_SCHEMA,
  STEP_SCHEMA,
  SIMULATION_SCHEMA,
  MAX_LIMITS,
  normalizeLimit,
  normalizeLimits,
  measureLimit,
  velocityViolation,
  solvePosition,
  solveVelocity,
  prepareWorld,
  step,
  simulate,
  validate
};