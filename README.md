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

Current live project handles:

- `software-project`
- `static-web-project`
- `python-project`
- `verify-project`
- `templated-software-project`
- `templated-static-web-project`
- `templated-python-project`
- `self-candidate-project`
- `organ-software-project`
- `organ-static-web-project`
- `organ-python-project`
- `software-organ-assembly`
- `inspect-executable-organs`
- `list-executable-organs`
- `resolve-executable-organ`
- `test-executable-organ`
- `discover-organ-assembly`
- `interface-organ-project`
- `explore-missing-organ-closure`
- `inspect-organ-materialization`
- `prepare-organ-materialization`
- `materialize-organ-candidate`
- `spawn-creation-unit`
- `inspect-spawned-unit`
- `test-spawned-unit`
- `request-unit-admission-check`
- `analyze-creation-gap`
- `propose-gap-candidate`
- `explore-gap-candidate`
- `inspect-asset-atom-schema`
- `list-asset-packages`
- `inspect-asset-package`
- `validate-asset-package`
- `compile-asset-package`
- `materialize-asset-package`

Project creation is staged before publish and project-relative file paths may not escape the project body. Plain project creation defaults to `grounded-draft`: exact publication integrity is required, while failed quality/grammar checks remain visible and the imperfect creation survives. Explicit `validated` mode and verified composite handles remain strict and do not publish a failed body.

Current deterministic project checks:

- `file-exists`
- `file-absent`
- `nonempty`
- `contains`
- `not-contains`
- `line-count`
- `byte-size`
- `sha256`
- `json-valid`
- `json-value`
- `file-set`
- `python-compile`
- `html-local-links`
- `css-local-links`
- `javascript-local-imports`

Every project automatically receives a no-symlink boundary check so validation cannot silently read through a project link into an outside file. `static-web` automatically checks for `index.html`, verifies local `src`/`href` references from every `.html` and `.htm` page, resolves CSS `url(...)` and `@import` references, and resolves local static/dynamic JavaScript module imports. Bare JavaScript package imports and explicit external URLs remain labeled external rather than being claimed as locally verified. `python` automatically compiles `.py` files for syntax without executing them.

Every `.json` file is automatically parsed for JSON validity in every project type.

Reusable project templates use strict `[[AXM:name]]` placeholders in paths and contents. Substitution is exact, raw, single-pass, and non-recursive; missing, unused, malformed, colliding, and escaping inputs are rejected. See `PROJECT_TEMPLATES.md` and `GROUNDED_CREATION.md`.

Software-organ assembly composes several versioned template organs through an explicit dependency graph. Organs may be supplied inline, resolved from the separate `executable-organs/` body through an exact `id@version` reference, or discovered from exact required interfaces plus caller-supplied bindings. Interface discovery selects only one uniquely smallest complete installed package closure; missing providers emit organ contracts and equally small alternatives HOLD. One explicit human/AI/recipe organ proposal can now be Forge-tested against such a missing contract, made visible only in a disposable exact library overlay, and required to participate in a validated full closure build. It remains detached afterward. Declared `provides`/`requires` interfaces must resolve through the graph, every rendered file has one visible organ owner, and missing dependencies, cycles, interface gaps, binding drift, package overrides, and ownership collisions are rejected before publication. Declared interface resolution does not yet prove source-level conformance. See `ORGAN_ASSEMBLY.md`, `EXECUTABLE_ORGANS.md`, and `ORGAN_GAP_CLOSURE.md`.

Every project file receipt now includes its SHA-256 content digest. The independent `trial` pass rechecks those exact observed digests, so direct, templated, and organ-based creations receive the same second-body integrity observation. This is artifact evidence, not a required global machine hash baseline.

The `trial` command ties the current loop together:

`PLAN -> CREATE -> POST-CREATE VERIFY -> PASS / GAP`

Run the included first real creation trial:

```bash
PYTHONPATH=src python -m axm_uc plan examples/requests/create_real_site.json
PYTHONPATH=src python -m axm_uc trial examples/requests/create_real_site.json
PYTHONPATH=src python -m axm_uc create examples/requests/verify_real_site.json
PYTHONPATH=src python -m axm_uc create examples/requests/create_templated_site.json
PYTHONPATH=src python -m axm_uc create examples/requests/create_organ_site.json
PYTHONPATH=src python -m axm_uc create examples/requests/create_reusable_organ_site.json
PYTHONPATH=src python -m axm_uc create examples/requests/explore_interface_discovered_organ_report_gap.json
PYTHONPATH=src python -m axm_uc create examples/requests/explore_missing_status_panel_organ_closure.json
PYTHONPATH=src python -m axm_uc create examples/requests/spawn_creation_protocol.json
PYTHONPATH=src python -m axm_uc create examples/requests/test_spawned_creation_protocol.json
PYTHONPATH=src python -m axm_uc create examples/requests/analyze_note_route_gap.json
PYTHONPATH=src python -m axm_uc create examples/requests/explore_note_route_gap.json
PYTHONPATH=src python -m axm_uc create examples/requests/analyze_verified_template_gap.json
PYTHONPATH=src python -m axm_uc create examples/requests/explore_verified_template_gap.json
```

