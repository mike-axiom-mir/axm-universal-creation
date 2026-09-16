'use strict';

const assert = require('assert');
const Core = require('./source/axm-physics-core.js');
const Gate = require('./uc-constraint-activity-gate.js');

function add(world, spec) {
  return Core.addBody(world, spec).world;
}

function overlapWorld() {
  let world = Core.createWorld({ gravity: { x: 0, y: 0 }, bounds: false, sleep: { enabled: false } });
  world = add(world, {
    id: 'root',
    type: 'static',
    shape: { kind: 'circle', radius: 1 },
    position: { x: 0, y: 0 }
  });
  world = add(world, {
    id: 'payload',
    type: 'dynamic',
    shape: { kind: 'circle', radius: 1 },
    position: { x: 0.5, y: 0 },
    mass: 1,
    linearDamping: 0
  });
  return world;
}

function separatedWorld() {
  let world = Core.createWorld({ gravity: { x: 0, y: 0 }, bounds: false, sleep: { enabled: false } });
  world = add(world, { id: 'root', type: 'static', position: { x: 0, y: 0 } });
  world = add(world, {
    id: 'payload',
    type: 'dynamic',
    position: { x: 3, y: 0 },
    mass: 1,
    linearDamping: 0
  });
  return world;
}

function hasPairContact(world, a, b) {
  return (world.contacts || []).some(contact =>
    (contact.a === a && contact.b === b) || (contact.a === b && contact.b === a)
  );
}

const disabledConstraints = {
  mounts: [{ id: 'disabled-mount', a: 'root', b: 'payload', offset: { x: 0, y: 0 }, enabled: false }],
  distanceJoints: [{ id: 'disabled-joint', a: 'root', b: 'payload', length: 0, enabled: false }],
  distanceLimits: [{ id: 'disabled-limit', a: 'root', b: 'payload', maxLength: 0, enabled: false }]
};

const validation = Gate.validate(overlapWorld(), disabledConstraints);
assert.equal(validation.ok, true);
assert.equal(validation.activeCount, 0);
assert.equal(validation.disabledCount, 3);
assert.match(validation.warnings.join(' '), /excludes them from solver residuals/i);
assert.match(validation.warnings.join(' '), /donor physics source remains untouched/i);

const disabledOnly = Gate.step(overlapWorld(), disabledConstraints, 0.01, { isolateCollisions: true });
assert.equal(disabledOnly.world.stepIndex, 1, 'activity gate must still delegate exactly one donor-core step');
assert.equal(disabledOnly.activityDiagnostics.activeCount, 0);
assert.equal(disabledOnly.activityDiagnostics.disabledCount, 3);
assert.deepEqual(disabledOnly.activityDiagnostics.disabledIds.mounts, ['disabled-mount']);
assert.deepEqual(disabledOnly.activityDiagnostics.disabledIds.distanceJoints, ['disabled-joint']);
assert.deepEqual(disabledOnly.activityDiagnostics.disabledIds.distanceLimits, ['disabled-limit']);
assert.equal(disabledOnly.activityDiagnostics.disabledExcludedFromSolve, true);
assert.equal(disabledOnly.activityDiagnostics.disabledExcludedFromIsolationTopology, true);
assert.equal(disabledOnly.isolationDiagnostics.componentCount, 0, 'disabled edges must not create collision-isolation components');
assert.equal(disabledOnly.isolationDiagnostics.appliedComponents, 0);
assert.equal(
  hasPairContact(disabledOnly.core.worldAsIntegratedWithTemporaryGroups, 'root', 'payload'),
  true,
  'disabled constraints must not suppress ordinary donor-core collision contact'
);
assert.equal(disabledOnly.composerDiagnostics.after.maxMountError, 0, 'disabled mount residual must not enter convergence diagnostics');
assert.equal(disabledOnly.composerDiagnostics.after.maxDistanceError, 0, 'disabled distance-joint residual must not enter convergence diagnostics');
assert.equal(disabledOnly.composerDiagnostics.after.maxDistanceLimitError, 0, 'disabled distance-limit residual must not enter convergence diagnostics');
assert.equal(disabledOnly.activityDiagnostics.finalChecksum, Core.checksum(disabledOnly.world));

const inert = Gate.step(separatedWorld(), disabledConstraints, 0.01);
const inertPayload = inert.world.bodies.find(item => item.id === 'payload');
assert.ok(Math.abs(inertPayload.position.x - 3) < 1e-9, 'disabled mount/joint/limit definitions must not pull a separated body');
assert.equal(inert.activityDiagnostics.activeCount, 0);
assert.equal(inert.isolationDiagnostics, null);

const mixedConstraints = {
  mounts: [{ id: 'active-mount', a: 'root', b: 'payload', offset: { x: 0.5, y: 0 } }],
  distanceJoints: [{ id: 'disabled-joint', a: 'root', b: 'payload', length: 100, enabled: false }],
  distanceLimits: [{ id: 'disabled-limit', a: 'root', b: 'payload', minLength: 100, enabled: false }]
};
const mixed = Gate.step(overlapWorld(), mixedConstraints, 0.01, { isolateCollisions: true });
assert.equal(mixed.activityDiagnostics.activeCount, 1);
assert.equal(mixed.activityDiagnostics.disabledCount, 2);
assert.deepEqual(mixed.activityDiagnostics.activeIds.mounts, ['active-mount']);
assert.equal(mixed.isolationDiagnostics.componentCount, 1, 'enabled edge must still form an isolation component');
assert.equal(mixed.isolationDiagnostics.appliedComponents, 1);
assert.equal(
  hasPairContact(mixed.core.worldAsIntegratedWithTemporaryGroups, 'root', 'payload'),
  false,
  'enabled component isolation must continue to suppress its own donor-core contact'
);
assert.equal(mixed.composerDiagnostics.after.maxDistanceError, 0, 'disabled exact joint must not poison convergence beside an active mount');
assert.equal(mixed.composerDiagnostics.after.maxDistanceLimitError, 0, 'disabled limit must not poison convergence beside an active mount');

const invalidDisabled = Gate.validate(separatedWorld(), {
  mounts: [{ id: 'bad-disabled', a: 'root', b: 'missing', enabled: false }]
});
assert.equal(invalidDisabled.ok, false, 'disabled definitions still pass through source-integrity/body-reference validation');
assert.match(invalidDisabled.errors.join(' '), /body not found/i);

const replayA = Gate.step(overlapWorld(), mixedConstraints, 1 / 60, { isolateCollisions: true });
const replayB = Gate.step(overlapWorld(), mixedConstraints, 1 / 60, { isolateCollisions: true });
assert.equal(Core.checksum(replayA.world), Core.checksum(replayB.world), 'activity-gated mixed constraint step must replay deterministically in one JS runtime');
assert.match(replayA.limitations.join(' '), /lower-level composer or isolation/i);
assert.match(replayA.limitations.join(' '), /not scientific validation/i);

console.log('UC Constraint Activity Gate selftest: PASS (disabled solve/topology exclusion, enabled isolation continuity, source-integrity validation and deterministic replay)');
