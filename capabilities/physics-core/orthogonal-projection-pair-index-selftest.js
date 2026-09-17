'use strict';

const assert = require('assert');
const Core = require('./source/axm-physics-core.js');
const Preflight = require('./uc-orthogonal-projection-preflight.js');
const Guard = require('./uc-orthogonal-projection-preflight-guard.js');

function add(world, spec) {
  return Core.addBody(world, spec).world;
}

let world = Core.createWorld({ gravity: { x: 0, y: 0 }, bounds: false, sleep: { enabled: false } });
world = add(world, { id: 'a', type: 'static', position: { x: 0, y: 0 } });
world = add(world, { id: 'b', type: 'dynamic', position: { x: 1, y: 2 }, mass: 1, linearDamping: 0 });
world = add(world, { id: 'c', type: 'static', position: { x: 10, y: 0 } });
world = add(world, { id: 'd', type: 'dynamic', position: { x: 11, y: 2 }, mass: 1, linearDamping: 0 });

const constraints = {
  axisLocks: [
    { id: 'ab-x-three', a: 'a', b: 'b', axis: 'x', offset: 3 },
    { id: 'ab-y-four', a: 'a', b: 'b', axis: 'y', offset: 4 },
    { id: 'cd-x-one', a: 'c', b: 'd', axis: 'x', offset: 1 },
    { id: 'cd-y-two', a: 'c', b: 'd', axis: 'y', offset: 2 }
  ],
  distanceLimits: [
    { id: 'ab-radius-six', a: 'a', b: 'b', maxLength: 6 },
    { id: 'cd-radius-three', a: 'c', b: 'd', maxLength: 3 }
  ]
};

const report = Preflight.analyze(world, constraints);
assert.equal(report.schema, 'axm.uc-orthogonal-projection-preflight/v0.8');
assert.equal(report.version, '0.8.0');
assert.equal(report.proofGeometry, 'full-precision-normalized-singular-bounded');
assert.equal(report.conflictFree, true);
assert.equal(report.strongerProofComplete, true);
assert.equal(report.proofBudget.maxProjectionPairCandidates, null,
  'default stronger-proof candidate budget must remain unbounded');
assert.equal(report.proofBudget.exhausted, false);
assert.equal(report.counts.projectionPairBuckets, 2,
  'four projection groups across two body pairs must be indexed into exactly two canonical pair buckets');
assert.equal(report.counts.projectionMetricRecords, 4,
  'each non-conflicting projection group must get exactly one reusable metric record');
assert.equal(report.counts.projectionPairCandidatesAvailable, 2,
  'each two-projection pair bucket contributes one available candidate');
assert.equal(report.counts.projectionPairCandidates, 2,
  'unbounded/default proof must evaluate every available candidate pair');
assert.equal(report.counts.orthogonalProjectionRadialChecks, 2,
  'each radial group must reuse only its own pair bucket; cross-pair projection combinations must not be evaluated');
assert.equal(report.counts.radialMaximumChecks, 2);
assert.equal(report.counts.radialMaximumConflicts, 0);
assert.ok(report.orthogonalProjectionRadialChecks.every(check =>
  check.basisSingularValues.min === 1 && check.basisSingularValues.max === 1
), 'exact orthogonal axis pairs must retain singular values of one');
assert.ok(report.evidence.some(line => line.includes('indexed once and reused for radial lookup')),
  'receipt must expose the one-index-per-analysis lookup path');
assert.ok(report.evidence.some(line => line.includes('projection metric record(s) computed once and reused')),
  'receipt must expose one-time projection metric materialization');
assert.ok(report.evidence.some(line => line.includes('exact singular values')),
  'receipt must expose the conservative tolerance-safe basis conversion');

const replay = Preflight.analyze(world, constraints);
assert.equal(report.checksum, replay.checksum, 'pair-indexed proof planning must replay deterministically');
assert.deepEqual(report.orthogonalProjectionRadialChecks, replay.orthogonalProjectionRadialChecks);

const reuseConstraints = {
  axisLocks: [
    { id: 'ab-x-one', a: 'a', b: 'b', axis: 'x', offset: 1 },
    { id: 'ab-y-two', a: 'a', b: 'b', axis: 'y', offset: 2 }
  ],
  directionLocks: [
    { id: 'ab-diagonal-one', a: 'a', b: 'b', direction: { x: 1, y: 1 }, offset: 1 },
    { id: 'ab-diagonal-two', a: 'a', b: 'b', direction: { x: 1, y: -1 }, offset: 1 }
  ],
  distanceLimits: [
    { id: 'ab-radius-ten', a: 'a', b: 'b', maxLength: 10 }
  ]
};

