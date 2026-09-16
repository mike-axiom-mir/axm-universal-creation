# Mesh production and target observation

The product workflow can now execute automatic UV layout, mesh baking, a
physically lit target render, and sampled deformation checks. These are ordinary
UC capabilities owned by explicit profession stations. They can be invoked by
a human, a recipe or an AI through the same request surface.

## Runtime and source

The native runtime still requires only Python. UV packing, Cycles baking and
target rendering use an **optional local Blender** executable. Set `AXM_BLENDER`
to its absolute path, or put `blender` on `PATH`. The verified backend is Blender
4.3.2, Cycles CPU. Missing Blender produces an explicit error before publishing
an output. UC does not download or install it automatically.

Requests pass bounded JSON to a fixed worker with factory settings and automatic
script execution disabled. Inputs are native surface specifications or embedded
GLB; external image/buffer URIs and arbitrary `.blend` input are excluded.
Each station refuses existing outputs, preserves source, and independently
observes the published artifacts. Backend observers repeat the actual work,
including renders, against current source. Backend version/build and worker
source are retained with each report. Exact reproduction is scoped to that
runtime, not promised across Blender releases or machines.

## Capabilities

| Capability | Owner | Executes and checks |
| --- | --- | --- |
| `unwrap-surface-uv` | Technical artist | Smart UV Project, area-based scaling and axis-aligned island packing; independent triangle overlap, collapsed UV and pixel-padding checks |
| `bake-mesh-maps` | Technical artist | Cycles mesh AO; optional high-to-low tangent normal transfer with a bounded extrusion/distance contract and separate geometry-ray coverage |
| `validate-blender-target` | QA/playtest with graphics evidence | Fresh GLB imports, decoded images, native-versus-Blender geometry/pose comparison, Cycles environment/area-light reflection renders |
| `inspect-deformation` | Technical artist | Hierarchy/weights, authored keys and subdivisions, triangle collapse, excessive edge stretching, explicitly declared contact drift and loop discontinuity |
| `copy-animation-asset` | Technical artist | Byte-preserving copy of the supplied embedded rigged GLB into a new product draft |

The UV worker welds exact positions to find chart adjacency, then preserves the
original triangle corners, normals, colors and material assignments. It emits
one unique 0..1 atlas **per material**, with explicit base-level padding. Packing
uses bounding boxes for predictable bounded behavior. Native checks measure
actual triangles and island boundaries, rather than trusting the worker's label.
Re-layout of an already textured source is rejected: unwrap before binding, or
explicitly rebake its surface. This does not migrate an existing painted layout.

Baking requires a unique atlas. Bake size must match the source maps. AO is
multiplied into the packed ORM occlusion channel, leaving roughness/metallic and
the source material bundle intact. Without a high-detail source the existing
tangent normal stays intact. With `high_specification`, group ids must match;
the selected-to-active tangent +Y result explicitly **replaces** the generated
normal. Projection starts at `low_position + normal * cage_extrusion`, then
casts inward by `cage_extrusion + max_ray_distance`. Every covered texel must hit.
This separate check matters because a missed bake can look like a valid neutral
blue normal. Unhit projections hold downstream work. A failed report can still
be inspected; it does not authorize the next station.

Target lighting uses actual Cycles diffuse/glossy rays, a directional world
environment, three area sources, a contact floor, and AgX display rendering.
Fresh imports compare every selected pose's world bounds and triangle count
with UC's independent pose evaluator. Images must decode and renders must have
the requested dimensions, nonconstant output, and a nonempty object-index
coverage mask. An empty studio background cannot satisfy that last check.
Denoising is explicit and enabled by default; `denoise: false` retains the raw
sampled render. These measurements do not
replace a rendered visual review.

## Product requests

A `static-3d` request may add:

```json
{
  "production": {
    "uv": {"resolution": 256, "padding_px": 2, "angle_limit_degrees": 66},
    "bake": {"size": 256, "samples": 24, "margin_px": 2,
             "cage_extrusion": 0.02, "max_ray_distance": 0.1},
    "target": {"engine": "blender-cycles", "width": 800, "height": 600,
               "samples": 48, "environment_strength": 0.5, "denoise": true,
               "views": [{"yaw": 0.57, "elevation": 0.3},
                         {"yaw": -2.1, "elevation": 0.4}]}
  }
}
```

The sequence is brief/source -> unwrap/check -> generate/check materials ->
bind -> mesh bake/check -> geometry/density -> native previews -> actual target
import/render -> delivery record. UV and bake controls must agree with map size
and padding. The baked derivative is `baked/asset.glb`; the pre-bake assembly is
also retained. Each later station uses the selected derivative.

An `animated-3d` draft now accepts an **authored rigged GLB** through `asset`.
It copies the source, runs `production.deformation`, then optionally runs
`production.target`. Target views accept `clip` and `time_s` in addition to yaw
and elevation. It does not invent a rig or reskin an existing model.

Deformation policy defaults to four subdivisions per authored key interval,
minimum triangle area ratio 0.05 and maximum edge ratio 3. Supply `loop_clips`
and `maximum_loop_delta_m` for declared loops. Each `contacts` row names `clip`,
`mesh` (the instantiated primitive index), `vertex`, `start_s`, `end_s` and
`maximum_drift_m`. No contacts or loops are assumed when none are declared.
Measurements include all authored key times plus contact-window boundaries;
they are sampled evidence, not proof of every continuous extremum.

```sh
python tools/mesh_production_demo.py creations/mesh-production
```

The demo uses the actual crew workflow for a field case without authored UVs,
and for a closed, two-joint bend. It also tests a deliberately collapsed extreme.
`--quick` uses smaller real renders and maps for CI. Unit integration tests add
high-to-low projection and a deliberately undersized cage, report tampering,
source preservation, and missing-backend behavior.

## Boundaries

| Area | Still outside this implementation |
| --- | --- |
| UVs | UDIM, arbitrary atlas repacking with painted-texture preservation, seam editing, guaranteed padding at every mip level |
| Baking | Curvature/thickness maps, explicit cage meshes, arbitrary differently named high/low group pairing, automatic mesh-aware wear art direction |
| Materials/rendering | Universal MikkTSpace parity with UC's simpler native preview, authored decals, transparent material production, compressed texture delivery |
| Deformation | Morph/CUBICSPLINE support in the native evaluator, self-intersection, anatomical or artistic judgment, automatic rig authoring |
| Targets | Unity/Unreal/Godot integration, continuous gameplay/input/audio tests, actual device performance; the selected verified target is Blender/Cycles |
| Refinement | Dependency-aware partial rebuilds, automatic aesthetic acceptance or release |

The final product still has `released: false` and requires review. A target
check identifies the engine it actually ran. It cannot satisfy a different
engine's acceptance requirements by renaming its report.

## References

- [Khronos skinning tutorial](https://github.khronos.org/glTF-Tutorials/gltfTutorial/gltfTutorial_020_Skins.html): joint/weight/inverse-bind conventions used for independent pose comparisons.
- [Khronos PBR guide](https://www.khronos.org/gltf/pbr/): core color and material channel conventions.
- Blender's installed 4.3.2 operator RNA and actual execution were used to check UV, bake and render options. No third-party implementation code or artwork was copied.
