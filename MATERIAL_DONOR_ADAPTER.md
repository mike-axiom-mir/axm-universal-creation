# AXM Material Donor Adapter v0.1

Universal Creation can now consume one explicit interchange format from AXM Material / Surface Fabric:

`axm-material-donor-pack / v0.2.0`

The goal is deliberately narrow:

> **Prove that reusable material/texture ingredients retained by the Material / Surface Fabric can cross into Universal Creation and become valid Asset Atom texture/material descriptors without silently guessing what the pixels mean.**

## Route

The live handle is:

`import-material-donor-pack`

Example:

```bash
PYTHONPATH=src python -m axm_uc create examples/requests/import_material_donor_pack.json
```

The adapter performs:

`donor pack -> validate exact donor version -> inspect explicit channel hints -> decode portable image data URLs -> SHA-256 donor bytes -> create Asset Atom texture descriptors -> map exact declared families -> run existing Asset Atom validator -> READY / PARTIAL HOLD / FAIL`

It reuses the existing `axm.asset-atom-package/v0.1` grammar rather than inventing a parallel material representation inside Universal Creation.

## Entry mapping

A donor entry is accepted only when all of these are true:

- it has a stable donor entry ID;
- its `usage.channelHint` exactly names a channel already supported by Asset Atom textures;
- its image payload is present as a decodable data URL;
- its declared MIME type matches the data URL MIME type.

Accepted payload bytes receive a fresh SHA-256 digest. The resulting Asset Atom texture resource uses a `donor://` URI plus that digest.

The adapter does **not** infer a missing channel from:

- the image appearance;
- filename words;
- average color;
- generator source;
- a model guess.

`unassigned` remains a visible HOLD.

## Family mapping

A donor family may become one Asset Atom `material` atom when:

- every family member was accepted as a texture entry;
- every member has one supported explicit channel;
- no two family members claim the same channel.

The material atom binds those exact texture atoms through `texture_bindings`.

A family is held when a member is unavailable/unmappable or when two members collide on the same channel. Accepted standalone texture entries remain reusable texture roots even when a family holds.

This means a partially useful donor pack does not have to become all-or-nothing unless the caller asks for `strict: true`.

## Strict versus partial

Default mode may return:

`PARTIAL_EXACT_MATERIAL_DONOR_ADAPTER_WITH_HOLDS`

That result includes accepted entries/families and exact held-state reasons.

With:

```json
{"strict": true}
```

any held donor entry or family fails the adaptation instead. This is useful when a caller requires complete family continuity.

## What is actually proven

The adapter proves:

- the donor-pack v0.2 structure was accepted;
- explicit donor routing hints were used without semantic guessing;
- local data URLs were decoded;
- exact SHA-256 values were calculated over those decoded bytes;
- accepted donor entries were translated into Asset Atom texture descriptors;
- compatible declared families were translated into Asset Atom material descriptors;
- the resulting package passed the existing Asset Atom deterministic validator.

## What is not proven

The adapter does **not** prove:

- that donor bytes are a visually valid PNG merely because their data URL says `image/png`;
- that a texture is a physically correct base-color, normal, roughness, metallic, or other PBR map;
- that `donor://` resources are installed in a renderer;
- that Universal Creation rendered the adapted material;
- artistic quality;
- perceptual similarity;
- cross-engine material equivalence.

Those require later explicit resource materialization/render/host evidence rather than stronger wording here.

## Why this is the first reuse proof

The Material / Surface Fabric can now keep a persistent local library and export selected reusable ingredients as donor packs. Universal Creation already had a renderer-neutral Asset Atom grammar for texture/material relationships. This adapter creates the smallest truthful bridge between those two existing capabilities.

The loop is now structurally testable:

`visual source -> Material / Surface Fabric library -> donor pack -> Universal Creation adapter -> validated Asset Atom package`

That is not yet the full visual loop. The next stronger proof would materialize accepted donor bytes into an ordinary creation/runtime that can actually sample or render them, while preserving the same donor identity and evidence.

## Roots

- **Truth** — explicit routing declarations, byte evidence, descriptor validation, held state, and unverified rendering remain separate.
- **Agency / non-domination** — no donor meaning is silently inferred; strict versus partial acceptance is caller-controlled.
- **Continuity** — donor IDs, source metadata, family membership, SHA-256 receipts, and mapping receipts remain inspectable.
- **Wisdom before speed** — unknown or conflicting material state holds rather than being guessed away to make the integration look complete.
