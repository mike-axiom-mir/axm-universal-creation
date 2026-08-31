# Organ Materialization Fabric

Universal Creation now connects every descriptive organ to an explicit implementation state without pretending that a name or research seed is working software.

The current observed census is:

| Evidence state | Count | Meaning |
| --- | ---: | --- |
| Descriptive organ records | 415 | Canonical registry candidates, each exactly materialized under `organs/` |
| Connected executable-package mappings | 15 | An installed package cites the anatomy record and has a finite transitive provider chain within one declared project type |
| Executable mappings with missing interfaces | 0 | Installed source exists, but an exact declared interface provider is absent |
| Implementation required | 400 | No installed executable package cites the anatomy record |

“Connected” here means a finite transitive chain of exact structural interface coverage within one declared project type. Cycles without a complete base provider remain unresolved. Connection does not prove unique selection, semantic conformance, or runtime behavior.

## Inspect all 415

The read-only census verifies the canonical registry, every standalone organ source record, installed package mappings, and the current exact interface graph:

```bash
PYTHONPATH=src python -m axm_uc organ-census
PYTHONPATH=src python -m axm_uc organ-census --state IMPLEMENTATION_REQUIRED --limit 20
PYTHONPATH=src python -m axm_uc organ-census --id AXM-00-FOUNDATION-O-001-identity-registry
```

Every row reports one of three states:

- `CONNECTED_EXECUTABLE_PACKAGE`;
- `EXECUTABLE_PACKAGE_WITH_MISSING_INTERFACES`;
- `IMPLEMENTATION_REQUIRED`.

The summary separately reports malformed, missing, divergent, or extra standalone anatomy source files; dangling installed-package anatomy references; packages without anatomy references; and the descriptive/executable/runtime truth boundaries.

## Build one real organ body

The fabric does not create arbitrary semantic implementation source from a research-seed description. A human, AI, deterministic recipe, or explicitly labelled external source must supply a complete supported `axm.executable-software-organ/v0.1` or `v0.2` package containing:

- exact ID and semantic version;
- supported project types and template parameters;
- complete UTF-8 template files;
- provided and required interfaces;
- one or more exact anatomy references, including the selected target;
- provenance and limitations.

Version `v0.2` additionally requires at least one exact fixture: project type, complete parameter bindings, expected UTF-8 files, and bounded deterministic project checks. Fixtures run only in disposable project space and do not execute generated runtime source. Legacy `v0.1` packages remain valid with explicitly schema-only evidence.

`prepare-organ-materialization` validates that source, checks every cited anatomy ID against an exact standalone registry record, rejects an already-installed exact package ref, and compiles the source into the closed Creation-Unit Forge proposal. The compiler derives contracts, lineage relationships, deterministic JSON identity and digest checks, zero candidate authority, and four-root fit. It does not invent missing package fields or code.

`materialize-organ-candidate` performs that compilation and then uses the existing Forge to build and test the detached package:

```bash
PYTHONPATH=src python -m axm_uc create examples/requests/materialize_identity_registry_organ.json
```

The example produces `creations/spawned/identity-registry-document-organ/`. It is a bounded real implementation: a reusable generic-project organ that renders an initial namespaced identity-registry JSON document. Its limitations explicitly exclude persistence, authentication, and concurrent identity management.

The installed Foundation pack takes the next honest step: twelve `v0.2` document-producing packages, one per Foundation anatomy organ, each with a passing exact fixture. Their exact provided/required interfaces form a finite acyclic generic-project graph, so the census moves those twelve records from `IMPLEMENTATION_REQUIRED` to `CONNECTED_EXECUTABLE_PACKAGE`. See `FOUNDATION_ORGAN_PACK.md`.

## State transitions stay separate

The materialization flow is:

`415-row census -> explicit package source -> compiled Forge proposal -> detached materialization -> bounded package test`

A passing result is still:

- not installed;
- not registered;
- not promoted;
- not merged;
- not connected to the live executable-organ library;
- not runtime or semantic proof.

The existing `adopt-organ` evolution operation remains the separate transition that re-tests a candidate, evaluates four-root fit, establishes the daily recovery snapshot, and installs the exact tested package into the continuing machine.

This makes building all 415 a measurable queue rather than a count illusion: each accepted implementation can move one or more anatomy rows from `IMPLEMENTATION_REQUIRED` to installed structural coverage, while the census continues to show what remains.
