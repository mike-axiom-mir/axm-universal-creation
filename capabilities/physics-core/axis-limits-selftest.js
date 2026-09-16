'use strict';

const assert = require('assert');
const Core = require('./source/axm-physics-core.js');
const AxisLimits = require('./uc-axis-limits.js');

function add(world, body) {
  return Core.addBody(world, body).world;
}

function staticDynamicWorld(position, velocity) {
  let world = Core.createWorld({ gravity: { x: 0, y: 0 }, bounds: false, sleep: { enabled: false } });
  world = add(world, { id: 'root', type: 'static', position: { x: 0, y: 0 } });
  world = add(world, {
    id: 'body',
    type: 'dynamic',
    position: position || { x: 2, y: 3 },
    velocity: velocity || { x: 4, y: 2 },
    mass: 1,
    linearDamping: 0
  });
  return world;
}

const xRange = { id: 'x-range', a: 'root', b: 'body', axis: 'x', minOffset: 0, maxOffset: 1 };
const validation = AxisLimits.validate(staticDynamicWorld(), [xRange]);
assert.equal(validation.ok, true);
assert.equal(validation.limitCount, 1);
assert.match(validation.warnings.join(' '), /slack motion/i);
assert.match(validation.warnings.join(' '), /not.*full prismatic\/slider joint/i);

const stepped = AxisLimits.step(staticDynamicWorld(), [xRange], 0.1);
const body = stepped.world.bodies.find(item => item.id === 'body');
assert.ok(Math.abs(body.position.x - 1) < 1e-8, 'max axis limit must repair an excessive x offset');
assert.ok(body.position.y > 3.19, 'orthogonal y translation must remain free');
assert.ok(Math.abs(body.velocity.x) < 1e-8, 'outward velocity at the active max boundary must be removed');
assert.ok(Math.abs(body.velocity.y - 2) < 1e-8, 'orthogonal velocity must remain untouched');
assert.ok(stepped.axisLimitDiagnostics.maxViolationAfterStabilization < 1e-8);
assert.equal(stepped.axisLimitDiagnostics.after[0].state, 'AT_MAX');
assert.equal(stepped.axisLimitDiagnostics.after[0].orthogonalOffset, body.position.y);
assert.equal(stepped.world.diagnostics.checksum, Core.checksum(stepped.world));
assert.equal(stepped.axisLimitDiagnostics.contactEvidenceBasis, 'CORE_STAGE_BEFORE_POST_AXIS_LIMIT_STABILIZATION');
assert.ok(stepped.core.worldBeforePostAxisLimitStabilization);
assert.match(stepped.limitations.join(' '), /not a full prismatic\/slider joint/i);
assert.match(stepped.limitations.join(' '), /standalone/i);
assert.match(stepped.limitations.join(' '), /not scientific validation/i);

const slackWorld = staticDynamicWorld({ x: 0.5, y: 3 }, { x: 0.5, y: 2 });
const slackPrepared = AxisLimits.prepareWorld(slackWorld, [xRange], { positionIterations: 1, velocityIterations: 1 });
assert.equal(slackPrepared.initial[0].state, 'SLACK');
assert.equal(slackPrepared.positionReceipts[0].constrained, false, 'position inside the allowed interval must remain slack');
assert.equal(slackPrepared.velocityReceipts[0].constrained, false, 'velocity inside the allowed interval must remain slack');
const slackStepped = AxisLimits.step(slackWorld, [xRange], 0.1);
const slackBody = slackStepped.world.bodies.find(item => item.id === 'body');
assert.ok(slackBody.position.x > 0.54 && slackBody.position.x < 0.56, 'slack x motion must advance freely inside the interval');
assert.ok(Math.abs(slackBody.velocity.x - 0.5) < 1e-8, 'slack x velocity must remain unconstrained');

const minLimit = { id: 'x-min', a: 'root', b: 'body', axis: 'x', minOffset: -1 };
const minStepped = AxisLimits.step(staticDynamicWorld({ x: -2, y: 1 }, { x: -3, y: 0 }), [minLimit], 0.1);
const minBody = minStepped.world.bodies.find(item => item.id === 'body');
assert.ok(Math.abs(minBody.position.x + 1) < 1e-8, 'min axis limit must repair an undershoot');
assert.ok(Math.abs(minBody.velocity.x) < 1e-8, 'outward velocity at the active min boundary must be removed');
assert.equal(minStepped.axisLimitDiagnostics.after[0].state, 'AT_MIN');

const boundaryPrepared = AxisLimits.prepareWorld(
  staticDynamicWorld({ x: 1, y: 0 }, { x: 3, y: 7 }),
  [xRange],
  { positionIterations: 1, velocityIterations: 1 }
);
assert.equal(boundaryPrepared.positionReceipts[0].constrained, false, 'being exactly on a boundary is not a position violation');
assert.equal(boundaryPrepared.velocityReceipts[0].constrained, true, 'outward velocity at a boundary must activate the velocity limit');
assert.equal(boundaryPrepared.velocityReceipts[0].boundary, 'MAX');
assert.ok(Math.abs(boundaryPrepared.world.bodies.find(item => item.id === 'body').velocity.x) < 1e-8);
assert.equal(boundaryPrepared.world.bodies.find(item => item.id === 'body').velocity.y, 7);

