'use strict';

const ActiveSetVerifier = require('./uc-two-projection-radial-envelope-active-set-verifier.js');

const VERSION = '0.1.0';
const SCHEMA = 'axm.uc-two-projection-radial-envelope-projection-margins/v0.1';

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

function unsupported(reason, extra) {
  return Object.assign({
    schema: SCHEMA,
    version: VERSION,
    supported: false,
    verified: false,
    reason
  }, extra || {});
}

function deriveAxis(direction, point, interval, verifiedAxis, tolerance) {
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

function deriveExtremum(firstDirection, secondDirection, firstInterval, secondInterval, witness, verifiedExtremum, tolerance) {
  const first = deriveAxis(
    firstDirection,
    witness.point,
    firstInterval,
    verifiedExtremum && verifiedExtremum.first,
    tolerance
  );
  if (!first.supported) return { supported: false, axis: 'first', detail: first };

  const second = deriveAxis(
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

function derive(firstDirection, secondDirection, firstInterval, secondInterval, analysis, witnessReceipt, activeSetReceipt, options) {
  const tolerance = options && options.numericTolerance !== undefined
    ? options.numericTolerance
    : 1e-9;

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
    return unsupported('ACTIVE_SET_RECEIPT_NOT_VERIFIED', {
      numericTolerance: tolerance,
      activeSetVerification
    });
  }

  const minimum = deriveExtremum(
    firstDirection,
    secondDirection,
    firstInterval,
    secondInterval,
    witnessReceipt.minimumWitness,
    activeSetVerification.expectedMinimum,
    tolerance
  );
  if (!minimum.supported) {
    return unsupported(minimum.detail.reason, {
      numericTolerance: tolerance,
      extremum: 'minimum',
      axis: minimum.axis,
      detail: minimum.detail,
      activeSetVerification
    });
  }

  const maximum = deriveExtremum(
    firstDirection,
    secondDirection,
    firstInterval,
    secondInterval,
    witnessReceipt.maximumWitness,
    activeSetVerification.expectedMaximum,
    tolerance
  );
  if (!maximum.supported) {
    return unsupported(maximum.detail.reason, {
      numericTolerance: tolerance,
      extremum: 'maximum',
      axis: maximum.axis,
      detail: maximum.detail,
      activeSetVerification
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
    activeSetVerification,
    evidence: [
      'The independent radial-envelope active-set verifier must pass before projection margins are derived.',
      'Each extremum witness projection is recomputed from a fresh direction-point dot product and expressed as signed represented-projection margin to both interval endpoints.',
      'A margin may be slightly negative only inside the caller-selected JavaScript Number tolerance band; values outside that band are rejected as infeasible.',
      'Active-side reconstruction must exactly match the independently verified active-set receipt.',
      'Strict-interior classification requires both endpoint margins to exceed the local tolerance band on that represented projection axis.'
    ],
    limitations: [
      'Projection margins are represented signed-projection diagnostics; they are not world-space distances unless the represented direction happens to be unit length.',
      'These margins do not define collision contacts, contact normals, penetration depths, impulses, solver manifolds, or physical correctness.',
      'Direction eligibility remains the responsibility of the existing caller proof boundary and is not widened by this helper.',
      'All classifications are deterministic JavaScript Number evidence under caller-selected tolerance, not exact-arithmetic computational geometry or arbitrary-magnitude numerical-stability evidence.',
      'This helper does not establish global satisfiability, convergence, stability, 3D physics, gameplay correctness, or scientific validation.'
    ]
  };
}

module.exports = {
  VERSION,
  SCHEMA,
  derive
};
