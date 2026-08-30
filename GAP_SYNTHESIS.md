# Evidence-Bound Gap Synthesis

Universal Creation can now bridge one small part of the path between observing a missing creation route and supplying a complete Creation-Unit Forge proposal.

The implemented loop is:

`real unroutable request -> observe current live routes -> find supported structural bridges -> READY or HOLD -> compile closed proposal -> spawn detached candidate -> run request-shaped fixture -> stop before admission`

This is a deterministic proposal compiler, not a claim that the machine understands every requested format or can invent arbitrary semantic source.

## Why this layer exists

The planner already exposes `CAPABILITY_GAP` instead of silently weakening an output. The Creation-Unit Forge already materializes and tests a complete supplied design. The missing connection was a bounded way to turn some observed gaps into an exact proposal without requiring a human or AI to write every manifest field by hand.

`AXM-CAP-SYNTHESIZE-CREATION-GAP` implements that connection for one narrow, testable blueprint.

Every unroutable `create` result now includes a `gap_synthesis` analysis. This analysis is separate from lexical anatomy matching: it first checks whether an existing detached capability candidate already handles the request, then examines the exact request input shape and current live capability contracts. It reports whether reuse, an implemented proposal blueprint, or a HOLD is the smallest honest next step.

## Operations

| Operation | Effect | Persistent write |
| --- | --- | --- |
| `analyze` | Bind the exact request digest to current route coverage and supported structural bridge candidates | none |
| `propose` | Compile a complete closed `axm.creation-unit-spawn-proposal/v0.1` when one supported bridge is selected | none |
| `materialize-and-test` | Pass the compiled proposal through the detached forge and execute its exact request-shaped fixture | detached candidate package only |

No operation admits, installs, registers, promotes, merges, changes CANON, changes permissions, or rewrites the requested output destination.

## First implemented blueprint

The first recipe is:

`axm.blueprint.exact-utf8-file-route-alias/v0.1`

It applies only when:

- the requested kind has no live route;
- the request inputs are exactly `path` and `content`;
- `path` and `content` are text;
- a live deterministic capability requires exactly those inputs;
- that capability declares a UTF-8 file output;
- one compatible bridge is uniquely visible, or the caller explicitly names one exact ID from the observed candidate list.

The compiler emits a candidate `DETERMINISTIC_ALIAS` manifest. It copies the chosen live dependency's visible input/output contract, binds exact manifest and request digests into provenance, records the complete gap analysis inside `gap-analysis.json`, and derives one disposable test from the requested content.

The original output path is never used during the experiment. The fixture path is rewritten under `${TEST_DIR}/`, and the candidate tester removes its build space afterward.

## READY is not semantic proof

An exact input/output shape can justify an experiment; it cannot prove that two meanings are equivalent.

For example, an exact portable note can be written by the live UTF-8 text primitive. The generated adapter can prove that the exact supplied note bytes survive its route. That evidence does not prove parsing, rendering, links, accessibility, or every future note-format requirement.

The analysis therefore remains:

`DETERMINISTIC_STRUCTURAL_BRIDGE_HYPOTHESIS`

The tested candidate remains detached even when its fixture passes.

## HOLD states

The compiler refuses to guess when its blueprint cannot carry the gap:

- `COVERED_NO_SYNTHESIS_NEEDED` — the requested kind is already live;
- `REUSE_EXISTING_CANDIDATE_BEFORE_SYNTHESIS` — one detached candidate already handles the request kind and should be inspected or tested before generating a duplicate;
- `HOLD_AMBIGUOUS_EXISTING_CANDIDATES` — several detached candidates already claim the route and none is silently preferred;
- `HOLD_NO_SUPPORTED_SYNTHESIS_BLUEPRINT` — the current compiler would need to invent source or semantics;
- `HOLD_AMBIGUOUS_STRUCTURAL_BRIDGE` — several compatible primitives exist and none is silently selected.

An explicit `bridge_capability_id` may resolve ambiguity only when it exactly names one candidate already present in the analysis. It cannot inject an unobserved dependency.

Generated candidates also cannot shadow an existing live capability identity. Replacement or upgrade semantics require a separate explicit contract rather than being smuggled through this new-route compiler.

## Try a real new note-route gap

```bash
PYTHONPATH=src python -m axm_uc gap-forge
PYTHONPATH=src python -m axm_uc create examples/requests/analyze_note_route_gap.json
PYTHONPATH=src python -m axm_uc create examples/requests/propose_note_route_gap.json
PYTHONPATH=src python -m axm_uc create examples/requests/explore_note_route_gap.json
```

The final command creates `creations/spawned/generated-note-adapter/`, verifies its exact forge package, and executes the generated manifest's request-shaped fixture. It does not create `creations/generated/example.note`, add a live `portable-note-file` route, or request admission.

Measured on the current source body, the example selected `AXM-CAP-WRITE-TEXT@0.1.0`, produced package digest `sha256:2662c9dba54ff4005ad3bf346dd0b0066fad0bee29659fbe92c7b1545b24def5`, and passed the generated candidate test twice with that same digest. The original destination remained absent and the live route remained absent.

## Current boundary and next multiplier

The compiler currently knows one manifest-level alias recipe. It does not yet synthesize:

- parser-aware or runtime-aware format implementations;
- deterministic composites with several live capabilities;
- missing organ source or protocol semantics;
- verifier code for a previously unsupported evidence type;
- learned or AI-authored source without an explicitly labelled external cognition boundary;
- admission decisions.

The next useful growth should come from real creation gaps. Likely extensions are explicit composite-recipe compilation and verifier-aware proposals, but they should be added only with a concrete request and tests that expose why the new recipe is justified.
