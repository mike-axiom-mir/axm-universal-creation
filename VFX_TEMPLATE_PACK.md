# Source-Bound VFX / Particle Template Pack

`visual.vfx.core` is the reusable effect-authoring foundation for game effects, interface effects and visual storytelling.

A spectacular preview is not evidence that a runtime/gameplay event occurred. Visual effects stay bound to explicit effect identity, emitters, timing, modules, layers and interaction hooks.

## Surfaces

- project / effect hub
- effect stage
- emitter-state editor
- spawn-region editor
- curves / timing editor
- particle-module editor
- layer / composite editor
- runtime interaction-hook editor
- reduced-effect / performance variant editor
- review / export

## Source-truth contract

- `vfx-source` — exact effect identity, source, version, digest and semantic purpose;
- `emitter-state` — exact trigger, lifetime, rate/burst and enabled state;
- `spawn-region` — exact source shape/transform/dimensions/distribution;
- `emission-curve` — explicit named channel plus time/value state;
- `particle-module` — exact module identity, parameters, order and status;
- `vfx-layer` — exact layer identity, blend/order/depth relation and source;
- `vfx-interaction-hook` — exact subject/event/response/source and status;
- `vfx-timing-event` — exact timeline event marker, source and semantic purpose;
- `reduced-effect-rule` — reduced/minimal variant preserves required semantic feedback;
- `vfx-export-target` — exact source/module/timing/hook/performance/accessibility requirements.

## Truth boundary

Particle motion, flashes, impacts or explosions do not prove damage, collision or gameplay events. Spawn previews do not rewrite source spawn geometry. Layer compositing does not flatten canonical source. Reduced-effect/performance variants preserve required information rather than simply removing effects blindly.

This pack proves deterministic structural/editability contracts only. It does not prove runtime integration, game balance, collision/damage correctness, GPU cost, accessibility acceptance, frame pacing or aesthetic quality.