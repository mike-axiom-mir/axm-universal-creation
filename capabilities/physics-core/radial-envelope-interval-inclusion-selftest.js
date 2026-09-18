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

const expansionFixtures = [
  { name: 'first-pad-0.5', firstPad: 0.5, secondPad: 0 },
  { name: 'second-pad-0.5', firstPad: 0, secondPad: 0.5 },
  { name: 'both-pad-0.5', firstPad: 0.5, secondPad: 0.5 },
  { name: 'both-pad-4', firstPad: 4, secondPad: 4 }
];

function expandInterval(interval, padding) {
  return {
    min: interval.min - padding,
    max: interval.max + padding
  };
}

function toleranceFor(left, right) {
  return NUMERIC_TOLERANCE * Math.max(1, Math.abs(left), Math.abs(right));
}

function lessOrClose(actual, ceiling) {
  return actual <= ceiling + toleranceFor(actual, ceiling);
}

function greaterOrClose(actual, floor) {
  return actual >= floor - toleranceFor(actual, floor);
}

function valueInsideInterval(value, interval) {
  const lowerTolerance = toleranceFor(value, interval.min);
  const upperTolerance = toleranceFor(value, interval.max);
  return value >= interval.min - lowerTolerance && value <= interval.max + upperTolerance;
}

function project(point, direction) {
  return point.x * direction.x + point.y * direction.y;
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

let baseCaseCount = 0;
let expandedCaseCount = 0;
let distanceMethodTransitionCount = 0;
let originContainmentTransitionCount = 0;

for (const basis of basisFixtures) {
  for (const firstFixture of intervalFixtures) {
    for (const secondFixture of intervalFixtures) {
      const firstInterval = firstFixture.value;
      const secondInterval = secondFixture.value;
      const baseName = `${basis.name}/${firstFixture.name}/${secondFixture.name}`;

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
      requireVerified(
        baseName,
        basis.first,
        basis.second,
        firstInterval,
        secondInterval,
        baseAnalysis
      );
      baseCaseCount += 1;

      for (const expansion of expansionFixtures) {
        const expandedName = `${baseName}/${expansion.name}`;
        const expandedFirstInterval = expandInterval(firstInterval, expansion.firstPad);
        const expandedSecondInterval = expandInterval(secondInterval, expansion.secondPad);
        const expandedAnalysis = Envelope.analyze(
          basis.first,
          basis.second,
          expandedFirstInterval,
          expandedSecondInterval
        );
        assert.equal(
          expandedAnalysis.supported,
          true,
          `${expandedName}: interval expansion must remain supported`
        );

        const expandedReplay = Envelope.analyze(
          basis.first,
          basis.second,
          expandedFirstInterval,
          expandedSecondInterval
        );
        assert.deepEqual(
          expandedReplay,
          expandedAnalysis,
          `${expandedName}: expanded producer replay must be deterministic`
        );

        const expandedPlan = requireVerified(
          expandedName,
          basis.first,
          basis.second,
          expandedFirstInterval,
          expandedSecondInterval,
          expandedAnalysis
        );

        assert.equal(
          lessOrClose(expandedAnalysis.minimumDistance, baseAnalysis.minimumDistance),
          true,
          `${expandedName}: enlarging the feasible projection rectangle must not increase radial minimum`
        );
        assert.equal(
          greaterOrClose(expandedAnalysis.maximumDistance, baseAnalysis.maximumDistance),
          true,
          `${expandedName}: enlarging the feasible projection rectangle must not decrease radial maximum`
        );

        for (let index = 0; index < baseAnalysis.corners.length; index += 1) {
          const corner = baseAnalysis.corners[index];
          const firstProjection = project(corner, basis.first);
          const secondProjection = project(corner, basis.second);
          assert.equal(
            valueInsideInterval(firstProjection, expandedFirstInterval),
            true,
            `${expandedName}: base corner ${index} must remain feasible on expanded first projection interval`
          );
          assert.equal(
            valueInsideInterval(secondProjection, expandedSecondInterval),
            true,
            `${expandedName}: base corner ${index} must remain feasible on expanded second projection interval`
          );
        }

        assert.equal(
          expandedAnalysis.determinant,
          baseAnalysis.determinant,
          `${expandedName}: changing intervals must not alter represented basis determinant`
        );
        assert.deepEqual(
          expandedAnalysis.basisWork,
          baseAnalysis.basisWork,
          `${expandedName}: changing intervals must not alter basis-work classification`
        );
        assert.equal(
          expandedPlan.expected.producerSchema,
          expandedAnalysis.schema,
          `${expandedName}: independent plan must bind producer schema`
        );
        assert.deepEqual(
          expandedPlan.expected.basisWork,
          expandedAnalysis.basisWork,
          `${expandedName}: independent plan basis work must match producer receipt`
        );
        assert.deepEqual(
          expandedPlan.expected.geometryWork,
          expandedAnalysis.geometryWork,
          `${expandedName}: independent plan geometry work must match producer receipt`
        );
        assert.equal(
          expandedPlan.expected.distanceMethod,
          expandedAnalysis.distanceMethod,
          `${expandedName}: independent plan method must match producer receipt`
        );
        assert.deepEqual(
          expandedPlan.expected.distanceWork,
          expandedAnalysis.distanceWork,
          `${expandedName}: independent plan distance work must match producer receipt`
        );

        if (expandedAnalysis.distanceMethod !== baseAnalysis.distanceMethod) {
          distanceMethodTransitionCount += 1;
        }
        if (expandedAnalysis.originInsideProjectionRectangle !== baseAnalysis.originInsideProjectionRectangle) {
          originContainmentTransitionCount += 1;
        }
        expandedCaseCount += 1;
      }
    }
  }
}

assert.equal(baseCaseCount, 196, 'base classification matrix size must remain deterministic');
assert.equal(expandedCaseCount, 784, 'four interval expansions must be checked for every base matrix case');
assert.equal(
  distanceMethodTransitionCount > 0,
  true,
  'interval inclusion matrix must cross at least one public distance-method classification boundary'
);
assert.equal(
  originContainmentTransitionCount > 0,
  true,
  'interval inclusion matrix must cross at least one origin-containment structural boundary'
);

console.log(
  `radial envelope interval inclusion selftest passed (${baseCaseCount} base + ${expandedCaseCount} expanded cases; ${distanceMethodTransitionCount} method transitions; ${originContainmentTransitionCount} origin-containment transitions)`
);
