# Editable Key Art / Poster / Cover Template Pack

`visual.keyart.core` gives Universal Creation a source-first composition foundation for game key art, posters, covers, banners and related promotional/editorial visuals.

The goal is not to generate one attractive flat image and lose control. The goal is to retain meaningful edit handles for the visual system.

## Product surfaces

The product contains ten responsive screens:

- project hub;
- composition editor;
- hero subject staging;
- title / typography editor;
- lighting / effects editor;
- background / atmosphere editor;
- crop / format variants;
- composition variant board;
- review / comparison;
- export matrix.

## Editable composition contracts

New primitives preserve distinct source state:

- `hero-subject` — source, mask, crop/depth and transform remain editable;
- `depth-layer` — foreground/midground/background order remains explicit;
- `focal-mask` — focus guidance never replaces source art;
- `title-lockup` — title text and layout remain separate;
- `credit-block` — exact credits/legal/byline content and placement;
- `lighting-pass` — effects remain derived contributions rather than source authority;
- `crop-safe-frame` — target crop never rewrites source geometry;
- `variant-card` — alternate compositions have exact identities;
- `export-target` — dimensions/crop/quality/file expectations remain explicit.

## Format adaptation

The source composition can be inspected through portrait, landscape, square, banner and other output-safe regions while preserving the richer canonical composition. `math_hooks` expose focal/safe-area ratio ranges so the mathematics lane can later improve crop/layout derivation without changing template identity.

## Truth boundary

This pack proves deterministic visual structure, responsive regions, editability contracts and explicit output targets. It does not prove illustration quality, typography quality, lighting quality, print production, store-platform compliance, target renderer fidelity or aesthetic acceptance.

A generated SVG gallery is inspection evidence for structure only. It is not the final key art and never replaces richer source state.
