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
| graphic-toon | Three albedo value bands within the source field's range, flat tangent normals and broad roughness |

These are **surface finishes**, not complete art styles. In particular,
graphic-toon is not a cel-lighting shader. Lighting, silhouette, shape hierarchy,
animation and target-engine integration are separate pending capabilities.
Surface fields are authored approximations, not scans or measured materials.
No mesh-aware wear or seamless texture repetition is claimed.

```sh
axm-assets game-material-catalog
axm-assets game-material painted-metal out/comic-paint --finish comic-salvage --size 128 --seed 471
axm-assets game-material carved-wood out/painted-wood --finish painted-adventure --color 157 100 48
axm-assets game-material painted-metal out/worn --finish comic-salvage --layered-wear .7 --protect .3 .3 .7 .7
```

Each publication includes PNG base color, normal, AO, roughness, height and ORM
maps, plus a manifest with parameters, color spaces and file digests. Woven
fabric also retains its thickness map. ORM channels are occlusion, roughness,
metallic. Finish stylization never changes AO or conductivity. The opt-in
removable-coat layer can expose a separately authored substrate and therefore
changes correlated albedo, roughness, conductivity and paint-edge normals while
retaining proposal/protection/exposure/coat masks. Height remains an
authoring proxy; rebuilding normals from it replaces the selected normal finish.
Normal orientation for existing donors is tangent -Y; new families use tangent
+Y. The opt-in Blender adapter now corrects inherited direction in packed
derivatives, preserving original source maps. Generated files are not silently
accepted as engine-ready merely because their PNG structure passes.

Python callers can compose `game_material_fields`, `apply_finish`, or
`game_material_request`. The latter uses the existing mixed-media-project
machine protocol; the CLI uses the same transactional publisher. No overwrite
flag is added. Sizes are bounded to 16–512 and no new dependencies are required.

## Next priorities

Choose the next useful unoccupied step after reading current main and PRs.
Dependencies and observed failures may change the order. Finish and repair a
bounded change before starting another; no quota of new files or assets.

1. **Completed:** connect surface fields to the opt-in Blender adapter and
   independently inspect actual GLBs, data color spaces and normal direction.
2. **Completed:** controllable layered paint, exposed-metal response, roughness
   variation and protected readable regions, with attributed mask sources.
3. **Completed:** reusable playful form controls: taper, squash, oversized
   functional parts, asymmetry and explicit large/medium/small hierarchy, with
   protected contact/socket coordinates and canonical source retained.
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

### Expressive form pass — 2026-09-13

- Completed renderer-neutral `game_form_styles.py` and `axm-assets game-form`.
  Four opt-in profiles now alter actual silhouette geometry using coordinated
  squash, taper, functional/armor exaggeration, hierarchy scaling and seeded
  asymmetry. `realistic` remains an exact geometry identity. Every component
  requires an explicit semantic role; unclassified components fail closed.
- Canonical source is embedded unchanged beside the realization. Named contact
  and socket points fade displacement to exact zero and receive before/after
  drift receipts. This protects declared coordinates, not entire contact patches,
  rig deformation, collisions or articulation clearance.
- Actual verification: **8 focused tests pass** for identity, immutability,
  geometry-not-color changes, hierarchy, functional exaggeration, deterministic
  asymmetry, exact anchors, CLI publishing/overwrite refusal and malformed input.
  Blender 4.3 exported a neutral/comic courier comparison to GLB, reopened the
  editable `.blend`, freshly imported the GLB, and checked all 44 mesh bounds
  against renderer-neutral geometry (maximum error 0.000000222 m). Nine declared
  anchors stayed exact; source/re-import still MAE was 0.0.
- Visual repair: the first render cropped the source wrench. Wider framing fixed
  it; a second render showed the explanatory caption fighting the wheel contacts,
  so the caption was removed. Final still visibly shows larger head/wrench/wheels,
  a squashed/tapered chassis, reduced badge detail and controlled imbalance.
