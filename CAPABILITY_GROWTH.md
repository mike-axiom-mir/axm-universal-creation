# Standalone Capability Growth

The current machine has seven additional executable creation routes. They widen what the standalone body can actually do without redefining the 2,165-record research map as implemented machinery.

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

## Procedural media

`AXM-CAP-GENERATE-PROCEDURAL-MEDIA` originates deterministic binary media instead of requiring a caller to arrive with pre-built base64 bytes.

The PNG grammar rasterizes an explicit background plus ordered filled rectangles and circles into RGBA8 pixels. It checks every PNG chunk CRC, decompresses the complete IDAT payload, and verifies the raster shape. The WAV grammar synthesizes explicit mono PCM16 square-tone and silence segments. It re-parses the complete RIFF, format, and data sizes after publication.

Both formats are intentionally small grammars, not learned image/audio generators. Their receipts prove exact bytes and bounded container payloads, not appearance, meaning, musicality, or perceptual quality.

```bash
PYTHONPATH=src python -m axm_uc create examples/requests/generate_target_icon.json
PYTHONPATH=src python -m axm_uc create examples/requests/generate_fire_sound.json
```

## Offline browser games

`AXM-CAP-BUILD-OFFLINE-BROWSER-GAME` compiles one `axm.browser-arena/v0.1` specification into a dependency-free local game project.

The current arena grammar emits an inspectable Canvas renderer, requestAnimationFrame game loop, keyboard/pointer/touch input map, HUD, projectile and damage rules, ammo/reload path, rewards, and ready/playing/paused/won/lost session graph. The game builder reuses the deterministic state-machine grammar, generates its own local PNG icon and WAV cue, and publishes all eight project files through the mixed-project digest boundary.

The reference example uses only visible cues from the supplied photo: a dark tactical surface, block-like characters, a command tower, selected hostile target, health, credits, and ammo. It does not copy or claim access to hidden source, assets, or live behavior.

```bash
PYTHONPATH=src python -m axm_uc trial examples/requests/create_command_tower_arena.json
PYTHONPATH=src python -m axm_uc create examples/requests/pack_command_tower_arena.json
```

Open `creations/command-tower-arena/index.html` for the separate browser observation. A deterministic trial validates source, JSON, local links, media containers, and exact bytes; it does not claim the browser actually rendered, accepted input, played audio, or delivered good gameplay.

## Procedural 3D

`AXM-CAP-GENERATE-PROCEDURAL-3D` originates deterministic glTF 2.0 binary assets through the `procedural-glb-asset` route.

The bounded grammar composes boxes, pyramids, and cylinders with explicit translation, scale, color, metallic, and roughness values. Generation writes indexed triangle positions and normals, then reparses the complete GLB header, JSON and BIN chunks, buffer ranges, accessors, meshes, materials, and nodes after atomic publication. The same specification produces the same bytes.

```bash
PYTHONPATH=src python -m axm_uc create examples/requests/generate_command_tower_glb.json
```

The structural receipt does not claim rendered appearance, good geometry, manifold topology, physics behavior, or import compatibility with an untested host.

## Creation growth through one organ

`AXM-CAP-GROW-CREATION-WITH-ORGAN` connects a real creation gap to the 415-organ materialization queue through `creation-organ-growth`.

The operation begins at exactly one `HOLD_MISSING_ORGAN_INTERFACE`, requires the caller to name the exact anatomy record and supply one complete executable organ package, compiles that package into a detached Forge proposal, and tests it. It then creates a disposable installed-plus-candidate overlay and requires the candidate to participate in a complete request-shaped assembly.

```bash
PYTHONPATH=src python -m axm_uc create examples/requests/grow_status_panel_creation.json
```

Success proves that the explicit candidate closed the selected structural gap in that bounded experiment. It does not invent source, install the package, register a route, promote a capability, merge code, or prove runtime semantics.

## Phone creation console

The [AXM Universal Creation Console](https://axm-universal-creation-console.miketobi90.chatgpt.site) is a mobile-first browser surface for five portable creation classes: website, browser game, device-local tool, GLB model, and WAV cue. It generates files entirely in the browser, computes SHA-256 digests, adds a truth-boundary receipt, and downloads a standalone ZIP.

The console is deliberately a smaller browser runtime, not a hosted copy of the Python machine. Its receipts state that the full machine did not execute and that runtime, visual, and quality behavior remains unproven. See `CREATION_CONSOLE.md`.

## Truth boundary

These routes implement three real pieces of the larger direction:

`explicit organ source -> one closed creation gap` and `generated media/3D -> mixed bytes -> explicit state behavior -> offline game source -> portable verified body`

They do not establish arbitrary media generation, arbitrary game genres, observed browser behavior, arbitrary task correctness, automatic capability invention, autonomous promotion, or universal host compatibility. New domains still need versioned capabilities or adapters and direct evidence.
