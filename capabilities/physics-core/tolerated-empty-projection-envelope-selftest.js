'use strict';

const assert = require('assert');
const Core = require('./source/axm-physics-core.js');
const Envelope = require('./uc-two-projection-radial-envelope.js');
const Preflight = require('./uc-orthogonal-projection-preflight.js');

function add(world, spec) {
  return Core.addBody(world, spec).world;
}

function baseWorld() {
  let world = Core.createWorld({ gravity: { x: 0, y: 0 }, bounds: false, sleep: { enabled: false } });
  world = add(world, { id: 'a', type: 'static', position: { x: 0, y: 0 } });
  world = add(world, { id: 'b', type: 'dynamic', position: { x: 1, y: 2 }, mass: 1, linearDamping: 0 });
  return world;
}

const emptyEnvelope = Envelope.analyze(
  { x: 1, y: 0 },
  { x: 0, y: 1 },
  { min: 4.0000000005, max: 4 },
  { min: 4, max: 4 }
);
assert.equal(emptyEnvelope.supported, false,
  'min > max is an empty exact interval even when an upstream tolerance may choose not to reject it');
assert.equal(emptyEnvelope.reason, 'EMPTY_PROJECTION_INTERVAL');
assert.deepEqual(emptyEnvelope.emptyIntervals, [true, false]);

const constraints = {
  axisLimits: [
    { id: 'x-left-band', a: 'a', b: 'b', axis: 'x', minOffset: 3, maxOffset: 4 },
    { id: 'x-right-band', a: 'a', b: 'b', axis: 'x', minOffset: 4.0000000005, maxOffset: 5 }
  ],
  axisLocks: [
    { id: 'y-four', a: 'a', b: 'b', axis: 'y', offset: 4 }
  ],
  distanceLimits: [
    { id: 'radius-six', a: 'a', b: 'b', maxLength: 6 }
  ]
};

const tolerated = Preflight.analyze(baseWorld(), constraints);
assert.equal(tolerated.base.valid, true);
assert.equal(tolerated.base.conflictFree, true,
  'the conservative base preflight intentionally tolerates the 5e-10 local projection gap under its 1e-9 default tolerance');
assert.equal(tolerated.counts.projectionPairCandidates, 1);
assert.equal(tolerated.counts.exactRadialEnvelopeChecks, 0,
  'a tolerance-accepted but exactly empty projection intersection must not be counted as an exact feasible parallelogram');
assert.equal(tolerated.counts.radialMaximumChecks, 1);
assert.equal(tolerated.counts.radialMaximumConflicts, 0);
assert.equal(tolerated.conflictFree, true);
assert.equal(tolerated.orthogonalProjectionRadialChecks.length, 1);
const check = tolerated.orthogonalProjectionRadialChecks[0];
assert.equal(check.radialEnvelope, null);
assert.equal(check.radialBoundModel, 'singular-value-conservative',
  'the stronger layer must fall back conservatively instead of fabricating exact geometry from min > max');
assert.equal(check.radialMaximumCheck.boundModel, 'singular-value-conservative');

const replay = Preflight.analyze(baseWorld(), constraints);
assert.equal(tolerated.checksum, replay.checksum,
  'tolerated-empty interval fallback must replay deterministically');

console.log('tolerated empty projection envelope selftest passed');
