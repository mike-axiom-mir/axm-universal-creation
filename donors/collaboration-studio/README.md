# Recovered Studio and Universal Component Protocol

Mike requested the actual old Studio source as a donor for Universal Creation.
The collaboration platform remains read-only and paused. This directory recovers
all 19 files of `tools/studio`, selected shared dependencies, and UCP from
`mike-axiom-mir/axm-collaboration-platform` at
`27757ace6133b243a200b0463e427c8b04d5a8e3`.

All executable source is byte-identical to its pinned Git blob. Of 34 original
file copies, 33 are unchanged. COMMAND_DECK_EVIDENCE.md uses backslash Markdown
hard breaks to satisfy UC's existing whitespace gate; its exact original text is
preserved losslessly in the JSON archive named by `manifest.json`. Tests verify
the original Git blob and the precise three-line formatting conversion.
The compositor itself lives in `src/axm_uc/data/studio/raster-compositor.js` so it
ships in the Python package. The manifest records this relocation. Apache-2.0
LICENSE, original notices, THIRD_PARTY and the referenced license registry are
retained. The registry names Comlink, jsPDF and wasm-vips; their implementations
are not imported by this extraction. No third-party seed meshes are included.

## What is usable now

- UC calls the original raster compositor through a separate bounded Node adapter:
  layers, 14 blend modes, masks, 13 filters and editable PNG projects.
- The original UCP JavaScript runs its unchanged fixture with its two local
  dependencies: target-canvas and native-bridge-codec. UCP validates typed component
  graphs and produces a contract receipt; it does not execute renderers.
- The Studio mirror bridge's unchanged selftest runs standalone.
- Studio core metadata and all 84 actions can be inspected. Inline scripts parse.

## What is preserved, not presented as integrated

The Studio folder contains the real canvas editor, paint/vector/pixel tools,
layer ownership/visibility/locking/opacity/blending, per-layer undo, frame stacks,
onion skin, spritesheet export and machine draw packets. These are original source
capabilities, not a new claim that its UI works in UC or a browser tested here.

The folder is a module but not a complete dependency bundle:

| Source | External platform references |
| --- | --- |
| `engine.html` | Agent Command Center identity registry, hub identity router, profile client and two skin preview images |
| `index.html` / `studio-shell.js` | Visual Actions (recovered), presentation spine CSS, hub module, continuity, Asset Vault and Asset Hands workbench |
| Optional UI/skin/pack modes | UI/UX Builder, Skinner and Asset Pack Lab sibling modules |
| `axm-foundation.js` | Optional local/remote AI connectors in original source; not started by UC |

The original Studio `selftest.js`, `html-inline-syntax-test.js` and shared raster
Hands selftest reference further platform files. They are retained unmodified;
the entire suites were not executed. UC's focused syntax/action checks do not
substitute for interactive verification. Historical evidence documents inside
`source/` describe donor-era runs, not this extraction's observations.

## UCP and skins

UCP means Universal Component Protocol. It seals component versions/digests,
resolves exact references, checks typed ports and acyclic graphs, checks canvas
compatibility, aggregates declared resource requirements and records adapter
losses. A skin can provide a different control surface for the same component
graph; a texture/material skin can be one of the graph's components. Actual
rendering still needs a matching creation hand/adapter. The included fixture
explicitly asserts `executed: false` and `visually_approved: false`.

This pass preserves and tests UCP as donor code. It does not replace UC's
canonical contracts or yet wire UCP graph dispatch into UC. Next useful work:
map one existing UC compositor operation into UCP ports/target canvas, then
connect the recovered layer panel and brush draw packets to that operation.

See `docs/STUDIO_DONOR.md` for execution, limits and verification.
