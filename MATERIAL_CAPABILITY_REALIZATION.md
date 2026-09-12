# Material Capability Realization v0.20

Universal Creation can now do more than preserve Material / Surface Fabric capability state as detached descriptors. It can use one selected capability of every current v0.18 kind to generate a real deterministic native SVG creation.

The bounded path is:

`v0.18 capability pack -> v0.19 exact detached intake -> selected material / family / sprite / recipe / pattern state -> native structural realization -> SVG artifact + SHA-256 -> v0.18 PASS reused feedback`

## What actually affects the output

The realization requires exactly one selected capability of each current kind unless the caller explicitly selects IDs when a pack contains more than one:

- `material-entry` — its exact capability fingerprint participates in the native palette seed. The producer image pixels are not sampled.
- `material-family` — the exact family capability participates in creation identity and native material grouping.
- `sprite-candidate` — its producer-declared normalized alpha bounds constrain the native motif region for the matching recipe atlas layer.
- `recipe` — canvas size, layer order, asset IDs, transforms, opacity and blend structure drive the SVG layout.
- `pattern` — slot order, categories and support drive motif category and density.

Changing bounded input state therefore changes the creation identity and/or emitted SVG state.

## Output

`realize_material_capability_pack(...)` emits an SVG file and an `axm.uc.material-capability-realization/v0.1` receipt containing:

- exact source pack ID/fingerprint;
- exact selected capability IDs;
- deterministic creation ID;
- output path, byte size and SHA-256;
- transparent canvas state;
- an exact `axm-material-use-feedback/v0.18.0` receipt.

The feedback action is `PASS reused`, not `rendered`, because Universal Creation is creating a native structural reinterpretation. It is **not** pretending to render the original Material / Surface atlas pixels.

Each feedback event names the same downstream creation ID and states the exact use mode for that capability kind.

## CLI

```bash
python tools/realize_material_capability_pack.py \
  examples/material-capability-packs/full-circulation-v0.18.json \
  build/material-capability-realization.svg \
  --receipt-out build/material-capability-realization.json \
  --feedback-out build/material-capability-realization-feedback.json
```

The output is local and deterministic. No network access or external rendering dependency is required.

## What this proves

This proves that imported material capability state can cross the boundary from detached compatibility into a concrete generated visual artifact while preserving exact lineage.

It also proves that Material Fabric can receive a stronger class of evidence than descriptor adoption: the capability directly influenced a generated downstream creation.

## What it does not prove

The v0.20 path does **not** claim:

- that producer PNG/WebP atlas pixels were rendered or sampled;
- faithful visual equivalence with the Material / Surface recipe renderer;
- semantic recognition of an alpha sprite candidate;
- browser/raster pixel parity for the SVG;
- aesthetics, realism or taste;
- PBR/BRDF or physical-material correctness;
- live Universal Creation topology installation;
- automatic canonical promotion or producer-memory authority.

The generated SVG is observed output. Its meaning beyond the explicitly recorded structural inputs remains bounded by the evidence.

## Roots

- **Truth:** native reinterpretation is distinguished from faithful producer-pixel rendering.
- **Agency / non-domination:** use evidence does not grant either repository authority over the other.
- **Continuity:** pack -> selected capability IDs -> creation ID -> output hash -> feedback stays inspectable.
- **Wisdom before speed:** the system first proves a small deterministic real creation path rather than claiming a universal renderer bridge.
