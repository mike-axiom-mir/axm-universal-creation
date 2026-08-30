# AXM Universal Creation

**A standalone persistent creation system for humans and AI, built to remain inspectable to the last word.**

AXM Universal Creation is an experimental machine intended to grow toward creating any kind of software artifact and, where future research makes it possible, creation beyond software.

It is **not** defined as an autonomous AI agent. It is a persistent running computational system in which creation machinery, memory/state, deterministic organs, learned systems, tools, interfaces, and whatever forms of cognition prove useful may coexist.

The brain is deliberately **not predefined**. It may remain deterministic, become neural, become coupled/recurrent, contain several kinds of cognition, or evolve into something else. The architecture must not force the answer before the experiment has earned one.

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

Project creation is staged before publish. Project-relative file paths may not escape the project body. A failed deterministic validation does not publish the staged project.

Current deterministic project checks:

- `file-exists`
- `nonempty`
- `contains`
- `json-valid`
- `python-compile`
- `html-local-links`

`static-web` automatically checks for `index.html` and verifies local `src`/`href` references from every `.html` and `.htm` page in the project. `python` automatically compiles `.py` files for syntax without executing them.

Every `.json` file is automatically parsed for JSON validity in every project type.

The `trial` command ties the current loop together:

`PLAN -> CREATE -> POST-CREATE VERIFY -> PASS / GAP`

Run the included first real creation trial:

```bash
PYTHONPATH=src python -m axm_uc plan examples/requests/create_real_site.json
PYTHONPATH=src python -m axm_uc trial examples/requests/create_real_site.json
PYTHONPATH=src python -m axm_uc create examples/requests/verify_real_site.json
```

That creates `creations/first-real-site/` with `index.html`, `style.css`, and `app.js`. Open `index.html` in a browser for the separate human/host visual and interaction test.

A passing deterministic trial proves what it actually checked. It **does not** claim that generated code was executed, that browser interaction was automatically verified, that visual quality was judged, or that every semantic user requirement was satisfied.

See `REAL_CREATION_TRIAL.md` for the working-chat protocol and exact truth boundary.

## Anatomy / kernel topology bridge

The 2,165-record master anatomy is broad but currently flat: it contains zero dependency edges and zero relationships. The separate 100-record implementation kernel contains 175 declared dependency edges, all of which resolve internally.

The runtime now connects the two conservatively without editing the master map or inventing edges. A master record becomes a traversable kernel seed only when its normalized name exactly matches one unique kernel record at the same anatomy level. Weaker correspondences remain visible suggestions and are never traversed as facts.

Current measured bridge coverage:

- 104 master records have a traversable exact crosswalk;
- those exact mappings reach 94 of the 100 kernel records;
- 0 exact mappings are ambiguous;
- 2,061 master records remain explicitly unresolved.

The planner keeps its top-level truth label `DETERMINISTIC_LEXICAL_BASELINE`; kernel topology is reported separately so attaching a dependency graph does not pretend the lexical matcher became semantic intelligence.

Inspect the bridge directly:

```bash
PYTHONPATH=src python -m axm_uc topology
PYTHONPATH=src python -m axm_uc topology --master-id AXM-02-DATA-MATH-C-012-graph --depth 4
PYTHONPATH=src python -m axm_uc plan examples/requests/plan_graph.json --per-level 8
```

See `TOPOLOGY.md` for the measured baseline, crosswalk rule, truth boundary, and graph example.

### Core commands

```bash
PYTHONPATH=src python -m axm_uc inspect
PYTHONPATH=src python -m axm_uc topology
PYTHONPATH=src python -m axm_uc plan examples/requests/plan_mesh.json
PYTHONPATH=src python -m axm_uc create examples/requests/create_hello.json
PYTHONPATH=src python -m axm_uc trial examples/requests/create_real_site.json
PYTHONPATH=src python -m axm_uc candidate test capabilities/candidates/AXM-CAP-WRITE-MARKDOWN.json
python tools/build.py
```

The Markdown example intentionally begins as a gap. The candidate demonstrates the smallest justified growth in this case: reuse the exact text writer and add an inspectable Markdown route rather than inventing a duplicate writer.

GitHub collaboration uses one branch/PR lane per AI chat or instance by default; see `AGENTS.md`. That convention is repository hygiene, not machine architecture.

## Status

**SEED / EXPERIMENTAL**

No claim of universal creation is made. The name describes the direction of the experiment, not a completed capability.

Mike - Axiom/Mir
