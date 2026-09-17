'use strict';

const assert = require('assert');
const Envelope = require('./uc-two-projection-radial-envelope.js');

const nearOrthogonalDirection = {
  x: 5e-7,
  y: Math.sqrt(1 - 25e-14)
};

function pointSegmentDistanceToOrigin(start, end) {
  const dx = end.x - start.x;
  const dy = end.y - start.y;
  const lengthSquared = dx * dx + dy * dy;
  if (lengthSquared === 0) return Math.hypot(start.x, start.y);
  const unclamped = -(start.x * dx + start.y * dy) / lengthSquared;
  const t = Math.max(0, Math.min(1, unclamped));
  return Math.hypot(start.x + dx * t, start.y + dy * t);
}

function allEdgeDistances(corners) {
  return corners.map((corner, index) =>
    pointSegmentDistanceToOrigin(corner, corners[(index + 1) % corners.length]));
}

function verifyTwoActiveEdges(firstInterval, secondInterval, expectedActiveEdges, label) {
  const result = Envelope.analyze(
    { x: 1, y: 0 },
    nearOrthogonalDirection,
    firstInterval,
    secondInterval
  );

  assert.equal(result.supported, true, `${label}: envelope should remain supported`);
  assert.equal(result.degenerateProjectionIntervals, 0, `${label}: test requires a non-degenerate rectangle`);
  assert.equal(result.zeroContainingProjectionIntervals, 0, `${label}: neither interval should contain zero`);
  assert.equal(result.originInsideProjectionRectangle, false, `${label}: origin must remain outside the rectangle`);
  assert.equal(result.distanceMethod, 'inverse-basis-parallelogram-two-active-edges');
  assert.deepEqual(result.distanceWork, {
    edgeDistanceEvaluations: 2,
    cornerNormEvaluations: 4
  }, `${label}: only the two nearest-to-zero projection boundaries should be scanned for radial minimum`);

  const edgeDistances = allEdgeDistances(result.corners);
  const fullFourEdgeMinimum = Math.min(...edgeDistances);
  const activeEdgeMinimum = Math.min(...expectedActiveEdges.map(index => edgeDistances[index]));

  assert.ok(Math.abs(result.minimumDistance - fullFourEdgeMinimum) < 1e-12,
    `${label}: two-edge result must match the authoritative four-edge minimum`);
  assert.ok(Math.abs(result.minimumDistance - activeEdgeMinimum) < 1e-12,
    `${label}: radial minimum must lie on one of the two nearest-to-zero projection boundaries`);

  return result;
}

const positive = verifyTwoActiveEdges(
  { min: 2, max: 5 },
  { min: 3, max: 7 },
  [3, 0],
  'positive/positive intervals'
);

verifyTwoActiveEdges(
  { min: -8, max: -2 },
  { min: -9, max: -4 },
  [1, 2],
  'negative/negative intervals'
);

verifyTwoActiveEdges(
  { min: -8, max: -2 },
  { min: 4, max: 9 },
  [1, 0],
  'mixed-sign one-sided intervals'
);

assert.deepEqual(
  Envelope.analyze(
    { x: 1, y: 0 },
    nearOrthogonalDirection,
    { min: 2, max: 5 },
    { min: 3, max: 7 }
  ),
  positive,
  'two-active-edge evidence must replay deterministically'
);

console.log('two active edge projection envelope selftest passed');
