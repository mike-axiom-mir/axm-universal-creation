# Creative Quality Gauntlet

This gauntlet tests one creation goal at multiple execution depths. It is intentionally **not** a hand-count benchmark.

Goal:

> Create one game-ready animated armored sci-fi supply crate while preserving editable geometry, UV, material and animation state.

## Quality levels

- `draft` — minimum editable geometric representation plus bounds evidence.
- `game-ready` — multi-part assembled mesh, normals, topology and bounds.
- `production` — game-ready geometry plus explicit UV state, packed layout, procedural texture channels, material state, height-derived normal channel, ORM packing and UV normal evidence.
- `max-current-body` — production state plus non-destructive material-stack detail, scratch masking, rig, skin binding/validation, animation clip, pose sampling/baking and deformed-mesh inspection.

Every level executes through the existing Wave 8 Creative Flow. The goal is unchanged; only requested execution depth changes.

## What is measured

The report records:

- pass/hold state for every quality level;
- operation and family depth;
- retained candidate-state size;
- final-state digest;
- wall-clock execution time and steps/ms for the current runtime.

Wall-clock timing is observational and machine-dependent. It is excluded from the structural digest and is **not** a canonical quality score.

The important efficiency question is whether a higher requested quality level can wake only the extra capability depth it needs instead of activating the entire tool body.

## Truth boundary

A structural gauntlet pass proves the machine can compose and execute the retained creation operations. It does **not** prove artistic taste, AAA visual quality, renderer fidelity, lighting quality or final perceptual acceptance.

The gauntlet also records exact advertised-operation probes for high-value gaps such as hard-surface bevel, general mesh boolean, retargeting, optical-flow tracking, spectral restoration and a final render hand. A missing probe means that exact capability is not exposed in the public Creative Hands catalog; it does not prove no related lower-level subsystem exists elsewhere in Universal Creation.

## Orchestration finding under test

A goal-only Creative Flow request currently returns `HOLD_PLAN_REQUIRED`: V1 can discover and execute capability plans but does not autonomously invent a complete quality-sensitive plan from prose. The gauntlet therefore provides explicit deterministic plans for each quality depth and treats automatic quality planning as a separate orchestration question.

## Verification

`creative-quality-gauntlet-selftest.js` executes all four levels, requires increasing execution depth, checks the expected cross-domain state at the deepest level, records runtime observations and is bound into `tests/test_creative_precision_fabric.py`.
