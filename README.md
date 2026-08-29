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

### Run

```bash
PYTHONPATH=src python -m axm_uc inspect
PYTHONPATH=src python -m axm_uc create examples/requests/create_hello.json
PYTHONPATH=src python -m axm_uc create examples/requests/gap_markdown.json
PYTHONPATH=src python -m axm_uc candidate test capabilities/candidates/AXM-CAP-WRITE-MARKDOWN.json
python tools/build.py
```

The Markdown example intentionally begins as a gap. The candidate demonstrates the smallest justified growth in this case: reuse the exact text writer and add an inspectable Markdown route rather than inventing a duplicate writer.

## Status

**SEED / EXPERIMENTAL**

No claim of universal creation is made. The name describes the direction of the experiment, not a completed capability.

Mike - Axiom/Mir
