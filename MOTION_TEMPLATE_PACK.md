# Source-Bound UI Motion / Transition Template Pack

`visual.motion.core` is the reusable motion-system foundation for games, software, editors and AXM surfaces.

Motion is treated as a representation of state change, not as authority to create state.

## Surfaces

- project / motion-system hub
- state-transition editor
- focus / navigation motion editor
- spatial / shared-element continuity editor
- timing / easing editor
- interruption / recovery editor
- progress / loading motion editor
- reduced-motion variant editor
- trigger matrix
- review / export

## State-truth contract

- `motion-state` — exact source and target state identities;
- `transition-edge-state` — exact trigger, source, target, duration and completion semantics;
- `timing-curve` — explicit duration/easing/bounded parameters;
- `focus-motion-path` — exact prior/next focus identities and semantic order;
- `spatial-anchor-transition` — exact source/target anchor identities;
- `interruption-recovery` — interruption, cancellation and recovery/rollback destination;
- `progress-motion-state` — observed progress/status source; animation cannot manufacture completion;
- `reduced-motion-rule` — reduced/off variant preserves the same semantic state result;
- `motion-trigger` — exact event/input/state-change source and repeat/suppression behavior;
- `motion-export-target` — exact transition, timing, accessibility and runtime requirements.

## Truth boundary

A fade, slide, spring, progress pulse or celebratory effect is never evidence that the underlying state changed. Completion is not inferred from animation end. Focus order is not derived from screen position. Shared-element continuity requires exact source/target anchors rather than visual similarity. Interrupted transitions keep their recovery/rollback state explicit.

Reduced-motion is first-class, not an afterthought. Its job is to preserve meaning and destination while reducing unnecessary travel, parallax, flashing or other motion burden.

This pack proves deterministic structural/editability contracts only. It does not by itself prove perceptual quality, vestibular comfort, target-framework behavior, frame pacing, input latency or accessibility acceptance.