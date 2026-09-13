# Game style growth

Mike's 2026-09-13 direction: retain the existing realistic/product-design
finish, and grow more distinctive, high-quality and fun game creation choices.
Realism is an option, not the default destination for every reference. Preserve
the comic salvage personality, readable silhouettes and rich editable source.
Color changes and higher polygon counts alone do not establish style quality.

The ten hourly activations are managed by the external ChatGPT task. This file
is a working checkpoint, not a scheduler, machine governance system, or promise
of ten completed assets. Do not extend the schedule from this file.

## Executable foundation

`src/axm_uc/game_material_styles.py` adds an opt-in portable material path.
The original Blender hero/companion/trike surfaces and donors are unchanged.

| Family | Surface source |
| --- | --- |
| painted-metal | Existing painted-metal donor fields |
| woven-fabric | Existing woven fabric donor fields, including thickness |
| rubber | Fine stipple, soft reflection and shallow relief |
| leather | Pores with correlated albedo, roughness and relief |
| ceramic | Restrained glaze variation and shallow surface detail |
| carved-wood | Bent grain and an authored knot field |

| Finish | What executes |
| --- | --- |
| realistic | Identity transformation of source fields |
| comic-salvage | Partially grouped albedo values, reduced normal detail and broader roughness |
| painted-adventure | Soft value grouping, directional procedural brush variation and restrained normals |
| graphic-toon | Three albedo value bands, flat tangent normals and broad roughness |

These are **surface finishes**, not complete art styles. In particular,
graphic-toon is not a cel-lighting shader. Lighting, silhouette, shape hierarchy,
animation and target-engine integration are separate pending capabilities.
Surface fields are authored approximations, not scans or measured materials.
No mesh-aware wear or seamless texture repetition is claimed.

```sh
axm-assets game-material-catalog
axm-assets game-material painted-metal out/comic-paint --finish comic-salvage --size 128 --seed 471
axm-assets game-material carved-wood out/painted-wood --finish painted-adventure --color 157 100 48
```

Each publication includes PNG base color, normal, AO, roughness, height and ORM
maps, plus a manifest with parameters, color spaces and file digests. Woven
fabric also retains its thickness map. ORM channels are occlusion, roughness,
metallic. Stylization never changes AO or conductivity. Height remains an
authoring proxy; rebuilding normals from it replaces the selected normal finish.
Normal orientation for existing donors is inherited and must be checked by a
renderer adapter; new families use tangent +Y. Generated files are not silently
accepted as engine-ready merely because their PNG structure passes.

Python callers can compose `game_material_fields`, `apply_finish`, or
`game_material_request`. The latter uses the existing mixed-media-project
machine protocol; the CLI uses the same transactional publisher. No overwrite
flag is added. Sizes are bounded to 16–512 and no new dependencies are required.

## Next priorities

Choose the next useful unoccupied step after reading current main and PRs.
Dependencies and observed failures may change the order. Finish and repair a
bounded change before starting another; no quota of new files or assets.

1. Connect the new surface fields to the Blender material adapter and independently
   inspect actual exported GLBs, including data color spaces and normal direction.
2. Add controllable layered paint, exposed-metal edges, roughness variation and
   protected readable regions; distinguish authored masks from mesh-derived wear.
3. Add reusable playful form controls: taper, squash, oversized functional parts,
   asymmetry, large/medium/small detail hierarchy. Preserve rig/contact invariants.
4. Build distinct graphic/painterly realization options that survive export;
   state exactly which shader features need a target-engine adapter or bake.
5. Improve expressive character/robot face shapes and stances with identity checks.
6. Expand animation composition for anticipation, acceleration, impact and settle.
7. Add reusable secondary motion for springs, cloth, antennae and carried props.
8. Improve contact, sockets, useful LOD selection and game-distance readability.
9. Exercise the combined capabilities on one memorable animated game asset,
   such as a mischievous salvage delivery bot, with editable source and real GLBs.
10. Repair the weakest demonstrated quality gap; verify and package a coherent
    result instead of maximizing output count.

Retain source, named rigs and clips. A render is evidence of appearance; a
structural test is evidence of structure; neither alone proves gameplay fit.
Inspect representative motion frames, contact, loop seams and re-imported
exports when those features change. Measure performance before making claims.

## Current checkpoint

- Bootstrap: executable material families/finish composition and `axm-assets`
  commands implemented; this precedes the ten scheduled activations.
- Local verification: eight tests pass, covering all 24 family/finish combinations,
  donor identity, source immutability, ORM consistency, bounded inputs, deterministic
  variation, normal lengths/direction, actual CLI publication and overwrite refusal.
- Applicable full-repository checks are required at the actual proposed GitHub head.
  Their live GitHub results, not this pre-publication note, establish merge readiness.
- Visual status: no shaded game asset or engine integration demonstrated by this
  change. Surface maps alone do not satisfy Mike's complete game-style goal.
- Next useful step: material-to-Blender/export adapter plus a small rendered proof.
- Working lane: `codex/rts-reference-foundry`; continue an existing open PR when
  present and keep related fixes together. Prior trike PR #58 is already merged.
- Approval basis: Mike explicitly authorizes this bounded improvement campaign
  and its merges; evaluate against the four roots and relevant checks, preserving
  uncertainty. Do not leave sound changes waiting solely for Mike's confirmation.
