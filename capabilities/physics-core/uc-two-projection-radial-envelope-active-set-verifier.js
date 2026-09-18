'use strict';

const WitnessVerifier = require('./uc-two-projection-radial-envelope-witness-verifier.js');

const VERSION = '0.1.0';
const SCHEMA = 'axm.uc-two-projection-radial-envelope-active-set-verifier/v0.1';
const ACTIVE_SET_SCHEMA = 'axm.uc-two-projection-radial-envelope-active-set/v0.1';
const ACTIVE_SET_VERSION = '0.1.0';

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

function classifyProjection(value, interval, tolerance) {
  const activeSides = [];
  if (closeEnough(value, interval.min, tolerance)) activeSides.push('min');
  if (closeEnough(value, interval.max, tolerance)) activeSides.push('max');

  return {
    projection: value,
    active: activeSides.length > 0,
    activeSides,
    exactDegenerateInterval: interval.min === interval.max
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

function verifyAxis(receiptAxis, expectedAxis, prefix, tolerance, violations) {
  if (!receiptAxis || typeof receiptAxis !== 'object') {
    violations.push(`${prefix}_AXIS_RECEIPT_MISSING`);
    return;
  }
  if (!closeEnough(receiptAxis.projection, expectedAxis.projection, tolerance)) {
    violations.push(`${prefix}_PROJECTION_MISMATCH`);
  }
  if (receiptAxis.active !== expectedAxis.active) {
    violations.push(`${prefix}_ACTIVE_FLAG_MISMATCH`);
  }
  if (!sameStringArray(receiptAxis.activeSides, expectedAxis.activeSides)) {
    violations.push(`${prefix}_ACTIVE_SIDES_MISMATCH`);
  }
  if (receiptAxis.exactDegenerateInterval !== expectedAxis.exactDegenerateInterval) {
    violations.push(`${prefix}_DEGENERATE_FLAG_MISMATCH`);
  }
}

function verify(firstDirection, secondDirection, firstInterval, secondInterval, analysis, witnessReceipt, activeSetReceipt, options) {
  const tolerance = options && options.numericTolerance !== undefined
    ? options.numericTolerance
    : 1e-9;

  if (!Number.isFinite(tolerance) || tolerance < 0) {
    return invalid('INVALID_NUMERIC_TOLERANCE', { numericTolerance: tolerance });
  }

  const witnessVerification = WitnessVerifier.verify(
    firstDirection,
    secondDirection,
    firstInterval,
    secondInterval,
    analysis,
    witnessReceipt,
    { numericTolerance: tolerance }
  );

  if (!witnessVerification.verified) {
    return invalid('WITNESS_RECEIPT_NOT_VERIFIED', {
      numericTolerance: tolerance,
      witnessVerification
    });
  }

  if (!activeSetReceipt || activeSetReceipt.supported !== true || activeSetReceipt.verified !== true) {
    return invalid('ACTIVE_SET_RECEIPT_NOT_SUPPORTED', {
      numericTolerance: tolerance,
      witnessVerification
    });
  }

  const minimumWitness = witnessReceipt.minimumWitness;
  const maximumWitness = witnessReceipt.maximumWitness;
  const minimum = {
    witnessKind: minimumWitness.kind,
    first: classifyProjection(dot(firstDirection, minimumWitness.point), firstInterval, tolerance),
    second: classifyProjection(dot(secondDirection, minimumWitness.point), secondInterval, tolerance)
  };
  minimum.activeProjectionCount = Number(minimum.first.active) + Number(minimum.second.active);

  const maximum = {
    witnessKind: maximumWitness.kind,
    first: classifyProjection(dot(firstDirection, maximumWitness.point), firstInterval, tolerance),
    second: classifyProjection(dot(secondDirection, maximumWitness.point), secondInterval, tolerance)
  };
  maximum.activeProjectionCount = Number(maximum.first.active) + Number(maximum.second.active);

  const expectedFinite = [
    minimum.first.projection,
    minimum.second.projection,
    maximum.first.projection,
    maximum.second.projection
  ].every(Number.isFinite);
  if (!expectedFinite) {
    return invalid('NON_FINITE_INDEPENDENT_ACTIVE_SET_PROJECTION', {
      numericTolerance: tolerance,
      witnessVerification,
      expectedMinimum: minimum,
      expectedMaximum: maximum
    });
  }

  const violations = [];
  if (activeSetReceipt.schema !== ACTIVE_SET_SCHEMA || activeSetReceipt.version !== ACTIVE_SET_VERSION) {
    violations.push('ACTIVE_SET_SCHEMA_MISMATCH');
  }
  if (activeSetReceipt.numericTolerance !== tolerance) {
    violations.push('NUMERIC_TOLERANCE_MISMATCH');
  }
  if (JSON.stringify(activeSetReceipt.witnessVerification) !== JSON.stringify(witnessVerification)) {
    violations.push('EMBEDDED_WITNESS_VERIFICATION_MISMATCH');
  }

  const receiptMinimum = activeSetReceipt.minimum;
  const receiptMaximum = activeSetReceipt.maximum;
  if (!receiptMinimum || typeof receiptMinimum !== 'object') {
    violations.push('MINIMUM_ACTIVE_SET_MISSING');
  } else {
    if (receiptMinimum.witnessKind !== minimum.witnessKind) {
      violations.push('MINIMUM_WITNESS_KIND_MISMATCH');
    }
    verifyAxis(receiptMinimum.first, minimum.first, 'MINIMUM_FIRST', tolerance, violations);
    verifyAxis(receiptMinimum.second, minimum.second, 'MINIMUM_SECOND', tolerance, violations);
    if (receiptMinimum.activeProjectionCount !== minimum.activeProjectionCount) {
      violations.push('MINIMUM_ACTIVE_PROJECTION_COUNT_MISMATCH');
    }
  }

  if (!receiptMaximum || typeof receiptMaximum !== 'object') {
    violations.push('MAXIMUM_ACTIVE_SET_MISSING');
  } else {
    if (receiptMaximum.witnessKind !== maximum.witnessKind) {
      violations.push('MAXIMUM_WITNESS_KIND_MISMATCH');
    }
    verifyAxis(receiptMaximum.first, maximum.first, 'MAXIMUM_FIRST', tolerance, violations);
    verifyAxis(receiptMaximum.second, maximum.second, 'MAXIMUM_SECOND', tolerance, violations);
    if (receiptMaximum.activeProjectionCount !== maximum.activeProjectionCount) {
      violations.push('MAXIMUM_ACTIVE_PROJECTION_COUNT_MISMATCH');
    }
  }

  if (minimum.witnessKind === 'boundary-segment' && minimum.activeProjectionCount < 1) {
    violations.push('INDEPENDENT_BOUNDARY_MINIMUM_WITHOUT_ACTIVE_PROJECTION');
  }
  if (maximum.witnessKind === 'corner' && maximum.activeProjectionCount !== 2) {
    violations.push('INDEPENDENT_CORNER_MAXIMUM_WITHOUT_TWO_ACTIVE_PROJECTIONS');
  }

  const uniqueViolations = Array.from(new Set(violations));
  return {
    schema: SCHEMA,
    version: VERSION,
    verified: uniqueViolations.length === 0,
    reason: uniqueViolations.length === 0 ? null : 'ACTIVE_SET_RECEIPT_INCONSISTENT',
    numericTolerance: tolerance,
    witnessVerification,
    expectedMinimum: minimum,
    expectedMaximum: maximum,
    violations: uniqueViolations,
    evidence: [
      'The independent radial-envelope witness verifier must pass before active-set receipt evidence is trusted.',
      'The embedded witness-verification receipt must exactly match a fresh verification over the same represented directions, intervals, analysis, witness receipt, and tolerance.',
      'Minimum and maximum witness projections are independently recomputed from fresh direction-point dot products before interval-side activity is classified.',
      'Projection values, active flags, ordered active-side lists, exact-degenerate interval flags, witness kinds, and active-axis counts must match the independent reconstruction.',
      'A non-origin boundary-segment minimum must independently activate at least one represented projection axis, and a corner maximum must activate both represented projection axes.'
    ],
    limitations: [
      'This verifier checks deterministic internal consistency of represented projection active sets for already-verified finite two-projection radial-extremum witnesses only.',
      'Active interval sides are tolerance-relative geometric metadata, not collision contacts, contact normals, penetration constraints, impulses, or solver manifolds.',
      'Direction eligibility remains the responsibility of the existing caller proof boundary and is not widened by active-set verification.',
      'Agreement does not establish arbitrary-magnitude numerical stability, exact-arithmetic computational geometry, global satisfiability, convergence, stability, physical correctness, 3D physics, gameplay correctness, or scientific validation.'
    ]
  };
}

module.exports = {
  VERSION,
  SCHEMA,
  verify
};
