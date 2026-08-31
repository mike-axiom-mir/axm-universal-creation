# Stepwise Perspective Workflow

## Purpose

Universal Creation can now preserve a deliberate thinking cadence even when the entire operation finishes quickly.

The core rule is:

```text
goal
-> competing small-step plans
-> select an explicit plan
-> pre-step perspective checkpoint
-> one bounded action or one bounded analysis result
-> post-step perspective checkpoint
-> PROCEED / SPLIT / REPLAN / HOLD
-> next step
```

Wall-clock speed does not remove logical chronology.

An operation may finish in one call or in milliseconds and still retain an inspectable sequence proving that planning, pre-analysis, execution/result, and post-analysis happened as separate states.

This is not a requirement to make software artificially slow. It is a requirement not to confuse fast execution with one opaque leap.

## Why small steps matter

A large goal can contain several independent unknowns. Treating them as one action hides where an assumption entered and makes failure harder to localize.

Stepwise Perspective Workflow therefore makes step size revisable.

An initial plan may contain up to 64 steps. During execution a perspective checkpoint may decide a step is still too broad and return `SPLIT`.

The current step can then be replaced by two or more smaller steps. The replacement is bounded by:

- maximum split depth: 8;
- maximum total workflow steps after splitting: 128.

The retired broad step, its analyses, and the reason for splitting remain visible.

Small does not mean trivial. It means one step has one inspectable purpose, one expected-evidence contract, and one stop condition.

## Planning from different perspectives

`prepare` does not silently invent a plan.

It prepares a Specialist Tournament whose challenge is to propose the smallest truthful executable plan for the supplied goal.

The same Specialist Tournament machinery already provides:

- detailed universal working perspectives;
- challenge-derived registry specialists;
- best, middle, lowest-third, mixed-random, and combination teams;
- isolated team challenge packets;
- evidence-backed judging;
- finalist voting and contextual fit history when that voting process is explicitly used.

A planning packet existing is not evidence that a specialist or model reasoned over it. An executor must produce actual plan proposals.

The selected plan is then validated into `axm.stepwise-perspective-plan/v0.1`.

If an ordinary machine request is supplied during preparation, the normal deterministic software-direction/anatomy/topology plan is attached as structural context. This gives semantic planning teams the machine's already-observed structure without pretending that structural matching is itself reasoning.

## Step contract

Every step declares:

- stable step id;
- purpose;
- mode: `action` or `analysis`;
- expected evidence;
- stop condition;
- dependencies;
- perspective focus;
- split depth.

An `action` step also declares exactly one action:

```json
{
  "kind": "some-live-creation-kind",
  "inputs": {},
  "direction": "optional visible direction"
}
```

Dependencies may reference only earlier steps. This keeps the initial selected plan acyclic and chronologically inspectable.

## Pre-step checkpoint

Before an action/result, the engine selects a small contextual panel from the specialist pool.

The panel deliberately includes different historical positions:

1. current best-fit perspective;
2. middle-fit perspective;
3. lowest-third challenger;
4. deterministic-random challenger when a fourth unique profile is available.

Historical winners therefore influence attention without becoming the only eyes allowed to inspect the workflow.

The pre-step checkpoint asks questions such as:

- Which assumption could make this step too large or incorrectly ordered?
- What evidence should exist before execution?
- Should this step `PROCEED`, `SPLIT`, `REPLAN`, or `HOLD`?

The deterministic engine only prepares these prompts. It does not claim the perspectives answered them until an executor supplies analyses for the exact prepared specialist ids.

## One bounded action or analysis result

### Action step

After a successful pre-checkpoint, an action step can invoke an already-live Universal Creation capability.

The workflow engine does not bypass that capability's own contracts, truth boundaries, permissions, or errors.

If no live route exists, the workflow becomes:

`HOLD_NO_LIVE_STEP_ROUTE`

It does not invent execution.

If the live capability returns an error, the workflow becomes:

`HOLD_STEP_EXECUTION_ERROR`

### Analysis step

An analysis-only step is deliberately not treated as executable deterministic cognition.

A human, local model, connected model, future cognition organ, or another explicit executor must supply the result plus evidence.

The result receipt records the executor and exact result digest.

