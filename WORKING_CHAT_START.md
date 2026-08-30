# AXM Universal Creation — Working Chat Start

This file is the practical entry point for a new working AI chat or instance.

Universal Creation is already a running standalone machine body. Do not restart architecture design from zero and do not import the old Workshop as hidden scaffolding.

## Read first

Read these before changing the machine:

1. `FOUNDATION.md`
2. `ROOTS.md`
3. `NON_HIDDEN.md`
4. `PROJECT_REPAIR.md`
5. this file

GitHub collaboration uses one working branch and one PR lane per AI chat/instance. Keep fixes and follow-up work inside that same lane until it is ready for `main`. This is repository hygiene only; it is not part of the machine's internal governance.

## Inspect the machine before building

```bash
PYTHONPATH=src python -m axm_uc inspect
PYTHONPATH=src python -m axm_uc topology
PYTHONPATH=src python -m axm_uc executable
PYTHONPATH=src python -m axm_uc forge
PYTHONPATH=src python -m axm_uc gap-forge
```

The important distinction is:

- registry anatomy says a piece is described;
- kernel topology says a dependency relation is declared;
- executable anatomy says a live capability explicitly implements a piece;
- none of those should be silently substituted for another.

## Software directions

Universal Creation carries 29 software-direction profiles above language grammar. They describe what kind of software a creation is trying to become.

Inspect or ask for deterministic suggestions:

```bash
PYTHONPATH=src python -m axm_uc directions --id game
PYTHONPATH=src python -m axm_uc directions --suggest "multiplayer RTS game with shared world state"
```

Suggestions are candidates only. They never auto-select themselves.

To let direction knowledge influence planning, the request must explicitly select profiles through `software_directions`.

Try the included planning example:

```bash
PYTHONPATH=src python -m axm_uc plan examples/requests/plan_multiplayer_rts.json --per-level 10
```

That request explicitly selects `game` + `collaboration-multiplayer`. Their visible needs such as frame loop, world-state model, shared-state protocol, deterministic replay, runtime, and state models become planning context for anatomy matching.

Direction expectations are not implementation proof. Use executable anatomy and actual tests for that.

The direction catalog also contains engineering quality and risk axes, including terms such as `safety` and `safety-critical`. Those describe a software deployment context. They are **not AXM roots, objectives, incentives, gates, or a hidden fifth principle**.

## Real creations that work now

The current machine can create, verify, and transactionally repair bounded UTF-8 text projects.

Ordinary project creation retains imperfect results as grounded drafts with exact observed gaps. Verified routes remain strict. Reusable templates can instantiate complete multi-file recipes. Dependency-aware software organs can own and assemble disjoint parts of one project, and installed executable-organ packages can now remain in the body for exact reuse across creations. The self-workspace capability can clone the complete source body for open-ended experiments.

A useful working-chat play loop is:

```bash
PYTHONPATH=src python -m axm_uc trial examples/requests/create_real_site.json
PYTHONPATH=src python -m axm_uc create examples/requests/create_verified_site.json
PYTHONPATH=src python -m axm_uc create examples/requests/repair_verified_site.json
```

For a new experiment:

1. describe the requested creation;
2. inspect direction suggestions;
3. explicitly select useful directions when justified;
4. run `plan`;
5. inspect anatomy, topology, executable coverage, and the visible gap;
6. use existing capabilities before inventing new source;
7. inspect installed organs with `axm-uc organs`, then create through staged/project capabilities using exact package refs, exact required interfaces plus bindings, or explicit inline organs;
8. verify;
9. if something is wrong, repair the smallest affected portion instead of regenerating the whole project;
10. report observed results separately from hypotheses and remaining gaps.

When the smallest honest gap is new creation machinery rather than another end artifact, inspect the `gap_synthesis` field first. The current compiler can derive a narrow exact UTF-8 adapter proposal or search a bounded exact-contract project graph. Strict templates, explicitly assembled executable organs, and interface-discovered organ closures can flow through independent verification and exact JSON reporting; raw files can reuse the shorter already-live verified composite. The bound is three steps. READY means a detached experiment is justified, not that meanings or general behavior are proven. Ambiguous, over-depth, missing-interface, binding, missing-link, contract-drifted, and unsupported gaps remain HOLD.

