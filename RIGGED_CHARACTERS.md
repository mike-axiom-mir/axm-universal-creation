# Original rigged characters: AXM OOPS

OOPS (Overconfident Onboard Patch Specialist) is an original comic repair
courier built from authored geometry. The adapter adds a reusable character
builder, rigid mechanical skinning, animation export, and independent import
checks to the machine. It does not claim exhaustive similarity clearance or
plug-and-play compatibility with every future game engine.

## Create a new version

With `PYTHONPATH` set to `src`, from the machine root:

```text
python -m axm_uc.visual_assets_cli character-catalog
python -m axm_uc.visual_assets_cli character-forge examples/requests/forge_oops_character.json creations/oops-v1
python -m axm_uc.visual_assets_cli character-inspect creations/oops-v1/AXM_OOPS_LOD0.glb
```

The forge refuses existing output directories. Use `--blender` for an existing
runtime or let the machine resolve/provision its managed runtime. Optional
`--state-root` selects the machine containing the source tools and learning
profile. Requests support `render_resolution` (256–2048), `detail_pass` (1, 2, or 3),
`texture_resolution` (1024, 2048, or 4096 for detail 3), `no_render`, and
`auto_provision_runtime`, and `verify_roundtrip` (boolean, default false).
`examples/requests/forge_oops_hero.json` enables automatic independent round-trip
verification and selects the
crafted detail-3 profile with a 4K unique texture atlas. Profiles 1 and 2 retain
the original geometry and shared-color atlas workflow.

The bridge exposes `character-catalog`, `character-forge` (`request`, explicit
`path`, optional `blender` and `timeout_seconds`), and `character-inspect` (`path`).

## Outputs and truth boundaries

- One skeleton (32 bones in profiles 1/2; 37 in profile 3), one skinned mesh,
  one PBR atlas material.
- Three independently exportable GLB LODs, each with all four motion clips.
- All-clips character FBX plus individual skeleton-only FBX animation takes.
- Editable Blender source with packed images and original actions.
- A separate coarse collision box, not an automatically configured character controller.
- Four-angle PNG proof, manifests, and structural receipts.

The clips are Idle, Walk_InPlace, Wave, and Oops_Recover. The walk is in place;
world movement belongs to the game. Mechanical pieces have rigid bone weights,
not soft-tissue skinning. The hand-grip sockets, antenna, eyes, brows, hatch, and
spool remain independently addressable bones. This is a custom rig, not a
preconfigured humanoid-retarget skeleton.

The original large-mech AAA gates are deliberately not reused as a definition
of a good stylized character: extra polygons or materials do not establish
character quality. This adapter reports explicit structure/playback/visual
boundaries rather than calling the result AAA.

## Independent verification and motion preview

```text
blender --background --factory-startup --python-exit-code 1 --python tools/blender/verify_rigged_character.py -- --directory creations/oops-v1
blender --background --factory-startup --python-exit-code 1 --python tools/blender/render_character_preview.py -- --glb creations/oops-v1/AXM_OOPS_LOD0.glb --output creations/oops-motion-frames --clip Wave
```

The verifier reimports each GLB and FBX, checks normalized weights, bones,
meter-scale bounds, grounded rest pose, sampled walking sole contact, sampled deformation, and closed clip
endpoints. It also checks the separate FBX takes when present. Preview frames
come from a fresh import of the exported GLB, not from an unexported source.
The importer creates a custom bone-shape Icosphere: the verifier recognizes
that actual helper relationship instead of counting it as character geometry.

## Learning from use

Reviews use the existing `3d-review` operation with context
`3d/axm-oops/rigged-v1`. The request for each new version includes the current
exact-context observations. The generator does not pretend prose constraints
automatically remodel geometry: relevant source changes still must be authored,
tested and re-reviewed. This delivery improved the shared builder from actual
surface-normal, seam-attachment, gesture-clearance, and walking sole-contact observations.

Nothing in this path requires GitHub publication. All character creation and
verification can remain local.

## Crafted character profile

Detail 3 replaces primitive head/boot/hatch massing with section-lofted surfaces,
adds articulated distal fingers and a ground attachment socket, and projects
densely sampled service seams onto the evaluated shell. Toe markings project
onto their actual curved panels. The distinctive asymmetric optics, ceramic
pear body, coral hatch, teal magnetic boots, and repair flag remain OOPS's identity.

`tools/blender/axm_character_surfaces.py` is the reusable surface-baking module.
It unwraps unique islands and bakes authored paint variation, curvature wear,
localized toe abrasion, roughness, metallic, local AO, and micrograin normals.
The final GLB uses standard packed ORM, tangent-space normal maps, and explicit
tangents; no procedural Blender shader is required at runtime. Source shaders
are code-owned and reproducible. This is not high-poly sculpt-to-low-poly baking.
The atlas is shared across LODs; project-specific texture compression/streaming
and lightmap setup remain engine work.

The triangle basis is fixed before baking. Tangent generation is an explicit
builder check; crafted exports missing any required PBR map or tangents report
`SURFACE_STRUCTURE_FAILED`. Requested importer checks run inside the same build
time budget and save the verifier's hash and report hash in the receipt. Passing
them returns `STRUCTURE_AND_PLAYBACK_CHECKED_VISUAL_REVIEW_REQUIRED`, never an
automatic visual or AAA acceptance.

The crafted walk uses analytic two-link leg poses and level soles, keyed every
frame. Its 0.15 m stance travel corresponds to 0.28125 m/s forward controller
motion. The verifier measures sole height and stance displacement at every
exported walk frame, in all three GLBs and the combined FBX. FBX import can infer
bone lengths and connect a single translating child to its parent, ignoring
that child's location animation; the ground socket makes the Root layout
unambiguous and the verifier checks unmodified imports. Individual animation
FBXs must all exist and match the manifest's bone names.

## Local real-time inspection

```text
python tools/serve_character_inspector.py creations/oops-hero --port 8769
```

Open `http://127.0.0.1:8769/`. The inspector loads actual GLBs with Three.js,
supports animation playback/scrubbing, bind pose, three LODs, neutral/studio
lighting, orbit controls, wireframe, and skeleton display. The server only serves
the inspector and the three selected GLBs, not arbitrary workspace files. It
binds to loopback only. Three.js 0.180.0 loads from jsDelivr; model files remain
local. An internet connection is needed for that runtime unless cached.

Playback in this renderer is additional evidence, not Unity/Unreal/Godot gameplay
certification. No combination of polygon count, texture resolution, export tests,
or this inspector automatically marks a character AAA. Final character animation,
camera distance, lighting, controller, platform budgets, and art-direction approval
need the actual game context.
