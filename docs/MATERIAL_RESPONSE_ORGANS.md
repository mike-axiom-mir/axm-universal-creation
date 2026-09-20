# Material response organs v0.1

This intake adds the user-supplied Opus material-response update above UC's existing texture/channel material data.

It contains 13 response families composed from eight bounded behaviors: subsurface, sheen, anisotropy, clear coat, breakup, transmission, iridescence and wear layering.

## What is implemented now

- exact family/variant lookup and deterministic deep overrides;
- explicit active-organ detection;
- zero-weight/no-effect organ inputs are treated as true no-ops;
- material-graph schema can name a response family/variant/overrides beside existing parameters/bindings;
- unknown response keys/families fail closed;
- `axm-rich-materials response-catalog` and `axm-rich-materials response <family>` expose the contract;
- supplied pack/organ/schema data is retained in the installed Python package.

## Evidence boundary

The supplied standalone reference host was rerun before intake and passed 8/8 organ checks. That evidence belongs to that reference host.

**UC's renderers have not yet earned those receipts.** Resolution therefore returns `HOLD_RENDERER_BINDING_NOT_TESTED` whenever active organs are present. This is intentional: an unbound organ must not silently collapse into ordinary plastic while pretending the requested material behavior was realized.

Texture/channel values remain source values. A response layer describes behavior above them; it does not erase or replace a supplied base-color/roughness/etc map.

Source archive SHA-256: `9b263ddd536c7f9aa1b6640ad7672283c0e30e7c2b818a7ee23076aafdd1a363`

Declared source response-pack SHA-256: `cc101f7f975e4334570b89d3dacede28e537f6ae09fd11af49d9864a2d064cf5`
