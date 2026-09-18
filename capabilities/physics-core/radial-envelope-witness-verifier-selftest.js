'use strict';

const assert = require('assert');
const Envelope = require('./uc-two-projection-radial-envelope.js');
const Witness = require('./uc-two-projection-radial-envelope-witness.js');
const WitnessVerifier = require('./uc-two-projection-radial-envelope-witness-verifier.js');

const TOLERANCE = 1e-9;

function dot(direction, point) {
  return direction.x * point.x + direction.y * point.y;
}

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function build(firstDirection, secondDirection, firstInterval, secondInterval) {
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
    { numericTolerance: TOLERANCE }
  );
  assert.strictEqual(witnessReceipt.supported, true);
  assert.strictEqual(witnessReceipt.verified, true);

  const verification = WitnessVerifier.verify(
    firstDirection,
    secondDirection,
    firstInterval,
    secondInterval,
    analysis,
    witnessReceipt,
    { numericTolerance: TOLERANCE }
  );
  assert.strictEqual(verification.verified, true, JSON.stringify(verification, null, 2));
  assert.deepStrictEqual(verification.violations, []);

  return {
    firstDirection,
    secondDirection,
    firstInterval,
    secondInterval,
    analysis,
    witnessReceipt,
    verification
  };
}

const orthonormal = build(
  { x: 1, y: 0 },
  { x: 0, y: 1 },
  { min: 2, max: 4 },
  { min: -1, max: 3 }
);

const symmetricTie = build(
  { x: 1, y: 0 },
  { x: 0, y: 1 },
  { min: -1, max: 1 },
  { min: -1, max: 1 }
);

const inverseBasis = build(
  { x: 1, y: 0 },
  { x: 2e-10, y: 1 },
  { min: 1, max: 4 },
  { min: 2, max: 5 }
);

const segment = build(
  { x: 1, y: 0 },
  { x: 2e-10, y: 1 },
  { min: 0, max: 0 },
  { min: 2, max: 5 }
);

const point = build(
  { x: 1, y: 0 },
  { x: 2e-10, y: 1 },
  { min: 2, max: 2 },
  { min: 3, max: 3 }
);

const replay = WitnessVerifier.verify(
  inverseBasis.firstDirection,
  inverseBasis.secondDirection,
  inverseBasis.firstInterval,
  inverseBasis.secondInterval,
  inverseBasis.analysis,
  inverseBasis.witnessReceipt,
  { numericTolerance: TOLERANCE }
);
assert.deepStrictEqual(replay, inverseBasis.verification);

const tamperedMinimumPoint = clone(orthonormal.witnessReceipt);
tamperedMinimumPoint.minimumWitness.point.x += 0.25;
const rejectedMinimumPoint = WitnessVerifier.verify(
  orthonormal.firstDirection,
  orthonormal.secondDirection,
  orthonormal.firstInterval,
  orthonormal.secondInterval,
  orthonormal.analysis,
  tamperedMinimumPoint,
  { numericTolerance: TOLERANCE }
);
assert.strictEqual(rejectedMinimumPoint.verified, false);
assert.ok(rejectedMinimumPoint.violations.includes('MINIMUM_POINT_MISMATCH'));
assert.ok(rejectedMinimumPoint.violations.includes('MINIMUM_PROJECTION_RECEIPT_MISMATCH'));

const tamperedSegmentParameter = clone(orthonormal.witnessReceipt);
tamperedSegmentParameter.minimumWitness.segmentParameter += 0.25;
const rejectedSegmentParameter = WitnessVerifier.verify(
  orthonormal.firstDirection,
  orthonormal.secondDirection,
  orthonormal.firstInterval,
  orthonormal.secondInterval,
  orthonormal.analysis,
  tamperedSegmentParameter,
  { numericTolerance: TOLERANCE }
);
assert.strictEqual(rejectedSegmentParameter.verified, false);
assert.ok(rejectedSegmentParameter.violations.includes('MINIMUM_SEGMENT_PARAMETER_MISMATCH'));