const reuseReport = Preflight.analyze(world, reuseConstraints);
assert.equal(reuseReport.conflictFree, true);
assert.equal(reuseReport.strongerProofComplete, true);
assert.equal(reuseReport.counts.projectionPairBuckets, 1);
assert.equal(reuseReport.counts.projectionMetricRecords, 4,
  'four normalized projection groups must produce four metric records, not one record per pair candidate');
assert.equal(reuseReport.counts.projectionPairCandidatesAvailable, 6,
  'four same-pair projections create six available deterministic candidate pairs');
assert.equal(reuseReport.counts.projectionPairCandidates, 6,
  'default unbounded proof must evaluate all six same-pair candidate pairs');
assert.equal(reuseReport.counts.orthogonalProjectionRadialChecks, 2,
  'only x/y and the two diagonal directions are mutually orthogonal');
assert.equal(reuseReport.counts.radialMaximumChecks, 2);
assert.equal(reuseReport.counts.radialMaximumConflicts, 0);
assert.ok(reuseReport.counts.projectionMetricRecords < reuseReport.counts.projectionPairCandidates,
  'metric materialization must be reused when candidate-pair count exceeds projection-group count');

const reuseReplay = Preflight.analyze(world, reuseConstraints);
assert.equal(reuseReport.checksum, reuseReplay.checksum,
  'metric reuse planning must replay deterministically');
assert.deepEqual(reuseReport.orthogonalProjectionRadialChecks, reuseReplay.orthogonalProjectionRadialChecks);

const nearOrthogonalDirection = {
  x: 5e-7,
  y: Math.sqrt(1 - 25e-14)
};

const toleranceSafeMaximumConstraints = {
  axisLocks: [
    { id: 'safe-max-x-three', a: 'a', b: 'b', axis: 'x', offset: 3 }
  ],
  directionLocks: [
    { id: 'safe-max-near-y-four', a: 'a', b: 'b', direction: nearOrthogonalDirection, offset: 4 }
  ],
  distanceLimits: [
    { id: 'safe-max-radius', a: 'a', b: 'b', maxLength: 4.9999995 }
  ]
};

const toleranceSafeMaximum = Preflight.analyze(world, toleranceSafeMaximumConstraints, {
  orthogonalityTolerance: 1e-6
});
assert.equal(toleranceSafeMaximum.valid, true);
assert.equal(toleranceSafeMaximum.conflictFree, true,
  'strict-tolerance near-orthogonal inputs must not use raw hypot as an unsafe radial lower bound');
assert.equal(toleranceSafeMaximum.counts.radialMaximumChecks, 1);
assert.equal(toleranceSafeMaximum.counts.radialMaximumConflicts, 0);
const maximumCheck = toleranceSafeMaximum.orthogonalProjectionRadialChecks[0].radialMaximumCheck;
assert.ok(maximumCheck.projectionMagnitudeLowerBound > maximumCheck.maximumAllowedDistance,
  'the old raw projection-vector hypot would have exceeded the radial maximum in this regression');
assert.ok(maximumCheck.minimumRequiredDistance < maximumCheck.maximumAllowedDistance,
  'singular-value correction must conservatively reduce the radial lower bound at the tolerance edge');
assert.ok(maximumCheck.decisionWitness.basisSingularValues.max > 1,
  'decision witness must retain the full-precision operator expansion used by the lower bound');

const toleranceSafeMinimumConstraints = {
  axisLimits: [
    { id: 'safe-min-x-range', a: 'a', b: 'b', axis: 'x', minOffset: -2, maxOffset: 2 }
  ],
  directionLimits: [
    { id: 'safe-min-near-y-range', a: 'a', b: 'b', direction: nearOrthogonalDirection, minOffset: -2, maxOffset: 2 }
  ],
  distanceLimits: [
    { id: 'safe-min-radius', a: 'a', b: 'b', minLength: 2.8284275 }
  ]
};

