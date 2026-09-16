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

const constraints = {
  mounts: [{ id: 'payload-mount', a: 'mount-root', b: 'mounted', offset: { x: 1, y: 0 } }],
  distanceJoints: [{ id: 'tether', a: 'joint-root', b: 'bob', length: 2 }]
};

const validation = Composer.validate(mixedWorld(), constraints);
assert.equal(validation.ok, true);
assert.equal(validation.mountCount, 1);
assert.equal(validation.distanceJointCount, 1);
assert.deepEqual(Composer.FAMILY_ORDER, ['translation-mounts', 'distance-joints']);

const stepped = Composer.step(mixedWorld(), constraints, 0.1);
assert.equal(stepped.world.stepIndex, 1, 'mixed constraints must share exactly one donor-core integration step');
assert.ok(stepped.composerDiagnostics.afterCore.maxMountError > 1e-4, 'gravity should create measurable mount drift during the shared core step');
assert.ok(stepped.composerDiagnostics.afterCore.maxDistanceError > 1e-4, 'gravity should create measurable distance drift during the shared core step');
assert.ok(stepped.composerDiagnostics.after.maxMountError < 1e-8, 'post composition must restore the fixed translation mount');
assert.ok(stepped.composerDiagnostics.after.maxDistanceError < 1e-8, 'post composition must restore the distance joint');
assert.equal(stepped.composerDiagnostics.contactEvidenceBasis, 'CORE_STAGE_BEFORE_POST_COMPOSITE_STABILIZATION');
assert.ok(stepped.core.worldBeforePostCompositeStabilization, 'core-stage world must remain separately inspectable');
assert.equal(stepped.world.diagnostics.checksum, Core.checksum(stepped.world), 'final diagnostics checksum must describe the final composed world');
assert.match(stepped.limitations.join(' '), /ordering bias/i);
assert.match(stepped.limitations.join(' '), /not scientific validation/i);

const bounded = Composer.step(mixedWorld(), constraints, 0.1, {
  prePasses: 999,
  postPasses: 999,
  mountPositionIterations: 999,
  distancePositionIterations: 999
});
assert.equal(bounded.composerDiagnostics.preConfig.passes, Composer.MAX_FAMILY_PASSES, 'pre family passes must remain bounded');
assert.equal(bounded.composerDiagnostics.postConfig.passes, Composer.MAX_FAMILY_PASSES, 'post family passes must remain bounded');
assert.equal(bounded.composerDiagnostics.preConfig.mounts.positionIterations, 32, 'nested mount iterations must retain their bounded solver limit');
assert.equal(bounded.composerDiagnostics.preConfig.distanceJoints.positionIterations, 32, 'nested distance iterations must retain their bounded solver limit');

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

console.log('UC Constraint Composer selftest: PASS (single integration, mixed-family stabilization, bounded passes, evidence boundary and deterministic replay)');
