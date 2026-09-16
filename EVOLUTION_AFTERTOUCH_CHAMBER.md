# Seven-Round Evolution + Deep Aftertouch Chamber

UC now has a bounded orchestration layer for the pattern:

`brief -> parallel creative teams -> simulate/test/observe -> preview -> repair -> re-test -> independently judge -> keep two -> repeat x7 -> retain two finalists with evidence`

The core implementation is `src/axm_uc/evolution_aftertouch.py`. Rich 3D/game observations live in `src/axm_uc/aftertouch_media_observers.py`, and intermediate visual checkpoint policy/retention lives in `src/axm_uc/aftertouch_preview.py`. The live capability is `AXM-CAP-EVOLUTION-AFTERTOUCH`.

## Why it exists

Creation depth and tool count do not guarantee a finished result. A creator can stop as soon as an object is technically valid even when detail, use quality, context behavior, or final polish is still thin. This chamber makes repeated evidence-bearing aftertouch an explicit part of the creation path.

It deliberately reuses the existing UC specialist tournament instead of inventing another agent/team ontology. Every round prepares multiple isolated creative-team packets. The deterministic machine does **not** pretend those teams reasoned or built anything until a cognition provider, human, or other executor returns concrete submissions and evidence.

## Fixed seven rounds

1. **Foundation** — structure, function, interfaces, feasibility.
2. **Composition** — shape, layout, hierarchy, spatial/system composition.
3. **Detail** — secondary/tertiary construction and detail density.
4. **Experience** — actual use/play/interaction, readability and recovery.
5. **Stress** — edge cases, bad inputs, collisions, load, failure/retry and regression pressure.
6. **Creative elevation** — search beyond the obvious local optimum without discarding proven working behavior.
7. **Deep aftertouch** — structural, functional, visual, experience, context, adversarial and polish passes followed by re-test.

Each completed round keeps **exactly two** judged survivor outputs. Those exact survivors become the two parent bodies for the next round; new teams are deterministically assigned one parent so both outputs remain live rather than being silently collapsed into one.

## Intermediate screenshot / visual checkpoints

A technically valid result can still look obviously wrong. UC therefore has an explicit preview layer between rounds.

When a preview adapter is available, the surviving candidate can retain exact visual evidence before another round proceeds:

- browser games can retain the real offline headless-browser PNG captured by the existing browser observer;
- visual/Paintgun thoughts can retain their deterministic SVG projection;
- 3D candidates can bind a renderer-produced `preview_image_path` to the exact survivor. The GLB pose/skin runtime remains separate evidence and does not pretend it rendered pixels.

Preview capture is not aesthetic judgment. A screenshot proves that exact pixels were produced; it does not prove they are attractive, readable, coherent, or finished.

The user chooses the preview policy at chamber preparation:

- `internal` — default. Machine-observable preview evidence is retained between rounds without interrupting the user. AI review remains off.
- `user-milestones` — internal previews continue, and selected rounds (default 3, 6, 7) stop for user feedback.
- `user-every-round` — every completed round stops after preview capture until both surviving candidates receive user feedback.
- `off` — no intermediate preview checkpoint is added.

`preview_policy.ai_review=true` explicitly allows an AI reviewer to inspect the retained preview. It is **false by default** so UC's normal local/offline path does not silently invoke AI.

At a user checkpoint, each retained survivor receives a digest-bound `preview_checkpoint`. The user may record `continue`, `adjust`, or `hold`, plus requested changes. Until both survivors have feedback, the next round is blocked. The exact review and requested changes are then copied into the next round's parent/creative-team context, so the visual correction is not lost in hidden chat state.

A final-round user checkpoint also blocks output readiness until the preview review is resolved.

## Team workflow

Each round packet asks its team to:

`create concrete candidate -> self-test/simulate -> observe actual result -> inspect preview when available -> diagnose -> repair -> re-run same tests -> submit evidence`

Available UC evidence surfaces can be used as appropriate. Direct self-test adapters include:

- visual/Paintgun thoughts through the existing UC simulation loop;
- project/software directories through the existing project verifier;
- GLB assets through the existing pure-Python game-pose runtime;
- playable local browser games through the existing offline headless-browser observer.

Unknown media are returned as **NOT_TESTED**. The chamber never converts missing evidence into a fake PASS.

## Rich media observation boundaries

### 3D / GLB

UC can parse exact GLB bytes, inspect nodes, clips, skins, primitives and vertices, sample static/animated poses, inspect skinned bounds, measure sampled movement and verify required named socket positions. This is strong geometry/runtime evidence, not rendering or aesthetic proof.

For pixel review, a 3D creation supplies a renderer-produced preview image until an explicit renderer executor is available. The image digest is retained alongside the candidate.

### Playable browser games

When a caller supplies or explicitly allows discovery of a Chromium-compatible executable, UC can execute the local game offline, retain screenshot/DOM/runtime evidence, detect JavaScript runtime errors and viewport overflow, and optionally run bounded focus/activation/reset recipes. Synthetic activation is opt-in.

The screenshot can then be reviewed between rounds instead of only after the final output.

## Two-survivor tournament

The chamber composes the existing context-learning specialist tournament. Independent judgements must cover the complete parallel field before a round can advance. The two finalists in that ranking become the two survivor candidates. Scores are the supplied declared-criterion judgements; UC does not invent missing performance.

A survivor records:

- parent candidate (after round one);
- concrete proposal/output body;
- evidence;
- verification receipts;
- dissent and unknowns;
- criterion judgements and judged score;
- exact candidate digest and lineage identity;
- intermediate preview checkpoint and review history when enabled.

## Final aftertouch evidence gate

After round seven, both finalists are retained. Their verification receipts are summarized across:

- structural;
- functional;
- visual;
- experience;
- context;
- adversarial;
- polish.

Possible final evidence states include:

- `TWO_FINALISTS_RETAINED_ALL_DECLARED_AFTERTOUCH_GATES_PASS`
- `TWO_FINALISTS_RETAINED_WITH_EXPLICIT_TEST_GAPS`
- `TWO_FINALISTS_RETAINED_FINAL_GATE_FAILED`

A user preview checkpoint may additionally keep output readiness false until feedback is recorded.

Even an all-PASS packet means only that the declared evidence lanes passed. It is not a claim of perfection, universal aesthetic quality, semantic omniscience, or human acceptance.

## Authority boundary

The chamber never auto-accepts a finalist, never auto-canonizes one, and never gives a winning team hidden authority. Both finalists remain inspectable outputs with lineage, evidence, previews and feedback so a human or higher-level workflow can choose, combine, continue, repair, or reject them explicitly.

## Operations

- `inspect`
- `prepare`
- `advance-round`
- `self-test-candidate`
- `capture-preview`
- `record-preview-feedback`

A normal machine request can route with `kind: "creative-evolution-chamber"` or the other handles declared in the capability manifest.
