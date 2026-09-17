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
assert.equal(report.schema, 'axm.uc-orthogonal-projection-preflight/v0.6');
assert.equal(report.version, '0.6.0');
assert.equal(report.conflictFree, true);
assert.equal(report.counts.projectionPairBuckets, 2,
  'four projection groups across two body pairs must be indexed into exactly two canonical pair buckets');
assert.equal(report.counts.projectionMetricRecords, 4,
  'each non-conflicting projection group must get exactly one reusable metric record');
assert.equal(report.counts.projectionPairCandidates, 2,
  'each two-projection pair bucket contributes exactly one candidate pair');
assert.equal(report.counts.orthogonalProjectionRadialChecks, 2,
  'each radial group must reuse only its own pair bucket; cross-pair projection combinations must not be evaluated');
assert.equal(report.counts.radialMaximumChecks, 2);
assert.equal(report.counts.radialMaximumConflicts, 0);
assert.ok(report.evidence.some(line => line.includes('indexed once and reused for radial lookup')),
  'receipt must expose the one-index-per-analysis lookup path');
assert.ok(report.evidence.some(line => line.includes('projection metric record(s) computed once and reused')),
  'receipt must expose one-time projection metric materialization');

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
assert.equal(reuseReport.counts.projectionPairBuckets, 1);
assert.equal(reuseReport.counts.projectionMetricRecords, 4,
  'four normalized projection groups must produce four metric records, not one record per pair candidate');
assert.equal(reuseReport.counts.projectionPairCandidates, 6,
  'four same-pair projections create six deterministic candidate pairs');
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

console.log('orthogonal projection pair index selftest passed');
