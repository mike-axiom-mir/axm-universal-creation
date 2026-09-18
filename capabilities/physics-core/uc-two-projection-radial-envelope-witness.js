'use strict';

const BaseVerifier = require('./uc-two-projection-radial-envelope-verifier.js');

const VERSION = '0.1.0';
const SCHEMA = 'axm.uc-two-projection-radial-envelope-witness/v0.1';

function finitePoint(point) {
  return point && Number.isFinite(point.x) && Number.isFinite(point.y);
}

function intervalContainsZero(interval) {
  return interval.min <= 0 && interval.max >= 0;
}

function dot(direction, point) {
  return direction.x * point.x + direction.y * point.y;
}

function norm(point) {
  return Math.hypot(point.x, point.y);
}

function closeEnough(actual, expected, tolerance) {
  if (!Number.isFinite(actual) || !Number.isFinite(expected)) return false;
  const scale = Math.max(1, Math.abs(actual), Math.abs(expected));
  return Math.abs(actual - expected) <= tolerance * scale;
}

function closestPointOnSegmentToOrigin(start, end) {
  const scale = Math.max(
    Math.abs(start.x),
    Math.abs(start.y),
    Math.abs(end.x),
    Math.abs(end.y)
  );

  if (!Number.isFinite(scale)) return null;
  if (scale === 0) {
    return {
      point: { x: 0, y: 0 },
      distance: 0,
      segmentParameter: 0
    };
  }

  const sx = start.x / scale;
  const sy = start.y / scale;
  const ex = end.x / scale;
  const ey = end.y / scale;
  const dx = ex - sx;
  const dy = ey - sy;
  const lengthSquared = dx * dx + dy * dy;

  let segmentParameter = 0;
  if (lengthSquared !== 0) {
    const unclamped = -(sx * dx + sy * dy) / lengthSquared;
    segmentParameter = Math.max(0, Math.min(1, unclamped));
  }

  const px = sx + dx * segmentParameter;
  const py = sy + dy * segmentParameter;
  const point = {
    x: px * scale,
    y: py * scale
  };
  const distance = scale * Math.hypot(px, py);

  if (!finitePoint(point) || !Number.isFinite(distance)) return null;

  return {
    point,
    distance,
    segmentParameter
  };
}

function unsupported(reason, extra) {
  return Object.assign({
    schema: SCHEMA,
    version: VERSION,
    supported: false,
    verified: false,
    reason
  }, extra || {});
}

