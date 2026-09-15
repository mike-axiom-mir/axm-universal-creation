# Editable Card / Deck Template Pack

`visual.cards.core` gives Universal Creation a source-first foundation for game cards, ability cards, collectible/lore cards, deck-building interfaces and printable card sets.

The goal is not to generate one attractive card image and lose control. Face/back geometry, artwork, text, statistics, rules, costs, rarity, finish, deck membership and physical-output guides remain separately editable state.

## Product surfaces

The product contains eleven responsive screens:

- project / set hub;
- card face editor;
- card back editor;
- artwork editor;
- text / statistics editor;
- ability / rules editor;
- rarity / style editor;
- finish / foil editor;
- deck builder;
- print / sheet layout;
- review / export.

## Source contracts

New primitives preserve distinct state:

- `card-frame` — named face/back geometry remains editable;
- `artwork-window` — source artwork and crop remain separate;
- `stat-block` — statistic labels and values remain explicit pairs;
- `ability-row` — exact rules text is retained as source state;
- `rarity-badge` — rarity cannot depend on color alone;
- `cost-symbol` — value and resource type are both explicit;
- `card-state` — ownership/deck/playability state stays visible;
- `deck-slot` — deck membership points to an exact card reference;
- `foil-pass` — decorative finish never replaces base artwork;
- `print-safe-frame` — trim/bleed/safe guides never rewrite source layout.

## Digital and physical variants

One card source can support screen, deck-builder and physical-print targets. Print sheets expose trim, bleed, safe areas and front/back pairing without promoting those derived guides into the canonical card layout. `math_hooks` retain art/text-area and bleed/safe-area ranges for later mathematical improvement.

## Truth boundary

This pack proves deterministic layout/state contracts, responsive geometry and source separation. It does not prove card-game balance, rules correctness, illustration quality, typography quality, foil rendering, printer calibration, color management, physical manufacturing or aesthetic acceptance.

Generated SVG galleries are structural evidence only and never replace richer editable source state.
