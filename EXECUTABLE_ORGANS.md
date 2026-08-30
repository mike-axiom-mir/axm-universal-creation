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

## Capability multiplier

The top-level live-capability count measures routed machine operations. Executable-organ packages are a second, composable capability surface. Adding a valid package can expand what assemblies create without adding a new Python builtin or pretending the package is a top-level route.

This is the intended multiplier:

`working organ source -> installed versioned package -> exact reusable assembly -> many distinct creations`

## Truth boundary

Package validation proves structure, exact identity, template/parameter agreement, and inspectable source presence.

It does not yet prove that source semantically implements its declared interfaces, execute JavaScript, judge browser visuals, invent runtime wiring, or select the best organ for an ambiguous request.

Those remain later interface-validator, linker, test/simulation, and discovery milestones.