## Post-step checkpoint

After a result exists, a new contextual perspective panel inspects what reality actually produced.

The post checkpoint asks questions such as:

- Does the observed result satisfy the declared evidence and stop condition?
- What gap or contradiction appeared only after this result existed?
- Should the workflow `PROCEED`, `SPLIT`, `REPLAN`, or `HOLD` before the next step?

This makes analysis an inter-step activity rather than a one-time ceremony at the start.

## Transition rule

Each supplied perspective chooses one transition:

- `PROCEED`
- `REPLAN`
- `SPLIT`
- `HOLD`

The current deterministic aggregation rule is conservative:

```text
HOLD > SPLIT > REPLAN > PROCEED
```

This is a workflow-control rule, not a claim that the strictest perspective is objectively correct.

It intentionally makes one serious dissent sufficient to stop an opaque continuation.

A future evolution may support other explicit aggregation policies if evidence shows they are useful. Such a policy should remain named and inspectable rather than silently changing the meaning of a checkpoint.

## SPLIT

When the aggregate transition is `SPLIT`, the current step is retired and replaced by two or more smaller steps.

The first child inherits the old dependencies.

Later children form a dependency chain.

Any later step that depended on the retired parent is rebound to the final child.

The retired step remains in workflow evidence with:

- old step body;
- old state;
- reason for splitting;
- replacement ids.

This allows recursive decomposition without rewriting history.

## REPLAN

`REPLAN` preserves completed work and replaces only the remaining plan tail.

The previous remaining plan is retained as retired evidence with the replanning reason.

This lets new observations change the future without pretending the earlier plan never existed.

## HOLD

`HOLD` stops progression while preserving the exact current state.

A HOLD is not failure-by-default. It means the workflow has reached a point where its current evidence or capabilities do not justify automatic continuation.

## Instant staged mode

`instant-staged` exists for work where all required executor analyses/results are already available in one call.

It still processes every step in chronological order:

```text
step 1 pre
step 1 result/action
step 1 post
step 2 pre
step 2 result/action
step 2 post
...
```

If any checkpoint produces `SPLIT`, `REPLAN`, or `HOLD`, the instant run stops in that state.

It does not skip intermediate reasoning states simply because the caller provided all inputs up front.

This distinction is important:

```text
instant wall-clock completion != one-step logical completion
```

## Digest-bound continuity

Workflow states are digest-bound.

A checkpoint is tied to:

- the exact workflow digest;
- the exact current step;
- the checkpoint phase.

A checkpoint prepared for an earlier workflow state cannot be silently replayed after the workflow changes.

The timeline records:

- perspective checkpoints;
- exact results;
- execution HOLDs;
- split events;
- replanning events.

## Existing anatomy made executable

This capability deliberately reuses the existing Universal Creation Map instead of adding duplicate terminology.

`AXM-CAP-STEPWISE-PERSPECTIVE-WORKFLOW@0.1.0` explicitly implements:

- `AXM-24-WORKSPACE-COLLABORATION-O-006-project-planner`;
- `AXM-03-TIME-STATE-EVENT-O-007-workflow-engine`;
- `AXM-03-TIME-STATE-EVENT-C-015-workflow-step`.

It also uses the already-live specialist profile component.

## Truth boundary

The current implementation proves that Universal Creation can:

- prepare competing perspective-based planning packets;
- validate an explicit small-step plan;
- maintain digest-bound workflow state;
- prepare different contextual perspectives before and after each step;
- execute already-live deterministic action capabilities;
- record externally executed analysis results without relabeling them as deterministic cognition;
- recursively split broad steps;
- replan only the remaining future;
- HOLD when execution or evidence does not justify continuation;
- preserve pre/result/post chronology even in one fast call.

It does **not** prove that:

- prepared specialist packets actually reasoned without an executor;
- the conservative checkpoint policy is universally optimal;
- every broad real-world problem can be decomposed automatically into correct semantic steps;
- more steps are always better;
- completing many steps implies the overall goal is correct;
- wall-clock speed corresponds to reasoning depth.

The useful rule is narrower:

> Make the next thing small enough to inspect, look at it through different eyes, act or observe once, then decide again from the new state.
