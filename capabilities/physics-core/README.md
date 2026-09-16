# AXM Universal Creation Physics Core

This capsule pulls the real AXM Physics Core out of `mike-axiom-mir/axm-collaboration-platform` and grows it inside Universal Creation without rewriting the donor source.

## Source integrity

The imported files under `source/` are byte-for-byte copies:

- `source/axm-physics-core.js` — AXM Physics Core v0.3.1, Git blob `b21b5d71f93c532b26e580766a7f5505024c8cfd`
- `source/axm-physics-adapter.js` — shared physics adapter, Git blob `666587df5a8849be3bf0ad8708c63679f7366adb`

`SOURCE_MANIFEST.json` records the donor repository, observed source commit and exact blob lineage. `selftest.js` recomputes both Git blob hashes before exercising the UC extension.

The donor core remains the collision/integration authority. UC-specific growth lives beside it in `uc-physics-fabric.js`.

## What the imported core already gives UC

The source core provides deterministic-order 2D prototype physics with fixed stepping, adaptive substeps, dynamic/static/kinematic bodies, circle and axis-aligned box collision, gravity, forces, impulses, damping, restitution, friction, sensors, collision filtering, contact lifecycle, sleeping/waking, spatial-hash broadphase, persistent contact manifolds, optional warm starting, diagnostics, checksums, replay traces, point queries and raycasts.

## UC Physics Fabric v0.1

`uc-physics-fabric.js` adds composable creation-level controls around that core:

- named materials with friction, restitution, damping, gravity scale, explicit mass or density-derived mass;
- batch body construction using those materials;
- uniform, radial, vortex and drag force fields, optionally bounded to circle or box regions;
- force-based spring-distance constraints with stiffness, damping and force caps;
- explicit velocity and seek drivers for dynamic or kinematic bodies;
- deterministic scheduled actions for force, impulse, velocity, gravity, enable/disable and teleport operations;
- one-step and multi-step simulation with UC receipts layered over the core evidence;
- bounded sampled traces and final core checksums;
- point query, raycast and inspection routes;
- a small adapter surface so humans, recipes or AI orchestration can invoke the same deterministic capabilities.

## Boundary

This is a real increase in UC capability, but it is not a claim that physics is finished.

The imported v0.3.1 core does **not** claim scientific validation, continuous rigid-body rotation, angular inertia, hard rigid joints, deformables, fluids, 3D physics or deterministic agreement across different JavaScript engines. The UC spring-distance layer is deliberately labeled as a force-based spring rather than pretending to be a hard joint solver.

Those missing branches are future physics work and should be added with their own evidence instead of being implied by this graft.

## Use

```js
const Physics = require('./capabilities/physics-core');

let fabric = Physics.fabric.createFabric({
  world: { gravity: { x: 0, y: 9.81 }, bounds: false },
  materials: [{ id: 'rubber', density: 1.1, restitution: 0.75, friction: 0.9 }],
  bodies: [
    { id: 'ball', material: 'rubber', shape: { kind: 'circle', radius: 0.4 }, position: { x: 0, y: 0 } }
  ],
  fields: [
    { id: 'side-wind', kind: 'uniform', acceleration: { x: 1.5, y: 0 } }
  ]
});

const result = Physics.fabric.stepFabric(fabric, 1 / 60);
fabric = result.fabric;
console.log(result.world.bodies[0].position, result.diagnostics.checksum);
```

Run the capsule check with:

```bash
node capabilities/physics-core/selftest.js
```

The selftest verifies source hashes first, then exercises materials, all four field types, springs, drivers, scheduled actions, stepping and deterministic same-runtime replay.
