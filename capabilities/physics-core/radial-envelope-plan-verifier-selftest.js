'use strict';

const assert = require('assert');
const Envelope = require('./uc-two-projection-radial-envelope.js');
const PlanVerifier = require('./uc-two-projection-radial-envelope-plan-verifier.js');

const nearOrthogonalFirst = { x: 1 + 2e-10, y: 0 };
const nearOrthogonalSecond = { x: 5e-7, y: Math.sqrt(1 - 25e-14) };

function verifyPlan(firstDirection, secondDirection, firstInterval, secondInterval) {
  const analysis = Envelope.analyze(firstDirection, secondDirection, firstInterval, secondInterval);
  assert.equal(analysis.supported, true, 'fixture must stay inside the existing finite invertible envelope contract');
  const receipt = PlanVerifier.verify(
    firstDirection,
    secondDirection,
    firstInterval,
    secondInterval,
    analysis,
    { numericTolerance: 1e-9 }
  );
  assert.equal(receipt.verified, true, `optimization plan verification failed: ${receipt.violations.join(', ')}`);
  assert.equal(receipt.producerSchemaMatches, true);
  assert.equal(receipt.basisWorkMatches, true);
  assert.equal(receipt.geometryWorkMatches, true);
  assert.equal(receipt.distanceMethodMatches, true);
  assert.equal(receipt.distanceWorkMatches, true);
  return { analysis, receipt };
}

const orthonormal = verifyPlan(
  { x: 1, y: 0 },
  { x: 0, y: 1 },
  { min: -2, max: 5 },
  { min: -4, max: 1 }
);
assert.deepEqual(orthonormal.analysis.basisWork, {
  directionNormSquaredEvaluations: 2,
  representedDotEvaluations: 1,
  directionNormEvaluations: 0
});
assert.deepEqual(orthonormal.analysis.geometryWork, { projectionPointEvaluations: 4 });
assert.equal(orthonormal.analysis.distanceMethod, 'orthonormal-projection-rectangle');
assert.deepEqual(orthonormal.analysis.distanceWork, {
  edgeDistanceEvaluations: 0,
  cornerNormEvaluations: 0
});

const scaledOrthogonal = verifyPlan(
  { x: 2, y: 0 },
  { x: 0, y: 3 },
  { min: 2, max: 5 },
  { min: -4, max: -1 }
);
assert.deepEqual(scaledOrthogonal.analysis.basisWork, {
  directionNormSquaredEvaluations: 2,
  representedDotEvaluations: 1,
  directionNormEvaluations: 2
});
assert.equal(scaledOrthogonal.analysis.distanceMethod, 'orthogonal-scaled-projection-rectangle');
assert.deepEqual(scaledOrthogonal.analysis.distanceWork, {
  edgeDistanceEvaluations: 0,
  cornerNormEvaluations: 0
});

const inverseBasis = verifyPlan(
  nearOrthogonalFirst,
  nearOrthogonalSecond,
  { min: 2, max: 5 },
  { min: -4, max: -1 }
);
assert.deepEqual(inverseBasis.analysis.basisWork, {
  directionNormSquaredEvaluations: 2,
  representedDotEvaluations: 1,
  directionNormEvaluations: 0
});
assert.deepEqual(inverseBasis.analysis.geometryWork, { projectionPointEvaluations: 4 });
assert.equal(inverseBasis.analysis.distanceMethod, 'inverse-basis-parallelogram-two-active-edges');
assert.deepEqual(inverseBasis.analysis.distanceWork, {
  edgeDistanceEvaluations: 2,
  cornerNormEvaluations: 4
});

const centrallySymmetric = verifyPlan(
  nearOrthogonalFirst,
  nearOrthogonalSecond,
  { min: -2, max: 2 },
  { min: -3, max: 3 }
);
assert.deepEqual(centrallySymmetric.analysis.geometryWork, { projectionPointEvaluations: 2 });
assert.equal(centrallySymmetric.analysis.distanceMethod, 'inverse-basis-parallelogram-origin-symmetric');
assert.deepEqual(centrallySymmetric.analysis.distanceWork, {
  edgeDistanceEvaluations: 0,
  cornerNormEvaluations: 1
});

const symmetricSegment = verifyPlan(
  nearOrthogonalFirst,
  nearOrthogonalSecond,
  { min: 0, max: 0 },
  { min: -3, max: 3 }
);
assert.deepEqual(symmetricSegment.analysis.geometryWork, { projectionPointEvaluations: 2 });
assert.equal(symmetricSegment.analysis.distanceMethod, 'inverse-basis-segment-origin-contained');
assert.deepEqual(symmetricSegment.analysis.distanceWork, {
  edgeDistanceEvaluations: 0,
  cornerNormEvaluations: 1
});

