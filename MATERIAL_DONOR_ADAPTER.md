# AXM Material Donor Adapter v0.1

Universal Creation can now consume one explicit interchange format from AXM Material / Surface Fabric:

`axm-material-donor-pack / v0.2.0`

The goal is deliberately narrow:

> **Prove that reusable material/texture ingredients retained by the Material / Surface Fabric can cross into Universal Creation and become valid Asset Atom texture/material descriptors without silently guessing what the pixels mean.**

## First proof boundary

The first bridge is deliberately a **detached adapter tool**, not a new live machine capability:

```bash
python tools/import_material_donor.py \
  examples/material-donor-packs/painted-metal-v0.2.json \
  --strict
```

This keeps the first cross-repository compatibility proof separate from Universal Creation's live capability count and anatomy bindings. Promotion into a live creation route can happen later if real use justifies it; the first experiment does not need to silently enlarge the running machine topology.

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

This means a partially useful donor pack does not have to become all-or-nothing unless the caller asks for `--strict` / `strict=True`.

## Strict versus partial

Default mode may return:

`PARTIAL_EXACT_MATERIAL_DONOR_ADAPTER_WITH_HOLDS`

That result includes accepted entries/families and exact held-state reasons.

With `--strict`, any held donor entry or family fails the adaptation instead. This is useful when a caller requires complete family continuity.

## What is actually proven

The adapter and its CLI tests prove:

- the donor-pack v0.2 structure was accepted;
- explicit donor routing hints were used without semantic guessing;
- local data URLs were decoded;
- exact SHA-256 values were calculated over those decoded bytes;
- accepted donor entries were translated into Asset Atom texture descriptors;
- compatible declared families were translated into Asset Atom material descriptors;
- the resulting package passed the existing Asset Atom deterministic validator;
- the standalone command-line consumer can take a donor JSON file and emit the same validated descriptor result.

## What is not proven

The adapter does **not** prove:

- that donor bytes are a visually valid PNG merely because their data URL says `image/png`;
- that a texture is a physically correct base-color, normal, roughness, metallic, or other PBR map;
- that `donor://` resources are installed in a renderer;
- that Universal Creation rendered the adapted material;
- artistic quality;
- perceptual similarity;
- cross-engine material equivalence;
- that this detached adapter has been promoted into the live Universal Creation capability registry.

Those require later explicit resource materialization/render/host evidence and, separately, a justified live-admission choice rather than stronger wording here.

## Why this is the first reuse proof

The Material / Surface Fabric can now keep a persistent local library and export selected reusable ingredients as donor packs. Universal Creation already has a renderer-neutral Asset Atom grammar for texture/material relationships. This adapter creates the smallest truthful bridge between those two existing systems.

The loop is now structurally testable:

`visual source -> Material / Surface Fabric library -> donor pack -> Universal Creation detached adapter -> validated Asset Atom package`

That is not yet the full visual loop. The next stronger proof would materialize accepted donor bytes into an ordinary creation/runtime that can actually sample or render them, while preserving the same donor identity and evidence.

## Roots

- **Truth** — explicit routing declarations, byte evidence, descriptor validation, held state, detached/live status, and unverified rendering remain separate.
- **Agency / non-domination** — no donor meaning is silently inferred; strict versus partial acceptance is caller-controlled.
- **Continuity** — donor IDs, source metadata, family membership, SHA-256 receipts, and mapping receipts remain inspectable.
- **Wisdom before speed** — unknown or conflicting material state holds, and the first consumer remains detached until a stronger need for live promotion is earned.
