'use strict';

const assert = require('assert');
const Envelope = require('./uc-two-projection-radial-envelope.js');
const ReceiptVerifier = require('./uc-two-projection-radial-envelope-verifier.js');
const PlanVerifier = require('./uc-two-projection-radial-envelope-plan-verifier.js');

const NUMERIC_TOLERANCE = 1e-9;
const SCALE_FACTORS = [0.125, 0.5, 2, 8];
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

function scaleInterval(interval, factor) {
  return {
    min: interval.min * factor,
    max: interval.max * factor
  };
}

function closeEnough(actual, expected) {
  const scale = Math.max(1, Math.abs(actual), Math.abs(expected));
  return Math.abs(actual - expected) <= NUMERIC_TOLERANCE * scale;
}

function requireVerified(caseName, firstDirection, secondDirection, firstInterval, secondInterval, analysis) {
  const receipt = ReceiptVerifier.verify(
    firstDirection,
    secondDirection,
    firstInterval,
    secondInterval,
    analysis,
    { numericTolerance: NUMERIC_TOLERANCE }
  );
  assert.equal(
    receipt.verified,
    true,
    `${caseName}: generic receipt verification failed: ${receipt.violations.join(', ')}`
  );

  const planReceipt = PlanVerifier.verify(
    firstDirection,
    secondDirection,
    firstInterval,
    secondInterval,
    analysis,
    { numericTolerance: NUMERIC_TOLERANCE }
  );
  assert.equal(
    planReceipt.verified,
    true,
    `${caseName}: optimization-plan verification failed: ${planReceipt.violations.join(', ')}`
  );
  return planReceipt;
}

const structuralFields = [
  'degenerateProjectionIntervals',
  'zeroContainingProjectionIntervals',
  'originInsideProjectionRectangle',
  'centrallySymmetricProjectionRectangle',
  'exactOriginPoint',
  'originSymmetricSegmentThroughOrigin'
];

let baseCaseCount = 0;
let scaledCaseCount = 0;
for (const basis of basisFixtures) {
  for (const firstFixture of intervalFixtures) {
    for (const secondFixture of intervalFixtures) {
      const baseName = `${basis.name}/${firstFixture.name}/${secondFixture.name}`;
      const firstInterval = firstFixture.value;
      const secondInterval = secondFixture.value;
      const baseAnalysis = Envelope.analyze(
        basis.first,
        basis.second,
        firstInterval,
        secondInterval
      );
      assert.equal(baseAnalysis.supported, true, `${baseName}: base producer must stay supported`);
      const baseReplay = Envelope.analyze(
        basis.first,
        basis.second,
        firstInterval,
        secondInterval
      );
      assert.deepEqual(baseReplay, baseAnalysis, `${baseName}: base producer replay must be deterministic`);
      const basePlan = requireVerified(
        baseName,
        basis.first,
        basis.second,
        firstInterval,
        secondInterval,
        baseAnalysis
      );
      baseCaseCount += 1;

      for (const factor of SCALE_FACTORS) {
        const scaledName = `${baseName}/scale-${factor}`;
        const scaledFirstInterval = scaleInterval(firstInterval, factor);
        const scaledSecondInterval = scaleInterval(secondInterval, factor);
        const scaledAnalysis = Envelope.analyze(
          basis.first,
          basis.second,
          scaledFirstInterval,
          scaledSecondInterval
        );
        assert.equal(scaledAnalysis.supported, true, `${scaledName}: scaled producer must stay supported`);

        const scaledReplay = Envelope.analyze(
          basis.first,
          basis.second,
          scaledFirstInterval,
          scaledSecondInterval
        );
        assert.deepEqual(
          scaledReplay,
          scaledAnalysis,
          `${scaledName}: scaled producer replay must be deterministic`
        );

        const scaledPlan = requireVerified(
          scaledName,
          basis.first,
          basis.second,
          scaledFirstInterval,
          scaledSecondInterval,
          scaledAnalysis
        );

        assert.equal(
          closeEnough(scaledAnalysis.minimumDistance, baseAnalysis.minimumDistance * factor),
          true,
          `${scaledName}: radial minimum must scale linearly with positive interval scale`
        );
        assert.equal(
          closeEnough(scaledAnalysis.maximumDistance, baseAnalysis.maximumDistance * factor),
          true,
          `${scaledName}: radial maximum must scale linearly with positive interval scale`
        );

        assert.equal(
          scaledAnalysis.corners.length,
          baseAnalysis.corners.length,
          `${scaledName}: scaled receipt must retain four corner evidence slots`
        );
        for (let index = 0; index < baseAnalysis.corners.length; index += 1) {
          assert.equal(
            closeEnough(scaledAnalysis.corners[index].x, baseAnalysis.corners[index].x * factor),
            true,
            `${scaledName}: corner ${index} x must scale linearly`
          );
          assert.equal(
            closeEnough(scaledAnalysis.corners[index].y, baseAnalysis.corners[index].y * factor),
            true,
            `${scaledName}: corner ${index} y must scale linearly`
          );
        }

        assert.equal(
          scaledAnalysis.determinant,
          baseAnalysis.determinant,
          `${scaledName}: interval scaling must not alter represented basis determinant`
        );
        for (const field of structuralFields) {
          assert.deepEqual(
            scaledAnalysis[field],
            baseAnalysis[field],
            `${scaledName}: positive scale must retain structural receipt field ${field}`
          );
        }
        assert.equal(
          scaledAnalysis.distanceMethod,
          baseAnalysis.distanceMethod,
          `${scaledName}: positive scale must retain distance-method classification`
        );
        assert.deepEqual(
          scaledAnalysis.basisWork,
          baseAnalysis.basisWork,
          `${scaledName}: positive scale must retain basis-work classification`
        );
        assert.deepEqual(
          scaledAnalysis.geometryWork,
          baseAnalysis.geometryWork,
          `${scaledName}: positive scale must retain geometry-work classification`
        );
        assert.deepEqual(
          scaledAnalysis.distanceWork,
          baseAnalysis.distanceWork,
          `${scaledName}: positive scale must retain distance-work classification`
        );

        assert.equal(
          scaledPlan.expected.producerSchema,
          scaledAnalysis.schema,
          `${scaledName}: independent plan must bind the producer schema`
        );
        assert.deepEqual(
          scaledPlan.expected.basisWork,
          scaledAnalysis.basisWork,
          `${scaledName}: independent plan basis work must match producer receipt`
        );
        assert.deepEqual(
          scaledPlan.expected.geometryWork,
          scaledAnalysis.geometryWork,
          `${scaledName}: independent plan geometry work must match producer receipt`
        );
        assert.equal(
          scaledPlan.expected.distanceMethod,
          scaledAnalysis.distanceMethod,
          `${scaledName}: independent plan method must match producer receipt`
        );
        assert.deepEqual(
          scaledPlan.expected.distanceWork,
          scaledAnalysis.distanceWork,
          `${scaledName}: independent plan distance work must match producer receipt`
        );
        assert.equal(
          basePlan.expected.distanceMethod,
          scaledPlan.expected.distanceMethod,
          `${scaledName}: independent plan classification must remain scale-covariant`
        );
        scaledCaseCount += 1;
      }
    }
  }
}

assert.equal(baseCaseCount, 196, 'base classification matrix size must remain deterministic');
assert.equal(
  scaledCaseCount,
  784,
  'four positive power-of-two scales must be checked for every base matrix case'
);

console.log(
  `radial envelope scale covariance selftest passed (${baseCaseCount} base + ${scaledCaseCount} scaled cases)`
);
