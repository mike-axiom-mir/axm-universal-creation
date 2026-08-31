# Executable Organ Body

AXM Universal Creation now has a distinct local body for reusable working software organs:

`executable-organs/`

This is deliberately separate from `organs/`.

- `organs/` contains 415 descriptive anatomy candidates.
- `executable-organs/` contains source packages the current machine can actually inspect, resolve, render, assemble, and test within its stated limits.

An anatomy name never becomes executable merely because a similarly named package exists.

## Package contract

Every installed package uses the exact schema:

`axm.executable-software-organ/v0.1`

A package declares:

- stable `id`, `version`, and `status: executable`;
- purpose and supported project types;
- exact template parameters;
- provided and required interface names;
- complete UTF-8 file templates;
- descriptive anatomy references;
- local source provenance;
- explicit limitations.

Loading the library validates that package parameters exactly match its template placeholders. Missing, unused, malformed, duplicated, or unsupported declarations fail package loading instead of being silently repaired.

## Exact reference resolution

Assemblies may keep supplying inline organ source for experiments, or reference an installed package:

```json
{
  "instance_id": "theme",
  "ref": "axm.web.theme@1.0.0",
  "depends_on": ["shell"],
  "bindings": {
    "background": "#15172b"
  }
}
```

References are exact. There is no newest-version substitution, fuzzy matching, semantic selection, or silent source override.

`instance_id` separates one assembly instance from the reusable package identity. The same package can therefore be reused across different assemblies with different instance-scoped bindings while retaining one inspectable source package. Within one assembly, the existing single-provider and exclusive-file-ownership rules still reject ambiguous duplicate contributions.

A referenced instance cannot override the package's files, version, provided interfaces, required interfaces, or purpose. To experiment with changed source, use an explicit inline organ or create a new versioned package.

## Current installed packages

The first body contains three reusable local-web packages:

- `axm.web.shell@1.0.0`;
- `axm.web.theme@1.0.0`;
- `axm.web.interaction@1.0.0`.

Inspect them:

```bash
PYTHONPATH=src python -m axm_uc organs
PYTHONPATH=src python -m axm_uc organs --provides visual-theme
PYTHONPATH=src python -m axm_uc organs --ref axm.web.shell@1.0.0
```

Create a project by reference:

```bash
PYTHONPATH=src python -m axm_uc create examples/requests/create_reusable_organ_site.json
```

The resolution receipt preserves every instance, exact package ref, package source path, bound parameter name, interface, dependency, and rendered file owner.

## Interface-driven discovery

An exact assembly no longer has to name package refs and dependency edges itself. `AXM-CAP-COMPOSE-ORGAN-PROJECT` accepts an `axm.interface-organ-goal/v0.1` object containing:

- one project ID, version, and project type;
- one or more exact required interface names;
- explicit parameter bindings keyed by provided interface.

For example, requesting only `local-interaction` discovers that the installed interaction package also requires `visual-theme` and `document-shell`. The bounded constraint search selects an assembly only when one uniquely smallest acyclic, collision-free package set satisfies the requested and transitive exact interfaces. Dependency edges and stable instance IDs are then derived from those declarations before the existing exact assembly path runs.

```json
{
  "schema": "axm.interface-organ-goal/v0.1",
  "id": "axm.example.discovered-site",
  "version": "1.0.0",
  "project_type": "static-web",
  "required_interfaces": ["local-interaction"],
  "bindings": {
    "document-shell": {"idle_label": "Create", "title": "Creation freedom"},
    "visual-theme": {"background": "#10223b"},
    "local-interaction": {"active_label": "Created", "state": "created"}
  }
}
```

`discover-organ-assembly` exposes the complete read-only plan. `interface-organ-project` publishes it. Multiple equally small complete assemblies produce `HOLD_AMBIGUOUS_ORGAN_ASSEMBLY`. An absent provider produces `HOLD_MISSING_ORGAN_INTERFACE` plus an `axm.missing-executable-organ-contract/v0.1` body suitable for later human, AI, recipe, or Forge design. Incomplete bindings, cycles, collisions, and the 10,000-state search bound remain typed HOLDs. No HOLD invents source, installs a package, or admits a candidate.

`explore-missing-organ-closure` can test one explicitly supplied organ answer to that HOLD. It requires exact agreement between the Forge proposal and package interface declarations, materializes and tests the candidate detached, adds it only to a disposable installed-plus-candidate library, re-runs the original goal, requires the candidate to participate in the selected READY assembly, and validates the complete project in disposable space. The candidate is not copied into this live package body. See `ORGAN_GAP_CLOSURE.md`.

## Complete anatomy-to-body census and compiler

`organ-census` now accounts for all 415 descriptive organs against the installed package body. It verifies that each `organs/*.json` record exactly matches its canonical registry record, maps exact installed package anatomy refs, and reports structural interface coverage separately from semantic or runtime proof.

The paired organ-materialization compiler accepts one complete explicitly supplied executable-organ package, checks its anatomy lineage, rejects installed-ref collisions, and converts it into the existing closed Forge proposal. It can then materialize and test that candidate while leaving installation and connection to the live library to the separate `adopt-organ` evolution transition. See `ORGAN_MATERIALIZATION.md`.

## Capability multiplier

The top-level live-capability count measures routed machine operations. Executable-organ packages are a second, composable capability surface. Adding a valid package can expand what assemblies create without adding a new Python builtin or pretending the package is a top-level route.

This is the intended multiplier:

`working organ source -> installed versioned package -> required interfaces -> exact reusable assembly -> many distinct creations`

## Truth boundary

Package validation proves structure, exact identity, template/parameter agreement, and inspectable source presence.

It does not yet prove that source semantically implements its declared interfaces, execute JavaScript, judge browser visuals, invent runtime wiring, or select the best organ for an ambiguous request. Discovery proves only that exact declared contracts have one bounded structural solution.

Semantic interface validators, runtime linkers, simulation, and learned or explicitly guided creative selection remain later milestones.
