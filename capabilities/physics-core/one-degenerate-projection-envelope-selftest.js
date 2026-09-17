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
assert.equal(fixedFirstProjection.originSymmetricSegmentThroughOrigin, false);
assert.deepEqual(fixedFirstProjection.distanceWork, {
  edgeDistanceEvaluations: 1,
  cornerNormEvaluations: 2
});
assert.deepEqual(fixedFirstProjection.geometryWork, {
  projectionPointEvaluations: 2
}, 'a collapsed first projection should reconstruct only the two unique segment endpoints');
const fixedFirstStart = expectedPoint(3, 4);
const fixedFirstEnd = expectedPoint(3, 6);
assert.ok(Math.abs(fixedFirstProjection.minimumDistance - radius(fixedFirstStart)) < 1e-12,
  'one collapsed projection interval must preserve the segment minimum radius');
assert.ok(Math.abs(fixedFirstProjection.maximumDistance - radius(fixedFirstEnd)) < 1e-12,
  'one collapsed projection interval must preserve the farthest endpoint radius');
assert.deepEqual(fixedFirstProjection.corners[0], fixedFirstProjection.corners[1],
  'the full evidence corners may retain duplicated vertices for the collapsed projection edge');
assert.deepEqual(fixedFirstProjection.corners[2], fixedFirstProjection.corners[3]);
assert.notStrictEqual(fixedFirstProjection.corners[0], fixedFirstProjection.corners[1],
  'duplicated evidence-corner values should remain independent objects for caller mutation safety');

const fixedSecondProjection = Envelope.analyze(
  { x: 1, y: 0 },
  nearOrthogonalDirection,
  { min: 3, max: 5 },
  { min: 4, max: 4 }
);
assert.equal(fixedSecondProjection.supported, true);
assert.equal(fixedSecondProjection.degenerateProjectionIntervals, 1);
assert.equal(fixedSecondProjection.distanceMethod, 'inverse-basis-segment');
assert.equal(fixedSecondProjection.originSymmetricSegmentThroughOrigin, false);
assert.deepEqual(fixedSecondProjection.distanceWork, {
  edgeDistanceEvaluations: 1,
  cornerNormEvaluations: 2
}, 'the collapsed-second-interval case must use the same bounded segment work');
assert.deepEqual(fixedSecondProjection.geometryWork, {
  projectionPointEvaluations: 2
}, 'the reconstruction reduction must be orientation-independent');
assert.deepEqual(fixedSecondProjection.corners[0], fixedSecondProjection.corners[3]);
assert.deepEqual(fixedSecondProjection.corners[1], fixedSecondProjection.corners[2]);
assert.notStrictEqual(fixedSecondProjection.corners[0], fixedSecondProjection.corners[3]);

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
assert.equal(originContainedSegment.originSymmetricSegmentThroughOrigin, false,
  'a merely zero-containing varying interval must not be treated as exactly origin-symmetric');
assert.deepEqual(originContainedSegment.distanceWork, {
  edgeDistanceEvaluations: 0,
  cornerNormEvaluations: 2
}, 'a non-symmetric origin-contained segment still needs both endpoint norms for the radial maximum');
assert.deepEqual(originContainedSegment.geometryWork, {
  projectionPointEvaluations: 2
});

const symmetricOriginSegmentFixedFirst = Envelope.analyze(
  { x: 1, y: 0 },
  nearOrthogonalDirection,
  { min: 0, max: 0 },
  { min: -5, max: 5 }
);
assert.equal(symmetricOriginSegmentFixedFirst.supported, true);
assert.equal(symmetricOriginSegmentFixedFirst.minimumDistance, 0);
assert.equal(symmetricOriginSegmentFixedFirst.originSymmetricSegmentThroughOrigin, true,
  'an exact zero first projection plus an exactly symmetric second interval should identify a segment through the origin');
assert.equal(symmetricOriginSegmentFixedFirst.distanceMethod, 'inverse-basis-segment-origin-contained');
assert.deepEqual(symmetricOriginSegmentFixedFirst.distanceWork, {
  edgeDistanceEvaluations: 0,
  cornerNormEvaluations: 1
}, 'opposite segment endpoints have equal radius, so one endpoint norm must be sufficient');
assert.deepEqual(symmetricOriginSegmentFixedFirst.geometryWork, {
  projectionPointEvaluations: 2
});
assert.ok(Math.abs(
  symmetricOriginSegmentFixedFirst.maximumDistance - radius(expectedPoint(0, 5))
) < 1e-12, 'one-norm shortcut must preserve the exact endpoint radius');
assert.ok(Math.abs(
  radius(symmetricOriginSegmentFixedFirst.corners[0]) -
  radius(symmetricOriginSegmentFixedFirst.corners[2])
) < 1e-12, 'reconstructed symmetric segment endpoints must have equal radius');

const symmetricOriginSegmentFixedSecond = Envelope.analyze(
  { x: 1, y: 0 },
  nearOrthogonalDirection,
  { min: -5, max: 5 },
  { min: 0, max: 0 }
);
assert.equal(symmetricOriginSegmentFixedSecond.supported, true);
assert.equal(symmetricOriginSegmentFixedSecond.minimumDistance, 0);
assert.equal(symmetricOriginSegmentFixedSecond.originSymmetricSegmentThroughOrigin, true,
  'the one-norm symmetric-segment shortcut must be orientation-independent');
