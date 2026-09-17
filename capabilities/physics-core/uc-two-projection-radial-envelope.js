'use strict';

const VERSION = '0.1.8';
const SCHEMA = 'axm.uc-two-projection-radial-envelope/v0.1';

function finiteDirection(direction) {
  return direction && Number.isFinite(direction.x) && Number.isFinite(direction.y);
}

function finiteInterval(interval) {
  return interval && Number.isFinite(interval.min) && Number.isFinite(interval.max);
}

function orderedInterval(interval) {
  return interval.min <= interval.max;
}

function intervalContainsZero(interval) {
  return interval.min <= 0 && interval.max >= 0;
}

function finitePoint(point) {
  return point && Number.isFinite(point.x) && Number.isFinite(point.y);
}

function norm(point) {
  return Math.hypot(point.x, point.y);
}

function directionNormSquared(direction) {
  return direction.x * direction.x + direction.y * direction.y;
}

function dot(left, right) {
  return left.x * right.x + left.y * right.y;
}

function exactOrthonormalPair(firstDirection, secondDirection) {
  return directionNormSquared(firstDirection) === 1 &&
    directionNormSquared(secondDirection) === 1 &&
    dot(firstDirection, secondDirection) === 0;
}

function minimumAbsoluteInterval(interval) {
  if (intervalContainsZero(interval)) return 0;
  return Math.min(Math.abs(interval.min), Math.abs(interval.max));
}

function maximumAbsoluteInterval(interval) {
  return Math.max(Math.abs(interval.min), Math.abs(interval.max));
}

function inverseProjectionPoint(firstDirection, secondDirection, firstProjection, secondProjection, determinant) {
  return {
    x: (firstProjection * secondDirection.y - firstDirection.y * secondProjection) / determinant,
    y: (firstDirection.x * secondProjection - firstProjection * secondDirection.x) / determinant
  };
}

function orthonormalProjectionPoint(firstDirection, secondDirection, firstProjection, secondProjection) {
  return {
    x: firstProjection * firstDirection.x + secondProjection * secondDirection.x,
    y: firstProjection * firstDirection.y + secondProjection * secondDirection.y
  };
}

