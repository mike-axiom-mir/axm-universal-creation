# Editable Cinematic Title / Credits / Trailer Overlay Pack

`visual.cinematic.core` gives Universal Creation a source-first foundation for game intros, trailers, chapter cards, lower-thirds, subtitles/captions, credits, end cards and other timed overlays.

The goal is not to burn text/effects into a video and lose control. Exact text, timing, track order, shot markers, transition-safe regions and derived output targets remain independently editable state.

## Product surfaces

The product contains eleven responsive screens:

- project hub;
- title-card editor;
- lower-third editor;
- chapter/beat-card editor;
- subtitle/caption editor;
- credits editor;
- overlay timeline;
- transition/safe-zone editor;
- trailer overlay / beat layout;
- end-card editor;
- review / export.

## Timed source contracts

- `title-card` — text, timing and layout remain separate;
- `lower-third` — identity and duration/transition timing remain explicit;
- `subtitle-cue` — exact text, speaker and timecode are source state;
- `credit-entry` — names/roles remain exact rather than inferred;
- `timeline-cue` — named events use explicit time ranges;
- `transition-safe-zone` — transitions cannot silently hide required content;
- `overlay-track` — track order and timing remain explicit;
- `shot-marker` — shot/beat/chapter identity and time are exact;
- `end-card` — content and duration remain explicit;
- `legal-line` — exact legal/disclaimer text remains source state.

## Truth boundary

This pack proves deterministic layout/timing contracts, responsive geometry and source separation. It does not prove motion-render quality, subtitle transcription accuracy, trailer editorial quality, transition rendering, platform compliance or aesthetic acceptance.

Generated SVG galleries are structural snapshots only; real motion behavior must be bound to actual timeline/media state by the consuming product.
