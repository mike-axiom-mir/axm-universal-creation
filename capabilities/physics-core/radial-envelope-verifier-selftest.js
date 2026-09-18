'use strict';

const assert = require('assert');
const Envelope = require('./uc-two-projection-radial-envelope.js');
const Verifier = require('./uc-two-projection-radial-envelope-verifier.js');

function verifyEnvelope(firstDirection, secondDirection, firstInterval, secondInterval) {
  const analysis = Envelope.analyze(firstDirection, secondDirection, firstInterval, secondInterval);
  assert.equal(analysis.supported, true, 'fixture must stay inside the existing finite invertible envelope contract');
  const receipt = Verifier.verify(
    firstDirection,
    secondDirection,
    firstInterval,
    secondInterval,
    analysis,
    { numericTolerance: 1e-9 }
  );
  assert.equal(receipt.verified, true, `independent receipt verification failed: ${receipt.violations.join(', ')}`);
  assert.equal(receipt.determinantMatches, true);
  assert.ok(receipt.structuralChecks.every(check => check.matches));
  return { analysis, receipt };
}

const orthonormal = verifyEnvelope(
  { x: 1, y: 0 },
  { x: 0, y: 1 },
  { min: -2, max: 5 },
  { min: -4, max: 1 }
);
assert.equal(orthonormal.analysis.distanceMethod, 'orthonormal-projection-rectangle');

const nearOrthogonalFirst = { x: 1 + 2e-10, y: 0 };
const nearOrthogonalSecond = { x: 5e-7, y: Math.sqrt(1 - 25e-14) };
const oneSidedFirst = { min: 2, max: 5 };
const oneSidedSecond = { min: -4, max: -1 };
const inverseBasis = verifyEnvelope(
  nearOrthogonalFirst,
  nearOrthogonalSecond,
  oneSidedFirst,
  oneSidedSecond
);
assert.equal(inverseBasis.analysis.distanceMethod, 'inverse-basis-parallelogram-two-active-edges');

const segment = verifyEnvelope(
  { x: 1, y: 0 },
  { x: 5e-7, y: Math.sqrt(1 - 25e-14) },
  { min: 0, max: 0 },
  { min: -3, max: 3 }
);
assert.equal(segment.analysis.degenerateProjectionIntervals, 1);
assert.equal(segment.analysis.originSymmetricSegmentThroughOrigin, true);

const point = verifyEnvelope(
  { x: 1, y: 0 },
  { x: 5e-7, y: Math.sqrt(1 - 25e-14) },
  { min: 2, max: 2 },
  { min: -1, max: -1 }
);
assert.equal(point.analysis.degenerateProjectionIntervals, 2);

const tamperedMaximum = Object.assign({}, inverseBasis.analysis, {
  maximumDistance: inverseBasis.analysis.maximumDistance + 0.25
});
const maximumFailure = Verifier.verify(
  nearOrthogonalFirst,
  nearOrthogonalSecond,
  oneSidedFirst,
  oneSidedSecond,
  tamperedMaximum,
  { numericTolerance: 1e-9 }
);
assert.equal(maximumFailure.verified, false);
assert.ok(maximumFailure.violations.includes('MAXIMUM_DISTANCE_MISMATCH'));

const tamperedCorners = inverseBasis.analysis.corners.map(pointValue => ({
  x: pointValue.x,
  y: pointValue.y
}));
tamperedCorners[0].x += 0.5;
const tamperedCornerAnalysis = Object.assign({}, inverseBasis.analysis, {
  corners: tamperedCorners
});
const cornerFailure = Verifier.verify(
  nearOrthogonalFirst,
  nearOrthogonalSecond,
  oneSidedFirst,
  oneSidedSecond,
  tamperedCornerAnalysis,
  { numericTolerance: 1e-9 }
);
assert.equal(cornerFailure.verified, false);
assert.ok(cornerFailure.violations.includes('CORNER_PROJECTION_MISMATCH'));

const tamperedDeterminant = Object.assign({}, inverseBasis.analysis, {
  determinant: inverseBasis.analysis.determinant + 0.25
});
const determinantFailure = Verifier.verify(
  nearOrthogonalFirst,
  nearOrthogonalSecond,
  oneSidedFirst,
  oneSidedSecond,
  tamperedDeterminant,
  { numericTolerance: 1e-9 }
);
assert.equal(determinantFailure.verified, false);
assert.ok(determinantFailure.violations.includes('DETERMINANT_MISMATCH'));
assert.equal(determinantFailure.determinantMatches, false);

const tamperedStructure = Object.assign({}, inverseBasis.analysis, {
  degenerateProjectionIntervals: 1,
  originInsideProjectionRectangle: true
});
const structureFailure = Verifier.verify(
  nearOrthogonalFirst,
  nearOrthogonalSecond,
  oneSidedFirst,
  oneSidedSecond,
  tamperedStructure,
  { numericTolerance: 1e-9 }
);
assert.equal(structureFailure.verified, false);
assert.ok(structureFailure.violations.includes('STRUCTURAL_RECEIPT_MISMATCH'));
assert.ok(structureFailure.structuralChecks.some(check => !check.matches));

const invalidDirectionFailure = Verifier.verify(
  { x: Infinity, y: 0 },
  nearOrthogonalSecond,
  oneSidedFirst,
  oneSidedSecond,
  inverseBasis.analysis,
  { numericTolerance: 1e-9 }
);
assert.equal(invalidDirectionFailure.verified, false);
assert.equal(invalidDirectionFailure.reason, 'INVALID_DIRECTION_INPUT');

const reversedIntervalFailure = Verifier.verify(
  nearOrthogonalFirst,
  nearOrthogonalSecond,
  { min: 5, max: 2 },
  oneSidedSecond,
  inverseBasis.analysis,
  { numericTolerance: 1e-9 }
);
assert.equal(reversedIntervalFailure.verified, false);
assert.equal(reversedIntervalFailure.reason, 'EMPTY_PROJECTION_INTERVAL');
assert.deepEqual(reversedIntervalFailure.emptyIntervals, [true, false]);

const singularDirectionFailure = Verifier.verify(
  nearOrthogonalFirst,
  nearOrthogonalFirst,
  oneSidedFirst,
  oneSidedSecond,
  inverseBasis.analysis,
  { numericTolerance: 1e-9 }
);
assert.equal(singularDirectionFailure.verified, false);
assert.equal(singularDirectionFailure.reason, 'SINGULAR_DIRECTION_PAIR');

assert.deepEqual(
  Verifier.verify(
    nearOrthogonalFirst,
    nearOrthogonalSecond,
    oneSidedFirst,
    oneSidedSecond,
    inverseBasis.analysis,
    { numericTolerance: 1e-9 }
  ),
  inverseBasis.receipt,
  'receipt verification must replay deterministically'
);

console.log('radial envelope verifier selftest passed');
