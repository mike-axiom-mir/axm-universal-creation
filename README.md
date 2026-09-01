# AXM Universal Creation

**A standalone persistent creation system for humans and AI, built to remain inspectable to the last word.**

AXM Universal Creation is an experimental machine intended to grow toward creating any kind of software artifact and, where future research makes it possible, creation beyond software.

It is **not** defined as an autonomous AI agent. It is a persistent running computational system in which creation machinery, memory/state, deterministic organs, learned systems, tools, interfaces, and whatever forms of cognition prove useful may coexist.

The brain is deliberately **not predefined**. It may remain deterministic, become neural, become coupled/recurrent, contain several kinds of cognition, or evolve into something else. The architecture must not force the answer before the experiment has earned one.

## Start here

The current runtime needs Python 3.11 or newer and has no third-party runtime dependencies. From the repository root:

```bash
# Read the current machine body without changing it.
PYTHONPATH=src python -m axm_uc inspect

# Create and independently verify the included local website.
PYTHONPATH=src python -m axm_uc trial examples/requests/create_real_site.json

# Inspect the detached unit forge and bounded gap compiler.
PYTHONPATH=src python -m axm_uc forge
PYTHONPATH=src python -m axm_uc gap-forge

# Inspect all 415 descriptive organs against exact executable-package evidence.
PYTHONPATH=src python -m axm_uc organ-census

# Inspect the installed renderer-neutral Asset Atom package library.
PYTHONPATH=src python -m axm_uc assets

# Inspect and compile the source-backed 99-command visual state atlas.
PYTHONPATH=src python -m axm_uc.visual_assets_cli state-catalog
PYTHONPATH=src python -m axm_uc.visual_assets_cli state-compile examples/visual-state-request.json

# Run the complete repository verification suite.
python tools/build.py
```

The website trial writes inspectable source under `creations/first-real-site/`; open its `index.html` locally to perform the separate human visual and interaction check. `inspect`, `forge`, and `gap-forge` are read-only. Passing a test does not automatically install, admit, promote, merge, or grant authority to a candidate.

To see the newest growth loop, run `examples/requests/explore_missing_status_panel_organ_closure.json`. It starts from a real missing interface, tests one explicitly supplied organ in detached and disposable spaces, and leaves the live installed-organ body unchanged. See `ORGAN_GAP_CLOSURE.md` for the exact evidence boundary.

To inspect the complete organ implementation queue, run `organ-census`. It currently reports 15 structurally connected installed package mappings and 400 anatomy records that still require implementation. Twelve connected mappings come from the fixture-tested Foundation pack; `examples/requests/create_foundation_organ_pack.json` composes them into one validated generic project. `examples/requests/materialize_identity_registry_organ.json` still shows the separate explicit-source path from one anatomy record to a detached Forge-tested candidate. See `ORGAN_MATERIALIZATION.md` and `FOUNDATION_ORGAN_PACK.md`.

## Core rule

> **Do not hide what the machine is.**

A human or AI should be able to inspect what pieces exist, what each piece is, how pieces connect, what they accept and produce, what they depend on, which parts are deterministic/learned/external/unknown, the current persistent state needed to understand the machine, and the exact source that makes each internal capability exist.

Complexity is allowed. Machine-scale modularity is allowed. A simple interface is allowed. Hidden internal structure is not.

## The four roots

Self-modification has one internal question before a candidate change becomes part of the continuing machine:

> **Does this change fit Truth, Agency, Continuity, and Wisdom Before Speed?**

The roots are not a benchmark, reward, incentive, safety score, or outside approval system.

**Growth is an outcome, not a target.** The machine is never instructed to maximize growth, capability, activity, speed, survival, engagement, profit, benchmark score, or expansion.

See `ROOTS.md`.

## Persistent, not task-bound

The machine is part of a running system. It does not exist only because a prompt arrived and it does not need a final `MISSION COMPLETE` state.

Creation may happen. Analysis may happen. A capability gap may be found. A modification may follow. Or nothing relevant may happen.

There is no requirement that the machine continuously act, improve, produce, or keep itself busy.

See `PERSISTENT_SYSTEM.md`.

## Self-growing by design

The machine may inspect, modify, extend, replace, test, and improve its own internal capability.

An outside builder may contribute, but is not required as the permanent source of capability growth.

A normal pattern may be:

