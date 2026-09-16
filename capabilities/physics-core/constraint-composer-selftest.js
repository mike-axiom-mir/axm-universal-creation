'use strict';

const assert = require('assert');
const Core = require('./source/axm-physics-core.js');
const Composer = require('./uc-constraint-composer.js');

function add(world, body) {
  return Core.addBody(world, body).world;
}

function mixedWorld() {
  let world = Core.createWorld({ gravity: { x: 0, y: 10 }, bounds: false, sleep: { enabled: false } });
  world = add(world, { id: 'mount-root', type: 'static', position: { x: 0, y: 0 } });
  world = add(world, { id: 'mounted', type: 'dynamic', position: { x: 4, y: 3 }, mass: 1, linearDamping: 0 });
  world = add(world, { id: 'joint-root', type: 'static', position: { x: 5, y: 0 } });
  world = add(world, { id: 'bob', type: 'dynamic', position: { x: 9, y: 2 }, mass: 1, linearDamping: 0 });
  return world;
}

function settledWorld() {
  let world = Core.createWorld({ gravity: { x: 0, y: 0 }, bounds: false, sleep: { enabled: false } });
  world = add(world, { id: 'mount-root', type: 'static', position: { x: 0, y: 0 } });
  world = add(world, { id: 'mounted', type: 'dynamic', position: { x: 1, y: 0 }, mass: 1, linearDamping: 0 });
  world = add(world, { id: 'joint-root', type: 'static', position: { x: 5, y: 0 } });
  world = add(world, { id: 'bob', type: 'dynamic', position: { x: 7, y: 0 }, mass: 1, linearDamping: 0 });
  return world;
}

function conflictingWorld() {
  let world = Core.createWorld({ gravity: { x: 0, y: 0 }, bounds: false, sleep: { enabled: false } });
  world = add(world, { id: 'root', type: 'static', position: { x: 0, y: 0 } });
  world = add(world, { id: 'body', type: 'dynamic', position: { x: 1, y: 0 }, mass: 1, linearDamping: 0 });
  return world;
}

const constraints = {
  mounts: [{ id: 'payload-mount', a: 'mount-root', b: 'mounted', offset: { x: 1, y: 0 } }],
  distanceJoints: [{ id: 'tether', a: 'joint-root', b: 'bob', length: 2 }]
};

const validation = Composer.validate(mixedWorld(), constraints);
assert.equal(validation.ok, true);
assert.equal(validation.mountCount, 1);
assert.equal(validation.distanceJointCount, 1);
assert.deepEqual(Composer.FAMILY_ORDER, ['translation-mounts', 'distance-joints']);
assert.match(validation.warnings.join(' '), /early exit/i);

const stepped = Composer.step(mixedWorld(), constraints, 0.1);
assert.equal(stepped.world.stepIndex, 1, 'mixed constraints must share exactly one donor-core integration step');
assert.ok(stepped.composerDiagnostics.afterCore.maxMountError > 1e-4, 'gravity should create measurable mount drift during the shared core step');
assert.ok(stepped.composerDiagnostics.afterCore.maxDistanceError > 1e-4, 'gravity should create measurable distance drift during the shared core step');
assert.ok(stepped.composerDiagnostics.after.maxMountError < 1e-8, 'post composition must restore the fixed translation mount');
assert.ok(stepped.composerDiagnostics.after.maxDistanceError < 1e-8, 'post composition must restore the distance joint');
assert.ok(stepped.composerDiagnostics.after.maxMountRelativeSpeed <= Composer.DEFAULT_VELOCITY_TOLERANCE, 'mount velocity residual must be measured and stabilized');
assert.ok(stepped.composerDiagnostics.after.maxDistanceRelativeSpeed <= Composer.DEFAULT_VELOCITY_TOLERANCE, 'distance velocity residual must be measured and stabilized');
assert.equal(stepped.composerDiagnostics.contactEvidenceBasis, 'CORE_STAGE_BEFORE_POST_COMPOSITE_STABILIZATION');
assert.ok(stepped.core.worldBeforePostCompositeStabilization, 'core-stage world must remain separately inspectable');
assert.equal(stepped.world.diagnostics.checksum, Core.checksum(stepped.world), 'final diagnostics checksum must describe the final composed world');
assert.match(stepped.limitations.join(' '), /ordering bias/i);
assert.match(stepped.limitations.join(' '), /not a proof/i);
assert.match(stepped.limitations.join(' '), /not scientific validation/i);