- Evidence: `tools/blender/game_form_roundtrip.py`,
  `docs/GAME_FORM_STYLES.md`, and
  `docs/evidence/game-form-roundtrip-2026-09-13.json`. The pinned theme-park
  cartoon/fantasy source was reviewed for coordinated form ideas; no donor code
  or park runtime was copied.
- Limits: static comparison specimen, not a finished game asset. No rig,
  animation, collision, LOD, UV, target-engine/game-distance/performance or
  perceptual style acceptance. Optional Draco is unavailable and unused.
- **Next useful step: priority 4**, portable graphic/painterly realization that
  survives export, with target-engine-only shader features stated explicitly.
- Active lane: `codex/rts-reference-foundry`, based on merged PR #62/main
  `2243cbb`; unrelated PR #54 remains outside this pass. Current-head checks are
  required before merge; final GitHub state is authoritative.
- Roots: Truth separates point/bounds/render evidence from artistic or runtime
  acceptance; Agency keeps profiles optional and caller roles explicit;
  Continuity embeds immutable canonical source; Wisdom repaired visible framing
  and hierarchy presentation before publication.

### Layered wear pass — 2026-09-13

- Completed opt-in `WearLayer`, deterministic UV chip/scratch proposals,
  caller-supplied mask composition, normalized protected rectangles and CLI
  controls. Protection is applied as an exact veto after proposed damage.
  Runtime base color is blended in linear light; roughness, metallic response and
  paint-edge normals change together. Original finish maps and authoring height
  remain unchanged; proposal, protection, actual exposure and remaining coat are
  retained as separate maps with declared sources in the manifest.
- Actual local verification: **26 focused tests pass** across all six families ×
  four finishes, exact protected-pixel invariants, source immutability, correlated
  ORM, deterministic variation, normal convention, mask/source validation, CLI
  publication and Blender bundle acceptance. Full repository checks are still
  required at the actual proposed head.
- Real Blender 4.3 evidence: `tools/blender/layered_wear_roundtrip.py` built a
  three-panel specimen, exported actual GLB, independently matched its embedded
  runtime textures, reopened nine packed images from editable `.blend`, re-imported
  the GLB into an empty scene and rendered it. Source maps stayed byte-identical;
  protected pixels had zero exposure; source/re-import render MAE was 0.002662.
  Evidence: `docs/evidence/layered-wear-roundtrip-2026-09-13.json` and
  `docs/GAME_MATERIAL_BLENDER.md`. Deliverable: `AXM-Layered-Wear-Proof.zip` plus
  `AXM-Layered-Wear.png`.
- Visual repair: the first specimen cropped two panels and smeared UV masks; a
  wider camera and explicit front-planar UVs fixed both. A second render exposed
  implausibly deep paint-edge normals; calibrated thickness-scale relief fixed
  the false gouge while preserving exposed-metal readability. Final source and
  re-imported stills visibly show the same wear proposal interrupted around the
  protected M. This is visible evidence for this bounded specimen only.
- Limits: static material specimen, not a complete game asset, animation, LOD,
  performance or target-engine acceptance. Built-in wear is UV procedural, not
  curvature/mesh derived. Caller source labels are provenance statements, not
  independently proven authorship. The proof's analytic UV mask and unwrap are
  authored specifically for inspection; seamless tiling is not claimed.
- **Next useful step: priority 3**, reusable playful form controls (taper,
  squash, functional exaggeration, asymmetry and detail hierarchy) while
  preserving rig/contact invariants. A later geometry adapter can provide actual
  mesh-baked wear masks without conflating them with this procedural proposal.
- Active branch: `codex/rts-reference-foundry`, based on merged PR #61/main
  `c20bcc4`; unrelated open PR #54 remains outside this pass. Require current-head
  checks before merge; final GitHub state is authoritative.
- Roots: Truth preserves mask source and evidence boundaries; Agency keeps the
  layer optional/offline and prevents damage proposals overriding authored
  protection; Continuity retains canonical inputs and editable masks; Wisdom
  repaired visible UV/framing/relief faults before publishing.

### Material realization pass — 2026-09-13

