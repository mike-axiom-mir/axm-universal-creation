# Sticker Clearance / Contact Instruments v0.1

This wave adds the next deterministic workshop instrument after actual geometry calipers: measure how exact built parts relate to one another in the authored/default rest pose.

## Why this exists

A size caliper can prove that one sticker is 1.0 x 0.2 x 0.2 m. It cannot prove that another sticker is 0.03 m away, touching it, or geometrically inside it. Clearance/contact is therefore a separate evidence layer.

The machine loop can now progress through:

`sketch -> exact sticker assembly -> placement gauges -> real geometry calipers -> clearance/contact evidence`

No result from this layer silently edits the asset or assembly.

## Geometry source

The capability reads the same bounded rigid GLB subset as Sticker Geometry Calipers:

- embedded glTF 2.0 GLB
- ordinary TRIANGLES primitives
- actual triangle-referenced POSITION bytes
- exact node transforms
- exact sticker attachment anchors
- exact instance offsets/scales
- exact nested assembly transforms
- multiplied wrappers flattened like ordinary assemblies

Accessor `min` / `max` metadata is not the geometric source of truth.

## Two-stage pair measurement

### Broad phase

For each direct assembly part the instrument derives actual transformed triangle bounds. It records:

- AABB distance lower bound
- whether the AABBs overlap
- per-axis overlap depths

AABB overlap is **not** a contact claim.

### Narrow phase

For bounded part pairs it evaluates actual triangle geometry and records:

- minimum surface distance
- closest point on A
- closest point on B
- number of triangle pairs tested/pruned

Triangle/segment/point distance is used so a broad-phase overlap can still resolve to a positive real clearance.

## Relation vocabulary

### `SEPARATED`

Actual supported triangle surfaces have positive distance above tolerance and no penetration witness.

### `TOUCHING`

Actual surface distance is zero/within tolerance, broad-phase bounds are tangent on at least one axis, and closed-surface sampling does not find an inside witness.

This is intentionally narrower than "any zero distance".

### `PENETRATING`

At least one sampled actual geometry point is classified **inside** the other part's welded closed triangle surface.

This can detect full containment where two surfaces never touch. The report carries the witness point and container/inside part ids.

No penetration-depth value is invented in v0.1.

### `CONTACT_OR_INTERSECTION`

Actual zero-distance evidence exists, but touching versus penetration is not grounded strongly enough. This returns `HOLD` rather than choosing a nicer story.

### `UNMEASURED`

Required geometry is unsupported/incomplete or bounded-work limits prevent the requested relation from being established.

## Closed-surface truth boundary

`ClosedTriangleSurface` checks welded two-triangles-per-edge topology and uses bounded multi-ray point classification. It returns inside/outside/boundary/hold.

That topology check does not independently prove a surface is free from self-intersections. Ambiguous parity/tolerance returns HOLD.

Therefore:

- a positive inside witness is sufficient for the capability's `PENETRATING` claim;
- absence of a sampled inside witness is not silently treated as proof that arbitrary zero-distance geometry only touches;
- unresolved zero-distance cases stay `CONTACT_OR_INTERSECTION`.

## Assembly scanning

`measure-sticker-assembly-clearances` can scan all direct-part pairs for bounded assemblies or an explicit subset supplied by the caller.

Limits keep work finite:

- at most 64 direct parts for this first observer
- at most 256 explicit pair requests
- bounded triangle-pair work per pair and per scan
- bounded rigid source geometry

Callers can request a smaller pair set when a large assembly would exceed the all-pairs budget.

## Sketch-bound clearance plan

Clearance does not silently change `axm.design-sketch/v0.1`. Instead a companion contract is pinned to the exact `sketch_digest`:

`axm.design-clearance-plan/v0.1`

Supported requirements:

- `minimum-clearance` — actual rest-pose clearance must meet an explicit minimum in metres
- `contact` — requires resolved `TOUCHING`, not penetration
- `no-penetration` — passes on resolved `SEPARATED`/`TOUCHING`, fails on `PENETRATING`, holds on unresolved intersection

This lets a future planner say things like "wheel must stay at least 0.02 m from chassis" without rewriting the original blockout contract.

## Human / script / AI parity

Universal Creation operations:

- `measure-sticker-clearance-pair`
- `measure-sticker-assembly-clearances`
- `validate-clearance-plan`
- `compare-sketch-clearance`

The same underlying functions are exposed through `axm-sticker-create` JSON operations using underscore spellings.

## What this does not prove

This is rest-pose geometric evidence only. It does not prove:

- swept animation clearance
- continuous collision detection
- contact response / friction
- rigid-body or soft-body physics
- structural strength
- manufacturability
- gameplay correctness
- aesthetic quality
- engine import/runtime acceptance
- penetration depth

Those require separate evidence layers.

## Intended next use

The immediate consumer is a bounded autonomous workshop planner experiment:

1. choose explicit candidate stickers;
2. assemble a proposal;
3. measure placement, dimensions, and pair clearances;
4. reject or hold geometrically bad proposals;
5. keep acceptable modules as reusable stickers;
6. multiply useful verified families without confusing multiplication with quality proof.
