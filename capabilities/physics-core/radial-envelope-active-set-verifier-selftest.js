'use strict';

const assert = require('assert');
const Envelope = require('./uc-two-projection-radial-envelope.js');
const Witness = require('./uc-two-projection-radial-envelope-witness.js');
const ActiveSet = require('./uc-two-projection-radial-envelope-active-set.js');
const ActiveSetVerifier = require('./uc-two-projection-radial-envelope-active-set-verifier.js');

function build(firstDirection, secondDirection, firstInterval, secondInterval, options) {
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

  const verification = ActiveSetVerifier.verify(
    firstDirection,
    secondDirection,
    firstInterval,
    secondInterval,
    analysis,
    witnessReceipt,
    activeSetReceipt,
    options
  );
  assert.strictEqual(verification.verified, true);
  assert.deepStrictEqual(verification.violations, []);

  return {
    firstDirection,
    secondDirection,
    firstInterval,
    secondInterval,
    analysis,
    witnessReceipt,
    activeSetReceipt,
    verification
  };
}

function verifyCase(fixture, activeSetReceipt, witnessReceipt, options) {
  return ActiveSetVerifier.verify(
    fixture.firstDirection,
    fixture.secondDirection,
    fixture.firstInterval,
    fixture.secondInterval,
    fixture.analysis,
    witnessReceipt || fixture.witnessReceipt,
    activeSetReceipt,
    options || { numericTolerance: 1e-9 }
  );
}

const orthonormal = build(
  { x: 1, y: 0 },
  { x: 0, y: 1 },
  { min: 2, max: 4 },
  { min: -1, max: 3 },
  { numericTolerance: 1e-9 }
);
assert.deepStrictEqual(orthonormal.verification.expectedMinimum.first.activeSides, ['min']);
assert.deepStrictEqual(orthonormal.verification.expectedMinimum.second.activeSides, []);
assert.deepStrictEqual(orthonormal.verification.expectedMaximum.first.activeSides, ['max']);
assert.deepStrictEqual(orthonormal.verification.expectedMaximum.second.activeSides, ['max']);

const symmetric = build(
  { x: 1, y: 0 },
  { x: 0, y: 1 },
  { min: -1, max: 1 },
  { min: -1, max: 1 },
  { numericTolerance: 1e-9 }
);
assert.strictEqual(symmetric.verification.expectedMinimum.activeProjectionCount, 0);
assert.strictEqual(symmetric.verification.expectedMaximum.activeProjectionCount, 2);

const inverseBasis = build(
  { x: 1, y: 0 },
  { x: 2e-10, y: 1 },
  { min: 1, max: 4 },
  { min: 2, max: 5 },
  { numericTolerance: 1e-9 }
);
assert.ok(inverseBasis.verification.expectedMinimum.activeProjectionCount >= 1);
assert.strictEqual(inverseBasis.verification.expectedMaximum.activeProjectionCount, 2);

const segment = build(
  { x: 1, y: 0 },
  { x: 2e-10, y: 1 },
  { min: 0, max: 0 },
  { min: 2, max: 5 },
  { numericTolerance: 1e-9 }
);
assert.deepStrictEqual(segment.verification.expectedMinimum.first.activeSides, ['min', 'max']);
assert.strictEqual(segment.verification.expectedMinimum.first.exactDegenerateInterval, true);

const point = build(
  { x: 1, y: 0 },
  { x: 2e-10, y: 1 },
  { min: 2, max: 2 },
  { min: 3, max: 3 },
  { numericTolerance: 1e-9 }
);
assert.deepStrictEqual(point.verification.expectedMinimum.first.activeSides, ['min', 'max']);
assert.deepStrictEqual(point.verification.expectedMinimum.second.activeSides, ['min', 'max']);
assert.deepStrictEqual(point.verification.expectedMaximum.first.activeSides, ['min', 'max']);
assert.deepStrictEqual(point.verification.expectedMaximum.second.activeSides, ['min', 'max']);

const replay = ActiveSetVerifier.verify(
  inverseBasis.firstDirection,
  inverseBasis.secondDirection,
  inverseBasis.firstInterval,
  inverseBasis.secondInterval,
  inverseBasis.analysis,
  inverseBasis.witnessReceipt,
  inverseBasis.activeSetReceipt,
  { numericTolerance: 1e-9 }
);
assert.deepStrictEqual(replay, inverseBasis.verification);

const tamperedProjection = JSON.parse(JSON.stringify(inverseBasis.activeSetReceipt));
tamperedProjection.minimum.first.projection += 0.25;
let rejected = verifyCase(inverseBasis, tamperedProjection);
assert.strictEqual(rejected.verified, false);
assert.strictEqual(rejected.reason, 'ACTIVE_SET_RECEIPT_INCONSISTENT');
assert.ok(rejected.violations.includes('MINIMUM_FIRST_PROJECTION_MISMATCH'));

