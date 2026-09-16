'use strict';

const assert = require('assert');
const Core = require('./source/axm-physics-core.js');
const AxisLocks = require('./uc-axis-locks.js');

function add(world, body) {
  return Core.addBody(world, body).world;
}

function staticDynamicWorld() {
  let world = Core.createWorld({ gravity: { x: 0, y: 0 }, bounds: false, sleep: { enabled: false } });
  world = add(world, { id: 'root', type: 'static', position: { x: 0, y: 0 } });
  world = add(world, { id: 'body', type: 'dynamic', position: { x: 2, y: 3 }, velocity: { x: 4, y: 2 }, mass: 1, linearDamping: 0 });
  return world;
}

const xLock = { id: 'x-only', a: 'root', b: 'body', axis: 'x', offset: 1 };
const validation = AxisLocks.validate(staticDynamicWorld(), [xLock]);
assert.equal(validation.ok, true);
assert.equal(validation.lockCount, 1);
assert.match(validation.warnings.join(' '), /orthogonal translation remains intentionally unconstrained/i);
assert.match(validation.warnings.join(' '), /not a rotational\/prismatic joint/i);

const stepped = AxisLocks.step(staticDynamicWorld(), [xLock], 0.1);
const body = stepped.world.bodies.find(item => item.id === 'body');
assert.ok(Math.abs(body.position.x - 1) < 1e-8, 'x lock must restore the requested x offset');
assert.ok(body.position.y > 3.19, 'orthogonal y translation must remain free');
assert.ok(Math.abs(body.velocity.x) < 1e-8, 'locked-axis relative velocity must be removed');
assert.ok(Math.abs(body.velocity.y - 2) < 1e-8, 'orthogonal velocity must remain untouched');
assert.ok(stepped.axisLockDiagnostics.maxErrorAfterStabilization < 1e-8);
assert.equal(stepped.axisLockDiagnostics.after[0].axis, 'x');
assert.equal(stepped.axisLockDiagnostics.after[0].orthogonalOffset, body.position.y);
assert.equal(stepped.world.diagnostics.checksum, Core.checksum(stepped.world));
assert.equal(stepped.axisLockDiagnostics.contactEvidenceBasis, 'CORE_STAGE_BEFORE_POST_AXIS_LOCK_STABILIZATION');
assert.ok(stepped.core.worldBeforePostAxisLockStabilization);
assert.match(stepped.limitations.join(' '), /does not represent a full prismatic\/slider joint/i);
assert.match(stepped.limitations.join(' '), /not scientific validation/i);

let yWorld = Core.createWorld({ gravity: { x: 0, y: 10 }, bounds: false, sleep: { enabled: false } });
yWorld = add(yWorld, { id: 'ceiling', type: 'static', position: { x: 0, y: 0 } });
yWorld = add(yWorld, { id: 'payload', type: 'dynamic', position: { x: 1, y: 1 }, velocity: { x: 3, y: 0 }, mass: 1, linearDamping: 0 });
const yLock = { id: 'y-only', a: 'ceiling', b: 'payload', axis: 'y', offset: 1 };
const yStepped = AxisLocks.step(yWorld, [yLock], 0.1);
const payload = yStepped.world.bodies.find(item => item.id === 'payload');
assert.ok(payload.position.x > 1.29, 'x must remain free under a y-only lock');
assert.ok(Math.abs(payload.position.y - 1) < 1e-8, 'post stabilization must repair gravity drift on the locked y axis');
assert.ok(yStepped.axisLockDiagnostics.maxErrorAfterCoreStep > 1e-4, 'gravity should create measurable locked-axis drift during the donor-core stage');
assert.ok(yStepped.axisLockDiagnostics.maxErrorAfterStabilization < 1e-8);