const originPoint = verifyPlan(
  nearOrthogonalFirst,
  nearOrthogonalSecond,
  { min: 0, max: 0 },
  { min: 0, max: 0 }
);
assert.deepEqual(originPoint.analysis.geometryWork, { projectionPointEvaluations: 1 });
assert.equal(originPoint.analysis.distanceMethod, 'inverse-basis-point');
assert.deepEqual(originPoint.analysis.distanceWork, {
  edgeDistanceEvaluations: 0,
  cornerNormEvaluations: 0
});

const methodTamper = Object.assign({}, inverseBasis.analysis, {
  distanceMethod: 'inverse-basis-parallelogram-single-active-edge'
});
const methodFailure = PlanVerifier.verify(
  nearOrthogonalFirst,
  nearOrthogonalSecond,
  { min: 2, max: 5 },
  { min: -4, max: -1 },
  methodTamper,
  { numericTolerance: 1e-9 }
);
assert.equal(methodFailure.verified, false);
assert.ok(methodFailure.violations.includes('DISTANCE_PLAN_MISMATCH'));
assert.equal(methodFailure.distanceMethodMatches, false);

const distanceWorkTamper = Object.assign({}, inverseBasis.analysis, {
  distanceWork: {
    edgeDistanceEvaluations: 4,
    cornerNormEvaluations: 4
  }
});
const distanceWorkFailure = PlanVerifier.verify(
  nearOrthogonalFirst,
  nearOrthogonalSecond,
  { min: 2, max: 5 },
  { min: -4, max: -1 },
  distanceWorkTamper,
  { numericTolerance: 1e-9 }
);
assert.equal(distanceWorkFailure.verified, false);
assert.ok(distanceWorkFailure.violations.includes('DISTANCE_PLAN_MISMATCH'));
assert.equal(distanceWorkFailure.distanceWorkMatches, false);

const geometryWorkTamper = Object.assign({}, centrallySymmetric.analysis, {
  geometryWork: { projectionPointEvaluations: 4 }
});
const geometryWorkFailure = PlanVerifier.verify(
  nearOrthogonalFirst,
  nearOrthogonalSecond,
  { min: -2, max: 2 },
  { min: -3, max: 3 },
  geometryWorkTamper,
  { numericTolerance: 1e-9 }
);
assert.equal(geometryWorkFailure.verified, false);
assert.ok(geometryWorkFailure.violations.includes('GEOMETRY_WORK_MISMATCH'));
assert.equal(geometryWorkFailure.geometryWorkMatches, false);

const basisWorkTamper = Object.assign({}, scaledOrthogonal.analysis, {
  basisWork: {
    directionNormSquaredEvaluations: 2,
    representedDotEvaluations: 1,
    directionNormEvaluations: 0
  }
});
const basisWorkFailure = PlanVerifier.verify(
  { x: 2, y: 0 },
  { x: 0, y: 3 },
  { min: 2, max: 5 },
  { min: -4, max: -1 },
  basisWorkTamper,
  { numericTolerance: 1e-9 }
);
assert.equal(basisWorkFailure.verified, false);
assert.ok(basisWorkFailure.violations.includes('BASIS_WORK_MISMATCH'));
assert.equal(basisWorkFailure.basisWorkMatches, false);

const schemaTamper = Object.assign({}, inverseBasis.analysis, {
  schema: 'foreign.radial-envelope/v9'
});
const schemaFailure = PlanVerifier.verify(
  nearOrthogonalFirst,
  nearOrthogonalSecond,
  { min: 2, max: 5 },
  { min: -4, max: -1 },
  schemaTamper,
  { numericTolerance: 1e-9 }
);
assert.equal(schemaFailure.verified, false);
assert.ok(schemaFailure.violations.includes('PRODUCER_SCHEMA_MISMATCH'));
assert.equal(schemaFailure.producerSchemaMatches, false);

const corruptedGeometry = Object.assign({}, inverseBasis.analysis, {
  maximumDistance: inverseBasis.analysis.maximumDistance + 0.5
});
const baseFailure = PlanVerifier.verify(
  nearOrthogonalFirst,
  nearOrthogonalSecond,
  { min: 2, max: 5 },
  { min: -4, max: -1 },
  corruptedGeometry,
  { numericTolerance: 1e-9 }
);
assert.equal(baseFailure.verified, false);
assert.equal(baseFailure.reason, 'BASE_RECEIPT_VERIFICATION_FAILED');
assert.ok(baseFailure.baseReceipt.violations.includes('MAXIMUM_DISTANCE_MISMATCH'));

assert.deepEqual(
  PlanVerifier.verify(
    nearOrthogonalFirst,
    nearOrthogonalSecond,
    { min: 2, max: 5 },
    { min: -4, max: -1 },
    inverseBasis.analysis,
    { numericTolerance: 1e-9 }
  ),
  inverseBasis.receipt,
  'optimization plan verification must replay deterministically'
);

console.log('radial envelope optimization plan verifier selftest passed');
