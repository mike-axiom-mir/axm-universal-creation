'use strict';

const assert = require('assert');
const Core = require('./source/axm-physics-core.js');
const DirectionLimits = require('./uc-direction-limits.js');

function add(world, body) { return Core.addBody(world, body).world; }
function projection(vector, direction) {
  const length = Math.hypot(direction.x, direction.y);
  return (vector.x * direction.x + vector.y * direction.y) / length;
}
function staticDynamicWorld(position, velocity, gravity) {
  let world = Core.createWorld({ gravity: gravity || { x: 0, y: 0 }, bounds: false, sleep: { enabled: false } });
  world = add(world, { id: 'root', type: 'static', position: { x: 0, y: 0 } });
  world = add(world, {
    id: 'body', type: 'dynamic', position: position || { x: 2, y: 2 }, velocity: velocity || { x: 3, y: 1 }, mass: 1, linearDamping: 0
  });
  return world;
}

const diagonal = { x: 1, y: 1 };
const diagonalMax = Math.SQRT2;
const range = { id: 'diag-range', a: 'root', b: 'body', direction: diagonal, minOffset: 0, maxOffset: diagonalMax };

const validation = DirectionLimits.validate(staticDynamicWorld(), [range]);
assert.equal(validation.ok, true);
assert.equal(validation.limitCount, 1);
assert.match(validation.warnings.join(' '), /slack motion/i);
assert.match(validation.warnings.join(' '), /not a full prismatic\/slider joint/i);

const normalized = DirectionLimits.normalizeLimits([range], staticDynamicWorld());
assert.ok(Math.abs(normalized[0].direction.x - Math.SQRT1_2) < 1e-12, 'direction x must normalize deterministically');
assert.ok(Math.abs(normalized[0].direction.y - Math.SQRT1_2) < 1e-12, 'direction y must normalize deterministically');

const stepped = DirectionLimits.step(staticDynamicWorld(), [range], 0.1);
const steppedBody = stepped.world.bodies.find(item => item.id === 'body');
assert.ok(Math.abs(projection(steppedBody.position, diagonal) - diagonalMax) < 1e-8, 'max direction limit must repair excessive projected offset');
assert.ok(Math.abs(projection(steppedBody.velocity, diagonal)) < 1e-8, 'outward projected velocity at max boundary must be removed');
assert.ok(Math.abs(steppedBody.velocity.x - 1) < 1e-8 && Math.abs(steppedBody.velocity.y + 1) < 1e-8, 'perpendicular velocity component must remain free');
assert.ok(stepped.directionLimitDiagnostics.maxViolationAfterStabilization < 1e-8);
assert.equal(stepped.directionLimitDiagnostics.after[0].state, 'AT_MAX');
assert.equal(stepped.world.diagnostics.checksum, Core.checksum(stepped.world));
assert.equal(stepped.directionLimitDiagnostics.contactEvidenceBasis, 'CORE_STAGE_BEFORE_POST_DIRECTION_LIMIT_STABILIZATION');
assert.ok(stepped.core.worldBeforePostDirectionLimitStabilization);
assert.match(stepped.limitations.join(' '), /not a full prismatic\/slider joint/i);
assert.match(stepped.limitations.join(' '), /not yet integrated/i);
assert.match(stepped.limitations.join(' '), /not scientific validation/i);

const slackStart = { x: 3, y: -2.5 };
const slackWorld = staticDynamicWorld(slackStart, { x: 1, y: -1 });
const slackPrepared = DirectionLimits.prepareWorld(slackWorld, [range], { positionIterations: 1, velocityIterations: 1 });
assert.equal(slackPrepared.initial[0].state, 'SLACK');
assert.equal(slackPrepared.positionReceipts[0].constrained, false, 'position inside projected range must remain slack');
assert.equal(slackPrepared.velocityReceipts[0].constrained, false, 'velocity inside projected range must remain slack');
const slackStep = DirectionLimits.step(slackWorld, [range], 0.1);
const slackBody = slackStep.world.bodies.find(item => item.id === 'body');
assert.ok(Math.abs(projection(slackBody.position, diagonal) - projection(slackStart, diagonal)) < 1e-8, 'pure perpendicular slack motion must preserve projected offset');
assert.ok(Math.abs(slackBody.velocity.x - 1) < 1e-8 && Math.abs(slackBody.velocity.y + 1) < 1e-8, 'slack perpendicular velocity must remain unconstrained');

