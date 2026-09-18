'use strict';

const assert = require('assert');
const Envelope = require('./uc-two-projection-radial-envelope.js');
const Witness = require('./uc-two-projection-radial-envelope-witness.js');
const ActiveSet = require('./uc-two-projection-radial-envelope-active-set.js');
const ProjectionMargins = require('./uc-two-projection-radial-envelope-projection-margins.js');
const ProjectionMarginsVerifier = require('./uc-two-projection-radial-envelope-projection-margins-verifier.js');

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

  const projectionMarginsReceipt = ProjectionMargins.derive(
    firstDirection,
    secondDirection,
    firstInterval,
    secondInterval,
    analysis,
    witnessReceipt,
    activeSetReceipt,
    options
  );
  assert.strictEqual(projectionMarginsReceipt.supported, true);
  assert.strictEqual(projectionMarginsReceipt.verified, true);

  const verification = ProjectionMarginsVerifier.verify(
    firstDirection,
    secondDirection,
    firstInterval,
    secondInterval,
    analysis,
    witnessReceipt,
    activeSetReceipt,
    projectionMarginsReceipt,
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
    projectionMarginsReceipt,
    verification
  };
}

function verifyWithCase(base, projectionMarginsReceipt, options, activeSetReceipt) {
  return ProjectionMarginsVerifier.verify(
    base.firstDirection,
    base.secondDirection,
    base.firstInterval,
    base.secondInterval,
    base.analysis,
    base.witnessReceipt,
    activeSetReceipt || base.activeSetReceipt,
    projectionMarginsReceipt,
    options || { numericTolerance: 1e-9 }
  );
}

const orthonormal = build(
  { x: 1, y: 0 },
  { x: 0, y: 1 },
  { min: 2, max: 4 },
  { min: -1, max: 3 }
);
assert.strictEqual(orthonormal.verification.expectedMinimum.first.classification, 'boundary');
assert.strictEqual(orthonormal.verification.expectedMinimum.second.classification, 'interior');
assert.strictEqual(orthonormal.verification.expectedMaximum.activeProjectionCount, 2);

const symmetric = build(
  { x: 1, y: 0 },
  { x: 0, y: 1 },
  { min: -1, max: 1 },
  { min: -1, max: 1 }
);
assert.strictEqual(symmetric.verification.expectedMinimum.witnessKind, 'origin');
assert.strictEqual(symmetric.verification.expectedMinimum.first.strictInterior, true);
assert.strictEqual(symmetric.verification.expectedMinimum.second.strictInterior, true);

const inverseBasis = build(
  { x: 1, y: 0 },
  { x: 2e-10, y: 1 },
  { min: 1, max: 4 },
  { min: 2, max: 5 }
);
assert.strictEqual(inverseBasis.verification.expectedMaximum.activeProjectionCount, 2);

const segment = build(
  { x: 1, y: 0 },
  { x: 2e-10, y: 1 },
  { min: 0, max: 0 },
  { min: 2, max: 5 }
);
assert.strictEqual(segment.verification.expectedMinimum.first.exactDegenerateInterval, true);
assert.deepStrictEqual(segment.verification.expectedMinimum.first.activeSides, ['min', 'max']);

const point = build(
  { x: 1, y: 0 },
  { x: 2e-10, y: 1 },
  { min: 2, max: 2 },
  { min: 3, max: 3 }
);
assert.strictEqual(point.verification.expectedMinimum.first.classification, 'degenerate-boundary');
assert.strictEqual(point.verification.expectedMaximum.second.classification, 'degenerate-boundary');

const replay = verifyWithCase(inverseBasis, inverseBasis.projectionMarginsReceipt, { numericTolerance: 1e-9 });
assert.deepStrictEqual(replay, inverseBasis.verification);

const projectionTamper = JSON.parse(JSON.stringify(inverseBasis.projectionMarginsReceipt));
projectionTamper.minimum.first.projection += 0.25;
let rejected = verifyWithCase(inverseBasis, projectionTamper);
assert.strictEqual(rejected.verified, false);
assert.ok(rejected.violations.includes('MINIMUM_FIRST_PROJECTION_MISMATCH'));

const marginTamper = JSON.parse(JSON.stringify(inverseBasis.projectionMarginsReceipt));
marginTamper.maximum.second.toMin += 0.25;
marginTamper.maximum.second.signedFeasibilityMargin += 0.25;
rejected = verifyWithCase(inverseBasis, marginTamper);
assert.strictEqual(rejected.verified, false);
assert.ok(rejected.violations.includes('MAXIMUM_SECOND_TO_MIN_MISMATCH'));
assert.ok(rejected.violations.includes('MAXIMUM_SECOND_SIGNED_FEASIBILITY_MARGIN_MISMATCH'));

const toleranceBandTamper = JSON.parse(JSON.stringify(inverseBasis.projectionMarginsReceipt));
toleranceBandTamper.minimum.second.toleranceBand *= 2;
rejected = verifyWithCase(inverseBasis, toleranceBandTamper);
assert.strictEqual(rejected.verified, false);
assert.ok(rejected.violations.includes('MINIMUM_SECOND_TOLERANCE_BAND_MISMATCH'));