That creates `creations/first-real-site/` with `index.html`, `style.css`, and `app.js`. Open `index.html` in a browser for the separate human/host visual and interaction test.

A passing deterministic trial proves what it actually checked. It **does not** claim that generated code was executed, that browser interaction was automatically observed, or that a created project is excellent. Those remain separate evidence layers.

## First missing-part build loop

Candidate capability manifests live under `capabilities/candidates/` and declare both their implementation and their tests.

The first included candidate adds deterministic slug/identifier creation. It is not counted as live until:

1. the candidate is tested;
2. the four-root declaration is reviewed;
3. the user explicitly adopts it.

```bash
PYTHONPATH=src python -m axm_uc test-candidate capabilities/candidates/AXM-CAP-CREATE-IDENTIFIER.json
PYTHONPATH=src python -m axm_uc adopt capabilities/candidates/AXM-CAP-CREATE-IDENTIFIER.json
```

Testing writes into a temporary directory and removes it in the same operation. Adoption is direct after a passing test and four-root fit declaration; it first ensures the day's recovery snapshot exists, then installs/registers the capability. It does not create a benchmark, reward loop, global merge gate, or automatic self-approval system.

## Self-modification loop

The machine may evolve one exact deterministic candidate through explicit operations:

- inspect a candidate's exact source and declared tests;
- modify that exact source with a bounded replacement;
- run the candidate's declared tests;
- create or reuse the day's whole-body recovery snapshot;
- adopt the tested candidate only if its tested content digest still matches;
- restore a whole prior machine body while quarantining the current body first.

Live handles:

- `inspect-self-candidate`
- `modify-self-candidate`
- `test-self-candidate`
- `adopt-self-candidate`
- `restore-self-snapshot`

A passing test is evidence, not authority. The machine does not choose a global growth target and does not automatically install every passing candidate. See `SELF_GROWTH.md`, `DAILY_SNAPSHOT.md`, and the capability manifests under `capabilities/live/`.

## Daily snapshots

```bash
PYTHONPATH=src python -m axm_uc snapshot --reason "manual checkpoint"
PYTHONPATH=src python -m axm_uc snapshots
PYTHONPATH=src python -m axm_uc restore snapshots/2026-08-29 --reason "restore known-good body"
```

At most one snapshot is made for a UTC day, it is never silently replaced, and restore moves the current body into `quarantine/` before replacement. Snapshot management ignores runtime output surfaces such as `snapshots/`, `quarantine/`, `candidate-tests/`, `creations/`, `.git/`, and cache directories.

## Current truth boundary

Implemented now:

- persistent standalone machine state;
- inspectable exact structure;
- exact deterministic registry decomposition baseline;
- dependency-aware creation topology;
- real deterministic project creation with configurable strict or grounded-draft publication;
- strict reusable project templates;
- reusable versioned executable-organ packages with exact reference resolution;
- exact-interface organ discovery with unique-minimum selection and explicit missing/ambiguous HOLDs;
- explicit supplied-organ gap closure through detached Forge test, ephemeral discovery, and disposable full assembly;
- explicit organ materialization census plus an exact-source package-to-Forge compiler;
- independently rechecked exact created-file digests;
- symlink-safe project validation;
- CSS and JavaScript local-reference validation;
- direct tested-candidate adoption after a daily recovery snapshot;
- full editable candidate-body clones with independent builds and voluntary check requests;
- detached creation-unit materialization for known and future unit kinds;
- bounded gap synthesis for exact UTF-8 route aliases and short exact-contract project recipes;
- closed renderer-neutral Asset Atom packages with deterministic compile/materialize behavior;
- one daily whole-body recovery snapshot;
- explicit self-modification operations;
- inspectable current truth and gaps;
- build-owned cleanup;
- no required agent architecture.

Not claimed:

- universal creation ability;
- autonomous semantic understanding;
- autonomous arbitrary code invention from a name;
- arbitrary semantic or computational gap synthesis;
- proof that a structurally compiled adapter has correct new-kind semantics;
- browser behavior from static validation;
- generated-code execution from Python compilation;
- automatic admission of candidates;
- a final brain design;
- self-improvement as an incentive or permanent objective.

## Current factual limitation

The machine is still small relative to its recovered map. Most registry records describe potential structure, not implemented capability. The point of the current foundation is to preserve that distinction while making the gap between the two explicit and buildable.
