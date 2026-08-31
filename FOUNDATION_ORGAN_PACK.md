# Foundation Organ Pack

The Foundation pack connects the twelve descriptive `AXM-00-FOUNDATION-O-*` records to twelve installed executable-organ packages without claiming that a document template is a full service runtime.

Each package:

- uses `axm.executable-software-organ/v0.2`;
- renders one bounded JSON document under `axm/foundation/`;
- declares one exact generic-project interface;
- cites exactly one Foundation anatomy record;
- carries one deterministic fixture with exact bindings, expected bytes, JSON checks, and an exact file-set check;
- states the runtime behavior it does not implement.

## Exact package graph

| Anatomy | Package | Provides | Requires | Owned file |
| --- | --- | --- | --- | --- |
| O-001 identity registry | `axm.foundation.identity-registry@1.0.0` | `foundation-identity-registry` | — | `identity-registry.json` |
| O-002 schema registry | `axm.foundation.schema-registry@1.0.0` | `foundation-schema-registry` | — | `schema-registry.json` |
| O-003 metadata manager | `axm.foundation.metadata-manager@1.0.0` | `foundation-metadata` | identity registry, schema registry | `metadata.json` |
| O-004 version manager | `axm.foundation.version-manager@1.0.0` | `foundation-version-policy` | metadata | `version-policy.json` |
| O-005 capability registry | `axm.foundation.capability-registry@1.0.0` | `foundation-capability-registry` | identity registry, schema registry | `capability-registry.json` |
| O-006 dependency resolver | `axm.foundation.dependency-resolver@1.0.0` | `foundation-dependency-plan` | capability registry | `dependency-plan.json` |
| O-007 extension manager | `axm.foundation.extension-manager@1.0.0` | `foundation-extension-policy` | capability registry, dependency plan | `extension-policy.json` |
| O-008 compatibility checker | `axm.foundation.compatibility-checker@1.0.0` | `foundation-compatibility-policy` | version policy, dependency plan | `compatibility-policy.json` |
| O-009 migration manager | `axm.foundation.migration-manager@1.0.0` | `foundation-migration-plan` | compatibility policy | `migration-plan.json` |
| O-010 canonicalization organ | `axm.foundation.canonicalization@1.0.0` | `foundation-canonicalization-policy` | schema registry | `canonicalization-policy.json` |
| O-011 relationship graph manager | `axm.foundation.relationship-graph@1.0.0` | `foundation-relationship-graph` | identity registry, canonicalization policy | `relationship-graph.json` |
| O-012 interface validator | `axm.foundation.interface-validator@1.0.0` | `foundation-interface-validation` | schema registry, compatibility policy, capability registry | `interface-validation.json` |

The roots have no requirements. Every later requirement has a finite transitive provider chain in the same `generic` project type. The graph is acyclic, and every provided interface has exactly one provider within the complete pack.

## Verify and assemble

Run one package fixture:

```bash
PYTHONPATH=src python -m axm_uc organs --test-ref axm.foundation.identity-registry@1.0.0
```

Build the exact twelve-package assembly:

```bash
PYTHONPATH=src python -m axm_uc create examples/requests/create_foundation_organ_pack.json
```

The assembly request supplies exact refs, dependencies, and bindings. The normal organ assembler verifies dependency reachability, unique interface providers, exclusive file ownership, all rendered JSON, and the exact twelve-file set before publishing in `validated` mode.

Run the census:

```bash
PYTHONPATH=src python -m axm_uc organ-census
```

The observed result is 415 descriptive organs, 15 connected installed mappings, no installed mapping with missing interfaces, and 400 records still requiring implementation. The 15 connected mappings are the twelve Foundation packages plus the existing three static-web packages.

## Evidence boundary

“Executable” means the machine can exactly resolve, render, compose, publish, and deterministically validate these package bodies. The emitted JSON documents are real files with reusable parameters and exact fixture evidence.

They are not persistent registries, schema engines, dependency solvers, extension loaders, compatibility analyzers, migration runners, canonicalizers, graph databases, or interface-validation runtimes. Declared interface coverage is structural composition evidence, not source-level semantic conformance or runtime-call proof. Generated runtime is never executed by the fixture runner.
