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

const radialCompatible = Preflight.analyze(baseWorld(), {
  distanceJoints: [{ id: 'distance', a: 'a', b: 'b', length: 2 }],
  distanceLimits: [{ id: 'rope', a: 'a', b: 'b', minLength: 1, maxLength: 3 }]
});
assert.equal(radialCompatible.ok, true, 'same-pair distance equality inside a distance range must remain conflict-free');
assert.equal(radialCompatible.radialGroups.length, 1);
assert.equal(radialCompatible.radialGroups[0].constraintCount, 2);
assert.deepEqual(radialCompatible.radialGroups[0].intersection, { min: 2, max: 2 });
assert.equal(radialCompatible.counts.analyzedRadialEntries, 2);
assert.equal(radialCompatible.counts.unsupportedConstraints, 0);
assert.deepEqual(radialCompatible.unsupportedFamilies, []);

const radialConflict = Preflight.analyze(baseWorld(), {
  distanceJoints: [{ id: 'distance-three', a: 'a', b: 'b', length: 3 }],
  distanceLimits: [{ id: 'max-two', a: 'a', b: 'b', maxLength: 2 }]
});
assert.equal(radialConflict.valid, true);
assert.equal(radialConflict.conflictFree, false);
assert.equal(radialConflict.counts.radialConflicts, 1);
assert.equal(radialConflict.conflicts[0].code, 'CONFLICTING_DISTANCE_INTERVALS');
assert.deepEqual(radialConflict.conflicts[0].constraintIds, ['distance-three', 'max-two']);
assert.deepEqual(radialConflict.conflicts[0].families, ['distance-joints', 'distance-limits']);

const reversedRadialConflict = Preflight.analyze(baseWorld(), {
  distanceJoints: [{ id: 'forward-distance', a: 'a', b: 'b', length: 1 }],
  distanceLimits: [{ id: 'reverse-distance', a: 'b', b: 'a', minLength: 2, maxLength: 4 }]
});
assert.equal(reversedRadialConflict.conflicts.length, 1, 'distance constraints must canonicalize reversed body pairs without sign inversion');
assert.equal(reversedRadialConflict.conflicts[0].code, 'CONFLICTING_DISTANCE_INTERVALS');

const disabledRadial = Preflight.analyze(baseWorld(), {
  distanceJoints: [
    { id: 'live-distance', a: 'a', b: 'b', length: 2 },
    { id: 'off-distance', a: 'a', b: 'b', length: 9, enabled: false }
  ],
  distanceLimits: [{ id: 'distance-band', a: 'a', b: 'b', minLength: 1, maxLength: 3 }]
});
assert.equal(disabledRadial.ok, true);
assert.equal(disabledRadial.counts.disabledConstraints, 1);
assert.equal(disabledRadial.radialGroups[0].constraintCount, 2, 'disabled distance constraints must not enter radial intersections');

const projectionRadialConflict = Preflight.analyze(baseWorld(), {
  axisLocks: [{ id: 'x-three', a: 'a', b: 'b', axis: 'x', offset: 3 }],
  distanceLimits: [{ id: 'radius-two', a: 'a', b: 'b', maxLength: 2 }]
});
assert.equal(projectionRadialConflict.valid, true);
assert.equal(projectionRadialConflict.conflictFree, false, 'a fixed projection magnitude above the same-pair radial maximum is impossible');
assert.equal(projectionRadialConflict.counts.projectionConflicts, 0, 'the projected interval alone is internally satisfiable');
assert.equal(projectionRadialConflict.counts.radialConflicts, 0, 'the radial interval alone is internally satisfiable');
assert.equal(projectionRadialConflict.counts.projectionRadialChecks, 1);
assert.equal(projectionRadialConflict.counts.projectionRadialConflicts, 1);
assert.equal(projectionRadialConflict.conflicts[0].code, 'PROJECTION_EXCEEDS_DISTANCE_MAX');
assert.equal(projectionRadialConflict.conflicts[0].minimumRequiredDistance, 3);
assert.equal(projectionRadialConflict.conflicts[0].maximumAllowedDistance, 2);
assert.deepEqual(projectionRadialConflict.conflicts[0].constraintIds, ['radius-two', 'x-three']);
assert.deepEqual(projectionRadialConflict.conflicts[0].families, ['axis-locks', 'distance-limits']);

