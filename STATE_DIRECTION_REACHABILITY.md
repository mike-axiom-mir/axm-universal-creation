# State Direction and Current Reachability

AXM Universal Creation should not confuse a missing path in the current machine with proof that no path can exist.

This is a truth-boundary rule, not a claim that every imagined result is physically achievable.

## Core distinction

When a requested outcome has no current route, report the strongest statement justified by present evidence:

- `CURRENT_PATH_AVAILABLE` — the current machine has an identified path;
- `PATH_UNKNOWN_CURRENTLY` — no current path is known;
- `BLOCKED_BY_CURRENT_CONSTRAINT` — a specific present constraint has been observed.

Do not silently promote `PATH_UNKNOWN_CURRENTLY` into `IMPOSSIBLE` or `FUNDAMENTALLY_UNREACHABLE`.

A statement of fundamental impossibility would require evidence appropriate to that much stronger claim. The machine's ordinary capability gaps do not provide that proof.

## Creation orientation

A creation request can be treated as direction toward a more specific machine-observable state rather than only as a request to select a pre-existing tool.

A bounded creation loop may therefore be represented as:

`current state -> target direction -> explicit properties/constraints -> known path? -> identify missing transition -> reuse/build/test intermediate machinery -> verify -> next state`

If a path is missing, the machine should preserve the target direction while it identifies what is currently missing. That missing piece may be knowledge, representation, resource handling, constraint handling, transition machinery, verification machinery, or some combination of them.

Friction is evidence about the current path. Friction alone is not proof that the target is impossible.

## Prompts and machine state

A natural-language or visual-generation prompt is not literally processor machine code.

It can, however, act as a high-level **state-direction source**. Useful details can be progressively compiled into machine-readable forms such as:

- explicit constraints;
- structured target properties;
- geometry/material/lighting/state descriptors;
- relationships and dependencies;
- candidate transition rules;
- deterministic parameters;
- verification criteria.

This matters for deterministic creation because a prompt may contain reusable construction information even when the original prompt was written for a learned image model. The useful question is not "was this written for AI or deterministic code?" but "which parts describe state, relationships, constraints, transformations, or evidence strongly enough to compile into another representation?"

No source prompt is automatically treated as ground truth. Extracted rules remain hypotheses until tested against the intended result.

## Open transition graph

The currently implemented transition graph is not assumed to be complete.

A missing capability may therefore remain a construction or research question:

`no known edge -> identify required edge -> search/reuse/synthesize candidate machinery -> bounded experiment -> evidence -> retain, revise, or hold`

This does not create a growth mandate. The machine is not required to search indefinitely, expand itself, or force a target to become reachable. The four roots remain the governing orientation for self-change.

## Authority remains separate

Discovering a path does not grant permission to use it.

Likewise:

- capability is not permission;
- understanding is not permission;
- a successful experiment is not automatic admission;
- a candidate transition is not automatic promotion;
- reachability is not automatic merge or CANON authority.

This preserves Agency while allowing the machine to reason about capability without pretending current software boundaries are universal laws.

## Relation to the current machine

The existing `CAPABILITY_GAP` path already uses bounded language such as `truth_status: HYPOTHESIS` and `smallest_missing_capability_currently_justified` rather than declaring unsupported requests impossible.

This addition makes that underlying distinction explicit and gives future prompt-to-state, image-rule extraction, deterministic visual compilation, and broader creation experiments a shared vocabulary.

## Truth boundary

This document claims:

- the machine can distinguish a current missing path from a stronger impossibility claim;
- prompts can contain descriptions that are compilable into deterministic state/rule representations;
- a transition graph can be extended by verified new machinery.

It does **not** claim:

- literal unlimited physical capability;
- that every requested target is reachable;
- that natural-language prompts are literal machine instructions;
- that state descriptions alone solve construction;
- that discovering a transition authorizes executing it;
- that the present experimental machine already implements general target-state synthesis.
