'use strict';

const VERSION = '0.1.2';
const SCHEMA = 'axm.uc-two-projection-radial-envelope/v0.1';

function finiteDirection(direction) {
  return direction && Number.isFinite(direction.x) && Number.isFinite(direction.y);
}

function finiteInterval(interval) {
  return interval && Number.isFinite(interval.min) && Number.isFinite(interval.max);
}

function finitePoint(point) {
  return point && Number.isFinite(point.x) && Number.isFinite(point.y);
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
  // Scale the represented coordinates before the projection calculation. Squaring
  // a finite world-space delta directly can overflow even when the actual nearest
  // distance is finite (for example a 1e200-wide edge), which would otherwise turn
  // the segment parameter into Infinity / Infinity -> NaN.
  const scale = Math.max(
    Math.abs(start.x),
    Math.abs(start.y),
    Math.abs(end.x),
    Math.abs(end.y)
  );
  if (scale === 0) return 0;
  if (!Number.isFinite(scale)) return Infinity;

  const sx = start.x / scale;
  const sy = start.y / scale;
  const ex = end.x / scale;
  const ey = end.y / scale;
  const dx = ex - sx;
  const dy = ey - sy;
  const lengthSquared = dx * dx + dy * dy;

  // A short but non-zero represented edge remains real geometry. Only an exactly
  // collapsed edge is treated as a point after the common scaling step.
  if (lengthSquared === 0) return scale * Math.hypot(sx, sy);

  const unclamped = -(sx * dx + sy * dy) / lengthSquared;
  const t = Math.max(0, Math.min(1, unclamped));
  return scale * Math.hypot(sx + dx * t, sy + dy * t);
}

function unsupported(reason, extra) {
  return Object.assign({
    schema: SCHEMA,
    version: VERSION,
    supported: false,
    reason
  }, extra || {});
}

function analyze(firstDirection, secondDirection, firstInterval, secondInterval) {
  if (!finiteDirection(firstDirection) || !finiteDirection(secondDirection)) {
    return unsupported('NON_FINITE_DIRECTION');
  }
  if (!finiteInterval(firstInterval) || !finiteInterval(secondInterval)) {
    return unsupported('NON_FINITE_INTERVAL');
  }

  const determinant = firstDirection.x * secondDirection.y - firstDirection.y * secondDirection.x;
  if (!Number.isFinite(determinant) || Math.abs(determinant) <= Number.EPSILON) {
    return unsupported('SINGULAR_DIRECTION_PAIR', { determinant });
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

  if (!corners.every(finitePoint)) {
    return unsupported('NON_FINITE_ENVELOPE_GEOMETRY', { determinant });
  }

  let minimumDistance = Infinity;
  for (let index = 0; index < corners.length; index += 1) {
    const edgeDistance = pointSegmentDistanceToOrigin(corners[index], corners[(index + 1) % corners.length]);
    if (!Number.isFinite(edgeDistance)) {
      return unsupported('NON_FINITE_RADIAL_ENVELOPE', { determinant });
    }
    minimumDistance = Math.min(minimumDistance, edgeDistance);
  }

  const cornerDistances = corners.map(norm);
  if (!cornerDistances.every(Number.isFinite)) {
    return unsupported('NON_FINITE_RADIAL_ENVELOPE', { determinant });
  }
  const maximumDistance = cornerDistances.reduce((maximum, distance) => Math.max(maximum, distance), 0);
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
      'Minimum radius is the distance from the origin to that finite parallelogram; maximum radius is the farthest corner distance.',
      'Point-to-segment distance is evaluated after common coordinate scaling so finite large-magnitude geometry does not overflow merely because an edge delta is squared.',
      'Non-zero parallelogram edges are retained at their represented floating-point length rather than collapsed by an epsilon-length heuristic.'
    ],
    limitations: [
      'This helper only handles two finite projection intervals and an invertible 2D direction pair.',
      'It does not decide whether directions are eligible for a stronger proof and does not combine more than two projections.',
      'It uses JavaScript Number arithmetic; geometry whose represented inverse-basis points or radial distances are non-finite is declined so the caller can use its conservative fallback.',
      'The caller must retain a proof tolerance for contradiction decisions.',
      'It does not reason across body pairs, triangles, loops, convergence, stability, 3D physics or scientific validation.'
    ]
  };
}

module.exports = {
  VERSION,
  SCHEMA,
  analyze
};
