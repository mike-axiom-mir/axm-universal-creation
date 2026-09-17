'use strict';

const assert = require('assert');
const Envelope = require('./uc-two-projection-radial-envelope.js');

const nearOrthogonalDirection = {
  x: 5e-7,
  y: Math.sqrt(1 - 25e-14)
};

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
  cornerNormEvaluations: 2
}, 'exact origin symmetry should avoid both edge scans and duplicate opposite-corner norms');

const firstUniqueRadius = Math.hypot(symmetric.corners[0].x, symmetric.corners[0].y);
const secondUniqueRadius = Math.hypot(symmetric.corners[1].x, symmetric.corners[1].y);
const thirdRadius = Math.hypot(symmetric.corners[2].x, symmetric.corners[2].y);
const fourthRadius = Math.hypot(symmetric.corners[3].x, symmetric.corners[3].y);
assert.ok(Math.abs(firstUniqueRadius - thirdRadius) < 1e-12,
  'opposite first/third corners must have the same radius under exact projection symmetry');
assert.ok(Math.abs(secondUniqueRadius - fourthRadius) < 1e-12,
  'opposite second/fourth corners must have the same radius under exact projection symmetry');
assert.equal(symmetric.maximumDistance, Math.max(firstUniqueRadius, secondUniqueRadius));

const nearSymmetric = Envelope.analyze(
  { x: 1, y: 0 },
  nearOrthogonalDirection,
  { min: -3, max: 3.0000000001 },
  { min: -4, max: 4 }
);
assert.equal(nearSymmetric.supported, true);
assert.equal(nearSymmetric.originInsideProjectionRectangle, true);
assert.equal(nearSymmetric.centrallySymmetricProjectionRectangle, false,
  'merely near-symmetric represented intervals must not take the exact symmetry fast path');
assert.equal(nearSymmetric.distanceMethod, 'inverse-basis-parallelogram-origin-contained');
assert.deepEqual(nearSymmetric.distanceWork, {
  edgeDistanceEvaluations: 0,
  cornerNormEvaluations: 4
}, 'near-symmetric intervals must retain the established four-corner maximum scan');

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
