'use strict';

const ActiveSetVerifier = require('./uc-two-projection-radial-envelope-active-set-verifier.js');

const VERSION = '0.1.0';
const SCHEMA = 'axm.uc-two-projection-radial-envelope-projection-margins-verifier/v0.1';
const PROJECTION_MARGINS_SCHEMA = 'axm.uc-two-projection-radial-envelope-projection-margins/v0.1';
const PROJECTION_MARGINS_VERSION = '0.1.0';

function closeEnough(actual, expected, tolerance) {
  if (!Number.isFinite(actual) || !Number.isFinite(expected)) return false;
  const scale = Math.max(1, Math.abs(actual), Math.abs(expected));
  return Math.abs(actual - expected) <= tolerance * scale;
}

function dot(direction, point) {
  return direction.x * point.x + direction.y * point.y;
}

function sameStringArray(actual, expected) {
  return Array.isArray(actual) &&
    actual.length === expected.length &&
    actual.every((value, index) => value === expected[index]);
}

function classifySides(projection, interval, tolerance) {
  const activeSides = [];
  if (closeEnough(projection, interval.min, tolerance)) activeSides.push('min');
  if (closeEnough(projection, interval.max, tolerance)) activeSides.push('max');
  return activeSides;
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

function deriveExpectedAxis(direction, point, interval, verifiedAxis, tolerance) {
  const projection = dot(direction, point);
  if (!Number.isFinite(projection)) {
    return { supported: false, reason: 'NON_FINITE_PROJECTION' };
  }

  const toMin = projection - interval.min;
  const toMax = interval.max - projection;
  const toleranceScale = Math.max(
    1,
    Math.abs(projection),
    Math.abs(interval.min),
    Math.abs(interval.max)
  );
  const toleranceBand = tolerance * toleranceScale;
  const activeSides = classifySides(projection, interval, tolerance);

  if (!Number.isFinite(toMin) || !Number.isFinite(toMax) || !Number.isFinite(toleranceBand)) {
    return { supported: false, reason: 'NON_FINITE_PROJECTION_MARGIN' };
  }

  if (toMin < -toleranceBand || toMax < -toleranceBand) {
    return {
      supported: false,
      reason: 'WITNESS_PROJECTION_OUTSIDE_INTERVAL',
      projection,
      toMin,
      toMax,
      toleranceBand
    };
  }

  if (!verifiedAxis || !sameStringArray(activeSides, verifiedAxis.activeSides)) {
    return {
      supported: false,
      reason: 'ACTIVE_SIDE_RECONSTRUCTION_MISMATCH',
      projection,
      activeSides,
      verifiedActiveSides: verifiedAxis && verifiedAxis.activeSides
    };
  }

  const exactDegenerateInterval = interval.min === interval.max;
  let classification = 'interior';
  if (exactDegenerateInterval) classification = 'degenerate-boundary';
  else if (activeSides.length > 0) classification = 'boundary';

  return {
    supported: true,
    projection,
    toMin,
    toMax,
    signedFeasibilityMargin: Math.min(toMin, toMax),
    nearestBoundaryGap: Math.min(Math.abs(toMin), Math.abs(toMax)),
    toleranceBand,
    activeSides,
    exactDegenerateInterval,
    classification,
    strictInterior: activeSides.length === 0 && toMin > toleranceBand && toMax > toleranceBand
  };
}

function deriveExpectedExtremum(
  firstDirection,
  secondDirection,
  firstInterval,
  secondInterval,
  witness,
  verifiedExtremum,
  tolerance
) {
  const first = deriveExpectedAxis(
    firstDirection,
    witness.point,
    firstInterval,
    verifiedExtremum && verifiedExtremum.first,
    tolerance
  );
  if (!first.supported) return { supported: false, axis: 'first', detail: first };

  const second = deriveExpectedAxis(
    secondDirection,
    witness.point,
    secondInterval,
    verifiedExtremum && verifiedExtremum.second,
    tolerance
  );
  if (!second.supported) return { supported: false, axis: 'second', detail: second };

  return {
    supported: true,
    witnessKind: witness.kind,
    first,
    second,
    minimumSignedFeasibilityMargin: Math.min(
      first.signedFeasibilityMargin,
      second.signedFeasibilityMargin
    ),
    nearestRepresentedBoundaryGap: Math.min(
      first.nearestBoundaryGap,
      second.nearestBoundaryGap
    ),
    activeProjectionCount: Number(first.activeSides.length > 0) + Number(second.activeSides.length > 0)
  };
}

function verifyAxis(receiptAxis, expectedAxis, prefix, tolerance, violations) {
  if (!receiptAxis || typeof receiptAxis !== 'object') {
    violations.push(`${prefix}_AXIS_RECEIPT_MISSING`);
    return;
  }

  for (const [field, code] of [
    ['projection', 'PROJECTION_MISMATCH'],
    ['toMin', 'TO_MIN_MISMATCH'],
    ['toMax', 'TO_MAX_MISMATCH'],
    ['signedFeasibilityMargin', 'SIGNED_FEASIBILITY_MARGIN_MISMATCH'],
    ['nearestBoundaryGap', 'NEAREST_BOUNDARY_GAP_MISMATCH'],
    ['toleranceBand', 'TOLERANCE_BAND_MISMATCH']
  ]) {
    if (!closeEnough(receiptAxis[field], expectedAxis[field], tolerance)) {
      violations.push(`${prefix}_${code}`);
    }
  }

  if (!sameStringArray(receiptAxis.activeSides, expectedAxis.activeSides)) {
    violations.push(`${prefix}_ACTIVE_SIDES_MISMATCH`);
  }
  if (receiptAxis.exactDegenerateInterval !== expectedAxis.exactDegenerateInterval) {
    violations.push(`${prefix}_DEGENERATE_FLAG_MISMATCH`);
  }
  if (receiptAxis.classification !== expectedAxis.classification) {
    violations.push(`${prefix}_CLASSIFICATION_MISMATCH`);
  }
  if (receiptAxis.strictInterior !== expectedAxis.strictInterior) {
    violations.push(`${prefix}_STRICT_INTERIOR_MISMATCH`);
  }
}

function verifyExtremum(receiptExtremum, expectedExtremum, prefix, tolerance, violations) {
  if (!receiptExtremum || typeof receiptExtremum !== 'object') {
    violations.push(`${prefix}_MARGINS_MISSING`);
    return;
  }
  if (receiptExtremum.witnessKind !== expectedExtremum.witnessKind) {
    violations.push(`${prefix}_WITNESS_KIND_MISMATCH`);
  }
  verifyAxis(receiptExtremum.first, expectedExtremum.first, `${prefix}_FIRST`, tolerance, violations);
  verifyAxis(receiptExtremum.second, expectedExtremum.second, `${prefix}_SECOND`, tolerance, violations);

  if (!closeEnough(
    receiptExtremum.minimumSignedFeasibilityMargin,
    expectedExtremum.minimumSignedFeasibilityMargin,
    tolerance
  )) {
    violations.push(`${prefix}_MINIMUM_SIGNED_FEASIBILITY_MARGIN_MISMATCH`);
  }
  if (!closeEnough(
    receiptExtremum.nearestRepresentedBoundaryGap,
    expectedExtremum.nearestRepresentedBoundaryGap,
    tolerance
  )) {
    violations.push(`${prefix}_NEAREST_REPRESENTED_BOUNDARY_GAP_MISMATCH`);
  }
  if (receiptExtremum.activeProjectionCount !== expectedExtremum.activeProjectionCount) {
    violations.push(`${prefix}_ACTIVE_PROJECTION_COUNT_MISMATCH`);
  }
}

function verify(
  firstDirection,
  secondDirection,
  firstInterval,
  secondInterval,
  analysis,
  witnessReceipt,
  activeSetReceipt,
  projectionMarginsReceipt,
  options
) {
  const tolerance = options && options.numericTolerance !== undefined
    ? options.numericTolerance
    : 1e-9;

  if (!Number.isFinite(tolerance) || tolerance < 0) {
    return invalid('INVALID_NUMERIC_TOLERANCE', { numericTolerance: tolerance });
  }

  const activeSetVerification = ActiveSetVerifier.verify(
    firstDirection,
    secondDirection,
    firstInterval,
    secondInterval,
    analysis,
    witnessReceipt,
    activeSetReceipt,
    { numericTolerance: tolerance }
  );

  if (!activeSetVerification.verified) {
    return invalid('ACTIVE_SET_RECEIPT_NOT_VERIFIED', {
      numericTolerance: tolerance,
      activeSetVerification
    });
  }

  if (!projectionMarginsReceipt ||
      projectionMarginsReceipt.supported !== true ||
      projectionMarginsReceipt.verified !== true) {
    return invalid('PROJECTION_MARGINS_RECEIPT_NOT_SUPPORTED', {
      numericTolerance: tolerance,
      activeSetVerification
    });
  }

  const expectedMinimum = deriveExpectedExtremum(
    firstDirection,
    secondDirection,
    firstInterval,
    secondInterval,
    witnessReceipt.minimumWitness,
    activeSetVerification.expectedMinimum,
    tolerance
  );
  if (!expectedMinimum.supported) {
    return invalid('INDEPENDENT_MINIMUM_MARGIN_DERIVATION_FAILED', {
      numericTolerance: tolerance,
      activeSetVerification,
      extremum: 'minimum',
      axis: expectedMinimum.axis,
      detail: expectedMinimum.detail
    });
  }

  const expectedMaximum = deriveExpectedExtremum(
    firstDirection,
    secondDirection,
    firstInterval,
    secondInterval,
    witnessReceipt.maximumWitness,
    activeSetVerification.expectedMaximum,
    tolerance
  );
  if (!expectedMaximum.supported) {
    return invalid('INDEPENDENT_MAXIMUM_MARGIN_DERIVATION_FAILED', {
      numericTolerance: tolerance,
      activeSetVerification,
      extremum: 'maximum',
      axis: expectedMaximum.axis,
      detail: expectedMaximum.detail
    });
  }

  const violations = [];
  if (projectionMarginsReceipt.schema !== PROJECTION_MARGINS_SCHEMA ||
      projectionMarginsReceipt.version !== PROJECTION_MARGINS_VERSION) {
    violations.push('PROJECTION_MARGINS_SCHEMA_MISMATCH');
  }
  if (projectionMarginsReceipt.numericTolerance !== tolerance) {
    violations.push('NUMERIC_TOLERANCE_MISMATCH');
  }
  if (JSON.stringify(projectionMarginsReceipt.activeSetVerification) !== JSON.stringify(activeSetVerification)) {
    violations.push('EMBEDDED_ACTIVE_SET_VERIFICATION_MISMATCH');
  }

  verifyExtremum(
    projectionMarginsReceipt.minimum,
    expectedMinimum,
    'MINIMUM',
    tolerance,
    violations
  );
  verifyExtremum(
    projectionMarginsReceipt.maximum,
    expectedMaximum,
    'MAXIMUM',
    tolerance,
    violations
  );

  const uniqueViolations = Array.from(new Set(violations));
  return {
    schema: SCHEMA,
    version: VERSION,
    verified: uniqueViolations.length === 0,
    reason: uniqueViolations.length === 0 ? null : 'PROJECTION_MARGINS_RECEIPT_INCONSISTENT',
    numericTolerance: tolerance,
    activeSetVerification,
    expectedMinimum,
    expectedMaximum,
    violations: uniqueViolations,
    evidence: [
      'The independent radial-envelope active-set verifier must pass before projection-margin receipt evidence is trusted.',
      'The embedded active-set verification receipt must exactly match a fresh verification over the same represented directions, intervals, analysis, witness receipt, active-set receipt, and tolerance.',
      'Every extremum projection and signed endpoint margin is independently recomputed from fresh direction-point dot products and represented intervals.',
      'Tolerance bands, feasibility margins, nearest-boundary gaps, active sides, degenerate flags, boundary/interior classifications, strict-interior flags, and extremum aggregates must match the independent reconstruction.',
      'Numeric comparisons remain tolerance-relative JavaScript Number checks; exact schema, boolean, string, count, and ordered-side evidence must match exactly.'
    ],
    limitations: [
      'This verifier checks deterministic internal consistency of represented signed-projection margin receipts for already-verified finite two-projection radial-extremum evidence only.',
      'Projection margins are represented-coordinate diagnostics and are not world-space distances unless the corresponding represented direction is unit length.',
      'Projection-margin agreement does not define collision contacts, contact normals, penetration depths, impulses, solver manifolds, or physical correctness.',
      'Direction eligibility remains the responsibility of the existing caller proof boundary and is not widened by this verifier.',
      'Agreement does not establish arbitrary-magnitude numerical stability, exact-arithmetic computational geometry, global satisfiability, convergence, stability, 3D physics, gameplay correctness, or scientific validation.'
    ]
  };
}

module.exports = {
  VERSION,
  SCHEMA,
  verify
};
