'use strict';

const assert = require('assert');
const Core = require('./source/axm-physics-core.js');
const Composer = require('./uc-constraint-composer.js');
const Isolation = require('./uc-constraint-collision-isolation.js');
const Gate = require('./uc-constraint-activity-gate.js');

function add(world, spec) { return Core.addBody(world, spec).world; }
function hasPairContact(world, a, b) {
  return (world.contacts || []).some(contact =>
    (contact.a === a && contact.b === b) || (contact.a === b && contact.b === a)
  );
}

function overlapWorld() {
  let world = Core.createWorld({ gravity: { x: 0, y: 0 }, bounds: false, sleep: { enabled: false } });
  world = add(world, { id: 'root', type: 'static', shape: { kind: 'circle', radius: 1 }, position: { x: 0, y: 0 } });
  world = add(world, { id: 'payload', type: 'dynamic', shape: { kind: 'circle', radius: 1 }, position: { x: 0.5, y: 0 }, mass: 1, linearDamping: 0 });
  return world;
}

const activeAxis = {
  mounts: [], distanceJoints: [], distanceLimits: [], axisLimits: [],
  axisLocks: [{ id: 'x-lock', a: 'root', b: 'payload', axis: 'x', offset: 0.5 }]
};

const composerValidation = Composer.validate(overlapWorld(), activeAxis);
assert.equal(composerValidation.ok, true);
assert.equal(composerValidation.axisLockCount, 1);
assert.equal(composerValidation.axisLimitCount, 0);
assert.deepEqual(Composer.FAMILY_ORDER, ['translation-mounts', 'distance-joints', 'distance-limits', 'axis-locks', 'axis-limits']);

let freeWorld = overlapWorld();
freeWorld = Core.applyImpulse(freeWorld, 'payload', { x: 3, y: 4 });
const composed = Composer.step(freeWorld, activeAxis, 0.1);
assert.equal(composed.world.stepIndex, 1, 'axis lock inside composer must share one donor-core integration');
assert.ok(composed.composerDiagnostics.after.maxAxisLockError < 1e-8, 'composed axis lock must stabilize its selected axis');
assert.ok(composed.composerDiagnostics.after.maxAxisLockRelativeSpeed < 1e-8, 'composed axis lock must stabilize selected-axis relative velocity');
assert.equal(composed.composerDiagnostics.after.maxAxisLimitError, 0);
assert.ok(composed.world.bodies.find(item => item.id === 'payload').position.y > 0.3, 'orthogonal translation must remain free inside the mixed composer');

const baseline = Composer.step(overlapWorld(), activeAxis, 0.01);
assert.equal(hasPairContact(baseline.core.worldBeforePostCompositeStabilization, 'root', 'payload'), true, 'without isolation an overlapping axis-locked pair still reaches donor contact detection');

const isolated = Isolation.step(overlapWorld(), activeAxis, 0.01);
assert.equal(isolated.world.stepIndex, 1);
assert.equal(isolated.isolationDiagnostics.componentCount, 1, 'axis-lock edge must form an isolation component');
assert.equal(isolated.isolationDiagnostics.appliedComponents, 1);
assert.equal(hasPairContact(isolated.core.worldAsIntegratedWithTemporaryGroups, 'root', 'payload'), false, 'axis-lock component must receive temporary self-collision suppression when requested');
assert.equal(isolated.constraints.axisLocks.length, 1);

const disabledAxis = {
  mounts: [], distanceJoints: [], distanceLimits: [], axisLimits: [],
  axisLocks: [{ id: 'disabled-x-lock', a: 'root', b: 'payload', axis: 'x', offset: 0.5, enabled: false }]
};
const disabled = Gate.step(overlapWorld(), disabledAxis, 0.01, { isolateCollisions: true });
assert.equal(disabled.activityDiagnostics.activeCount, 0);
assert.equal(disabled.activityDiagnostics.disabledCount, 1);
assert.deepEqual(disabled.activityDiagnostics.disabledIds.axisLocks, ['disabled-x-lock']);
assert.equal(disabled.isolationDiagnostics.componentCount, 0, 'disabled axis-lock edge must not enter isolation topology');
assert.equal(hasPairContact(disabled.core.worldAsIntegratedWithTemporaryGroups, 'root', 'payload'), true, 'disabled axis lock must not suppress ordinary donor contact');
assert.equal(disabled.composerDiagnostics.after.maxAxisLockError, 0, 'disabled axis lock must not enter guarded convergence residuals');

const enabled = Gate.step(overlapWorld(), activeAxis, 0.01, { isolateCollisions: true });
assert.equal(enabled.activityDiagnostics.activeCount, 1);
assert.deepEqual(enabled.activityDiagnostics.activeIds.axisLocks, ['x-lock']);
assert.equal(enabled.isolationDiagnostics.componentCount, 1);
assert.equal(hasPairContact(enabled.core.worldAsIntegratedWithTemporaryGroups, 'root', 'payload'), false);

const replayA = Gate.step(overlapWorld(), activeAxis, 1 / 60, { isolateCollisions: true });
const replayB = Gate.step(overlapWorld(), activeAxis, 1 / 60, { isolateCollisions: true });
assert.equal(Core.checksum(replayA.world), Core.checksum(replayB.world), 'five-family-capable guarded axis-lock path must replay deterministically in one JS runtime');
assert.match(enabled.limitations.join(' '), /not scientific validation/i);

console.log('UC Axis Lock Integration selftest: PASS (single-step composition, activity filtering, component isolation, orthogonal freedom and deterministic replay under five-family order)');
