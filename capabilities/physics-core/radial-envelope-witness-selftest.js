'use strict';

const assert = require('assert');
const Envelope = require('./uc-two-projection-radial-envelope.js');
const Witness = require('./uc-two-projection-radial-envelope-witness.js');

function derive(firstDirection, secondDirection, firstInterval, secondInterval, options) {
  const analysis = Envelope.analyze(
    firstDirection,
    secondDirection,
    firstInterval,
    secondInterval
  );
  assert.strictEqual(analysis.supported, true);
  const receipt = Witness.derive(
    firstDirection,
    secondDirection,
    firstInterval,
    secondInterval,
    analysis,
    options
  );
  assert.strictEqual(receipt.supported, true);
  assert.strictEqual(receipt.verified, true);
  return { analysis, receipt };
}

function near(actual, expected, tolerance = 1e-9) {
  const scale = Math.max(1, Math.abs(actual), Math.abs(expected));
  assert.ok(Math.abs(actual - expected) <= tolerance * scale, `${actual} != ${expected}`);
}

const orthonormal = derive(
  { x: 1, y: 0 },
  { x: 0, y: 1 },
  { min: 2, max: 4 },
  { min: -1, max: 3 }
);
assert.strictEqual(orthonormal.receipt.minimumWitness.kind, 'boundary-segment');
assert.strictEqual(orthonormal.receipt.minimumWitness.boundaryEdgeIndex, 3);
near(orthonormal.receipt.minimumWitness.point.x, 2);
near(orthonormal.receipt.minimumWitness.point.y, 0);
near(orthonormal.receipt.minimumWitness.distance, 2);
assert.strictEqual(orthonormal.receipt.maximumWitness.cornerIndex, 2);
near(orthonormal.receipt.maximumWitness.point.x, 4);
near(orthonormal.receipt.maximumWitness.point.y, 3);
near(orthonormal.receipt.maximumWitness.distance, 5);

const symmetricTie = derive(
  { x: 1, y: 0 },
  { x: 0, y: 1 },
  { min: -1, max: 1 },
  { min: -1, max: 1 }
);
assert.strictEqual(symmetricTie.receipt.minimumWitness.kind, 'origin');
assert.deepStrictEqual(symmetricTie.receipt.minimumWitness.point, { x: 0, y: 0 });
assert.strictEqual(symmetricTie.receipt.maximumWitness.cornerIndex, 0);
near(symmetricTie.receipt.maximumWitness.distance, Math.SQRT2);

const inverseBasis = derive(
  { x: 1, y: 0 },
  { x: 2e-10, y: 1 },
  { min: 1, max: 4 },
  { min: 2, max: 5 }
);
near(inverseBasis.receipt.minimumWitness.distance, inverseBasis.analysis.minimumDistance);
near(inverseBasis.receipt.maximumWitness.distance, inverseBasis.analysis.maximumDistance);
assert.strictEqual(inverseBasis.receipt.minimumWitness.kind, 'boundary-segment');
assert.strictEqual(inverseBasis.receipt.maximumWitness.kind, 'corner');

const segment = derive(
  { x: 1, y: 0 },
  { x: 2e-10, y: 1 },
  { min: 0, max: 0 },
  { min: 2, max: 5 }
);
assert.strictEqual(segment.receipt.minimumWitness.kind, 'boundary-segment');
assert.strictEqual(segment.receipt.minimumWitness.boundaryEdgeIndex, 0);
near(segment.receipt.minimumWitness.distance, segment.analysis.minimumDistance);
near(segment.receipt.maximumWitness.distance, segment.analysis.maximumDistance);

const point = derive(
  { x: 1, y: 0 },
  { x: 2e-10, y: 1 },
  { min: 2, max: 2 },
  { min: 3, max: 3 }
);
assert.strictEqual(point.receipt.minimumWitness.boundaryEdgeIndex, 0);
assert.strictEqual(point.receipt.maximumWitness.cornerIndex, 0);
near(point.receipt.minimumWitness.distance, point.receipt.maximumWitness.distance);

const replay = Witness.derive(
  { x: 1, y: 0 },
  { x: 2e-10, y: 1 },
  { min: 1, max: 4 },
  { min: 2, max: 5 },
  inverseBasis.analysis,
  { numericTolerance: 1e-9 }
);
assert.deepStrictEqual(replay, inverseBasis.receipt);

const tampered = JSON.parse(JSON.stringify(inverseBasis.analysis));
tampered.maximumDistance += 0.5;
const rejectedTamper = Witness.derive(
  { x: 1, y: 0 },
  { x: 2e-10, y: 1 },
  { min: 1, max: 4 },
  { min: 2, max: 5 },
  tampered,
  { numericTolerance: 1e-9 }
);
assert.strictEqual(rejectedTamper.supported, false);
assert.strictEqual(rejectedTamper.reason, 'BASE_RECEIPT_NOT_VERIFIED');
assert.ok(rejectedTamper.baseReceipt.violations.includes('MAXIMUM_DISTANCE_MISMATCH'));

const invalidTolerance = Witness.derive(
  { x: 1, y: 0 },
  { x: 0, y: 1 },
  { min: 2, max: 4 },
  { min: -1, max: 3 },
  orthonormal.analysis,
  { numericTolerance: -1 }
);
assert.strictEqual(invalidTolerance.supported, false);
assert.strictEqual(invalidTolerance.reason, 'BASE_RECEIPT_NOT_VERIFIED');
assert.strictEqual(invalidTolerance.baseReceipt.reason, 'INVALID_NUMERIC_TOLERANCE');

console.log(JSON.stringify({
  ok: true,
  schema: Witness.SCHEMA,
  cases: {
    orthonormalBoundaryWitness: true,
    exactOriginWitness: true,
    deterministicCornerTieBreak: true,
    inverseBasisWitnesses: true,
    degenerateSegmentWitness: true,
    degeneratePointWitness: true,
    deterministicReplay: true,
    tamperRejection: true,
    invalidToleranceRejection: true
  }
}, null, 2));
