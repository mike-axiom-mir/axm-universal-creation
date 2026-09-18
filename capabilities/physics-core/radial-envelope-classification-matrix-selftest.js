'use strict';

const assert = require('assert');
const Envelope = require('./uc-two-projection-radial-envelope.js');
const ReceiptVerifier = require('./uc-two-projection-radial-envelope-verifier.js');
const PlanVerifier = require('./uc-two-projection-radial-envelope-plan-verifier.js');

const nearOrthogonalY = Math.sqrt(1 - 25e-14);
const basisFixtures = [
  {
    name: 'exact-orthonormal',
    first: { x: 1, y: 0 },
    second: { x: 0, y: 1 }
  },
  {
    name: 'scaled-exact-orthogonal',
    first: { x: 2, y: 0 },
    second: { x: 0, y: 3 }
  },
  {
    name: 'inverse-basis-positive-dot',
    first: { x: 1 + 2e-10, y: 0 },
    second: { x: 5e-7, y: nearOrthogonalY }
  },
  {
    name: 'inverse-basis-negative-dot',
    first: { x: 1 + 2e-10, y: 0 },
    second: { x: -5e-7, y: nearOrthogonalY }
  }
];

const intervalFixtures = [
  { name: 'origin-symmetric', value: { min: -3, max: 3 } },
  { name: 'origin-contained-asymmetric', value: { min: -1, max: 4 } },
  { name: 'positive-one-sided', value: { min: 2, max: 5 } },
  { name: 'negative-one-sided', value: { min: -5, max: -2 } },
  { name: 'exact-zero', value: { min: 0, max: 0 } },
  { name: 'positive-point', value: { min: 3, max: 3 } },
  { name: 'negative-point', value: { min: -3, max: -3 } }
];

const coverage = {
  distanceMethods: new Set(),
  projectionPointEvaluations: new Set(),
  edgeDistanceEvaluations: new Set(),
  cornerNormEvaluations: new Set(),
  directionNormEvaluations: new Set()
};

let caseCount = 0;
for (const basis of basisFixtures) {
  for (const firstFixture of intervalFixtures) {
    for (const secondFixture of intervalFixtures) {
      const firstInterval = firstFixture.value;
      const secondInterval = secondFixture.value;
      const caseName = `${basis.name}/${firstFixture.name}/${secondFixture.name}`;

      const analysis = Envelope.analyze(
        basis.first,
        basis.second,
        firstInterval,
        secondInterval
      );
      assert.equal(analysis.supported, true, `${caseName}: producer must stay supported`);

      const replayAnalysis = Envelope.analyze(
        basis.first,
        basis.second,
        firstInterval,
        secondInterval
      );
      assert.deepEqual(replayAnalysis, analysis, `${caseName}: producer replay must be deterministic`);

      const receipt = ReceiptVerifier.verify(
        basis.first,
        basis.second,
        firstInterval,
        secondInterval,
        analysis,
        { numericTolerance: 1e-9 }
      );
      assert.equal(
        receipt.verified,
        true,
        `${caseName}: generic receipt verification failed: ${receipt.violations.join(', ')}`
      );

      const planReceipt = PlanVerifier.verify(
        basis.first,
        basis.second,
        firstInterval,
        secondInterval,
        analysis,
        { numericTolerance: 1e-9 }
      );
      assert.equal(
        planReceipt.verified,
        true,
        `${caseName}: optimization-plan verification failed: ${planReceipt.violations.join(', ')}`
      );

      const planReplay = PlanVerifier.verify(
        basis.first,
        basis.second,
        firstInterval,
        secondInterval,
        analysis,
        { numericTolerance: 1e-9 }
      );
      assert.deepEqual(planReplay, planReceipt, `${caseName}: plan verification replay must be deterministic`);

      assert.equal(
        planReceipt.expected.distanceMethod,
        analysis.distanceMethod,
        `${caseName}: independent plan method must match producer method`
      );
      assert.deepEqual(
        planReceipt.expected.distanceWork,
        analysis.distanceWork,
        `${caseName}: independent plan distance work must match producer receipt`
      );
      assert.deepEqual(
        planReceipt.expected.geometryWork,
        analysis.geometryWork,
        `${caseName}: independent plan geometry work must match producer receipt`
      );
      assert.deepEqual(
        planReceipt.expected.basisWork,
        analysis.basisWork,
        `${caseName}: independent plan basis work must match producer receipt`
      );

      coverage.distanceMethods.add(analysis.distanceMethod);
      coverage.projectionPointEvaluations.add(analysis.geometryWork.projectionPointEvaluations);
      coverage.edgeDistanceEvaluations.add(analysis.distanceWork.edgeDistanceEvaluations);
      coverage.cornerNormEvaluations.add(analysis.distanceWork.cornerNormEvaluations);
      coverage.directionNormEvaluations.add(analysis.basisWork.directionNormEvaluations);
      caseCount += 1;
    }
  }
}

assert.equal(caseCount, 196, 'classification matrix size must remain deterministic');
assert.deepEqual(
  Array.from(coverage.distanceMethods).sort(),
  [
    'inverse-basis-parallelogram-origin-contained',
    'inverse-basis-parallelogram-origin-symmetric',
    'inverse-basis-parallelogram-single-active-edge',
    'inverse-basis-parallelogram-two-active-edges',
    'inverse-basis-point',
    'inverse-basis-segment',
    'inverse-basis-segment-origin-contained',
    'orthogonal-scaled-projection-rectangle',
    'orthonormal-projection-rectangle'
  ].sort(),
  'matrix must exercise every current public distance-method classification'
);
assert.deepEqual(
  Array.from(coverage.projectionPointEvaluations).sort((a, b) => a - b),
  [1, 2, 4],
  'matrix must cover point, segment/symmetry, and general rectangle reconstruction work'
);
assert.deepEqual(
  Array.from(coverage.edgeDistanceEvaluations).sort((a, b) => a - b),
  [0, 1, 2],
  'matrix must cover zero-, one-, and two-active-edge distance work'
);
assert.deepEqual(
  Array.from(coverage.cornerNormEvaluations).sort((a, b) => a - b),
  [0, 1, 2, 4],
  'matrix must cover all current corner-norm work classifications'
);
assert.deepEqual(
  Array.from(coverage.directionNormEvaluations).sort((a, b) => a - b),
  [0, 2],
  'matrix must cover lazy and scaled-orthogonal direction-norm classifications'
);

console.log(`radial envelope classification matrix selftest passed (${caseCount} deterministic cases)`);
