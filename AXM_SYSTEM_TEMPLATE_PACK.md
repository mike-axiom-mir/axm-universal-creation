# AXM System / Monolith Visual Template Pack

`axm.system.shell` is a reusable visual foundation for AXM-native control surfaces. It is part of the existing Visual Template Fabric v1 schema and uses the same responsive resolver and immutable Sticker Registry bridge.

## Surfaces

The product contains twelve coordinated screens:

- home / current-state overview;
- exact registry browser;
- capability browser;
- monolith/cartridge loader;
- machine-state inspector;
- evidence/truth review;
- workflow/creation-flow view;
- specialist perspectives;
- machine workfloor;
- snapshots/continuity;
- settings/policy;
- recovery/repair.

## Progressive detail

The shell is designed so ordinary use does not require understanding the deepest machine representation. Summary state is visible first; source, evidence, dependencies and lower-level detail are available when they matter.

This is a presentation rule only. The underlying canonical state remains richer than any simplified view.

## Reusable contracts

New primitives include:

- `truth-state` — observed/inferred/proposed/blocked/unknown with visible source;
- `capability-card` — exact capability identity and availability;
- `registry-entry` — exact registered item/version, no floating latest;
- `evidence-chip` — evidence state linked to source;
- `state-diff` — explicit before/after difference;
- `cartridge-card` — pinned portable package and compatibility state;
- `specialist-card` — perspective/contribution with evidence field;
- `workfloor-lane` — bounded lane tied to shared state;
- `snapshot-entry` — checkpoint with verification and explicit restore;
- `recovery-choice` — bounded recovery option with visible consequence.

## Truth boundary

The template pack proves only structural layout/state contracts. It does not prove real cartridge mounting, machine execution, snapshot restore, recovery success, capability availability or runtime evidence. A product using these templates must connect displayed status to its actual observed machine state.

The layered metallic/glass `axm.machine.glass` style is a starting visual system, not canonical AXM identity. Products may replace it while retaining the structural contracts.
