# Source-Bound Inventory / Item Reference Template Pack

`visual.inventory.core` is the reusable inventory/item foundation for games and interactive products.

Item presentation is not gameplay truth. Identity, ownership, quantities, durability, stats, slots, compatibility, provenance and visual variants remain separate editable state.

## Surfaces

- project / item hub
- item identity / instance inspector
- inventory grid / container editor
- equipment slot / loadout editor
- stats / durability / quantity editor
- compatibility-rule editor
- item comparison editor
- icon / rarity / presentation variant editor
- ownership / provenance history
- review / export

## Source-truth contract

- `item-source` — exact item identity, source, version, owner/context and provenance;
- `inventory-instance` — exact item instance, owner/container and lifecycle status;
- `item-stack-state` — exact quantity/capacity/unit/source/freshness;
- `item-durability-state` — exact value/range/unit/source and condition status;
- `equipment-slot` — exact slot identity, accepted categories, occupancy and source;
- `item-compatibility-rule` — exact subjects, rule, result, source and status;
- `item-stat-field` — exact value, unit, source, context/version and confidence/status;
- `item-presentation-variant` — exact base item, visual deltas, context and source;
- `item-comparison-state` — exact compared identities/configurations, fields and source;
- `inventory-export-target` — exact identity/stat/ownership/slot/compatibility/provenance requirements.

## Truth boundary

An icon, rarity color, card frame, inventory position or "equipped-looking" preview never proves item ownership, rarity, equip state or compatibility. Stat bars never replace exact value/unit/source. Visual comparison does not establish an objective winner. Presentation variants may change the visual language while preserving exact item identity and gameplay semantics.

This pack proves deterministic structural/editability contracts only. It does not prove game balance, economy design, item usefulness, runtime ownership correctness, input ergonomics, accessibility acceptance or aesthetic quality.
