# AXM Asset Atom Fabric v0.1

The Asset Atom Fabric makes a reusable visual asset an inspectable dependency graph rather than one opaque file:

`asset package -> roots -> exact atom references -> deterministic instance selection`

The closed package schema is `axm.asset-atom-package/v0.1`. The compiled selection schema is `axm.asset-instance/v0.1`. Installed packages live in `asset-packages/` and resolve only by exact `id@version` reference.

## Audit result

Before this fabric, AXM already had useful visual machinery: Paintgun separated SVG shape/material/color/light/shade/skin channels, Chameleon retained richer PBR-style material truth, Vector Cells provided hierarchical reusable cells and scale-bounded representations, and simulation carried deterministic state. Those pieces did not form one versioned reusable asset contract.

| Requested layer | Earlier real coverage | Asset Atom v0.1 contract | Runtime proof today |
|---|---|---|---|
| Shape | Paintgun 2D shapes; Vector Cells; external concepts in anatomy | `shape`: 2D/3D primitive, vector, mesh, sprite, or impostor descriptor with bounds | SVG shapes render through Paintgun; external mesh/sprite bytes are not rendered here |
| Reusable parts | Vector Cell hierarchy | `part`: shape, material, children, collision, transform, tags | Dependency graph is validated; no 3D assembly runtime is executed |
| Texture maps | No package-level texture bundle | `texture`: channel, resource, UV set, tiling, offset, strength | Resource references are recorded, not fetched or sampled |
| Material channels | Paintgun scalar surface inputs; Chameleon rich material descriptors | `material`: scalar/color channels plus texture, shader, palette, gradient, mask, and overlay bindings | Descriptor graph compiles; no new physical renderer is claimed |
| Palette | Colors existed per visual thought | `palette`: named roles with deterministic per-instance overrides | Overrides are resolved and hashed |
| Gradient | Paintgun skin gradients | `gradient`: strict ordered stops, color space, angle, optional palette roles | Descriptor resolution only outside Paintgun's current SVG grammar |
| Masks | Registry definition only | `mask`: texture component, meaning, threshold, inversion | Validated descriptor only |
| Detail overlays | No reusable package contract | `overlay`: source, optional mask, blend, opacity, order, named states | Layer instructions are not composited by this capability |
| Shader instructions | Chameleon material graph retained richer truth | `shader`: closed model names, parameters, animated parameter names, optional runtime source descriptor | Shader code is never executed |
| Animation | Vector morphs and simulation state existed | `animation`: duration, looping, target tracks, interpolation, strictly ordered keyframes | Clip selection is deterministic; playback is not executed |
| State variants | Simulation and Chameleon state existed | `state`: activated/deactivated atoms and deterministic override objects | Exact state is selected; host application remains future work |
| Behavior | No reusable visual-asset behavior contract | `behavior`: target, trigger, optional animation and state transition, conditions | Wiring is validated; event runtime is not executed |
| LOD | Vector Cells selected scale-bounded representations | `lod`: continuous non-overlapping distance ranges from zero to infinity | Exact distance selection is executed |
| Collision | Registry definition only | `collision`: simplified shape, dimensions, layers, trigger flag, optional source shape | No collision or physics simulation is run |
| Sockets / anchors | No asset-package contract | `socket`: owner part, name, transform, accepted tags, required flag | Attachment compatibility is described, not instantiated in 3D |
| Metadata | Broad registry metadata existed | `metadata`: name, category, dimensions, era, factions, cost, rarity, technology, tags | Closed deterministic JSON is validated |

The result fills the composition-contract gap. It deliberately does not pretend that descriptor completeness equals rendered, animated, or gameplay-tested completeness.

## Exact atom rule

Every atom has five fields:

```json
{
  "id": "armor-material",
  "kind": "material",
  "purpose": "Complete reusable armor surface descriptor.",
  "uses": ["armor-base-texture", "armor-shader"],
  "payload": {}
}
```

`uses` must exactly equal every direct atom reference inferred from the kind-specific payload. Missing edges, extra edges, unresolved IDs, wrong target kinds, and dependency cycles fail validation. Unknown package, atom, payload, and nested fields also fail closed.

This makes a grammar such as the following inspectable:

`Tank -> LOD -> hull part -> turret part -> weapon socket -> shape/material -> textures/palette/mask/overlay/shader -> state/animation/behavior`

## Deterministic compilation

Compilation validates the complete package and resolves:

- one representation for every LOD group at the supplied observation distance;
- an optional exact state atom;
- an optional exact animation atom;
- palette overrides restricted to declared palette roles;
- ordered dependencies and socket descriptors;
- a package digest over normalized source truth;
- an instance digest over the complete resolved selection.

The same normalized package and inputs produce the same digests. Changing a palette, state, animation, or distance changes the instance without rewriting the source package.

## Installed demonstrator

`axm.example.modular-tank@1.0.0` contains 26 atoms and exercises all 16 kinds. It selects:

- `hull-high-part` from 0 through 25 distance units;
- `hull-medium-part` from 25 through 100;
- `hull-low-part` from 100 onward.

Its `asset://` mesh and texture URIs are intentionally declared references, not bundled media. The example proves schema coverage, dependency validation, deterministic selection, and materialization—not that those media bytes exist or that a tank was rendered.

Inspect it directly:

```bash
PYTHONPATH=src python -m axm_uc assets
PYTHONPATH=src python -m axm_uc assets --ref axm.example.modular-tank@1.0.0
PYTHONPATH=src python -m axm_uc create examples/requests/compile_modular_tank_asset.json
PYTHONPATH=src python -m axm_uc create examples/requests/materialize_modular_tank_asset.json
```

Materialization publishes exactly `asset.package.json` and `asset.instance.json` through the ordinary validated project boundary.

## Truth boundary

The v0.1 capability validates and compiles renderer-neutral descriptors. It does not:

- fetch or verify external resource bytes, even when a digest is declared;
- execute shader source;
- play animation or run behavior transitions;
- perform collision or physics simulation;
- render 3D meshes, impostors, textures, masks, or overlays;
- prove artistic quality, socket fit in a host engine, or gameplay behavior.

Those are separate future runtime capabilities. Keeping them separate is what lets this schema be useful now without overstating what AXM can physically execute.