const classificationTamper = JSON.parse(JSON.stringify(orthonormal.projectionMarginsReceipt));
classificationTamper.minimum.first.classification = 'interior';
classificationTamper.minimum.first.strictInterior = true;
rejected = verifyWithCase(orthonormal, classificationTamper);
assert.strictEqual(rejected.verified, false);
assert.ok(rejected.violations.includes('MINIMUM_FIRST_CLASSIFICATION_MISMATCH'));
assert.ok(rejected.violations.includes('MINIMUM_FIRST_STRICT_INTERIOR_MISMATCH'));

const sideTamper = JSON.parse(JSON.stringify(segment.projectionMarginsReceipt));
sideTamper.minimum.first.activeSides = ['min'];
sideTamper.minimum.first.exactDegenerateInterval = false;
rejected = verifyWithCase(segment, sideTamper);
assert.strictEqual(rejected.verified, false);
assert.ok(rejected.violations.includes('MINIMUM_FIRST_ACTIVE_SIDES_MISMATCH'));
assert.ok(rejected.violations.includes('MINIMUM_FIRST_DEGENERATE_FLAG_MISMATCH'));

const supportFlagTamper = JSON.parse(JSON.stringify(inverseBasis.projectionMarginsReceipt));
supportFlagTamper.minimum.supported = false;
supportFlagTamper.minimum.first.supported = false;
supportFlagTamper.reason = 'tampered';
rejected = verifyWithCase(inverseBasis, supportFlagTamper);
assert.strictEqual(rejected.verified, false);
assert.ok(rejected.violations.includes('MINIMUM_SUPPORTED_FLAG_MISMATCH'));
assert.ok(rejected.violations.includes('MINIMUM_FIRST_SUPPORTED_FLAG_MISMATCH'));
assert.ok(rejected.violations.includes('PROJECTION_MARGINS_REASON_MISMATCH'));

const aggregateTamper = JSON.parse(JSON.stringify(inverseBasis.projectionMarginsReceipt));
aggregateTamper.maximum.minimumSignedFeasibilityMargin += 0.5;
aggregateTamper.maximum.nearestRepresentedBoundaryGap += 0.5;
aggregateTamper.maximum.activeProjectionCount = 1;
rejected = verifyWithCase(inverseBasis, aggregateTamper);
assert.strictEqual(rejected.verified, false);
assert.ok(rejected.violations.includes('MAXIMUM_MINIMUM_SIGNED_FEASIBILITY_MARGIN_MISMATCH'));
assert.ok(rejected.violations.includes('MAXIMUM_NEAREST_REPRESENTED_BOUNDARY_GAP_MISMATCH'));
assert.ok(rejected.violations.includes('MAXIMUM_ACTIVE_PROJECTION_COUNT_MISMATCH'));

const embeddedVerificationTamper = JSON.parse(JSON.stringify(inverseBasis.projectionMarginsReceipt));
embeddedVerificationTamper.activeSetVerification.expectedMinimum.first.active = false;
rejected = verifyWithCase(inverseBasis, embeddedVerificationTamper);
assert.strictEqual(rejected.verified, false);
assert.ok(rejected.violations.includes('EMBEDDED_ACTIVE_SET_VERIFICATION_MISMATCH'));

const schemaTamper = JSON.parse(JSON.stringify(inverseBasis.projectionMarginsReceipt));
schemaTamper.schema = 'axm.tampered-projection-margins/v9';
rejected = verifyWithCase(inverseBasis, schemaTamper);
assert.strictEqual(rejected.verified, false);
assert.ok(rejected.violations.includes('PROJECTION_MARGINS_SCHEMA_MISMATCH'));

const missingMargins = verifyWithCase(inverseBasis, null);
assert.strictEqual(missingMargins.verified, false);
assert.strictEqual(missingMargins.reason, 'PROJECTION_MARGINS_RECEIPT_NOT_SUPPORTED');

const tamperedActiveSet = JSON.parse(JSON.stringify(inverseBasis.activeSetReceipt));
tamperedActiveSet.maximum.second.activeSides = [];
tamperedActiveSet.maximum.second.active = false;
const activeSetRejected = verifyWithCase(
  inverseBasis,
  inverseBasis.projectionMarginsReceipt,
  { numericTolerance: 1e-9 },
  tamperedActiveSet
);
assert.strictEqual(activeSetRejected.verified, false);
assert.strictEqual(activeSetRejected.reason, 'ACTIVE_SET_RECEIPT_NOT_VERIFIED');

const invalidTolerance = verifyWithCase(
  inverseBasis,
  inverseBasis.projectionMarginsReceipt,
  { numericTolerance: -1 }
);
assert.strictEqual(invalidTolerance.verified, false);
assert.strictEqual(invalidTolerance.reason, 'INVALID_NUMERIC_TOLERANCE');

console.log(JSON.stringify({
  ok: true,
  schema: ProjectionMarginsVerifier.SCHEMA,
  cases: {
    orthonormalBoundaryVerification: true,
    interiorOriginVerification: true,
    inverseBasisVerification: true,
    degenerateSegmentVerification: true,
    degeneratePointVerification: true,
    deterministicReplay: true,
    projectionTamperRejection: true,
    signedMarginTamperRejection: true,
    toleranceBandTamperRejection: true,
    classificationTamperRejection: true,
    activeSideTamperRejection: true,
    supportFlagAndReasonTamperRejection: true,
    aggregateTamperRejection: true,
    embeddedVerificationTamperRejection: true,
    schemaTamperRejection: true,
    missingReceiptRejection: true,
    underlyingActiveSetTamperRejection: true,
    invalidToleranceRejection: true
  }
}, null, 2));
