# Simulation to Reality

AXM Universal Creation can now place a bounded simulated creation state between intent and reality.

The purpose is not to make a decorative preview before building. The simulated state is itself a creation substrate. A specialist can later materialize the exact state that was simulated instead of receiving a prose description and inventing a second interpretation.

The current loop is:

`intent -> simulated thought -> known improvements -> cinematic projections -> NO_KNOWN_IMPROVEMENTS -> freeze exact thought -> Paintgun materialization -> real project evidence`

If later real evidence exposes something the simulator did not know, the loop can reopen:

`reality contradiction/new observation -> explicit new gap or improvement rule -> simulate again`

## The stopping condition

The simulator does **not** search for `PERFECT`.

Its strongest current stop state is:

`NO_KNOWN_IMPROVEMENTS`

That means only:

> No currently registered deterministic improvement rule can identify another change to this exact simulated thought.

It does not mean optimum, beautiful, semantically complete, physically accurate, universally correct, or impossible to improve.

New knowledge may make an old `NO_KNOWN_IMPROVEMENTS` state improvable again without contradiction.

The current v0 rules can:

- complete known Paintgun channel dependencies when a deterministic value is available;
- derive neutral material, light, shade, and solid-skin channels;
- clamp known render parameters to their declared ranges;
- fit supported shapes inside the declared canvas when requested;
- select a higher-contrast color from caller-supplied known alternatives or palette.

A gap remains a HOLD when no current rule knows how to improve it. For example, a missing shape is not invented merely to make the simulation finish.

## Cinematic thought

Every simulation iteration records the exact thought state and, when that state is renderable, a cinematic SVG projection.

The cinematic view is not independent artwork. It is one deterministic projection of the scene graph.

For the current grammar:

`thought state -> deterministic cinematic renderer -> SVG frame`

The final frame is digest-bound to the final thought.

This gives the machine something closer to an inspectable visual thought than a text-only draft while avoiding a claim that an opaque hidden imagination exists.

A future 3D engine, game engine, physics world, renderer, or learned simulator may expose richer projections while keeping the same boundary: the state being viewed must remain identifiable and the evidence type must say what was actually simulated.

## Paintgun specialist

`AXM-CAP-PAINTGUN-SPECIALIST` is the first specialist that pulls one final simulated thought into an ordinary real project artifact.

Every visual object currently requires six separate but mutually necessary channels:

1. `shape`
2. `material`
3. `color`
4. `light`
5. `shade`
6. `skin`

These are not six unrelated decorations. Together they define one renderable object state.

The vocabulary remains deliberately open. A material may be named `glass`, `steel`, `liquid-starship-ceramic`, or a future material the original kernel never listed. The name does not magically prove physical behavior. The currently rendered material contract is carried by explicit values such as metallic, roughness, opacity, and emission, alongside the other channels.

This preserves both directions:

- **open creation vocabulary**: a new material or visual concept does not need to be on a fixed master list before it can be represented;
- **closed current evidence**: the machine only claims the parameters and renderer behavior it actually implements.

## Pull the thought into reality

Paintgun materialization requires all of the following:

- simulation status is exactly `NO_KNOWN_IMPROVEMENTS`;
- the final thought satisfies the complete Paintgun scene grammar;
- the supplied final thought digest equals a fresh digest of the thought being materialized;
- re-rendering that exact thought produces the same SVG bytes stored as the simulation's final cinematic projection.

Only then is the ordinary creation project written.

The current materialized project contains:

- `thought.json` — the exact normalized final simulated scene;
- `scene.svg` — the deterministic cinematic projection of that scene;
- `index.html` — a small local viewing shell.

For this v0 grammar, the scene SVG shown by the simulator and the scene SVG placed into the real project are byte-identical.

That is the first concrete implementation of:

`simulate a thought -> freeze it -> specialist builds from that thought`

rather than:

`simulate -> describe it again -> second builder guesses what was meant`

## What this does not prove

The current simulator is deliberately small. It does not yet prove:

- photoreal or physical material behavior;
- arbitrary 3D geometry;
- animation or temporal behavior;
- browser interaction behavior;
- game mechanics;
- real lighting physics;
- human aesthetic preference;
- semantic correctness of the requested design;
- that no unknown improvement exists.

The current cinematic renderer is SVG/static-web evidence, not a physical world simulator.

Those are extension points, not reasons to weaken the current truth label.

## Why the architecture matters

The important multiplier is not this first SVG renderer. It is the reusable sequence:

`state -> simulate -> find known improvements -> change state -> repeat -> freeze -> materialize -> observe reality`

A richer future simulator could run a game world, UI interaction graph, mechanical system, 3D scene, software architecture, or whole candidate machine through the same pattern.

The machine can then spend simulation before spending reality while still allowing reality to correct simulation afterward.

The reality boundary therefore remains open in both directions:

`simulation -> reality`

and

`reality -> new knowledge -> simulation`
