'use strict';

const assert = require('assert');
const Core = require('./source/axm-physics-core.js');
const Gate = require('./uc-constraint-activity-gate.js');
const Isolation = require('./uc-constraint-collision-isolation.js');

function add(world, spec) { return Core.addBody(world, spec).world; }
function overlapWorld() {
  let world = Core.createWorld({ gravity: { x: 0, y: 0 }, bounds: false, sleep: { enabled: false } });
  world = add(world, { id: 'root', type: 'static', shape: { kind: 'circle', radius: 1 }, position: { x: 0, y: 0 } });
  world = add(world, { id: 'payload', type: 'dynamic', shape: { kind: 'circle', radius: 1 }, position: { x: 0.5, y: 0 }, mass: 1, linearDamping: 0 });
  return world;
}
function hasPairContact(world, a, b) {
  return (world.contacts || []).some(contact =>
    (contact.a === a && contact.b === b) || (contact.a === b && contact.b === a)
  );
}

const satisfiedOffset = 0.5 / Math.SQRT2;
const active = {
  directionLocks: [{ id: 'diagonal', a: 'root', b: 'payload', direction: { x: 1, y: 1 }, offset: satisfiedOffset }]
};
const disabled = {
  directionLocks: [{ id: 'disabled-diagonal', a: 'root', b: 'payload', direction: { x: 1, y: 1 }, offset: 99, enabled: false }]
};

const validation = Gate.validate(overlapWorld(), disabled);
assert.equal(validation.ok, true);
assert.equal(validation.activeCount, 0);
assert.equal(validation.disabledCount, 1);
assert.ok(Gate.FAMILY_KEYS.includes('directionLocks'), 'activity gate must enumerate fixed-direction locks as a guarded family');
assert.match(validation.warnings.join(' '), /fixed-direction locks/i);

const disabledStep = Gate.step(overlapWorld(), disabled, 0.01, { isolateCollisions: true });
assert.equal(disabledStep.world.stepIndex, 1, 'disabled direction lock path must still execute exactly one donor-core step');
assert.deepEqual(disabledStep.activityDiagnostics.disabledIds.directionLocks, ['disabled-diagonal']);
assert.equal(disabledStep.isolationDiagnostics.componentCount, 0, 'disabled direction lock must not create isolation topology');
assert.equal(disabledStep.composerDiagnostics.after.maxDirectionLockError, 0, 'disabled direction lock residual must not enter composer convergence');
assert.equal(hasPairContact(disabledStep.core.worldAsIntegratedWithTemporaryGroups, 'root', 'payload'), true, 'disabled direction lock must not suppress ordinary donor-core contact');

const isolated = Isolation.step(overlapWorld(), active, 0.01);
assert.equal(isolated.world.stepIndex, 1, 'isolated direction lock must share the composer donor-core step');
assert.equal(isolated.constraints.directionLocks.length, 1);
assert.equal(isolated.isolationDiagnostics.componentCount, 1, 'enabled direction-lock edge must form one component');
assert.equal(isolated.isolationDiagnostics.appliedComponents, 1);
assert.equal(isolated.isolationDiagnostics.receipts[0].temporaryGroup, -1);
assert.equal(hasPairContact(isolated.core.worldAsIntegratedWithTemporaryGroups, 'root', 'payload'), false, 'direction-lock component must receive temporary collision suppression');
assert.ok(isolated.composerDiagnostics.after.maxDirectionLockError < 1e-8, 'direction-lock projection must remain stabilized through isolated composition');
assert.equal(isolated.world.bodies.find(item => item.id === 'root').collision.group, 0);
assert.equal(isolated.world.bodies.find(item => item.id === 'payload').collision.group, 0);
assert.match(isolated.limitations.join(' '), /direction-lock edges participate in component topology/i);

const guarded = Gate.step(overlapWorld(), active, 0.01, { isolateCollisions: true });
assert.equal(guarded.activityDiagnostics.activeCount, 1);
assert.deepEqual(guarded.activityDiagnostics.activeIds.directionLocks, ['diagonal']);
assert.equal(guarded.isolationDiagnostics.componentCount, 1);
assert.equal(hasPairContact(guarded.core.worldAsIntegratedWithTemporaryGroups, 'root', 'payload'), false);
assert.equal(guarded.activityDiagnostics.finalChecksum, Core.checksum(guarded.world));

const invalidDisabled = Gate.validate(overlapWorld(), {
  directionLocks: [{ id: 'bad-disabled', a: 'root', b: 'missing', direction: { x: 1, y: 1 }, enabled: false }]
});
assert.equal(invalidDisabled.ok, false, 'disabled direction locks must still pass source/body-reference validation');
assert.match(invalidDisabled.errors.join(' '), /body not found/i);

const replayA = Gate.step(overlapWorld(), active, 1 / 60, { isolateCollisions: true });
const replayB = Gate.step(overlapWorld(), active, 1 / 60, { isolateCollisions: true });
assert.equal(Core.checksum(replayA.world), Core.checksum(replayB.world), 'guarded isolated direction-lock path must replay deterministically in one JS runtime');
assert.match(replayA.limitations.join(' '), /fixed-direction locks remain fixed in world space/i);
assert.match(replayA.limitations.join(' '), /not scientific validation/i);

console.log('UC Direction Lock Integration selftest: PASS (activity filtering, component isolation, one-step composition, group restoration and deterministic replay)');
