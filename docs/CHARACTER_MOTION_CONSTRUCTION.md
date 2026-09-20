# Retained character motion construction

This extends the whole-character route from static form to an explicit skeleton,
skin and clips. It preserves the current freeform compiler, material intent,
character semantics and source-first publication. No Blender or model is needed.

## Invoke

`PYTHONPATH=src python -m axm_uc create examples/character-motion/bonsai-wave.json`

The existing `character-recipe-asset` and `whole-character-asset` handles accept
motion; `animated-character-recipe-asset` makes that intent discoverable. Static
recipes keep their prior path. The new alias does not invent animation if omitted.

The optional recipe `rig` uses `axm.character-rig/v0.1`:

- `joints`: parent-first rows with unique `id`, `parent` (null for the single root)
  and parent-local `translation`. Rest orientation and scale are identity.
- `bindings`: exactly one binding for every compiled form part. Either `joint`
  for rigid binding, `weights` with one named-joint weight map per compiled vertex,
  or `axis_blend` with `from`, `to`, `axis` (0/1/2) and increasing `range`.
- Explicit weights allow up to four influences, must be nonnegative and sum to
  one; malformed weights are refused. Axis blend deterministically clamps a
  construction-space coordinate into a two-joint linear weight field. It is a
  reusable control, not anatomical automatic weighting.

Optional `animation` is a list of named clips. Each has `tracks` with `joint`,
`path` (translation or rotation), `times`, `values`, and optional `interpolation`
(LINEAR or STEP). Rotation uses unit xyzw quaternions. Translation keys are
absolute parent-local positions, not deltas. Times start at zero and strictly
increase; no timing, loop or gait is invented. Existing pose playback supports
explicit looping and blending.

The compiler emits standard glTF skins, inverse bind matrices, JOINTS_0,
WEIGHTS_0, joint hierarchy, animation samplers and channels. Static geometry is
validated by UC's existing encoder before motion is added. The independent
existing GamePoseAsset decoder then checks the final bytes and evaluates rest
pose and authored key transforms. Numerical tests compare deformed positions
with analytic rotation and weighted translation, not the encoder's own answer.

Construction sidecars retain the exact form, rig, weights/weight field, clips,
material intent and normalized motion. Replay creates byte-identical GLBs in the
tested environment. Failed source-sidecar writes restore previous GLB and source
bytes. This is process-level rollback, not a crash-atomic multi-file transaction.
No automatic library admission or capability growth is claimed merely by export.

## Evidence procedure

`PYTHONPATH=src python -m unittest tests.test_character_motion tests.test_form_character_recipe -v`

`PYTHONPATH=src python tools/character_motion_demo.py /tmp/uc-motion-demo --plot`

The demo creates two differently shaped freeform bodies with the identical rig,
axis-blend recipe and clip. It decodes the resulting GLBs and optionally plots
actual vertex samples at three times. Matplotlib is optional for this diagnostic
only, never a runtime dependency. This proves deformation/reuse, not finished
character appearance or target-engine compatibility.

## Boundaries

The explicit route does not infer bone placement, bone rest rotations, animated
scale, retargeting, corrective shapes, cloth or face solving. The optional
[body-fitted performance route](CHARACTER_PERFORMANCE.md) now adds declared
landmark fitting, segment-distance skin fields and sampled two-bone reach/walk
with stationary support targets at authored samples.
Explicit vertex arrays must be rebound if topology changes; axis fields regenerate
from the new geometry. Existing character sockets/clothing regions remain retained
metadata, not animated socket or garment-fit proof. Material-response HOLDs remain
unchanged. Pose sampling checks positions; it does not validate shaded normals.
Topology, collision and deformation quality during arbitrary motion remain separate
checks. Source recipes remain authoritative; no export replaces them.

## Body-aware performance: delivered slice and remaining work

The first connected slice below is now implemented in `character_performance.py`:
body-relative landmarks, regenerated segment weights, bend limits, reach targets
and walk support phases. See [its contract and evidence procedure](CHARACTER_PERFORMANCE.md).
Influence masks, corrective deformation, expression/response integration and
runtime contact repair below remain future work.

The current main already contains generic form patterns, character semantics,
material responses, Creative Hands skeleton/skin/pose tools, two-bone solve math,
and GLB pose evaluation. The remaining high-value work is making those tools
cooperate around a reusable body and intended performance.

The larger direction remains:

1. **Body-family rig recipes.** Landmark and joint relationships expressed against
   named form parts and dimensions. Fit the same biped, quadruped or branching rig
   recipe to different proportions. Preserve fit controls and report missing
   landmarks rather than assuming humanoid anatomy.
2. **Deformation construction.** Segment-distance weight fields, influence masks,
   explicit joint limits and corrective shapes. Keep material seams and attachment
   regions stable. Validate bent poses, not only bind pose.
3. **Performance recipes.** Idle/reach/walk actions with phase, support contacts,
   root travel, targets and explicit pole/axis conventions. Connect existing IK
   solve math to declared rigs. Retarget by body relationships, not bone-name luck.
4. **Expression and response.** Layer face/secondary motion without changing body
   identity. Bind retained material response to a real renderer; preserve unsupported
   response behavior as an explicit limitation instead of flattening the source.
5. **Observe, repair, retain.** Render turntables and motion; measure contact slip,
   joint limits, mesh intersections and attachment drift; inspect appearance.
   Retain accepted rig/weight/motion recipes through the existing creator-growth
   machinery, deduplicating structural methods separately from appearance variants.

Acceptance demonstration: two substantially different bodies use the same retained
rig/performance family to reach and walk. Change a limb proportion and regenerate
without manually rewriting skeleton, weights or keys. Export, reimport and sample
both in an independent host; verify contact and attachment behavior. Demonstrate
that a third construction can retrieve the accepted method, while a rejected
candidate leaves the reusable library unchanged.

This should grow through actual requested body families. Universal anatomical
inference or guaranteed aesthetic quality is not a prerequisite or a promise.
