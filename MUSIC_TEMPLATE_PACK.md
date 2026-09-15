# Editable Music Visualizer / Album-Art Template Pack

`visual.music.core` is a source-first music-visual identity and reactive-presentation foundation. It is intended for album/single covers, track sequences, music visualizers, game/music presentation and export variants without flattening track truth into decoration.

## Surfaces

- project / music-visual hub
- album / single cover editor
- track identity / source inspector
- waveform / audio-analysis editor
- beat and non-lyrical timing-marker editor
- reactive visual mapping editor
- track-list / sequence editor
- format / crop variants
- playback preview
- review / export

## Source-first contracts

- `music-track-source` preserves exact track identity, source/digest and duration state.
- `music-analysis` keeps analysis algorithm/source/version/status explicit.
- `beat-marker` keeps exact time and observed/derived/manual source status.
- `waveform-source` binds waveform representation to exact track and analysis source.
- `cover-composition` keeps artwork/type/identity layers editable.
- `reactive-visual-layer` requires an explicit input mapping.
- `music-marker-cue` provides named non-lyrical timing/event cues with exact time/source.
- `album-variant` preserves base identity, deltas and output target.
- `track-list-entry` preserves exact track identity and sequence order.
- `music-export-target` keeps track/variant/aspect/timing/provenance requirements visible.

## Truth boundary

A visualizer-looking output is not evidence that beat, waveform, spectral or timing analysis exists. Analysis must be observed or explicitly derived from a declared track source. Unknown/unavailable/stale state remains visible. Reactive visuals and playback previews never replace source audio/project state.

The deterministic proof can establish responsive layout and structural/editability contracts. It does not prove audio-analysis correctness, musical timing quality, loudness/mastering quality, rights/licensing, renderer fidelity or aesthetic acceptance.
