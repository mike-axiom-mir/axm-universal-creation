# Stepwise Perspective Workflow

## Purpose

Universal Creation preserves a deliberate internal work cadence even when an entire operation finishes very quickly.

The rule is:

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

Wall-clock speed does not erase logical chronology.

A workflow may complete inside one call while its receipt still proves that planning, pre-analysis, action/result, post-analysis, and advancement happened as separate states.

## Shared orchestration body

Stepwise workflow is not a second top-level coordination system.

The live handle `stepwise-workflow` is owned by `AXM-CAP-SPECIALIST-TOURNAMENT@0.2.0`, the same multi-perspective orchestration body that owns specialist tournaments and contextual specialist-fit history.

The shared body dispatches to:

- `src/axm_uc/specialist_pool.py` for specialist pools, tournaments, ranking, finalist voting, and fit history;
- `src/axm_uc/stepwise_workflow.py` for explicit plans, checkpoints, step execution, splitting, replanning, and chronological receipts.

This keeps one perspective/orchestration surface while allowing two different modes:

```text
many teams inspect one challenge
```

and

```text
many perspectives repeatedly inspect one evolving workflow
```

## Smallness is revisable

A large goal can hide several independent unknowns inside one attractive-looking action.

A valid step therefore declares:

- one stable id;
- one purpose;
- mode `action` or `analysis`;
- expected evidence;
- stop condition;
- dependencies on earlier steps;
- perspective focus;
- split depth.

Initial plans may contain up to 64 steps.

If a checkpoint concludes that the current step still contains separable work, `SPLIT` can replace it with two or more smaller steps.

Current bounds:

- maximum split depth: 8;
- maximum total workflow steps after splitting: 128.

The retired broad step and the reason for replacement remain in evidence.

Small does not mean trivial. It means the next unit has one inspectable purpose and one observable stopping boundary.

## Planning from different perspectives

`prepare` does not silently invent a semantic plan.

It prepares a Specialist Tournament whose challenge is to propose a truthful small-step plan for the goal. The normal deterministic machine/anatomy plan can also be attached as structural context when an ordinary creation request is supplied.

Prepared packets are not claimed to have reasoned. A human, local model, connected model, future cognition organ, or another explicit executor must produce the semantic plan proposals.

A selected plan is validated as `axm.stepwise-perspective-plan/v0.1` before execution.

## Perspective checkpoints

Before and after every meaningful result, the engine selects a contextual panel from different historical positions:

1. current best-fit perspective;
2. middle-fit perspective;
3. lowest-third challenger;
4. deterministic-random challenger when available.

Historical specialist voting therefore influences attention without turning previous winners into the only allowed viewpoint.

A checkpoint asks whether the exact current step should:

- `PROCEED`
- `REPLAN`
- `SPLIT`
- `HOLD`

The deterministic engine prepares the checkpoint. It does not claim the selected specialists answered it until executor-supplied analyses exist for the exact prepared specialist ids.

## Step execution

### Action step

An action step invokes an already-live Universal Creation capability through its existing contract.

No route produces:

`HOLD_NO_LIVE_STEP_ROUTE`

A live capability error produces:

`HOLD_STEP_EXECUTION_ERROR`

The workflow does not invent execution to keep moving.

### Analysis step

An analysis-only step requires an explicit external result, evidence references, and executor identity.

The deterministic workflow engine records and orders that result but does not relabel semantic reasoning as deterministic computation.

## Post-result analysis

After a result exists, a new perspective checkpoint inspects the changed state.

This matters because some useful questions only become visible after an action has produced evidence.

The workflow therefore behaves as:

```text
look
-> act or observe once
-> look again from the changed state
-> choose the next smallest justified move
```

## Transition policy

Current checkpoint aggregation is explicitly conservative:

```text
HOLD > SPLIT > REPLAN > PROCEED
```

This is a named workflow-control policy, not a claim that the strictest perspective is objectively correct.

Different aggregation policies may be added later, but their meaning must remain explicit and testable.

## SPLIT

`SPLIT` retires the current broad step and inserts smaller replacements.

The first replacement inherits the old dependencies. Later children are dependency-ordered, and downstream steps that depended on the retired parent are rebound to the final replacement.

History is not rewritten.

## REPLAN

`REPLAN` preserves completed work and replaces only the remaining future plan.

The old remaining tail and the replanning reason stay visible.

## HOLD

`HOLD` preserves the exact current workflow state when evidence or capability is insufficient to justify continuation.

A HOLD is a truth state, not automatically a failure.

## Instant staged mode

`instant-staged` exists for cases where all required executor analyses/results are already available in one call.

The logical sequence still remains:

```text
step 1 pre
step 1 result/action
step 1 post
step 2 pre
step 2 result/action
step 2 post
...
```

If a checkpoint reaches `SPLIT`, `REPLAN`, or `HOLD`, the instant run stops there.

Therefore:

```text
instant wall-clock completion != one-step logical completion
```

## Digest-bound continuity

Workflow states and checkpoints are digest-bound.

A checkpoint is tied to the exact workflow state, current step, and checkpoint phase. An old checkpoint cannot be silently replayed after the workflow changes.

The timeline retains perspective checkpoints, results, execution HOLDs, split events, and replanning events.

## Existing anatomy made executable

The shared `AXM-CAP-SPECIALIST-TOURNAMENT@0.2.0` orchestration body explicitly live-backs:

- `AXM-19-AI-ML-AGENTS-O-021-specialist-summoner`;
- `AXM-19-AI-ML-AGENTS-C-035-specialist-profile`;
- `AXM-24-WORKSPACE-COLLABORATION-O-006-project-planner`;
- `AXM-03-TIME-STATE-EVENT-O-007-workflow-engine`;
- `AXM-03-TIME-STATE-EVENT-C-015-workflow-step`.

No duplicate stepwise capability manifest is required.

## Truth boundary

The implementation proves that Universal Creation can prepare multi-perspective planning work, validate explicit small-step plans, maintain digest-bound workflow state, inspect each meaningful step before and after its result, invoke existing live capabilities, record external semantic results truthfully, split broad steps, replan only the future, HOLD when continuation is unjustified, and preserve chronology even in one fast call.

It does not prove that prepared perspective packets reasoned without an executor, that the current transition policy is universally optimal, that every real-world goal can be automatically decomposed into semantically correct steps, that more steps are always better, or that completing a workflow proves the overall goal was correct.

The narrower reusable rule is:

> Make the next thing small enough to inspect, look at it through different eyes, act or observe once, then decide again from the new state.
