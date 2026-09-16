'use strict';

const assert = require('assert');
const Core = require('./source/axm-physics-core.js');
const Composer = require('./uc-constraint-composer.js');

function add(world, body) { return Core.addBody(world, body).world; }

function mixedWorld() {
  let world = Core.createWorld({ gravity: { x: 0, y: 10 }, bounds: false, sleep: { enabled: false } });
  world = add(world, { id: 'mount-root', type: 'static', position: { x: 0, y: 0 } });
  world = add(world, { id: 'mounted', type: 'dynamic', position: { x: 4, y: 3 }, mass: 1, linearDamping: 0 });
  world = add(world, { id: 'joint-root', type: 'static', position: { x: 5, y: 0 } });
  world = add(world, { id: 'bob', type: 'dynamic', position: { x: 9, y: 2 }, mass: 1, linearDamping: 0 });
  world = add(world, { id: 'limit-root', type: 'static', position: { x: 10, y: 0 } });
  world = add(world, { id: 'limited', type: 'dynamic', position: { x: 12, y: 0 }, mass: 1, linearDamping: 0 });
  world = add(world, { id: 'axis-root', type: 'static', position: { x: 15, y: 0 } });
  world = add(world, { id: 'slider', type: 'dynamic', position: { x: 16, y: 0 }, mass: 1, linearDamping: 0 });
  world = Core.applyImpulse(world, 'slider', { x: 2, y: 0 });
  return world;
}

function settledWorld() {
  let world = Core.createWorld({ gravity: { x: 0, y: 0 }, bounds: false, sleep: { enabled: false } });
  world = add(world, { id: 'mount-root', type: 'static', position: { x: 0, y: 0 } });
  world = add(world, { id: 'mounted', type: 'dynamic', position: { x: 1, y: 0 }, mass: 1, linearDamping: 0 });
  world = add(world, { id: 'joint-root', type: 'static', position: { x: 5, y: 0 } });
  world = add(world, { id: 'bob', type: 'dynamic', position: { x: 7, y: 0 }, mass: 1, linearDamping: 0 });
  world = add(world, { id: 'limit-root', type: 'static', position: { x: 10, y: 0 } });
  world = add(world, { id: 'limited', type: 'dynamic', position: { x: 11, y: 0 }, mass: 1, linearDamping: 0 });
  world = add(world, { id: 'axis-root', type: 'static', position: { x: 15, y: 0 } });
  world = add(world, { id: 'slider', type: 'dynamic', position: { x: 16, y: 0 }, mass: 1, linearDamping: 0 });
  return world;
}

const constraints = {
  mounts: [{ id: 'payload-mount', a: 'mount-root', b: 'mounted', offset: { x: 1, y: 0 } }],
  distanceJoints: [{ id: 'tether', a: 'joint-root', b: 'bob', length: 2 }],
  distanceLimits: [{ id: 'range-tether', a: 'limit-root', b: 'limited', maxLength: 2 }],
  axisLocks: [{ id: 'vertical-lock', a: 'axis-root', b: 'slider', axis: 'y', offset: 0 }],
  axisLimits: []
};

const validation = Composer.validate(mixedWorld(), constraints);
assert.equal(validation.ok, true);
assert.equal(validation.mountCount, 1);
assert.equal(validation.distanceJointCount, 1);
assert.equal(validation.distanceLimitCount, 1);
assert.equal(validation.axisLockCount, 1);
assert.equal(validation.axisLimitCount, 0);
assert.deepEqual(Composer.FAMILY_ORDER, ['translation-mounts', 'distance-joints', 'distance-limits', 'axis-locks', 'axis-limits']);
assert.match(validation.warnings.join(' '), /not full prismatic joints/i);