const projectionRadialCompatible = Preflight.analyze(baseWorld(), {
  axisLimits: [{ id: 'x-band', a: 'a', b: 'b', axis: 'x', minOffset: -3, maxOffset: 3 }],
  distanceLimits: [{ id: 'radius-half', a: 'a', b: 'b', maxLength: 0.5 }]
});
assert.equal(projectionRadialCompatible.ok, true, 'a projected range containing zero must not be rejected merely because its outer endpoints exceed the radial maximum');
assert.equal(projectionRadialCompatible.counts.projectionRadialChecks, 1);
assert.equal(projectionRadialCompatible.projectionRadialChecks[0].minimumRequiredDistance, 0);

const radialMinimumDoesNotConflict = Preflight.analyze(baseWorld(), {
  axisLocks: [{ id: 'x-zero', a: 'a', b: 'b', axis: 'x', offset: 0 }],
  distanceLimits: [{ id: 'radius-min-five', a: 'a', b: 'b', minLength: 5 }]
});
assert.equal(radialMinimumDoesNotConflict.ok, true, 'radial minimum alone cannot contradict one projected coordinate because perpendicular freedom may satisfy it');
assert.equal(radialMinimumDoesNotConflict.counts.projectionRadialChecks, 1, 'the normalized distance-limit contract carries its bounded MAX_LENGTH ceiling even when only minLength is supplied');
assert.equal(radialMinimumDoesNotConflict.counts.projectionRadialConflicts, 0);

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
  ],
  distanceLimits: [
    { id: 'radial-left', a: 'a', b: 'b', minLength: 0, maxLength: 2 },
    { id: 'radial-right', a: 'a', b: 'b', minLength: 2.0000000005, maxLength: 4 }
  ]
}, { tolerance: 1e-9 });
assert.equal(tolerance.conflictFree, true, 'configured bounded tolerance may absorb sub-tolerance projection and radial interval separation');

const coupledTolerance = Preflight.analyze(baseWorld(), {
  axisLocks: [{ id: 'x-near', a: 'a', b: 'b', axis: 'x', offset: 2.0000000005 }],
  distanceLimits: [{ id: 'radius-two', a: 'a', b: 'b', maxLength: 2 }]
}, { tolerance: 1e-9 });
assert.equal(coupledTolerance.conflictFree, true, 'bounded tolerance also applies to the single-projection versus radial-maximum proof');

const replayA = Preflight.analyze(baseWorld(), {
  mounts: [{ id: 'mount', a: 'a', b: 'b', offset: { x: 0, y: 2 } }],
  axisLocks: [
    { id: 'x-lock', a: 'a', b: 'b', axis: 'x', offset: 1 },
    { id: 'x-three', a: 'a', b: 'b', axis: 'y', offset: 3 }
  ],
  distanceJoints: [{ id: 'distance-three', a: 'a', b: 'b', length: 3 }],
  distanceLimits: [{ id: 'max-two', a: 'a', b: 'b', maxLength: 2 }]
});
const replayB = Preflight.analyze(baseWorld(), {
  mounts: [{ id: 'mount', a: 'a', b: 'b', offset: { x: 0, y: 2 } }],
  axisLocks: [
    { id: 'x-lock', a: 'a', b: 'b', axis: 'x', offset: 1 },
    { id: 'x-three', a: 'a', b: 'b', axis: 'y', offset: 3 }
  ],
  distanceJoints: [{ id: 'distance-three', a: 'a', b: 'b', length: 3 }],
  distanceLimits: [{ id: 'max-two', a: 'a', b: 'b', maxLength: 2 }]
});
assert.equal(replayA.checksum, replayB.checksum, 'preflight evidence must replay deterministically in one JS runtime');
assert.deepEqual(replayA.conflicts, replayB.conflicts);
assert.deepEqual(replayA.projectionRadialChecks, replayB.projectionRadialChecks);

console.log('UC Constraint Preflight selftest: PASS (projected, same-pair radial and bounded projection-vs-distance conflicts, canonical handling, disabled validation, tolerance and deterministic evidence)');
