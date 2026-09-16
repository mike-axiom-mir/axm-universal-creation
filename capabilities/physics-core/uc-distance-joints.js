'use strict';

const Core = require('./source/axm-physics-core.js');

const VERSION = '0.1.0';
const JOINT_SCHEMA = 'axm.uc-distance-joint/v0.1';
const STEP_SCHEMA = 'axm.uc-distance-joint-step/v0.1';
const MAX_JOINTS = 4096;

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

function normalizeAxis(delta) {
  const distance = Math.hypot(delta.x, delta.y);
  return distance > 1e-12
    ? { distance, x: delta.x / distance, y: delta.y / distance }
    : { distance: 0, x: 1, y: 0 };
}

function normalizeJoint(input, world, index) {
  input = input || {};
  const a = String(input.a || '').trim();
  const b = String(input.b || '').trim();
  if (!a || !b || a === b) throw new Error('distance joint requires distinct a and b body ids');
  const bodyA = body(world, a);
  const bodyB = body(world, b);
  if (!bodyA || !bodyB) throw new Error('distance joint body not found: ' + (!bodyA ? a : b));
  const current = Math.hypot(bodyB.position.x - bodyA.position.x, bodyB.position.y - bodyA.position.y);
  return {
    schema: JOINT_SCHEMA,
    id: String(input.id || ('distance-joint-' + String(index + 1).padStart(3, '0'))),
    a,
    b,
    length: bounded(input.length, 0, 1e9, current),
    positionFactor: bounded(input.positionFactor, 0, 1, 1),
    velocityFactor: bounded(input.velocityFactor, 0, 1, 1),
    slop: bounded(input.slop, 0, 1e6, 1e-6),
    maxCorrection: bounded(input.maxCorrection, 0, 1e9, 1e6),
    maxImpulse: bounded(input.maxImpulse, 0, 1e12, 1e9),
    enabled: input.enabled !== false,
    userData: clone(input.userData || {})
  };
}

function normalizeJoints(joints, world) {
  const list = Array.isArray(joints) ? joints : [];
  if (list.length > MAX_JOINTS) throw new Error('distance joint limit exceeded');
  const normalized = list.map((joint, index) => normalizeJoint(joint, world, index));
  const seen = new Set();
  normalized.forEach(joint => {
    if (seen.has(joint.id)) throw new Error('duplicate distance joint id ' + joint.id);
    seen.add(joint.id);
  });
  return normalized.sort((a, b) => a.id.localeCompare(b.id));
}

function measureJoint(world, joint) {
  const a = body(world, joint.a);
  const b = body(world, joint.b);
  if (!a || !b) throw new Error('distance joint body missing for ' + joint.id);
  const dx = b.position.x - a.position.x;
  const dy = b.position.y - a.position.y;
  const distance = Math.hypot(dx, dy);
  return {
    id: joint.id,
    a: joint.a,
    b: joint.b,
    targetLength: joint.length,
    distance: round(distance),
    error: round(distance - joint.length)
  };
}

function solvePosition(world, joint) {
  if (!joint.enabled) return { id: joint.id, enabled: false, solved: false, correction: 0, errorBefore: 0, errorAfter: 0 };
  const a = body(world, joint.a);
  const b = body(world, joint.b);
  if (!a || !b) throw new Error('distance joint body missing for ' + joint.id);
  const wa = inverseMass(a);
  const wb = inverseMass(b);
  const inverseTotal = wa + wb;
  const delta = { x: b.position.x - a.position.x, y: b.position.y - a.position.y };
  const axis = normalizeAxis(delta);
  const errorBefore = axis.distance - joint.length;
  if (!(inverseTotal > 0)) {
    return { id: joint.id, enabled: true, solved: false, reason: 'NO_DYNAMIC_MASS', correction: 0, errorBefore: round(errorBefore), errorAfter: round(errorBefore) };
  }
  if (Math.abs(errorBefore) <= joint.slop) {
    return { id: joint.id, enabled: true, solved: true, correction: 0, errorBefore: round(errorBefore), errorAfter: round(errorBefore) };
  }
  wake(a);
  wake(b);
  const signedCorrection = Math.max(-joint.maxCorrection, Math.min(joint.maxCorrection, errorBefore * joint.positionFactor));
  const lambda = signedCorrection / inverseTotal;
  if (wa > 0) {
    a.position.x += axis.x * lambda * wa;
    a.position.y += axis.y * lambda * wa;
  }
  if (wb > 0) {
    b.position.x -= axis.x * lambda * wb;
    b.position.y -= axis.y * lambda * wb;
  }
  const after = Math.hypot(b.position.x - a.position.x, b.position.y - a.position.y) - joint.length;
  return {
    id: joint.id,
    enabled: true,
    solved: true,
    correction: round(signedCorrection),
    errorBefore: round(errorBefore),
    errorAfter: round(after)
  };
}

