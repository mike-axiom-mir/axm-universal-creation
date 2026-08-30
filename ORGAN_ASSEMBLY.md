# Deterministic Software-Organ Assembly

AXM Universal Creation can assemble one software project from several reusable, inspectable software organs.

At this milestone, an executable software organ is a versioned template fragment with:

- a stable `id` and `version`;
- an optional purpose statement;
- explicit dependencies on other organ IDs;
- declared interface names it `provides` and `requires`;
- ownership of one or more templated project files.

The assembly itself declares an ID, version, project type, organs, shared exact variables, and optional deterministic project checks. An organ may carry inline source or name an exact installed executable package through `ref` plus an assembly-local `instance_id` and `bindings`.

## Assembly sequence

The live `AXM-CAP-ASSEMBLE-ORGAN-PROJECT` capability performs:

`resolve exact package refs -> validate organ identities -> resolve dependency graph -> resolve declared interfaces -> render organs once -> verify exclusive file ownership -> publish one grounded project`

Dependency order is deterministic. When several organs are ready at the same time, their declared list order is preserved.

The result exposes:

- every declared dependency edge;
- every interface provider and each organ's requirements;
- the resolved organ order;
- each organ's version, purpose, dependencies, variables, and rendered paths;
- exact file-to-organ ownership;
- exact package refs, source paths, and instance-scoped parameter bindings when installed packages are used;
- the final project validation and grounding receipt.

The assembly logic also exposes a read-only deterministic preview seam. It performs exact package resolution, dependency/interface validation, rendering, and ownership checks without publishing a project. Gap synthesis uses that preview together with the live `AXM-CAP-ASSEMBLE-ORGAN-PROJECT@0.3.0` receipt contract to compile a detached `produce -> digest-verify` composite for a real unroutable organ request. The preview does not select packages, invent organs, wire runtime semantics, or grant admission authority.

Try the included three-organ local site:

```bash
PYTHONPATH=src python -m axm_uc create examples/requests/create_organ_site.json
PYTHONPATH=src python -m axm_uc create examples/requests/create_reusable_organ_site.json
PYTHONPATH=src python -m axm_uc create examples/requests/explore_verified_organ_gap.json
```

Its `shell-organ` owns `index.html`, `theme-organ` owns `style.css`, and `interaction-organ` owns `app.js`. The latter two depend on the shell, and the interaction organ also depends on the theme.

The shell provides `document-shell`; the theme requires that interface and provides `visual-theme`; the interaction organ requires both. A required interface is valid only when its single provider is reachable through the requiring organ's declared dependency closure.

## Explicit failures

Assembly rejects:

- duplicate organ IDs;
- missing dependency targets;
- dependency cycles;
- missing, duplicate, or dependency-unreachable interface providers;
- duplicate dependency declarations;
- missing, invalid, or globally unused variables;
- malformed template placeholders;
- rendered paths that escape the project;
- two organs claiming the same rendered file path.
- missing exact package references, package binding drift, unsupported package/project combinations, or attempted source/contract overrides on referenced instances.

No partial project is published for these structural errors.

After structural assembly, ordinary `grounded-draft` publication retains a complete exact project when grammar or caller checks expose gaps. Explicit `validated` mode blocks a failed project.

## Truth boundary

The 415 registry organ records describe candidate anatomy. A record does not become executable merely because its name appears in the map.

This live capability assembles organs whose source templates were supplied inline or resolved exactly from the separately validated `executable-organs/` body. It creates a real joint between organ architecture and software creation without claiming that all described organs already have implementations.

Declared dependencies determine order and remain visible. Provided/required names validate the declared interface graph, but do not prove that source code conforms to those names. The capability does not invent imports, APIs, state flow, or runtime wiring. Those connections must be present in the organ source or proven by later explicit interface validators.

Each file currently has one organ owner. Parser-aware shared-file composition, source-level interface conformance checking, binary assets, learned organ selection, and semantic discovery remain capability gaps. See `EXECUTABLE_ORGANS.md` for the installed package boundary.
