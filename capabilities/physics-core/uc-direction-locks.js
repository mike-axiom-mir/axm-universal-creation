'use strict';

const Core = require('./source/axm-physics-core.js');

const VERSION = '0.1.1';
const LOCK_SCHEMA = 'axm.uc-direction-lock/v0.1';
const STEP_SCHEMA = 'axm.uc-direction-lock-step/v0.1';
const SIMULATION_SCHEMA = 'axm.uc-direction-lock-simulation/v0.1';
const MAX_LOCKS = 4096;
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
function dot(vector, direction) { return component(vector, 'x') * direction.x + component(vector, 'y') * direction.y; }
function relativeVector(a, b, field) {
  const av = a && a[field] ? a[field] : {};
  const bv = b && b[field] ? b[field] : {};
  return { x: component(bv, 'x') - component(av, 'x'), y: component(bv, 'y') - component(av, 'y') };
}
function perpendicular(direction) { return { x: -direction.y, y: direction.x }; }

function normalizeDirection(input) {
  const source = input || {};
  const x = Number(source.x);
  const y = Number(source.y);
  if (!Number.isFinite(x) || !Number.isFinite(y)) throw new Error('direction lock requires finite direction x and y');
  const length = Math.hypot(x, y);
  if (!(length > MIN_DIRECTION_LENGTH)) throw new Error('direction lock requires a non-zero direction vector');
  return { x: x / length, y: y / length };
}

function normalizeLock(input, world, index) {
  input = input || {};
  const a = String(input.a || '').trim();
  const b = String(input.b || '').trim();
  if (!a || !b || a === b) throw new Error('direction lock requires distinct a and b body ids');
  const bodyA = body(world, a);
  const bodyB = body(world, b);
  if (!bodyA || !bodyB) throw new Error('direction lock body not found: ' + (!bodyA ? a : b));
  const direction = normalizeDirection(input.direction);
  const currentOffset = dot(relativeVector(bodyA, bodyB, 'position'), direction);
  return {
    schema: LOCK_SCHEMA,
    id: String(input.id || ('direction-lock-' + String(index + 1).padStart(3, '0'))),
    a, b, direction,
    offset: bounded(input.offset, -1e9, 1e9, currentOffset),
    positionFactor: bounded(input.positionFactor, 0, 1, 1),
    velocityFactor: bounded(input.velocityFactor, 0, 1, 1),
    slop: bounded(input.slop, 0, 1e6, 1e-6),
    maxCorrection: bounded(input.maxCorrection, 0, 1e9, 1e6),
    maxImpulse: bounded(input.maxImpulse, 0, 1e12, 1e9),
    enabled: input.enabled !== false,
    userData: clone(input.userData || {})
  };
}

function normalizeLocks(locks, world) {
  const list = Array.isArray(locks) ? locks : [];
  if (list.length > MAX_LOCKS) throw new Error('direction lock limit exceeded');
  const normalized = list.map((lock, index) => normalizeLock(lock, world, index));
  const seen = new Set();
  normalized.forEach(lock => { if (seen.has(lock.id)) throw new Error('duplicate direction lock id ' + lock.id); seen.add(lock.id); });
  return normalized.sort((left, right) => left.id.localeCompare(right.id));
}

function measureLock(world, lock) {
  const a = body(world, lock.a); const b = body(world, lock.b);
  if (!a || !b) throw new Error('direction lock body missing for ' + lock.id);
  const relative = relativeVector(a, b, 'position');
  const offset = dot(relative, lock.direction);
  const error = offset - lock.offset;
  return {
    id: lock.id, a: lock.a, b: lock.b,
    direction: { x: round(lock.direction.x), y: round(lock.direction.y) },
    targetOffset: round(lock.offset), offset: round(offset), error: round(error),
    perpendicularOffset: round(dot(relative, perpendicular(lock.direction)))
  };
}

