'use strict';

const Core = require('./source/axm-physics-core.js');

const VERSION = '0.1.0';
const LIMIT_SCHEMA = 'axm.uc-direction-limit/v0.1';
const STEP_SCHEMA = 'axm.uc-direction-limit-step/v0.1';
const SIMULATION_SCHEMA = 'axm.uc-direction-limit-simulation/v0.1';
const MAX_LIMITS = 4096;
const MAX_OFFSET = 1e9;
const MIN_DIRECTION_LENGTH = 1e-12;

function clone(value) { return JSON.parse(JSON.stringify(value)); }
function finite(value, fallback) { const n = Number(value); return Number.isFinite(n) ? n : fallback; }
function bounded(value, min, max, fallback) { return Math.max(min, Math.min(max, finite(value, fallback))); }
function iterationCount(value, fallback) { return Math.round(bounded(value, 0, 32, fallback)); }
function round(value) { return Math.round(value * 1e9) / 1e9; }
function body(world, id) { return (world.bodies || []).find(item => item.id === id) || null; }
function inverseMass(item) { return item && item.enabled && item.type === 'dynamic' ? finite(item.invMass, 0) : 0; }
function wake(item) { if (!item || item.type !== 'dynamic') return; item.sleeping = false; item.sleepFrames = 0; }
function component(vector, key) { return finite(vector && vector[key], 0); }
function relativeVector(a, b, field) {
  const av = a && a[field] ? a[field] : {};
  const bv = b && b[field] ? b[field] : {};
  return { x: component(bv, 'x') - component(av, 'x'), y: component(bv, 'y') - component(av, 'y') };
}
function dot(vector, direction) { return component(vector, 'x') * direction.x + component(vector, 'y') * direction.y; }
function perpendicular(direction) { return { x: -direction.y, y: direction.x }; }

function normalizeDirection(input) {
  const source = input || {};
  const x = Number(source.x);
  const y = Number(source.y);
  if (!Number.isFinite(x) || !Number.isFinite(y)) throw new Error('direction limit requires finite direction x and y');
  const length = Math.hypot(x, y);
  if (!(length > MIN_DIRECTION_LENGTH)) throw new Error('direction limit requires a non-zero direction vector');
  return { x: x / length, y: y / length };
}

