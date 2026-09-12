# Production readiness: a bounded post-apocalyptic slice

This is a source-grounded planning audit, not a generated game's acceptance
receipt. It audits UC's `axm/browser-arena-use-loop` lane, starting from local
commit `de45551` / tree `808799962f791566efe2b32367001a75a14ed991`, plus the
explicit changes documented below. Remote PR #40 was observed open at
`d0c21aeebac105dbf92b1feaa6af1ef471ab8161`; its base was
`e7e5a68cce2206da72cc9cac6ce6582304387598`. The starting local and remote trees
matched. This is not a claim that these changes are installed on main.

Scope: installed UC source, its existing anatomy census, and already pinned
donor workbenches. This pass does not establish the current contents of every
AXM repository. Missing below means missing from the inspected slice route;
potential donor implementations still require source and runtime checks.

## The 400-organ question

The reproducible package census reports 415 descriptors, 15 installed packages,
and 400 records without an installed package. The independent live-capability
binding map reports 21 organ records with explicit `implements` declarations.
Their intersection contains one organ. The union therefore covers 35 organs;
380 have neither declaration. The census now reports both routes together.

These counts measure declarations and installed package mappings. A package
such as `axm.foundation.identity-registry@1.0.0` renders a namespaced empty JSON
document; it does not supply an identity service. Likewise a geometry-generator
binding can cover a three-primitive exporter without covering professional
asset creation. Do not turn any of these counts into an AAA-readiness score.

Descriptors need bounded implementations where useful. They are not dormant
production code that can all be switched on. Several useful tools also remain
outside the manifest/package census, so absence of a binding is not proof that
all relevant source is absent.

## Slice used to expose the gaps

An offline survivor outpost: one environment, one worker, one defender, one
enemy family, a custom workshop, three buildable structures, a short encounter,
resource spending and repair, sound feedback, and a declared target device.
This is an authored test brief. Multiplayer, a large streaming world, and AAA
acceptance would add requirements and are not implied by this slice.

`AVAILABLE` means a bounded local operation exists. `PARTIAL` means the required
stage exceeds that operation. `PRESENT-BUT-DISCONNECTED` means inspectable source
or an authored asset exists but no integration in this slice is established.
`MISSING` means no implementation was established in the inspected route.
None of the labels alone certifies runtime availability or artistic quality.

| Stage | Status | Concrete source/evidence | Missing connection or acceptance |
| --- | --- | --- | --- |
| Find declared implementation coverage | AVAILABLE | `organ_materialization.census_organs`, `ExecutableAnatomy`; all 415 rows | Unmapped donor code needs separate inspection |
| Compose an explicit bounded program | AVAILABLE | `CapabilityStore.invoke` COMPOSITE steps; `organ_project.assemble_organ_project` dependency/interface resolution | These already execute compositions; the conductor does not start from zero |
| Discover candidate creation chains | AVAILABLE | `pipeline_map.map_capabilities`; exact tokens, bounded search | 32 manifest nodes + 15 package nodes + four request builders; candidate connections are not executed |
| Execute a production graph with artifact handoffs and review-driven repair | PARTIAL | Existing composites, `visual_3d_iteration` state and `design_observer` repair proposals | No established end-to-end director combining these stages; mapper output is not an executable contract |
| Carry visual direction and attributed reviews | PARTIAL | `design_observer.record_render_observation`, `judge_rendered_design`, `visual_3d.assess_3d_output` | Criteria and supplied judgments exist; automatic semantic visual judgment is not established |
| Generate basic geometry and material maps | AVAILABLE | `procedural_3d.build_glb`, `media_workbench.py`, `fabric_material.py` | Native GLB grammar is boxes/pyramids/cylinders with scalar materials; maps are separate artifacts |
| Produce distinctive survivor architecture | PRESENT-BUT-DISCONNECTED | Authored workshop v03 handoff from this chat: custom surfaces, 11,338 near / 3,174 far triangles, nine material groups | Recipe lives outside UC's installed source; not a UC CLI organ, no UV texture set or target-engine import proof |
| Forge richer Blender assets | PARTIAL | `visual_3d.forge_3d_asset`, `tools/blender/axm_blender_forge.py` | Source exists; Blender unavailable in this session. Full retopo/UV/bake/material/decal/engine acceptance is not established |
| Rig, export and inspect a character | PARTIAL | `tools/blender/axm_oops_character.py`, `verify_rigged_character.py`, `package_rigged_character.py` | Specialist path exists; survivor faction fit, live retargeting, foot contacts and weapon synchronization need proof |
| Run construction and encounter rules | AVAILABLE | `browser_game.py` optional outpost economy, rosters, waves; executable generated-JS regressions | Bounded arena behavior, not a complete RTS |
| Reuse explicit state operations | PRESENT-BUT-DISCONNECTED | `grammar_workbench.run_grammar_tool`: construction-program and State Ripple | Standalone adapters exist; neither is automatically the RTS's authoritative game state |
| Navigation, building damage and obstruction | MISSING | Relevant descriptors exist in game/simulation anatomy | No established path from current arena rules to these slice requirements |
| Render and interact in a browser | PARTIAL | Generated arena renderer; `design_browser.capture_local_browser` | Browser support depends on runtime; no current target-device performance acceptance |
| Import, launch and probe a production engine | MISSING | GLB/FBX export and Blender inspection are useful predecessors | No established engine import/play/profile/repair loop for this slice |
| Generate/convert sound files | AVAILABLE | `procedural_media.py`, `media_workbench.py` PCM operations | Parsing/normalization does not establish good sound |
| Coordinate spatial sound, Foley, reactions and mix | MISSING | Audio descriptors and PCM plumbing | No established complete slice sound-event/mix/listening loop |
| Plan cheaper visual realization | PRESENT-BUT-DISCONNECTED | Grammar Glass render-budget adapter; arena scenery caching | Selection plans and Canvas command counts do not measure CPU/GPU frame time |
| Profile and repair against a device budget | MISSING | No fresh frame/GPU/memory trace for the slice in this audit | Define device/workload; capture real timings and memory before adaptation claims |
| Iterate one complete accepted playable slice | PARTIAL | `visual_3d_iteration`, browser use/repair evidence, structural tests | No joint visual, gameplay, audio, reliability and performance acceptance receipt |

