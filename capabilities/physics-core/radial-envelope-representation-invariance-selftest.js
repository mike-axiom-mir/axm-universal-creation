'use strict';

const assert = require('assert');
const Envelope = require('./uc-two-projection-radial-envelope.js');
const ReceiptVerifier = require('./uc-two-projection-radial-envelope-verifier.js');
const PlanVerifier = require('./uc-two-projection-radial-envelope-plan-verifier.js');

const NUMERIC_TOLERANCE = 1e-9;
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

function negateDirection(direction) {
  return { x: -direction.x, y: -direction.y };
}

function negateInterval(interval) {
  return { min: -interval.max, max: -interval.min };
}

function rotateQuarterTurn(direction) {
  return { x: -direction.y, y: direction.x };
}

function closeEnough(actual, expected) {
  const scale = Math.max(1, Math.abs(actual), Math.abs(expected));
  return Math.abs(actual - expected) <= NUMERIC_TOLERANCE * scale;
}

const transforms = [
  {
    name: 'flip-first-representation',
    apply(firstDirection, secondDirection, firstInterval, secondInterval) {
      return {
        firstDirection: negateDirection(firstDirection),
        secondDirection,
        firstInterval: negateInterval(firstInterval),
        secondInterval
      };
    }
  },
  {
    name: 'flip-second-representation',
    apply(firstDirection, secondDirection, firstInterval, secondInterval) {
      return {
        firstDirection,
        secondDirection: negateDirection(secondDirection),
        firstInterval,
        secondInterval: negateInterval(secondInterval)
      };
    }
  },
  {
    name: 'swap-projection-order',
    apply(firstDirection, secondDirection, firstInterval, secondInterval) {
      return {
        firstDirection: secondDirection,
        secondDirection: firstDirection,
        firstInterval: secondInterval,
        secondInterval: firstInterval
      };
    }
  },
  {
    name: 'rotate-quarter-turn',
    apply(firstDirection, secondDirection, firstInterval, secondInterval) {
      return {
        firstDirection: rotateQuarterTurn(firstDirection),
        secondDirection: rotateQuarterTurn(secondDirection),
        firstInterval,
        secondInterval
      };
    }
  }
];

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

let baseCaseCount = 0;
let transformedCaseCount = 0;
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
      const basePlan = requireVerified(
        baseName,
        basis.first,
        basis.second,
        firstInterval,
        secondInterval,
        baseAnalysis
      );
      baseCaseCount += 1;

      for (const transform of transforms) {
        const transformed = transform.apply(
          basis.first,
          basis.second,
          firstInterval,
          secondInterval
        );
        const transformedName = `${baseName}/${transform.name}`;
        const transformedAnalysis = Envelope.analyze(
          transformed.firstDirection,
          transformed.secondDirection,
          transformed.firstInterval,
          transformed.secondInterval
        );
        assert.equal(
          transformedAnalysis.supported,
          true,
          `${transformedName}: transformed producer must stay supported`
        );

        const replay = Envelope.analyze(
          transformed.firstDirection,
          transformed.secondDirection,
          transformed.firstInterval,
          transformed.secondInterval
        );
        assert.deepEqual(
          replay,
          transformedAnalysis,
          `${transformedName}: transformed producer replay must be deterministic`
        );

        const transformedPlan = requireVerified(
          transformedName,
          transformed.firstDirection,
          transformed.secondDirection,
          transformed.firstInterval,
          transformed.secondInterval,
          transformedAnalysis
        );

        assert.equal(
          closeEnough(transformedAnalysis.minimumDistance, baseAnalysis.minimumDistance),
          true,
          `${transformedName}: radial minimum must be invariant under equivalent representation`
        );
        assert.equal(
          closeEnough(transformedAnalysis.maximumDistance, baseAnalysis.maximumDistance),
          true,
          `${transformedName}: radial maximum must be invariant under equivalent representation`
        );
        assert.equal(
          transformedAnalysis.distanceMethod,
          baseAnalysis.distanceMethod,
          `${transformedName}: equivalent representation must retain distance-method classification`
        );
        assert.deepEqual(
          transformedAnalysis.basisWork,
          baseAnalysis.basisWork,
          `${transformedName}: equivalent representation must retain basis-work classification`
        );
        assert.deepEqual(
          transformedAnalysis.geometryWork,
          baseAnalysis.geometryWork,
          `${transformedName}: equivalent representation must retain geometry-work classification`
        );
        assert.deepEqual(
          transformedAnalysis.distanceWork,
          baseAnalysis.distanceWork,
          `${transformedName}: equivalent representation must retain distance-work classification`
        );

        assert.equal(
          transformedPlan.expected.producerSchema,
          transformedAnalysis.schema,
          `${transformedName}: independent plan must bind the producer schema`
        );
        assert.deepEqual(
          transformedPlan.expected.basisWork,
          transformedAnalysis.basisWork,
          `${transformedName}: independent plan basis work must match producer receipt`
        );
        assert.deepEqual(
          transformedPlan.expected.geometryWork,
          transformedAnalysis.geometryWork,
          `${transformedName}: independent plan geometry work must match producer receipt`
        );
        assert.equal(
          transformedPlan.expected.distanceMethod,
          transformedAnalysis.distanceMethod,
          `${transformedName}: independent plan method must match producer receipt`
        );
        assert.deepEqual(
          transformedPlan.expected.distanceWork,
          transformedAnalysis.distanceWork,
          `${transformedName}: independent plan distance work must match producer receipt`
        );
        assert.equal(
          basePlan.expected.distanceMethod,
          transformedPlan.expected.distanceMethod,
          `${transformedName}: independent plan classification must be representation-invariant`
        );
        transformedCaseCount += 1;
      }
    }
  }
}

assert.equal(baseCaseCount, 196, 'base representation matrix size must remain deterministic');
assert.equal(
  transformedCaseCount,
  784,
  'four exact representation transforms must be checked for every base matrix case'
);

console.log(
  `radial envelope representation invariance selftest passed (${baseCaseCount} base + ${transformedCaseCount} transformed cases)`
);
