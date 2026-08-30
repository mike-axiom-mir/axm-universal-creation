# AXM Universal Creation — Executable Anatomy and Composition

This layer separates **described anatomy** from **implemented capability**.

The broad registry can contain an atom, component, or organ without the machine being able to execute it. A kernel crosswalk can expose a declared dependency path without proving that path is live. A live capability is therefore connected to anatomy only through an explicit inspectable declaration.

## Current truth rule

A live capability may declare:

```json
"anatomy_refs": [
  {
    "id": "AXM-...",
    "role": "implements",
    "basis": "why this capability really implements this anatomy record"
  }
]
```

Allowed roles are:

- `implements` — counts as a live-backed anatomy implementation;
- `supports` — contributes to the anatomy but is not implementation proof;
- `uses` — consumes or delegates to that anatomy but does not claim to implement it.

Only an explicit, resolved `implements` declaration with a non-empty basis changes an anatomy record from `definition-only` to `live-backed`.

No lexical match, shared source key, similar name, kernel crosswalk, or planner score is allowed to manufacture implementation truth.

## Current live-backed anatomy

At this milestone the machine deliberately starts sparse:

- `AXM-24-WORKSPACE-COLLABORATION-C-010-project` is explicitly implemented by `AXM-CAP-WRITE-PROJECT`;
- `AXM-20-TESTING-OBSERVABILITY-C-015-validation-report` is explicitly implemented by `AXM-CAP-VERIFY-PROJECT`;
- `AXM-05-CODE-GRAMMAR-C-029-code-patch` is explicitly implemented by `AXM-CAP-PATCH-PROJECT`;
- `AXM-05-CODE-GRAMMAR-C-022-code-template` is explicitly implemented by `AXM-CAP-INSTANTIATE-PROJECT-TEMPLATE`;
- `AXM-24-WORKSPACE-COLLABORATION-C-011-workspace` is explicitly implemented by `AXM-CAP-SELF-WORKSPACE`;
- `AXM-05-CODE-GRAMMAR-C-025-dependency-graph` and `AXM-00-FOUNDATION-C-019-interface-contract` are explicitly implemented for declared software-organ assembly by `AXM-CAP-ASSEMBLE-ORGAN-PROJECT`.

The runtime reports the current counts rather than hard-coding a claim:

```bash
PYTHONPATH=src python -m axm_uc executable
PYTHONPATH=src python -m axm_uc executable --master-id AXM-24-WORKSPACE-COLLABORATION-C-010-project
PYTHONPATH=src python -m axm_uc executable --master-id AXM-20-TESTING-OBSERVABILITY-C-015-validation-report
```

`axm-uc inspect` also includes the executable-anatomy summary, and `axm-uc plan` returns a separate executable-anatomy view beside lexical matching and kernel topology.

The truth status of this layer is:

`EXPLICIT_LIVE_CAPABILITY_BINDINGS`

## First deterministic composite capability

The runtime now supports:

`DETERMINISTIC_COMPOSITE`

A composite capability is executable machinery described by its manifest. It can call existing live capabilities in visible ordered steps and bind request inputs or earlier step outputs into later steps.

The first live example is:

`AXM-CAP-BUILD-VERIFY-PROJECT`

It adds no bespoke Python function for the new route. Its manifest composes:

1. `AXM-CAP-WRITE-PROJECT`
2. `AXM-CAP-VERIFY-PROJECT`

The caller can therefore request:

- `verified-software-project`
- `verified-static-web-project`
- `verified-python-project`

and receive both the build result and the independent verification result through one live route.

Example:

```bash
PYTHONPATH=src python -m axm_uc create examples/requests/create_verified_site.json
```

This is the first small capability-fabric step: a new live route can exist as inspectable composition of existing live machinery instead of requiring a new source function for every combination.

## Binding language

Composite step inputs use explicit bindings:

```json
{"from": "request.path"}
{"from": "steps.build.path"}
{"from": "request.project_type", "default": "generic"}
```

A composite may return selected step outputs through the same binding mechanism.

Current composition is deliberately sequential and deterministic. It is not a hidden planner or autonomous agent.

## Project truth-boundary hardening in this milestone

Project creation now also guarantees more precise claims:

- ordinary repo-local creation can write only under `creations/`; short-lived candidate manifest tests use `.axm-build/`, while persistent editable self-workspaces are explicit creations;
- ordinary creation cannot overwrite root machine files such as `README.md`;
- a generic project never passes with zero checks;
- requested text files are re-opened and compared exactly before and after publication;
- replacing a project retains the previous body until post-publish verification succeeds;
- if post-publish verification fails, the previous project is restored.

Generated code is still not silently executed, and browser visual or interaction quality is still not silently claimed as verified.

## What this does not mean

Seven live-backed components do not turn the remaining anatomy green.

A `uses` relationship does not become `implements`.

A kernel dependency does not become a live capability.

A composite does not become a new primitive merely because it has a convenient handle.

The point of this layer is to let executable coverage grow while keeping the difference between **map**, **dependency skeleton**, **live implementation**, and **composition** mechanically visible.
