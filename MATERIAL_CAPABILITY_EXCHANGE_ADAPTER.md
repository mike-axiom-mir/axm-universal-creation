# Material Capability Exchange Adapter v0.18

Universal Creation can now consume the exact `axm-material-capability-pack/v0.18.0` contract emitted by AXM Material / Surface Fabric and return an exact `axm-material-use-feedback/v0.18.0` receipt.

This adapter is deliberately detached from live Universal Creation topology. Its first bounded use path is material-native:

`Material / Surface capability pack -> exact identity/fingerprint validation -> material-entry/material-family projection -> existing v0.2 donor adapter -> validated Asset Atom package -> v0.18 downstream-use feedback`

## What is adopted

`material-entry` capabilities are adopted only when their portable data URL and explicit channel state can be mapped exactly through the existing Material Donor adapter.

`material-family` capabilities are adopted only when their declared entry membership can be mapped exactly to accepted entries and one texture per supported channel.

A successful adoption emits a `PASS adopted` feedback event carrying the exact source capability ID and the derived Universal Creation Asset Atom ID.

The derived state is detached. `PASS adopted` does **not** mean that the material was silently installed into the live capability graph or promoted into canonical project state.

## What remains HOLD

The first adapter intentionally leaves `sprite-candidate`, `recipe`, and `pattern` capabilities as explicit `HOLD inspected` events. Universal Creation does not yet have a bounded native consumer contract for those v0.18 capability kinds, so this adapter refuses to guess one.

That is a truth boundary, not a failure of the transport contract.

## CLI

```bash
python tools/import_material_capability_pack.py \
  examples/material-capability-packs/painted-metal-v0.18.json \
  --out build/material-capability-consumer.json \
  --feedback-out build/material-use-feedback.json
```

Use `--strict` to fail if any supplied capability remains HOLD.

## Cross-repo proof

The checked-in fixture uses the same v0.18 identity/fingerprint rules as Material / Surface Fabric. The test proves that Universal Creation:

1. validates the exact producer pack identity before use;
2. creates validated detached texture/material Asset Atoms from the material capabilities;
3. preserves unsupported pattern state as HOLD;
4. emits deterministic downstream feedback linked to the exact pack ID/fingerprint;
5. preserves the exact source capability IDs and downstream derived atom IDs.

The feedback receipt can be fed back into Material / Surface Fabric's v0.18 usage ledger without granting it authority over Universal Creation state.

## Truth boundary

This integration proves exact transport identity, byte decoding/hash verification through the donor adapter, detached Asset Atom adaptation, and deterministic use-feedback generation.

It does not prove:

- aesthetic quality;
- PBR correctness;
- physical-material truth;
- renderer parity;
- live topology installation;
- automatic keeper/pattern promotion;
- canonical authority in either repository.

The constitutional merge gate remains the AXM roots: Truth, Agency / non-domination, Continuity, and Wisdom before speed.
