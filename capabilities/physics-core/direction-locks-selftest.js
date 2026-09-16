'use strict';

const assert = require('assert');
const Core = require('./source/axm-physics-core.js');
const DirectionLocks = require('./uc-direction-locks.js');

function add(world, body) { return Core.addBody(world, body).world; }
function projection(vector, direction) { const length = Math.hypot(direction.x, direction.y); return (vector.x * direction.x + vector.y * direction.y) / length; }
function relative(a, b, field) { return { x: b[field].x - a[field].x, y: b[field].y - a[field].y }; }
function diagonalWorld() {
  let world = Core.createWorld({ gravity: { x: 0, y: 0 }, bounds: false, sleep: { enabled: false } });
  world = add(world, { id: 'root', type: 'static', position: { x: 0, y: 0 } });
  world = add(world, { id: 'body', type: 'dynamic', position: { x: 3, y: 1 }, velocity: { x: 2, y: 0 }, mass: 1, linearDamping: 0 });
  return world;
}

const direction = { x: 1, y: 1 };
const targetOffset = Math.SQRT2;
const lock = { id: 'diagonal', a: 'root', b: 'body', direction, offset: targetOffset };
const validation = DirectionLocks.validate(diagonalWorld(), [lock]);
assert.equal(validation.ok, true);
assert.equal(validation.lockCount, 1);
assert.match(validation.warnings.join(' '), /perpendicular translation remains intentionally unconstrained/i);
assert.match(validation.warnings.join(' '), /not a rotating local-axis or full prismatic joint/i);
assert.match(validation.warnings.join(' '), /shared composer\/activity\/isolation integration is available/i);

const beforeWorld = diagonalWorld();
const beforeRoot = beforeWorld.bodies.find(item => item.id === 'root');
const beforeBody = beforeWorld.bodies.find(item => item.id === 'body');
const perpendicular = { x: -1, y: 1 };
const beforePerpendicularPosition = projection(relative(beforeRoot, beforeBody, 'position'), perpendicular);
const beforePerpendicularVelocity = projection(relative(beforeRoot, beforeBody, 'velocity'), perpendicular);
const stepped = DirectionLocks.step(beforeWorld, [lock], 0.1);
const root = stepped.world.bodies.find(item => item.id === 'root');
const body = stepped.world.bodies.find(item => item.id === 'body');
const finalRelativePosition = relative(root, body, 'position');
const finalRelativeVelocity = relative(root, body, 'velocity');
assert.ok(Math.abs(projection(finalRelativePosition, direction) - targetOffset) < 1e-8, 'direction lock must restore requested projected offset');
assert.ok(Math.abs(projection(finalRelativeVelocity, direction)) < 1e-8, 'relative velocity along locked direction must be removed');
assert.ok(Math.abs(projection(finalRelativeVelocity, perpendicular) - beforePerpendicularVelocity) < 1e-8, 'perpendicular velocity must remain untouched');
assert.ok(Math.abs(projection(finalRelativePosition, perpendicular) - (beforePerpendicularPosition + beforePerpendicularVelocity * 0.1)) < 1e-7, 'perpendicular motion must remain free through donor integration');
assert.ok(stepped.directionLockDiagnostics.maxErrorAfterStabilization < 1e-8);
assert.equal(stepped.directionLockDiagnostics.contactEvidenceBasis, 'CORE_STAGE_BEFORE_POST_DIRECTION_LOCK_STABILIZATION');
assert.ok(stepped.core.worldBeforePostDirectionLockStabilization);
assert.equal(stepped.world.diagnostics.checksum, Core.checksum(stepped.world));
assert.match(stepped.limitations.join(' '), /standalone step entrypoint performs its own donor-core integration/i);
assert.match(stepped.limitations.join(' '), /component isolation is broader than the one-axis physical correction/i);
assert.match(stepped.limitations.join(' '), /not scientific validation/i);

let gravityWorld = Core.createWorld({ gravity: { x: 0, y: 10 }, bounds: false, sleep: { enabled: false } });
gravityWorld = add(gravityWorld, { id: 'ceiling', type: 'static', position: { x: 0, y: 0 } });
gravityWorld = add(gravityWorld, { id: 'payload', type: 'dynamic', position: { x: 1, y: 1 }, velocity: { x: 3, y: 0 }, mass: 1, linearDamping: 0 });
const gravityLock = { id: 'vertical-vector', a: 'ceiling', b: 'payload', direction: { x: 0, y: 5 }, offset: 1 };
const gravityStep = DirectionLocks.step(gravityWorld, [gravityLock], 0.1);
const payload = gravityStep.world.bodies.find(item => item.id === 'payload');
assert.ok(payload.position.x > 1.29, 'perpendicular x motion must remain free');
assert.ok(Math.abs(payload.position.y - 1) < 1e-8, 'post stabilization must repair gravity drift along the locked direction');
assert.ok(gravityStep.directionLockDiagnostics.maxErrorAfterCoreStep > 1e-4);
assert.ok(gravityStep.directionLockDiagnostics.maxErrorAfterStabilization < 1e-8);
assert.equal(gravityStep.locks[0].direction.x, 0);
assert.equal(gravityStep.locks[0].direction.y, 1, 'direction input must be normalized deterministically');