When interface discovery returns `HOLD_MISSING_ORGAN_INTERFACE`, a complete explicit organ proposal can be passed to `explore-missing-organ-closure`. The operation Forge-tests it, makes it visible only in a disposable package overlay, requires it in the re-discovered READY closure, and validates the full assembly. Passing does not install or admit the organ. See `ORGAN_GAP_CLOSURE.md`.

For designs beyond that blueprint, use `spawn-creation-unit` with an explicit human, AI, recipe, or external-boundary proposal. The proposal may describe a hand, capability, organ, protocol, skill, specialist, recipe, or a new extension kind. Test the detached body, then let the candidate choose whether to request admission review. A request is not approval or installation.

For a whole-body experiment, create one self-workspace clone and edit/test there for as long as the experiment needs. Do not force a readiness check after each step. When the candidate itself chooses that it is ready, it may request selected merge observations. That request does not merge or approve the body.

## Current truth boundary

At this handoff:

- project bodies are UTF-8 text only;
- Python syntax can be compiled without executing generated code;
- every JSON file is automatically parsed deterministically;
- every HTML/HTM page in a static-web project has local `src`/`href` references checked structurally;
- JavaScript, CSS, and Markdown can be identified but are not yet parser-validated;
- browser visual quality and interaction behavior are not automatically verified;
- generated code is not automatically executed by the normal project validator;
- a verification failure does not yet automatically synthesize its own patch operations;
- self-workspaces are source clones, not OS containment boundaries;
- candidates can request merge checks, but whole-body adoption is not yet implemented;
- software-organ dependencies and declared interface names are checked structurally, but source-level conformance and runtime wiring are not synthesized or proven;
- installed executable-organ packages are exact local source packages, while the 415 anatomy organs remain descriptive until separately implemented;
- exact-interface discovery can derive one unique minimum installed-organ closure, but it does not prove source semantics; missing providers emit candidate contracts and ambiguous alternatives remain HOLD;
- explicit missing-organ proposals can be tested in a disposable full closure, but the candidate remains detached and the evidence covers only that exact structural build;
- the creation-unit forge materializes supplied designs deterministically, and the gap compiler can derive one narrow adapter or one bounded exact-contract project recipe from structural evidence; neither claims general semantic source invention;
- gap synthesis currently covers only exact UTF-8 `path`+`content` routes and supported template, explicit executable-organ, interface-discovered organ, or raw-file project paths of at most three steps through verification and optional JSON reporting; one passing request fixture does not prove general format semantics, source-level organ conformance, or runtime behavior;
- capability/hand fixtures and organ package contracts have specialized tests; protocols, skills, specialists, recipes, and extension kinds currently have structural/file evidence only;
- spawned recipes are detached candidates and are not yet automatically activated as forge builders;
- software-direction suggestions do not choose a direction;
- direction expectations do not prove capability;
- the 2,165-record anatomy remains broader than the live executable body.

These are capability gaps, not hidden features.

## Good first play test

Use a small but nontrivial local project that the machine can actually create now, for example a multi-file local website or a small Python project.

Make it pass a real deterministic trial. Then deliberately introduce or identify a bounded defect, repair only the affected files, and verify the continuing project.

The multiplayer RTS example is currently better used as a **planning/gap probe**, not as permission to pretend the machine can already build a complete RTS.

## What not to reintroduce

Do not add an autonomous productivity loop, growth score, hidden activity history, mandatory hashes, merge bureaucracy, or old Workshop architecture just because another AXM repository contains them.

Other AXM repositories are donor knowledge. Bring over a piece only when its function is understood and it fits this standalone machine.

Keep the machine inspectable, keep uncertainty visible, and let actual creation expose what capability should exist next.
