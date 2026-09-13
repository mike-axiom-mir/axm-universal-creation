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
4. **Completed:** distinct graphic/painterly realizations that survive GLB
   export through final linear vertex colours and `KHR_materials_unlit`, with
   target-engine-only shader features stated explicitly.
5. **Completed:** explicit character/robot face expressions and hierarchical
   storytelling stances with protected rigid identity and eye-pivot checks.
6. **Completed:** deterministic animation composition for anticipation,
   acceleration, impact, recoil/counter-overshoot and settle, with sampled
   portable tracks, exact phase events and fresh-import loop/contact receipts.
7. **Completed:** reusable causal secondary motion for springs, short rigid
   cloth chains, antennae and carried props, with bounded response and exact
   authored loop closure.
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

### Secondary motion pass — 2026-09-13

- Completed `game_secondary_motion.py`, `axm-assets secondary-motion-compose`
  and its catalog. Four reusable classes derive per-frame local tracks from an
  explicit sampled primary channel: `coil-spring`, `antenna`, `cloth-tail` and
  `carried-prop`. Response frequency, damping, drive gain, causal frame lag,
  axis, direction and amplitude remain explicit rather than inferred.
- The primary composition and secondary request are embedded unchanged with
  SHA-256 identities. Missing/static drivers, duplicate outputs, zero axes,
  unsafe scale and unbounded samples fail closed. Receipts expose declared and
  observed lag, peak/limit, pre-closure residual and exact loop seam. Primary
  `settle` starts an authored cubic return to rest; this is not presented as a
  physical simulation.
- Actual verification: **9 new focused tests pass** for all four classes,
  deterministic composition, source immutability, identical sample clocks,
  causal chainable delays, quaternion normalization, positive scale, bounds,
  invalid/static drivers, transactional publication and CLI execution.
- Blender 4.3 proof: the same original Clockwork Smacker now has 11 bones and
  five secondary controls across a coil, antenna, two-panel cape and tool bag.
  It exports actual LOD0 (58,928 triangles) and LOD1 (28,284 triangles) GLBs,
  editable `.blend`, and the named 37-frame
  `Bell_Smack_Secondary_Followthrough` clip. A separate process imported both
  files and evaluated every secondary track at every sample: maximum local
  error `0.000000306`; maximum secondary world loop seam `0 m`.
- Visual repair: the first comparison silently rendered both rows with active
  curves, so identical pixels failed the evidence claim. Explicit curve muting
  fixed the comparison. Rear inspection then exposed two plain black cape
  backs; patched red, ivory and teal panels restored the salvage story. Final
  locked/enabled RMSE is 0.0248 at anticipation and 0.0638 at settle; the full
  silhouette remains framed. These stills prove visible sampled differences,
  not continuous playback.
- Evidence: `tools/blender/game_secondary_motion_roundtrip.py`,
  `docs/GAME_SECONDARY_MOTION.md`, and
  `docs/evidence/game-secondary-motion-roundtrip-2026-09-13.json`.
  Deliverable: `AXM-Secondary-Motion-Proof.zip` plus
  `AXM-Secondary-Motion.png`.
- Limits: rigid bone controls only. No soft cloth, collision/self-contact, rig
  inference, target-engine playback, state-machine/controller integration,
  audio sync, continuous perceptual acceptance or measured frame time.
- **Next useful step: priority 8**, improve contact/socket evidence, useful LOD
  selection and game-distance readability without conflating those gates.
- Active lane: `codex/rts-reference-foundry`, based on merged PR #66/main
  `6b68f09`; unrelated PR #54 remains outside this pass. Recheck current main,
  overlap and exact-head checks before merge; final GitHub state rules.
- Roots: Truth keeps rigid follow-through separate from cloth/engine claims;
  Agency requires explicit caller-owned drivers and profiles; Continuity embeds
  unchanged primary/source state and exact endpoints; Wisdom repaired invalid
  visual evidence and the exposed cape style defect before publication.

### Motion timing composition pass — 2026-09-13