const toleranceSafeMinimum = Preflight.analyze(world, toleranceSafeMinimumConstraints, {
  orthogonalityTolerance: 1e-6
});
assert.equal(toleranceSafeMinimum.valid, true);
assert.equal(toleranceSafeMinimum.conflictFree, true,
  'strict-tolerance near-orthogonal inputs must not use raw hypot as an unsafe radial upper bound');
assert.equal(toleranceSafeMinimum.counts.radialMinimumChecks, 1);
assert.equal(toleranceSafeMinimum.counts.radialMinimumConflicts, 0);
const minimumCheck = toleranceSafeMinimum.orthogonalProjectionRadialChecks[0].radialMinimumCheck;
assert.ok(minimumCheck.projectionMagnitudeUpperBound < minimumCheck.minimumAllowedDistance,
  'the old raw projection-vector hypot would have fallen below the radial minimum in this regression');
assert.ok(minimumCheck.maximumPossibleDistance > minimumCheck.minimumAllowedDistance,
  'singular-value correction must conservatively expand the radial upper bound at the tolerance edge');
assert.ok(minimumCheck.decisionWitness.basisSingularValues.min < 1,
  'decision witness must retain the full-precision inverse-basis contraction used by the upper bound');

const toleranceSafeReplay = Preflight.analyze(world, toleranceSafeMaximumConstraints, {
  orthogonalityTolerance: 1e-6
});
assert.equal(toleranceSafeMaximum.checksum, toleranceSafeReplay.checksum,
  'tolerance-safe singular-bound proof must replay deterministically');

const budgetConstraints = {
  axisLocks: [
    { id: 'budget-x-zero', a: 'a', b: 'b', axis: 'x', offset: 0 },
    { id: 'budget-y-zero', a: 'a', b: 'b', axis: 'y', offset: 0 }
  ],
  directionLocks: [
    { id: 'budget-diagonal-zero', a: 'a', b: 'b', direction: { x: 1, y: 1 }, offset: 0 },
    { id: 'budget-other-diagonal-zero', a: 'a', b: 'b', direction: { x: 1, y: -1 }, offset: 0 }
  ],
  distanceLimits: [
    { id: 'budget-radius-ten', a: 'a', b: 'b', maxLength: 10 }
  ]
};

const budgeted = Preflight.analyze(world, budgetConstraints, { maxProjectionPairCandidates: 2 });
assert.equal(budgeted.valid, true);
assert.equal(budgeted.conflictFree, true,
  'budget exhaustion is not contradiction evidence by itself');
assert.equal(budgeted.ok, false,
  'an incomplete stronger proof must not report the overall extended receipt as ok');
assert.equal(budgeted.strongerProofComplete, false);
assert.equal(budgeted.proofBudget.maxProjectionPairCandidates, 2);
assert.equal(budgeted.proofBudget.exhausted, true);
assert.equal(budgeted.counts.projectionPairCandidatesAvailable, 6);
assert.equal(budgeted.counts.projectionPairCandidates, 2,
  'explicit proof budget must stop after exactly the configured deterministic candidate count');
assert.ok(budgeted.evidence.some(line => line.includes('coverage is incomplete')),
  'budget exhaustion must be explicit evidence rather than silently treated as a complete proof');

const budgetReplay = Preflight.analyze(world, budgetConstraints, { maxProjectionPairCandidates: 2 });
assert.equal(budgeted.checksum, budgetReplay.checksum,
  'budgeted proof truncation must replay deterministically');

const budgetGuardWorld = Core.cloneWorld ? Core.cloneWorld(world) : world;
const budgetGuardBefore = Core.checksum(budgetGuardWorld);
const budgetGuard = Guard.step(
  budgetGuardWorld,
  budgetConstraints,
  1 / 60,
  { preflight: { maxProjectionPairCandidates: 2 } }
);
assert.equal(budgetGuard.accepted, false);
assert.equal(budgetGuard.blocked, true);
assert.equal(budgetGuard.reason, 'ORTHOGONAL_PROOF_BUDGET_EXHAUSTED');
assert.equal(budgetGuard.coreStepExecuted, false);
assert.equal(budgetGuard.worldChecksumBefore, budgetGuardBefore);
assert.equal(budgetGuard.worldChecksumAfter, budgetGuardBefore);
assert.equal(Core.checksum(budgetGuardWorld), budgetGuardBefore,
  'fail-closed budget exhaustion must preserve caller world state');

console.log('orthogonal projection pair index selftest passed');
