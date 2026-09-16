'use strict';

const assert = require('assert');
const Core = require('./source/axm-physics-core.js');
const Preflight = require('./uc-orthogonal-projection-preflight.js');
const Guard = require('./uc-orthogonal-projection-preflight-guard.js');

function add(world, spec) {
  return Core.addBody(world, spec).world;
}

function baseWorld() {
  let world = Core.createWorld({ gravity: { x: 0, y: 0 }, bounds: false, sleep: { enabled: false } });
  world = add(world, { id: 'a', type: 'static', position: { x: 0, y: 0 } });
  world = add(world, { id: 'b', type: 'dynamic', position: { x: 1, y: 2 }, mass: 1, linearDamping: 0 });
  return world;
}

const combinedConflictConstraints = {
  axisLocks: [
    { id: 'x-three', a: 'a', b: 'b', axis: 'x', offset: 3 },
    { id: 'y-four', a: 'a', b: 'b', axis: 'y', offset: 4 }
  ],
  distanceLimits: [
    { id: 'radius-four-point-five', a: 'a', b: 'b', maxLength: 4.5 }
  ]
};

const combined = Preflight.analyze(baseWorld(), combinedConflictConstraints);
assert.equal(combined.valid, true);
assert.equal(combined.base.conflictFree, true, 'neither projection alone exceeds the radial maximum');
assert.equal(combined.counts.baseConflicts, 0);
assert.equal(combined.counts.orthogonalProjectionRadialChecks, 1);
assert.equal(combined.counts.orthogonalProjectionRadialConflicts, 1);
assert.equal(combined.conflictFree, false);
assert.equal(combined.conflicts[0].code, 'ORTHOGONAL_PROJECTIONS_EXCEED_DISTANCE_MAX');
assert.equal(combined.conflicts[0].minimumRequiredDistance, 5);
assert.equal(combined.conflicts[0].maximumAllowedDistance, 4.5);
assert.deepEqual(combined.conflicts[0].constraintIds, ['radius-four-point-five', 'x-three', 'y-four']);

const compatible = Preflight.analyze(baseWorld(), {
  axisLocks: combinedConflictConstraints.axisLocks,
  distanceLimits: [{ id: 'radius-five', a: 'a', b: 'b', maxLength: 5 }]
});
assert.equal(compatible.conflictFree, true, 'the exact 3-4-5 boundary must remain accepted');
assert.equal(compatible.counts.orthogonalProjectionRadialChecks, 1);
assert.equal(compatible.counts.orthogonalProjectionRadialConflicts, 0);

const oblique = Preflight.analyze(baseWorld(), {
  directionLocks: [
    { id: 'x-three', a: 'a', b: 'b', direction: { x: 1, y: 0 }, offset: 3 },
    { id: 'diagonal-four', a: 'a', b: 'b', direction: { x: 1, y: 1 }, offset: 4 }
  ],
  distanceLimits: [{ id: 'radius-four-point-five', a: 'a', b: 'b', maxLength: 4.5 }]
});
assert.equal(oblique.counts.orthogonalProjectionRadialChecks, 0, 'oblique directions must not be combined by the bounded proof');
assert.equal(oblique.counts.orthogonalProjectionRadialConflicts, 0);

const radialMinimumOnly = Preflight.analyze(baseWorld(), {
  axisLocks: [
    { id: 'x-zero', a: 'a', b: 'b', axis: 'x', offset: 0 },
    { id: 'y-zero', a: 'a', b: 'b', axis: 'y', offset: 0 }
  ],
  distanceLimits: [{ id: 'minimum-ten', a: 'a', b: 'b', minLength: 10 }]
});
assert.equal(radialMinimumOnly.counts.orthogonalProjectionRadialConflicts, 0, 'radial minima are outside this proof');

const blockedWorld = baseWorld();
const blockedBefore = Core.checksum(blockedWorld);
const blocked = Guard.step(blockedWorld, combinedConflictConstraints, 1 / 60);
assert.equal(blocked.ok, false);
assert.equal(blocked.accepted, false);
assert.equal(blocked.blocked, true);
assert.equal(blocked.reason, 'PROVABLE_ORTHOGONAL_LOCAL_CONFLICT');
assert.equal(blocked.coreStepExecuted, false);
assert.equal(blocked.worldChecksumBefore, blockedBefore);
assert.equal(blocked.worldChecksumAfter, blockedBefore);
assert.equal(Core.checksum(blockedWorld), blockedBefore, 'blocked guard must preserve caller world state');

const acceptedConstraints = {
  axisLocks: combinedConflictConstraints.axisLocks,
  distanceLimits: [{ id: 'radius-six', a: 'a', b: 'b', maxLength: 6 }]
};
const accepted = Guard.step(baseWorld(), acceptedConstraints, 1 / 60);
assert.equal(accepted.accepted, true);
assert.equal(accepted.blocked, false);
assert.equal(accepted.coreStepExecuted, true, 'accepted input must delegate through the established guard/composer path');

const replayA = Preflight.analyze(baseWorld(), combinedConflictConstraints);
const replayB = Preflight.analyze(baseWorld(), combinedConflictConstraints);
assert.equal(replayA.checksum, replayB.checksum, 'extended preflight receipt must replay deterministically');

const guardReplayA = Guard.step(baseWorld(), combinedConflictConstraints, 1 / 60);
const guardReplayB = Guard.step(baseWorld(), combinedConflictConstraints, 1 / 60);
assert.equal(guardReplayA.decisionChecksum, guardReplayB.decisionChecksum, 'blocked guard decision receipt must replay deterministically');

console.log('orthogonal projection preflight selftest passed');
