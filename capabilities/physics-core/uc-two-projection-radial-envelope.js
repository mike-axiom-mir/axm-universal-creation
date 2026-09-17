'use strict';

const VERSION = '0.1.14';
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

function intervalIsExactlyOriginSymmetric(interval) {
  return interval.min === -interval.max;
}

function finitePoint(point) {
  return point && Number.isFinite(point.x) && Number.isFinite(point.y);
}

function copyPoint(point) {
  return { x: point.x, y: point.y };
}

function norm(point) {
  return Math.hypot(point.x, point.y);
}

function directionNorm(direction) {
  return Math.hypot(direction.x, direction.y);
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

function fartherAbsoluteEndpoint(interval) {
  if (Math.abs(interval.min) >= Math.abs(interval.max)) {
    return { value: interval.min, usesMin: true };
  }
  return { value: interval.max, usesMin: false };
}

function originSymmetricMaximumCornerIndex(firstInterval, secondInterval, representedDot) {
  if (!Number.isFinite(representedDot) || representedDot === 0) return null;

  const firstSymmetric = intervalIsExactlyOriginSymmetric(firstInterval);
  const secondSymmetric = intervalIsExactlyOriginSymmetric(secondInterval);
  if (!firstSymmetric && !secondSymmetric) return null;

  // If A has the two projection directions as rows, the inverse-basis
  // column cross term is -(firstDirection dot secondDirection) / det(A)^2.
  // Exact origin symmetry lets us select the sign of the symmetric
  // projection coordinate that maximizes that cross term.
  const inverseCrossSign = representedDot > 0 ? -1 : 1;

  if (firstSymmetric) {
    const secondEndpoint = fartherAbsoluteEndpoint(secondInterval);
    const secondSign = secondEndpoint.value < 0 ? -1 : 1;
    const desiredFirstSign = inverseCrossSign * secondSign;
    const firstUsesMin = desiredFirstSign < 0;

    if (secondEndpoint.usesMin) return firstUsesMin ? 0 : 1;
    return firstUsesMin ? 3 : 2;
  }

  const firstEndpoint = fartherAbsoluteEndpoint(firstInterval);
  const firstSign = firstEndpoint.value < 0 ? -1 : 1;
  const desiredSecondSign = inverseCrossSign * firstSign;
  const secondUsesMin = desiredSecondSign < 0;

  if (firstEndpoint.usesMin) return secondUsesMin ? 0 : 3;
  return secondUsesMin ? 1 : 2;
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
  const representedDot = dot(firstDirection, secondDirection);
  const firstDirectionNorm = directionNorm(firstDirection);
  const secondDirectionNorm = directionNorm(secondDirection);
  const scaledOrthogonalFastPath =
    !orthonormalFastPath &&
    representedDot === 0 &&
    Number.isFinite(firstDirectionNorm) &&
    Number.isFinite(secondDirectionNorm) &&
    firstDirectionNorm > 0 &&
    secondDirectionNorm > 0;
  const firstDegenerate = firstInterval.min === firstInterval.max;
  const secondDegenerate = secondInterval.min === secondInterval.max;
  const degenerateProjectionIntervals = Number(firstDegenerate) + Number(secondDegenerate);
  const firstContainsZero = intervalContainsZero(firstInterval);
  const secondContainsZero = intervalContainsZero(secondInterval);
  const zeroContainingProjectionIntervals = Number(firstContainsZero) + Number(secondContainsZero);
  const originInsideProjectionRectangle = firstContainsZero && secondContainsZero;
  const firstOriginSymmetric = intervalIsExactlyOriginSymmetric(firstInterval);
  const secondOriginSymmetric = intervalIsExactlyOriginSymmetric(secondInterval);
  const originSymmetricProjectionIntervals = Number(firstOriginSymmetric) + Number(secondOriginSymmetric);
  const centrallySymmetricProjectionRectangle = originSymmetricProjectionIntervals === 2;
  const exactOriginPoint =
    degenerateProjectionIntervals === 2 &&
    firstInterval.min === 0 &&
    secondInterval.min === 0;
  const originSymmetricSegmentThroughOrigin =
    degenerateProjectionIntervals === 1 &&
    originInsideProjectionRectangle &&
    (
      (firstDegenerate && firstInterval.min === 0 && secondOriginSymmetric) ||
      (secondDegenerate && secondInterval.min === 0 && firstOriginSymmetric)
    );
  const projectionCorners = [
    [firstInterval.min, secondInterval.min],
    [firstInterval.max, secondInterval.min],
    [firstInterval.max, secondInterval.max],
    [firstInterval.min, secondInterval.max]
  ];
  let projectionPointEvaluations = 0;
  const reconstructProjectionPoint = pair => {
    projectionPointEvaluations += 1;
    return orthonormalFastPath
      ? orthonormalProjectionPoint(firstDirection, secondDirection, pair[0], pair[1])
      : inverseProjectionPoint(firstDirection, secondDirection, pair[0], pair[1], determinant);
  };
  let corners;
  if (degenerateProjectionIntervals === 2) {
    const point = reconstructProjectionPoint(projectionCorners[0]);
    corners = [copyPoint(point), copyPoint(point), copyPoint(point), copyPoint(point)];
  } else if (firstDegenerate) {
    const start = reconstructProjectionPoint(projectionCorners[0]);
    const end = reconstructProjectionPoint(projectionCorners[2]);
    corners = [copyPoint(start), copyPoint(start), copyPoint(end), copyPoint(end)];
  } else if (secondDegenerate) {
    const start = reconstructProjectionPoint(projectionCorners[0]);
    const end = reconstructProjectionPoint(projectionCorners[1]);
    corners = [copyPoint(start), copyPoint(end), copyPoint(end), copyPoint(start)];
  } else if (centrallySymmetricProjectionRectangle) {
    const firstCorner = reconstructProjectionPoint(projectionCorners[0]);
    const secondCorner = reconstructProjectionPoint(projectionCorners[1]);
    corners = [
      copyPoint(firstCorner),
      copyPoint(secondCorner),
      { x: -firstCorner.x, y: -firstCorner.y },
      { x: -secondCorner.x, y: -secondCorner.y }
    ];
  } else {
    corners = projectionCorners.map(reconstructProjectionPoint);
  }
  const geometryWork = { projectionPointEvaluations };

  if (!corners.every(finitePoint)) {
    return unsupported('NON_FINITE_ENVELOPE_GEOMETRY', { determinant });
  }

  let minimumDistance;
  let maximumDistance;
  let distanceMethod;
  let distanceWork;
  let symmetricMaximumCornerIndex = null;

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
  } else if (scaledOrthogonalFastPath) {
    minimumDistance = Math.hypot(
      minimumAbsoluteInterval(firstInterval) / firstDirectionNorm,
      minimumAbsoluteInterval(secondInterval) / secondDirectionNorm
    );
    maximumDistance = Math.hypot(
      maximumAbsoluteInterval(firstInterval) / firstDirectionNorm,
      maximumAbsoluteInterval(secondInterval) / secondDirectionNorm
    );
    distanceMethod = 'orthogonal-scaled-projection-rectangle';
    distanceWork = {
      edgeDistanceEvaluations: 0,
      cornerNormEvaluations: 0
    };
  } else if (degenerateProjectionIntervals === 2) {
    if (exactOriginPoint) {
      minimumDistance = 0;
      maximumDistance = 0;
      distanceWork = {
        edgeDistanceEvaluations: 0,
        cornerNormEvaluations: 0
      };
    } else {
      const pointDistance = norm(corners[0]);
      if (!Number.isFinite(pointDistance)) {
        return unsupported('NON_FINITE_RADIAL_ENVELOPE', { determinant });
      }
      minimumDistance = pointDistance;
      maximumDistance = pointDistance;
      distanceWork = {
        edgeDistanceEvaluations: 0,
        cornerNormEvaluations: 1
      };
    }
    distanceMethod = 'inverse-basis-point';
  } else if (degenerateProjectionIntervals === 1) {
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

    let cornerNormEvaluations;
    if (originSymmetricSegmentThroughOrigin) {
      const endpointDistance = norm(start);
      if (!Number.isFinite(endpointDistance)) {
        return unsupported('NON_FINITE_RADIAL_ENVELOPE', { determinant });
      }
      maximumDistance = endpointDistance;
      cornerNormEvaluations = 1;
    } else {
      const startDistance = norm(start);
      const endDistance = norm(end);
      if (!Number.isFinite(startDistance) || !Number.isFinite(endDistance)) {
        return unsupported('NON_FINITE_RADIAL_ENVELOPE', { determinant });
      }
      maximumDistance = Math.max(startDistance, endDistance);
      cornerNormEvaluations = 2;
    }
    distanceMethod = originInsideProjectionRectangle
      ? 'inverse-basis-segment-origin-contained'
      : 'inverse-basis-segment';
    distanceWork = {
      edgeDistanceEvaluations: originInsideProjectionRectangle ? 0 : 1,
      cornerNormEvaluations
    };
  } else {
    if (originInsideProjectionRectangle) {
      minimumDistance = 0;
    } else if (zeroContainingProjectionIntervals === 1) {
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
      const firstNearestIsMin = Math.abs(firstInterval.min) <= Math.abs(firstInterval.max);
      const secondNearestIsMin = Math.abs(secondInterval.min) <= Math.abs(secondInterval.max);
      const firstEdgeStart = firstNearestIsMin ? corners[0] : corners[1];
      const firstEdgeEnd = firstNearestIsMin ? corners[3] : corners[2];
      const secondEdgeStart = secondNearestIsMin ? corners[0] : corners[3];
      const secondEdgeEnd = secondNearestIsMin ? corners[1] : corners[2];
      const firstEdgeDistance = pointSegmentDistanceToOrigin(firstEdgeStart, firstEdgeEnd);
      const secondEdgeDistance = pointSegmentDistanceToOrigin(secondEdgeStart, secondEdgeEnd);
      if (!Number.isFinite(firstEdgeDistance) || !Number.isFinite(secondEdgeDistance)) {
        return unsupported('NON_FINITE_RADIAL_ENVELOPE', { determinant });
      }
      minimumDistance = Math.min(firstEdgeDistance, secondEdgeDistance);
    }

    let cornerNormEvaluations;
    if (originSymmetricProjectionIntervals > 0) {
      symmetricMaximumCornerIndex = originSymmetricMaximumCornerIndex(
        firstInterval,
        secondInterval,
        representedDot
      );
    }

    if (symmetricMaximumCornerIndex !== null) {
      const selectedCornerDistance = norm(corners[symmetricMaximumCornerIndex]);
      if (!Number.isFinite(selectedCornerDistance)) {
        return unsupported('NON_FINITE_RADIAL_ENVELOPE', { determinant });
      }
      maximumDistance = selectedCornerDistance;
      cornerNormEvaluations = 1;
    } else if (centrallySymmetricProjectionRectangle) {
      const firstCornerDistance = norm(corners[0]);
      const secondCornerDistance = norm(corners[1]);
      if (!Number.isFinite(firstCornerDistance) || !Number.isFinite(secondCornerDistance)) {
        return unsupported('NON_FINITE_RADIAL_ENVELOPE', { determinant });
      }
      maximumDistance = Math.max(firstCornerDistance, secondCornerDistance);
      cornerNormEvaluations = 2;
    } else {
      const cornerDistances = corners.map(norm);
      if (!cornerDistances.every(Number.isFinite)) {
        return unsupported('NON_FINITE_RADIAL_ENVELOPE', { determinant });
      }
      maximumDistance = cornerDistances.reduce((maximum, distance) => Math.max(maximum, distance), 0);
      cornerNormEvaluations = corners.length;
    }

    distanceMethod = centrallySymmetricProjectionRectangle
      ? 'inverse-basis-parallelogram-origin-symmetric'
      : originInsideProjectionRectangle
        ? 'inverse-basis-parallelogram-origin-contained'
        : zeroContainingProjectionIntervals === 1
          ? 'inverse-basis-parallelogram-single-active-edge'
          : 'inverse-basis-parallelogram-two-active-edges';
    distanceWork = {
      edgeDistanceEvaluations: originInsideProjectionRectangle
        ? 0
        : zeroContainingProjectionIntervals === 1
          ? 1
          : 2,
      cornerNormEvaluations
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
    centrallySymmetricProjectionRectangle,
    exactOriginPoint,
    originSymmetricSegmentThroughOrigin,
    distanceMethod,
    distanceWork,
    geometryWork,
    evidence: [
      'The two finite non-empty signed projection intervals are mapped through the exact inverse 2D basis into one feasible affine envelope.',
      orthonormalFastPath
        ? 'An exactly orthonormal two-direction basis preserves Euclidean distance, so radial extrema come directly from the projection rectangle without edge-distance or corner-norm scans.'
        : scaledOrthogonalFastPath
          ? 'An exactly represented orthogonal two-direction basis with finite nonzero direction norms separates radial distance into scale-adjusted projection components, so radial extrema come directly from the projection rectangle without edge-distance or corner-norm scans.'
          : degenerateProjectionIntervals === 2
            ? exactOriginPoint
              ? 'Two exact zero projections define the world-space origin under any accepted invertible basis, so both radial extrema are exactly zero without a point-norm evaluation.'
              : 'Two exact projections define one feasible inverse-basis point, so radial minimum and maximum are the same single point norm.'
            : degenerateProjectionIntervals === 1
              ? originSymmetricSegmentThroughOrigin
                ? 'One exact zero projection plus one exactly origin-symmetric finite interval defines a segment through the world-space origin whose endpoints are negatives of each other, so radial minimum is zero and radial maximum needs only one endpoint norm.'
                : originInsideProjectionRectangle
                  ? 'One exact projection plus one finite interval defines a feasible segment containing the origin, so radial minimum is zero and radial maximum needs only the two endpoint norms.'
                  : 'One exact projection plus one finite interval defines a feasible segment, so radial minimum needs one point-to-segment evaluation and radial maximum needs only the two endpoint norms.'
              : centrallySymmetricProjectionRectangle
                ? 'Both projection intervals are exactly symmetric about zero, so the inverse-basis parallelogram is centrally symmetric and radial minimum is zero.'
                : originInsideProjectionRectangle
                  ? 'Both projection intervals contain zero, so linear inverse-basis geometry makes the world-space origin exactly feasible and radial minimum is zero without scanning parallelogram edges.'
                  : zeroContainingProjectionIntervals === 1
                    ? 'Exactly one projection interval contains zero; convex inverse-basis squared distance puts the radial minimum on the nearest boundary edge of the other one-sided interval, so only that active edge is evaluated.'
                    : 'Neither projection interval contains zero. Positive homogeneity of the linear inverse basis means any feasible point away from both nearest-to-zero projection boundaries can be scaled toward zero until one of those two boundaries is reached with strictly smaller radius, so only those two active edges can contain the radial minimum.',
      orthonormalFastPath
        ? 'Orthonormal corners are reconstructed through the transpose basis, avoiding determinant division on this exact common-case path.'
        : scaledOrthogonalFastPath
          ? 'The scale-adjusted orthogonal radial calculation uses represented direction norms; inverse-basis corners remain available as finite geometry evidence.'
          : 'Point-to-segment distance is evaluated after common coordinate scaling so finite large-magnitude geometry does not overflow merely because an edge delta is squared.',
      degenerateProjectionIntervals === 2
        ? exactOriginPoint
          ? 'The all-zero collapsed projection rectangle is recognized before radial norm work; deterministic corner evidence is still reconstructed and checked finite.'
          : 'A finite projection rectangle with two collapsed intervals is treated as its actual unique point instead of scanning four zero-length edges and four duplicate corners.'
        : degenerateProjectionIntervals === 1
          ? originSymmetricSegmentThroughOrigin
            ? 'Exact origin symmetry on the varying projection coordinate makes the two reconstructed segment endpoints negatives of each other, so their Euclidean norms are exactly equal and one endpoint norm is sufficient.'
            : 'A finite projection rectangle with exactly one collapsed interval is treated as its actual segment geometry instead of repeatedly scanning duplicate corners and collapsed edges.'
          : symmetricMaximumCornerIndex !== null
            ? 'At least one projection interval is exactly symmetric about zero. The inverse-basis quadratic cross-term sign selects the maximizing sign for that symmetric coordinate while the other coordinate uses its farther absolute endpoint, so one corner norm is sufficient for the exact radial maximum.'
            : centrallySymmetricProjectionRectangle
              ? 'Exact origin symmetry makes opposite world-space corners negatives of each other under the linear inverse basis, so only two unique corner norms are required when the represented cross-term sign is not finite and usable.'
              : zeroContainingProjectionIntervals === 1
                ? 'For a non-degenerate projection rectangle with exactly one zero-containing interval, only the nearest boundary edge of the other interval can contain the radial minimum; the other three edge scans are skipped.'
                : 'For a non-degenerate projection rectangle with neither interval containing zero, only the nearest-to-zero boundary edge from each projection axis can contain the radial minimum; the two farther boundary edges are skipped.',
      degenerateProjectionIntervals === 2
        ? 'Collapsed point envelopes reconstruct their one unique world-space point once and copy that deterministic value into the four evidence-corner slots.'
        : degenerateProjectionIntervals === 1
          ? 'Collapsed segment envelopes reconstruct only their two unique world-space endpoints and copy them into the duplicated evidence-corner slots.'
          : centrallySymmetricProjectionRectangle
            ? 'Non-degenerate exactly origin-symmetric envelopes reconstruct two adjacent world-space corners and derive the opposite pair by sign negation into independent evidence objects.'
            : 'Other non-degenerate envelopes retain four independent projection-to-world corner reconstructions.'
    ],
    limitations: [
      'This helper only handles two finite non-empty projection intervals and an invertible 2D direction pair.',
      'The orthonormal fast path requires exact represented unit norms and exact represented zero dot product.',
      'The scaled-orthogonal fast path requires an exact represented zero dot product plus finite nonzero represented direction norms; tolerance-accepted nonzero-dot pairs retain the inverse-basis geometry paths.',
      'Degenerate interval fast paths only reduce repeated work after the same two-direction inverse-basis geometry has already been accepted; one collapsed interval is a segment and two collapsed intervals are one point.',
      'The zero-work point shortcut requires both collapsed represented projection values to be exactly zero; the one-norm segment shortcut requires the collapsed projection to be exactly zero and the varying represented interval to be exactly symmetric about zero.',
      'The general 2D inverse-basis path may skip all edge-distance scans only when both signed intervals contain zero, because linear invertibility then makes world-space displacement zero exactly feasible.',
      'For a non-degenerate general envelope with exactly one zero-containing projection interval, only the nearest boundary edge of the other one-sided interval is evaluated for radial minimum.',
      'For a non-degenerate general envelope with neither interval containing zero, radial minimum is evaluated on exactly two edges: the boundary of each one-sided projection interval nearest zero. Positive homogeneity excludes the two farther edges from containing the minimum.',
      'The one-corner radial-maximum reduction requires at least one represented projection interval to be exactly symmetric about zero plus a finite nonzero represented direction dot product; merely near-symmetric intervals do not qualify.',
      '`geometryWork.projectionPointEvaluations` counts projection-to-world point reconstructions only; it does not claim fewer evidence-corner objects or fewer radial arithmetic operations.',
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