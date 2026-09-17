'use strict';

const VERSION = '0.1.0';
const SCHEMA = 'axm.uc-two-projection-radial-envelope/v0.1';

function finiteDirection(direction) {
  return direction && Number.isFinite(direction.x) && Number.isFinite(direction.y);
}

function finiteInterval(interval) {
  return interval && Number.isFinite(interval.min) && Number.isFinite(interval.max);
}

function norm(point) {
  return Math.hypot(point.x, point.y);
}

function inverseProjectionPoint(firstDirection, secondDirection, firstProjection, secondProjection, determinant) {
  return {
    x: (firstProjection * secondDirection.y - firstDirection.y * secondProjection) / determinant,
    y: (firstDirection.x * secondProjection - firstProjection * secondDirection.x) / determinant
  };
}

function pointSegmentDistanceToOrigin(start, end) {
  const dx = end.x - start.x;
  const dy = end.y - start.y;
  const lengthSquared = dx * dx + dy * dy;
  if (!(lengthSquared > Number.EPSILON)) return norm(start);
  const unclamped = -(start.x * dx + start.y * dy) / lengthSquared;
  const t = Math.max(0, Math.min(1, unclamped));
  return Math.hypot(start.x + dx * t, start.y + dy * t);
}

function analyze(firstDirection, secondDirection, firstInterval, secondInterval) {
  if (!finiteDirection(firstDirection) || !finiteDirection(secondDirection)) {
    return {
      schema: SCHEMA,
      version: VERSION,
      supported: false,
      reason: 'NON_FINITE_DIRECTION'
    };
  }
  if (!finiteInterval(firstInterval) || !finiteInterval(secondInterval)) {
    return {
      schema: SCHEMA,
      version: VERSION,
      supported: false,
      reason: 'NON_FINITE_INTERVAL'
    };
  }

  const determinant = firstDirection.x * secondDirection.y - firstDirection.y * secondDirection.x;
  if (!Number.isFinite(determinant) || Math.abs(determinant) <= Number.EPSILON) {
    return {
      schema: SCHEMA,
      version: VERSION,
      supported: false,
      reason: 'SINGULAR_DIRECTION_PAIR',
      determinant
    };
  }

  const projectionCorners = [
    [firstInterval.min, secondInterval.min],
    [firstInterval.max, secondInterval.min],
    [firstInterval.max, secondInterval.max],
    [firstInterval.min, secondInterval.max]
  ];
  const corners = projectionCorners.map(pair => inverseProjectionPoint(
    firstDirection,
    secondDirection,
    pair[0],
    pair[1],
    determinant
  ));

  let minimumDistance = Infinity;
  for (let index = 0; index < corners.length; index += 1) {
    minimumDistance = Math.min(
      minimumDistance,
      pointSegmentDistanceToOrigin(corners[index], corners[(index + 1) % corners.length])
    );
  }

  const maximumDistance = corners.reduce((maximum, corner) => Math.max(maximum, norm(corner)), 0);
  const originInsideProjectionRectangle =
    firstInterval.min <= 0 && firstInterval.max >= 0 &&
    secondInterval.min <= 0 && secondInterval.max >= 0;
  if (originInsideProjectionRectangle) minimumDistance = 0;

  return {
    schema: SCHEMA,
    version: VERSION,
    supported: true,
    determinant,
    minimumDistance,
    maximumDistance,
    corners,
    evidence: [
      'The two finite signed projection intervals are mapped through the exact inverse 2D basis into one feasible parallelogram.',
      'Minimum radius is the exact distance from the origin to that finite parallelogram; maximum radius is the farthest corner distance.'
    ],
    limitations: [
      'This helper only handles two finite projection intervals and an invertible 2D direction pair.',
      'It does not decide whether directions are eligible for a stronger proof and does not combine more than two projections.',
      'It does not reason across body pairs, triangles, loops, convergence, stability, 3D physics or scientific validation.'
    ]
  };
}

module.exports = {
  VERSION,
  SCHEMA,
  analyze
};
