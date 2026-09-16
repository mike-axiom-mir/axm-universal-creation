# Seven-Round Evolution + Deep Aftertouch Chamber

UC now has a bounded orchestration layer for the pattern:

`brief -> parallel creative teams -> simulate/test/observe -> repair -> re-test -> independently judge -> keep two -> repeat x7 -> retain two finalists with evidence`

The implementation is `src/axm_uc/evolution_aftertouch.py` and the live capability is `AXM-CAP-EVOLUTION-AFTERTOUCH`.

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

## Team workflow

Each round packet asks its team to:

`create concrete candidate -> self-test/simulate -> observe actual result -> diagnose -> repair -> re-run same tests -> submit evidence`

Available UC evidence surfaces can be used as appropriate. The v0.1 chamber has direct self-test adapters for:

- visual/Paintgun thoughts through the existing UC simulation loop;
- project/software/game directories through the existing project verifier.

Unknown media are returned as **NOT_TESTED**. The chamber never converts missing evidence into a fake PASS.

## Two-survivor tournament

The chamber composes the existing context-learning specialist tournament. Independent judgements must cover the complete parallel field before a round can advance. The two finalists in that ranking become the two survivor candidates. Scores are the supplied declared-criterion judgements; UC does not invent missing performance.

A survivor records:

- parent candidate (after round one);
- concrete proposal/output body;
- evidence;
- verification receipts;
- dissent and unknowns;
- criterion judgements and judged score;
- exact candidate digest and lineage identity.

## Final aftertouch evidence gate

After round seven, both finalists are retained. Their verification receipts are summarized across:

- structural;
- functional;
- visual;
- experience;
- context;
- adversarial;
- polish.

Possible final states are:

- `TWO_FINALISTS_RETAINED_ALL_DECLARED_AFTERTOUCH_GATES_PASS`
- `TWO_FINALISTS_RETAINED_WITH_EXPLICIT_TEST_GAPS`
- `TWO_FINALISTS_RETAINED_FINAL_GATE_FAILED`

Even an all-PASS packet means only that the declared evidence lanes passed. It is not a claim of perfection, universal aesthetic quality, semantic omniscience, or human acceptance.

## Authority boundary

The chamber never auto-accepts a finalist, never auto-canonizes one, and never gives a winning team hidden authority. Both finalists remain inspectable outputs with lineage and evidence so a human or higher-level workflow can choose, combine, continue, or reject them explicitly.

## Operations

- `inspect`
- `prepare`
- `advance-round`
- `self-test-candidate`

A normal machine request can route with `kind: "creative-evolution-chamber"` or the other handles declared in the capability manifest.