let shared = Core.createWorld({ gravity: { x: 0, y: 0 }, bounds: false, sleep: { enabled: false } });
shared = add(shared, { id: 'a', type: 'dynamic', position: { x: 0, y: 0 }, mass: 1, linearDamping: 0 });
shared = add(shared, { id: 'b', type: 'dynamic', position: { x: 4, y: 5 }, mass: 1, linearDamping: 0 });
const sharedPrepared = AxisLocks.prepareWorld(shared, [{ id: 'share', a: 'a', b: 'b', axis: 'x', offset: 2 }], { positionIterations: 1, velocityIterations: 0 });
const sharedA = sharedPrepared.world.bodies.find(item => item.id === 'a');
const sharedB = sharedPrepared.world.bodies.find(item => item.id === 'b');
assert.ok(Math.abs(sharedA.position.x - 1) < 1e-8, 'equal inverse masses must share x correction');
assert.ok(Math.abs(sharedB.position.x - 3) < 1e-8, 'equal inverse masses must share x correction');
assert.equal(sharedA.position.y, 0);
assert.equal(sharedB.position.y, 5);

let kinematic = Core.createWorld({ gravity: { x: 0, y: 0 }, bounds: false, sleep: { enabled: false } });
kinematic = add(kinematic, { id: 'rail', type: 'kinematic', position: { x: 0, y: 0 }, velocity: { x: 1, y: 0 } });
kinematic = add(kinematic, { id: 'follower', type: 'dynamic', position: { x: 1, y: 2 }, mass: 1, linearDamping: 0 });
const followed = AxisLocks.step(kinematic, [{ id: 'follow-x', a: 'rail', b: 'follower', axis: 'x', offset: 1 }], 0.1);
const rail = followed.world.bodies.find(item => item.id === 'rail');
const follower = followed.world.bodies.find(item => item.id === 'follower');
assert.ok(rail.position.x > 0.09);
assert.ok(follower.position.x > 1.09);
assert.ok(Math.abs((follower.position.x - rail.position.x) - 1) < 1e-8, 'dynamic follower must inherit locked-axis motion from the kinematic carrier');
assert.equal(follower.position.y, 2, 'orthogonal coordinate must remain unchanged without orthogonal forces');

let immovable = Core.createWorld({ gravity: { x: 0, y: 0 }, bounds: false });
immovable = add(immovable, { id: 's1', type: 'static', position: { x: 0, y: 0 } });
immovable = add(immovable, { id: 's2', type: 'static', position: { x: 2, y: 0 } });
const immovablePrepared = AxisLocks.prepareWorld(immovable, [{ id: 'static-x', a: 's1', b: 's2', axis: 'x', offset: 1 }], { positionIterations: 1, velocityIterations: 1 });
assert.equal(immovablePrepared.positionReceipts[0].solved, false);
assert.equal(immovablePrepared.positionReceipts[0].reason, 'NO_DYNAMIC_MASS');

const disabledPrepared = AxisLocks.prepareWorld(staticDynamicWorld(), [{ id: 'off', a: 'root', b: 'body', axis: 'x', offset: 99, enabled: false }], { positionIterations: 1, velocityIterations: 1 });
assert.equal(disabledPrepared.positionReceipts[0].enabled, false);
assert.equal(disabledPrepared.world.bodies.find(item => item.id === 'body').position.x, 2, 'disabled lock must not move bodies during projection');

const bounded = AxisLocks.prepareWorld(staticDynamicWorld(), [xLock], { positionIterations: 999, velocityIterations: 999 });
assert.equal(bounded.positionIterations, 32);
assert.equal(bounded.velocityIterations, 32);

const simA = AxisLocks.simulate(yWorld, [yLock], 40, 1 / 60);
const simB = AxisLocks.simulate(yWorld, [yLock], 40, 1 / 60);
assert.equal(simA.checksum, simB.checksum, 'axis-lock simulation must replay deterministically in one JS runtime');
assert.equal(simA.world.stepIndex, 40);
assert.ok(simA.axisLockDiagnostics.maxErrorAfterStabilization < 1e-8);

const invalidAxis = AxisLocks.validate(staticDynamicWorld(), [{ id: 'bad-axis', a: 'root', b: 'body', axis: 'z' }]);
assert.equal(invalidAxis.ok, false);
assert.match(invalidAxis.errors.join(' '), /axis "x" or "y"/i);

const invalidBody = AxisLocks.validate(staticDynamicWorld(), [{ id: 'bad-body', a: 'missing', b: 'body', axis: 'x' }]);
assert.equal(invalidBody.ok, false);
assert.match(invalidBody.errors.join(' '), /body not found/i);

console.log('UC Axis Locks selftest: PASS (single-axis correction, orthogonal freedom, dynamic sharing, kinematic following, immovable truth, bounds and deterministic replay)');
