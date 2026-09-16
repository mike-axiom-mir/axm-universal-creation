'use strict';

const assert = require('assert');
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const Capsule = require('./index.js');
const Core = Capsule.core;
const SourceAdapter = Capsule.sourceAdapter;
const Fabric = Capsule.fabric;

function gitBlobSha(filePath) {
  const bytes = fs.readFileSync(filePath);
  const header = Buffer.from('blob ' + bytes.length + '\0');
  return crypto.createHash('sha1').update(header).update(bytes).digest('hex');
}

const corePath = path.join(__dirname, 'source', 'axm-physics-core.js');
const adapterPath = path.join(__dirname, 'source', 'axm-physics-adapter.js');

assert.equal(Core.VERSION, '0.3.1', 'imported platform core version must remain explicit');
assert.equal(gitBlobSha(corePath), 'b21b5d71f93c532b26e580766a7f5505024c8cfd', 'platform core copy must remain byte-for-byte identical');
assert.equal(gitBlobSha(adapterPath), '666587df5a8849be3bf0ad8708c63679f7366adb', 'platform adapter copy must remain byte-for-byte identical');
assert.equal(SourceAdapter.VERSION, Core.VERSION, 'source adapter must target imported core version');

assert.equal(typeof Fabric.createFabric, 'function');
assert.equal(typeof Fabric.stepFabric, 'function');
assert.equal(Fabric.adapter().id, 'axm-uc-physics-fabric');

let fabric = Fabric.createFabric({
  world: { gravity: { x: 0, y: 0 }, bounds: false },
  materials: [{ id: 'steel', density: 2, friction: 0.8, restitution: 0.1 }],
  bodies: [
    { id: 'a', shape: { kind: 'circle', radius: 0.5 }, position: { x: 0, y: 0 }, material: 'steel' },
    { id: 'b', shape: { kind: 'circle', radius: 0.5 }, position: { x: 2, y: 0 }, mass: 1 },
    { id: 'k', type: 'kinematic', shape: { kind: 'box', halfWidth: 0.25, halfHeight: 0.25 }, position: { x: 0, y: 2 } }
  ],
  fields: [{ id: 'wind', kind: 'uniform', acceleration: { x: 2, y: 0 } }],
  springs: [{ id: 'spring', a: 'a', b: 'b', restLength: 1, stiffness: 10, damping: 0 }],
  drivers: [{ id: 'platform-drive', bodyId: 'k', kind: 'velocity', velocity: { x: 1, y: 0 } }],
  actions: [{ id: 'kick', kind: 'apply-impulse', bodyId: 'b', impulse: { x: 1, y: 0 }, atStep: 1 }]
});

assert.ok(fabric.world.bodies.find(body => body.id === 'a').mass > 1.5, 'material density must derive dynamic mass from shape area');
assert.equal(Fabric.validateFabric(fabric).ok, true);

const first = Fabric.stepFabric(fabric, 0.1);
assert.equal(first.ok, true);
assert.equal(first.world.stepIndex, 1);
assert.equal(first.receipts.actions.length, 1, 'scheduled action must execute once');
assert.equal(first.receipts.drivers.length, 1, 'kinematic driver must execute');
assert.equal(first.receipts.fields.length, 1, 'force field must be evaluated');
assert.equal(first.receipts.fields[0].affectedBodies, 2, 'uniform field must affect both dynamic bodies');
assert.equal(first.receipts.springs.length, 1, 'spring-distance force must be evaluated');
assert.ok(first.world.bodies.find(body => body.id === 'a').velocity.x > 0, 'field plus spring must accelerate body a');
assert.ok(first.world.bodies.find(body => body.id === 'k').position.x > 0, 'kinematic driver must move body k through the imported core');

function oneField(kind, body, field) {
  return Fabric.stepFabric(Fabric.createFabric({
    world: { gravity: { x: 0, y: 0 }, bounds: false },
    bodies: [Object.assign({ id: 'probe', mass: 1 }, body)],
    fields: [Object.assign({ id: 'field', kind }, field)]
  }), 0.1).world.bodies[0];
}

const radial = oneField('radial', { position: { x: 1, y: 0 } }, { center: { x: 0, y: 0 }, strength: 2 });
assert.ok(radial.velocity.x > 0, 'radial field must accelerate away from center for positive strength');

const vortex = oneField('vortex', { position: { x: 1, y: 0 } }, { center: { x: 0, y: 0 }, strength: 2 });
assert.ok(vortex.velocity.y > 0, 'vortex field must add tangential acceleration');

const drag = oneField('drag', { velocity: { x: 10, y: 0 } }, { coefficient: 1 });
assert.ok(drag.velocity.x < 10, 'drag field must oppose velocity');

let seek = Fabric.createFabric({
  world: { gravity: { x: 0, y: 0 }, bounds: false },
  bodies: [{ id: 'seeker', type: 'kinematic', position: { x: 0, y: 0 } }],
  drivers: [{ id: 'seek', kind: 'seek', bodyId: 'seeker', target: { x: 10, y: 0 }, speed: 2 }]
});
seek = Fabric.stepFabric(seek, 0.1).fabric;
assert.ok(seek.world.bodies[0].velocity.x > 1.9, 'seek driver must convert a target into explicit velocity');

const seed = () => Fabric.createFabric({
  world: { gravity: { x: 0, y: 0 }, bounds: false },
  bodies: [{ id: 'x', position: { x: 1, y: 1 } }],
  fields: [{ id: 'push', kind: 'uniform', acceleration: { x: 1, y: 0 } }]
});
const traceA = Fabric.simulateFabric(seed(), 10, 0.1, 5);
const traceB = Fabric.simulateFabric(seed(), 10, 0.1, 5);
assert.equal(traceA.finalChecksum, traceB.finalChecksum, 'same UC fabric input must replay to the same core checksum in one runtime');
assert.equal(traceA.frames.length, 3, 'bounded trace must contain initial, step 5 and step 10 samples');
assert.equal(Fabric.inspectFabric(traceA.fabric).ok, true);

const warningText = Fabric.validateFabric(traceA.fabric).warnings.join(' ');
assert.match(warningText, /not claim scientific validation/i);
assert.match(warningText, /not hard rigid joints/i);

console.log('UC Physics Fabric selftest: PASS (source integrity, materials, fields, springs, drivers, actions, stepping and deterministic trace)');
