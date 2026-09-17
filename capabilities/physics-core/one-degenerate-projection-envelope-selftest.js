'use strict';

const assert = require('assert');
const Envelope = require('./uc-two-projection-radial-envelope.js');

const nearOrthogonalDirection = {
  x: 5e-7,
  y: Math.sqrt(1 - 25e-14)
};

function expectedPoint(firstProjection, secondProjection) {
  return {
    x: firstProjection,
    y: (secondProjection - firstProjection * nearOrthogonalDirection.x) / nearOrthogonalDirection.y
  };
}

function radius(point) {
  return Math.hypot(point.x, point.y);
}

const fixedFirstProjection = Envelope.analyze(
  { x: 1, y: 0 },
  nearOrthogonalDirection,
  { min: 3, max: 3 },
  { min: 4, max: 6 }
);
assert.equal(fixedFirstProjection.supported, true);
assert.equal(fixedFirstProjection.degenerateProjectionIntervals, 1);
assert.equal(fixedFirstProjection.distanceMethod, 'inverse-basis-segment');
assert.deepEqual(fixedFirstProjection.distanceWork, {
  edgeDistanceEvaluations: 1,
  cornerNormEvaluations: 2
});
const fixedFirstStart = expectedPoint(3, 4);
const fixedFirstEnd = expectedPoint(3, 6);
assert.ok(Math.abs(fixedFirstProjection.minimumDistance - radius(fixedFirstStart)) < 1e-12,
  'one collapsed projection interval must preserve the segment minimum radius');
assert.ok(Math.abs(fixedFirstProjection.maximumDistance - radius(fixedFirstEnd)) < 1e-12,
  'one collapsed projection interval must preserve the farthest endpoint radius');
assert.deepEqual(fixedFirstProjection.corners[0], fixedFirstProjection.corners[1],
  'the full evidence corners may retain duplicated vertices for the collapsed projection edge');
assert.deepEqual(fixedFirstProjection.corners[2], fixedFirstProjection.corners[3]);

const fixedSecondProjection = Envelope.analyze(
  { x: 1, y: 0 },
  nearOrthogonalDirection,
  { min: 3, max: 5 },
  { min: 4, max: 4 }
);
assert.equal(fixedSecondProjection.supported, true);
assert.equal(fixedSecondProjection.degenerateProjectionIntervals, 1);
assert.equal(fixedSecondProjection.distanceMethod, 'inverse-basis-segment');
assert.deepEqual(fixedSecondProjection.distanceWork, {
  edgeDistanceEvaluations: 1,
  cornerNormEvaluations: 2
}, 'the symmetric collapsed-second-interval case must use the same bounded segment work');

const originContainedSegment = Envelope.analyze(
  { x: 1, y: 0 },
  nearOrthogonalDirection,
  { min: 0, max: 0 },
  { min: -4, max: 6 }
);
assert.equal(originContainedSegment.supported, true);
assert.equal(originContainedSegment.minimumDistance, 0,
  'a one-dimensional inverse-basis envelope containing projection zero contains world-space origin exactly');
assert.equal(originContainedSegment.distanceMethod, 'inverse-basis-segment-origin-contained');
assert.deepEqual(originContainedSegment.distanceWork, {
  edgeDistanceEvaluations: 0,
  cornerNormEvaluations: 2
}, 'origin-contained segments need no edge-distance evaluation and only two endpoint norms');

const pointEnvelope = Envelope.analyze(
  { x: 1, y: 0 },
  nearOrthogonalDirection,
  { min: 3, max: 3 },
  { min: 4, max: 4 }
);
assert.equal(pointEnvelope.supported, true);
assert.equal(pointEnvelope.degenerateProjectionIntervals, 2);
assert.equal(pointEnvelope.distanceMethod, 'inverse-basis-point');
assert.deepEqual(pointEnvelope.distanceWork, {
  edgeDistanceEvaluations: 0,
  cornerNormEvaluations: 1
}, 'two collapsed projection intervals must evaluate their one unique inverse-basis point exactly once');
const expectedFixedPoint = expectedPoint(3, 4);
assert.ok(Math.abs(pointEnvelope.minimumDistance - radius(expectedFixedPoint)) < 1e-12,
  'two collapsed intervals must preserve the exact point radius as their minimum');
assert.equal(pointEnvelope.minimumDistance, pointEnvelope.maximumDistance,
  'a point envelope has identical minimum and maximum radius');
assert.deepEqual(pointEnvelope.corners[0], pointEnvelope.corners[1]);
assert.deepEqual(pointEnvelope.corners[0], pointEnvelope.corners[2]);
assert.deepEqual(pointEnvelope.corners[0], pointEnvelope.corners[3],
  'the evidence corners remain deterministic duplicates even though radial work uses one unique point');

const originPointEnvelope = Envelope.analyze(
  { x: 1, y: 0 },
  nearOrthogonalDirection,
  { min: 0, max: 0 },
  { min: 0, max: 0 }
);
assert.equal(originPointEnvelope.supported, true);
assert.equal(originPointEnvelope.originInsideProjectionRectangle, true);
assert.equal(originPointEnvelope.distanceMethod, 'inverse-basis-point');
assert.equal(originPointEnvelope.minimumDistance, 0);
assert.equal(originPointEnvelope.maximumDistance, 0);
assert.deepEqual(originPointEnvelope.distanceWork, {
  edgeDistanceEvaluations: 0,
  cornerNormEvaluations: 1
});

assert.deepEqual(
  Envelope.analyze(
    { x: 1, y: 0 },
    nearOrthogonalDirection,
    { min: 3, max: 3 },
    { min: 4, max: 6 }
  ),
  fixedFirstProjection,
  'degenerate segment evidence must replay deterministically'
);
assert.deepEqual(
  Envelope.analyze(
    { x: 1, y: 0 },
    nearOrthogonalDirection,
    { min: 3, max: 3 },
    { min: 4, max: 4 }
  ),
  pointEnvelope,
  'degenerate point evidence must replay deterministically'
);

console.log('one/two degenerate projection envelope selftest passed');
