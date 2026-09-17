'use strict';

const assert = require('assert');
const Envelope = require('./uc-two-projection-radial-envelope.js');

const nearOrthogonalDirection = {
  x: 5e-7,
  y: Math.sqrt(1 - 25e-14)
};

const firstExcluded = Envelope.analyze(
  { x: 1, y: 0 },
  nearOrthogonalDirection,
  { min: 3, max: 5 },
  { min: -10, max: 10 }
);
assert.equal(firstExcluded.supported, true);
assert.equal(firstExcluded.degenerateProjectionIntervals, 0);
assert.equal(firstExcluded.zeroContainingProjectionIntervals, 1);
assert.equal(firstExcluded.originInsideProjectionRectangle, false);
assert.equal(firstExcluded.distanceMethod, 'inverse-basis-parallelogram-single-active-edge');
assert.deepEqual(firstExcluded.distanceWork, {
  edgeDistanceEvaluations: 1,
  cornerNormEvaluations: 4
}, 'one zero-containing interval should require only the nearest boundary edge of the other interval');
assert.ok(Math.abs(firstExcluded.minimumDistance - 3) < 1e-12,
  'the positive first-projection interval should reach its radial minimum on the min boundary edge');

const firstExcludedNegative = Envelope.analyze(
  { x: 1, y: 0 },
  nearOrthogonalDirection,
  { min: -5, max: -3 },
  { min: -10, max: 10 }
);
assert.equal(firstExcludedNegative.supported, true);
assert.equal(firstExcludedNegative.distanceMethod, 'inverse-basis-parallelogram-single-active-edge');
assert.deepEqual(firstExcludedNegative.distanceWork, {
  edgeDistanceEvaluations: 1,
  cornerNormEvaluations: 4
});
assert.ok(Math.abs(firstExcludedNegative.minimumDistance - 3) < 1e-12,
  'the negative first-projection interval should reach its radial minimum on the max boundary edge nearest zero');

const secondExcluded = Envelope.analyze(
  { x: 1, y: 0 },
  nearOrthogonalDirection,
  { min: -10, max: 10 },
  { min: 4, max: 6 }
);
assert.equal(secondExcluded.supported, true);
assert.equal(secondExcluded.degenerateProjectionIntervals, 0);
assert.equal(secondExcluded.zeroContainingProjectionIntervals, 1);
assert.equal(secondExcluded.originInsideProjectionRectangle, false);
assert.equal(secondExcluded.distanceMethod, 'inverse-basis-parallelogram-single-active-edge');
assert.deepEqual(secondExcluded.distanceWork, {
  edgeDistanceEvaluations: 1,
  cornerNormEvaluations: 4
});
assert.ok(Math.abs(secondExcluded.minimumDistance - 4) < 1e-12,
  'the positive second-projection interval should reach its radial minimum on the min boundary edge');

const neitherContainsZero = Envelope.analyze(
  { x: 1, y: 0 },
  nearOrthogonalDirection,
  { min: 3, max: 5 },
  { min: 4, max: 6 }
);
assert.equal(neitherContainsZero.supported, true);
assert.equal(neitherContainsZero.zeroContainingProjectionIntervals, 0);
assert.equal(neitherContainsZero.distanceMethod, 'inverse-basis-parallelogram-edges');
assert.deepEqual(neitherContainsZero.distanceWork, {
  edgeDistanceEvaluations: 4,
  cornerNormEvaluations: 4
}, 'the optimization must not weaken the authoritative full edge scan when neither interval contains zero');

assert.deepEqual(
  Envelope.analyze(
    { x: 1, y: 0 },
    nearOrthogonalDirection,
    { min: 3, max: 5 },
    { min: -10, max: 10 }
  ),
  firstExcluded,
  'single-active-edge evidence must replay deterministically'
);

console.log('single zero projection envelope selftest passed');