const minLimit = { id: 'diag-min', a: 'root', b: 'body', direction: diagonal, minOffset: -diagonalMax };
const minStep = DirectionLimits.step(staticDynamicWorld({ x: -2, y: -2 }, { x: -3, y: -1 }), [minLimit], 0.1);
const minBody = minStep.world.bodies.find(item => item.id === 'body');
assert.ok(Math.abs(projection(minBody.position, diagonal) + diagonalMax) < 1e-8, 'min direction limit must repair projected undershoot');
assert.ok(Math.abs(projection(minBody.velocity, diagonal)) < 1e-8, 'outward projected velocity at min boundary must be removed');
assert.equal(minStep.directionLimitDiagnostics.after[0].state, 'AT_MIN');

const boundaryPrepared = DirectionLimits.prepareWorld(
  staticDynamicWorld({ x: 1, y: 1 }, { x: 3, y: 1 }),
  [range],
  { positionIterations: 1, velocityIterations: 1 }
);
assert.equal(boundaryPrepared.positionReceipts[0].constrained, false, 'exactly on projected boundary is not a position violation');
assert.equal(boundaryPrepared.velocityReceipts[0].constrained, true, 'outward projected velocity at boundary must activate limit');
assert.equal(boundaryPrepared.velocityReceipts[0].boundary, 'MAX');
assert.ok(Math.abs(projection(boundaryPrepared.world.bodies.find(item => item.id === 'body').velocity, diagonal)) < 1e-8);

let shared = Core.createWorld({ gravity: { x: 0, y: 0 }, bounds: false, sleep: { enabled: false } });
shared = add(shared, { id: 'a', type: 'dynamic', position: { x: 0, y: 0 }, mass: 1, linearDamping: 0 });
shared = add(shared, { id: 'b', type: 'dynamic', position: { x: 4, y: 4 }, mass: 1, linearDamping: 0 });
const sharedPrepared = DirectionLimits.prepareWorld(
  shared,
  [{ id: 'share', a: 'a', b: 'b', direction: diagonal, maxOffset: 2 * Math.SQRT2 }],
  { positionIterations: 1, velocityIterations: 0 }
);
const sharedA = sharedPrepared.world.bodies.find(item => item.id === 'a');
const sharedB = sharedPrepared.world.bodies.find(item => item.id === 'b');
assert.ok(Math.abs(sharedA.position.x - 1) < 1e-8 && Math.abs(sharedA.position.y - 1) < 1e-8, 'equal inverse masses must share projected correction');
assert.ok(Math.abs(sharedB.position.x - 3) < 1e-8 && Math.abs(sharedB.position.y - 3) < 1e-8, 'equal inverse masses must share projected correction');

let immovable = Core.createWorld({ gravity: { x: 0, y: 0 }, bounds: false });
immovable = add(immovable, { id: 's1', type: 'static', position: { x: 0, y: 0 } });
immovable = add(immovable, { id: 's2', type: 'static', position: { x: 2, y: 2 } });
const immovablePrepared = DirectionLimits.prepareWorld(
  immovable,
  [{ id: 'static-max', a: 's1', b: 's2', direction: diagonal, maxOffset: 1 }],
  { positionIterations: 1, velocityIterations: 1 }
);
assert.equal(immovablePrepared.positionReceipts[0].solved, false);
assert.equal(immovablePrepared.positionReceipts[0].constrained, true);
assert.equal(immovablePrepared.positionReceipts[0].reason, 'NO_DYNAMIC_MASS');

const disabledPrepared = DirectionLimits.prepareWorld(
  staticDynamicWorld(),
  [{ id: 'off', a: 'root', b: 'body', direction: diagonal, maxOffset: 0, enabled: false }],
  { positionIterations: 1, velocityIterations: 1 }
);
assert.equal(disabledPrepared.positionReceipts[0].enabled, false);
assert.equal(disabledPrepared.world.bodies.find(item => item.id === 'body').position.x, 2, 'disabled direction limit must not move bodies');
assert.equal(disabledPrepared.world.bodies.find(item => item.id === 'body').position.y, 2, 'disabled direction limit must not move bodies');

