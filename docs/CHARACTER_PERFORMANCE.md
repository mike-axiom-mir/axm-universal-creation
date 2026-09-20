# Body-fitted character performance

UC now compiles declared landmarks, skin fields and performance targets into the
existing explicit skeleton/skin/clip route. One template can regenerate its joints,
weights and motion when the form body changes. Compilation uses only the Python
standard library and UC's existing two-bone locus solver.

## Use

```sh
PYTHONPATH=src python -m axm_uc create examples/character-motion/seedling-performance.json
PYTHONPATH=src python tools/character_performance_demo.py /tmp/uc-performance --plot
PYTHONPATH=src python -m unittest tests.test_character_performance -v
```

The request handle is `character-performance-asset`; existing character-recipe
handles also accept performance. As with the animated-character alias, the handle
does not invent a missing performance. The demo exports two differently
proportioned bodies using exactly the same template, replays construction, and
optionally draws actual decoded GLB vertices. Plotting alone needs matplotlib.
Use a fresh output directory; the demo refuses overwriting existing assets.

## Construction contract

Recipe `performance` is mutually exclusive with an explicit `rig` or `animation`.
Its schema is `axm.character-performance/v0.1`, with these required fields:

| Field | Meaning |
| --- | --- |
| `body_family` | Must match the character's declared body family. |
| `joints` | Parent-first `{id, parent, anchor}` rows; one root, at most 128 joints. |
| `bindings` | Exactly one skin binding for each named form part. |
| `clips` | One to eight named reach or walk recipes. |

An anchor is an explicit `[x,y,z]` point, or
`{part, fraction:[x,y,z], offset?:[x,y,z], offset_fraction?:[x,y,z]}`.
Fractions are in 0..1 of the named part's compiled, transformed axis-aligned bounds.
Offsets are construction-space metres; fractional offsets scale with those bounds.
Landmarks are declared controls, not anatomical inference. Parent-local translations
are derived from fitted world positions; rest rotations and scales remain identity.

Bindings accept the existing rigid `joint`, explicit vertex `weights`, or
`axis_blend` contracts. A generated field is:

```json
{"segment_weights": {
  "segments": [["hip", "knee"], ["knee", "ankle"]],
  "falloff": 4,
  "softness_m": 0.025,
  "max_influences": 2
}}
```

Each segment contributes to its **start joint** according to inverse distance to
the finite segment. Weights are sorted deterministically, truncated to the declared
one-to-four influences, and normalized. Defaults are falloff 2, softness .02 m,
four influences. Segments must be nonzero and have distinct influence joints.
These are geometric fields; they do not infer muscle structure, volume preservation
or material seams. They regenerate after topology changes; explicit vertex arrays
still require rebinding.

## Reach and walk

Every clip declares `name`, `kind`, `duration`, `samples`, and `chains`.
Duration is .01..120 seconds; 3..257 uniformly spaced samples are emitted.
Each chain declares three consecutive joint IDs and a construction-space `pole`
direction. Chains are disjoint and may share static ancestors, but cannot animate
one another's ancestors. Their joints must be below the skeleton root.

Optional chain controls are `keep_end_orientation` (default false) and
`max_bend_degrees` (greater than 0, at most 180, default 180; measured bend 0 means a straight limb). Enabling the former
counter-rotates the end joint to preserve its identity world orientation. The latter
limits bend at authored samples; it is not a full joint-limit model. Unreachable
targets, zero-length segments and ambiguous pole/endpoint configurations are refused.

- **Reach:** each chain has `targets:[{at,point},...]`. Phase `at` starts at 0,
  ends at 1, and strictly increases. Points use the same anchor contract. Targets
  interpolate linearly in construction space, independently of optional clip
  `root_translation`, which is the root's total travel over the clip.
- **Walk:** the clip declares `stride`, `lift`, `up_axis`, `forward_axis`, and
  `stance_fraction` (.5 to less than .9). Each chain declares `phase` in [0,1).
  The root travels one positive stride along the forward axis. During support the
  end target stays at one world point; swing advances to the next plant with
  smoothstep travel and a squared-sine lift. Up/forward are distinct positive axes
  0/1/2; Z-up is not hardcoded. The original end height defines each support plane.

The compiler generates LINEAR quaternion/translation tracks and preserves quaternion
sign continuity. Endpoints repeat relative pose after one stride, but the standard
clip player does not accumulate root travel when wrapping. A controller must do so
for continuous forward locomotion. Sampling between keys interpolates rotations;
it does not rerun IK and can introduce contact drift.

## Evidence and retention

The independent GLB pose decoder checks each exported end joint against its declared
sample target, with an absolute .0001 m tolerance. Publication exposes the maximum
error and verified target/contact sample counts. These are measured positions,
not proof that arbitrary feet touch a ground surface. The fixture additionally
checks whole rigid foot vertices remain level and on its ground plane during
support, and clear that plane during swing.

Source sidecars preserve the original performance template, exact body recipe,
fitted landmarks, generated weights, solved clips, target observations and the
decoded-output validation linked to the artifact's hash. The
tested replay is byte-identical in the same runtime. Every use can retain reusable
construction; export alone does not automatically admit a new library capability.
The existing creator-growth acceptance and semantic deduplication rules still apply.

## Next connected build

The highest-value continuation is a **contact and deformation controller** over
this retained body state:

1. Accumulate root travel and solve support targets at runtime; measure between-key
   slip rather than relying on dense baked samples.
2. Add joint-frame limits, attachment tracking and corrective deformation with
   bent-pose intersection/volume checks. Preserve explicit unsupported cases.
3. Bind observed failures to bounded controls: plant timing, pelvis height, stride,
   pole direction, influence masks and corrective shapes. Refit and compare results.
4. Retain accepted corrections as reusable body-family construction through the
   existing growth path, separately from recolors or one-off exported variants.

This release does not establish dynamic balance, ground/collision sensing, arbitrary
rig retargeting, facial expression, cloth, shaded-normal correctness or external
engine compatibility. The seedling is a technical construction fixture, not a
finished character-art claim.