function derive(firstDirection, secondDirection, firstInterval, secondInterval, analysis, options) {
  const tolerance = options && options.numericTolerance !== undefined
    ? options.numericTolerance
    : 1e-9;

  const baseReceipt = BaseVerifier.verify(
    firstDirection,
    secondDirection,
    firstInterval,
    secondInterval,
    analysis,
    { numericTolerance: tolerance }
  );

  if (!baseReceipt.verified) {
    return unsupported('BASE_RECEIPT_NOT_VERIFIED', {
      numericTolerance: tolerance,
      baseReceipt
    });
  }

  const corners = analysis.corners;
  const edges = [
    [0, 1],
    [1, 2],
    [2, 3],
    [3, 0]
  ];

  let minimumWitness;
  if (intervalContainsZero(firstInterval) && intervalContainsZero(secondInterval)) {
    minimumWitness = {
      kind: 'origin',
      point: { x: 0, y: 0 },
      distance: 0,
      boundaryEdgeIndex: null,
      segmentParameter: null
    };
  } else {
    let selected = null;
    for (let edgeIndex = 0; edgeIndex < edges.length; edgeIndex += 1) {
      const edge = edges[edgeIndex];
      const candidate = closestPointOnSegmentToOrigin(corners[edge[0]], corners[edge[1]]);
      if (!candidate) {
        return unsupported('NON_FINITE_MINIMUM_WITNESS', {
          numericTolerance: tolerance,
          baseReceipt,
          boundaryEdgeIndex: edgeIndex
        });
      }

      if (selected === null || candidate.distance < selected.distance) {
        selected = Object.assign({ boundaryEdgeIndex: edgeIndex }, candidate);
      }
    }

    minimumWitness = {
      kind: 'boundary-segment',
      point: selected.point,
      distance: selected.distance,
      boundaryEdgeIndex: selected.boundaryEdgeIndex,
      segmentParameter: selected.segmentParameter
    };
  }

  let maximumCornerIndex = 0;
  let maximumDistance = norm(corners[0]);
  if (!Number.isFinite(maximumDistance)) {
    return unsupported('NON_FINITE_MAXIMUM_WITNESS', {
      numericTolerance: tolerance,
      baseReceipt,
      cornerIndex: 0
    });
  }

  for (let cornerIndex = 1; cornerIndex < corners.length; cornerIndex += 1) {
    const distance = norm(corners[cornerIndex]);
    if (!Number.isFinite(distance)) {
      return unsupported('NON_FINITE_MAXIMUM_WITNESS', {
        numericTolerance: tolerance,
        baseReceipt,
        cornerIndex
      });
    }
    if (distance > maximumDistance) {
      maximumDistance = distance;
      maximumCornerIndex = cornerIndex;
    }
  }

  const maximumWitness = {
    kind: 'corner',
    point: {
      x: corners[maximumCornerIndex].x,
      y: corners[maximumCornerIndex].y
    },
    distance: maximumDistance,
    cornerIndex: maximumCornerIndex
  };

  const minimumDistanceMatches = closeEnough(
    minimumWitness.distance,
    analysis.minimumDistance,
    tolerance
  );
  const maximumDistanceMatches = closeEnough(
    maximumWitness.distance,
    analysis.maximumDistance,
    tolerance
  );

  if (!minimumDistanceMatches || !maximumDistanceMatches) {
    return unsupported('EXTREMUM_WITNESS_DISTANCE_MISMATCH', {
      numericTolerance: tolerance,
      baseReceipt,
      minimumWitness,
      maximumWitness,
      minimumDistanceMatches,
      maximumDistanceMatches
    });
  }

  const minimumProjections = {
    first: dot(firstDirection, minimumWitness.point),
    second: dot(secondDirection, minimumWitness.point)
  };
  const maximumProjections = {
    first: dot(firstDirection, maximumWitness.point),
    second: dot(secondDirection, maximumWitness.point)
  };

  if (!Number.isFinite(minimumProjections.first) ||
      !Number.isFinite(minimumProjections.second) ||
      !Number.isFinite(maximumProjections.first) ||
      !Number.isFinite(maximumProjections.second)) {
    return unsupported('NON_FINITE_WITNESS_PROJECTION', {
      numericTolerance: tolerance,
      baseReceipt
    });
  }

  return {
    schema: SCHEMA,
    version: VERSION,
    supported: true,
    verified: true,
    reason: null,
    numericTolerance: tolerance,
    minimumWitness,
    maximumWitness,
    minimumProjections,
    maximumProjections,
    baseReceipt,
    evidence: [
      'The existing generic radial-envelope receipt verifier must pass before extremum witnesses are derived.',
      'When both represented projection intervals contain zero, linear invertibility makes the world-space origin the exact radial-minimum witness.',
      'Otherwise the radial-minimum witness is recomputed generically from all four returned boundary segments with deterministic lowest-edge-index tie breaking.',
      'The radial-maximum witness is recomputed from all four returned evidence corners with deterministic lowest-corner-index tie breaking.',
      'Both witness distances must agree with the producer radial extrema under the caller-selected JavaScript Number tolerance.'
    ],
    limitations: [
      'These are geometric witnesses for the already-supported two-projection affine envelope, not collision contacts, impulses, penetration vectors, or physical-validation evidence.',
      'Direction eligibility remains the responsibility of the existing caller proof boundary; this helper must not be used to admit additional directions or body pairs.',
      'Witness selection is deterministic under represented JavaScript Number arithmetic; exact ties choose the lowest boundary-edge or corner index.',
      'Agreement does not establish arbitrary-magnitude numerical stability, exact-arithmetic computational geometry, global satisfiability, convergence, stability, 3D physics, gameplay correctness, or scientific validation.'
    ]
  };
}

module.exports = {
  VERSION,
  SCHEMA,
  derive
};
