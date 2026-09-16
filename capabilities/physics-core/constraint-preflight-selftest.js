'use strict';

const assert = require('assert');
const Core = require('./source/axm-physics-core.js');
const Preflight = require('./uc-constraint-preflight.js');

function add(world, spec) { return Core.addBody(world, spec).world; }
function baseWorld() {
  let world = Core.createWorld({ gravity: { x: 0, y: 0 }, bounds: false, sleep: { enabled: false } });
  world = add(world, { id: 'a', type: 'static', position: { x: 0, y: 0 } });
  world = add(world, { id: 'b', type: 'dynamic', position: { x: 1, y: 2 }, mass: 1, linearDamping: 0 });
  return world;
}

const conflict = Preflight.analyze(baseWorld(), {
  mounts: [{ id: 'mount', a: 'a', b: 'b', offset: { x: 0, y: 2 } }],
  axisLocks: [{ id: 'x-lock', a: 'a', b: 'b', axis: 'x', offset: 1 }]
});
assert.equal(conflict.valid, true);
assert.equal(conflict.conflictFree, false);
assert.equal(conflict.conflicts.length, 1);
assert.equal(conflict.conflicts[0].code, 'CONFLICTING_TRANSLATION_INTERVALS');
assert.deepEqual(conflict.conflicts[0].constraintIds.slice().sort(), ['mount', 'x-lock']);
assert.deepEqual(conflict.conflicts[0].families, ['axis-locks', 'translation-mounts']);
assert.equal(conflict.counts.analyzedProjectionEntries, 3, 'mount contributes x/y projections plus the axis lock');

const overlap = Preflight.analyze(baseWorld(), {
  axisLimits: [
    { id: 'wide', a: 'a', b: 'b', axis: 'x', minOffset: 0, maxOffset: 2 },
    { id: 'narrow', a: 'a', b: 'b', axis: 'x', minOffset: 1, maxOffset: 3 }
  ]
});
assert.equal(overlap.ok, true);
assert.equal(overlap.groups.length, 1);
assert.deepEqual(overlap.groups[0].intersection, { min: 1, max: 2 });

const crossFamily = Preflight.analyze(baseWorld(), {
  axisLocks: [{ id: 'axis-one', a: 'a', b: 'b', axis: 'x', offset: 1 }],
  directionLocks: [{ id: 'direction-one', a: 'a', b: 'b', direction: { x: 2, y: 0 }, offset: 1 }],
  directionLimits: [{ id: 'reverse-range', a: 'b', b: 'a', direction: { x: -4, y: 0 }, minOffset: 0.5, maxOffset: 1.5 }]
});
assert.equal(crossFamily.ok, true, 'equivalent axis/fixed-direction projections should share one satisfiable group');
assert.equal(crossFamily.groups.length, 1);
assert.equal(crossFamily.groups[0].constraintCount, 3);
assert.deepEqual(crossFamily.groups[0].intersection, { min: 1, max: 1 });

const reversedConflict = Preflight.analyze(baseWorld(), {
  axisLocks: [
    { id: 'forward', a: 'a', b: 'b', axis: 'x', offset: 1 },
    { id: 'reversed', a: 'b', b: 'a', axis: 'x', offset: -2 }
  ]
});
assert.equal(reversedConflict.conflicts.length, 1, 'body-order reversal must canonicalize before interval intersection');

const disabled = Preflight.analyze(baseWorld(), {
  axisLocks: [
    { id: 'live', a: 'a', b: 'b', axis: 'x', offset: 1 },
    { id: 'off', a: 'a', b: 'b', axis: 'x', offset: 999, enabled: false }
  ]
});
assert.equal(disabled.ok, true);
assert.equal(disabled.counts.disabledConstraints, 1);
assert.equal(disabled.groups[0].constraintCount, 1, 'disabled constraints must not enter conflict intersections');

const invalidDisabled = Preflight.analyze(baseWorld(), {
  axisLocks: [{ id: 'off-bad-ref', a: 'a', b: 'missing', axis: 'x', offset: 1, enabled: false }]
});
assert.equal(invalidDisabled.valid, false, 'disabled constraints must still be source/body-reference validated');
assert.match(invalidDisabled.errors.join(' '), /body not found/i);

const unsupported = Preflight.analyze(baseWorld(), {
  distanceJoints: [{ id: 'distance', a: 'a', b: 'b', distance: 1 }],
  distanceLimits: [{ id: 'rope', a: 'a', b: 'b', minDistance: 0, maxDistance: 2 }]
});
assert.equal(unsupported.ok, true, 'unsupported families are reported rather than falsely classified as conflicting');
assert.equal(unsupported.counts.unsupportedConstraints, 2);
assert.deepEqual(unsupported.unsupportedFamilies.map(item => item.family), ['distance-joints', 'distance-limits']);
assert.match(unsupported.limitations.join(' '), /does not prove global constraint satisfiability/i);
assert.match(unsupported.limitations.join(' '), /not scientific validation/i);

const nearParallel = Preflight.analyze(baseWorld(), {
  directionLocks: [
    { id: 'one', a: 'a', b: 'b', direction: { x: 1, y: 1 }, offset: 1 },
    { id: 'almost', a: 'a', b: 'b', direction: { x: 1, y: 1.000000001 }, offset: 2 }
  ]
});
assert.equal(nearParallel.groups.length, 2, 'near-parallel but non-identical directions must remain separate to avoid false conflict claims');
assert.equal(nearParallel.conflictFree, true);

const tolerance = Preflight.analyze(baseWorld(), {
  axisLimits: [
    { id: 'left', a: 'a', b: 'b', axis: 'x', minOffset: 0, maxOffset: 1 },
    { id: 'right', a: 'a', b: 'b', axis: 'x', minOffset: 1.0000000005, maxOffset: 2 }
  ]
}, { tolerance: 1e-9 });
assert.equal(tolerance.conflictFree, true, 'configured bounded tolerance may absorb sub-tolerance interval separation');

const replayA = Preflight.analyze(baseWorld(), {
  mounts: [{ id: 'mount', a: 'a', b: 'b', offset: { x: 0, y: 2 } }],
  axisLocks: [{ id: 'x-lock', a: 'a', b: 'b', axis: 'x', offset: 1 }]
});
const replayB = Preflight.analyze(baseWorld(), {
  mounts: [{ id: 'mount', a: 'a', b: 'b', offset: { x: 0, y: 2 } }],
  axisLocks: [{ id: 'x-lock', a: 'a', b: 'b', axis: 'x', offset: 1 }]
});
assert.equal(replayA.checksum, replayB.checksum, 'preflight evidence must replay deterministically in one JS runtime');
assert.deepEqual(replayA.conflicts, replayB.conflicts);

console.log('UC Constraint Preflight selftest: PASS (conservative projected-interval conflicts, canonical body/direction handling, disabled validation, unsupported-family truth and deterministic evidence)');