function solvePosition(world, lock) {
  if (!lock.enabled) return { id: lock.id, enabled: false, solved: false, correction: 0, errorBefore: 0, errorAfter: 0 };
  const a = body(world, lock.a); const b = body(world, lock.b);
  if (!a || !b) throw new Error('direction lock body missing for ' + lock.id);
  const wa = inverseMass(a); const wb = inverseMass(b); const inverseTotal = wa + wb;
  const errorBefore = dot(relativeVector(a, b, 'position'), lock.direction) - lock.offset;
  if (!(inverseTotal > 0)) return { id: lock.id, enabled: true, solved: false, reason: 'NO_DYNAMIC_MASS', correction: 0, errorBefore: round(errorBefore), errorAfter: round(errorBefore) };
  if (Math.abs(errorBefore) <= lock.slop) return { id: lock.id, enabled: true, solved: true, correction: 0, errorBefore: round(errorBefore), errorAfter: round(errorBefore) };
  wake(a); wake(b);
  const signedCorrection = Math.max(-lock.maxCorrection, Math.min(lock.maxCorrection, errorBefore * lock.positionFactor));
  if (wa > 0) { a.position.x += lock.direction.x * signedCorrection * wa / inverseTotal; a.position.y += lock.direction.y * signedCorrection * wa / inverseTotal; }
  if (wb > 0) { b.position.x -= lock.direction.x * signedCorrection * wb / inverseTotal; b.position.y -= lock.direction.y * signedCorrection * wb / inverseTotal; }
  const errorAfter = dot(relativeVector(a, b, 'position'), lock.direction) - lock.offset;
  return { id: lock.id, enabled: true, solved: true, correction: round(signedCorrection), errorBefore: round(errorBefore), errorAfter: round(errorAfter) };
}

function solveVelocity(world, lock) {
  if (!lock.enabled) return { id: lock.id, enabled: false, solved: false, impulse: 0, relativeSpeedBefore: 0, relativeSpeedAfter: 0 };
  const a = body(world, lock.a); const b = body(world, lock.b);
  if (!a || !b) throw new Error('direction lock body missing for ' + lock.id);
  const wa = inverseMass(a); const wb = inverseMass(b); const inverseTotal = wa + wb;
  const relativeBefore = dot(relativeVector(a, b, 'velocity'), lock.direction);
  if (!(inverseTotal > 0)) return { id: lock.id, enabled: true, solved: false, reason: 'NO_DYNAMIC_MASS', impulse: 0, relativeSpeedBefore: round(relativeBefore), relativeSpeedAfter: round(relativeBefore) };
  if (Math.abs(relativeBefore) <= 1e-12) return { id: lock.id, enabled: true, solved: true, impulse: 0, relativeSpeedBefore: round(relativeBefore), relativeSpeedAfter: round(relativeBefore) };
  wake(a); wake(b);
  let impulse = relativeBefore * lock.velocityFactor / inverseTotal;
  impulse = Math.max(-lock.maxImpulse, Math.min(lock.maxImpulse, impulse));
  if (wa > 0) { a.velocity.x += lock.direction.x * impulse * wa; a.velocity.y += lock.direction.y * impulse * wa; }
  if (wb > 0) { b.velocity.x -= lock.direction.x * impulse * wb; b.velocity.y -= lock.direction.y * impulse * wb; }
  const relativeAfter = dot(relativeVector(a, b, 'velocity'), lock.direction);
  return { id: lock.id, enabled: true, solved: true, impulse: round(impulse), relativeSpeedBefore: round(relativeBefore), relativeSpeedAfter: round(relativeAfter) };
}

function solveIterations(world, normalized, positionIterations, velocityIterations) {
  const positionReceipts = []; const velocityReceipts = [];
  for (let iteration = 0; iteration < positionIterations; iteration++) normalized.forEach(lock => positionReceipts.push(Object.assign({ iteration: iteration + 1 }, solvePosition(world, lock))));
  for (let iteration = 0; iteration < velocityIterations; iteration++) normalized.forEach(lock => velocityReceipts.push(Object.assign({ iteration: iteration + 1 }, solveVelocity(world, lock))));
  world.bodies.forEach(item => { item.position.x = round(item.position.x); item.position.y = round(item.position.y); item.velocity.x = round(item.velocity.x); item.velocity.y = round(item.velocity.y); });
  return { positionReceipts, velocityReceipts };
}

