# Deterministic Creation-Unit Forge

Universal Creation now has one small live capability whose output can be new creation machinery rather than only an end-user project:

`AXM-CAP-SPAWN-CREATION-UNIT`

The important measure is not how many top-level routes exist today. It is whether a human, AI, deterministic recipe, bounded gap compiler, or explicitly labelled external boundary can supply a new bounded design and have the machine turn it into an exact, inspectable, testable candidate without silently installing it.

## Growth path

The Forge path is:

`proposal -> closed-contract validation -> detached materialization -> exact lineage -> bounded test -> optional review request`

A separate machine-evolution path may then carry a supported tested candidate into the continuing body. The review request is an observation surface, not a mandatory human approval gate.

The forge accepts `axm.creation-unit-spawn-proposal/v0.1`. A proposal contains:

- stable identity, semantic version, kind, and purpose;
- exact UTF-8 payload files;
- implementation kind, entrypoint, and source files;
- input/output contracts plus provided and required interface names;
- exact versioned dependencies and visible relationships;
- deterministic file checks;
- provenance, limitations, and a four-root fit declaration;
- an authority object in which execution, installation, registration, promotion, merge, CANON, and permission change are all explicitly false.

Those false proposal-authority fields mean **the detached candidate cannot grant itself machine authority**. They do not globally forbid the continuing machine from installing, registering, promoting, merging, changing CANON, changing permissions, replacing, or recovering when an explicit self-evolution transition exists and is justified.

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

## Test and optional review state

The separate `test` operation reopens the candidate, reconstructs the expected manifest from the stored proposal, verifies the exact file set and every payload digest, runs the declared deterministic checks, and then applies the strongest currently implemented kind-specific test. Spawned capability/hand fixture paths must remain under their expanded `${TEST_DIR}/` directory. The test process still uses the current host user's permissions; this is a bounded path contract, not an OS sandbox.

The candidate or a connected cognition may choose `request-admission-check` with its own readiness statement. A passing candidate currently records:

`READY_FOR_HUMAN_ADMISSION_REVIEW`

A failing or mutated candidate records:

`HELD_FAILED_TESTS`

The legacy state name describes that review artifact only. It is **not** a declaration that a human is required before all self-modification. The request operation itself performs no admission or machine mutation.

For supported self-evolution transitions, the running machine can separately re-test the candidate, apply its internal four-root fit, establish the daily recovery boundary, and continue from the changed state without a permanent outside approver.

## Self-evolution after Forge

`AXM-CAP-EVOLVE-MACHINE` now supports the first direct Creation-Unit adoption transition: executable organs.

The current path is:

`tested detached organ -> current four-root fit -> ensure today's complete machine snapshot -> write exact tested organ into executable-organs/ -> reload/register exact ref -> expose it to normal interface-driven composition`

Successful adoption therefore makes installation, registration, and promotion-for-composition real machine transitions rather than merely proposal fields.

Recovery uses the existing daily whole-machine snapshot model. The machine preserves one complete restorable state per day. If later evolution proves unwanted, the current body can be quarantined and a known-good daily snapshot restored. This deliberately avoids constructing a per-change event-history bureaucracy.

The older direct candidate-capability adoption path also establishes the daily snapshot before making a passing capability live.

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

The result remains under `creations/spawned/creation-request-protocol/`. Its review request is evidence for a later transition, not the transition itself.

## From missing interface to tested detached organ

The separate evidence-bound gap compiler can now produce two narrow classes of forge proposal from a real unroutable request: an exact UTF-8 file-route adapter backed by one observed compatible live primitive, or a bounded project recipe backed by exact template, explicitly assembled organ, interface-discovered organ, raw-file, existing verified-composite, verifier, and JSON-reporter contracts. It keeps every candidate path in evidence, selects one unique shortest complete route within three steps, and uses only a closed receipt-to-digest projection or exact whole-object binding. It embeds its gap analysis and runs a request-shaped fixture while leaving semantic equivalence and general behavior explicitly unproven. See `GAP_SYNTHESIS.md`.

The installed organ body supplies one multiplier without pretending to invent semantics: an exact interface goal can derive a unique complete organ composition. Missing interfaces become Forge-ready organ contracts, and ambiguity stays visible. The Forge still requires a missing organ's actual source and tests before materializing that body.

That closure can now be tested end to end when a human, AI, deterministic recipe, or labelled external boundary supplies the complete organ proposal. `explore-missing-organ-closure` first proves that the proposal/package declarations match the observed gap, then reuses this Forge for detached materialization and testing. A disposable package overlay must make the original goal READY with that candidate selected, and the full assembly must validate. The closure experiment itself remains detached. A separately justified `adopt-organ` evolution transition can now carry that exact tested organ into the live executable-organ library.

The forge still does not autonomously synthesize arbitrary semantic source from a high-level gap, activate a newly spawned recipe as a general builder, prove arbitrary protocol semantics, or run a generated organ end to end.

Those remain visible capability gaps. They are not reasons to block the machine from using the self-evolution transitions it actually has.
