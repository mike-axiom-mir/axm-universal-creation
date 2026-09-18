'use strict';

const WitnessVerifier = require('./uc-two-projection-radial-envelope-witness-verifier.js');

const VERSION = '0.1.0';
const SCHEMA = 'axm.uc-two-projection-radial-envelope-active-set/v0.1';

function closeEnough(actual, expected, tolerance) {
  if (!Number.isFinite(actual) || !Number.isFinite(expected)) return false;
  const scale = Math.max(1, Math.abs(actual), Math.abs(expected));
  return Math.abs(actual - expected) <= tolerance * scale;
}

function dot(direction, point) {
  return direction.x * point.x + direction.y * point.y;
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

function unsupported(reason, extra) {
  return Object.assign({
    schema: SCHEMA,
    version: VERSION,
    supported: false,
    verified: false,
    reason
  }, extra || {});
}

function derive(firstDirection, secondDirection, firstInterval, secondInterval, analysis, witnessReceipt, options) {
  const tolerance = options && options.numericTolerance !== undefined
    ? options.numericTolerance
    : 1e-9;

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
    return unsupported('WITNESS_RECEIPT_NOT_VERIFIED', {
      numericTolerance: tolerance,
      witnessVerification
    });
  }

  const minimumWitness = witnessReceipt.minimumWitness;
  const maximumWitness = witnessReceipt.maximumWitness;

  const minimumFirstProjection = dot(firstDirection, minimumWitness.point);
  const minimumSecondProjection = dot(secondDirection, minimumWitness.point);
  const maximumFirstProjection = dot(firstDirection, maximumWitness.point);
  const maximumSecondProjection = dot(secondDirection, maximumWitness.point);

  if (!Number.isFinite(minimumFirstProjection) ||
      !Number.isFinite(minimumSecondProjection) ||
      !Number.isFinite(maximumFirstProjection) ||
      !Number.isFinite(maximumSecondProjection)) {
    return unsupported('NON_FINITE_ACTIVE_SET_PROJECTION', {
      numericTolerance: tolerance,
      witnessVerification
    });
  }

  const minimum = {
    witnessKind: minimumWitness.kind,
    first: classifyProjection(minimumFirstProjection, firstInterval, tolerance),
    second: classifyProjection(minimumSecondProjection, secondInterval, tolerance)
  };
  minimum.activeProjectionCount = Number(minimum.first.active) + Number(minimum.second.active);

  const maximum = {
    witnessKind: maximumWitness.kind,
    first: classifyProjection(maximumFirstProjection, firstInterval, tolerance),
    second: classifyProjection(maximumSecondProjection, secondInterval, tolerance)
  };
  maximum.activeProjectionCount = Number(maximum.first.active) + Number(maximum.second.active);

  const provenanceViolations = [];
  if (minimumWitness.kind === 'boundary-segment' && minimum.activeProjectionCount < 1) {
    provenanceViolations.push('BOUNDARY_MINIMUM_WITHOUT_ACTIVE_PROJECTION');
  }
  if (maximumWitness.kind === 'corner' && maximum.activeProjectionCount !== 2) {
    provenanceViolations.push('CORNER_MAXIMUM_WITHOUT_TWO_ACTIVE_PROJECTIONS');
  }

  if (provenanceViolations.length > 0) {
    return unsupported('ACTIVE_SET_PROVENANCE_MISMATCH', {
      numericTolerance: tolerance,
      witnessVerification,
      minimum,
      maximum,
      violations: provenanceViolations
    });
  }

  return {
    schema: SCHEMA,
    version: VERSION,
    supported: true,
    verified: true,
    reason: null,
    numericTolerance: tolerance,
    minimum,
    maximum,
    witnessVerification,
    evidence: [
      'The independent radial-envelope witness verifier must pass before active projection sides are derived.',
      'Active projection sides are recomputed from fresh direction-point dot products against represented interval endpoints under the caller-selected JavaScript Number tolerance.',
      'A non-origin boundary-segment minimum must activate at least one represented projection boundary.',
      'A corner maximum must activate both represented projection axes; exact-degenerate intervals may report both min and max sides on the same axis.',
      'An origin minimum is allowed to be strictly interior or to lie on one or more represented interval endpoints.'
    ],
    limitations: [
      'These active sets describe which represented projection-interval sides contain the already-verified radial-extremum witnesses; they are not collision contacts, contact normals, penetration constraints, or solver manifolds.',
      'Direction eligibility remains the responsibility of the existing caller proof boundary and is not widened by this helper.',
      'Endpoint activity is tolerance-relative JavaScript Number evidence, not exact-arithmetic constraint classification.',
      'This helper does not establish arbitrary-magnitude numerical stability, global satisfiability, convergence, physical correctness, 3D physics, gameplay correctness, or scientific validation.'
    ]
  };
}

module.exports = {
  VERSION,
  SCHEMA,
  derive
};
