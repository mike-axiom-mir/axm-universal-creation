# Closed-Component Orientation Observer v0

`inspect_mesh_topology(..., include_closed_component_orientation=True)` adds an **opt-in, read-only** closed-component orientation report to the existing mesh-topology inspector.

The default call remains unchanged: when the option is false, the extra observer is not imported, no orientation-parity work is performed, and the historical topology report shape is preserved.

## Why this observer exists

Two independent AXM product families reached the same structural distinction:

- Building Geometry proved closed face-connected shell components and compared algebraic shell volume against the exact occupied-union volume without turning that into renderer policy.
- Object Geometry found an exact rigid source whose components were closed by edge incidence while local winding was inconsistent; its derived read-only candidate could make each rigid component coherent, but Materials/QA separately proved renderer front-face/culling behavior remains a receiving concern.

The reusable lesson is:

`EDGE CLOSURE != ORIENTABILITY != GLOBAL SIGNED ORIENTATION != RECEIVER FRONT-FACE POLICY`

Issue #199 records the shared placement proposal. Product-specific source repair, positive-volume adoption, material culling, target-host conversion and visual acceptance remain outside Universal Creation.

## Opt-in inputs

The existing topology inputs remain authoritative:

- `positions`
- `indices`
- `weld_tolerance`

The closed-orientation observer adds:

- `include_closed_component_orientation=True`
- `orientation_triangle_budget` — positive per-component triangle ceiling; default is the existing topology ceiling
- `orientation_volume_epsilon` — non-negative caller-unit-cubed threshold used only to label algebraic volume as `NEAR_ZERO`
- `orientation_frame_label` — non-empty caller-declared frame label
- `orientation_handedness` — `UNDECLARED`, `RIGHT_HANDED`, or `LEFT_HANDED`

The observer does not infer a coordinate convention that the caller did not declare.

## Per-component evidence

For each edge-connected valid-triangle component the report records:

- deterministic component index and exact source-triangle identity digest;
- triangle and edge counts;
- `CLOSED`, `OPEN`, or `NON_MANIFOLD` closure state;
- current shared-edge winding state for eligible closed components;
- `ORIENTABLE`, `NON_ORIENTABLE`, or `NOT_EVALUATED` orientability state;
- deterministic face-parity solution digest when orientable;
- diagnostic face-flip count and bounded triangle-index examples;
- current signed volume only when the exact input component is closed and already shared-edge coherent;
- coherent-candidate signed volume only after a valid parity solution;
- signed-volume state `POSITIVE`, `NEGATIVE`, `NEAR_ZERO`, or `NOT_EVALUATED`.

Signed volume is evaluated from the seam-welded representative coordinates already used by the topology observer, with numeric XYZ convention:

`sum(dot(p0, cross(p1, p2))) / 6`

A handedness-changing coordinate transform can invert that sign.

## Deterministic parity contract

For each shared two-face edge, the observer derives one XOR constraint:

- if both current faces traverse the canonical undirected edge in the **same** direction, exactly one of those faces must be diagnostically flipped;
- if the current directions already oppose, both faces must keep the same parity.

The lowest triangle index in each connected component is seeded with parity `0`, and neighbors are visited deterministically. A contradiction returns `NON_ORIENTABLE`; it does not invent a partial repair.

The seed choice makes one coherent candidate deterministic, but the global complement is equally valid. Therefore the observer deliberately **does not normalize the result to positive signed volume** and never calls positive volume `outward`.

## Bounded failure states

Orientability/sign evidence is not emitted as a partial verdict when:

- the source topology contains a tolerance-collapsed triangle;
- the component is open;
- the component is non-manifold by edge incidence;
- the component exceeds the declared orientation triangle budget.

A valid parity solution whose algebraic volume lies within `orientation_volume_epsilon` remains `ORIENTABLE`, but its sign is explicitly `NEAR_ZERO` rather than being promoted to a directional claim.

## Regression fixtures

The dedicated regression suite retains these distinctions:

- a coherent outward tetrahedron is closed/orientable and has positive algebraic volume in a declared right-handed XYZ fixture;
- globally reversing every tetrahedron face preserves closure and orientability while flipping signed-volume sign;
- reversing only one tetrahedron face creates shared-edge conflicts but remains orientable, yielding a deterministic one-face parity candidate without mutating input;
- a six-vertex / ten-face triangulation of the real projective plane is closed by two-face edge incidence but fails the parity constraints as `NON_ORIENTABLE`;
- an open quad is explicitly `NOT_EVALUATED`;
- a too-small per-component triangle budget emits no partial parity digest or volume verdict;
- a deliberately large volume epsilon yields `NEAR_ZERO` without relabelling orientability;
- an all-collapsed input makes the opt-in inspection incomplete;
- invalid orientation-only options fail closed when the observer is requested while remaining dormant for historical default calls.

The projective-plane fixture is an indexed-complex topology negative only. Its finite coordinates are not a self-intersection or physical-embedding claim.

## Truth boundary

This observer does **not**:

- rewrite source indices or vertex positions;
- authorize winding repair or source adoption;
- choose the global parity complement;
- equate positive signed volume with semantic or renderer-facing `outward`;
- determine target-host front-face/culling conversion;
- rewrite normals or tangents;
- prove geometric vertex-manifoldness;
- prove self-intersection freedom;
- certify physical enclosed volume, watertight manufacturing, collision, physics or gameplay suitability;
- prove visual quality, production readiness, game readiness or mastery.

Renderer-facing orientation remains a Technical Art / Materials receiving responsibility. Product adoption remains with the product owner. Historical product PASS states do not transfer into this shared observer; every product consumer must pin an exact merged UC identity and rerun its own receiving evidence.

## Provenance and reuse boundary

Shared placement was proposed only after independent Building and Object evidence plus a third reuse signal from Object Procedural work. Universal Creation implements only the neutral read-only observation pattern. It does not copy product source geometry or product-specific adoption rules.

`axm-create-me` remains coordination-only. Profession Fabric remains the procedure/provenance layer. Truth, Agency / non-domination, Continuity, and Wisdom before speed remain the merge gate.
