# Design Workshop + Sticker Multiplier

Universal Creation now has two related deterministic growth surfaces: a rough spatial Design Workshop and a bounded Sticker Multiplier.

## Design Workshop

The workshop externalizes design intent before final construction. It is deliberately closer to a human blockout, ruler, square, level, spacing jig and caliper than to a final renderer.

`axm.design-sketch/v0.1` stores simple bounded parts as:

- stable id
- rough shape (`box`, `cylinder`, `sphere`, `plane`, or `marker`)
- exact rigid 4x4 frame
- declared three-axis size
- role and notes
- exact sketch-wide tolerances
- caller-authored provenance

A sketch may also retain explicit gauges:

- `distance` — ruler / center-to-center target
- `alignment` — straightedge evidence along world X/Y/Z
- `spacing` — equal-spacing jig evidence along an axis
- `angle` — square / relative local-axis angle
- `orientation` — level / local axis against world axis
- `symmetry` — mirrored center evidence across an explicit world-axis plane
- `size` — caliper-style three-axis size target

The corresponding `axm.design-workshop-observation/v0.1` is bound to the exact sketch digest and supplies observed frames/sizes. Comparison returns numeric residuals with `PASS`, `FAIL`, or `HOLD`; it never repairs the design silently.

Through `UniversalCreationMachine.create()` use kind `design-workshop` (or the other declared handles) and one of:

- `inspect-workshop`
- `validate-sketch`
- `compare-sketch`
- `measure-design`
- `materialize-sketch`

`materialize-sketch` writes exact `sketch.json` plus a simple `sketch.svg` front/top/side blockout. The SVG is explicitly schematic and does not replace the exact rigid frames in JSON.

### Truth boundary

Workshop evidence is numeric comparison of caller-supplied plan/state. A passing ruler, square, level, symmetry or size check does not prove mesh fit, collision clearance, load capacity, manufacturability, physics, semantics, aesthetics, or target-engine quality.

## Sticker Multiplier

The multiplier grows a reusable sticker library from exact source stickers without copying the source GLB/editable-source bytes into every variant.

`axm.sticker-multiplication/v0.1` pins one exact 3D source sticker and chooses exactly one growth mode.

### Explicit variants

The caller supplies 1..256 named variants. Each may declare:

- immutable id/version/name
- declared source parameter overrides
- optional rigid instance offset
- optional uniform scale
- tags

### Variant matrix

The caller supplies up to eight axes whose Cartesian product may contain at most 256 results. Axes may be:

- a parameter already declared by the source sticker
- one uniform scale axis

No undeclared parameter mutation and no random variation is inferred.

Each result is an ordinary `axm.sticker/v1` assembly wrapper with one exact child source pin. That means variants are independently reusable while source geometry/assets remain content-addressed once.

The full batch is expanded and validated before `Registry.register_many()` performs one SQLite transaction. If a later variant is invalid or conflicts with an immutable id/version, earlier variants are not partially committed.

Through `UniversalCreationMachine.create()` use kind `sticker-multiplier` / `preview-sticker-multiplication` / `multiply-stickers` with a registry `database` path. The same plan can also be sent to `axm-sticker-create` with operation `preview_multiplication` or `multiply_stickers`.

### Truth boundary

Multiplication proves exact source identity, declared parameter/scale variation, wrapper definition validity and atomic registration. It does not establish that every variant is visually distinct, useful, physically compatible, aesthetically successful, or accepted by a target engine.

## Combined machine workflow

A future creative loop can now stay explicit:

1. rough idea -> Design Workshop sketch
2. blockout -> numeric ruler/square/level/symmetry checks
3. exact construction -> normal Universal Creation capabilities
4. useful component -> save/reuse as a sticker
5. declared variation axes -> Sticker Multiplier family
6. new constructions may consume those exact reusable variants

The sketch remains intent, instrument reports remain evidence, and multiplied stickers remain exact reusable source relationships; none silently becomes aesthetic or physical truth.
