# Editable Cinematic Title / Credits / Overlay Template Pack

`visual.cinematic.core` gives Universal Creation a source-first foundation for title cards, chapter/intertitle cards, lower thirds, subtitles/captions, credits, transitions and timed overlays.

The goal is not to bake text into finished frames. Exact content, layout, timing, safe-area adaptation and transition state remain independently editable.

## Product surfaces

The product contains ten responsive screens:

- project / sequence hub;
- title card editor;
- chapter / intertitle editor;
- lower-third editor;
- subtitle / caption editor;
- credits editor;
- timed overlay timeline;
- transition editor;
- aspect / safe-area variants;
- review / export.

## Exact source contracts

New primitives preserve timed source state:

- `title-card` — text, layout and timing remain separate;
- `lower-third` — content, anchor and duration are explicit;
- `subtitle-cue` — exact text and start/end timing stay inspectable;
- `credit-line` — content and order remain exact;
- `time-cue` — start and end are required;
- `safe-zone` — format guides cannot rewrite source layout;
- `transition-cue` — transitions remain derived between source states;
- `chapter-marker` — label plus exact timeline location;
- `overlay-track` — overlaps/conflicts remain visible;
- `logo-lockup` — source identity and transform stay separate.

## Format adaptation

Title/subtitle safe regions and aspect variants are represented explicitly. Landscape, portrait, square and vertical outputs can adapt placement without silently changing exact words, cue timing or richer source composition. `math_hooks` expose safe-area ratios for the separate mathematics lane.

## Truth boundary

This pack proves deterministic layout, exact timing/content contracts, responsive variants and editable source separation. It does not prove typography quality, subtitle reading speed, credit accuracy, motion quality, renderer fidelity, video encoding, platform compliance or aesthetic acceptance.

Rendered SVG galleries are structural inspection evidence only. They are not final film/video frames and never replace the editable source state.
