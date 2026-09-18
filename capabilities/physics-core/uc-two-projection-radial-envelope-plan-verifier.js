'use strict';

const BaseVerifier = require('./uc-two-projection-radial-envelope-verifier.js');

const VERSION = '0.1.0';
const SCHEMA = 'axm.uc-two-projection-radial-envelope-plan-verifier/v0.1';
const PRODUCER_SCHEMA = 'axm.uc-two-projection-radial-envelope/v0.1';

function intervalContainsZero(interval) {
  return interval.min <= 0 && interval.max >= 0;
}

function intervalIsExactlyOriginSymmetric(interval) {
  return interval.min === -interval.max;
}

function directionNormSquared(direction) {
  return direction.x * direction.x + direction.y * direction.y;
}

function dot(left, right) {
  return left.x * right.x + left.y * right.y;
}

function exactObjectMatches(actual, expected) {
  if (!actual || typeof actual !== 'object') return false;
  return Object.keys(expected).every(key => actual[key] === expected[key]) &&
    Object.keys(actual).length === Object.keys(expected).length;
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

function expectedPlan(firstDirection, secondDirection, firstInterval, secondInterval) {
  const firstNormSquared = directionNormSquared(firstDirection);
  const secondNormSquared = directionNormSquared(secondDirection);
  const representedDot = dot(firstDirection, secondDirection);
  const orthonormalFastPath =
    firstNormSquared === 1 &&
    secondNormSquared === 1 &&
    representedDot === 0;

  let firstDirectionNorm = null;
  let secondDirectionNorm = null;
  let directionNormEvaluations = 0;
  let scaledOrthogonalFastPath = false;
  if (!orthonormalFastPath && representedDot === 0) {
    firstDirectionNorm = Math.hypot(firstDirection.x, firstDirection.y);
    secondDirectionNorm = Math.hypot(secondDirection.x, secondDirection.y);
    directionNormEvaluations = 2;
    scaledOrthogonalFastPath =
      Number.isFinite(firstDirectionNorm) &&
      Number.isFinite(secondDirectionNorm) &&
      firstDirectionNorm > 0 &&
      secondDirectionNorm > 0;
  }

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

  const basisWork = {
    directionNormSquaredEvaluations: 2,
    representedDotEvaluations: 1,
    directionNormEvaluations
  };

  const geometryWork = {
    projectionPointEvaluations:
      degenerateProjectionIntervals === 2
        ? 1
        : degenerateProjectionIntervals === 1 || centrallySymmetricProjectionRectangle
          ? 2
          : 4
  };

  let distanceMethod;
  let edgeDistanceEvaluations;
  let cornerNormEvaluations;

  if (orthonormalFastPath) {
    distanceMethod = 'orthonormal-projection-rectangle';
    edgeDistanceEvaluations = 0;
    cornerNormEvaluations = 0;
  } else if (scaledOrthogonalFastPath) {
    distanceMethod = 'orthogonal-scaled-projection-rectangle';
    edgeDistanceEvaluations = 0;
    cornerNormEvaluations = 0;
  } else if (degenerateProjectionIntervals === 2) {
    distanceMethod = 'inverse-basis-point';
    edgeDistanceEvaluations = 0;
    cornerNormEvaluations = exactOriginPoint ? 0 : 1;
  } else if (degenerateProjectionIntervals === 1) {
    distanceMethod = originInsideProjectionRectangle
      ? 'inverse-basis-segment-origin-contained'
      : 'inverse-basis-segment';
    edgeDistanceEvaluations = originInsideProjectionRectangle ? 0 : 1;
    cornerNormEvaluations = originSymmetricSegmentThroughOrigin ? 1 : 2;
  } else {
    distanceMethod = centrallySymmetricProjectionRectangle
      ? 'inverse-basis-parallelogram-origin-symmetric'
      : originInsideProjectionRectangle
        ? 'inverse-basis-parallelogram-origin-contained'
        : zeroContainingProjectionIntervals === 1
          ? 'inverse-basis-parallelogram-single-active-edge'
          : 'inverse-basis-parallelogram-two-active-edges';
    edgeDistanceEvaluations = originInsideProjectionRectangle
      ? 0
      : zeroContainingProjectionIntervals === 1
        ? 1
        : 2;

    const symmetricMaximumSelectable =
      originSymmetricProjectionIntervals > 0 &&
      Number.isFinite(representedDot) &&
      representedDot !== 0;
    cornerNormEvaluations = symmetricMaximumSelectable
      ? 1
      : centrallySymmetricProjectionRectangle
        ? 2
        : 4;
  }

  return {
    producerSchema: PRODUCER_SCHEMA,
    representedDot,
    firstNormSquared,
    secondNormSquared,
    orthonormalFastPath,
    scaledOrthogonalFastPath,
    basisWork,
    geometryWork,
    distanceMethod,
    distanceWork: {
      edgeDistanceEvaluations,
      cornerNormEvaluations
    }
  };
}

function verify(firstDirection, secondDirection, firstInterval, secondInterval, analysis, options) {
  const baseReceipt = BaseVerifier.verify(
    firstDirection,
    secondDirection,
    firstInterval,
    secondInterval,
    analysis,
    options
  );
  if (!baseReceipt.verified) {
    return invalid('BASE_RECEIPT_VERIFICATION_FAILED', { baseReceipt });
  }

  const expectation = expectedPlan(
    firstDirection,
    secondDirection,
    firstInterval,
    secondInterval
  );
  const violations = [];

  const producerSchemaMatches = analysis.schema === PRODUCER_SCHEMA;
  if (!producerSchemaMatches) {
    violations.push('PRODUCER_SCHEMA_MISMATCH');
  }

  const basisWorkMatches = exactObjectMatches(analysis.basisWork, expectation.basisWork);
  if (!basisWorkMatches) {
    violations.push('BASIS_WORK_MISMATCH');
  }

  const geometryWorkMatches = exactObjectMatches(analysis.geometryWork, expectation.geometryWork);
  if (!geometryWorkMatches) {
    violations.push('GEOMETRY_WORK_MISMATCH');
  }

  const distanceMethodMatches = analysis.distanceMethod === expectation.distanceMethod;
  const distanceWorkMatches = exactObjectMatches(analysis.distanceWork, expectation.distanceWork);
  if (!distanceMethodMatches || !distanceWorkMatches) {
    violations.push('DISTANCE_PLAN_MISMATCH');
  }

  return {
    schema: SCHEMA,
    version: VERSION,
    verified: violations.length === 0,
    reason: violations.length === 0 ? null : 'OPTIMIZATION_RECEIPT_INCONSISTENT',
    producerSchema: analysis.schema,
    producerVersion: analysis.version,
    producerSchemaMatches,
    basisWorkMatches,
    geometryWorkMatches,
    distanceMethodMatches,
    distanceWorkMatches,
    expected: expectation,
    actual: {
      basisWork: analysis.basisWork,
      geometryWork: analysis.geometryWork,
      distanceMethod: analysis.distanceMethod,
      distanceWork: analysis.distanceWork
    },
    baseReceipt,
    violations,
    evidence: [
      'The existing generic radial-envelope receipt verifier must pass before optimization-plan receipt fields are examined.',
      'The producer schema is bound explicitly so a foreign receipt with coincidentally similar fields is not accepted as this envelope contract.',
      'Basis-work expectations are derived from represented squared norms and dot product, including lazy Euclidean direction-norm evaluation only for exact-zero-dot non-orthonormal classification.',
      'Geometry-work expectations are derived from point, segment, exact central-symmetry, or general rectangle structure without trusting the producer work counters.',
      'Distance-method and distance-work expectations are derived from the public interval/basis classifications without trusting the producer optimization label or counters.',
      'These checks verify declarative receipt-plan consistency; they do not measure runtime instruction counts or prove that an implementation executed only the reported amount of work.'
    ],
    limitations: [
      'The optimization-plan verifier intentionally mirrors the public fast-path contract and therefore must be reviewed when that contract changes.',
      'Work counters remain deterministic declarative evidence, not hardware performance counters or execution traces.',
      'Passing this verifier does not widen direction eligibility or establish physical correctness, global satisfiability, convergence, stability, 3D physics, gameplay correctness, or scientific validation.'
    ]
  };
}

module.exports = {
  VERSION,
  SCHEMA,
  PRODUCER_SCHEMA,
  expectedPlan,
  verify
};
