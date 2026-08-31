# Context-Learning Specialist Tournament

AXM Universal Creation can now prepare a large, inspectable pool of specialist working profiles around a concrete need, combine them into many competing teams, keep those teams isolated during parallel challenge work, expose the two best evidence-backed finalists, and remember an explicit final vote as contextual evidence about which specialists tend to fit which kinds of problems.

This capability is implemented by `AXM-CAP-SPECIALIST-TOURNAMENT@0.1.0` and `src/axm_uc/specialist_pool.py`.

It makes two existing Universal Creation Map records live-backed:

- `AXM-19-AI-ML-AGENTS-O-021-specialist-summoner`
- `AXM-19-AI-ML-AGENTS-C-035-specialist-profile`

## Core loop

```text
need
  -> build detailed specialist pool
  -> read contextual +1 vote history
  -> rank current fit evidence
  -> form best team
  -> form middle team
  -> form lowest-third challenger
  -> form mixed-random challenger
  -> sample many additional team combinations
  -> issue identical isolated challenge packets
  -> parallel work happens outside the deterministic tournament engine
  -> independently judge every team under declared criteria
  -> show best two teams
  -> explicit finalist vote
  -> each winning team member receives +1
  -> persist contextual and global fit history
  -> future tournaments use that evidence while still keeping challengers alive
```

## Specialists are detailed method profiles

A specialist profile is not merely a role name.

Each profile exposes fields such as:

- temperament
- core question
- strength
- blind spot
- evidence preference
- novelty bias
- risk posture
- time horizon
- scale preference
- disagreement style
- communication pattern
- challenge behavior
- synthesis role
- domain focus when the specialist comes from registry anatomy

These fields deliberately create working-personality differences. They are perspective and method differences, not claims of separate identity, consciousness, expertise authority, or independent execution.

## Universal pool

The current base contains twenty universal perspectives, including:

- System Architect
- Falsifier
- Wild Explorer
- Minimalist
- Performance Optimizer
- Adversarial Tester
- Human Use Specialist
- Maintainer
- Integrator
- Empiricist
- Contrarian
- Cross-Domain Translator
- Simulationist
- Boundary Keeper
- Repairer
- Cost Controller
- Visual Composer
- Reliability Engineer
- Accessibility and Inclusion Specialist
- Future Stress Tester

This avoids making every challenge depend only on keyword-matched domain experts.

## Need-derived specialists

For a normal 32-person pool, remaining positions are populated from the real master registry.

The challenge is tokenized and compared against registry IDs, names, definitions, domains, and domain codes. Matching records become bounded specialists whose focus remains tied to their exact registry reference.

Their personality style is assigned deterministically from the registry record ID so repeated runs remain reconstructable.

The result is a pool that changes with the need.

A rendering challenge can pull rendering/material/spatial records.

A data challenge can pull database, serialization, provenance, or state records.

A future unknown challenge can still use the universal perspectives even when no registry record matches strongly enough.

## Contextual +1 voting

The `+1` is historical voting evidence.

It is intentionally simple:

```text
winning finalist team member -> +1
```

Each winning member receives:

- `+1` global point
- `+1` point in the tournament's matched context

The ledger also records:

- tournament appearances
- finalist appearances
- context appearances
- context finalist appearances
- duplicate-safe vote receipts

Current persistent state:

`state/specialist-fit.json`

## Why context and global history are separate

A single global number would flatten different capabilities into one popularity contest.

Instead, ranking primarily looks at the challenge context.

A specialist may accumulate strong evidence for rendering problems and remain unproven for networking problems.

Global points remain visible as weaker cross-context history.

Zero points never means `bad` by itself. It can mean `not tested enough`.

That is why the system continues to form low-ranked, middle-ranked, and mixed teams even after historical winners emerge.

## Team tiers

Every prepared tournament attempts to preserve four special teams before sampling the larger combination space.

### Best evidence team

Members with the strongest current contextual/global finalist-vote history.

### Middle evidence team

