'use strict';

const assert = require('assert');
const Envelope = require('./uc-two-projection-radial-envelope.js');
const Witness = require('./uc-two-projection-radial-envelope-witness.js');
const ActiveSet = require('./uc-two-projection-radial-envelope-active-set.js');
const ProjectionMargins = require('./uc-two-projection-radial-envelope-projection-margins.js');

function derive(firstDirection, secondDirection, firstInterval, secondInterval, options) {
  const analysis = Envelope.analyze(
    firstDirection,
    secondDirection,
    firstInterval,
    secondInterval
  );
  assert.strictEqual(analysis.supported, true);

  const witnessReceipt = Witness.derive(
    firstDirection,
    secondDirection,
    firstInterval,
    secondInterval,
    analysis,
    options
  );
  assert.strictEqual(witnessReceipt.supported, true);
  assert.strictEqual(witnessReceipt.verified, true);

  const activeSetReceipt = ActiveSet.derive(
    firstDirection,
    secondDirection,
    firstInterval,
    secondInterval,
    analysis,
    witnessReceipt,
    options
  );
  assert.strictEqual(activeSetReceipt.supported, true);
  assert.strictEqual(activeSetReceipt.verified, true);

  const receipt = ProjectionMargins.derive(
    firstDirection,
    secondDirection,
    firstInterval,
    secondInterval,
    analysis,
    witnessReceipt,
    activeSetReceipt,
    options
  );
  assert.strictEqual(receipt.supported, true);
  assert.strictEqual(receipt.verified, true);
  return { analysis, witnessReceipt, activeSetReceipt, receipt };
}

const orthonormal = derive(
  { x: 1, y: 0 },
  { x: 0, y: 1 },
  { min: 2, max: 4 },
  { min: -1, max: 3 }
);
assert.strictEqual(orthonormal.receipt.minimum.first.classification, 'boundary');
assert.strictEqual(orthonormal.receipt.minimum.first.toMin, 0);
assert.strictEqual(orthonormal.receipt.minimum.first.toMax, 2);
assert.strictEqual(orthonormal.receipt.minimum.first.strictInterior, false);
assert.strictEqual(orthonormal.receipt.minimum.second.classification, 'interior');
assert.strictEqual(orthonormal.receipt.minimum.second.toMin, 1);
assert.strictEqual(orthonormal.receipt.minimum.second.toMax, 3);
assert.strictEqual(orthonormal.receipt.minimum.second.strictInterior, true);
assert.strictEqual(orthonormal.receipt.maximum.first.toMax, 0);
assert.strictEqual(orthonormal.receipt.maximum.second.toMax, 0);
assert.strictEqual(orthonormal.receipt.maximum.activeProjectionCount, 2);

const symmetric = derive(
  { x: 1, y: 0 },
  { x: 0, y: 1 },
  { min: -1, max: 1 },
  { min: -1, max: 1 }
);
assert.strictEqual(symmetric.receipt.minimum.witnessKind, 'origin');
assert.strictEqual(symmetric.receipt.minimum.first.toMin, 1);
assert.strictEqual(symmetric.receipt.minimum.first.toMax, 1);
assert.strictEqual(symmetric.receipt.minimum.second.toMin, 1);
assert.strictEqual(symmetric.receipt.minimum.second.toMax, 1);
assert.strictEqual(symmetric.receipt.minimum.first.strictInterior, true);
assert.strictEqual(symmetric.receipt.minimum.second.strictInterior, true);
assert.strictEqual(symmetric.receipt.minimum.nearestRepresentedBoundaryGap, 1);

const originOnBoundary = derive(
  { x: 1, y: 0 },
  { x: 0, y: 1 },
  { min: 0, max: 2 },
  { min: -1, max: 1 }
);
assert.strictEqual(originOnBoundary.receipt.minimum.first.classification, 'boundary');
assert.strictEqual(originOnBoundary.receipt.minimum.first.toMin, 0);
assert.strictEqual(originOnBoundary.receipt.minimum.first.strictInterior, false);
assert.strictEqual(originOnBoundary.receipt.minimum.second.classification, 'interior');
assert.strictEqual(originOnBoundary.receipt.minimum.second.strictInterior, true);

