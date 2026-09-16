'use strict';

const assert = require('assert');
const Core = require('./source/axm-physics-core.js');
const Mounts = require('./uc-translation-mounts.js');

function add(world, body) {
  return Core.addBody(world, body).world;
}

function staticDynamicWorld() {
  let world = Core.createWorld({ gravity: { x: 0, y: 0 }, bounds: false, sleep: { enabled: false } });
  world = add(world, {
    id: 'parent',
    type: 'static',
    shape: { kind: 'circle', radius: 0.1 },
    position: { x: 1, y: 2 }
  });
  world = add(world, {
    id: 'child',
    type: 'dynamic',
    shape: { kind: 'circle', radius: 0.1 },
    position: { x: 9, y: 9 },
    mass: 1,
    linearDamping: 0
  });
  return world;
}

const mount = { id: 'weapon-mount', a: 'parent', b: 'child', offset: { x: 2, y: -1 } };
assert.equal(Mounts.VERSION, '0.1.0');
assert.equal(Mounts.validate(staticDynamicWorld(), [mount]).ok, true);

const corrected = Mounts.step(staticDynamicWorld(), [mount], 0.01);
const correctedParent = corrected.world.bodies.find(item => item.id === 'parent');
const correctedChild = corrected.world.bodies.find(item => item.id === 'child');
assert.ok(Math.abs((correctedChild.position.x - correctedParent.position.x) - 2) < 1e-8, 'mount must preserve target x offset');
assert.ok(Math.abs((correctedChild.position.y - correctedParent.position.y) + 1) < 1e-8, 'mount must preserve target y offset');
assert.ok(corrected.mountDiagnostics.after[0].errorDistance < 1e-8, 'mounted body must finish on target translation offset');
assert.match(corrected.limitations.join(' '), /do not rotate anchor offsets/i);
assert.match(corrected.limitations.join(' '), /not scientific validation/i);

let kinematic = Core.createWorld({ gravity: { x: 0, y: 0 }, bounds: false, sleep: { enabled: false } });
kinematic = add(kinematic, {
  id: 'carrier',
  type: 'kinematic',
  shape: { kind: 'circle', radius: 0.1 },
  position: { x: 0, y: 0 },
  velocity: { x: 1, y: 0.5 }
});
kinematic = add(kinematic, {
  id: 'payload',
  type: 'dynamic',
  shape: { kind: 'circle', radius: 0.1 },
  position: { x: 2, y: -1 },
  velocity: { x: 0, y: 0 },
  mass: 1,
  linearDamping: 0
});
const follow = Mounts.step(kinematic, [{ id: 'follow', a: 'carrier', b: 'payload', offset: { x: 2, y: -1 } }], 0.1);
const carrier = follow.world.bodies.find(item => item.id === 'carrier');
const payload = follow.world.bodies.find(item => item.id === 'payload');
assert.ok(carrier.position.x > 0.09 && carrier.position.y > 0.04, 'kinematic carrier must move under donor-core integration');
assert.ok(Math.abs((payload.position.x - carrier.position.x) - 2) < 1e-8, 'dynamic payload must keep mounted x offset while carrier moves');
assert.ok(Math.abs((payload.position.y - carrier.position.y) + 1) < 1e-8, 'dynamic payload must keep mounted y offset while carrier moves');
assert.ok(Math.abs(payload.velocity.x - carrier.velocity.x) < 1e-8 && Math.abs(payload.velocity.y - carrier.velocity.y) < 1e-8, 'mount velocity solve must make payload inherit carrier translation velocity');

let balanced = Core.createWorld({ gravity: { x: 0, y: 0 }, bounds: false, sleep: { enabled: false } });
balanced = add(balanced, { id: 'light', type: 'dynamic', position: { x: 0, y: 0 }, mass: 1, linearDamping: 0 });
balanced = add(balanced, { id: 'heavy', type: 'dynamic', position: { x: 4, y: 0 }, mass: 3, linearDamping: 0 });
const balancedStep = Mounts.step(balanced, [{ id: 'balanced', a: 'light', b: 'heavy', offset: { x: 2, y: 0 } }], 0.01);
const light = balancedStep.world.bodies.find(item => item.id === 'light');
const heavy = balancedStep.world.bodies.find(item => item.id === 'heavy');
assert.ok(Math.abs((heavy.position.x - light.position.x) - 2) < 1e-8, 'two dynamic bodies must satisfy the mounted offset');
const centerOfMass = (light.position.x * 1 + heavy.position.x * 3) / 4;
assert.ok(Math.abs(centerOfMass - 3) < 1e-8, 'inverse-mass position projection must preserve center of mass in the no-force case');