A team drawn from the middle of current fit history.

This prevents the competition from collapsing into only champions versus complete newcomers.

### Lowest-third challenge team

A team drawn from the lowest-ranked third.

`Lowest` means lowest current evidence rank. It does not mean least intelligent or least valuable.

This team is deliberately retained so underexposed specialists can overthrow a stale ranking.

### Mixed random team

A deterministic RNG mixture containing top, middle, and low members when the pool permits it.

By default the RNG is seeded from the challenge digest, so the same challenge and state reconstruct the same field.

A caller may supply a different seed to deliberately reshuffle exploration.

## Combination search

The tournament also samples the wider team combination space.

For a 32-specialist pool with four-person teams:

```text
C(32, 4) = 35,960 possible teams
```

The current bounded implementation may generate up to 512 teams for one tournament.

The receipt records:

- total combination space
- number of generated teams
- explicit team-size bound
- deterministic random seed
- top/middle/lowest thirds
- each generated team and its members

If the possible combination space is larger than the configured bound, the engine deterministically samples combinations rather than pretending it evaluated every possible team.

## Parallel challenge packets

Every generated team receives the same challenge and criteria.

Packets explicitly state:

`solve independently; no other team's submission, ranking, or vote is visible before parallel challenge work is complete`

A packet asks for:

- proposal
- evidence
- dissent
- unknowns
- criterion notes

The deterministic engine does **not** fake these answers.

A human, connected model, local model, future cognition organ, or another executor may run the packets in parallel.

Until actual submissions exist, the tournament truth status remains preparation, not reasoning.

## Judging

Judging is separate from team work.

For every declared criterion, an independent judgement supplies:

- numeric score from 0 to 100
- non-empty evidence explaining that score

Default criteria are:

- evidence
- correctness
- gap discovery
- feasibility
- simplicity
- consequence awareness

Custom weighted criteria are allowed.

If even one generated team is missing its judgement, the result stays:

`PARTIAL_RANKING_NO_FINALIST_VOTE`

The machine does not pretend the observed subset contains the true best two.

Only a completely judged field can reach:

`AWAITING_FINALIST_VOTE`

## Top two are shown before the vote

A complete ranking exposes exactly two finalists.

No fit points have been awarded yet.

The final choice is a separate operation:

`record-finalist-vote`

The selected team must be one of those two exact finalists.

The ranking is digest-bound. Tampering with the tournament or ranking invalidates the vote path.

## Duplicate-safe voting

A completed ranking can create only one vote receipt.

Repeating the same winner returns the existing receipt without adding more points.

Trying to record a different winner for a ranking that already has a vote is rejected.

This prevents accidental or deliberate point farming.

## What +1 means

A +1 means:

> This specialist was a member of the explicitly selected winning team for this judged challenge context.

It does **not** mean:

- universally smartest specialist
- authority over other specialists
- proof every contribution from that specialist was correct
- proof of consciousness or identity
- permission change
- CANON promotion
- machine growth reward
- instruction to seek more points

The score exists to improve future perspective routing.

## Why winners do not monopolize the future

Historical winners influence the `best` team, but the field continues to contain:

- middle evidence teams
- lowest-third challengers
- mixed-random teams
- broad combination teams

So accumulated fit history creates memory without turning memory into permanent rule.

A low-ranked specialist can win later and immediately gain +1 evidence.

A specialist can also be strong in one context and weak or unknown in another.

## Current truth boundary

The tournament currently proves deterministic orchestration, scoring, finalist selection, and vote-history updates.

It does not prove that unexecuted specialist packets have reasoned.

It does not prove that the supplied judge is correct.

It does not claim the bounded team sample exhausts a larger combination space.

It does not turn personality profiles into autonomous identities.

It does not convert historical wins into authority.

The purpose is narrower and more useful:

> make many different perspectives available, repeatedly challenge the current favorites, and let explicit outcomes gradually teach the machine which specialist mixtures have worked best for which kinds of needs.
