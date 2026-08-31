# Context-Learning Specialist Tournament

## Shared multi-perspective body

`AXM-CAP-SPECIALIST-TOURNAMENT@0.2.0` is the live multi-perspective orchestration body.

It owns two related handles families:

```text
specialist-tournament
```

for broad parallel team competition, and:

```text
stepwise-workflow
```

for repeated perspective checks around an evolving small-step workflow.

The shared body keeps perspective selection, contextual fit history, and challenge matching in one place instead of creating duplicate coordination systems.

Implementation is split across:

- `src/axm_uc/specialist_pool.py` for pools, teams, rankings, finalist votes, and fit history;
- `src/axm_uc/stepwise_workflow.py` for explicit plans, checkpoints, actions/results, splitting, replanning, and chronology;
- `src/axm_uc/__init__.py` for the deterministic dispatch between those two modes.

## Specialist pool

The current pool supports:

- 20 reusable universal perspectives;
- up to 20 challenge-matched specialists derived from the master registry;
- maximum pool size 40.

Each specialist exposes detailed working-method fields including temperament, core question, strength, blind spot, evidence preference, novelty bias, risk posture, time horizon, scale preference, disagreement style, communication pattern, challenge behavior, synthesis role, and domain focus when registry-derived.

These are method/personality overlays. They are not claims of separate identity, consciousness, execution authority, or automatic expertise.

## Tournament loop

```text
need
-> build contextual specialist pool
-> read contextual +1 history
-> form best team
-> form middle team
-> form lowest-third challenger
-> form mixed-random challenger
-> add bounded deterministic combinations
-> issue isolated parallel challenge packets
-> external executors do the actual work
-> independently judge every generated team
-> show exactly two finalists
-> explicit finalist vote
-> each winning member receives +1
-> persist contextual and global fit evidence
```

Team size is 3..6 and one tournament may generate up to 512 teams.

With the default 32-person pool and four-person teams, the raw combination space is:

```text
C(32,4) = 35,960
```

The engine records that space but does not pretend all combinations were executed when the explicit bound is smaller.

## Best, middle, low, and mixed challengers

Historical fit influences team construction, but the field deliberately keeps different exposure bands alive:

- best-evidence team;
- middle-evidence team;
- lowest-third challenge team;
- mixed-random team;
- additional deterministic combination teams.

The mixed-random path is reproducible by default because the seed derives from the challenge digest. An explicit seed can deliberately produce another shuffle.

This prevents early winners from becoming a permanent closed club.

## Parallel truth boundary

Every generated team receives the same challenge under isolation.

The deterministic tournament engine does not claim the team reasoned merely because a packet exists. A human, local model, connected model, future cognition organ, or another explicit executor must actually produce the submission and evidence.

Incomplete judging stays incomplete.

Only a fully judged field exposes two finalists.

## +1 contextual fit voting

After the best two are shown, one exact finalist team can be selected by explicit vote.

Each winning member receives:

- `+1` in the matched challenge context;
- `+1` in global historical fit.

The ledger also tracks appearances and finalist appearances.

Duplicate voting on the same ranking cannot farm extra points.

Persistent history lives at:

```text
state/specialist-fit.json
```

`+1` means only:

> This specialist participated in the explicitly selected winning team for this judged challenge context.

It is not a global intelligence score, identity value, authority grant, CANON promotion, permission change, or growth reward.

## Context matters

A specialist may accumulate strong evidence for rendering-shaped challenges while remaining unproven for database, networking, economic, or other challenges.

Context fit is therefore preferred over global popularity when building the current best-evidence team.

Low or zero points can also mean under-exposure rather than poor capability, which is another reason low/middle/mixed challengers stay in circulation.

## Connection to stepwise workflow

The same contextual specialist pool is reused inside `stepwise-workflow`.

Instead of competing only once over an entire problem, a small panel is selected before and after each meaningful step from different historical positions:

- best-fit;
- middle-fit;
- lowest-third;
- deterministic-random when available.

That lets the machine repeatedly ask different eyes whether the next step is still too broad, wrongly ordered, unsupported, or ready to continue.

See `STEPWISE_PERSPECTIVE_WORKFLOW.md`.

## Existing anatomy made executable

The shared orchestration body live-backs:

- `AXM-19-AI-ML-AGENTS-O-021-specialist-summoner`;
- `AXM-19-AI-ML-AGENTS-C-035-specialist-profile`;
- `AXM-24-WORKSPACE-COLLABORATION-O-006-project-planner`;
- `AXM-03-TIME-STATE-EVENT-O-007-workflow-engine`;
- `AXM-03-TIME-STATE-EVENT-C-015-workflow-step`.

## Truth boundary

The current implementation does not claim that tournament scores are objective truth, that every possible team was explored, that a prepared specialist packet contains real reasoning, that historical winners are universally superior, or that more perspectives always improve a result.

It provides a bounded, inspectable mechanism for repeatedly exposing work to different methods, comparing evidence, remembering explicit votes, and keeping challengers alive as the machine learns which perspectives tend to fit which kinds of problems.
