'use strict';

const assert = require('assert');
const Core = require('./source/axm-physics-core.js');
const Joints = require('./uc-distance-joints.js');

function worldWithAnchor(dynamicPosition) {
  let world = Core.createWorld({ gravity: { x: 0, y: 0 }, bounds: false, sleep: { enabled: false } });
  world = Core.addBody(world, {
    id: 'anchor',
    type: 'static',
    shape: { kind: 'circle', radius: 0.2 },
    position: { x: 0, y: 0 }
  }).world;
  world = Core.addBody(world, {
    id: 'mass',
    type: 'dynamic',
    shape: { kind: 'circle', radius: 0.2 },
    position: dynamicPosition || { x: 2, y: 0 },
    mass: 1,
    linearDamping: 0
  }).world;
  return world;
}

const joint = { id: 'link', a: 'anchor', b: 'mass', length: 1 };
assert.equal(Joints.validate(worldWithAnchor(), [joint]).ok, true);

const corrected = Joints.step(worldWithAnchor(), [joint], 0.01);
const mass = corrected.world.bodies.find(item => item.id === 'mass');
assert.ok(Math.abs(mass.position.x - 1) < 1e-8, 'projected distance joint must correct initial position error before the core step');
assert.ok(Math.abs(corrected.jointDiagnostics.after[0].error) < 1e-8, 'zero-force step should retain the target distance');
assert.match(corrected.limitations.join(' '), /translation-only/i);
assert.match(corrected.limitations.join(' '), /not scientific validation/i);

let kicked = worldWithAnchor({ x: 1, y: 0 });
kicked = Core.applyImpulse(kicked, 'mass', { x: 5, y: 0 });
const velocityLocked = Joints.step(kicked, [joint], 0.01);
const lockedMass = velocityLocked.world.bodies.find(item => item.id === 'mass');
assert.ok(Math.abs(lockedMass.velocity.x) < 1e-8, 'joint velocity solve must remove separating axis velocity for a static anchor');
assert.ok(Math.abs(velocityLocked.jointDiagnostics.after[0].error) < 1e-8, 'velocity correction must prevent immediate distance drift in the zero-force case');

let kinematic = Core.createWorld({ gravity: { x: 0, y: 0 }, bounds: false, sleep: { enabled: false } });
kinematic = Core.addBody(kinematic, {
  id: 'platform',
  type: 'kinematic',
  shape: { kind: 'circle', radius: 0.2 },
  position: { x: 0, y: 0 },
  velocity: { x: 1, y: 0 }
}).world;
kinematic = Core.addBody(kinematic, {
  id: 'follower',
  type: 'dynamic',
  shape: { kind: 'circle', radius: 0.2 },
  position: { x: 1, y: 0 },
  mass: 1,
  linearDamping: 0
}).world;
const followJoint = { id: 'follow', a: 'platform', b: 'follower', length: 1 };
const followed = Joints.step(kinematic, [followJoint], 0.1);
const platform = followed.world.bodies.find(item => item.id === 'platform');
const follower = followed.world.bodies.find(item => item.id === 'follower');
assert.ok(platform.position.x > 0.09, 'kinematic anchor must move under the imported core');
assert.ok(follower.position.x > 1.09, 'dynamic body must inherit constrained axis motion from the kinematic anchor');
assert.ok(Math.abs((follower.position.x - platform.position.x) - 1) < 1e-8, 'kinematic following must preserve distance in the zero-force case');

let staticWorld = Core.createWorld({ gravity: { x: 0, y: 0 }, bounds: false });
staticWorld = Core.addBody(staticWorld, { id: 's1', type: 'static', position: { x: 0, y: 0 } }).world;
staticWorld = Core.addBody(staticWorld, { id: 's2', type: 'static', position: { x: 2, y: 0 } }).world;
const staticPrepared = Joints.prepareWorld(staticWorld, [{ id: 'static-link', a: 's1', b: 's2', length: 1 }], { positionIterations: 1, velocityIterations: 1 });
assert.equal(staticPrepared.positionReceipts[0].solved, false, 'two immovable bodies must not be falsely reported as solved');
assert.equal(staticPrepared.positionReceipts[0].reason, 'NO_DYNAMIC_MASS');

function deterministicSeed() {
  let world = Core.createWorld({ gravity: { x: 0, y: 1 }, bounds: false, sleep: { enabled: false } });
  world = Core.addBody(world, { id: 'a', type: 'static', position: { x: 0, y: 0 } }).world;
  world = Core.addBody(world, { id: 'b', type: 'dynamic', position: { x: 1, y: 0 }, mass: 1, linearDamping: 0 }).world;
  return world;
}
const simA = Joints.simulate(deterministicSeed(), [{ id: 'j', a: 'a', b: 'b', length: 1 }], 60, 1 / 60);
const simB = Joints.simulate(deterministicSeed(), [{ id: 'j', a: 'a', b: 'b', length: 1 }], 60, 1 / 60);
assert.equal(simA.checksum, simB.checksum, 'distance-joint simulation must replay deterministically in one JS runtime');
assert.equal(simA.world.stepIndex, 60);

const invalid = Joints.validate(worldWithAnchor(), [{ id: 'bad', a: 'anchor', b: 'missing', length: 1 }]);
assert.equal(invalid.ok, false);
assert.match(invalid.errors.join(' '), /body not found/i);

console.log('UC Distance Joints selftest: PASS (projection, velocity locking, kinematic following, immovable truth and deterministic replay)');
