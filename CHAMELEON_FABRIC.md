# Chameleon Fabric

Chameleon Fabric extends the existing adaptive visual creation body without adding another top-level machine subsystem.

The live surface remains:

`AXM-CAP-SIMULATE-CREATION`

Version `0.3.0` adds four connected capabilities around the existing Vector Cell -> simulation -> Paintgun chain:

1. continuous visual morphing;
2. richer material-graph truth;
3. explicit environmental sensor fusion;
4. reality-to-simulator discrepancy feedback and bounded recalibration.

The design rule is:

> Keep one inspectable state lineage while allowing the visible expression, material description, environmental response and simulation assumptions to change.

## 1. Continuous morphing

A Vector Cell already keeps stable identity while explicit scale or choice selects a representation. Chameleon Fabric adds states between those representations.

### Compatible geometry

When the same object exists at both endpoints and its geometry is compatible, the current implementation interpolates the geometry and visual channels continuously.

Supported geometry interpolation in this generation:

- rectangle;
- circle;
- ellipse;
- polygon when both endpoints contain the same number of points.

The interpolated channels include:

- shape numbers;
- material numbers;
- color;
- light;
- shade;
- skin values when their structure is compatible;
- camera state;
- canvas background.

The explicit `factor` is bounded from `0` to `1`.

`0` is the exact source endpoint.

`1` is the exact target endpoint.

Intermediate factors produce deterministic intermediate thoughts and digests.

### Incompatible topology

A rectangle cannot truthfully become a circle through the current bounded geometry grammar, and a one-object coarse representation may not have the same topology as a three-object detailed representation.

Chameleon Fabric does not call those cases geometry interpolation.

Instead it continuously crossfades source and target objects while retaining an explicit morph trace.

This means:

`same topology -> interpolate`

`different topology -> crossfade`

A future renderer or geometry organ may add stronger topology-aware deformation without changing this truth boundary.

### Path boundary

SVG paths interpolate as geometry only when their path data is identical. Different path data crossfades in this generation rather than being silently rewritten.

## 2. Rich material graph

Paintgun originally required six composition channels:

`shape + material + color + light + shade + skin`

Chameleon Fabric keeps those channels as the current materialization contract while allowing the material channel to retain a richer structured graph.

Current rich material fields include:

- material name;
- metallic;
- roughness;
- opacity;
- emission;
- transmission;
- index of refraction (`ior`);
- clearcoat;
- anisotropy;
- subsurface amount;
- normal strength;
- displacement;
- procedural microstructure.

Current bounded microstructure kinds:

- none;
- fibers;
- stripes;
- checker;
- noise;
- scales.

### Renderer truth versus material truth

The current materializer is still deterministic SVG/static-web output.

SVG does not physically implement all of the material properties above.

The compiler therefore emits two things at the same time:

1. a Paintgun-compatible visual approximation that the current renderer can materialize;
2. retained structured material descriptors for richer future renderers.

Examples:

- fibers or stripes may be approximated with a linear gradient;
- scale/noise/checker microstructure may be approximated with a radial gradient;
- transmission may influence current visual opacity;
- clearcoat may influence the current visual roughness approximation;
- normal strength remains an explicit normal descriptor;
- displacement remains an explicit displacement descriptor;
- IOR/refraction, anisotropy and subsurface remain explicit material state even when current SVG cannot physically reproduce them.

An approximation receipt states how each rich field was represented.

Therefore:

`material field exists` does not mean `current SVG physically simulates that material field`.

The richer material state can later be consumed by a more capable renderer without changing the source concept into a different material.

## 3. Environmental adaptation

Chameleon adaptation may be driven by explicit environmental readings.

The current engine never claims that it sampled hardware, a browser sensor or the physical world by itself.

The caller supplies numeric readings such as:

- temperature;
- humidity;
- ambient light;
- distance;
- pressure;
- speed;
- performance budget;
- interaction intensity;
- any other explicitly named numeric signal.

A policy declares one or more drivers.

Each driver specifies:

- sensor name;
- minimum;
- maximum;
- weight;
- optional inversion.

The reading is normalized into `0..1`. The declared weighted readings are fused into one inspectable adaptation factor.

That factor drives a continuous morph between explicit `from_state` and `to_state` Vector Cell endpoints.