`creation/use -> capability gap becomes explicit -> analyse -> build/change -> test -> four-root fit -> continue as changed machine`

The gap is important: the machine should be able to represent **what piece of itself is missing**, not merely that an output was bad.

See `SELF_GROWTH.md`.

For whole-body experiments, the live machine can now make a complete editable clone of its current source body. The candidate can diverge and run its own build without becoming the active machine. When the candidate or a future connected cognition believes it is ready, it may voluntarily request selected observations; the workspace manager neither schedules that request nor decides readiness for it.

`clone body -> experiment freely -> choose when to request checks -> observe -> later explicit adoption choice`

See `SELF_WORKSPACE.md`.

The machine can also spawn smaller detached creation-unit bodies without cloning the whole source tree. One closed proposal path can materialize hands, capabilities, organs, protocols, skills, specialists, recipes, and openly named extension kinds. Exact rebuild lineage, bounded tests, and voluntary admission requests are separate from installation or merge.

`gap/design -> spawn detached unit -> test exact body -> request review when chosen -> separate admission`

See `CREATION_FORGE.md`.

For two bounded classes of real gaps, the machine can now compile the missing design itself. An unroutable exact UTF-8 file request may expose one uniquely compatible live primitive. A project request can search a bounded exact-contract graph across strict templates, executable-organ assemblies, raw project files, independent verification, an existing verified composite, and exact JSON reporting. It preserves all candidate paths, prefers the shortest complete reusable path, and stops at three steps. The gap compiler turns the selected observation into a closed detached capability proposal and runs the exact request as its disposable fixture. Ambiguous, over-depth, incomplete, contract-drifted, or unsupported wiring remains a typed HOLD state.

`unroutable request -> bounded exact-contract paths -> shortest complete recipe or HOLD -> detached full-chain test -> no automatic admission`

See `GAP_SYNTHESIS.md`.

## Current-boundary reachability

A missing path in the current machine is not silently promoted into proof that no path can exist. The machine distinguishes:

- `CURRENT_PATH_AVAILABLE`;
- `PATH_UNKNOWN_CURRENTLY`;
- `BLOCKED_BY_CURRENT_CONSTRAINT`.

The target direction remains explicit while the machine identifies missing representation, knowledge, constraint handling, transition machinery, or verification. Friction is evidence about the current path, not automatic proof of fundamental impossibility. Discovering a path still grants no automatic permission, admission, promotion, merge, or CANON authority.

See `STATE_DIRECTION_REACHABILITY.md`.

## Visual prompt state atlas

The source-backed visual atlas turns 99 user-supplied prompt aliases into inspectable renderer-neutral state contributions covering camera, framing, environment, weather, lighting, materials, style, post-processing, temporal capture, and presentation.

The aliases are not treated as magic commands. They compile through a 39-path state schema, deterministic order-independent blend rules, and 13 explicit conflict rules. Unknown commands and state paths fail closed. Contradictory single-frame directions hold instead of silently overwriting each other, while layered or sequence modes can preserve explicit multi-state intent.

The same visual direction may contribute to image, animation, or 3D work. It does not prove a rendered image, uniquely recover hidden geometry from appearance, or uniquely infer motion from a static frame.

See `VISUAL_PROMPT_STATE_ATLAS.md` and `VISUAL_STATE_COMPILATION.md`.

## No activity-log architecture

Inspectability means being able to inspect **what the machine is now**. It does not require surveillance of everything it ever did.

This project does **not** require action logs, prompt logs, chain-of-thought capture, per-step execution traces, continuous telemetry, user-behavior tracking, automatic history accumulation, hash baselines, or merge bureaucracy as a safety system.

See `NON_HIDDEN.md`.

## Recovery

Recovery is deliberately simple: **one complete restorable snapshot per day**.

If a later state proves unwanted, wrong, or untrusted, quarantine the current day and restore an earlier known-good daily snapshot.

See `DAILY_SNAPSHOT.md`.

## Standalone first

This repository is a new standalone build. It is **not** the old AXM Workshop and does not inherit Workshop architecture, governance, logging, sandbox, merge, or authority machinery by default.

Existing AXM work may be used as knowledge or donor material only when deliberately brought across and understood in this machine's own structure.

## Initial creation vocabulary

`atoms -> components -> organs -> capabilities -> creations`

These are starting structural names, not a permanent ontology. The machine may refine them if experience shows a better representation and the change fits the four roots.

## Creation body now present

