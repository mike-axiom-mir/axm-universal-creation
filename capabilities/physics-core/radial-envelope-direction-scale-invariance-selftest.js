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

const transforms = [
  { name: 'first-times-2', firstScale: 2, secondScale: 1 },
  { name: 'second-times-half', firstScale: 1, secondScale: 0.5 },
  { name: 'reciprocal-axis-scale', firstScale: 0.5, secondScale: 2 },
  { name: 'both-times-2', firstScale: 2, secondScale: 2 }
];

const structuralFields = [
  'degenerateProjectionIntervals',
  'zeroContainingProjectionIntervals',
  'originInsideProjectionRectangle',
  'centrallySymmetricProjectionRectangle',
  'exactOriginPoint',
  'originSymmetricSegmentThroughOrigin'
];

function scaleDirection(direction, factor) {
  return {
    x: direction.x * factor,
    y: direction.y * factor
  };
}

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

let baseCaseCount = 0;
let transformedCaseCount = 0;
let distanceMethodTransitions = 0;
let basisWorkTransitions = 0;

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
      requireVerified(
        baseName,
        basis.first,
        basis.second,
        firstInterval,
        secondInterval,
        baseAnalysis
      );
      baseCaseCount += 1;

      for (const transform of transforms) {
        const transformedName = `${baseName}/${transform.name}`;
        const firstDirection = scaleDirection(basis.first, transform.firstScale);
        const secondDirection = scaleDirection(basis.second, transform.secondScale);
        const transformedFirstInterval = scaleInterval(firstInterval, transform.firstScale);
        const transformedSecondInterval = scaleInterval(secondInterval, transform.secondScale);
        const transformedAnalysis = Envelope.analyze(
          firstDirection,
          secondDirection,
          transformedFirstInterval,
          transformedSecondInterval
        );
        assert.equal(
          transformedAnalysis.supported,
          true,
          `${transformedName}: positively rescaled representation must stay supported`
        );

        const replay = Envelope.analyze(
          firstDirection,
          secondDirection,
          transformedFirstInterval,
          transformedSecondInterval
        );
        assert.deepEqual(
          replay,
          transformedAnalysis,
          `${transformedName}: transformed producer replay must be deterministic`
        );

        const transformedPlan = requireVerified(
          transformedName,
          firstDirection,
          secondDirection,
          transformedFirstInterval,
          transformedSecondInterval,
          transformedAnalysis
        );

        assert.equal(
          closeEnough(transformedAnalysis.minimumDistance, baseAnalysis.minimumDistance),
          true,
          `${transformedName}: positive direction/interval rescaling must preserve radial minimum`
        );
        assert.equal(
          closeEnough(transformedAnalysis.maximumDistance, baseAnalysis.maximumDistance),
          true,
          `${transformedName}: positive direction/interval rescaling must preserve radial maximum`
        );

        assert.equal(
          transformedAnalysis.corners.length,
          baseAnalysis.corners.length,
          `${transformedName}: transformed receipt must retain four corner evidence slots`
        );
        for (let index = 0; index < baseAnalysis.corners.length; index += 1) {
          assert.equal(
            closeEnough(transformedAnalysis.corners[index].x, baseAnalysis.corners[index].x),
            true,
            `${transformedName}: corner ${index} x must remain world-space invariant`
          );
          assert.equal(
            closeEnough(transformedAnalysis.corners[index].y, baseAnalysis.corners[index].y),
            true,
            `${transformedName}: corner ${index} y must remain world-space invariant`
          );
        }

        assert.equal(
          closeEnough(
            transformedAnalysis.determinant,
            baseAnalysis.determinant * transform.firstScale * transform.secondScale
          ),
          true,
          `${transformedName}: represented determinant must scale with both direction factors`
        );

        for (const field of structuralFields) {
          assert.deepEqual(
            transformedAnalysis[field],
            baseAnalysis[field],
            `${transformedName}: positive representation scaling must retain structural field ${field}`
          );
        }

        assert.deepEqual(
          transformedAnalysis.geometryWork,
          baseAnalysis.geometryWork,
          `${transformedName}: equivalent represented set must retain geometry-work classification`
        );
        assert.deepEqual(
          transformedAnalysis.distanceWork,
          baseAnalysis.distanceWork,
          `${transformedName}: equivalent represented set must retain distance-work classification`
        );

        if (transformedAnalysis.distanceMethod !== baseAnalysis.distanceMethod) {
          distanceMethodTransitions += 1;
        }
        if (JSON.stringify(transformedAnalysis.basisWork) !== JSON.stringify(baseAnalysis.basisWork)) {
          basisWorkTransitions += 1;
        }

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

        transformedCaseCount += 1;
      }
    }
  }
}

assert.equal(baseCaseCount, 196, 'base classification matrix size must remain deterministic');
assert.equal(
  transformedCaseCount,
  784,
  'four positive direction/interval representation scales must be checked for every base matrix case'
);
assert.equal(
  distanceMethodTransitions > 0,
  true,
  'matrix must exercise at least one public distance-method transition while preserving world geometry'
);
assert.equal(
  basisWorkTransitions > 0,
  true,
  'matrix must exercise at least one basis-work transition while preserving world geometry'
);

console.log(
  `radial envelope direction-scale invariance selftest passed (${baseCaseCount} base + ${transformedCaseCount} transformed cases; ${distanceMethodTransitions} method transitions, ${basisWorkTransitions} basis-work transitions)`
);
