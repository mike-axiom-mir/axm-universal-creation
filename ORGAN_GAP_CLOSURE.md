# Missing-Organ Closure Experiments

Interface discovery can expose that a creation goal needs an organ the live package body does not contain. Universal Creation can now test an explicitly supplied answer to that gap without pretending the answer was generated automatically or installing it.

The live operation is:

`explore-missing-organ-closure`

Its fixed evidence sequence is:

`missing interface HOLD -> supplied organ proposal -> exact contract alignment -> detached Forge materialization -> Forge test -> ephemeral installed+candidate library -> re-run original goal -> candidate-selected READY closure -> disposable validated assembly -> remain detached`

## Required input

The caller supplies:

- a candidate directory path;
- the same exact `axm.interface-organ-goal/v0.1` object that currently produces `HOLD_MISSING_ORGAN_INTERFACE`;
- one complete `axm.creation-unit-spawn-proposal/v0.1` with `kind: organ`;
- optional deterministic checks for the full closure project.

The proposal contains the actual executable-organ source. That design may come from a human, AI, deterministic recipe, or explicitly labelled external boundary. The closure operation does not claim the deterministic kernel invented the semantic implementation.

## What must agree

Before materializing anything, the operation validates:

- the closed Creation-Unit Forge proposal;
- the complete `axm.executable-software-organ/v0.1` entrypoint;
- exact proposal/package identity;
- exact set equality between the Forge unit's `provides`/`requires` and the package's `provides`/`requires`;
- that the package provides at least one interface named by the observed missing contracts;
- that its exact `id@version` does not shadow an installed package.

Contract drift, invalid source, unrelated source, or identity collision HOLD before the candidate directory is created.

## Detached proof

A linked candidate is materialized and tested through the existing Creation-Unit Forge. Passing proves package integrity and executable-organ schema validity, not usefulness by itself.

The operation then creates a temporary exact package library containing:

- byte copies of the currently installed package sources;
- the tested detached candidate entrypoint.

It re-runs the original interface goal against that overlay. Success requires:

1. discovery becomes `READY_EXACT_INTERFACE_ASSEMBLY`;
2. the supplied candidate exact ref participates in the selected closure;
3. exact resolution and organ assembly succeed;
4. the complete project passes validated publication and caller checks in disposable space.

The candidate entrypoint is hashed again after it is copied into the overlay. If those bytes differ from the source that passed the Forge test, the experiment stops before discovery rather than attaching stale test evidence to changed source.

The overlay and project are deleted after the experiment. Their source digests, package refs, selected assembly, file receipts, validation, and proof limits remain in the returned evidence.

## HOLD states

- `HOLD_NO_MISSING_ORGAN_INTERFACE_TO_CLOSE`
- `HOLD_INVALID_ORGAN_FORGE_PROPOSAL`
- `HOLD_FORGE_PROPOSAL_IS_NOT_ORGAN`
- `HOLD_CANDIDATE_ORGAN_PACKAGE_INVALID`
- `HOLD_ORGAN_PROPOSAL_CONTRACT_MISMATCH`
- `HOLD_ORGAN_PROPOSAL_NOT_LINKED_TO_GAP`
- `HOLD_CANDIDATE_ORGAN_REF_COLLISION`
- `HOLD_CANDIDATE_ORGAN_TEST_FAILED`
- `HOLD_CANDIDATE_ORGAN_SOURCE_DRIFT`
- `HOLD_CANDIDATE_ORGAN_CLOSURE_INCOMPLETE`
- `HOLD_CANDIDATE_ORGAN_NOT_SELECTED`
- `HOLD_CANDIDATE_ORGAN_CLOSURE_BUILD_FAILED`

Once a linked candidate has been materialized, a later closure or build HOLD leaves that detached candidate available for inspection and repair. It still does not become installed.

## Try the included experiment

```bash
PYTHONPATH=src python -m axm_uc create examples/requests/explore_missing_status_panel_organ_closure.json
```

The live library initially has no `status-panel` provider. The explicit candidate supplies it and requires `local-interaction`. The ephemeral goal therefore derives the candidate plus the installed interaction, theme, and shell organs, then validates `status.html`, `app.js`, `style.css`, and `index.html` together.

After the command:

- the candidate remains under `creations/spawned/status-panel-organ-candidate/`;
- the ephemeral overlay and full project are gone;
- `executable-organs/` remains unchanged;
- the original goal still reports missing when run against the live library;
- no admission request, approval, installation, registration, promotion, merge, CANON, or permission change occurred.

## Truth boundary

`TESTED_DETACHED_ORGAN_CLOSES_INTERFACE_GAP` means one supplied candidate was necessary in one exact structural closure and the resulting project passed deterministic validation.

It does not mean the source semantically implements the human meaning of the interface, that browser/runtime behavior was executed, that visual quality was judged, that the organ works for every future assembly, or that it should be admitted. Those require further explicit evidence and a separate choice.
