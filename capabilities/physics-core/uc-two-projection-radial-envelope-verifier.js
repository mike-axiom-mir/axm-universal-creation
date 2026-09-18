'use strict';

const VERSION = '0.1.2';
const SCHEMA = 'axm.uc-two-projection-radial-envelope-verifier/v0.1';

function finiteDirection(direction) {
  return direction && Number.isFinite(direction.x) && Number.isFinite(direction.y);
}

function finiteInterval(interval) {
  return interval && Number.isFinite(interval.min) && Number.isFinite(interval.max);
}

function orderedInterval(interval) {
  return interval.min <= interval.max;
}

function finitePoint(point) {
  return point && Number.isFinite(point.x) && Number.isFinite(point.y);
}

function dot(direction, point) {
  return direction.x * point.x + direction.y * point.y;
}

function norm(point) {
  return Math.hypot(point.x, point.y);
}

function intervalContainsZero(interval) {
  return interval.min <= 0 && interval.max >= 0;
}

function intervalIsExactlyOriginSymmetric(interval) {
  return interval.min === -interval.max;
}

function closeEnough(actual, expected, tolerance) {
  if (!Number.isFinite(actual) || !Number.isFinite(expected)) return false;
  const scale = Math.max(1, Math.abs(actual), Math.abs(expected));
  return Math.abs(actual - expected) <= tolerance * scale;
}

