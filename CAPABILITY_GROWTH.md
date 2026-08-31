# Standalone Capability Growth

The current machine has five additional executable creation routes. They widen what the standalone body can actually do without redefining the 2,165-record research map as implemented machinery.

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

## Truth boundary

These routes implement three real pieces of the larger direction:

`generated media -> mixed bytes -> explicit state behavior -> offline game source -> portable verified body`

They do not establish arbitrary media generation, arbitrary game genres, observed browser behavior, arbitrary task correctness, automatic capability invention, autonomous promotion, or universal host compatibility. New domains still need versioned capabilities or adapters and direct evidence.