function pointSegmentDistanceToOrigin(start, end) {
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
  if (!orderedInterval(firstInterval) || !orderedInterval(secondInterval)) {
    return unsupported('EMPTY_PROJECTION_INTERVAL', {
      emptyIntervals: [
        firstInterval.min > firstInterval.max,
        secondInterval.min > secondInterval.max
      ]
    });
  }

  const determinant = firstDirection.x * secondDirection.y - firstDirection.y * secondDirection.x;
  if (!Number.isFinite(determinant) || Math.abs(determinant) <= Number.EPSILON) {
    return unsupported('SINGULAR_DIRECTION_PAIR', { determinant });
  }

  const orthonormalFastPath = exactOrthonormalPair(firstDirection, secondDirection);
  const firstDegenerate = firstInterval.min === firstInterval.max;
  const secondDegenerate = secondInterval.min === secondInterval.max;
  const degenerateProjectionIntervals = Number(firstDegenerate) + Number(secondDegenerate);
  const firstContainsZero = intervalContainsZero(firstInterval);
  const secondContainsZero = intervalContainsZero(secondInterval);
  const zeroContainingProjectionIntervals = Number(firstContainsZero) + Number(secondContainsZero);
  const originInsideProjectionRectangle = firstContainsZero && secondContainsZero;
  const projectionCorners = [
    [firstInterval.min, secondInterval.min],
    [firstInterval.max, secondInterval.min],
    [firstInterval.max, secondInterval.max],
    [firstInterval.min, secondInterval.max]
  ];
  const corners = projectionCorners.map(pair => orthonormalFastPath
    ? orthonormalProjectionPoint(firstDirection, secondDirection, pair[0], pair[1])
    : inverseProjectionPoint(firstDirection, secondDirection, pair[0], pair[1], determinant)
  );

  if (!corners.every(finitePoint)) {
    return unsupported('NON_FINITE_ENVELOPE_GEOMETRY', { determinant });
  }

  let minimumDistance;
  let maximumDistance;
  let distanceMethod;
  let distanceWork;

  if (orthonormalFastPath) {
    minimumDistance = Math.hypot(
      minimumAbsoluteInterval(firstInterval),
      minimumAbsoluteInterval(secondInterval)
    );
    maximumDistance = Math.hypot(
      maximumAbsoluteInterval(firstInterval),
      maximumAbsoluteInterval(secondInterval)
    );
    distanceMethod = 'orthonormal-projection-rectangle';
    distanceWork = {
      edgeDistanceEvaluations: 0,
      cornerNormEvaluations: 0
    };
  } else if (degenerateProjectionIntervals === 2) {
    // Two collapsed projection intervals define one exact inverse-basis point.
    // Evaluate that unique point once instead of scanning four zero-length edges
    // and four duplicate corners.
    const pointDistance = norm(corners[0]);
    if (!Number.isFinite(pointDistance)) {
      return unsupported('NON_FINITE_RADIAL_ENVELOPE', { determinant });
    }
    minimumDistance = pointDistance;
    maximumDistance = pointDistance;
    distanceMethod = 'inverse-basis-point';
    distanceWork = {
      edgeDistanceEvaluations: 0,
      cornerNormEvaluations: 1
    };
  } else if (degenerateProjectionIntervals === 1) {
    // Exactly one collapsed projection interval makes the feasible inverse-basis
    // envelope a segment rather than a 2D parallelogram. Use its two unique
    // endpoints directly instead of scanning four edges and four duplicate corners.
    const start = corners[0];
    const end = firstDegenerate ? corners[2] : corners[1];
    if (originInsideProjectionRectangle) {
      minimumDistance = 0;
    } else {
      minimumDistance = pointSegmentDistanceToOrigin(start, end);
      if (!Number.isFinite(minimumDistance)) {
        return unsupported('NON_FINITE_RADIAL_ENVELOPE', { determinant });
      }
    }

    const startDistance = norm(start);
    const endDistance = norm(end);
    if (!Number.isFinite(startDistance) || !Number.isFinite(endDistance)) {
      return unsupported('NON_FINITE_RADIAL_ENVELOPE', { determinant });
    }
    maximumDistance = Math.max(startDistance, endDistance);
    distanceMethod = originInsideProjectionRectangle
      ? 'inverse-basis-segment-origin-contained'
      : 'inverse-basis-segment';
    distanceWork = {
      edgeDistanceEvaluations: originInsideProjectionRectangle ? 0 : 1,
      cornerNormEvaluations: 2
    };
  } else {
    if (originInsideProjectionRectangle) {
      minimumDistance = 0;
    } else if (zeroContainingProjectionIntervals === 1) {
      // With exactly one projection interval containing zero, minimizing the
      // positive-definite inverse-basis distance over that coordinate leaves a
      // convex function of the other coordinate whose global minimum is at zero.
      // Because the other interval lies wholly on one side of zero, its nearest
      // feasible radius must therefore lie on that interval's boundary edge
      // closest to zero. Evaluate only that one active edge.
      let start;
      let end;
      if (firstContainsZero) {
        if (Math.abs(secondInterval.min) <= Math.abs(secondInterval.max)) {
          start = corners[0];
          end = corners[1];
        } else {
          start = corners[3];
          end = corners[2];
        }
      } else if (Math.abs(firstInterval.min) <= Math.abs(firstInterval.max)) {
        start = corners[0];
        end = corners[3];
      } else {
        start = corners[1];
        end = corners[2];
      }

      minimumDistance = pointSegmentDistanceToOrigin(start, end);
      if (!Number.isFinite(minimumDistance)) {
        return unsupported('NON_FINITE_RADIAL_ENVELOPE', { determinant });
      }
    } else {
      minimumDistance = Infinity;
      for (let index = 0; index < corners.length; index += 1) {
        const edgeDistance = pointSegmentDistanceToOrigin(corners[index], corners[(index + 1) % corners.length]);
        if (!Number.isFinite(edgeDistance)) {
          return unsupported('NON_FINITE_RADIAL_ENVELOPE', { determinant });
        }
        minimumDistance = Math.min(minimumDistance, edgeDistance);
      }
    }

    const cornerDistances = corners.map(norm);
    if (!cornerDistances.every(Number.isFinite)) {
      return unsupported('NON_FINITE_RADIAL_ENVELOPE', { determinant });
    }
    maximumDistance = cornerDistances.reduce((maximum, distance) => Math.max(maximum, distance), 0);
    distanceMethod = originInsideProjectionRectangle
      ? 'inverse-basis-parallelogram-origin-contained'
      : zeroContainingProjectionIntervals === 1
        ? 'inverse-basis-parallelogram-single-active-edge'
        : 'inverse-basis-parallelogram-edges';
    distanceWork = {
      edgeDistanceEvaluations: originInsideProjectionRectangle
        ? 0
        : zeroContainingProjectionIntervals === 1
          ? 1
          : corners.length,
      cornerNormEvaluations: corners.length
    };
  }

  if (!Number.isFinite(minimumDistance) || !Number.isFinite(maximumDistance)) {
    return unsupported('NON_FINITE_RADIAL_ENVELOPE', { determinant });
  }

  return {
    schema: SCHEMA,
    version: VERSION,
    supported: true,
    determinant,
    minimumDistance,
    maximumDistance,
    corners,
    degenerateProjectionIntervals,
    zeroContainingProjectionIntervals,
    originInsideProjectionRectangle,
    distanceMethod,
    distanceWork,
    evidence: [
      'The two finite non-empty signed projection intervals are mapped through the exact inverse 2D basis into one feasible affine envelope.',
      orthonormalFastPath
        ? 'An exactly orthonormal two-direction basis preserves Euclidean distance, so radial extrema come directly from the projection rectangle without edge-distance or corner-norm scans.'
        : degenerateProjectionIntervals === 2
          ? 'Two exact projections define one feasible inverse-basis point, so radial minimum and maximum are the same single point norm.'
          : degenerateProjectionIntervals === 1
            ? originInsideProjectionRectangle
              ? 'One exact projection plus one finite interval defines a feasible segment containing the origin, so radial minimum is zero and radial maximum needs only the two endpoint norms.'
              : 'One exact projection plus one finite interval defines a feasible segment, so radial minimum needs one point-to-segment evaluation and radial maximum needs only the two endpoint norms.'
            : originInsideProjectionRectangle
              ? 'Both projection intervals contain zero, so linear inverse-basis geometry makes the world-space origin exactly feasible and radial minimum is zero without scanning parallelogram edges.'
              : zeroContainingProjectionIntervals === 1
                ? 'Exactly one projection interval contains zero; convex inverse-basis squared distance puts the radial minimum on the nearest boundary edge of the other one-sided interval, so only that active edge is evaluated.'
                : 'Minimum radius is the distance from the origin to the finite parallelogram edges; maximum radius is the farthest corner distance.',
      orthonormalFastPath
        ? 'Orthonormal corners are reconstructed through the transpose basis, avoiding determinant division on this exact common-case path.'
        : 'Point-to-segment distance is evaluated after common coordinate scaling so finite large-magnitude geometry does not overflow merely because an edge delta is squared.',
      degenerateProjectionIntervals === 2
        ? 'A finite projection rectangle with two collapsed intervals is treated as its actual unique point instead of scanning four zero-length edges and four duplicate corners.'
        : degenerateProjectionIntervals === 1
          ? 'A finite projection rectangle with exactly one collapsed interval is treated as its actual segment geometry instead of repeatedly scanning duplicate corners and collapsed edges.'
          : zeroContainingProjectionIntervals === 1
            ? 'For a non-degenerate projection rectangle with exactly one zero-containing interval, only the nearest boundary edge of the other interval can contain the radial minimum; the other three edge scans are skipped.'
            : 'General non-degenerate envelopes retain the complete edge scan unless the origin is feasible or the single-active-edge proof applies.'
    ],
    limitations: [
      'This helper only handles two finite non-empty projection intervals and an invertible 2D direction pair.',
      'The orthonormal fast path requires exact represented unit norms and exact represented zero dot product; tolerance-accepted near-orthogonal pairs retain the inverse-basis geometry paths.',
      'Degenerate interval fast paths only reduce repeated work after the same two-direction inverse-basis geometry has already been accepted; one collapsed interval is a segment and two collapsed intervals are one point.',
      'The general 2D inverse-basis path may skip all edge-distance scans only when both signed intervals contain zero, because linear invertibility then makes world-space displacement zero exactly feasible.',
      'For a non-degenerate general envelope with exactly one zero-containing projection interval, only the nearest boundary edge of the other one-sided interval is evaluated for radial minimum; when neither interval contains zero, all four edges remain authoritative.',
      'A caller may tolerate a tiny interval gap under its own proof tolerance, but this exact-envelope helper declines min > max rather than manufacturing feasible geometry from an empty intersection.',
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
