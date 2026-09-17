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
assert.equal(axisBox.distanceMethod, 'orthonormal-projection-rectangle');
assert.equal(axisBox.originInsideProjectionRectangle, true);
assert.deepEqual(axisBox.distanceWork, {
  edgeDistanceEvaluations: 0,
  cornerNormEvaluations: 0
}, 'exact orthonormal envelopes should avoid the general edge/corner radial scans');

const swappedAxisBox = Envelope.analyze(
  { x: 0, y: 1 },
  { x: 1, y: 0 },
  { min: 3, max: 5 },
  { min: -6, max: -4 }
);
assert.equal(swappedAxisBox.supported, true);
assert.equal(swappedAxisBox.determinant, -1,
  'orientation-reversing orthonormal bases remain invertible exact fast-path inputs');
assert.equal(swappedAxisBox.minimumDistance, Math.hypot(3, 4));
assert.equal(swappedAxisBox.maximumDistance, Math.hypot(5, 6));
assert.equal(swappedAxisBox.distanceMethod, 'orthonormal-projection-rectangle');
assert.equal(swappedAxisBox.originInsideProjectionRectangle, false);
assert.deepEqual(swappedAxisBox.corners[0], { x: -6, y: 3 },
  'transpose reconstruction must preserve exact corners for determinant -1 orthonormal bases');

const shortFiniteEdge = Envelope.analyze(
  { x: 1, y: 0 },
  { x: 0, y: 1 },
  { min: -5e-9, max: 5e-9 },
  { min: 1e-10, max: 1e-10 }
);
assert.equal(shortFiniteEdge.supported, true);
assert.ok(Math.abs(shortFiniteEdge.minimumDistance - 1e-10) < 1e-20,
  'a represented non-zero edge shorter than sqrt(Number.EPSILON) must not be collapsed to one endpoint');
assert.ok(shortFiniteEdge.minimumDistance < 2e-9,
  'the true feasible short edge must remain inside the bounded radial maximum used by the integration regression');
assert.equal(shortFiniteEdge.distanceMethod, 'orthonormal-projection-rectangle',
  'the exact-axis short-edge case should use the direct projection-rectangle extrema path');

const largeFiniteEnvelope = Envelope.analyze(
  { x: 1, y: 0 },
  { x: 0, y: 1 },
  { min: 1e200, max: 2e200 },
  { min: 1e200, max: 2e200 }
);
assert.equal(largeFiniteEnvelope.supported, true,
  'finite large-magnitude geometry must not be rejected merely because an unscaled edge-length square would overflow');
assert.ok(Number.isFinite(largeFiniteEnvelope.minimumDistance));
assert.ok(Number.isFinite(largeFiniteEnvelope.maximumDistance));
assert.ok(Math.abs(largeFiniteEnvelope.minimumDistance / Math.hypot(1e200, 1e200) - 1) < 1e-15);
assert.ok(Math.abs(largeFiniteEnvelope.maximumDistance / Math.hypot(2e200, 2e200) - 1) < 1e-15);
assert.equal(largeFiniteEnvelope.distanceMethod, 'orthonormal-projection-rectangle');

const nonRepresentableRadialEnvelope = Envelope.analyze(
  { x: 1, y: 0 },
  { x: 0, y: 1 },
  { min: 1.3e308, max: 1.3e308 },
  { min: 1.3e308, max: 1.3e308 }
);
assert.equal(nonRepresentableRadialEnvelope.supported, false,
  'finite projection coordinates whose radial geometry exceeds Number range must be declined, not emitted as NaN evidence');
assert.equal(nonRepresentableRadialEnvelope.reason, 'NON_FINITE_RADIAL_ENVELOPE');

const shortFiniteCompatible = Preflight.analyze(baseWorld(), {
  axisLimits: [
    { id: 'short-x-band', a: 'a', b: 'b', axis: 'x', minOffset: -5e-9, maxOffset: 5e-9 }
  ],
  axisLocks: [
    { id: 'short-y-lock', a: 'a', b: 'b', axis: 'y', offset: 1e-10 }
  ],
  distanceLimits: [
    { id: 'short-radius-max', a: 'a', b: 'b', maxLength: 2e-9 }
  ]
});
assert.equal(shortFiniteCompatible.base.conflictFree, true);
assert.equal(shortFiniteCompatible.counts.radialMaximumChecks, 1);
assert.equal(shortFiniteCompatible.counts.radialMaximumConflicts, 0,
  'sub-epsilon finite-edge handling must not manufacture a local contradiction');
assert.equal(shortFiniteCompatible.conflictFree, true);

const largeFiniteConflict = Preflight.analyze(baseWorld(), {
  axisLimits: [
    { id: 'large-x-band', a: 'a', b: 'b', axis: 'x', minOffset: 1e200, maxOffset: 2e200 },
    { id: 'large-y-band', a: 'a', b: 'b', axis: 'y', minOffset: 1e200, maxOffset: 2e200 }
  ],
  distanceLimits: [
    { id: 'large-radius-max', a: 'a', b: 'b', maxLength: 1.3e200 }
  ]
});
assert.equal(largeFiniteConflict.base.conflictFree, true,
  'neither large finite projection alone exceeds the radial maximum');
assert.equal(largeFiniteConflict.counts.radialMaximumChecks, 1);
assert.equal(largeFiniteConflict.counts.radialMaximumConflicts, 1,
  'scaled segment geometry must preserve the exact finite-envelope contradiction at large represented magnitudes');
const largeFiniteMaximumConflict = largeFiniteConflict.conflicts.find(
  item => item.code === 'ORTHOGONAL_PROJECTIONS_EXCEED_DISTANCE_MAX'
);
assert.ok(largeFiniteMaximumConflict);
assert.equal(largeFiniteMaximumConflict.boundModel, 'finite-interval-parallelogram-exact');
assert.ok(Number.isFinite(largeFiniteMaximumConflict.decisionWitness.minimumRequiredDistance));

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
assert.equal(pointEnvelope.distanceMethod, 'inverse-basis-parallelogram-edges',
  'tolerance-eligible but not exactly orthonormal directions must retain the general exact geometry path');
assert.equal(pointEnvelope.originInsideProjectionRectangle, false);
assert.deepEqual(pointEnvelope.distanceWork, {
  edgeDistanceEvaluations: 4,
  cornerNormEvaluations: 4
});

const originContainedGeneralEnvelope = Envelope.analyze(
  { x: 1, y: 0 },
  nearOrthogonalDirection,
  { min: -3, max: 2 },
  { min: -4, max: 5 }
);
assert.equal(originContainedGeneralEnvelope.supported, true);
assert.equal(originContainedGeneralEnvelope.minimumDistance, 0,
  'if both signed projection intervals contain zero, the invertible linear basis makes world-space origin exactly feasible');
assert.equal(originContainedGeneralEnvelope.originInsideProjectionRectangle, true);
assert.equal(originContainedGeneralEnvelope.distanceMethod, 'inverse-basis-parallelogram-origin-contained');
assert.deepEqual(originContainedGeneralEnvelope.distanceWork, {
  edgeDistanceEvaluations: 0,
  cornerNormEvaluations: 4
}, 'origin-contained general envelopes should skip all four redundant edge-distance scans while retaining corner work for the radial maximum');
assert.deepEqual(
  Envelope.analyze(
    { x: 1, y: 0 },
    nearOrthogonalDirection,
    { min: -3, max: 2 },
    { min: -4, max: 5 }
  ),
  originContainedGeneralEnvelope,
  'origin-contained general-envelope evidence must replay deterministically'
);

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