- Completed `game_motion_timing.py`, `axm-assets motion-compose` and its
  catalog. Four opt-in profiles derive fully sampled local translation,
  quaternion and scale tracks through rest, anticipation, accelerated action,
  impact, recoil, counter, settle and complete. Geometry, materials and the
  realistic/product path remain unchanged.
- Canonical requests and SHA-256 identity stay embedded. Inputs are bounded;
  duplicate channels, invalid quaternions, negative/inverted scale and unsafe
  durations fail closed. Rotations use shortest-hemisphere normalized slerp.
  Receipts measure acceleration, declared impact endpoints, quaternion error
  and exact loop seams. The publisher refuses overwrite.
- Actual verification: **8 new focused tests pass** across deterministic
  profiles, phase quantization, per-frame portable samples, quaternion
  hemisphere equivalence, source immutability, validation, publication and
  CLI execution. Full repository checks remain required at the proposed head.
- Blender 4.3 proof: the original six-bone AXM Clockwork Smacker exports actual
  LOD0 (40,572 triangles) and LOD1 (19,473 triangles) GLBs, editable `.blend`
  and four named clips. A separate fresh process imported both GLBs, selected
  all eight exported clip instances, verified 37-frame ranges, measured a
  maximum bell marker gap of 0.000000137 m and a 0 m world loop seam.
- Visual repair: the first GLB showed no hammer swing and missed the bell by
  0.816 m. The exporter had evaluated quaternion curves while the pose channel
  was left in Euler mode; restoring the explicit mode made the hidden failure
  visible, then a local-bone-axis and scaled-target repair closed contact. The
  final imported-frame sheet visibly keeps the whole silhouette and separates
  weighty versus snappy anticipation/recoil on the same action endpoints.
- Evidence: `tools/blender/game_motion_timing_roundtrip.py`,
  `docs/GAME_MOTION_TIMING.md`, and
  `docs/evidence/game-motion-timing-roundtrip-2026-09-13.json`. Deliverable:
  `AXM-Motion-Timing-Proof.zip` plus `AXM-Motion-Timing.png`.
- Limits: local timing is not rig inference, secondary motion, IK/contact
  solving, transition/state-machine authoring, audio synchronization, target-
  engine playback, soft-deformation acceptance or frame-time performance. The
  contact receipt proves the two declared rig markers, not arbitrary surfaces.
- Donor boundary: `native_animation.py` and Apache-2.0 at Axm-game-assets
  `aaae29c8` were inspected for sampling/contact concepts; no donor source or
  mesh was copied. The capability and proof asset are independently authored.
- **Next useful step: priority 7**, reusable phase-lagged secondary motion for
  springs, cloth, antennae and carried props driven from these primary tracks.
- Active lane: `codex/rts-reference-foundry`, based on merged PR #65/main
  `f41d73a`; unrelated open PR #54 remains outside this pass. Recheck current
  main, overlap and exact-head checks before merge; final GitHub state rules.
- Roots: Truth separated timing, contact-marker, visual and engine claims;
  Agency keeps profiles explicit/offline and rig semantics caller-owned;
  Continuity retains exact sources and unchanged endpoints; Wisdom repaired an
  actual export-mode/contact failure before publishing instead of weakening the
  gate.

### Character expression and stance pass — 2026-09-13

- Completed `game_character_expression.py`, the transactional
  `axm-assets character-expression` publisher and catalog. Five expressions
  reshape declared eyes, brows and mouths around authored pivots. Four stances
  compose rigid body/head/arm/leg/prop transforms through an explicit acyclic
  parent tree. Neutral/neutral is an exact identity.
- Identity is caller-defined rather than guessed. Protected components cannot
  receive local face or stance changes; the gate verifies their radial geometry,
  pairwise pivot relationships and authored eye-pivot spacing. Canonical source,
  semantic controls and receipts remain embedded. Inverse-transpose normal
  transformation preserves authored shading through non-uniform face changes.
- Actual verification: **31 focused tests pass** across nine new expression
  tests plus form, render-style and native GLB regressions. Blender 4.3 exported
  and freshly imported four actual 33-primitive/2,302-triangle GLBs. Maximum
  decoded position error was 0.000000119 m; maximum protected identity error was
  0.000000010 m; the editable-source/re-import render MAE was 0.0.
