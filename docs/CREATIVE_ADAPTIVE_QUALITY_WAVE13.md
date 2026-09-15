# Adaptive Quality Resolver — Wave 13

Wave 13 turns the Creative Flow gauntlet result into a bounded machine capability: for an installed deterministic quality profile, Universal Creation can derive an explicit Creative Flow plan from **goal + requested quality + machine policy** instead of requiring the caller to name every hand.

This is not universal prose planning. Unknown or ambiguous goals remain on HOLD.

## Quality is depth, not a hand-count target

`quality` accepts any finite number from `0..1`. Convenience aliases such as `draft`, `game-ready`, `production`, `high`, `ultra`, `max-current-body`, and `maximum` only map into that numeric range.

For the first installed profile, higher quality progressively wakes more of the already-installed Creative Hands body:

- draft shape;
- assembled game geometry and topology evidence;
- UV/material/texture production;
- material detail, rigging, skinning and animation;
- premium hard-surface work when the required operation exists.

Texture resolution, scratch density/length and animation bake sampling continue to scale inside the deeper ranges. Stage boundaries therefore coexist with continuous parameters.

The resolver reports `requested_quality` and `realized_quality` separately. It never renames a cheaper realization as the requested quality.

## Initial deterministic profile

Wave 13 installs one proven profile:

`game-prop.armored-crate/v1`

It is derived from the quality gauntlet that already executed the same armored sci-fi supply-crate creation at several depths. Goal matching is deterministic and noun-bounded. This profile is not presented as an arbitrary-prop planner.

Additional profiles should come from future proven creation gauntlets or other grounded deterministic routes rather than from speculative generic prose recipes.

## Maximum-quality truth boundary

For this hard-surface crate profile, quality `>= 0.92` requires the exact future operation:

`creative.mesh-model-finish.bevel`

That hand is not currently present in the public Creative Hands catalog. Therefore a `maximum` request currently returns `HOLD_CAPABILITY_GAP` unless the caller explicitly allows quality degradation. With `allow_quality_degrade: true`, the resolver searches downward in 0.01 quality increments and returns the highest executable/budget-fitting realization while preserving the original requested quality in the result.

The missing-hand result includes an `axm.creative-capability-gap/v1` contract suitable as explicit future gap/Forge input. Wave 13 does not auto-install or self-canonize a replacement hand.

## Machine policy

Adaptive requests can bound:

- `max_steps`;
- `max_work_units`;
- `max_state_bytes`;
- `time_budget_ms`;
- observed `work_units_per_ms`;
- planned `concurrency`;
- explicit `allow_quality_degrade`.

A time budget without observed throughput returns `HOLD_CALIBRATION_REQUIRED`. The resolver does not guess machine speed.

Work units are deterministic planning weights, not milliseconds. State bytes are profile estimates used for preflight, not a claim that a future runtime allocation will exactly equal the estimate.

## Scheduler

The resolver derives dependencies from retained `$state` references, then emits bounded concurrency groups. The schedule reports:

- serial work units;
- concurrency-limited groups;
- a theoretical parallel work-unit floor.

**Wave 13 does not execute those groups in parallel.** The existing Creative Flow executor remains serial and authoritative. Time-budget acceptance therefore uses serial work. `parallel_runtime` is explicitly `PLANNED_NOT_EXECUTED` until a real worker runtime is connected and tested.

This distinction lets machine speed and future parallel execution improve without rewriting canonical creation state or pretending an unimplemented speedup already exists.

## Public modes

The existing `creative-flow` live capability and `PlatformHands.creativeFlow` service gain:

- `adaptive-plan` — resolve profile, quality, budgets, missing operations and schedule without executing;
- `adaptive-execute` — explicitly authorize execution of the resolved plan through the same existing Creative Flow transaction.

Ordinary `plan` mode remains unchanged: arbitrary prose without explicit steps still returns `HOLD_PLAN_REQUIRED`.

## Agency and continuity

Adaptive execution is explicit. Quality degradation is off by default. A profile cannot silently broaden itself to an unknown goal. The supplied canonical state is still cloned into candidate state; held or failed work does not partially publish final state.

## Verification

`creative-quality-resolver-selftest.js` proves:

- continuous/alias quality normalization;
- unsupported goals HOLD;
- 3 / 18 / 32 / 47-step depth growth across the proven profile;
- dependency-derived concurrency groups;
- current maximum-quality bevel gap;
- explicit degradation below that gap;
- step-budget adaptation;
- throughput/time-budget adaptation where a faster calibrated machine can realize at least as much quality as a slower one;
- `HOLD_CALIBRATION_REQUIRED` when time is supplied without observed throughput;
- real `adaptive-execute` through the same Creative Flow executor, including a degraded execution.

`tests/test_creative_flow.py` separately proves the adaptive modes cross the ordinary `UniversalCreationMachine.create(kind="creative-flow")` live-capability bridge.
