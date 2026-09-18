'use strict';

const assert = require('assert');
const Envelope = require('./uc-two-projection-radial-envelope.js');
const Witness = require('./uc-two-projection-radial-envelope-witness.js');
const ActiveSet = require('./uc-two-projection-radial-envelope-active-set.js');

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

  const receipt = ActiveSet.derive(
    firstDirection,
    secondDirection,
    firstInterval,
    secondInterval,
    analysis,
    witnessReceipt,
    options
  );
  assert.strictEqual(receipt.supported, true);
  assert.strictEqual(receipt.verified, true);
  return { analysis, witnessReceipt, receipt };
}

const orthonormal = derive(
  { x: 1, y: 0 },
  { x: 0, y: 1 },
  { min: 2, max: 4 },
  { min: -1, max: 3 }
);
assert.deepStrictEqual(orthonormal.receipt.minimum.first.activeSides, ['min']);
assert.deepStrictEqual(orthonormal.receipt.minimum.second.activeSides, []);
assert.strictEqual(orthonormal.receipt.minimum.activeProjectionCount, 1);
assert.deepStrictEqual(orthonormal.receipt.maximum.first.activeSides, ['max']);
assert.deepStrictEqual(orthonormal.receipt.maximum.second.activeSides, ['max']);
assert.strictEqual(orthonormal.receipt.maximum.activeProjectionCount, 2);

const symmetric = derive(
  { x: 1, y: 0 },
  { x: 0, y: 1 },
  { min: -1, max: 1 },
  { min: -1, max: 1 }
);
assert.strictEqual(symmetric.receipt.minimum.witnessKind, 'origin');
assert.strictEqual(symmetric.receipt.minimum.activeProjectionCount, 0);
assert.deepStrictEqual(symmetric.receipt.maximum.first.activeSides, ['min']);
assert.deepStrictEqual(symmetric.receipt.maximum.second.activeSides, ['min']);

const originOnBoundary = derive(
  { x: 1, y: 0 },
  { x: 0, y: 1 },
  { min: 0, max: 2 },
  { min: -1, max: 1 }
);
assert.strictEqual(originOnBoundary.receipt.minimum.witnessKind, 'origin');
assert.deepStrictEqual(originOnBoundary.receipt.minimum.first.activeSides, ['min']);
assert.deepStrictEqual(originOnBoundary.receipt.minimum.second.activeSides, []);
assert.strictEqual(originOnBoundary.receipt.minimum.activeProjectionCount, 1);

const inverseBasis = derive(
  { x: 1, y: 0 },
  { x: 2e-10, y: 1 },
  { min: 1, max: 4 },
  { min: 2, max: 5 }
);
assert.ok(inverseBasis.receipt.minimum.activeProjectionCount >= 1);
assert.strictEqual(inverseBasis.receipt.maximum.activeProjectionCount, 2);

const segment = derive(
  { x: 1, y: 0 },
  { x: 2e-10, y: 1 },
  { min: 0, max: 0 },
  { min: 2, max: 5 }
);
assert.deepStrictEqual(segment.receipt.minimum.first.activeSides, ['min', 'max']);
assert.strictEqual(segment.receipt.minimum.first.exactDegenerateInterval, true);
assert.ok(segment.receipt.minimum.activeProjectionCount >= 1);
assert.strictEqual(segment.receipt.maximum.activeProjectionCount, 2);

const point = derive(
  { x: 1, y: 0 },
  { x: 2e-10, y: 1 },
  { min: 2, max: 2 },
  { min: 3, max: 3 }
);
assert.deepStrictEqual(point.receipt.minimum.first.activeSides, ['min', 'max']);
assert.deepStrictEqual(point.receipt.minimum.second.activeSides, ['min', 'max']);
assert.deepStrictEqual(point.receipt.maximum.first.activeSides, ['min', 'max']);
assert.deepStrictEqual(point.receipt.maximum.second.activeSides, ['min', 'max']);
assert.strictEqual(point.receipt.minimum.activeProjectionCount, 2);
assert.strictEqual(point.receipt.maximum.activeProjectionCount, 2);

const replay = ActiveSet.derive(
  { x: 1, y: 0 },
  { x: 2e-10, y: 1 },
  { min: 1, max: 4 },
  { min: 2, max: 5 },
  inverseBasis.analysis,
  inverseBasis.witnessReceipt,
  { numericTolerance: 1e-9 }
);
assert.deepStrictEqual(replay, inverseBasis.receipt);

const tamperedWitness = JSON.parse(JSON.stringify(inverseBasis.witnessReceipt));
tamperedWitness.minimumProjections.first += 0.25;
const rejectedTamper = ActiveSet.derive(
  { x: 1, y: 0 },
  { x: 2e-10, y: 1 },
  { min: 1, max: 4 },
  { min: 2, max: 5 },
  inverseBasis.analysis,
  tamperedWitness,
  { numericTolerance: 1e-9 }
);
assert.strictEqual(rejectedTamper.supported, false);
assert.strictEqual(rejectedTamper.reason, 'WITNESS_RECEIPT_NOT_VERIFIED');
assert.ok(rejectedTamper.witnessVerification.violations.includes('MINIMUM_PROJECTION_RECEIPT_MISMATCH'));

const invalidTolerance = ActiveSet.derive(
  { x: 1, y: 0 },
  { x: 0, y: 1 },
  { min: 2, max: 4 },
  { min: -1, max: 3 },
  orthonormal.analysis,
  orthonormal.witnessReceipt,
  { numericTolerance: -1 }
);
assert.strictEqual(invalidTolerance.supported, false);
assert.strictEqual(invalidTolerance.reason, 'WITNESS_RECEIPT_NOT_VERIFIED');
assert.strictEqual(invalidTolerance.witnessVerification.reason, 'INVALID_NUMERIC_TOLERANCE');

console.log(JSON.stringify({
  ok: true,
  schema: ActiveSet.SCHEMA,
  cases: {
    orthonormalBoundaryActiveSet: true,
    interiorOriginActiveSet: true,
    boundaryOriginActiveSet: true,
    inverseBasisActiveSet: true,
    degenerateSegmentActiveSet: true,
    degeneratePointActiveSet: true,
    deterministicReplay: true,
    tamperedWitnessRejection: true,
    invalidToleranceRejection: true
  }
}, null, 2));
