'use strict';

const assert = require('assert');
const Core = require('./source/axm-physics-core.js');
const BasePreflight = require('./uc-constraint-preflight.js');
const ExactGeometry = require('./uc-exact-projection-geometry.js');

function add(world, spec) {
  return Core.addBody(world, spec).world;
}

function baseWorld() {
  let world = Core.createWorld({ gravity: { x: 0, y: 0 }, bounds: false, sleep: { enabled: false } });
  world = add(world, { id: 'a', type: 'static', position: { x: 0, y: 0 } });
  world = add(world, { id: 'b', type: 'dynamic', position: { x: 1, y: 2 }, mass: 1, linearDamping: 0 });
  return world;
}

const constraints = {
  axisLocks: [
    { id: 'x-zero', a: 'a', b: 'b', axis: 'x', offset: 0 },
    { id: 'x-half', a: 'a', b: 'b', axis: 'x', offset: 0.5 },
    { id: 'y-two', a: 'a', b: 'b', axis: 'y', offset: 2 }
  ],
  distanceLimits: [
    { id: 'radius-band', a: 'a', b: 'b', minLength: 1, maxLength: 4 }
  ]
};

const defaultReport = ExactGeometry.analyze(baseWorld(), constraints);
assert.equal(defaultReport.schema, 'axm.uc-exact-projection-geometry/v0.2');
assert.equal(defaultReport.version, '0.2.0');
assert.equal(defaultReport.tolerance, BasePreflight.DEFAULT_TOLERANCE);
assert.equal(defaultReport.counts.projectionGroups, defaultReport.groups.length);
assert.equal(defaultReport.counts.radialGroups, defaultReport.radialGroups.length);
assert.equal(defaultReport.counts.projectionEntries, 3);
assert.equal(defaultReport.counts.projectionGroups, 2);
assert.equal(defaultReport.counts.radialEntries, 1);
assert.equal(defaultReport.counts.radialGroups, 1);
assert.equal(defaultReport.groups.find(group => group.direction.x === 1).conflict, true);
assert.ok(defaultReport.evidence.some(line => line.includes('materialized exactly once')),
  'receipt must state that grouped results are reused rather than recomputed');

const negativeTolerance = ExactGeometry.analyze(baseWorld(), constraints, { tolerance: -100 });
assert.equal(negativeTolerance.tolerance, 0, 'negative tolerance must clamp to zero');
assert.equal(negativeTolerance.groups.find(group => group.direction.x === 1).conflict, true,
  'clamped zero tolerance must not hide a real interval conflict');

const oversizedTolerance = ExactGeometry.analyze(baseWorld(), constraints, { tolerance: Infinity });
assert.equal(oversizedTolerance.tolerance, BasePreflight.DEFAULT_TOLERANCE,
  'non-finite tolerance must fall back to the base preflight default');

const clampedMaximum = ExactGeometry.analyze(baseWorld(), constraints, { tolerance: BasePreflight.MAX_TOLERANCE * 2 });
assert.equal(clampedMaximum.tolerance, BasePreflight.MAX_TOLERANCE,
  'finite oversized tolerance must clamp to the same maximum as the base preflight');
assert.equal(clampedMaximum.groups.find(group => group.direction.x === 1).conflict, false,
  'the bounded maximum tolerance is applied consistently to exact group conflict evidence');

const replayA = ExactGeometry.analyze(baseWorld(), constraints, { tolerance: 0 });
const replayB = ExactGeometry.analyze(baseWorld(), constraints, { tolerance: 0 });
assert.equal(JSON.stringify(replayA), JSON.stringify(replayB), 'exact geometry analysis must replay deterministically');

console.log('exact projection geometry selftest passed');
