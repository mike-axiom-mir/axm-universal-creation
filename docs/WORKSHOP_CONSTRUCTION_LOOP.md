# AXM Workshop Construction Loop

This layer sits on top of the Design Workshop and UC's embedded sticker core.
It does not replace either contract.

The bounded v0.1 loop is:

```text
rough design sketch
  -> explicit exact sticker binding for every sketch part
  -> deterministic assembly compile
  -> ordinary immutable axm.sticker/v1 assembly
  -> compare direct child target frames back to the exact sketch
  -> bounded placement repair proposal
  -> explicit new immutable assembly version
  -> compare again
```

## Why this exists

A workshop sketch is useful only if construction can stay related to it.
Humans use drawings, rulers, squares, levels and jigs while building; the machine
now gets a comparable structural loop instead of relying on language or a final
render alone.

The sketch still does **not** choose a real part automatically. A blockout box is
not evidence that one particular sticker is the correct beam, wheel or cockpit.
Every build plan therefore binds each sketch part to one exact sticker
`{id, version, digest}` plus explicit overrides and placement controls.

## Build plan

Schema: `axm.design-sticker-build/v0.1`

A plan contains:

- the exact Design Workshop sketch digest;
- one binding for every sketch part;
- one exact 3D sticker pin per binding;
- explicit parameter overrides;
- explicit normal sticker placement controls.

The sketch part frame becomes the target socket frame for that sticker. The
sticker's own attachment anchor and explicit placement remain active. This is a
connection contract, **not** an inferred geometric-center match.

`compile-sticker-build` is read-only. `save-sticker-build` commits the result as
a normal immutable assembly sticker and appends the exact sketch/build-plan
lineage to provenance.

## Construction evidence

`compare-sticker-assembly` reads an exact saved assembly and compares its direct
child target frames with the exact sketch.

It can prove or fail:

- part target position;
- part target orientation;
- distance/ruler relationships;
- straightedge/alignment relationships;
- spacing-jig relationships;
- square/angle relationships;
- level/orientation relationships;
- symmetry relationships.

It deliberately cannot derive actual mesh size from an assembly recipe.
Therefore size/caliper evidence stays `HOLD` and the overall report stays `HOLD`
when placement passes. A separate `placement_status` may still be `PASS`.

That distinction is intentional: **built where planned** is not the same claim as
**geometry has the planned physical/visual dimensions**.

## Repair

`propose-sticker-repair` recomputes evidence from the exact source assembly. It
may emit only one automatically grounded action type in v0.1:

```text
set-target-frame(part, exact_sketch_frame)
```

Missing parts, extra parts, size changes, geometry edits, source selection,
materials and aesthetic changes are never guessed. They remain unresolved.

`save-sticker-repair` applies an accepted bounded frame repair by creating a new
immutable assembly version. Existing versions are not modified.

If a moved child has explicit rigid motion samples, the motion is rebased by the
same rigid transform and the first sample is rebound exactly to the repaired
target frame. This preserves the declared rigid motion path; it is not an
animation-quality claim.

Parameterized source assemblies are rejected by repair v0.1 rather than silently
invalidating parameter defaults.

## Sticker multiplication composes normally

Sticker Multiplier outputs ordinary exact-pinned `axm.sticker/v1` assembly
wrappers. The construction loop therefore requires no special multiplier path:
a multiplied variant can simply be used as the exact sticker pin for a sketch
part.

This yields a useful machine workflow:

```text
sketch intent
  -> choose exact reusable stickers
  -> construct
  -> measure
  -> repair placement
  -> save useful assemblies
  -> multiply useful variants
  -> reuse those variants in later sketches
```

## Human / script / AI parity

The live Universal Creation capability is
`AXM-CAP-WORKSHOP-CONSTRUCTION-LOOP`.

The same underlying functions are exposed through `axm-sticker-create` using:

- `validate_sketch_build`
- `compile_sketch_build`
- `save_sketch_build`
- `compare_sketch_assembly`
- `propose_sketch_repair`
- `save_sketch_repair`

No external Sticker Fabric service or checkout is required at runtime.

## Truth boundary

This layer proves only exact identity, declared structural placement and the
numeric frame relationships it actually measures. It does **not** prove:

- correct automatic part choice;
- geometric-center correspondence;
- actual source mesh dimensions;
- mesh contact or collision clearance;
- strength or manufacturability;
- physics or joint behavior;
- material correctness;
- visual quality or aesthetics;
- target-engine acceptance or runtime performance.

Those remain separate evidence problems rather than being smuggled into a
`PASS` from a sketch or assembly recipe.