function normalizeLimit(input, world, index) {
  input = input || {};
  const a = String(input.a || '').trim();
  const b = String(input.b || '').trim();
  if (!a || !b || a === b) throw new Error('direction limit requires distinct a and b body ids');
  const bodyA = body(world, a);
  const bodyB = body(world, b);
  if (!bodyA || !bodyB) throw new Error('direction limit body not found: ' + (!bodyA ? a : b));

  const direction = normalizeDirection(input.direction);
  const hasMin = input.minOffset !== undefined && input.minOffset !== null;
  const hasMax = input.maxOffset !== undefined && input.maxOffset !== null;
  if (!hasMin && !hasMax) throw new Error('direction limit requires minOffset and/or maxOffset');
  const minOffset = hasMin ? bounded(input.minOffset, -MAX_OFFSET, MAX_OFFSET, -MAX_OFFSET) : -MAX_OFFSET;
  const maxOffset = hasMax ? bounded(input.maxOffset, -MAX_OFFSET, MAX_OFFSET, MAX_OFFSET) : MAX_OFFSET;
  if (minOffset > maxOffset) throw new Error('direction limit minOffset must be <= maxOffset');

  return {
    schema: LIMIT_SCHEMA,
    id: String(input.id || ('direction-limit-' + String(index + 1).padStart(3, '0'))),
    a,
    b,
    direction,
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
  if (list.length > MAX_LIMITS) throw new Error('direction limit count exceeded');
  const normalized = list.map((limit, index) => normalizeLimit(limit, world, index));
  const seen = new Set();
  normalized.forEach(limit => {
    if (seen.has(limit.id)) throw new Error('duplicate direction limit id ' + limit.id);
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
  if (!a || !b) throw new Error('direction limit body missing for ' + limit.id);
  const relative = relativeVector(a, b, 'position');
  const offset = dot(relative, limit.direction);
  const error = positionError(offset, limit);
  return {
    id: limit.id,
    a: limit.a,
    b: limit.b,
    enabled: limit.enabled,
    direction: { x: round(limit.direction.x), y: round(limit.direction.y) },
    minOffset: round(limit.minOffset),
    maxOffset: round(limit.maxOffset),
    offset: round(offset),
    error: round(error),
    state: limitState(offset, limit),
    violated: limit.enabled && Math.abs(error) > limit.slop,
    perpendicularOffset: round(dot(relative, perpendicular(limit.direction)))
  };
}

function velocityViolation(world, limit) {
  const a = body(world, limit.a);
  const b = body(world, limit.b);
  if (!a || !b) throw new Error('direction limit body missing for ' + limit.id);
  const offset = dot(relativeVector(a, b, 'position'), limit.direction);
  const relative = dot(relativeVector(a, b, 'velocity'), limit.direction);
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
  if (!a || !b) throw new Error('direction limit body missing for ' + limit.id);
  const wa = inverseMass(a);
  const wb = inverseMass(b);
  const inverseTotal = wa + wb;
  const errorBefore = positionError(dot(relativeVector(a, b, 'position'), limit.direction), limit);
  if (Math.abs(errorBefore) <= limit.slop) {
    return { id: limit.id, enabled: true, solved: true, constrained: false, correction: 0, errorBefore: round(errorBefore), errorAfter: round(errorBefore) };
  }
  if (!(inverseTotal > 0)) {
    return { id: limit.id, enabled: true, solved: false, constrained: true, reason: 'NO_DYNAMIC_MASS', correction: 0, errorBefore: round(errorBefore), errorAfter: round(errorBefore) };
  }

  wake(a);
  wake(b);
  const signedCorrection = Math.max(-limit.maxCorrection, Math.min(limit.maxCorrection, errorBefore * limit.positionFactor));
  if (wa > 0) {
    a.position.x += limit.direction.x * signedCorrection * wa / inverseTotal;
    a.position.y += limit.direction.y * signedCorrection * wa / inverseTotal;
  }
  if (wb > 0) {
    b.position.x -= limit.direction.x * signedCorrection * wb / inverseTotal;
    b.position.y -= limit.direction.y * signedCorrection * wb / inverseTotal;
  }
  const errorAfter = positionError(dot(relativeVector(a, b, 'position'), limit.direction), limit);
  return { id: limit.id, enabled: true, solved: true, constrained: true, correction: round(signedCorrection), errorBefore: round(errorBefore), errorAfter: round(errorAfter) };
}

function solveVelocity(world, limit) {
  if (!limit.enabled) return { id: limit.id, enabled: false, solved: false, constrained: false, impulse: 0, relativeSpeedBefore: 0, relativeSpeedAfter: 0 };
  const a = body(world, limit.a);
  const b = body(world, limit.b);
  if (!a || !b) throw new Error('direction limit body missing for ' + limit.id);
  const violation = velocityViolation(world, limit);
  if (!violation.active) {
    return { id: limit.id, enabled: true, solved: true, constrained: false, boundary: null, impulse: 0, relativeSpeedBefore: violation.relativeSpeed, relativeSpeedAfter: violation.relativeSpeed };
  }

  const wa = inverseMass(a);
  const wb = inverseMass(b);
  const inverseTotal = wa + wb;
  if (!(inverseTotal > 0)) {
    return { id: limit.id, enabled: true, solved: false, constrained: true, boundary: violation.boundary, reason: 'NO_DYNAMIC_MASS', impulse: 0, relativeSpeedBefore: violation.relativeSpeed, relativeSpeedAfter: violation.relativeSpeed };
  }

  wake(a);
  wake(b);
  let impulse = violation.relativeSpeed * limit.velocityFactor / inverseTotal;
  impulse = Math.max(-limit.maxImpulse, Math.min(limit.maxImpulse, impulse));
  if (wa > 0) {
    a.velocity.x += limit.direction.x * impulse * wa;
    a.velocity.y += limit.direction.y * impulse * wa;
  }
  if (wb > 0) {
    b.velocity.x -= limit.direction.x * impulse * wb;
    b.velocity.y -= limit.direction.y * impulse * wb;
  }
  const relativeAfter = dot(relativeVector(a, b, 'velocity'), limit.direction);
  return { id: limit.id, enabled: true, solved: true, constrained: true, boundary: violation.boundary, impulse: round(impulse), relativeSpeedBefore: violation.relativeSpeed, relativeSpeedAfter: round(relativeAfter) };
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
  return {
    world: out,
    limits: normalized,
    positionIterations,
    velocityIterations,
    initial,
    afterPreSolve: normalized.map(limit => measureLimit(out, limit)),
    positionReceipts: receipts.positionReceipts,
    velocityReceipts: receipts.velocityReceipts
  };
}

function refreshDiagnostics(world, coreDiagnostics, beforeCoreDiagnostics) {
  const refreshed = Core.measure(world, coreDiagnostics.substeps, coreDiagnostics.maxPenetration, coreDiagnostics.broadphasePairs, {
    overflowBodies: coreDiagnostics.broadphaseOverflowBodies,
    cellEntries: coreDiagnostics.broadphaseCellEntries,
    occupiedCells: coreDiagnostics.broadphaseOccupiedCells,
    warmStartedContacts: coreDiagnostics.warmStartedContacts,
    warmStartAppliedImpulse: coreDiagnostics.warmStartAppliedImpulse,
    warmStartCorrectionImpulse: coreDiagnostics.warmStartCorrectionImpulse,
    detectedUniqueContacts: coreDiagnostics.detectedUniqueContacts
  });
  refreshed.energyDelta = round(refreshed.totalEnergy - beforeCoreDiagnostics.totalEnergy);
  refreshed.directionLimitPostStabilized = true;
  refreshed.contactEvidenceBasis = 'CORE_STAGE_BEFORE_POST_DIRECTION_LIMIT_STABILIZATION';
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
    directionLimitDiagnostics: {
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
      worldBeforePostDirectionLimitStabilization: clone(coreStep.world)
    },
    evidence: [
      prepared.limits.length + ' fixed-direction translation limit(s) normalized in deterministic id order',
      prepared.positionIterations + ' bounded direction-limit position iteration(s) executed before the donor-core step',
      prepared.velocityIterations + ' boundary-directed direction-limit velocity iteration(s) executed before the donor-core step',
      'AXM Physics Core v' + Core.VERSION + ' executed collision/integration without donor-source modification',
      postPositionIterations + ' bounded direction-limit position stabilization iteration(s) executed after the donor-core step',
      postVelocityIterations + ' boundary-directed direction-limit velocity stabilization iteration(s) executed after the donor-core step',
      'Maximum enabled direction-limit violation changed from ' + maxViolationAfterCoreStep + ' after core integration to ' + maxViolationAfterStabilization + ' after stabilization',
      'Final state checksum ' + Core.checksum(postWorld)
    ],
    limitations: [
      'Direction limits bound one fixed world-space translation projection only; perpendicular translation intentionally remains free.',
      'The direction does not rotate with either body and this is not a full prismatic/slider joint.',
      'Slack motion inside the allowed interval is intentionally unconstrained; only violated or outward-moving boundaries activate.',
      'No angular inertia, rotating anchors, angular limits or motors are implemented.',
      'Post-core projection can move bodies after collision/contact evidence was generated; returned core events and contact geometry describe the donor-core stage before post-direction-limit stabilization.',
      'Connected limited bodies can still collide unless caller collision filters suppress that pair or a separate isolation wrapper later supports this family.',
      'This standalone v0.1.0 entrypoint performs its own donor-core step; it is not yet integrated into the shared composer/activity/isolation stack.',
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
    directionLimitDiagnostics: last ? last.directionLimitDiagnostics : null,
    checksum: Core.checksum(out),
    evidence: (last ? last.evidence : []).concat([count + ' direction-limit step(s) completed'])
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
      'Direction limits bound one fixed caller-selected world-space translation projection while perpendicular translation remains intentionally unconstrained.',
      'Slack motion inside min/max bounds is intentionally free; the direction does not rotate with bodies and this is not a full prismatic/slider joint.',
      'The donor physics source remains untouched; this standalone v0.1.0 entrypoint is not yet integrated into the shared composer/activity/isolation stack.'
    ]
  };
}

module.exports = {
  VERSION,
  LIMIT_SCHEMA,
  STEP_SCHEMA,
  SIMULATION_SCHEMA,
  MAX_LIMITS,
  normalizeDirection,
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