const inverseBasis = derive(
  { x: 1, y: 0 },
  { x: 2e-10, y: 1 },
  { min: 1, max: 4 },
  { min: 2, max: 5 }
);
for (const extremum of [inverseBasis.receipt.minimum, inverseBasis.receipt.maximum]) {
  for (const axis of [extremum.first, extremum.second]) {
    assert.ok(axis.signedFeasibilityMargin >= -axis.toleranceBand);
    assert.ok(Number.isFinite(axis.nearestBoundaryGap));
  }
}
assert.strictEqual(inverseBasis.receipt.maximum.activeProjectionCount, 2);

const segment = derive(
  { x: 1, y: 0 },
  { x: 2e-10, y: 1 },
  { min: 0, max: 0 },
  { min: 2, max: 5 }
);
assert.strictEqual(segment.receipt.minimum.first.classification, 'degenerate-boundary');
assert.ok(Math.abs(segment.receipt.minimum.first.toMin) <= segment.receipt.minimum.first.toleranceBand);
assert.ok(Math.abs(segment.receipt.minimum.first.toMax) <= segment.receipt.minimum.first.toleranceBand);
assert.deepStrictEqual(segment.receipt.minimum.first.activeSides, ['min', 'max']);
assert.strictEqual(segment.receipt.minimum.first.exactDegenerateInterval, true);

const point = derive(
  { x: 1, y: 0 },
  { x: 2e-10, y: 1 },
  { min: 2, max: 2 },
  { min: 3, max: 3 }
);
for (const extremum of [point.receipt.minimum, point.receipt.maximum]) {
  for (const axis of [extremum.first, extremum.second]) {
    assert.strictEqual(axis.classification, 'degenerate-boundary');
    assert.ok(Math.abs(axis.toMin) <= axis.toleranceBand);
    assert.ok(Math.abs(axis.toMax) <= axis.toleranceBand);
    assert.ok(axis.nearestBoundaryGap <= axis.toleranceBand);
    assert.ok(axis.signedFeasibilityMargin >= -axis.toleranceBand);
    assert.deepStrictEqual(axis.activeSides, ['min', 'max']);
  }
}

const replay = ProjectionMargins.derive(
  { x: 1, y: 0 },
  { x: 2e-10, y: 1 },
  { min: 1, max: 4 },
  { min: 2, max: 5 },
  inverseBasis.analysis,
  inverseBasis.witnessReceipt,
  inverseBasis.activeSetReceipt,
  { numericTolerance: 1e-9 }
);
assert.deepStrictEqual(replay, inverseBasis.receipt);

const tamperedActiveSet = JSON.parse(JSON.stringify(inverseBasis.activeSetReceipt));
tamperedActiveSet.minimum.first.activeSides = [];
tamperedActiveSet.minimum.first.active = false;
const rejectedTamper = ProjectionMargins.derive(
  { x: 1, y: 0 },
  { x: 2e-10, y: 1 },
  { min: 1, max: 4 },
  { min: 2, max: 5 },
  inverseBasis.analysis,
  inverseBasis.witnessReceipt,
  tamperedActiveSet,
  { numericTolerance: 1e-9 }
);
assert.strictEqual(rejectedTamper.supported, false);
assert.strictEqual(rejectedTamper.reason, 'ACTIVE_SET_RECEIPT_NOT_VERIFIED');
assert.ok(rejectedTamper.activeSetVerification.violations.includes('MINIMUM_FIRST_ACTIVE_FLAG_MISMATCH'));
assert.ok(rejectedTamper.activeSetVerification.violations.includes('MINIMUM_FIRST_ACTIVE_SIDES_MISMATCH'));

const invalidTolerance = ProjectionMargins.derive(
  { x: 1, y: 0 },
  { x: 0, y: 1 },
  { min: 2, max: 4 },
  { min: -1, max: 3 },
  orthonormal.analysis,
  orthonormal.witnessReceipt,
  orthonormal.activeSetReceipt,
  { numericTolerance: -1 }
);
assert.strictEqual(invalidTolerance.supported, false);
assert.strictEqual(invalidTolerance.reason, 'ACTIVE_SET_RECEIPT_NOT_VERIFIED');
assert.strictEqual(invalidTolerance.activeSetVerification.reason, 'INVALID_NUMERIC_TOLERANCE');

console.log(JSON.stringify({
  ok: true,
  schema: ProjectionMargins.SCHEMA,
  cases: {
    orthonormalBoundaryMargins: true,
    interiorOriginMargins: true,
    boundaryOriginMargins: true,
    inverseBasisMargins: true,
    degenerateSegmentMargins: true,
    degeneratePointMargins: true,
    deterministicReplay: true,
    tamperedActiveSetRejection: true,
    invalidToleranceRejection: true
  }
}, null, 2));
