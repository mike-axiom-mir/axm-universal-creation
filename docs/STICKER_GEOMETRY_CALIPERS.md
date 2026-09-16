# Sticker Geometry Calipers v0.1

Universal Creation now has a read-only geometry measurement layer for the Design Workshop and Sticker construction loop.

The purpose is narrow: replace the earlier **size = HOLD** boundary with evidence from the actual 3D sticker bytes when that evidence is available.

## Workshop analogy

A human builder may use a ruler or caliper after roughing out a plan. The plan says what was intended; the instrument measures what physically exists.

UC now has the same separation:

1. `axm.design-sketch/v0.1` records rough spatial intent.
2. Workshop Construction binds exact stickers and places them against that plan.
3. Sticker Geometry Calipers read the actual GLB geometry behind those exact pins.
4. Placement and measured dimensions are compared without silently changing the design.

The sketch remains intent. The geometry bytes remain observation. Neither is rewritten to make the other appear correct.

## What is actually measured

The caliper does not trust glTF accessor `min` / `max` metadata.

For supported rigid sticker geometry it:

- reads the exact content-addressed GLB asset bytes from the local sticker registry;
- validates the GLB through UC's existing pose/geometry machinery;
- walks the default scene and exact node transforms;
- reads actual `POSITION` accessor values;
- reads actual triangle indices, or the exact non-indexed triangle order;
- ignores unreferenced POSITION rows when computing rendered-triangle bounds;
- applies exact sticker attachment anchors, instance offsets and instance scale;
- applies every nested assembly transform;
- measures each direct assembly child in **that child's own socket coordinate frame**.

The last point matters. Rotating a long beam 90 degrees in the parent does not make its local length become its local height. The caliper frame rotates with the part.

## Nested stickers and multiplied variants

There is no special geometry format for multiplied stickers.

A multiplied sticker is an ordinary exact-pinned `axm.sticker/v1` assembly wrapper. The caliper expands that wrapper and all other nested reusable assemblies until it reaches actual GLB leaves, then transforms their real triangle vertices back into the direct part's socket frame.

This means the following is measurable without baking a duplicate mesh:

`source GLB -> multiplied wrapper scale -> reusable module -> workshop assembly`

The original shared source asset remains content-addressed and unchanged.

## Operations

### `measure-sticker-geometry`

Measures one exact 3D sticker in its external sticker socket frame.

The result includes:

- exact sticker pin;
- metre-space bounds;
- XYZ size;
- referenced triangle-point count;
- triangle / primitive / leaf counts;
- source asset digests;
- explicit geometry issues;
- animation tracks ignored by the rest-pose measurement.

### `measure-sticker-assembly-parts`

Measures every direct child of one exact assembly. Nested assemblies are flattened underneath each direct child, but each direct child keeps a separate measurement frame and result.

### `compare-sticker-geometry`

Combines the existing Workshop Construction placement report with actual geometry evidence.

A part can now separately report:

- placement status;
- geometry-observation status;
- size status;
- combined status.

The size comparison uses the rough sketch part `size` and the sketch size tolerance. Existing `size` gauges are also re-evaluated from the actual measured geometry rather than remaining automatically `HOLD`.

## Units

GLB geometry is measured in metres under the existing UC geometry convention.

v0.1 compares dimensions only when the sketch declares:

```text
units = "m"
```

A sketch using `cm`, `mm`, `in`, or another identifier remains `HOLD` for size comparison. The machine does not silently invent a conversion contract.

A later unit fabric can make conversions explicit without weakening this boundary.

## Animation boundary

v0.1 measures the **authored/default rest pose**.

Animation clips may exist and their presence is reported, but the caliper does not sample every keyframe or derive a swept motion envelope. Therefore a rest-pose size PASS does not prove that an animated part stays inside those bounds during motion.

## Geometry integrity

Bounds come only from triangle-referenced vertices. Unsupported compressed/morph/skinned geometry, invalid indices, resource-limit overflow, malformed assets, or other unsupported evidence does not become a partial PASS.

Degenerate triangles are surfaced as geometry-integrity failure evidence even when a numerical bound can still be computed.

## Truth boundary

A caliper PASS can support statements such as:

- this exact sticker's rest geometry measures `1.0 x 0.2 x 0.2 m` in its socket frame;
- this exact placed instance matches the sketch dimension within the declared tolerance;
- this nested multiplied module's real source geometry was measured after its exact stored scale and transforms;
- this result came from actual indexed triangle vertices, not accessor bounds metadata.

It does **not** prove:

- two meshes physically fit together;
- they do not intersect;
- there is enough mechanical clearance;
- an animated part stays inside the rest bound;
- strength or manufacturability;
- material correctness;
- visual quality or aesthetics;
- target-engine acceptance or runtime performance.

Those require their own evidence.

## Repair boundary

This wave is measurement only.

If an exact part is too large or too small relative to the sketch, the report says so. It does not silently scale the sticker, deform its mesh, choose a replacement sticker, or rewrite the sketch.

That keeps the next repair decision inspectable: the machine can later decide whether an explicit instance-scale adjustment, a different sticker, a geometry edit, or a sketch revision is the appropriate action.

## Human / script / AI parity

The same functions are exposed through:

- `AXM-CAP-STICKER-GEOMETRY-CALIPERS` in `UniversalCreationMachine`;
- `axm-sticker-create` JSON operations.

A human-authored request, an AI-generated request and a replayed script therefore hit the same measurement contracts.