Example:

`temperature 20 in range 0..40 -> 0.5`

`ambient light 50 in range 0..100 -> 0.5`

`equal weights -> adaptation factor 0.5`

The receipt retains every sensor reading, normalization and weight.

If a policy references a reading that was not supplied, the operation holds/errors instead of inventing environmental state.

### Why this is deliberately simple

The first sensor-fusion rule is transparent weighted normalization rather than a hidden learned controller.

It is small enough to inspect, test and replace later.

A future sensor-fusion organ can become more sophisticated while still emitting an explicit factor and evidence trace.

## 4. Reality feedback

Simulation is useful only while reality remains allowed to disagree with it.

The feedback loop is:

`simulate -> materialize/use -> external observation -> compare -> discrepancy -> reopen -> correction candidate -> re-simulate`

### External observation

Reality feedback requires an explicitly supplied observation containing:

- observation source;
- executor/observer identity string;
- one or more measurements;
- exact object id;
- channel;
- field;
- observed value;
- optional tolerance;
- explicit context key.

The system binds that evidence to one exact `NO_KNOWN_IMPROVEMENTS` simulation digest.

The deterministic engine does not claim it looked at a browser, human perception, camera or physical object unless an external observer actually supplied that evidence.

### Discrepancy

For a numeric field:

`delta = observed - simulated`

A discrepancy outside the supplied tolerance reopens simulation.

The first recalibration generation can propose a simple exact-condition inverse correction:

`candidate input = simulated - delta`

Example:

`simulated roughness = 0.20`

`observed roughness-equivalent measurement = 0.30`

`delta = +0.10`

`first-order candidate = 0.10`

The corrected thought then passes through the existing simulator again.

This does **not** prove the correction is right. It is a testable candidate for the exact observed condition.

Nonnumeric discrepancies remain explicit gaps until a deterministic correction rule exists.

### No silent universal law

Every feedback receipt contains:

`generalization_allowed: false`

One mismatch does not become a global renderer law.

Repeated mismatches also do not silently become a global law.

Optional calibration history can retain exact-context discrepancy evidence at:

`state/simulation-calibration.json`

That history can calculate repeated numeric delta statistics for future rule design, but an explicit later change is still required before the simulator's general rules change.

This protects the distinction between:

`observed evidence`

and

`generalized model rule`.

## One connected body

The intended flow can use all four upgrades together:

`Vector Cell canonical body`

`-> explicit environment readings`

`-> sensor fusion`

`-> continuous chameleon state`

`-> optional rich material graph`

`-> simulation`

`-> NO_KNOWN_IMPROVEMENTS`

`-> Paintgun materialization`

`-> external reality observation`

`-> discrepancy receipt`

`-> exact-condition recalibration candidate`

`-> re-simulation`

The four additions therefore do not form four independent agent-like systems. They extend one state lineage.

## Reused Universal Creation anatomy

The implementation makes existing anatomy live-backed rather than inventing a parallel vocabulary.

Implemented by the simulation/chameleon surface:

- `AXM-11-3D-SPATIAL-C-018-morph-target`;
- `AXM-13-ANIMATION-VIDEO-C-005-morph-animation`;
- `AXM-12-RENDERING-MATERIALS-C-007-material-graph`;
- `AXM-23-PROCEDURAL-C-013-procedural-material-graph`;
- `AXM-12-RENDERING-MATERIALS-O-001-material-compiler`;
- `AXM-15-SIMULATION-XR-C-019-sensor-model`;
- `AXM-15-SIMULATION-XR-O-011-sensor-fusion-organ`.

Used as explicit anatomy without overstating implementation:

- `AXM-10-2D-IMAGING-C-021-normal-map`;
- `AXM-01-PROVENANCE-A-012-observation`;
- `AXM-13-ANIMATION-VIDEO-A-013-morph-weight`.

## Current boundaries

Chameleon Fabric currently does not claim:

- physically accurate 3D material rendering;
- arbitrary topology-aware mesh deformation;
- hardware or browser sensor access;
- autonomous perception of reality;
- automatic universal learning from discrepancy evidence;
- semantic or aesthetic perfection;
- that more adaptation is automatically better.

It does provide the deterministic state machinery required to add those capabilities later without throwing away identity, lineage or evidence boundaries.