function prepareWorld(world, locks, options) {
  const out = clone(world); const normalized = normalizeLocks(locks, out);
  const positionIterations = iterationCount(options && options.positionIterations, 8);
  const velocityIterations = iterationCount(options && options.velocityIterations, 4);
  const initial = normalized.map(lock => measureLock(out, lock));
  const receipts = solveIterations(out, normalized, positionIterations, velocityIterations);
  return { world: out, locks: normalized, positionIterations, velocityIterations, initial, afterPreSolve: normalized.map(lock => measureLock(out, lock)), positionReceipts: receipts.positionReceipts, velocityReceipts: receipts.velocityReceipts };
}

function refreshDiagnostics(world, coreDiagnostics, beforeCoreDiagnostics) {
  const refreshed = Core.measure(world, coreDiagnostics.substeps, coreDiagnostics.maxPenetration, coreDiagnostics.broadphasePairs, {
    overflowBodies: coreDiagnostics.broadphaseOverflowBodies, cellEntries: coreDiagnostics.broadphaseCellEntries,
    occupiedCells: coreDiagnostics.broadphaseOccupiedCells, warmStartedContacts: coreDiagnostics.warmStartedContacts,
    warmStartAppliedImpulse: coreDiagnostics.warmStartAppliedImpulse, warmStartCorrectionImpulse: coreDiagnostics.warmStartCorrectionImpulse,
    detectedUniqueContacts: coreDiagnostics.detectedUniqueContacts
  });
  refreshed.energyDelta = round(refreshed.totalEnergy - beforeCoreDiagnostics.totalEnergy);
  refreshed.directionLockPostStabilized = true;
  refreshed.contactEvidenceBasis = 'CORE_STAGE_BEFORE_POST_DIRECTION_LOCK_STABILIZATION';
  world.diagnostics = refreshed;
  return refreshed;
}

