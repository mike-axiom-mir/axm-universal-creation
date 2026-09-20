# Freeform form, whole-character, and intent-routing convergence

This pass connects several pieces that previously existed beside one another without
pretending that one capability proves another.

## Geometry layers

UC now has three progressively richer source-first geometry levels:

1. `axm.procedural-3d/v0.1` — exact box/pyramid/cylinder primitives, or explicit
   `axm.surface-3d/v0.1` mesh groups supplied by the caller.
2. `axm.shape-recipe/v0.1` — MorphTile-inspired variables, loops, conditions,
   embedded definitions, per-use settings and position paint. Its current receiver
   still expands to box/pyramid/cylinder primitives and therefore keeps unsupported
   shape/rotation requests on HOLD.
3. `axm.form-pattern/v0.1` — generic deterministic surface construction from
   arbitrary declared profiles and paths. The first pattern vocabulary is
   `profile-extrude`, `loft`, `revolve`, and `tube`; each part supports
   translation, rotation and non-uniform scale and compiles into explicit surface
   vertices/normals/triangles.

The third level is not a fixed catalog of finished objects. A loft's sections, a
revolve's profile, an extrusion's outline, and a tube's path/radii are creation
data. They can therefore describe families of new forms while remaining inspectable.

This is still not unrestricted sculpting, arbitrary CSG, retopology or aesthetic
intelligence. Those remain separate capabilities/evidence.

## Whole static character recipe

`axm.character-recipe/v0.1` wraps a freeform body in character semantics:

- race id and body-family identity;
- semantic part roles;
- equipment/attachment sockets;
- clothing regions that may be race/body-family bound;
- material intent, including response-family intent even when the renderer binding
  is still unverified;
- the complete freeform body recipe and compiled geometry.

The output is one complete static GLB, not a pile of disconnected declarations.

Generic rigging and animation are still honest HOLDs. Existing OOPS/Chaos specialist
lanes prove that UC can produce rigged authored characters, but that does not yet
make one generic arbitrary-character rig/skin compiler. The whole-character route
will not silently borrow that claim.

## Source retention

The source-first 3D routes publish a sibling `.glb.source.json` by default. The
retained construction state is source authority; the GLB is a realization. Failed
sidecar publication rolls the GLB back so an end product is not silently separated
from its construction state.

## Intent routing

The direction router still derives claims from installed live manifests rather than
maintaining a hidden second capability registry.

A request that omits an internal `kind` may now execute one installed route only
when all of the following are true:

- the route is already `COMPATIBLE_AND_SUFFICIENT`;
- every required route input is present;
- there are no manifest contradictions;
- there are at least two semantic overlaps with the ordinary-language direction;
- exactly one live route has the best evidence-derived score.

A tie remains a HOLD. A multi-step production graph remains a plan until exact
bindings/inputs execute each step. This improves ordinary intent routing without
turning fuzzy language into silent authority.

## Materials

UC now has both the earlier rich PBR texture/material families and the material
response contract merged in PR #219. The response layer contains 13 families built
from eight behaviors including subsurface transport, sheen, anisotropy, clear coat,
micro-breakup, transmission, iridescence and wear layering.

Those response families are available as deterministic intent contracts. Active
response organs still report `HOLD_RENDERER_BINDING_NOT_TESTED` until a specific
renderer earns its own verification receipt. A character recipe can retain that
intent now without pretending the current static GLB has rendered the effect.

## Truth boundary

This convergence proves structural creation/routing/source retention only where the
tests and generated artifacts actually exercise it. It does not convert a green unit
suite into visual acceptance, generic rigging, universal clothing fit, target-engine
gameplay, or automatic CANON.