- Completed `src/axm_uc/game_material_bridge.py`: validated bounded UC bundles,
  packed editable Blender PBR materials, explicit glTF AO, correct ORM/data color
  spaces, tangent +Y derivative normals. Existing realistic/product generators
  remain untouched; updated manifest direction is metadata, not a field rewrite.
- Actual local verification: **17 tests pass** (11 prior + 6 bridge tests), source
  compilation, and two-process Blender 4.3 GLB export/re-import of all **24**
  family/finish combinations. Every embedded base/ORM/normal pixel matches the
  expected source or explicit Y-flipped derivative exactly. Reopened `.blend`
  contains 72 packed runtime images; original bundle bytes remain unchanged.
- Evidence: `tools/blender/game_material_roundtrip.py`,
  `docs/GAME_MATERIAL_BLENDER.md`, and
  `docs/evidence/game-material-roundtrip-2026-09-13.json`. Deliverable:
  `AXM-Material-Realization-Proof.zip` (actual GLB, editable Blender scene, original
  maps, before/after renders and verification receipt); preview
  `AXM-Material-Realization.png`.
- Visual inspection found pole-distorted cloth/wood and cramped labels in the
  first proof. Front-planar UVs and label spacing repaired those presentation
  faults. Source and re-import stills visibly retain the same materials; measured
  mean absolute RGB-byte difference is 0.000069 across this pair. This does not
  establish target-engine appearance or full game-style quality. The graphic
  finish stays PBR, not a cel shader; some finish differences remain subtle.
- Limits: static material proof only, not a new character/animated asset. No
  engine/gameplay/performance/LOD/animation/deformation or mesh-wear acceptance.
  AO is an export socket, not Blender preview darkening. Optional Draco was
  unavailable (not requested); shared ORM/AO sampler warning was checked against
  matching settings and actual GLB wrapping. Blender runtime recovered using
  cached Python 3.11/bpy 4.3 with NumPy 1.26.4, not UC's Windows provisioner.
- That pass's priority 2 is completed above. Continue with priority 3 form
  controls; retain both real export tests and do not duplicate this layer work.
- Active branch: `codex/rts-reference-foundry`, based on `bf607a5`; unrelated open
  PR #54 is outside this pass. Require current-head checks before merging this
  change; the final GitHub PR state is authoritative for merge completion.
- Roots: Truth distinguishes map/export/render evidence from game acceptance;
  Agency keeps this opt-in and free of remote/paid dependencies; Continuity keeps
  original maps, manifests and rich editable source; Wisdom repaired visible
  presentation errors and preserved uncertainty rather than claiming full style.

### Earlier bootstrap

- Bootstrap: executable material families/finish composition and `axm-assets`
  commands implemented; this precedes the ten scheduled activations.
- Local verification: eleven tests pass, covering all 24 family/finish combinations,
  donor identity, source immutability, ORM consistency, bounded inputs, deterministic
  variation, normal lengths/direction, actual CLI publication and overwrite refusal.
  Added regressions protect dark-material structure, narrow grain and constant surfaces after
  an albedo comparison exposed grain loss with absolute 0–1 quantization.
- Applicable full-repository checks are required at the actual proposed GitHub head.
  Their live GitHub results, not this pre-publication note, establish merge readiness.
- Visual status: a six-family/four-finish albedo comparison exposed erased wood
  grain and speckled thresholds. The finish now smooths fine value noise while
  preserving strong edges, and bands
  within each source field's range. No shaded game asset or engine integration
  demonstrated here. Surface maps alone do not satisfy Mike's complete style goal.
- Bootstrap's next step (now completed above): Blender/export adapter plus a
  small rendered proof.
- Working lane: `codex/rts-reference-foundry`; continue an existing open PR when
  present and keep related fixes together. Prior trike PR #58 is already merged.
- Approval basis: Mike explicitly authorizes this bounded improvement campaign
  and its merges; evaluate against the four roots and relevant checks, preserving
  uncertainty. Do not leave sound changes waiting solely for Mike's confirmation.