let shared = Core.createWorld({ gravity: { x: 0, y: 0 }, bounds: false, sleep: { enabled: false } });
shared = add(shared, { id: 'a', type: 'dynamic', position: { x: 0, y: 0 }, mass: 1, linearDamping: 0 });
shared = add(shared, { id: 'b', type: 'dynamic', position: { x: 4, y: 5 }, mass: 1, linearDamping: 0 });
const sharedPrepared = AxisLimits.prepareWorld(
  shared,
  [{ id: 'share', a: 'a', b: 'b', axis: 'x', maxOffset: 2 }],
  { positionIterations: 1, velocityIterations: 0 }
);
const sharedA = sharedPrepared.world.bodies.find(item => item.id === 'a');
const sharedB = sharedPrepared.world.bodies.find(item => item.id === 'b');
assert.ok(Math.abs(sharedA.position.x - 1) < 1e-8, 'equal inverse masses must share max-limit correction');
assert.ok(Math.abs(sharedB.position.x - 3) < 1e-8, 'equal inverse masses must share max-limit correction');
assert.equal(sharedA.position.y, 0);
assert.equal(sharedB.position.y, 5);

let immovable = Core.createWorld({ gravity: { x: 0, y: 0 }, bounds: false });
immovable = add(immovable, { id: 's1', type: 'static', position: { x: 0, y: 0 } });
immovable = add(immovable, { id: 's2', type: 'static', position: { x: 2, y: 0 } });
const immovablePrepared = AxisLimits.prepareWorld(
  immovable,
  [{ id: 'static-max', a: 's1', b: 's2', axis: 'x', maxOffset: 1 }],
  { positionIterations: 1, velocityIterations: 1 }
);
assert.equal(immovablePrepared.positionReceipts[0].solved, false);
assert.equal(immovablePrepared.positionReceipts[0].constrained, true);
assert.equal(immovablePrepared.positionReceipts[0].reason, 'NO_DYNAMIC_MASS');

const disabledPrepared = AxisLimits.prepareWorld(
  staticDynamicWorld(),
  [{ id: 'off', a: 'root', b: 'body', axis: 'x', maxOffset: 0, enabled: false }],
  { positionIterations: 1, velocityIterations: 1 }
);
assert.equal(disabledPrepared.positionReceipts[0].enabled, false);
assert.equal(disabledPrepared.world.bodies.find(item => item.id === 'body').position.x, 2, 'disabled limit must not move bodies');

const bounded = AxisLimits.prepareWorld(staticDynamicWorld(), [xRange], { positionIterations: 999, velocityIterations: 999 });
assert.equal(bounded.positionIterations, 32);
assert.equal(bounded.velocityIterations, 32);

let gravityWorld = Core.createWorld({ gravity: { x: 0, y: 10 }, bounds: false, sleep: { enabled: false } });
gravityWorld = add(gravityWorld, { id: 'ceiling', type: 'static', position: { x: 0, y: 0 } });
gravityWorld = add(gravityWorld, { id: 'payload', type: 'dynamic', position: { x: 0, y: 1 }, mass: 1, linearDamping: 0 });
const yRange = { id: 'y-range', a: 'ceiling', b: 'payload', axis: 'y', minOffset: 0.5, maxOffset: 1 };
const gravityStep = AxisLimits.step(gravityWorld, [yRange], 0.1);
assert.ok(gravityStep.axisLimitDiagnostics.maxViolationAfterCoreStep > 1e-4, 'gravity should create a measurable max-bound violation during the donor-core stage');
assert.ok(gravityStep.axisLimitDiagnostics.maxViolationAfterStabilization < 1e-8, 'post stabilization must repair the y-bound violation');

const simA = AxisLimits.simulate(gravityWorld, [yRange], 40, 1 / 60);
const simB = AxisLimits.simulate(gravityWorld, [yRange], 40, 1 / 60);
assert.equal(simA.checksum, simB.checksum, 'axis-limit simulation must replay deterministically in one JS runtime');
assert.equal(simA.world.stepIndex, 40);
assert.ok(simA.axisLimitDiagnostics.maxViolationAfterStabilization < 1e-8);

const equalLimit = AxisLimits.validate(staticDynamicWorld(), [{ id: 'equal', a: 'root', b: 'body', axis: 'x', minOffset: 1, maxOffset: 1 }]);
assert.equal(equalLimit.ok, true, 'equal min/max is a valid fixed world-axis offset range');

const invalidRange = AxisLimits.validate(staticDynamicWorld(), [{ id: 'bad-range', a: 'root', b: 'body', axis: 'x', minOffset: 2, maxOffset: 1 }]);
assert.equal(invalidRange.ok, false);
assert.match(invalidRange.errors.join(' '), /minOffset must be <= maxOffset/i);

const missingRange = AxisLimits.validate(staticDynamicWorld(), [{ id: 'missing-range', a: 'root', b: 'body', axis: 'x' }]);
assert.equal(missingRange.ok, false);
assert.match(missingRange.errors.join(' '), /minOffset and\/or maxOffset/i);

const invalidAxis = AxisLimits.validate(staticDynamicWorld(), [{ id: 'bad-axis', a: 'root', b: 'body', axis: 'z', maxOffset: 1 }]);
assert.equal(invalidAxis.ok, false);
assert.match(invalidAxis.errors.join(' '), /axis "x" or "y"/i);

const invalidBody = AxisLimits.validate(staticDynamicWorld(), [{ id: 'bad-body', a: 'missing', b: 'body', axis: 'x', maxOffset: 1 }]);
assert.equal(invalidBody.ok, false);
assert.match(invalidBody.errors.join(' '), /body not found/i);

console.log('UC Axis Limits selftest: PASS (slack ranges, one-sided boundaries, outward velocity blocking, orthogonal freedom, mass sharing, immovable truth, bounds and deterministic replay)');
