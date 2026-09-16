'use strict';

const assert = require('assert');
const Core = require('./source/axm-physics-core.js');
const Limits = require('./uc-distance-limits.js');

function worldWithAnchor(position, velocity, gravity) {
  let world = Core.createWorld({
    gravity: gravity || { x: 0, y: 0 },
    bounds: false,
    sleep: { enabled: false }
  });
  world = Core.addBody(world, {
    id: 'anchor',
    type: 'static',
    shape: { kind: 'circle', radius: 0.1 },
    position: { x: 0, y: 0 }
  }).world;
  world = Core.addBody(world, {
    id: 'mass',
    type: 'dynamic',
    shape: { kind: 'circle', radius: 0.1 },
    position: position || { x: 2, y: 0 },
    velocity: velocity || { x: 0, y: 0 },
    mass: 1,
    linearDamping: 0
  }).world;
  return world;
}

const rope = [{ id: 'rope', a: 'anchor', b: 'mass', maxLength: 1 }];
assert.equal(Limits.validate(worldWithAnchor(), rope).ok, true);

const stretched = Limits.prepareWorld(worldWithAnchor({ x: 2, y: 0 }), rope, { positionIterations: 1, velocityIterations: 1 });
const stretchedMass = stretched.world.bodies.find(item => item.id === 'mass');
assert.ok(Math.abs(stretchedMass.position.x - 1) < 1e-8, 'max-only distance limit must project an overstretched tether to its boundary');
assert.equal(stretched.positionReceipts[0].constrained, true);

const slack = Limits.prepareWorld(worldWithAnchor({ x: 0.5, y: 0 }, { x: 3, y: 0 }), rope, { positionIterations: 1, velocityIterations: 1 });
const slackMass = slack.world.bodies.find(item => item.id === 'mass');
assert.ok(Math.abs(slackMass.position.x - 0.5) < 1e-8, 'slack tether must not pull a body toward maxLength');
assert.ok(Math.abs(slackMass.velocity.x - 3) < 1e-8, 'slack tether must not lock allowed relative-axis motion');
assert.equal(slack.velocityReceipts[0].constrained, false);

const outward = Limits.prepareWorld(worldWithAnchor({ x: 1, y: 0 }, { x: 3, y: 0 }), rope, { positionIterations: 1, velocityIterations: 1 });
const outwardMass = outward.world.bodies.find(item => item.id === 'mass');
assert.ok(Math.abs(outwardMass.velocity.x) < 1e-8, 'max boundary must block outward relative-axis speed');
assert.equal(outward.velocityReceipts[0].boundary, 'MAX');

const strut = [{ id: 'strut', a: 'anchor', b: 'mass', minLength: 1 }];
const compressed = Limits.prepareWorld(worldWithAnchor({ x: 0.25, y: 0 }), strut, { positionIterations: 1, velocityIterations: 1 });
const compressedMass = compressed.world.bodies.find(item => item.id === 'mass');
assert.ok(Math.abs(compressedMass.position.x - 1) < 1e-8, 'min-only distance limit must project an over-compressed pair to its boundary');
assert.equal(compressed.positionReceipts[0].constrained, true);

const boundedRange = [{ id: 'range', a: 'anchor', b: 'mass', minLength: 1, maxLength: 2 }];
const inside = Limits.prepareWorld(worldWithAnchor({ x: 1.5, y: 0 }, { x: 2, y: 0 }), boundedRange, { positionIterations: 2, velocityIterations: 2 });
const insideMass = inside.world.bodies.find(item => item.id === 'mass');
assert.ok(Math.abs(insideMass.position.x - 1.5) < 1e-8, 'body inside min/max range must retain its allowed position');
assert.ok(Math.abs(insideMass.velocity.x - 2) < 1e-8, 'body inside min/max range must retain allowed relative motion');
assert.equal(Limits.measureLimit(inside.world, inside.limits[0]).state, 'SLACK');

let equalRangeWorld = Core.createWorld({ gravity: { x: 0, y: 0 }, bounds: false, sleep: { enabled: false } });
equalRangeWorld = Core.addBody(equalRangeWorld, {
  id: 'platform',
  type: 'kinematic',
  shape: { kind: 'circle', radius: 0.1 },
  position: { x: 0, y: 0 },
  velocity: { x: 1, y: 0 }
}).world;
equalRangeWorld = Core.addBody(equalRangeWorld, {
  id: 'follower',
  type: 'dynamic',
  shape: { kind: 'circle', radius: 0.1 },
  position: { x: 1, y: 0 },
  velocity: { x: 0, y: 0 },
  mass: 1,
  linearDamping: 0
}).world;
const equalRange = [{ id: 'equal', a: 'platform', b: 'follower', minLength: 1, maxLength: 1 }];
const followed = Limits.step(equalRangeWorld, equalRange, 0.1);
const platform = followed.world.bodies.find(item => item.id === 'platform');
const follower = followed.world.bodies.find(item => item.id === 'follower');
assert.ok(platform.position.x > 0.09, 'kinematic carrier must move under the preserved donor core');
assert.ok(follower.position.x > 1.09, 'equal min/max limit must inherit boundary-constrained axis motion');
assert.ok(Math.abs((follower.position.x - platform.position.x) - 1) < 1e-8, 'equal min/max distance range must preserve its fixed center distance');