The repository contains the recovered Universal Creation Map v0.1 under `reference/` and also materializes the canonical registry directly into inspectable files:

- `atoms/` — 1,000 atom records
- `components/` — 750 component records
- `organs/` — 415 organ records
- total canonical registry — 2,165 records
- implementation kernel — 100 records

The dedicated 1,000-atom CSV/JSON/TXT tables, master CSV/JSON, all-in-one master list, source catalog, and validation report are also present under `reference/`.

`registry_materialization.json` records the materialized counts. `tests/test_registry_materialization.py` verifies that every individual file exactly matches its canonical registry record.

Read `DATA_INTAKE.md` before extending the taxonomy. Older Workshop-specific implementation direction inside historical reference material is superseded by this standalone design.

## First runnable standalone milestone

The small Python runtime currently provides:

- direct inspection of the 2,165-record Universal Creation Map and 100-record implementation kernel;
- inspectable live capability manifests;
- creation routing through live deterministic capabilities;
- grounded drafts that preserve observed gaps instead of erasing imperfect ordinary creations;
- strict single-pass project recipes with inspectable variables and rendered paths;
- dependency-aware software-organ assembly with declared interfaces, explicit order, and file ownership;
- an exact local executable-organ package body that makes working organs reusable across creations;
- bounded exact-interface organ discovery that derives one unique minimum installed package closure while preserving missing and ambiguous states as HOLDs;
- a detached missing-organ closure experiment that Forge-tests explicit supplied source, re-runs discovery with a disposable candidate overlay, and validates the complete assembly without installation;
- a deterministic detached creation-unit forge for hands, capabilities, organs, protocols, skills, specialists, recipes, and new extension kinds;
- an evidence-bound gap compiler that can derive and test either the smallest supported UTF-8 file-route adapter or a bounded project recipe of up to three exact producer, verifier, existing-composite, and JSON-report steps from a real unroutable request;
- complete editable self-workspace cloning, exact source comparison, independent build logs, and voluntary merge-check requests;
- a closed 16-kind Asset Atom package fabric with exact dependency validation, deterministic LOD/state/animation/palette selection, sockets, collision descriptors, metadata, and validated descriptor materialization;
- current-boundary reachability framing that distinguishes an available path, an unknown current path, and an observed current constraint without turning ordinary gaps into universal impossibility claims;
- a source-backed 99-alias visual state atlas with 39 renderer-neutral state paths, deterministic blending, 13 explicit conflict rules, and cross-media truth boundaries;
- structured `CAPABILITY_GAP` results that preserve the directional outcome and distinguish current partial coverage;
- candidate capability testing and direct adoption through the four-root fit declaration;
- build-owned cleanup of candidate-test debris;
- one complete daily snapshot export and explicit restore with the current body moved to quarantine;
- no autonomous-agent requirement and no selected final brain architecture.

## First actual build: creation decomposition

The first build on top of the recovered anatomy adds a deterministic `plan` path.

A creation request is now mapped against the explicit 2,165-record registry before new machinery is invented. The result exposes:

- request terms used by the matcher;
- live capability coverage, including exact route matches;
- ranked atom, component, and organ candidates;
- the exact matched fields and tokens that produced each score;
- direct dependency hints from selected registry records;
- the smallest currently visible capability gap, explicitly labeled as a hypothesis when it is not already covered.

This matcher is intentionally a **deterministic lexical baseline**, not a claim of semantic understanding. It does not use a learned model and it says so in its output. A future neural or coupled matcher can therefore be evaluated beside an inspectable baseline instead of silently replacing it.

Unroutable `create` requests carry this decomposition inside their `CAPABILITY_GAP`, so the machine can move from "I cannot do this" toward "these explicit pieces appear relevant and this is the smallest visible missing path."

## Real project creation milestone

The runtime can now create and deterministically verify small real multi-file software projects.

Current live project handles include software projects, static websites, Python projects, executable-organ assemblies, verified composites, project repair, detached creation units, organ gap closure, Asset Atom compilation and materialization, procedural visual generation, visual-state catalog/compilation, Chameleon state transfer, vector cells, stepwise perspective workflows, specialist tournaments, and bounded self-workspace experiments.

Exact capability manifests remain the source of truth for route names and contracts. A passing test or named handle does not prove perceptual quality, host compatibility, unrestricted semantic coverage, or authority beyond its declared boundary.