function step(world, locks, dt, options) {
  const validation = Core.validate(world); if (!validation.ok) throw new Error(validation.errors.join('; '));
  options = options || {};
  const prepared = prepareWorld(world, locks, options);
  const beforeCoreDiagnostics = Core.measure(prepared.world, 0, 0);
  const coreStep = Core.step(prepared.world, dt);
  const afterCore = prepared.locks.map(lock => measureLock(coreStep.world, lock));
  const postWorld = clone(coreStep.world);
  const postPositionIterations = iterationCount(options.postPositionIterations, 4);
  const postVelocityIterations = iterationCount(options.postVelocityIterations, 2);
  const postReceipts = solveIterations(postWorld, prepared.locks, postPositionIterations, postVelocityIterations);
  const after = prepared.locks.map(lock => measureLock(postWorld, lock));
  const maxErrorAfterCoreStep = afterCore.reduce((max, item) => Math.max(max, Math.abs(item.error)), 0);
  const maxErrorAfterStabilization = after.reduce((max, item) => Math.max(max, Math.abs(item.error)), 0);
  const finalDiagnostics = refreshDiagnostics(postWorld, coreStep.diagnostics, beforeCoreDiagnostics);
  return {
    schema: STEP_SCHEMA, ok: true, world: postWorld, locks: clone(prepared.locks),
    directionLockDiagnostics: {
      positionIterations: prepared.positionIterations, velocityIterations: prepared.velocityIterations,
      postPositionIterations, postVelocityIterations, maxErrorAfterCoreStep: round(maxErrorAfterCoreStep), maxErrorAfterStabilization: round(maxErrorAfterStabilization),
      initial: prepared.initial, afterPreSolve: prepared.afterPreSolve, afterCore, after,
      positionReceipts: prepared.positionReceipts, velocityReceipts: prepared.velocityReceipts,
      postPositionReceipts: postReceipts.positionReceipts, postVelocityReceipts: postReceipts.velocityReceipts,
      contactEvidenceBasis: finalDiagnostics.contactEvidenceBasis
    },
    core: { diagnostics: clone(coreStep.diagnostics), events: clone(coreStep.events), worldBeforePostDirectionLockStabilization: clone(coreStep.world) },
    evidence: [
      prepared.locks.length + ' fixed-direction translation lock(s) normalized in deterministic id order',
      prepared.positionIterations + ' bounded direction-position iteration(s) executed before the donor-core step',
      prepared.velocityIterations + ' bounded direction-velocity iteration(s) executed before the donor-core step',
      'AXM Physics Core v' + Core.VERSION + ' executed collision/integration without donor-source modification',
      postPositionIterations + ' bounded direction-position stabilization iteration(s) executed after the donor-core step',
      postVelocityIterations + ' bounded direction-velocity stabilization iteration(s) executed after the donor-core step',
      'Maximum direction-projection error changed from ' + round(maxErrorAfterCoreStep) + ' after core integration to ' + round(maxErrorAfterStabilization) + ' after stabilization',
      'Final state checksum ' + Core.checksum(postWorld)
    ],
    limitations: [
      'Direction locks constrain translation along one fixed world-space direction only; perpendicular translation intentionally remains free.',
      'The direction does not rotate with either body and does not represent a full prismatic/slider joint.',
      'No angular inertia, rotating anchors, angular limits or motors are implemented.',
      'Post-core projection can move bodies after collision/contact evidence was generated; returned core events and contact geometry describe the donor-core stage before post-direction-lock stabilization.',
      'Connected locked bodies can still collide unless caller collision filters suppress that pair or the separate component-isolation wrapper is used.',
      'This standalone step entrypoint performs its own donor-core integration; mixed-family callers that require exactly one donor-core step must use the shared composer/activity/isolation path rather than chaining standalone step wrappers.',
      'Shared composer, guarded activity and component-isolation integration are provided separately; component isolation is broader than the one-axis physical correction and remains caller-opt-in.',
      'This is game/prototype physics evidence, not scientific validation.'
    ]
  };
}

function simulate(world, locks, steps, dt, options) {
  let out = clone(world); const count = Math.max(1, Math.min(100000, Math.round(finite(steps, 1)))); let last = null;
  for (let index = 0; index < count; index++) { last = step(out, locks, dt, options || {}); out = last.world; }
  return { schema: SIMULATION_SCHEMA, ok: true, steps: count, world: out, locks: last ? last.locks : normalizeLocks(locks, out), directionLockDiagnostics: last ? last.directionLockDiagnostics : null, checksum: Core.checksum(out), evidence: (last ? last.evidence : []).concat([count + ' direction-lock step(s) completed']) };
}

function validate(world, locks) {
  const core = Core.validate(world); const errors = (core.errors || []).slice(); let normalized = [];
  if (core.ok) { try { normalized = normalizeLocks(locks, world); } catch (error) { errors.push(error.message); } }
  return { ok: errors.length === 0, errors, lockCount: normalized.length, warnings: [
    'Direction locks preserve one caller-selected fixed world-space translation projection while perpendicular translation remains intentionally unconstrained.',
    'This is not a rotating local-axis or full prismatic joint: there are no rotating anchors, angular limits or motors.',
    'The standalone step performs its own donor-core integration; shared composer/activity/isolation integration is available through the dedicated wrappers and must be used instead of chaining step wrappers when exactly one donor-core step is required.',
    'The donor physics source remains untouched.'
  ] };
}

module.exports = { VERSION, LOCK_SCHEMA, STEP_SCHEMA, SIMULATION_SCHEMA, MAX_LOCKS, MIN_DIRECTION_LENGTH, normalizeDirection, normalizeLock, normalizeLocks, measureLock, solvePosition, solveVelocity, prepareWorld, step, simulate, validate };