- Visual repair: the first still visibly distinguished curious, mischief and
  alarmed faces and poses, but clipped the victory arm. A wider final camera
  retained every full silhouette. Static inspection then passed the bounded
  claim that all four expressions/stances are visibly distinct and the monocle
  ring/beak identity remains recognizable in this specimen.
- Evidence: `tools/blender/character_expression_roundtrip.py`,
  `docs/GAME_CHARACTER_EXPRESSION.md`, and
  `docs/evidence/character-expression-roundtrip-2026-09-13.json`. The proof is
  one original Patchwork Foreman and combines the existing portable painted
  realization after posing; no donor mesh or external character source was used.
- Limits: static geometry poses only—no skeleton, skin, clips, transitions,
  deformation, contact/collision, target-engine, game-distance or performance
  acceptance. Protected-pivot metrics do not prove general perceptual identity.
- **Next useful step: priority 6**, reusable motion timing composition for
  anticipation, acceleration, impact and settle over named animation tracks.
- Active lane: `codex/rts-reference-foundry`, based on merged PR #64/main
  `6ca9d30`; unrelated PR #54 remains outside this pass. Current-head checks are
  required before merge; final GitHub state is authoritative.
- Roots: Truth keeps static geometry, visual and animation claims separate;
  Agency requires explicit caller semantics and optional profiles; Continuity
  preserves canonical source and protected identity relationships; Wisdom
  repaired normals and framing before publication.

### Portable render-style pass — 2026-09-13

- Completed renderer-neutral `game_render_styles.py`, the
  `axm-assets game-render` publisher and a truthful catalog. `realistic-pbr`
  remains an exact identity. `graphic-toon-baked` authors three hard light
  bands; `painted-adventure-baked` authors six bands plus seeded, object-space
  warm/cool pigment rhythm. These are actual colour-field changes, not palette
  labels or extra polygons.
- Stylized realizations fold the source material factor into final linear
  vertex colours and opt into glTF `KHR_materials_unlit`. Positions, normals
  and indices remain exact. The canonical source, its digest, chosen light,
  seed, realization and engine-adapter limits are retained in every package.
  Existing non-unlit GLBs keep their prior document shape.
- Actual verification: **18 focused tests pass** across the eight new render
  tests plus procedural-3D and workshop regressions. Blender 4.3 exported and
  freshly re-imported three 22-primitive courier GLBs. Decoded geometry was
  identical across styles, maximum vertex-colour float error was
  0.0000000298, stylized materials re-imported as unlit while realistic stayed
  lit, and the editable-source/re-import render MAE was 0.0.
- Visual repair: the first comparison cropped the wrench and made painted too
  close to graphic. Stronger chromatic pigment rhythm separated them; final
  wider framing keeps all three silhouettes and labels clear. The final still
  visibly distinguishes lit PBR, hard graphic planes and softer faceted
  painted colour variation on the same form.
- Evidence: `tools/blender/game_render_style_roundtrip.py`,
  `docs/GAME_RENDER_STYLES.md`, and
  `docs/evidence/game-render-style-roundtrip-2026-09-13.json`. No donor code or
  external shader runtime was copied in this pass.
- Limits: fixed authored lighting only. Camera-responsive outlines, dynamic
  light direction, screen-space grain, camera rim and animated brush crawl need
  target-engine adapters. This is a static style/export proof, not animation,
  game-distance, engine colour-management or performance acceptance.
- **Next useful step: priority 5**, expressive character/robot face shapes and
  stances with explicit identity checks.
- Active lane: `codex/rts-reference-foundry`, based on merged PR #63/main
  `b98776a`; unrelated PR #54 remains outside this pass. Current-head checks are
  required before merge; final GitHub state is authoritative.
- Roots: Truth separates fixed-bake evidence from dynamic-shader acceptance;
  Agency keeps every style opt-in and offline; Continuity embeds the exact
  canonical source and preserves legacy realistic output; Wisdom repaired the
  visible style separation and framing before publication.

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
