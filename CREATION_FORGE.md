# Deterministic Creation-Unit Forge

Universal Creation now has one small live capability whose output can be new creation machinery rather than only an end-user project:

`AXM-CAP-SPAWN-CREATION-UNIT`

The important measure is not how many top-level routes exist today. It is whether a human, AI, deterministic recipe, bounded gap compiler, or explicitly labelled external boundary can supply a new bounded design and have the machine turn it into an exact, inspectable, testable candidate without silently installing it.

## Growth path

The implemented path is:

`proposal -> closed-contract validation -> detached materialization -> exact lineage -> bounded test -> voluntary admission request -> separate admission choice`

The forge accepts `axm.creation-unit-spawn-proposal/v0.1`. A proposal contains:

- stable identity, semantic version, kind, and purpose;
- exact UTF-8 payload files;
- implementation kind, entrypoint, and source files;
- input/output contracts plus provided and required interface names;
- exact versioned dependencies and visible relationships;
- deterministic file checks;
- provenance, limitations, and a four-root fit declaration;
- an authority object in which execution, installation, registration, promotion, merge, CANON, and permission change are all explicitly false.

Unknown proposal fields are rejected. Paths may not escape the candidate body. Payloads are currently bounded to 128 files and 2 MiB of exact UTF-8 text.

## First-class kinds and open extension

| Kind | Meaning | Current strongest automatic evidence |
| --- | --- | --- |
| `hand` | Bounded callable adapter or actuator candidate | Executes the candidate capability manifest's declared disposable tests |
| `capability` | Callable creation-ability candidate | Executes the candidate capability manifest's declared disposable tests |
| `organ` | Reusable subsystem package candidate | Validates the exact executable-organ package grammar |
| `protocol` | Typed exchange-contract candidate | Identity, JSON parsing, package integrity, and declared file checks |
| `skill` | Portable bounded method/instruction package | Package integrity and declared file checks |
| `specialist` | Temporary method overlay composed from declared skills | Identity, package integrity, and declared file checks |
| `recipe` | Deterministic build-definition candidate | Identity, package integrity, and declared file checks |

A syntactically valid new kind is also accepted as `OPEN_EXTENSION_GENERIC`. This keeps the ontology open. It does **not** turn a new label into a new runtime validator: extension kinds receive generic integrity and declared file evidence until a kind-specific verifier is actually implemented.

## Skills and specialists

A normal deterministic machine can use skills, but it does not need to pretend they are people or neural expertise.

- A **skill** is a portable bounded method. `INSTRUCTION_ONLY` and `HOST_MEDIATED` skills still require a suitable host at use time. The package grants no missing tool or permission.
- A **specialist** is a temporary `METHOD_OVERLAY` that may select and organize skills for an AI or human seat. It is not identity, durable memory, permission, proof of expertise, or an independent evidence source.

Several specialist views derived from one provenance root remain one provenance root. Quantity of perspectives is not manufactured corroboration.

## Deterministic package

Every successful spawn contains:

- `axm.proposal.json` — the normalized complete proposal;
- `axm.unit.json` — the typed detached unit manifest;
- `axm.spawn-receipt.json` — proposal, manifest, package, and file lineage plus the staged validation observation;
- the exact supplied payload files.

The package digest is independent of the chosen output path. Spawning the same normalized proposal twice therefore produces the same proposal digest, manifest digest, package digest, and body-file records.

Package integrity and runtime behavior are separate evidence planes. The receipt explicitly says generated code was not executed during materialization.

## Test and admission states

The separate `test` operation reopens the candidate, reconstructs the expected manifest from the stored proposal, verifies the exact file set and every payload digest, runs the declared deterministic checks, and then applies the strongest currently implemented kind-specific test. Spawned capability/hand fixture paths must remain under their expanded `${TEST_DIR}/` directory. The test process still uses the current host user's permissions; this is a bounded path contract, not an OS sandbox.

The candidate or a connected cognition may later choose `request-admission-check` with its own readiness statement. A passing candidate becomes:

`READY_FOR_HUMAN_ADMISSION_REVIEW`

A failing or mutated candidate becomes:

`HELD_FAILED_TESTS`

Neither state performs admission. The request does not install, register, route, promote, merge, change CANON, or change permissions. It records one current review request rather than an automatic activity history.

## WALMI and Workshop donor knowledge

This design deliberately borrows understood patterns from the WALMI/Workshop creation research without importing the old Workshop as a runtime dependency or governance layer.

Reviewed donor material in `mike-axiom-mir/waldo-axm-mirror-research` included the committed checkout at `db4ee1073cb718d13037c19899f961cc27c5b2be` and, specifically:

- the Capability Gap Hand's rule that absence becomes a typed gap rather than silent quality reduction;
- Capability Fabric's detached, digest-bound candidate packages;
- the separation of package integrity from generated-runtime parity;
- the rule that missing links hold rather than being invented;
- the separation of feasibility, selection, permission, action, installation, promotion, and CANON;
- specialist masks as temporary method overlays with no inherited authority or independent-evidence claim.

The implementation in this repository is new Python source fitted to Universal Creation's four roots, current project validator, executable-organ packages, and existing candidate capability tester. No donor runtime source was copied into the live machine.

## Try the protocol candidate

```bash
PYTHONPATH=src python -m axm_uc forge
PYTHONPATH=src python -m axm_uc create examples/requests/spawn_creation_protocol.json
PYTHONPATH=src python -m axm_uc create examples/requests/test_spawned_creation_protocol.json
PYTHONPATH=src python -m axm_uc create examples/requests/request_spawned_creation_protocol_review.json
```

The result remains under `creations/spawned/creation-request-protocol/`. Its admission request is evidence for a later decision, not the decision itself.

## Current capability gap

The separate evidence-bound gap compiler can now produce one narrow class of forge proposal from a real unroutable request: an exact UTF-8 file-route adapter backed by one observed compatible live primitive. It embeds its gap analysis and runs a request-shaped fixture, while explicitly leaving semantic equivalence unproven. See `GAP_SYNTHESIS.md`.

The forge still does not autonomously synthesize arbitrary semantic source from a high-level gap, activate a newly spawned recipe as a general builder, prove arbitrary protocol semantics, run a generated organ end to end, or adopt every unit kind into a live registry.

Those are now visible next layers rather than reasons to inflate the live capability count.
