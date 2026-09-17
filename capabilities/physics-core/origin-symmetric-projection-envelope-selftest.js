'use strict';

const assert = require('assert');
const Envelope = require('./uc-two-projection-radial-envelope.js');

const nearOrthogonalDirection = {
  x: 5e-7,
  y: Math.sqrt(1 - 25e-14)
};
const negativeDotNearOrthogonalDirection = {
  x: -5e-7,
  y: Math.sqrt(1 - 25e-14)
};

function allCornerRadii(result) {
  return result.corners.map(point => Math.hypot(point.x, point.y));
}

function assertSingleCornerMaximum(result, message) {
  const radii = allCornerRadii(result);
  assert.equal(
    result.maximumDistance,
    Math.max(...radii),
    `${message}: selected single-corner radius must equal the authoritative four-corner maximum`
  );
  assert.equal(
    result.distanceWork.cornerNormEvaluations,
    1,
    `${message}: exact represented interval symmetry should need only one corner norm`
  );
}

function assertOppositeCornerEvidence(result, message) {
  assert.deepEqual(result.corners[2], {
    x: -result.corners[0].x,
    y: -result.corners[0].y
  }, `${message}: third corner should be the exact negation of the first`);
  assert.deepEqual(result.corners[3], {
    x: -result.corners[1].x,
    y: -result.corners[1].y
  }, `${message}: fourth corner should be the exact negation of the second`);
  assert.notStrictEqual(result.corners[0], result.corners[2],
    `${message}: opposite evidence corners must remain independent objects`);
  assert.notStrictEqual(result.corners[1], result.corners[3],
    `${message}: opposite evidence corners must remain independent objects`);
}

const symmetric = Envelope.analyze(
  { x: 1, y: 0 },
  nearOrthogonalDirection,
  { min: -3, max: 3 },
  { min: -4, max: 4 }
);

assert.equal(symmetric.supported, true);
assert.equal(symmetric.originInsideProjectionRectangle, true);
assert.equal(symmetric.centrallySymmetricProjectionRectangle, true);
assert.equal(symmetric.degenerateProjectionIntervals, 0);
assert.equal(symmetric.distanceMethod, 'inverse-basis-parallelogram-origin-symmetric');
assert.equal(symmetric.minimumDistance, 0);
assert.deepEqual(symmetric.distanceWork, {
  edgeDistanceEvaluations: 0,
  cornerNormEvaluations: 1
}, 'exact origin symmetry should avoid edge scans and select one maximizing corner');
assert.deepEqual(symmetric.geometryWork, {
  projectionPointEvaluations: 2
}, 'a non-degenerate centrally symmetric rectangle should reconstruct only two adjacent corners');
assertSingleCornerMaximum(symmetric, 'positive represented dot');
assertOppositeCornerEvidence(symmetric, 'positive represented dot');

const negativeDotSymmetric = Envelope.analyze(
  { x: 1, y: 0 },
  negativeDotNearOrthogonalDirection,
  { min: -3, max: 3 },
  { min: -4, max: 4 }
);
assert.equal(negativeDotSymmetric.supported, true);
assert.equal(negativeDotSymmetric.centrallySymmetricProjectionRectangle, true);
assert.deepEqual(negativeDotSymmetric.geometryWork, {
  projectionPointEvaluations: 2
});
assertSingleCornerMaximum(negativeDotSymmetric, 'negative represented dot');
assertOppositeCornerEvidence(negativeDotSymmetric, 'negative represented dot');

const firstOnlySymmetric = Envelope.analyze(
  { x: 1, y: 0 },
  nearOrthogonalDirection,
  { min: -3, max: 3 },
  { min: -2, max: 5 }
);
assert.equal(firstOnlySymmetric.supported, true);
assert.equal(firstOnlySymmetric.centrallySymmetricProjectionRectangle, false);
assert.equal(firstOnlySymmetric.originInsideProjectionRectangle, true);
assert.equal(firstOnlySymmetric.distanceMethod, 'inverse-basis-parallelogram-origin-contained');
assert.equal(firstOnlySymmetric.minimumDistance, 0);
assert.deepEqual(firstOnlySymmetric.distanceWork, {
  edgeDistanceEvaluations: 0,
  cornerNormEvaluations: 1
}, 'one exact symmetric projection interval should reduce the radial maximum to one selected corner');
assert.deepEqual(firstOnlySymmetric.geometryWork, {
  projectionPointEvaluations: 4
}, 'one symmetric interval alone must retain four independent corner reconstructions');
assertSingleCornerMaximum(firstOnlySymmetric, 'first interval only symmetric');

