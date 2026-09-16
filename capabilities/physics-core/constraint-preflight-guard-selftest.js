'use strict';

const assert = require('assert');
const Core = require('./source/axm-physics-core.js');
const Composer = require('./uc-constraint-composer.js');
const Guard = require('./uc-constraint-preflight-guard.js');

function add(world, spec) { return Core.addBody(world, spec).world; }
function baseWorld() {
  let world = Core.createWorld({ gravity: { x: 0, y: 0 }, bounds: false, sleep: { enabled: false } });
  world = add(world, { id: 'a', type: 'static', shape: { kind: 'circle', radius: 0.2 }, position: { x: 0, y: 0 } });
  world = add(world, { id: 'b', type: 'dynamic', shape: { kind: 'circle', radius: 0.2 }, position: { x: 3, y: 2 }, mass: 1, linearDamping: 0 });
  return world;
}

const conflictingConstraints = {
  mounts: [{ id: 'mount', a: 'a', b: 'b', offset: { x: 0, y: 2 } }],
  axisLocks: [{ id: 'x-lock', a: 'a', b: 'b', axis: 'x', offset: 1 }]
};
const blockedInput = baseWorld();
const blockedSnapshot = JSON.stringify(blockedInput);
const blocked = Guard.step(blockedInput, conflictingConstraints, 1 / 60);
assert.equal(blocked.ok, false);
assert.equal(blocked.accepted, false);
assert.equal(blocked.blocked, true);
assert.equal(blocked.reason, 'PROVABLE_LOCAL_CONFLICT');
assert.equal(blocked.coreStepExecuted, false);
assert.equal(blocked.composer, null);
assert.equal(blocked.preflight.conflicts.length, 1);
assert.equal(blocked.worldChecksumBefore, blocked.worldChecksumAfter);
assert.equal(JSON.stringify(blockedInput), blockedSnapshot, 'guard must not mutate the caller world when it blocks');
assert.deepEqual(blocked.world, blockedInput, 'blocked result must preserve the input world state');
assert.match(blocked.limitations.join(' '), /not proof of global satisfiability/i);
assert.match(blocked.limitations.join(' '), /not scientific validation/i);

const blockedReplay = Guard.step(baseWorld(), conflictingConstraints, 1 / 60);
assert.equal(blocked.decisionChecksum, blockedReplay.decisionChecksum, 'blocked decision evidence must replay deterministically');
assert.equal(blocked.preflight.checksum, blockedReplay.preflight.checksum);

const radialConflictInput = baseWorld();
const radialConflictSnapshot = JSON.stringify(radialConflictInput);
const radialBlocked = Guard.step(radialConflictInput, {
  distanceJoints: [{ id: 'distance-three', a: 'a', b: 'b', length: 3 }],
  distanceLimits: [{ id: 'max-two', a: 'a', b: 'b', maxLength: 2 }]
}, 1 / 60);
assert.equal(radialBlocked.blocked, true, 'same-pair distance interval contradiction must fail closed before donor integration');
assert.equal(radialBlocked.reason, 'PROVABLE_LOCAL_CONFLICT');
assert.equal(radialBlocked.coreStepExecuted, false);
assert.equal(radialBlocked.preflight.conflicts[0].code, 'CONFLICTING_DISTANCE_INTERVALS');
assert.equal(radialBlocked.worldChecksumBefore, radialBlocked.worldChecksumAfter);
assert.equal(JSON.stringify(radialConflictInput), radialConflictSnapshot, 'radial conflict block must preserve caller world state');

const invalid = Guard.step(baseWorld(), {
  distanceJoints: [{ id: 'bad-distance', a: 'a', b: 'missing', length: 1 }]
}, 1 / 60);
assert.equal(invalid.blocked, true);
assert.equal(invalid.reason, 'INVALID_CONSTRAINTS');
assert.equal(invalid.coreStepExecuted, false);
assert.match(invalid.composerValidation.errors.join(' '), /body not found/i);

const acceptedConstraints = {
  axisLocks: [{ id: 'x-lock', a: 'a', b: 'b', axis: 'x', offset: 3 }],
  axisLimits: [{ id: 'y-band', a: 'a', b: 'b', axis: 'y', minOffset: 1, maxOffset: 3 }]
};
const composerOptions = { prePasses: 1, postPasses: 1, earlyExit: true };
const guardedAccepted = Guard.step(baseWorld(), acceptedConstraints, 1 / 60, { composer: composerOptions });
const directAccepted = Composer.step(baseWorld(), acceptedConstraints, 1 / 60, composerOptions);
assert.equal(guardedAccepted.ok, true);
assert.equal(guardedAccepted.accepted, true);
assert.equal(guardedAccepted.blocked, false);
assert.equal(guardedAccepted.reason, 'ACCEPTED');
assert.equal(guardedAccepted.coreStepExecuted, true);
assert.equal(guardedAccepted.preflight.conflicts.length, 0);
assert.deepEqual(guardedAccepted.world, directAccepted.world, 'accepted guard path must preserve existing composer world behavior exactly');
assert.deepEqual(guardedAccepted.composer, directAccepted, 'accepted guard path must expose the unmodified composer receipt');
assert.equal(guardedAccepted.worldChecksumAfter, Core.checksum(directAccepted.world));

const compatibleDistanceConstraints = {
  distanceJoints: [{ id: 'distance', a: 'a', b: 'b', length: Math.sqrt(13) }],
  distanceLimits: [{ id: 'distance-band', a: 'a', b: 'b', minLength: 3, maxLength: 4 }]
};
const guardedDistance = Guard.step(baseWorld(), compatibleDistanceConstraints, 1 / 60, { composer: composerOptions });
const directDistance = Composer.step(baseWorld(), compatibleDistanceConstraints, 1 / 60, composerOptions);
assert.equal(guardedDistance.accepted, true, 'compatible same-pair distance constraints must still delegate to the composer');
assert.equal(guardedDistance.preflight.counts.unsupportedConstraints, 0);
assert.equal(guardedDistance.preflight.counts.radialGroups, 1);
assert.equal(guardedDistance.preflight.conflicts.length, 0);
assert.equal(guardedDistance.coreStepExecuted, true);
assert.deepEqual(guardedDistance.composer, directDistance, 'accepted distance path must remain exact composer delegation');
assert.match(guardedDistance.evidence.join(' '), /radial distance group/i);

console.log('UC Constraint Preflight Guard selftest: PASS (fail-closed invalid/projected/radial conflict blocking, zero-step preservation, accepted composer equivalence and deterministic decision evidence)');