const stepped = Composer.step(mixedWorld(), constraints, 0.1);
assert.equal(stepped.world.stepIndex, 1, 'all active constraint families must share exactly one donor-core integration step');
assert.ok(stepped.composerDiagnostics.afterCore.maxMountError > 1e-4);
assert.ok(stepped.composerDiagnostics.afterCore.maxDistanceError > 1e-4);
assert.ok(stepped.composerDiagnostics.afterCore.maxDistanceLimitError > 1e-4);
assert.ok(stepped.composerDiagnostics.afterCore.maxAxisLockError > 1e-4, 'gravity should create measurable locked-y drift during the shared core step');
assert.equal(stepped.composerDiagnostics.afterCore.maxAxisLimitError, 0);
assert.ok(stepped.composerDiagnostics.after.maxMountError < 1e-8);
assert.ok(stepped.composerDiagnostics.after.maxDistanceError < 1e-8);
assert.ok(stepped.composerDiagnostics.after.maxDistanceLimitError < 1e-8);
assert.ok(stepped.composerDiagnostics.after.maxAxisLockError < 1e-8);
assert.equal(stepped.composerDiagnostics.after.maxAxisLimitError, 0);
assert.ok(stepped.composerDiagnostics.after.maxAxisLockRelativeSpeed <= Composer.DEFAULT_VELOCITY_TOLERANCE);
const slider = stepped.world.bodies.find(item => item.id === 'slider');
assert.ok(slider.position.x > 16.1, 'axis-lock integration must leave orthogonal x translation free');
assert.equal(stepped.composerDiagnostics.contactEvidenceBasis, 'CORE_STAGE_BEFORE_POST_COMPOSITE_STABILIZATION');
assert.equal(stepped.world.diagnostics.checksum, Core.checksum(stepped.world));
assert.match(stepped.limitations.join(' '), /ordering bias/i);
assert.match(stepped.limitations.join(' '), /not a full slider\/prismatic joint/i);
assert.match(stepped.limitations.join(' '), /not scientific validation/i);

const bounded = Composer.step(mixedWorld(), constraints, 0.1, {
  prePasses: 999, postPasses: 999, mountPositionIterations: 999, distancePositionIterations: 999,
  limitPositionIterations: 999, axisLockPositionIterations: 999, axisLimitPositionIterations: 999, earlyExit: false
});
assert.equal(bounded.composerDiagnostics.preConfig.passes, Composer.MAX_FAMILY_PASSES);
assert.equal(bounded.composerDiagnostics.postConfig.passes, Composer.MAX_FAMILY_PASSES);
assert.equal(bounded.composerDiagnostics.preConfig.axisLocks.positionIterations, 32, 'nested axis-lock iterations must retain the bounded solver limit');
assert.equal(bounded.composerDiagnostics.preConfig.axisLimits.positionIterations, 32, 'nested axis-limit iterations must retain the bounded solver limit');

const adaptive = Composer.step(settledWorld(), constraints, 0.01, {
  prePasses: Composer.MAX_FAMILY_PASSES,
  postPasses: Composer.MAX_FAMILY_PASSES
});
assert.equal(adaptive.composerDiagnostics.prePassesExecuted, 1);
assert.equal(adaptive.composerDiagnostics.postPassesExecuted, 1);
assert.equal(adaptive.composerDiagnostics.totalPassesAvoided, 30);
assert.equal(adaptive.composerDiagnostics.earlyExitTriggered, true);

const simA = Composer.simulate(mixedWorld(), constraints, 30, 1 / 60);
const simB = Composer.simulate(mixedWorld(), constraints, 30, 1 / 60);
assert.equal(simA.checksum, simB.checksum, 'five-family-capable composition must replay deterministically in one JS runtime');
assert.equal(simA.world.stepIndex, 30);
assert.ok(simA.composerDiagnostics.after.maxAxisLockError < 1e-8);
assert.equal(simA.composerDiagnostics.after.maxAxisLimitError, 0);

const invalid = Composer.validate(mixedWorld(), {
  mounts: [], distanceJoints: [], distanceLimits: [], axisLimits: [],
  axisLocks: [{ id: 'bad-axis', a: 'missing', b: 'slider', axis: 'x', offset: 0 }]
});
assert.equal(invalid.ok, false);
assert.match(invalid.errors.join(' '), /body not found/i);

console.log('UC Constraint Composer selftest: PASS (single integration, five-family contract, axis orthogonal freedom, bounded convergence and deterministic replay)');