function inverseProjectionPoint(firstDirection, secondDirection, firstProjection, secondProjection, determinant) {
  return {
    x: (firstProjection * secondDirection.y - firstDirection.y * secondProjection) / determinant,
    y: (firstDirection.x * secondProjection - firstProjection * secondDirection.x) / determinant
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

function invalid(reason, extra) {
  return Object.assign({
    schema: SCHEMA,
    version: VERSION,
    verified: false,
    reason,
    violations: []
  }, extra || {});
}

function structuralReceiptExpectation(firstInterval, secondInterval) {
  const firstDegenerate = firstInterval.min === firstInterval.max;
  const secondDegenerate = secondInterval.min === secondInterval.max;
  const firstContainsZero = intervalContainsZero(firstInterval);
  const secondContainsZero = intervalContainsZero(secondInterval);
  const firstOriginSymmetric = intervalIsExactlyOriginSymmetric(firstInterval);
  const secondOriginSymmetric = intervalIsExactlyOriginSymmetric(secondInterval);
  const degenerateProjectionIntervals = Number(firstDegenerate) + Number(secondDegenerate);
  const zeroContainingProjectionIntervals = Number(firstContainsZero) + Number(secondContainsZero);
  const originInsideProjectionRectangle = firstContainsZero && secondContainsZero;
  const centrallySymmetricProjectionRectangle = firstOriginSymmetric && secondOriginSymmetric;
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

  return {
    degenerateProjectionIntervals,
    zeroContainingProjectionIntervals,
    originInsideProjectionRectangle,
    centrallySymmetricProjectionRectangle,
    exactOriginPoint,
    originSymmetricSegmentThroughOrigin
  };
}

function verify(firstDirection, secondDirection, firstInterval, secondInterval, analysis, options) {
  const tolerance = options && options.numericTolerance !== undefined
    ? options.numericTolerance
    : 1e-9;

  if (!Number.isFinite(tolerance) || tolerance < 0) {
    return invalid('INVALID_NUMERIC_TOLERANCE', { numericTolerance: tolerance });
  }
  if (!finiteDirection(firstDirection) || !finiteDirection(secondDirection)) {
    return invalid('INVALID_DIRECTION_INPUT');
  }
  if (!finiteInterval(firstInterval) || !finiteInterval(secondInterval)) {
    return invalid('INVALID_INTERVAL_INPUT');
  }
  if (!orderedInterval(firstInterval) || !orderedInterval(secondInterval)) {
    return invalid('EMPTY_PROJECTION_INTERVAL', {
      emptyIntervals: [
        firstInterval.min > firstInterval.max,
        secondInterval.min > secondInterval.max
      ]
    });
  }

  const determinant =
    firstDirection.x * secondDirection.y -
    firstDirection.y * secondDirection.x;
  if (!Number.isFinite(determinant) || Math.abs(determinant) <= Number.EPSILON) {
    return invalid('SINGULAR_DIRECTION_PAIR', { determinant });
  }

  if (!analysis || analysis.supported !== true) {
    return invalid('ANALYSIS_NOT_SUPPORTED');
  }
  if (!Array.isArray(analysis.corners) || analysis.corners.length !== 4 || !analysis.corners.every(finitePoint)) {
    return invalid('INVALID_CORNER_EVIDENCE');
  }
  if (!Number.isFinite(analysis.minimumDistance) || !Number.isFinite(analysis.maximumDistance)) {
    return invalid('INVALID_RADIAL_EVIDENCE');
  }

  const violations = [];
  const determinantMatches = closeEnough(analysis.determinant, determinant, tolerance);
  if (!determinantMatches) {
    violations.push('DETERMINANT_MISMATCH');
  }

  const structuralExpectation = structuralReceiptExpectation(firstInterval, secondInterval);
  const structuralChecks = Object.keys(structuralExpectation).map(field => ({
    field,
    actual: analysis[field],
    expected: structuralExpectation[field],
    matches: analysis[field] === structuralExpectation[field]
  }));
  if (structuralChecks.some(check => !check.matches)) {
    violations.push('STRUCTURAL_RECEIPT_MISMATCH');
  }

  const corners = analysis.corners;
  const cornerObjectIndependence = new Set(corners).size === corners.length;
  if (!cornerObjectIndependence) {
    violations.push('CORNER_EVIDENCE_ALIASING');
  }

  const projectionTargets = [
    [firstInterval.min, secondInterval.min],
    [firstInterval.max, secondInterval.min],
    [firstInterval.max, secondInterval.max],
    [firstInterval.min, secondInterval.max]
  ];
  const projectionChecks = [];
  const reconstructionChecks = [];

  for (let index = 0; index < corners.length; index += 1) {
    const firstProjection = dot(firstDirection, corners[index]);
    const secondProjection = dot(secondDirection, corners[index]);
    const target = projectionTargets[index];
    const firstMatches = closeEnough(firstProjection, target[0], tolerance);
    const secondMatches = closeEnough(secondProjection, target[1], tolerance);
    projectionChecks.push({
      cornerIndex: index,
      firstProjection,
      secondProjection,
      expectedFirstProjection: target[0],
      expectedSecondProjection: target[1],
      firstMatches,
      secondMatches
    });
    if (!firstMatches || !secondMatches) {
      violations.push('CORNER_PROJECTION_MISMATCH');
    }

    const expectedCorner = inverseProjectionPoint(
      firstDirection,
      secondDirection,
      target[0],
      target[1],
      determinant
    );
    const expectedCornerFinite = finitePoint(expectedCorner);
    const xMatches = expectedCornerFinite && closeEnough(corners[index].x, expectedCorner.x, tolerance);
    const yMatches = expectedCornerFinite && closeEnough(corners[index].y, expectedCorner.y, tolerance);
    reconstructionChecks.push({
      cornerIndex: index,
      actualX: corners[index].x,
      actualY: corners[index].y,
      expectedX: expectedCorner.x,
      expectedY: expectedCorner.y,
      expectedCornerFinite,
      xMatches,
      yMatches
    });
    if (!expectedCornerFinite) {
      violations.push('NON_FINITE_RECONSTRUCTED_CORNER');
    } else if (!xMatches || !yMatches) {
      violations.push('CORNER_RECONSTRUCTION_MISMATCH');
    }
  }

  const cornerNorms = corners.map(norm);
  if (!cornerNorms.every(Number.isFinite)) {
    violations.push('NON_FINITE_CORNER_NORM');
  }
  const expectedMaximumDistance = cornerNorms.reduce(
    (maximum, distance) => Math.max(maximum, distance),
    0
  );

  let expectedMinimumDistance;
  if (intervalContainsZero(firstInterval) && intervalContainsZero(secondInterval)) {
    expectedMinimumDistance = 0;
  } else {
    const edgeDistances = [
      pointSegmentDistanceToOrigin(corners[0], corners[1]),
      pointSegmentDistanceToOrigin(corners[1], corners[2]),
      pointSegmentDistanceToOrigin(corners[2], corners[3]),
      pointSegmentDistanceToOrigin(corners[3], corners[0])
    ];
    expectedMinimumDistance = edgeDistances.reduce(
      (minimum, distance) => Math.min(minimum, distance),
      Infinity
    );
  }

  if (!Number.isFinite(expectedMinimumDistance) || !Number.isFinite(expectedMaximumDistance)) {
    violations.push('NON_FINITE_INDEPENDENT_RADIAL_CHECK');
  } else {
    if (!closeEnough(analysis.minimumDistance, expectedMinimumDistance, tolerance)) {
      violations.push('MINIMUM_DISTANCE_MISMATCH');
    }
    if (!closeEnough(analysis.maximumDistance, expectedMaximumDistance, tolerance)) {
      violations.push('MAXIMUM_DISTANCE_MISMATCH');
    }
    if (analysis.minimumDistance > analysis.maximumDistance &&
        !closeEnough(analysis.minimumDistance, analysis.maximumDistance, tolerance)) {
      violations.push('RADIAL_ORDER_MISMATCH');
    }
  }

  const uniqueViolations = Array.from(new Set(violations));
  return {
    schema: SCHEMA,
    version: VERSION,
    verified: uniqueViolations.length === 0,
    reason: uniqueViolations.length === 0 ? null : 'RECEIPT_INCONSISTENT',
    numericTolerance: tolerance,
    determinant,
    determinantMatches,
    structuralChecks,
    cornerObjectIndependence,
    reconstructionChecks,
    expectedMinimumDistance,
    expectedMaximumDistance,
    projectionChecks,
    violations: uniqueViolations,
    evidence: [
      'Verifier inputs are first required to be finite, interval-ordered, and represented by a finite non-singular 2D direction pair; this is a verifier precondition only and does not decide the caller orthogonality eligibility boundary.',
      'The represented direction determinant and interval-derived structural receipt flags are recomputed independently before geometry evidence is trusted.',
      'All four corner evidence objects must remain identity-distinct, including point and segment envelopes whose coordinate values legitimately repeat.',
      'Each expected world-space corner is independently reconstructed from its projection endpoint pair through the represented 2D inverse basis and compared directly with the returned corner coordinates.',
      'Corner projections are also checked against the four represented interval endpoint pairs returned by the existing two-projection envelope contract.',
      'Radial minimum is recomputed from the world-space origin against all four returned boundary segments, except that two zero-containing projection intervals make the origin exactly feasible.',
      'Radial maximum is recomputed from all four returned corner norms rather than trusting any optimized fast-path work receipt.',
      'This verifier checks deterministic internal consistency only; it does not decide direction eligibility or certify physical correctness.'
    ],
    limitations: [
      'The verifier uses JavaScript Number inverse-basis reconstruction under a caller-selected numeric tolerance; sufficiently ill-conditioned but non-singular inputs can require a tolerance appropriate to their represented scale.',
      'Structural receipt checks cover determinant and interval-derived flags only; helper-internal work counters and optimization-method labels remain implementation evidence rather than independently reproduced execution traces.',
      'Agreement does not prove exact-arithmetic geometry, global satisfiability, convergence, stability, collision correctness, 3D physics, gameplay correctness, or scientific validation.',
      'Direction eligibility remains the responsibility of the existing caller proof boundary; this verifier must not be used to admit additional directions or body pairs.'
    ]
  };
}

module.exports = {
  VERSION,
  SCHEMA,
  verify
};
