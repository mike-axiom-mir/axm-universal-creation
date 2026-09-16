'use strict';

const assert = require('assert');
const Core = require('./source/axm-physics-core.js');
const Composer = require('./uc-constraint-composer.js');
const Isolation = require('./uc-constraint-collision-isolation.js');

function add(world, spec) {
  return Core.addBody(world, spec).world;
}

function assemblyWorld(group) {
  const collision = group == null ? undefined : { category: 1, mask: 2147483647, group };
  let world = Core.createWorld({ gravity: { x: 0, y: 0 }, bounds: false, sleep: { enabled: false } });
  world = add(world, {
    id: 'root',
    type: 'static',
    shape: { kind: 'circle', radius: 1 },
    position: { x: 0, y: 0 },
    collision
  });
  world = add(world, {
    id: 'payload',
    type: 'dynamic',
    shape: { kind: 'circle', radius: 1 },
    position: { x: 0, y: 0 },
    mass: 1,
    linearDamping: 0,
    collision
  });
  return world;
}

const constraints = {
  mounts: [{ id: 'assembly-mount', a: 'root', b: 'payload', offset: { x: 0, y: 0 } }],
  distanceJoints: [],
  distanceLimits: []
};

function hasPairContact(world, a, b) {
  return (world.contacts || []).some(contact =>
    (contact.a === a && contact.b === b) || (contact.a === b && contact.b === a)
  );
}

const validation = Isolation.validate(assemblyWorld(), constraints);
assert.equal(validation.ok, true);
assert.equal(validation.componentCount, 1);
assert.match(validation.warnings.join(' '), /component-wide/i);
assert.match(validation.warnings.join(' '), /distance limits/i);
assert.match(validation.warnings.join(' '), /nonzero caller collision\.group/i);

const baseline = Composer.step(assemblyWorld(), constraints, 0.01);
assert.equal(
  hasPairContact(baseline.core.worldBeforePostCompositeStabilization, 'root', 'payload'),
  true,
  'without isolation the overlapping constrained pair must reach donor-core contact detection'
);

const isolated = Isolation.step(assemblyWorld(), constraints, 0.01);
assert.equal(isolated.world.stepIndex, 1, 'isolation wrapper must still perform exactly one donor-core integration step');
assert.equal(isolated.isolationDiagnostics.componentCount, 1);
assert.equal(isolated.isolationDiagnostics.appliedComponents, 1);
assert.equal(isolated.isolationDiagnostics.skippedComponents, 0);
assert.equal(isolated.isolationDiagnostics.isolatedBodies, 2);
assert.equal(isolated.isolationDiagnostics.receipts[0].temporaryGroup, -1, 'first eligible component should deterministically use -1 when unused');
assert.equal(
  hasPairContact(isolated.core.worldAsIntegratedWithTemporaryGroups, 'root', 'payload'),
  false,
  'temporary shared negative group must suppress donor-core contact for the connected component'
);
assert.equal(isolated.core.worldAsIntegratedWithTemporaryGroups.bodies.find(item => item.id === 'root').collision.group, -1);
assert.equal(isolated.core.worldAsIntegratedWithTemporaryGroups.bodies.find(item => item.id === 'payload').collision.group, -1);
assert.equal(isolated.world.bodies.find(item => item.id === 'root').collision.group, 0, 'caller collision group must be restored');
assert.equal(isolated.world.bodies.find(item => item.id === 'payload').collision.group, 0, 'caller collision group must be restored');
assert.equal(isolated.world.diagnostics.checksum, Core.checksum(isolated.world), 'restored final diagnostics must match restored final world');
assert.equal(isolated.world.diagnostics.collisionGroupsRestored, true);
assert.match(isolated.limitations.join(' '), /whole connected constraint components/i);
assert.match(isolated.limitations.join(' '), /distance-limit slack semantics/i);
assert.match(isolated.limitations.join(' '), /not scientific validation/i);