## Map the seven suggested multipliers onto existing machinery

| Proposed family | Existing starting point | Next bounded integration |
| --- | --- | --- |
| Creation Director | Composite interpreter, organ assembly, candidate mapper, per-asset iteration | Typed artifact inputs/outputs, preflighted dependencies, execution receipts and resumable stage state; reject cycles and missing inputs before mutation |
| Perceptual observers | Design observer and artifact-bound 3D reviews | Supply actual image/model/human observations for silhouette, proportion, material and gameplay-distance readability; retain observer attribution and uncertainty |
| Production assets | Native GLB, Blender forge, material tools, authored workshop | Bring custom surfaces into a reusable supported geometry contract; connect materials, collision and game-distance review |
| Engine runtime bridge | Exported GLB/FBX and browser capture | One selected engine's explicit import, launch, control probe and artifact-bound result adapter |
| Gameplay/world | Arena construction/waves, deterministic state machine, Glass programs | One reusable navigation/obstruction rule set; connect actual game state and verify worker/defender behavior |
| Performance | Scenery cache and render-budget planning | Measure a declared workload/device, retain frame-time distributions, compare identical workloads after repair |
| Slice evolution | Asset iteration and design repair loops | Assemble one versioned slice; route failed acceptance back to the exact source stage and retest dependent artifacts |

Relevant existing anatomy families are Foundation, Time/State/Event,
Code/Grammar, 3D/Spatial, Rendering/Materials, Animation/Video, Audio,
Simulation/Navigation, Games, and Workspace/Collaboration. Their names organize
implementation work; they do not supply missing implementations. Examples:
`AXM-11-3D-SPATIAL-O-003-topology-validator` has a bounded live binding;
`AXM-15-SIMULATION-XR-O-010-navigation-and-pathfinding-organ` and
`AXM-16-GAMES-O-004-world-builder` require checking concrete source before
claiming a slice-ready implementation. Use the exact-ID census to inspect the
package and capability routes separately.

Grammar donor provenance remains pinned in
`third_party/grammar-workbench/provenance.json`: Grammar 102
`ff58375b65a4033041e6de957263d4146aa7429e` and Grammar Glass
`e046b7adb5873b666c79182c90d46438116eef03`. Those are installed donor snapshots,
not claims about the latest remote heads.

## Concrete repairs made during this audit

1. The existing census now reconciles package mappings and live bindings,
   deduplicates anatomy IDs and exposes the actual bounded binding bases. Its
   `--coverage` filter can find the 380 records with neither declaration or the
   20 with only a live binding. It preserves package-only state semantics.
2. Native cylinders previously emitted inward triangle winding on the sides
   and both caps while assigning outward normals. The native generator now
   emits outward-facing triangles. This changes cylinder GLB bytes, so rebuild
   affected native assets rather than expecting prior files to change.
3. Native GLB verification now decodes actual positions, normals and indices.
   It rejects invalid accessor ranges, non-finite values, out-of-range indices,
   degenerate triangles and winding/normal disagreement. Regressions inspect
   emitted geometry and inject binary defects. This closes a real false-pass
   case; it does not certify appearance, manifoldness or engine compatibility.

The earlier workshop recipe had a local cylinder correction and a custom
geometry exporter. Existing ZIPs are unchanged. Neither that recipe nor all
400 descriptive organs were installed by this audit.

Recommended next production increment: one explicit workshop-to-outpost
pipeline using the existing composition machinery, with a supported custom
surface generator, material handoff, collision contract, actual browser/engine
observation and a gameplay-distance review. Implement and verify the missing
operations used by that slice, then expand the proven capability family.

Validation for this pass: `python tools/build.py` passed all 488 tests in
57.502 seconds (`BUILD_OK`). A direct CLI coverage query returned 380 matching
records with bounded pagination. Geometry regressions checked exported boxes,
pyramids and cylinders at 3/16/64 radial segments, positive signed volume, and
rejection of deliberately reversed, degenerate, invalid-index and NaN geometry.
No new browser screenshot, game playthrough, engine import, listening session
or performance trace was captured during this audit.