assert.equal(symmetricOriginSegmentFixedSecond.distanceMethod, 'inverse-basis-segment-origin-contained');
assert.deepEqual(symmetricOriginSegmentFixedSecond.distanceWork, {
  edgeDistanceEvaluations: 0,
  cornerNormEvaluations: 1
});
assert.deepEqual(symmetricOriginSegmentFixedSecond.geometryWork, {
  projectionPointEvaluations: 2
});
assert.ok(Math.abs(
  radius(symmetricOriginSegmentFixedSecond.corners[0]) -
  radius(symmetricOriginSegmentFixedSecond.corners[1])
) < 1e-12, 'opposite endpoints remain equal-radius when the second projection is the collapsed zero coordinate');

const pointEnvelope = Envelope.analyze(
  { x: 1, y: 0 },
  nearOrthogonalDirection,
  { min: 3, max: 3 },
  { min: 4, max: 4 }
);
assert.equal(pointEnvelope.supported, true);
assert.equal(pointEnvelope.degenerateProjectionIntervals, 2);
assert.equal(pointEnvelope.exactOriginPoint, false);
assert.equal(pointEnvelope.distanceMethod, 'inverse-basis-point');
assert.deepEqual(pointEnvelope.distanceWork, {
  edgeDistanceEvaluations: 0,
  cornerNormEvaluations: 1
}, 'two nonzero collapsed projection intervals must evaluate their one unique inverse-basis point exactly once');
assert.deepEqual(pointEnvelope.geometryWork, {
  projectionPointEvaluations: 1
}, 'a point envelope should reconstruct its unique world-space point only once');
const expectedFixedPoint = expectedPoint(3, 4);
assert.ok(Math.abs(pointEnvelope.minimumDistance - radius(expectedFixedPoint)) < 1e-12,
  'two collapsed intervals must preserve the exact point radius as their minimum');
assert.equal(pointEnvelope.minimumDistance, pointEnvelope.maximumDistance,
  'a point envelope has identical minimum and maximum radius');
assert.deepEqual(pointEnvelope.corners[0], pointEnvelope.corners[1]);
assert.deepEqual(pointEnvelope.corners[0], pointEnvelope.corners[2]);
assert.deepEqual(pointEnvelope.corners[0], pointEnvelope.corners[3],
  'the evidence corners remain deterministic duplicates even though radial work uses one unique point');
assert.notStrictEqual(pointEnvelope.corners[0], pointEnvelope.corners[1],
  'copied point evidence must preserve independent corner objects');

const originPointEnvelope = Envelope.analyze(
  { x: 1, y: 0 },
  nearOrthogonalDirection,
  { min: 0, max: 0 },
  { min: 0, max: 0 }
);
assert.equal(originPointEnvelope.supported, true);
assert.equal(originPointEnvelope.originInsideProjectionRectangle, true);
assert.equal(originPointEnvelope.exactOriginPoint, true,
  'two exact zero projections must identify the unique world-space origin point');
assert.equal(originPointEnvelope.distanceMethod, 'inverse-basis-point');
assert.equal(originPointEnvelope.minimumDistance, 0);
assert.equal(originPointEnvelope.maximumDistance, 0);
assert.deepEqual(originPointEnvelope.distanceWork, {
  edgeDistanceEvaluations: 0,
  cornerNormEvaluations: 0
}, 'the exact origin point needs no radial norm evaluation');
assert.deepEqual(originPointEnvelope.geometryWork, {
  projectionPointEvaluations: 1
}, 'exact origin evidence still needs only one projection-to-world reconstruction');

const fullRectangleEnvelope = Envelope.analyze(
  { x: 1, y: 0 },
  nearOrthogonalDirection,
  { min: 3, max: 5 },
  { min: 4, max: 6 }
);
assert.equal(fullRectangleEnvelope.supported, true);
assert.deepEqual(fullRectangleEnvelope.geometryWork, {
  projectionPointEvaluations: 4
}, 'non-degenerate envelopes retain four independent corner reconstructions');

const orthonormalPointEnvelope = Envelope.analyze(
  { x: 1, y: 0 },
  { x: 0, y: 1 },
  { min: 2, max: 2 },
  { min: 3, max: 3 }
);
assert.equal(orthonormalPointEnvelope.supported, true);
assert.equal(orthonormalPointEnvelope.distanceMethod, 'orthonormal-projection-rectangle');
assert.deepEqual(orthonormalPointEnvelope.geometryWork, {
  projectionPointEvaluations: 1
}, 'degenerate evidence reconstruction should also avoid duplicate transpose-basis evaluations');
assert.deepEqual(orthonormalPointEnvelope.corners, [
  { x: 2, y: 3 },
  { x: 2, y: 3 },
  { x: 2, y: 3 },
  { x: 2, y: 3 }
]);

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
    { min: 0, max: 0 },
    { min: -5, max: 5 }
  ),
  symmetricOriginSegmentFixedFirst,
  'origin-symmetric segment evidence must replay deterministically'
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
assert.deepEqual(
  Envelope.analyze(
    { x: 1, y: 0 },
    nearOrthogonalDirection,
    { min: 0, max: 0 },
    { min: 0, max: 0 }
  ),
  originPointEnvelope,
  'exact-origin point evidence must replay deterministically'
);

console.log('one/two degenerate projection envelope selftest passed');