let shared = Core.createWorld({ gravity: { x: 0, y: 0 }, bounds: false, sleep: { enabled: false } });
shared = add(shared, { id: 'a', type: 'dynamic', position: { x: 0, y: 0 }, mass: 1, linearDamping: 0 });
shared = add(shared, { id: 'b', type: 'dynamic', position: { x: 4, y: 4 }, mass: 1, linearDamping: 0 });
const sharedPrepared = DirectionLocks.prepareWorld(shared, [{ id: 'share', a: 'a', b: 'b', direction: { x: 1, y: 1 }, offset: 2 * Math.SQRT2 }], { positionIterations: 1, velocityIterations: 0 });
const sharedA = sharedPrepared.world.bodies.find(item => item.id === 'a');
const sharedB = sharedPrepared.world.bodies.find(item => item.id === 'b');
assert.ok(Math.abs(sharedA.position.x - 1) < 1e-8 && Math.abs(sharedA.position.y - 1) < 1e-8, 'equal inverse masses must share diagonal correction');
assert.ok(Math.abs(sharedB.position.x - 3) < 1e-8 && Math.abs(sharedB.position.y - 3) < 1e-8, 'equal inverse masses must share diagonal correction');

let immovable = Core.createWorld({ gravity: { x: 0, y: 0 }, bounds: false });
immovable = add(immovable, { id: 's1', type: 'static', position: { x: 0, y: 0 } });
immovable = add(immovable, { id: 's2', type: 'static', position: { x: 2, y: 2 } });
const immovablePrepared = DirectionLocks.prepareWorld(immovable, [{ id: 'static', a: 's1', b: 's2', direction: { x: 1, y: 1 }, offset: 0 }], { positionIterations: 1, velocityIterations: 1 });
assert.equal(immovablePrepared.positionReceipts[0].solved, false);
assert.equal(immovablePrepared.positionReceipts[0].reason, 'NO_DYNAMIC_MASS');

const disabledPrepared = DirectionLocks.prepareWorld(diagonalWorld(), [{ id: 'off', a: 'root', b: 'body', direction: { x: 1, y: 1 }, offset: 99, enabled: false }], { positionIterations: 1, velocityIterations: 1 });
assert.equal(disabledPrepared.positionReceipts[0].enabled, false);
assert.deepEqual(disabledPrepared.world.bodies.find(item => item.id === 'body').position, { x: 3, y: 1 }, 'disabled direction lock must not project bodies');

const bounded = DirectionLocks.prepareWorld(diagonalWorld(), [lock], { positionIterations: 999, velocityIterations: 999 });
assert.equal(bounded.positionIterations, 32);
assert.equal(bounded.velocityIterations, 32);

const simA = DirectionLocks.simulate(gravityWorld, [gravityLock], 40, 1 / 60);
const simB = DirectionLocks.simulate(gravityWorld, [gravityLock], 40, 1 / 60);
assert.equal(simA.checksum, simB.checksum, 'direction-lock simulation must replay deterministically in one JS runtime');
assert.equal(simA.world.stepIndex, 40);
assert.ok(simA.directionLockDiagnostics.maxErrorAfterStabilization < 1e-8);

const invalidZero = DirectionLocks.validate(diagonalWorld(), [{ id: 'zero', a: 'root', b: 'body', direction: { x: 0, y: 0 } }]);
assert.equal(invalidZero.ok, false);
assert.match(invalidZero.errors.join(' '), /non-zero direction vector/i);
const invalidFinite = DirectionLocks.validate(diagonalWorld(), [{ id: 'nan', a: 'root', b: 'body', direction: { x: 'nope', y: 1 } }]);
assert.equal(invalidFinite.ok, false);
assert.match(invalidFinite.errors.join(' '), /finite direction x and y/i);
const invalidBody = DirectionLocks.validate(diagonalWorld(), [{ id: 'missing', a: 'missing', b: 'body', direction: { x: 1, y: 0 } }]);
assert.equal(invalidBody.ok, false);
assert.match(invalidBody.errors.join(' '), /body not found/i);

console.log('UC Direction Locks selftest: PASS (arbitrary fixed world direction, perpendicular freedom, mass sharing, post stabilization, bounds, validation and deterministic replay)');
