# Standalone Capability Growth

The current machine has three additional executable creation routes. They widen what the standalone body can actually do without redefining the 2,165-record research map as implemented machinery.

## Mixed projects

`AXM-CAP-WRITE-MIXED-PROJECT` publishes one project containing exact UTF-8 text and exact binary bytes.

Binary inputs use strict base64 descriptors. Every file receives a byte count and SHA-256 receipt before publication and again from the published body. Optional `media-signature` checks recognize bounded PNG, JPEG, GIF, WebP, WAV, Ogg, GLB, PDF, and ZIP signatures. A signature is not a decoder, visual test, audio test, geometry test, or semantic judgment.

Limits are 256 files, 16 MiB per file, and 64 MiB total.

```bash
PYTHONPATH=src python -m axm_uc create examples/requests/create_mixed_media_project.json
```

## Deterministic state machines

`AXM-CAP-DETERMINISTIC-STATE-MACHINE` compiles, steps, or replays `axm.deterministic-state-machine/v0.1` data.

Each state/event pair may select at most one transition. An undeclared pair becomes `HOLD_NO_DECLARED_TRANSITION`; it does not guess. Effects are returned as inert JSON and are never executed. This makes the route usable as a small verified rule core for games, workflows, interfaces, tools, and simulations while leaving host action authority outside it.

```bash
PYTHONPATH=src python -m axm_uc create examples/requests/replay_game_state_machine.json
```

## Portable creation bundles

`AXM-CAP-PORTABLE-CREATION-BUNDLE` packs, inspects, and unpacks `axm.portable-creation-bundle/v0.1` archives.

The canonical manifest names every regular project file, byte count, and SHA-256 digest. Inspection rejects unsafe paths, duplicate or undeclared entries, symlinks, unsupported compression, and body drift. Unpack stages and revalidates the complete body before publication.

The bundle deliberately excludes permission bits, ownership, timestamps, symlinks, and platform metadata. A valid bundle proves portable byte identity, not that the receiving host can run or understand the creation.

```bash
PYTHONPATH=src python -m axm_uc create examples/requests/pack_portable_creation.json
```

## Truth boundary

These routes implement three real pieces of the larger direction:

`mixed bytes -> explicit state behavior -> portable verified body`

They do not establish arbitrary media generation, arbitrary task correctness, automatic capability invention, autonomous promotion, or universal host compatibility. New domains still need versioned capabilities or adapters and direct evidence.
