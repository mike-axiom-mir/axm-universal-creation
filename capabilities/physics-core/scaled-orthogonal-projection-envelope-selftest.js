'use strict';

const assert = require('assert');
const Envelope = require('./uc-two-projection-radial-envelope.js');

const firstDirection = { x: 1 + 2e-10, y: 0 };
const secondDirection = { x: 0, y: 1 - 2e-10 };
const firstInterval = { min: 2, max: 5 };
const secondInterval = { min: -4, max: -1 };

const result = Envelope.analyze(
  firstDirection,
  secondDirection,
  firstInterval,
  secondInterval
);

assert.equal(result.supported, true);
assert.equal(result.distanceMethod, 'orthogonal-scaled-projection-rectangle');
assert.deepEqual(result.distanceWork, {
  edgeDistanceEvaluations: 0,
  cornerNormEvaluations: 0
}, 'exact represented orthogonality with tiny scale error should avoid edge and corner radial scans');

const firstNorm = Math.hypot(firstDirection.x, firstDirection.y);
const secondNorm = Math.hypot(secondDirection.x, secondDirection.y);
const expectedMinimum = Math.hypot(2 / firstNorm, 1 / secondNorm);
const expectedMaximum = Math.hypot(5 / firstNorm, 4 / secondNorm);

assert.ok(Math.abs(result.minimumDistance - expectedMinimum) < 1e-14,
  'scaled orthogonal minimum must match the scale-adjusted projection rectangle');
assert.ok(Math.abs(result.maximumDistance - expectedMaximum) < 1e-14,
  'scaled orthogonal maximum must match the scale-adjusted projection rectangle');

assert.deepEqual(
  Envelope.analyze(firstDirection, secondDirection, firstInterval, secondInterval),
  result,
  'scaled orthogonal evidence must replay deterministically'
);

const nearOrthogonal = Envelope.analyze(
  firstDirection,
  { x: 5e-7, y: Math.sqrt(1 - 25e-14) },
  firstInterval,
  secondInterval
);

assert.equal(nearOrthogonal.supported, true);
assert.equal(nearOrthogonal.distanceMethod, 'inverse-basis-parallelogram-two-active-edges');
assert.deepEqual(nearOrthogonal.distanceWork, {
  edgeDistanceEvaluations: 2,
  cornerNormEvaluations: 4
}, 'a nonzero represented dot product must retain the established inverse-basis path');

console.log('scaled orthogonal projection envelope selftest passed');
