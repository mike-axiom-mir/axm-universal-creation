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

function motionWorld() {
  let world = Core.createWorld({ gravity: { x: 0, y: 0 }, bounds: false, sleep: { enabled: false } });
  world = add(world, { id: 'root', type: 'static', shape: { kind: 'circle', radius: 0.1 }, position: { x: 0, y: 0 } });
  world = add(world, { id: 'payload', type: 'dynamic', shape: { kind: 'circle', radius: 0.1 }, position: { x: 0.5, y: 0 }, mass: 1, linearDamping: 0 });
  return world;
}

function overlapWorld() {
  let world = Core.createWorld({ gravity: { x: 0, y: 0 }, bounds: false, sleep: { enabled: false } });
  world = add(world, { id: 'root', type: 'static', shape: { kind: 'circle', radius: 1 }, position: { x: 0, y: 0 } });
  world = add(world, { id: 'payload', type: 'dynamic', shape: { kind: 'circle', radius: 1 }, position: { x: 0.5, y: 0 }, mass: 1, linearDamping: 0 });
  return world;
}

const activeAxisLimit = {
  mounts: [], distanceJoints: [], distanceLimits: [], axisLocks: [],
  axisLimits: [{ id: 'x-range', a: 'root', b: 'payload', axis: 'x', minOffset: 0, maxOffset: 1 }]
};

const validation = Composer.validate(motionWorld(), activeAxisLimit);
assert.equal(validation.ok, true);
assert.equal(validation.axisLimitCount, 1);
assert.equal(validation.directionLockCount, 0);
assert.deepEqual(Composer.FAMILY_ORDER, ['translation-mounts', 'distance-joints', 'distance-limits', 'axis-locks', 'axis-limits', 'direction-locks']);

let driven = motionWorld();
driven = Core.applyImpulse(driven, 'payload', { x: 10, y: 4 });
const composed = Composer.step(driven, activeAxisLimit, 0.1);
assert.equal(composed.world.stepIndex, 1, 'axis limit inside composer must share one donor-core integration');
assert.ok(composed.composerDiagnostics.afterCore.maxAxisLimitError > 0.4, 'core integration should visibly cross the configured max bound before post stabilization');
assert.ok(composed.composerDiagnostics.after.maxAxisLimitError < 1e-8, 'composed axis limit must restore its selected-axis bound');
assert.ok(composed.composerDiagnostics.after.maxAxisLimitRelativeSpeed < 1e-8, 'composed axis limit must stop outward relative speed at the active boundary');
assert.equal(composed.composerDiagnostics.after.maxDirectionLockError, 0);
assert.equal(composed.composerDiagnostics.after.axisLimits[0].state, 'AT_MAX');
assert.ok(composed.world.bodies.find(item => item.id === 'payload').position.y > 0.3, 'orthogonal translation must remain free inside the mixed composer');
assert.ok(composed.composerDiagnostics.postPassSummaries[0].axisLimitPositionReceiptCount > 0);
assert.ok(composed.composerDiagnostics.postPassSummaries[0].axisLimitVelocityReceiptCount > 0);

let slackWorld = motionWorld();
slackWorld = Core.applyImpulse(slackWorld, 'payload', { x: 0, y: 3 });
const slack = Composer.step(slackWorld, activeAxisLimit, 0.1);
assert.equal(slack.composerDiagnostics.after.axisLimits[0].state, 'SLACK', 'range interior must remain physically slack in the shared composer');
assert.ok(Math.abs(slack.world.bodies.find(item => item.id === 'payload').position.x - 0.5) < 1e-8, 'slack axis limit must not pin the allowed x offset');
assert.ok(slack.world.bodies.find(item => item.id === 'payload').position.y > 0.2, 'slack axis limit must not block orthogonal motion');

const baseline = Composer.step(overlapWorld(), activeAxisLimit, 0.01);
assert.equal(hasPairContact(baseline.core.worldBeforePostCompositeStabilization, 'root', 'payload'), true, 'without isolation an overlapping axis-limited pair still reaches donor contact detection');

const isolated = Isolation.step(overlapWorld(), activeAxisLimit, 0.01);
assert.equal(isolated.world.stepIndex, 1);
assert.equal(isolated.isolationDiagnostics.componentCount, 1, 'axis-limit edge must form an isolation component even while its range is slack');
assert.equal(isolated.isolationDiagnostics.appliedComponents, 1);
assert.equal(hasPairContact(isolated.core.worldAsIntegratedWithTemporaryGroups, 'root', 'payload'), false, 'axis-limit component must receive temporary self-collision suppression when requested');
assert.equal(isolated.constraints.axisLimits.length, 1);
assert.equal(isolated.composerDiagnostics.after.axisLimits[0].state, 'SLACK', 'topology participation must not rewrite slack physical semantics');

const disabledAxisLimit = {
  mounts: [], distanceJoints: [], distanceLimits: [], axisLocks: [],
  axisLimits: [{ id: 'disabled-x-range', a: 'root', b: 'payload', axis: 'x', minOffset: 0, maxOffset: 1, enabled: false }]
};
const disabled = Gate.step(overlapWorld(), disabledAxisLimit, 0.01, { isolateCollisions: true });
assert.equal(disabled.activityDiagnostics.activeCount, 0);
assert.equal(disabled.activityDiagnostics.disabledCount, 1);
assert.deepEqual(disabled.activityDiagnostics.disabledIds.axisLimits, ['disabled-x-range']);
assert.equal(disabled.isolationDiagnostics.componentCount, 0, 'disabled axis-limit edge must not enter isolation topology');
assert.equal(hasPairContact(disabled.core.worldAsIntegratedWithTemporaryGroups, 'root', 'payload'), true, 'disabled axis limit must not suppress ordinary donor contact');
assert.equal(disabled.composerDiagnostics.after.maxAxisLimitError, 0, 'disabled axis limit must not enter guarded convergence residuals');

const enabled = Gate.step(overlapWorld(), activeAxisLimit, 0.01, { isolateCollisions: true });
assert.equal(enabled.activityDiagnostics.activeCount, 1);
assert.deepEqual(enabled.activityDiagnostics.activeIds.axisLimits, ['x-range']);
assert.equal(enabled.isolationDiagnostics.componentCount, 1);
assert.equal(hasPairContact(enabled.core.worldAsIntegratedWithTemporaryGroups, 'root', 'payload'), false);

const replayA = Gate.step(motionWorld(), activeAxisLimit, 1 / 60, { isolateCollisions: true });
const replayB = Gate.step(motionWorld(), activeAxisLimit, 1 / 60, { isolateCollisions: true });
assert.equal(Core.checksum(replayA.world), Core.checksum(replayB.world), 'five-family guarded axis-limit path must replay deterministically in one JS runtime');
assert.match(enabled.limitations.join(' '), /not scientific validation/i);

console.log('UC Axis Limit Integration selftest: PASS (single-step composition, slack range semantics, five-family activity/isolation filtering, orthogonal freedom and deterministic replay under the extended composer order)');
