# Procedural Effect Graph v0.1

This is the first bounded Universal Creation implementation from the GIMP / Script-Fu / GEGL / G'MIC procedural-effects research.

The architectural target is larger than an image filter:

`editable recipe -> deterministic canonical effect state -> replaceable realizations`

The first executable capability is `electric-arc`.

## Why the graph is canonical

A reusable effect should not become a PNG, SVG, browser animation or game-engine particle effect too early. The v0.1 electric arc first produces `axm.procedural-effect-graph/v0.1` containing normalized paths, consolidated edges, traversal intensity, source/target state, phase values and deterministic topology identity.

The current SVG and HTML files are realizations of that state. They are deliberately not source authority.

That allows a later adapter to reuse the same graph as:

- SVG/CSS in a website or app;
- polylines, particles or a shader input in a game;
- animated drawing/flicker through the stored path phase;
- emissive 3D curves or swept geometry;
- a crack/root/river/magic-path style realization when semantics justify it.

Those adapters are not claimed implemented in v0.1.

## Algorithm

The implementation is original AXM Python using the standard library only. No GIMP, G'MIC or donor code is embedded.

The high-level algorithm was informed by the reusable procedural pattern found during research, especially cost-field path routing:

1. Build a seeded multi-octave scalar cost field.
2. Optionally lower travel cost around explicit guide points.
3. Compute a target-rooted 8-neighbour Dijkstra routing field.
4. Start a bounded set of deterministic walkers near the requested source.
5. Trace minimal-cost paths toward the target.
6. Count shared edges so converging trunks naturally receive stronger intensity.
7. Preserve the paths/edges as canonical normalized state.
8. Realize the graph as layered SVG core + glow without changing topology.

This is a creative procedural path generator. It does not simulate plasma physics or electrical discharge.

## Call surfaces

Human / command line:

```sh
axm-effects catalog
axm-effects electric-arc examples/procedural-effects/electric-arc.json creations/electric-arc
```

Without installing the package:

```sh
PYTHONPATH=src python -m axm_uc.procedural_effects electric-arc \
  examples/procedural-effects/electric-arc.json creations/electric-arc
```

Python / deterministic program:

```python
from axm_uc.procedural_effects import build_electric_arc, publish_procedural_effect

result = build_electric_arc(request)
publish_procedural_effect("creations/electric-arc", request)
```

Machine adapter:

```python
from axm_uc.procedural_effects import operate_procedural_effect

operate_procedural_effect(
    machine_root,
    {"request": request, "path": "creations/electric-arc"},
)
```

The machine adapter refuses output paths outside its supplied root.

## Output

A successful publication creates a new directory and refuses overwrite:

- `recipe.json` — validated editable controls;
- `effect-graph.json` — canonical path topology/state;
- `effect.svg` — current vector realization;
- `preview.html` — local browser viewing surface;
- `receipt.json` — recipe/graph identities and truth boundary.

Changing only color, line width or glow changes the recipe/realization but not graph identity. Changing seed, guides or topology controls changes the canonical graph.

## Controls

Topology controls:

- normalized source and target;
- seed;
- routing grid;
- walker count;
- source spread;
- octave count;
- roughness;
- optional guide points, influence strength and radius.

Realization controls:

- color;
- optional background;
- core width;
- glow width;
- glow strength.

Bounds are deliberate. Expensive requests fail instead of silently consuming unbounded resources.

## Existing Universal Creation relationship

This does not replace the existing procedural texture/material forge, Asset Atom Fabric, game styles, Render Fabric work or AetherFX.

Universal Creation already owns deterministic seeded texture/material generation and renderer-neutral asset composition. This layer adds a missing kind of source: reusable procedural **effect topology** whose realization can vary independently.

The current implementation remains standalone inside Universal Creation so the paused Collaboration Platform does not need to change.

## Truth boundary

The v0.1 evidence can establish:

- deterministic topology under the same implementation and recipe;
- explicit seed/parameter/guide lineage;
- bounded minimal-cost paths that reach the target;
- editable canonical graph state;
- a real offline SVG/HTML realization;
- human, Python and machine-callable interfaces.

It does not establish:

- physical lightning correctness;
- volumetric lighting;
- collision or damage behavior;
- game-engine/native-app adapters;
- 3D curve extrusion;
- continuous animation quality;
- performance on arbitrary devices;
- aesthetic quality merely because rendering is expensive.

The next useful expansion should reuse this recipe/graph/realization split rather than turning each new effect into an isolated renderer-specific implementation.