const tamperedSides = JSON.parse(JSON.stringify(inverseBasis.activeSetReceipt));
tamperedSides.maximum.second.activeSides = [];
rejected = verifyCase(inverseBasis, tamperedSides);
assert.strictEqual(rejected.verified, false);
assert.ok(rejected.violations.includes('MAXIMUM_SECOND_ACTIVE_SIDES_MISMATCH'));

const tamperedActive = JSON.parse(JSON.stringify(inverseBasis.activeSetReceipt));
tamperedActive.minimum.first.active = !tamperedActive.minimum.first.active;
rejected = verifyCase(inverseBasis, tamperedActive);
assert.strictEqual(rejected.verified, false);
assert.ok(rejected.violations.includes('MINIMUM_FIRST_ACTIVE_FLAG_MISMATCH'));

const tamperedCount = JSON.parse(JSON.stringify(inverseBasis.activeSetReceipt));
tamperedCount.maximum.activeProjectionCount = 1;
rejected = verifyCase(inverseBasis, tamperedCount);
assert.strictEqual(rejected.verified, false);
assert.ok(rejected.violations.includes('MAXIMUM_ACTIVE_PROJECTION_COUNT_MISMATCH'));

const tamperedDegenerateFlag = JSON.parse(JSON.stringify(point.activeSetReceipt));
tamperedDegenerateFlag.minimum.first.exactDegenerateInterval = false;
rejected = verifyCase(point, tamperedDegenerateFlag);
assert.strictEqual(rejected.verified, false);
assert.ok(rejected.violations.includes('MINIMUM_FIRST_DEGENERATE_FLAG_MISMATCH'));

const tamperedKind = JSON.parse(JSON.stringify(orthonormal.activeSetReceipt));
tamperedKind.minimum.witnessKind = 'origin';
rejected = verifyCase(orthonormal, tamperedKind);
assert.strictEqual(rejected.verified, false);
assert.ok(rejected.violations.includes('MINIMUM_WITNESS_KIND_MISMATCH'));

const tamperedEmbeddedVerification = JSON.parse(JSON.stringify(inverseBasis.activeSetReceipt));
tamperedEmbeddedVerification.witnessVerification.verified = false;
rejected = verifyCase(inverseBasis, tamperedEmbeddedVerification);
assert.strictEqual(rejected.verified, false);
assert.ok(rejected.violations.includes('EMBEDDED_WITNESS_VERIFICATION_MISMATCH'));

const tamperedWitness = JSON.parse(JSON.stringify(inverseBasis.witnessReceipt));
tamperedWitness.minimumProjections.first += 0.25;
rejected = verifyCase(inverseBasis, inverseBasis.activeSetReceipt, tamperedWitness);
assert.strictEqual(rejected.verified, false);
assert.strictEqual(rejected.reason, 'WITNESS_RECEIPT_NOT_VERIFIED');
assert.ok(rejected.witnessVerification.violations.includes('MINIMUM_PROJECTION_RECEIPT_MISMATCH'));

rejected = verifyCase(inverseBasis, null);
assert.strictEqual(rejected.verified, false);
assert.strictEqual(rejected.reason, 'ACTIVE_SET_RECEIPT_NOT_SUPPORTED');

const invalidTolerance = ActiveSetVerifier.verify(
  orthonormal.firstDirection,
  orthonormal.secondDirection,
  orthonormal.firstInterval,
  orthonormal.secondInterval,
  orthonormal.analysis,
  orthonormal.witnessReceipt,
  orthonormal.activeSetReceipt,
  { numericTolerance: -1 }
);
assert.strictEqual(invalidTolerance.verified, false);
assert.strictEqual(invalidTolerance.reason, 'INVALID_NUMERIC_TOLERANCE');

console.log(JSON.stringify({
  ok: true,
  schema: ActiveSetVerifier.SCHEMA,
  cases: {
    orthonormalBoundaryVerification: true,
    interiorOriginVerification: true,
    inverseBasisVerification: true,
    degenerateSegmentVerification: true,
    degeneratePointVerification: true,
    deterministicReplay: true,
    projectionTamperRejection: true,
    activeSideTamperRejection: true,
    activeFlagTamperRejection: true,
    activeCountTamperRejection: true,
    degenerateFlagTamperRejection: true,
    witnessKindTamperRejection: true,
    embeddedWitnessVerificationTamperRejection: true,
    underlyingWitnessTamperRejection: true,
    missingActiveSetRejection: true,
    invalidToleranceRejection: true
  }
}, null, 2));