const secondOnlySymmetric = Envelope.analyze(
  { x: 1, y: 0 },
  nearOrthogonalDirection,
  { min: 2, max: 5 },
  { min: -4, max: 4 }
);
assert.equal(secondOnlySymmetric.supported, true);
assert.equal(secondOnlySymmetric.centrallySymmetricProjectionRectangle, false);
assert.equal(secondOnlySymmetric.originInsideProjectionRectangle, false);
assert.equal(secondOnlySymmetric.zeroContainingProjectionIntervals, 1);
assert.equal(secondOnlySymmetric.distanceMethod, 'inverse-basis-parallelogram-single-active-edge');
assert.deepEqual(secondOnlySymmetric.distanceWork, {
  edgeDistanceEvaluations: 1,
  cornerNormEvaluations: 1
}, 'second-only exact symmetry should preserve the one-active-edge minimum and reduce maximum work to one corner norm');
assert.deepEqual(secondOnlySymmetric.geometryWork, {
  projectionPointEvaluations: 4
});
assertSingleCornerMaximum(secondOnlySymmetric, 'second interval only symmetric');

const orthonormalSymmetric = Envelope.analyze(
  { x: 1, y: 0 },
  { x: 0, y: 1 },
  { min: -3, max: 3 },
  { min: -4, max: 4 }
);
assert.equal(orthonormalSymmetric.supported, true);
assert.equal(orthonormalSymmetric.centrallySymmetricProjectionRectangle, true);
assert.equal(orthonormalSymmetric.distanceMethod, 'orthonormal-projection-rectangle');
assert.deepEqual(orthonormalSymmetric.distanceWork, {
  edgeDistanceEvaluations: 0,
  cornerNormEvaluations: 0
});
assert.deepEqual(orthonormalSymmetric.geometryWork, {
  projectionPointEvaluations: 2
}, 'central-symmetry reconstruction reduction should also apply to exact orthonormal evidence');
assert.deepEqual(orthonormalSymmetric.corners, [
  { x: -3, y: -4 },
  { x: 3, y: -4 },
  { x: 3, y: 4 },
  { x: -3, y: 4 }
]);
assertOppositeCornerEvidence(orthonormalSymmetric, 'orthonormal central symmetry');

const nearSymmetric = Envelope.analyze(
  { x: 1, y: 0 },
  nearOrthogonalDirection,
  { min: -3, max: 3.0000000001 },
  { min: -4, max: 4.0000000001 }
);
assert.equal(nearSymmetric.supported, true);
assert.equal(nearSymmetric.originInsideProjectionRectangle, true);
assert.equal(nearSymmetric.centrallySymmetricProjectionRectangle, false,
  'merely near-symmetric represented intervals must not count as exact central symmetry');
assert.equal(nearSymmetric.distanceMethod, 'inverse-basis-parallelogram-origin-contained');
assert.deepEqual(nearSymmetric.distanceWork, {
  edgeDistanceEvaluations: 0,
  cornerNormEvaluations: 4
}, 'when neither interval is exactly symmetric, the established four-corner maximum scan must remain authoritative');
assert.deepEqual(nearSymmetric.geometryWork, {
  projectionPointEvaluations: 4
}, 'near symmetry must not reduce projection-to-world reconstruction work');

assert.deepEqual(
  Envelope.analyze(
    { x: 1, y: 0 },
    nearOrthogonalDirection,
    { min: -3, max: 3 },
    { min: -4, max: 4 }
  ),
  symmetric,
  'origin-symmetric fast-path evidence must replay deterministically'
);

console.log('origin symmetric projection envelope selftest passed');