const bounded = Composer.step(mixedWorld(), constraints, 0.1, {
  prePasses: 999,
  postPasses: 999,
  mountPositionIterations: 999,
  distancePositionIterations: 999,
  earlyExit: false
});
assert.equal(bounded.composerDiagnostics.preConfig.passes, Composer.MAX_FAMILY_PASSES, 'pre family passes must remain bounded');
assert.equal(bounded.composerDiagnostics.postConfig.passes, Composer.MAX_FAMILY_PASSES, 'post family passes must remain bounded');
assert.equal(bounded.composerDiagnostics.prePassesExecuted, Composer.MAX_FAMILY_PASSES, 'disabled early exit must execute the full bounded pre budget');
assert.equal(bounded.composerDiagnostics.postPassesExecuted, Composer.MAX_FAMILY_PASSES, 'disabled early exit must execute the full bounded post budget');
assert.equal(bounded.composerDiagnostics.preConfig.mounts.positionIterations, 32, 'nested mount iterations must retain their bounded solver limit');
assert.equal(bounded.composerDiagnostics.preConfig.distanceJoints.positionIterations, 32, 'nested distance iterations must retain their bounded solver limit');

const adaptive = Composer.step(settledWorld(), constraints, 0.01, {
  prePasses: Composer.MAX_FAMILY_PASSES,
  postPasses: Composer.MAX_FAMILY_PASSES
});
assert.equal(adaptive.composerDiagnostics.prePassesExecuted, 1, 'already-satisfied pre constraints should stop after one deterministic pass');
assert.equal(adaptive.composerDiagnostics.postPassesExecuted, 1, 'already-satisfied post constraints should stop after one deterministic pass');
assert.equal(adaptive.composerDiagnostics.totalPassesAvoided, 30, 'adaptive pass accounting must expose skipped bounded work');
assert.equal(adaptive.composerDiagnostics.earlyExitTriggered, true, 'adaptive pass savings must be explicit');
assert.ok(adaptive.composerDiagnostics.prePassSummaries[0].convergence.converged);
assert.ok(adaptive.composerDiagnostics.postPassSummaries[0].convergence.converged);

const exhaustive = Composer.step(settledWorld(), constraints, 0.01, {
  prePasses: Composer.MAX_FAMILY_PASSES,
  postPasses: Composer.MAX_FAMILY_PASSES,
  earlyExit: false
});
assert.equal(exhaustive.composerDiagnostics.prePassesExecuted, Composer.MAX_FAMILY_PASSES);
assert.equal(exhaustive.composerDiagnostics.postPassesExecuted, Composer.MAX_FAMILY_PASSES);
assert.equal(Core.checksum(adaptive.world), Core.checksum(exhaustive.world), 'early exit must preserve the settled final state versus exhaustive no-op passes');

const conflictingConstraints = {
  mounts: [{ id: 'fixed-one', a: 'root', b: 'body', offset: { x: 1, y: 0 } }],
  distanceJoints: [{ id: 'distance-two', a: 'root', b: 'body', length: 2 }]
};
const conflicting = Composer.step(conflictingWorld(), conflictingConstraints, 0.01, {
  prePasses: 4,
  postPasses: 4
});
assert.equal(conflicting.composerDiagnostics.prePassesExecuted, 4, 'conflicting constraints must consume the configured pre budget instead of falsely converging');
assert.equal(conflicting.composerDiagnostics.postPassesExecuted, 4, 'conflicting constraints must consume the configured post budget instead of falsely converging');
assert.equal(conflicting.composerDiagnostics.totalPassesAvoided, 0, 'unresolved residual error must prevent adaptive pass savings');
assert.equal(conflicting.composerDiagnostics.earlyExitTriggered, false);
assert.ok(conflicting.composerDiagnostics.after.maxMountError > Composer.DEFAULT_POSITION_TOLERANCE, 'conflicting residual must remain visible');

const simA = Composer.simulate(mixedWorld(), constraints, 30, 1 / 60);
const simB = Composer.simulate(mixedWorld(), constraints, 30, 1 / 60);
assert.equal(simA.checksum, simB.checksum, 'mixed constraint composition must replay deterministically in one JS runtime');
assert.equal(simA.world.stepIndex, 30, 'simulation must perform one donor-core integration per composed step');
assert.ok(simA.composerDiagnostics.after.maxMountError < 1e-8);
assert.ok(simA.composerDiagnostics.after.maxDistanceError < 1e-8);

const invalid = Composer.validate(mixedWorld(), {
  mounts: [{ id: 'bad', a: 'missing', b: 'mounted', offset: { x: 0, y: 0 } }],
  distanceJoints: []
});
assert.equal(invalid.ok, false);
assert.match(invalid.errors.join(' '), /body not found/i);

console.log('UC Constraint Composer selftest: PASS (single integration, mixed stabilization, convergence-aware pass savings, conflict truth, evidence boundary and deterministic replay)');
