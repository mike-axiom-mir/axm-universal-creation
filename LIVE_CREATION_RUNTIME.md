# UC Live Creation Runtime v0

Status: **EXPERIMENTAL, inside Universal Creation itself.**

The Live Creation Runtime (LCR) closes the first real loop between making a creation and using evidence from the running creation to change it again:

`canonical creation -> assemble -> execute -> observe -> repair -> execute again`

It is deliberately a native UC capability, not a permanent external service or engine dependency.

## Run it

```bash
PYTHONPATH=src python -m axm_uc.live_creation examples/requests/live_creation_repair_demo.json --root .
```

The retained receipt is written below:

```text
.axm/live-creation/runs/<run-id>/receipt.json
```

The runtime body for that run lives beside the receipt under `workspace/`.

## Manifest v0

A manifest declares:

- `source` — an existing UC creation directory inside the machine root;
- `domain` — descriptive domain such as `game`, `software`, `image`, `web`, or `generic`;
- `execute` — explicit command argv to run against the assembled body;
- `observe` — deterministic file/evidence checks;
- `repairs` — bounded deterministic edits tied to named failed observations;
- `max_iterations` — maximum execute/observe/repair cycles;
- `policy` — explicit execution and repair boundaries.

Python execution uses `@python`, which resolves to the current interpreter. Other local tools or engines can be connected by declaring their executable name in `policy.allowed_executables`. Commands use `shell=False`.

## Repair scope

The default is:

```json
{"repair_scope": "workspace"}
```

That repairs only the disposable assembled runtime copy.

For an actual UC creation that should grow in place during the loop, use:

```json
{"repair_scope": "workspace-and-source"}
```

Then each declared repair that changed the runtime copy is also applied to the canonical creation source before the next execution cycle. Receipts say whether canonical source changed.

This is the direct live-build path. It is opt-in because silent source rewrite would violate the machine's inspectability and user-agency rules.

## Current observations

v0 can observe:

- process exit success/failure;
- file exists / absent;
- UTF-8 text contains / not-contains;
- valid JSON;
- exact SHA-256.

v0 can repair:

- write UTF-8 text;
- replace exact text;
- delete a file.

These are intentionally small primitives. More repair and observer organs can be added without replacing the loop.

## What COMPLETE means

`COMPLETE` means **the evidence declared by this live-creation manifest passed**.

It does **not** mean the whole game, picture, application, asset, or other creation is finished.

If evidence fails and no declared repair changes the runtime body, the run stops at `HOLD` rather than inventing success.

## Truth boundary / next capability

This v0 is real execution and deterministic observation, but it is not yet a visual runtime observer.

It does not currently judge:

- rendered pixels;
- material/lighting fidelity;
- animation quality;
- gameplay feel;
- audio quality;
- semantic visual quality.

For games, the next meaningful organ is a target-runtime visual observer that can launch the UC-native game/runtime or an explicit adapter target, capture actual frames/state, and feed bounded evidence back into this same loop.

The architecture does not change when that arrives. The observer gets stronger; the loop stays:

`assemble -> run/render -> observe -> repair -> repeat`.
