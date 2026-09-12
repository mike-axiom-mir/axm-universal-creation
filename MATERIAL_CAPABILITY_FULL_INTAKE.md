# Material Capability Full Intake v0.19

Universal Creation can now consume every capability kind currently emitted by AXM Material / Surface Fabric's `axm-material-capability-pack/v0.18.0` without pretending that detached intake is live installation or visual proof.

The bounded path is:

`Material / Surface Fabric capability pack -> exact v0.18 identity validation -> material Asset Atoms + detached sprite / recipe / pattern descriptors -> exact v0.18 use feedback`

## What is adopted

### material-entry / material-family

These still use the existing material-native bridge:

`v0.18 capability -> synthetic donor v0.2 state -> existing Material Donor adapter -> validated detached Asset Atom package`

Portable material bytes are decoded and SHA-256 hashed by that existing adapter. Channel meaning still comes only from explicit producer declarations.

### sprite-candidate

A bounded `axm.uc.material-sprite-candidate/v0.1` descriptor preserves:

- exact source capability ID/fingerprint;
- source atlas ID;
- producer alpha-derived normalized bounds;
- observed bounds/coverage/component state when present;
- source-index provenance.

This is **not** semantic recognition and does not prove that source atlas bytes are installed or rendered by Universal Creation.

### recipe

A bounded `axm.uc.material-recipe/v0.1` descriptor accepts exact `axm-premade-composition/v0.12.0` state when:

- the recipe is deterministic JSON;
- transparent output remains `true`;
- its layer list is within the adapter bound;
- every layer has an explicit source asset ID.

The exact recipe, producer fingerprint, pack reference and lineage are retained. Descriptor adoption does not render the recipe, install its atlases, or claim visual quality.

### pattern

A bounded `axm.uc.material-pattern/v0.1` descriptor preserves explicit v0.15 keeper-derived structure, including support and ordered slots.

Support remains recurrence evidence only. Intake does not convert the pattern into a Universal Creation preference model, active generation rule, or canonical memory update.

## Feedback

Every exact adoption emits a deterministic `PASS adopted` event in `axm-material-use-feedback/v0.18.0`, preserving the producer capability ID and one or more downstream detached IDs.

A capability that cannot satisfy its bounded projection remains `HOLD inspected`. Strict mode turns any HOLD into a failed intake rather than manufacturing success.

## CLI

```bash
python tools/import_material_capability_pack_full.py \
  examples/material-capability-packs/full-circulation-v0.18.json \
  --strict \
  --out build/full-material-intake.json \
  --feedback-out build/full-material-feedback.json
```

## Cross-repo circulation fixture

`examples/material-capability-packs/full-circulation-v0.18.json` contains one capability of each current v0.18 kind:

- material entry;
- material family;
- alpha sprite candidate;
- deterministic composition recipe;
- keeper-derived pattern.

The repository tests require all five to reach bounded detached `PASS adopted` state while preserving `live_topology_modified=false`, `canonical_state_modified=false`, and `rendering_verified=false`.

The resulting feedback is intended to be validated and ingested by Material / Surface Fabric's v0.18 usage ledger as the first exact two-repository circulation proof.

## Truth boundary

This integration proves contract identity, bounded descriptor compatibility, material byte/hash validation where portable bytes are present, lineage preservation and exact feedback generation.

It does **not** prove:

- aesthetic improvement;
- sprite semantic meaning;
- recipe rendering;
- pattern preference or quality;
- PBR correctness or physical truth;
- runtime atlas availability;
- live Universal Creation topology installation;
- automatic canonical promotion in either repository.

The AXM roots remain the constitutional merge gate: Truth, Agency / non-domination, Continuity, and Wisdom before speed.