const tamperedMaximumTie = clone(symmetricTie.witnessReceipt);
const alternateMaximumCorner = symmetricTie.analysis.corners[1];
tamperedMaximumTie.maximumWitness.cornerIndex = 1;
tamperedMaximumTie.maximumWitness.point = {
  x: alternateMaximumCorner.x,
  y: alternateMaximumCorner.y
};
tamperedMaximumTie.maximumProjections = {
  first: dot(symmetricTie.firstDirection, alternateMaximumCorner),
  second: dot(symmetricTie.secondDirection, alternateMaximumCorner)
};
const rejectedMaximumTie = WitnessVerifier.verify(
  symmetricTie.firstDirection,
  symmetricTie.secondDirection,
  symmetricTie.firstInterval,
  symmetricTie.secondInterval,
  symmetricTie.analysis,
  tamperedMaximumTie,
  { numericTolerance: TOLERANCE }
);
assert.strictEqual(rejectedMaximumTie.verified, false);
assert.ok(rejectedMaximumTie.violations.includes('MAXIMUM_CORNER_INDEX_MISMATCH'));

const tamperedProjectionEvidence = clone(inverseBasis.witnessReceipt);
tamperedProjectionEvidence.minimumProjections.first += 0.5;
const rejectedProjectionEvidence = WitnessVerifier.verify(
  inverseBasis.firstDirection,
  inverseBasis.secondDirection,
  inverseBasis.firstInterval,
  inverseBasis.secondInterval,
  inverseBasis.analysis,
  tamperedProjectionEvidence,
  { numericTolerance: TOLERANCE }
);
assert.strictEqual(rejectedProjectionEvidence.verified, false);
assert.ok(rejectedProjectionEvidence.violations.includes('MINIMUM_PROJECTION_RECEIPT_MISMATCH'));

const tamperedEmbeddedBase = clone(point.witnessReceipt);
tamperedEmbeddedBase.baseReceipt.expectedMaximumDistance += 1;
const rejectedEmbeddedBase = WitnessVerifier.verify(
  point.firstDirection,
  point.secondDirection,
  point.firstInterval,
  point.secondInterval,
  point.analysis,
  tamperedEmbeddedBase,
  { numericTolerance: TOLERANCE }
);
assert.strictEqual(rejectedEmbeddedBase.verified, false);
assert.ok(rejectedEmbeddedBase.violations.includes('EMBEDDED_BASE_RECEIPT_MISMATCH'));

const tamperedAnalysis = clone(segment.analysis);
tamperedAnalysis.minimumDistance += 0.5;
const rejectedBaseReceipt = WitnessVerifier.verify(
  segment.firstDirection,
  segment.secondDirection,
  segment.firstInterval,
  segment.secondInterval,
  tamperedAnalysis,
  segment.witnessReceipt,
  { numericTolerance: TOLERANCE }
);
assert.strictEqual(rejectedBaseReceipt.verified, false);
assert.strictEqual(rejectedBaseReceipt.reason, 'BASE_RECEIPT_NOT_VERIFIED');

const rejectedMissingWitness = WitnessVerifier.verify(
  orthonormal.firstDirection,
  orthonormal.secondDirection,
  orthonormal.firstInterval,
  orthonormal.secondInterval,
  orthonormal.analysis,
  null,
  { numericTolerance: TOLERANCE }
);
assert.strictEqual(rejectedMissingWitness.verified, false);
assert.strictEqual(rejectedMissingWitness.reason, 'WITNESS_RECEIPT_NOT_SUPPORTED');

const rejectedTolerance = WitnessVerifier.verify(
  orthonormal.firstDirection,
  orthonormal.secondDirection,
  orthonormal.firstInterval,
  orthonormal.secondInterval,
  orthonormal.analysis,
  orthonormal.witnessReceipt,
  { numericTolerance: -1 }
);
assert.strictEqual(rejectedTolerance.verified, false);
assert.strictEqual(rejectedTolerance.reason, 'INVALID_NUMERIC_TOLERANCE');

console.log(JSON.stringify({
  ok: true,
  schema: WitnessVerifier.SCHEMA,
  validCases: {
    orthonormalBoundaryWitness: true,
    originContainedTieWitness: true,
    toleranceEligibleInverseBasisWitness: true,
    degenerateSegmentWitness: true,
    degeneratePointWitness: true,
    deterministicReplay: true
  },
  tamperCases: {
    minimumPointMismatch: true,
    minimumSegmentParameterMismatch: true,
    maximumTieBreakMismatch: true,
    projectionReceiptMismatch: true,
    embeddedBaseReceiptMismatch: true,
    baseReceiptRejection: true,
    missingWitnessRejection: true,
    invalidToleranceRejection: true
  }
}, null, 2));