function solveVelocity(world, joint) {
  if (!joint.enabled) return { id: joint.id, enabled: false, solved: false, impulse: 0, relativeSpeedBefore: 0, relativeSpeedAfter: 0 };
  const a = body(world, joint.a);
  const b = body(world, joint.b);
  if (!a || !b) throw new Error('distance joint body missing for ' + joint.id);
  const wa = inverseMass(a);
  const wb = inverseMass(b);
  const inverseTotal = wa + wb;
  if (!(inverseTotal > 0)) return { id: joint.id, enabled: true, solved: false, reason: 'NO_DYNAMIC_MASS', impulse: 0, relativeSpeedBefore: 0, relativeSpeedAfter: 0 };
  const axis = normalizeAxis({ x: b.position.x - a.position.x, y: b.position.y - a.position.y });
  const relativeBefore = (b.velocity.x - a.velocity.x) * axis.x + (b.velocity.y - a.velocity.y) * axis.y;
  if (Math.abs(relativeBefore) <= 1e-12) {
    return { id: joint.id, enabled: true, solved: true, impulse: 0, relativeSpeedBefore: round(relativeBefore), relativeSpeedAfter: round(relativeBefore) };
  }
  wake(a);
  wake(b);
  let impulse = relativeBefore * joint.velocityFactor / inverseTotal;
  impulse = Math.max(-joint.maxImpulse, Math.min(joint.maxImpulse, impulse));
  if (wa > 0) {
    a.velocity.x += axis.x * impulse * wa;
    a.velocity.y += axis.y * impulse * wa;
  }
  if (wb > 0) {
    b.velocity.x -= axis.x * impulse * wb;
    b.velocity.y -= axis.y * impulse * wb;
  }
  const relativeAfter = (b.velocity.x - a.velocity.x) * axis.x + (b.velocity.y - a.velocity.y) * axis.y;
  return {
    id: joint.id,
    enabled: true,
    solved: true,
    impulse: round(impulse),
    relativeSpeedBefore: round(relativeBefore),
    relativeSpeedAfter: round(relativeAfter)
  };
}

function prepareWorld(world, joints, options) {
  const out = clone(world);
  const normalized = normalizeJoints(joints, out);
  const positionIterations = Math.round(bounded(options && options.positionIterations, 1, 32, 8));
  const velocityIterations = Math.round(bounded(options && options.velocityIterations, 1, 32, 4));
  const positionReceipts = [];
  const velocityReceipts = [];
  for (let iteration = 0; iteration < positionIterations; iteration++) {
    normalized.forEach(joint => positionReceipts.push(Object.assign({ iteration: iteration + 1 }, solvePosition(out, joint))));
  }
  for (let iteration = 0; iteration < velocityIterations; iteration++) {
    normalized.forEach(joint => velocityReceipts.push(Object.assign({ iteration: iteration + 1 }, solveVelocity(out, joint))));
  }
  out.bodies.forEach(item => {
    item.position.x = round(item.position.x);
    item.position.y = round(item.position.y);
    item.velocity.x = round(item.velocity.x);
    item.velocity.y = round(item.velocity.y);
  });
  return { world: out, joints: normalized, positionIterations, velocityIterations, positionReceipts, velocityReceipts };
}

function step(world, joints, dt, options) {
  const validation = Core.validate(world);
  if (!validation.ok) throw new Error(validation.errors.join('; '));
  const prepared = prepareWorld(world, joints, options || {});
  const before = prepared.joints.map(joint => measureJoint(prepared.world, joint));
  const coreStep = Core.step(prepared.world, dt);
  const after = prepared.joints.map(joint => measureJoint(coreStep.world, joint));
  const maxError = after.reduce((max, item) => Math.max(max, Math.abs(item.error)), 0);
  return {
    schema: STEP_SCHEMA,
    ok: true,
    world: coreStep.world,
    joints: clone(prepared.joints),
    jointDiagnostics: {
      positionIterations: prepared.positionIterations,
      velocityIterations: prepared.velocityIterations,
      maxErrorAfterCoreStep: round(maxError),
      before,
      after,
      positionReceipts: prepared.positionReceipts,
      velocityReceipts: prepared.velocityReceipts
    },
    core: {
      diagnostics: clone(coreStep.diagnostics),
      events: clone(coreStep.events)
    },
    evidence: [
      prepared.joints.length + ' translation-only distance joint(s) normalized in deterministic id order',
      prepared.positionIterations + ' projected position iteration(s) executed before the core step',
      prepared.velocityIterations + ' relative-axis velocity iteration(s) executed before the core step',
      'AXM Physics Core v' + Core.VERSION + ' executed collisions and integration from the constrained start state',
      'Post-core maximum distance error ' + round(maxError),
      'State checksum ' + Core.checksum(coreStep.world)
    ],
    limitations: [
      'Distance joints constrain body centers only; local anchors and angular response are not implemented.',
      'Joint projection occurs before the imported core collision/integration step, so external forces can create bounded distance error until the next joint solve.',
      'Connected-body collision suppression is not implemented.',
      'This is game/prototype physics evidence, not scientific validation.'
    ]
  };
}

function simulate(world, joints, steps, dt, options) {
  let out = clone(world);
  const count = Math.max(1, Math.min(100000, Math.round(finite(steps, 1))));
  let last = null;
  for (let index = 0; index < count; index++) {
    last = step(out, joints, dt, options);
    out = last.world;
  }
  return {
    schema: 'axm.uc-distance-joint-simulation/v0.1',
    ok: true,
    steps: count,
    world: out,
    joints: last ? last.joints : normalizeJoints(joints, out),
    jointDiagnostics: last ? last.jointDiagnostics : null,
    checksum: Core.checksum(out),
    evidence: (last ? last.evidence : []).concat([count + ' distance-joint step(s) completed'])
  };
}

function validate(world, joints) {
  const core = Core.validate(world);
  const errors = (core.errors || []).slice();
  let normalized = [];
  if (core.ok) {
    try { normalized = normalizeJoints(joints, world); }
    catch (error) { errors.push(error.message); }
  }
  return {
    ok: errors.length === 0,
    errors,
    jointCount: normalized.length,
    warnings: [
      'This solver provides translation-only center-to-center distance constraints, not angular or anchored rigid joints.',
      'Constraint projection is intentionally layered around the imported v0.3.1 core instead of silently rewriting donor source.'
    ]
  };
}

module.exports = {
  VERSION,
  JOINT_SCHEMA,
  STEP_SCHEMA,
  MAX_JOINTS,
  normalizeJoint,
  normalizeJoints,
  measureJoint,
  prepareWorld,
  step,
  simulate,
  validate
};
