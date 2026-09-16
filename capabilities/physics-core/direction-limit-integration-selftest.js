'use strict';

const assert = require('assert');
const Core = require('./source/axm-physics-core.js');
const Composer = require('./uc-constraint-composer.js');
const Gate = require('./uc-constraint-activity-gate.js');
const Isolation = require('./uc-constraint-collision-isolation.js');

function add(world, spec) { return Core.addBody(world, spec).world; }
function body(world, id) { return world.bodies.find(item => item.id === id); }
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
function violatedWorld() {
  let world = Core.createWorld({ gravity: { x: 0, y: 0 }, bounds: false, sleep: { enabled: false } });
  world = add(world, { id: 'root', type: 'static', shape: { kind: 'circle', radius: 0.1 }, position: { x: 0, y: 0 } });
  world = add(world, { id: 'payload', type: 'dynamic', shape: { kind: 'circle', radius: 0.1 }, position: { x: 3, y: 0 }, velocity: { x: 2, y: 2 }, mass: 1, linearDamping: 0 });
  return world;
}

const diagonal = { x: 1, y: 1 };
const activeSlack = {
  directionLimits: [{ id: 'diagonal-range', a: 'root', b: 'payload', direction: diagonal, minOffset: -1, maxOffset: 1 }]
};
const disabled = {
  directionLimits: [{ id: 'disabled-diagonal-range', a: 'root', b: 'payload', direction: diagonal, minOffset: -1, maxOffset: 1, enabled: false }]
};

const validation = Gate.validate(overlapWorld(), disabled);
assert.equal(validation.ok, true);
assert.equal(validation.activeCount, 0);
assert.equal(validation.disabledCount, 1);
assert.ok(Gate.FAMILY_KEYS.includes('directionLimits'), 'activity gate must enumerate fixed-direction limits as a guarded family');
assert.match(validation.warnings.join(' '), /fixed-direction limits/i);

const disabledStep = Gate.step(overlapWorld(), disabled, 0.01, { isolateCollisions: true });
assert.equal(disabledStep.world.stepIndex, 1, 'disabled direction-limit path must still execute exactly one donor-core step');
assert.deepEqual(disabledStep.activityDiagnostics.disabledIds.directionLimits, ['disabled-diagonal-range']);
assert.equal(disabledStep.isolationDiagnostics.componentCount, 0, 'disabled direction limit must not create isolation topology');
assert.equal(disabledStep.composerDiagnostics.after.maxDirectionLimitError, 0, 'disabled direction-limit residual must not enter composer convergence');
assert.equal(hasPairContact(disabledStep.core.worldAsIntegratedWithTemporaryGroups, 'root', 'payload'), true, 'disabled direction limit must not suppress ordinary donor-core contact');

const isolated = Isolation.step(overlapWorld(), activeSlack, 0.01);
assert.equal(isolated.world.stepIndex, 1, 'isolated direction limit must share the composer donor-core step');
assert.equal(isolated.constraints.directionLimits.length, 1);
assert.equal(isolated.isolationDiagnostics.componentCount, 1, 'enabled direction-limit edge must form one component even while its range is slack');
assert.equal(isolated.isolationDiagnostics.appliedComponents, 1);
assert.equal(isolated.isolationDiagnostics.receipts[0].temporaryGroup, -1);
assert.equal(hasPairContact(isolated.core.worldAsIntegratedWithTemporaryGroups, 'root', 'payload'), false, 'direction-limit component must receive temporary collision suppression');
assert.equal(isolated.composerDiagnostics.after.directionLimits[0].state, 'SLACK');
assert.equal(isolated.composerDiagnostics.after.maxDirectionLimitError, 0);
assert.equal(body(isolated.world, 'root').collision.group, 0);
assert.equal(body(isolated.world, 'payload').collision.group, 0);
assert.match(isolated.limitations.join(' '), /direction-limit edges participate in component topology/i);

const guarded = Gate.step(overlapWorld(), activeSlack, 0.01, { isolateCollisions: true });
assert.equal(guarded.activityDiagnostics.activeCount, 1);
assert.deepEqual(guarded.activityDiagnostics.activeIds.directionLimits, ['diagonal-range']);
assert.equal(guarded.isolationDiagnostics.componentCount, 1);
assert.equal(hasPairContact(guarded.core.worldAsIntegratedWithTemporaryGroups, 'root', 'payload'), false);
assert.equal(guarded.activityDiagnostics.finalChecksum, Core.checksum(guarded.world));

const violated = {
  directionLimits: [{ id: 'max-diagonal', a: 'root', b: 'payload', direction: diagonal, maxOffset: 1 }]
};
const composed = Composer.step(violatedWorld(), violated, 1 / 60);
assert.equal(composed.world.stepIndex, 1, 'direction-limit composer integration must execute one donor-core step');
assert.equal(composed.constraints.directionLimits.length, 1);
assert.equal(composed.composerDiagnostics.familyOrder.at(-1), 'direction-limits');
assert.ok(composed.composerDiagnostics.initial.maxDirectionLimitError > 1, 'fixture must begin with a real projected-range violation');
assert.ok(composed.composerDiagnostics.after.maxDirectionLimitError < 1e-8, 'post-composer solve must repair the projected range violation');
assert.ok(composed.composerDiagnostics.after.maxDirectionLimitRelativeSpeed <= Composer.DEFAULT_VELOCITY_TOLERANCE, 'outward projected velocity must be stabilized at the active max boundary');
const initialPerpendicular = composed.composerDiagnostics.initial.directionLimits[0].perpendicularOffset;
const finalPerpendicular = composed.composerDiagnostics.after.directionLimits[0].perpendicularOffset;
assert.ok(Math.abs(finalPerpendicular - initialPerpendicular) < 1e-8, 'direction-limit correction must preserve perpendicular translation in the collision-free fixture');

const invalidDisabled = Gate.validate(overlapWorld(), {
  directionLimits: [{ id: 'bad-disabled', a: 'root', b: 'missing', direction: diagonal, maxOffset: 1, enabled: false }]
});
assert.equal(invalidDisabled.ok, false, 'disabled direction limits must still pass source/body-reference validation');
assert.match(invalidDisabled.errors.join(' '), /body not found/i);

const replayA = Gate.step(overlapWorld(), activeSlack, 1 / 60, { isolateCollisions: true });
const replayB = Gate.step(overlapWorld(), activeSlack, 1 / 60, { isolateCollisions: true });
assert.equal(Core.checksum(replayA.world), Core.checksum(replayB.world), 'guarded isolated direction-limit path must replay deterministically in one JS runtime');
assert.match(replayA.limitations.join(' '), /direction-limit range interiors remain slack/i);
assert.match(replayA.limitations.join(' '), /not scientific validation/i);

console.log('UC Direction Limit Integration selftest: PASS (seven-family composition, slack topology, activity filtering, component isolation, one-step delegation and deterministic replay)');