const bounded = DirectionLimits.prepareWorld(staticDynamicWorld(), [range], { positionIterations: 999, velocityIterations: 999 });
assert.equal(bounded.positionIterations, 32);
assert.equal(bounded.velocityIterations, 32);

const start = Math.SQRT1_2;
const gravityStart = { x: 0.5 - 3 * Math.SQRT1_2, y: 0.5 + 3 * Math.SQRT1_2 };
let gravityWorld = Core.createWorld({ gravity: { x: 10, y: 10 }, bounds: false, sleep: { enabled: false } });
gravityWorld = add(gravityWorld, { id: 'anchor', type: 'static', position: { x: 0, y: 0 } });
gravityWorld = add(gravityWorld, { id: 'payload', type: 'dynamic', position: gravityStart, mass: 1, linearDamping: 0 });
const gravityLimit = { id: 'gravity-diag', a: 'anchor', b: 'payload', direction: diagonal, minOffset: 0, maxOffset: start };
const gravityStep = DirectionLimits.step(gravityWorld, [gravityLimit], 0.1);
assert.ok(gravityStep.directionLimitDiagnostics.maxViolationAfterCoreStep > 1e-4, 'diagonal gravity should create a measurable projected max-bound violation during donor-core integration');
assert.ok(gravityStep.directionLimitDiagnostics.maxViolationAfterStabilization < 1e-8, 'post stabilization must repair diagonal projected drift');

const simA = DirectionLimits.simulate(gravityWorld, [gravityLimit], 40, 1 / 60);
const simB = DirectionLimits.simulate(gravityWorld, [gravityLimit], 40, 1 / 60);
assert.equal(simA.checksum, simB.checksum, 'direction-limit simulation must replay deterministically in one JS runtime');
assert.equal(simA.world.stepIndex, 40);
assert.ok(simA.directionLimitDiagnostics.maxViolationAfterStabilization < 1e-8);

const equalRange = DirectionLimits.validate(staticDynamicWorld(), [{ id: 'equal', a: 'root', b: 'body', direction: diagonal, minOffset: 1, maxOffset: 1 }]);
assert.equal(equalRange.ok, true, 'equal min/max is a valid fixed direction projected offset range');

const invalidRange = DirectionLimits.validate(staticDynamicWorld(), [{ id: 'bad-range', a: 'root', b: 'body', direction: diagonal, minOffset: 2, maxOffset: 1 }]);
assert.equal(invalidRange.ok, false);
assert.match(invalidRange.errors.join(' '), /minOffset must be <= maxOffset/i);

const missingRange = DirectionLimits.validate(staticDynamicWorld(), [{ id: 'missing-range', a: 'root', b: 'body', direction: diagonal }]);
assert.equal(missingRange.ok, false);
assert.match(missingRange.errors.join(' '), /minOffset and\/or maxOffset/i);

const zeroDirection = DirectionLimits.validate(staticDynamicWorld(), [{ id: 'zero', a: 'root', b: 'body', direction: { x: 0, y: 0 }, maxOffset: 1 }]);
assert.equal(zeroDirection.ok, false);
assert.match(zeroDirection.errors.join(' '), /non-zero direction vector/i);

const nonFiniteDirection = DirectionLimits.validate(staticDynamicWorld(), [{ id: 'nan', a: 'root', b: 'body', direction: { x: 'bad', y: 1 }, maxOffset: 1 }]);
assert.equal(nonFiniteDirection.ok, false);
assert.match(nonFiniteDirection.errors.join(' '), /finite direction x and y/i);

const invalidBody = DirectionLimits.validate(staticDynamicWorld(), [{ id: 'bad-body', a: 'missing', b: 'body', direction: diagonal, maxOffset: 1 }]);
assert.equal(invalidBody.ok, false);
assert.match(invalidBody.errors.join(' '), /body not found/i);

console.log('UC Direction Limits selftest: PASS (normalized fixed directions, slack ranges, one-sided boundaries, outward projected velocity blocking, perpendicular freedom, mass sharing, immovable truth, bounds and deterministic replay)');
