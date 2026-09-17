'use strict';

const assert = require('assert');
const Core = require('./source/axm-physics-core.js');
const Envelope = require('./uc-two-projection-radial-envelope.js');
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

const axisBox = Envelope.analyze(
  { x: 1, y: 0 },
  { x: 0, y: 1 },
  { min: -2, max: 2 },
  { min: -2, max: 2 }
);
assert.equal(axisBox.supported, true);
assert.equal(axisBox.determinant, 1);
assert.equal(axisBox.minimumDistance, 0);
assert.equal(axisBox.maximumDistance, Math.hypot(2, 2));

const nearOrthogonalDirection = {
  x: 5e-7,
  y: Math.sqrt(1 - 25e-14)
};
const pointEnvelope = Envelope.analyze(
  { x: 1, y: 0 },
  nearOrthogonalDirection,
  { min: 3, max: 3 },
  { min: 4, max: 4 }
);
assert.equal(pointEnvelope.supported, true);
assert.ok(pointEnvelope.minimumDistance > 4.99999879 && pointEnvelope.minimumDistance < 4.99999881);
assert.equal(pointEnvelope.minimumDistance, pointEnvelope.maximumDistance,
  'two exact projections define one displacement point and therefore one exact radius');

const unboundedEnvelope = Envelope.analyze(
  { x: 1, y: 0 },
  { x: 0, y: 1 },
  { min: 3, max: Infinity },
  { min: 4, max: 4 }
);
assert.equal(unboundedEnvelope.supported, false);
assert.equal(unboundedEnvelope.reason, 'NON_FINITE_INTERVAL');

const projectionLocks = {
  axisLocks: [
    { id: 'tight-x-three', a: 'a', b: 'b', axis: 'x', offset: 3 }
  ],
  directionLocks: [
    { id: 'tight-near-y-four', a: 'a', b: 'b', direction: nearOrthogonalDirection, offset: 4 }
  ]
};

const tighterMaximum = Preflight.analyze(baseWorld(), {
  axisLocks: projectionLocks.axisLocks,
  directionLocks: projectionLocks.directionLocks,
  distanceLimits: [
    { id: 'tight-radius-max', a: 'a', b: 'b', maxLength: 4.999998775 }
  ]
}, { orthogonalityTolerance: 1e-6 });
assert.equal(tighterMaximum.valid, true);
assert.equal(tighterMaximum.base.conflictFree, true,
  'neither single projection alone exceeds the radial maximum');
assert.equal(tighterMaximum.counts.radialMaximumChecks, 1);
assert.equal(tighterMaximum.counts.radialMaximumConflicts, 1,
  'exact finite parallelogram minimum radius must prove the tighter local conflict');
const maximumConflict = tighterMaximum.conflicts.find(item => item.code === 'ORTHOGONAL_PROJECTIONS_EXCEED_DISTANCE_MAX');
assert.ok(maximumConflict);
assert.equal(maximumConflict.boundModel, 'finite-interval-parallelogram-exact');
assert.ok(maximumConflict.decisionWitness.singularValueLowerBound < maximumConflict.decisionWitness.maximumAllowedDistance,
  'the previous singular-value lower bound alone must be too loose to prove this regression');
assert.ok(maximumConflict.decisionWitness.minimumRequiredDistance > maximumConflict.decisionWitness.maximumAllowedDistance,
  'the exact finite-envelope lower bound must prove the contradiction');
assert.ok(maximumConflict.decisionWitness.exactEnvelope.minimumDistance > maximumConflict.decisionWitness.singularValueLowerBound);

const tighterMinimum = Preflight.analyze(baseWorld(), {
  axisLocks: projectionLocks.axisLocks,
  directionLocks: projectionLocks.directionLocks,
  distanceLimits: [
    { id: 'tight-radius-min', a: 'a', b: 'b', minLength: 4.999998825 }
  ]
}, { orthogonalityTolerance: 1e-6 });
assert.equal(tighterMinimum.base.conflictFree, true);
assert.equal(tighterMinimum.counts.radialMinimumChecks, 1);
assert.equal(tighterMinimum.counts.radialMinimumConflicts, 1,
  'exact finite parallelogram maximum radius must prove the tighter local conflict');
const minimumConflict = tighterMinimum.conflicts.find(item => item.code === 'DISTANCE_MIN_EXCEEDS_ORTHOGONAL_PROJECTION_MAX');
assert.ok(minimumConflict);
assert.equal(minimumConflict.boundModel, 'finite-interval-parallelogram-exact');
assert.ok(minimumConflict.decisionWitness.singularValueUpperBound > minimumConflict.decisionWitness.minimumAllowedDistance,
  'the previous singular-value upper bound alone must be too loose to prove this regression');
assert.ok(minimumConflict.decisionWitness.maximumPossibleDistance < minimumConflict.decisionWitness.minimumAllowedDistance,
  'the exact finite-envelope upper bound must prove the contradiction');
assert.ok(minimumConflict.decisionWitness.exactEnvelope.maximumDistance < minimumConflict.decisionWitness.singularValueUpperBound);

const blockedWorld = baseWorld();
const blockedBefore = Core.checksum(blockedWorld);
const blocked = Guard.step(
  blockedWorld,
  {
    axisLocks: projectionLocks.axisLocks,
    directionLocks: projectionLocks.directionLocks,
    distanceLimits: [{ id: 'tight-radius-max', a: 'a', b: 'b', maxLength: 4.999998775 }]
  },
  1 / 60,
  { preflight: { orthogonalityTolerance: 1e-6 } }
);
assert.equal(blocked.accepted, false);
assert.equal(blocked.blocked, true);
assert.equal(blocked.reason, 'PROVABLE_ORTHOGONAL_LOCAL_CONFLICT');
assert.equal(blocked.coreStepExecuted, false);
assert.equal(blocked.worldChecksumBefore, blockedBefore);
assert.equal(blocked.worldChecksumAfter, blockedBefore);
assert.equal(Core.checksum(blockedWorld), blockedBefore,
  'exact-envelope fail-closed proof must preserve caller world state');

const oblique = Preflight.analyze(baseWorld(), {
  directionLocks: [
    { id: 'oblique-a', a: 'a', b: 'b', direction: { x: 1, y: 0 }, offset: 3 },
    { id: 'oblique-b', a: 'a', b: 'b', direction: { x: 1, y: 1 }, offset: 4 }
  ],
  distanceLimits: [{ id: 'oblique-radius', a: 'a', b: 'b', maxLength: 4 }]
}, { orthogonalityTolerance: 1e-6 });
assert.equal(oblique.counts.orthogonalProjectionRadialChecks, 0,
  'exact radial envelopes must not widen eligibility to oblique direction pairs');
assert.equal(oblique.counts.orthogonalProjectionRadialConflicts, 0);

const replay = Preflight.analyze(baseWorld(), {
  axisLocks: projectionLocks.axisLocks,
  directionLocks: projectionLocks.directionLocks,
  distanceLimits: [{ id: 'tight-radius-max', a: 'a', b: 'b', maxLength: 4.999998775 }]
}, { orthogonalityTolerance: 1e-6 });
assert.equal(tighterMaximum.checksum, replay.checksum,
  'exact finite radial-envelope proof must replay deterministically');

console.log('two projection radial envelope selftest passed');