const limitOnlyConstraints = {
  mounts: [],
  distanceJoints: [],
  distanceLimits: [{ id: 'slack-assembly-edge', a: 'root', b: 'payload', maxLength: 1 }]
};
const limitAssembly = assemblyWorld();
limitAssembly.bodies.find(item => item.id === 'payload').position.x = 0.5;
const limitPrepared = Isolation.prepare(limitAssembly, limitOnlyConstraints);
assert.deepEqual(limitPrepared.components, [['payload', 'root']], 'a distance-limit edge alone must form an isolation component even while slack');
const isolatedLimitOnly = Isolation.step(limitAssembly, limitOnlyConstraints, 0.01);
assert.equal(isolatedLimitOnly.world.stepIndex, 1, 'distance-limit isolation must still share one donor-core integration');
assert.equal(isolatedLimitOnly.constraints.distanceLimits.length, 1);
assert.equal(isolatedLimitOnly.composerDiagnostics.after.distanceLimits[0].state, 'SLACK', 'component participation must not change distance-limit slack semantics');
assert.equal(
  hasPairContact(isolatedLimitOnly.core.worldAsIntegratedWithTemporaryGroups, 'root', 'payload'),
  false,
  'a distance-limit-only connected component must receive the temporary collision group'
);

const existingGroup = Isolation.step(assemblyWorld(7), constraints, 0.01);
assert.equal(existingGroup.isolationDiagnostics.appliedComponents, 0, 'existing nonzero group semantics must not be overwritten');
assert.equal(existingGroup.isolationDiagnostics.skippedComponents, 1);
assert.equal(existingGroup.isolationDiagnostics.receipts[0].reason, 'EXISTING_GROUP_SEMANTICS');
assert.equal(existingGroup.world.bodies.find(item => item.id === 'root').collision.group, 7);
assert.equal(existingGroup.world.bodies.find(item => item.id === 'payload').collision.group, 7);
assert.equal(
  hasPairContact(existingGroup.core.worldAsIntegratedWithTemporaryGroups, 'root', 'payload'),
  true,
  'skipped component must retain caller collision-group behavior'
);

let two = Core.createWorld({ gravity: { x: 0, y: 0 }, bounds: false, sleep: { enabled: false } });
two = add(two, { id: 'a', type: 'static', position: { x: 0, y: 0 } });
two = add(two, { id: 'b', type: 'dynamic', position: { x: 1, y: 0 }, mass: 1 });
two = add(two, { id: 'c', type: 'static', position: { x: 10, y: 0 } });
two = add(two, { id: 'd', type: 'dynamic', position: { x: 11, y: 0 }, mass: 1 });
two = add(two, { id: 'e', type: 'static', position: { x: 20, y: 0 } });
two = add(two, { id: 'f', type: 'dynamic', position: { x: 21, y: 0 }, mass: 1 });
const twoConstraints = {
  mounts: [{ id: 'm', a: 'a', b: 'b', offset: { x: 1, y: 0 } }],
  distanceJoints: [{ id: 'j', a: 'c', b: 'd', length: 1 }],
  distanceLimits: [{ id: 'l', a: 'e', b: 'f', maxLength: 2 }]
};
const prepared = Isolation.prepare(two, twoConstraints);
assert.deepEqual(prepared.components, [['a', 'b'], ['c', 'd'], ['e', 'f']], 'all supported constraint families must contribute deterministic components by body id');
assert.equal(prepared.receipts[0].temporaryGroup, -1);
assert.equal(prepared.receipts[1].temporaryGroup, -2);
assert.equal(prepared.receipts[2].temporaryGroup, -3);

let reserved = assemblyWorld();
reserved = add(reserved, {
  id: 'unrelated',
  type: 'static',
  position: { x: 100, y: 100 },
  collision: { category: 1, mask: 2147483647, group: -1 }
});
const reservedPrepared = Isolation.prepare(reserved, constraints);
assert.equal(reservedPrepared.receipts[0].temporaryGroup, -2, 'temporary allocator must skip negative group ids already used anywhere in the caller world');

const simA = Isolation.simulate(assemblyWorld(), constraints, 20, 1 / 60);
const simB = Isolation.simulate(assemblyWorld(), constraints, 20, 1 / 60);
assert.equal(simA.checksum, simB.checksum, 'collision-isolated assembly simulation must replay deterministically in one JS runtime');
assert.equal(simA.world.stepIndex, 20);
assert.equal(simA.world.bodies.find(item => item.id === 'root').collision.group, 0);
assert.equal(simA.world.bodies.find(item => item.id === 'payload').collision.group, 0);

console.log('UC Constraint Collision Isolation selftest: PASS (three-family component suppression, caller-group preservation, deterministic allocation/restoration and replay)');