let gravityWorld = Core.createWorld({ gravity: { x: 0, y: 10 }, bounds: false, sleep: { enabled: false } });
gravityWorld = add(gravityWorld, { id: 'root', type: 'static', position: { x: 0, y: 0 } });
gravityWorld = add(gravityWorld, { id: 'hung', type: 'dynamic', position: { x: 1, y: 0 }, mass: 1, linearDamping: 0 });
const gravityMount = [{ id: 'hung-mount', a: 'root', b: 'hung', offset: { x: 1, y: 0 } }];
const noPost = Mounts.step(gravityWorld, gravityMount, 0.1, {
  positionIterations: 8,
  velocityIterations: 4,
  postPositionIterations: 0,
  postVelocityIterations: 0
});
const stabilized = Mounts.step(gravityWorld, gravityMount, 0.1, {
  positionIterations: 8,
  velocityIterations: 4,
  postPositionIterations: 4,
  postVelocityIterations: 2
});
assert.ok(noPost.mountDiagnostics.after[0].errorDistance > 1e-4, 'gravity must demonstrate post-integration mount drift when post stabilization is disabled');
assert.ok(stabilized.mountDiagnostics.after[0].errorDistance < 1e-8, 'post-core stabilization must restore fixed translation offset under gravity');
assert.ok(stabilized.mountDiagnostics.maxErrorAfterStabilization < stabilized.mountDiagnostics.maxErrorAfterCoreStep, 'post-core stabilization must reduce mount error');
assert.equal(stabilized.mountDiagnostics.contactEvidenceBasis, 'CORE_STAGE_BEFORE_POST_TRANSLATION_MOUNT_STABILIZATION');
assert.ok(stabilized.core.worldBeforePostMountStabilization, 'core-stage world must remain separately inspectable');
assert.equal(stabilized.world.diagnostics.checksum, Core.checksum(stabilized.world), 'final diagnostics checksum must describe stabilized final world');

let immovable = Core.createWorld({ gravity: { x: 0, y: 0 }, bounds: false });
immovable = add(immovable, { id: 's1', type: 'static', position: { x: 0, y: 0 } });
immovable = add(immovable, { id: 's2', type: 'static', position: { x: 5, y: 0 } });
const prepared = Mounts.prepareWorld(immovable, [{ id: 'static-static', a: 's1', b: 's2', offset: { x: 1, y: 0 } }], { positionIterations: 1, velocityIterations: 1 });
assert.equal(prepared.positionReceipts[0].solved, false, 'two immovable bodies must not be falsely reported as solved');
assert.equal(prepared.positionReceipts[0].reason, 'NO_DYNAMIC_MASS');

function deterministicSeed() {
  let world = Core.createWorld({ gravity: { x: 0, y: 2 }, bounds: false, sleep: { enabled: false } });
  world = add(world, { id: 'base', type: 'kinematic', position: { x: 0, y: 0 }, velocity: { x: 0.25, y: 0 } });
  world = add(world, { id: 'module', type: 'dynamic', position: { x: 1.5, y: -0.5 }, mass: 2, linearDamping: 0 });
  return world;
}
const replayMount = [{ id: 'module-mount', a: 'base', b: 'module', offset: { x: 1.5, y: -0.5 } }];
const simA = Mounts.simulate(deterministicSeed(), replayMount, 60, 1 / 60);
const simB = Mounts.simulate(deterministicSeed(), replayMount, 60, 1 / 60);
assert.equal(simA.checksum, simB.checksum, 'translation-mount simulation must replay deterministically in one JS runtime');
assert.equal(simA.world.stepIndex, 60);
assert.ok(simA.mountDiagnostics.after[0].errorDistance < 1e-8, 'deterministic replay must retain mounted offset');

const invalid = Mounts.validate(staticDynamicWorld(), [{ id: 'bad', a: 'parent', b: 'missing' }]);
assert.equal(invalid.ok, false);
assert.match(invalid.errors.join(' '), /body not found/i);

console.log('UC Translation Mounts selftest: PASS (fixed offsets, kinematic following, inverse-mass balance, post-core stabilization, immovable truth and deterministic replay)');
