# Editable Video / Stream Overlay Template Pack

`visual.broadcast.core` gives Universal Creation a source-first foundation for video/program/stream scenes and overlays.

The goal is not to draw a convincing fake live screen. Every live-looking element keeps explicit source, freshness, delivery, scene and output state so a real product can bind it to observed runtime evidence.

## Product surfaces

The product contains ten responsive screens:

- project / scene-set hub;
- scene layout editor;
- source router and health view;
- camera/source frame editor;
- score/status field editor;
- alert/notification editor;
- chat/event-feed editor;
- scene set and switching editor;
- format / safe-area variants;
- review / output.

## Source and state contracts

New primitives preserve exact source/runtime presentation state:

- `source-window` — exact source identity plus crop/fit and health state;
- `camera-slot` — source identity remains separate from crop/framing;
- `status-field` — value, source and freshness are explicit;
- `alert-cue` — unobserved delivery/success cannot be presented as completed;
- `chat-panel` — delivery/source/offline/error state stays visible;
- `scene-state` — preview/live/transition scene identity is exact;
- `overlay-zone` — overlaps/conflicts remain visible;
- `identity-panel` — identity source and transform remain separate;
- `transition-state` — from/to scene identities are explicit;
- `output-monitor` — output target state must come from observed status.

## Format adaptation

Landscape, portrait, square and vertical variants adapt scene geometry without rewriting source bindings or current scene state. Safe-area `math_hooks` remain open to the separate mathematics lane.

## Truth boundary

This pack proves deterministic layout and state contracts only. It does not prove camera capture, network/live delivery, score correctness, message delivery, encoder health, streaming-platform integration, privacy compliance, latency, frame accuracy or aesthetic acceptance.

A convincing preview is never evidence that a live source exists. Consuming products must bind visible source/status/output state to real observations.