let pair = Core.createWorld({ gravity: { x: 0, y: 0 }, bounds: false, sleep: { enabled: false } });
pair = Core.addBody(pair, { id: 'a', type: 'dynamic', shape: { kind: 'circle', radius: 0.1 }, position: { x: 0, y: 0 }, mass: 1, linearDamping: 0 }).world;
pair = Core.addBody(pair, { id: 'b', type: 'dynamic', shape: { kind: 'circle', radius: 0.1 }, position: { x: 4, y: 0 }, mass: 1, linearDamping: 0 }).world;
const pairPrepared = Limits.prepareWorld(pair, [{ id: 'pair-rope', a: 'a', b: 'b', maxLength: 2 }], { positionIterations: 1, velocityIterations: 0 });
const a = pairPrepared.world.bodies.find(item => item.id === 'a');
const b = pairPrepared.world.bodies.find(item => item.id === 'b');
assert.ok(Math.abs(a.position.x - 1) < 1e-8 && Math.abs(b.position.x - 3) < 1e-8, 'two equal dynamic masses must share distance correction symmetrically');

const gravityStep = Limits.step(worldWithAnchor({ x: 1, y: 0 }, { x: 0, y: 0 }, { x: 0, y: 9.81 }), rope, 1 / 30, {
  positionIterations: 2,
  velocityIterations: 2,
  postPositionIterations: 4,
  postVelocityIterations: 2
});
assert.ok(gravityStep.limitDiagnostics.maxViolationAfterCoreStep > 0, 'donor integration under gravity must be visible before post stabilization');
assert.ok(gravityStep.limitDiagnostics.maxViolationAfterStabilization < 1e-7, 'post stabilization must repair bounded max-distance drift');
assert.equal(gravityStep.limitDiagnostics.contactEvidenceBasis, 'CORE_STAGE_BEFORE_POST_DISTANCE_LIMIT_STABILIZATION');
assert.equal(gravityStep.world.diagnostics.checksum, Core.checksum(gravityStep.world));
assert.match(gravityStep.limitations.join(' '), /not yet a family inside the mixed constraint composer/i);
assert.match(gravityStep.limitations.join(' '), /not scientific validation/i);

let staticWorld = Core.createWorld({ gravity: { x: 0, y: 0 }, bounds: false });
staticWorld = Core.addBody(staticWorld, { id: 's1', type: 'static', position: { x: 0, y: 0 } }).world;
staticWorld = Core.addBody(staticWorld, { id: 's2', type: 'static', position: { x: 2, y: 0 } }).world;
const staticPrepared = Limits.prepareWorld(staticWorld, [{ id: 'static-rope', a: 's1', b: 's2', maxLength: 1 }], { positionIterations: 1, velocityIterations: 0 });
assert.equal(staticPrepared.positionReceipts[0].solved, false, 'two immovable violating bodies must not be falsely reported as solved');
assert.equal(staticPrepared.positionReceipts[0].reason, 'NO_DYNAMIC_MASS');

const invalidRange = Limits.validate(worldWithAnchor(), [{ id: 'bad-range', a: 'anchor', b: 'mass', minLength: 2, maxLength: 1 }]);
assert.equal(invalidRange.ok, false);
assert.match(invalidRange.errors.join(' '), /minLength must be <= maxLength/i);

const missingBounds = Limits.validate(worldWithAnchor(), [{ id: 'missing', a: 'anchor', b: 'mass' }]);
assert.equal(missingBounds.ok, false);
assert.match(missingBounds.errors.join(' '), /requires minLength and\/or maxLength/i);

function deterministicSeed() {
  return worldWithAnchor({ x: 1, y: 0 }, { x: 1.5, y: 0 }, { x: 0, y: 3 });
}
const simA = Limits.simulate(deterministicSeed(), [{ id: 'bounded', a: 'anchor', b: 'mass', minLength: 0.5, maxLength: 1.25 }], 90, 1 / 60);
const simB = Limits.simulate(deterministicSeed(), [{ id: 'bounded', a: 'anchor', b: 'mass', minLength: 0.5, maxLength: 1.25 }], 90, 1 / 60);
assert.equal(simA.checksum, simB.checksum, 'distance-limit simulation must replay deterministically in one JS runtime');
assert.equal(simA.world.stepIndex, 90);

console.log('UC Distance Limits selftest: PASS (rope max, strut min, slack range, equal range following, mass sharing, stabilization, immovable truth and deterministic replay)');
