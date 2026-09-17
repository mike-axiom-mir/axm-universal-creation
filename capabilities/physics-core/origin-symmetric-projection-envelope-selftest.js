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
assertSingleCornerMaximum(symmetric, 'positive represented dot');

const negativeDotSymmetric = Envelope.analyze(
  { x: 1, y: 0 },
  negativeDotNearOrthogonalDirection,
  { min: -3, max: 3 },
  { min: -4, max: 4 }
);
assert.equal(negativeDotSymmetric.supported, true);
assert.equal(negativeDotSymmetric.centrallySymmetricProjectionRectangle, true);
assertSingleCornerMaximum(negativeDotSymmetric, 'negative represented dot');

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
assertSingleCornerMaximum(secondOnlySymmetric, 'second interval only symmetric');

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
