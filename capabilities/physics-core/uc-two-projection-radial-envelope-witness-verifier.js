'use strict';

const BaseVerifier = require('./uc-two-projection-radial-envelope-verifier.js');

const VERSION = '0.1.0';
const SCHEMA = 'axm.uc-two-projection-radial-envelope-witness-verifier/v0.1';
const WITNESS_SCHEMA = 'axm.uc-two-projection-radial-envelope-witness/v0.1';
const WITNESS_VERSION = '0.1.0';

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

function pointWithinInterval(value, interval, tolerance) {
  if (!Number.isFinite(value)) return false;
  const scale = Math.max(1, Math.abs(value), Math.abs(interval.min), Math.abs(interval.max));
  const slack = tolerance * scale;
  return value >= interval.min - slack && value <= interval.max + slack;
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

function invalid(reason, extra) {
  return Object.assign({
    schema: SCHEMA,
    version: VERSION,
    verified: false,
    reason,
    violations: []
  }, extra || {});
}

function verify(firstDirection, secondDirection, firstInterval, secondInterval, analysis, witnessReceipt, options) {
  const tolerance = options && options.numericTolerance !== undefined
    ? options.numericTolerance
    : 1e-9;

  if (!Number.isFinite(tolerance) || tolerance < 0) {
    return invalid('INVALID_NUMERIC_TOLERANCE', { numericTolerance: tolerance });
  }

  const baseReceipt = BaseVerifier.verify(
    firstDirection,
    secondDirection,
    firstInterval,
    secondInterval,
    analysis,
    { numericTolerance: tolerance }
  );

  if (!baseReceipt.verified) {
    return invalid('BASE_RECEIPT_NOT_VERIFIED', {
      numericTolerance: tolerance,
      baseReceipt
    });
  }

  if (!witnessReceipt || witnessReceipt.supported !== true || witnessReceipt.verified !== true) {
    return invalid('WITNESS_RECEIPT_NOT_SUPPORTED', {
      numericTolerance: tolerance,
      baseReceipt
    });
  }

  const violations = [];

  if (witnessReceipt.schema !== WITNESS_SCHEMA || witnessReceipt.version !== WITNESS_VERSION) {
    violations.push('WITNESS_SCHEMA_MISMATCH');
  }
  if (witnessReceipt.numericTolerance !== tolerance) {
    violations.push('NUMERIC_TOLERANCE_MISMATCH');
  }
  if (JSON.stringify(witnessReceipt.baseReceipt) !== JSON.stringify(baseReceipt)) {
    violations.push('EMBEDDED_BASE_RECEIPT_MISMATCH');
  }

  const minimumWitness = witnessReceipt.minimumWitness;
  const maximumWitness = witnessReceipt.maximumWitness;
  const minimumPointFinite = minimumWitness && finitePoint(minimumWitness.point);
  const maximumPointFinite = maximumWitness && finitePoint(maximumWitness.point);

  if (!minimumPointFinite || !Number.isFinite(minimumWitness.distance) || minimumWitness.distance < 0) {
    violations.push('INVALID_MINIMUM_WITNESS');
  }
  if (!maximumPointFinite || !Number.isFinite(maximumWitness.distance) || maximumWitness.distance < 0) {
    violations.push('INVALID_MAXIMUM_WITNESS');
  }

  const corners = analysis.corners;
  const edges = [
    [0, 1],
    [1, 2],
    [2, 3],
    [3, 0]
  ];

  let expectedMinimumWitness = null;
  if (minimumPointFinite) {
    if (intervalContainsZero(firstInterval) && intervalContainsZero(secondInterval)) {
      expectedMinimumWitness = {
        kind: 'origin',
        point: { x: 0, y: 0 },
        distance: 0,
        boundaryEdgeIndex: null,
        segmentParameter: null
      };

      if (minimumWitness.kind !== 'origin') violations.push('MINIMUM_KIND_MISMATCH');
      if (minimumWitness.point.x !== 0 || minimumWitness.point.y !== 0) {
        violations.push('MINIMUM_POINT_MISMATCH');
      }
      if (minimumWitness.distance !== 0) violations.push('MINIMUM_DISTANCE_MISMATCH');
      if (minimumWitness.boundaryEdgeIndex !== null || minimumWitness.segmentParameter !== null) {
        violations.push('MINIMUM_ORIGIN_METADATA_MISMATCH');
      }
    } else {
      const candidates = [];
      for (let edgeIndex = 0; edgeIndex < edges.length; edgeIndex += 1) {
        const edge = edges[edgeIndex];
        const candidate = closestPointOnSegmentToOrigin(corners[edge[0]], corners[edge[1]]);
        if (!candidate) {
          return invalid('NON_FINITE_INDEPENDENT_MINIMUM_WITNESS', {
            numericTolerance: tolerance,
            baseReceipt,
            boundaryEdgeIndex: edgeIndex
          });
        }
        candidates.push(Object.assign({ boundaryEdgeIndex: edgeIndex }, candidate));
      }

      let selected = candidates[0];
      for (let index = 1; index < candidates.length; index += 1) {
        if (candidates[index].distance < selected.distance) selected = candidates[index];
      }
      expectedMinimumWitness = {
        kind: 'boundary-segment',
        point: selected.point,
        distance: selected.distance,
        boundaryEdgeIndex: selected.boundaryEdgeIndex,
        segmentParameter: selected.segmentParameter
      };

      if (minimumWitness.kind !== 'boundary-segment') violations.push('MINIMUM_KIND_MISMATCH');
      if (minimumWitness.boundaryEdgeIndex !== selected.boundaryEdgeIndex) {
        violations.push('MINIMUM_EDGE_INDEX_MISMATCH');
      }
      if (!Number.isFinite(minimumWitness.segmentParameter) ||
          !closeEnough(minimumWitness.segmentParameter, selected.segmentParameter, tolerance)) {
        violations.push('MINIMUM_SEGMENT_PARAMETER_MISMATCH');
      }
      if (!closeEnough(minimumWitness.point.x, selected.point.x, tolerance) ||
          !closeEnough(minimumWitness.point.y, selected.point.y, tolerance)) {
        violations.push('MINIMUM_POINT_MISMATCH');
      }
      if (!closeEnough(minimumWitness.distance, selected.distance, tolerance)) {
        violations.push('MINIMUM_DISTANCE_MISMATCH');
      }
    }
  }

  let expectedMaximumWitness = null;
  if (maximumPointFinite) {
    let selectedCornerIndex = 0;
    let selectedCornerDistance = norm(corners[0]);
    for (let cornerIndex = 1; cornerIndex < corners.length; cornerIndex += 1) {
      const distance = norm(corners[cornerIndex]);
      if (distance > selectedCornerDistance) {
        selectedCornerDistance = distance;
        selectedCornerIndex = cornerIndex;
      }
    }

    expectedMaximumWitness = {
      kind: 'corner',
      point: {
        x: corners[selectedCornerIndex].x,
        y: corners[selectedCornerIndex].y
      },
      distance: selectedCornerDistance,
      cornerIndex: selectedCornerIndex
    };

    if (maximumWitness.kind !== 'corner') violations.push('MAXIMUM_KIND_MISMATCH');
    if (maximumWitness.cornerIndex !== selectedCornerIndex) {
      violations.push('MAXIMUM_CORNER_INDEX_MISMATCH');
    }
    if (!closeEnough(maximumWitness.point.x, corners[selectedCornerIndex].x, tolerance) ||
        !closeEnough(maximumWitness.point.y, corners[selectedCornerIndex].y, tolerance)) {
      violations.push('MAXIMUM_POINT_MISMATCH');
    }
    if (!closeEnough(maximumWitness.distance, selectedCornerDistance, tolerance)) {
      violations.push('MAXIMUM_DISTANCE_MISMATCH');
    }
  }

  const projectionChecks = {};
  if (minimumPointFinite) {
    const firstProjection = dot(firstDirection, minimumWitness.point);
    const secondProjection = dot(secondDirection, minimumWitness.point);
    const receiptProjections = witnessReceipt.minimumProjections;
    const receiptMatches = Boolean(receiptProjections) &&
      closeEnough(receiptProjections.first, firstProjection, tolerance) &&
      closeEnough(receiptProjections.second, secondProjection, tolerance);
    const feasible = pointWithinInterval(firstProjection, firstInterval, tolerance) &&
      pointWithinInterval(secondProjection, secondInterval, tolerance);
    projectionChecks.minimum = { firstProjection, secondProjection, receiptMatches, feasible };
    if (!receiptMatches) violations.push('MINIMUM_PROJECTION_RECEIPT_MISMATCH');
    if (!feasible) violations.push('MINIMUM_WITNESS_OUTSIDE_ENVELOPE');

    const pointDistance = norm(minimumWitness.point);
    if (!closeEnough(pointDistance, minimumWitness.distance, tolerance)) {
      violations.push('MINIMUM_POINT_DISTANCE_MISMATCH');
    }
    if (!closeEnough(minimumWitness.distance, analysis.minimumDistance, tolerance)) {
      violations.push('MINIMUM_ANALYSIS_DISTANCE_MISMATCH');
    }
  }

  if (maximumPointFinite) {
    const firstProjection = dot(firstDirection, maximumWitness.point);
    const secondProjection = dot(secondDirection, maximumWitness.point);
    const receiptProjections = witnessReceipt.maximumProjections;
    const receiptMatches = Boolean(receiptProjections) &&
      closeEnough(receiptProjections.first, firstProjection, tolerance) &&
      closeEnough(receiptProjections.second, secondProjection, tolerance);
    const feasible = pointWithinInterval(firstProjection, firstInterval, tolerance) &&
      pointWithinInterval(secondProjection, secondInterval, tolerance);
    projectionChecks.maximum = { firstProjection, secondProjection, receiptMatches, feasible };
    if (!receiptMatches) violations.push('MAXIMUM_PROJECTION_RECEIPT_MISMATCH');
    if (!feasible) violations.push('MAXIMUM_WITNESS_OUTSIDE_ENVELOPE');

    const pointDistance = norm(maximumWitness.point);
    if (!closeEnough(pointDistance, maximumWitness.distance, tolerance)) {
      violations.push('MAXIMUM_POINT_DISTANCE_MISMATCH');
    }
    if (!closeEnough(maximumWitness.distance, analysis.maximumDistance, tolerance)) {
      violations.push('MAXIMUM_ANALYSIS_DISTANCE_MISMATCH');
    }
  }

  const uniqueViolations = Array.from(new Set(violations));
  return {
    schema: SCHEMA,
    version: VERSION,
    verified: uniqueViolations.length === 0,
    reason: uniqueViolations.length === 0 ? null : 'WITNESS_RECEIPT_INCONSISTENT',
    numericTolerance: tolerance,
    baseReceipt,
    expectedMinimumWitness,
    expectedMaximumWitness,
    projectionChecks,
    violations: uniqueViolations,
    evidence: [
      'The generic radial-envelope receipt is independently reverified before witness evidence is trusted.',
      'The embedded base receipt must exactly match the newly recomputed generic receipt for the same represented inputs and tolerance.',
      'Non-origin minimum witnesses are independently recomputed from all four boundary segments with deterministic lowest-edge-index exact-tie selection.',
      'Origin-contained envelopes require the exact world-space origin witness and null boundary metadata.',
      'Maximum witnesses are independently recomputed from all four returned corner norms with deterministic lowest-corner-index exact-tie selection.',
      'Witness projections must remain feasible in both represented intervals, and stored projection evidence must match freshly recomputed projections.',
      'Witness point norms must agree with both their stored witness distances and the producer radial extrema under the caller-selected JavaScript Number tolerance.'
    ],
    limitations: [
      'This verifier checks deterministic internal witness consistency for the already-supported finite two-projection affine envelope only.',
      'The witnesses remain geometric radial extrema, not collision contacts, penetration vectors, impulses, solver guarantees, or physical-validation evidence.',
      'Direction eligibility remains the responsibility of the existing caller proof boundary and is not widened by witness verification.',
      'Agreement does not establish arbitrary-magnitude numerical stability, exact-arithmetic computational geometry, global satisfiability, convergence, stability, 3D physics, gameplay correctness, or scientific validation.'
    ]
  };
}

module.exports = {
  VERSION,
  SCHEMA,
  verify
};
