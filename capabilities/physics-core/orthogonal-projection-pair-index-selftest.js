'use strict';

const assert = require('assert');
const Core = require('./source/axm-physics-core.js');
const Preflight = require('./uc-orthogonal-projection-preflight.js');

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
assert.equal(report.schema, 'axm.uc-orthogonal-projection-preflight/v0.5');
assert.equal(report.version, '0.5.0');
assert.equal(report.conflictFree, true);
assert.equal(report.counts.projectionPairBuckets, 2,
  'four projection groups across two body pairs must be indexed into exactly two canonical pair buckets');
assert.equal(report.counts.orthogonalProjectionRadialChecks, 2,
  'each radial group must reuse only its own pair bucket; cross-pair projection combinations must not be evaluated');
assert.equal(report.counts.radialMaximumChecks, 2);
assert.equal(report.counts.radialMaximumConflicts, 0);
assert.ok(report.evidence.some(line => line.includes('indexed once and reused for radial lookup')),
  'receipt must expose the one-index-per-analysis lookup path');

const replay = Preflight.analyze(world, constraints);
assert.equal(report.checksum, replay.checksum, 'pair-indexed proof planning must replay deterministically');
assert.deepEqual(report.orthogonalProjectionRadialChecks, replay.orthogonalProjectionRadialChecks);

console.log('orthogonal projection pair index selftest passed');
