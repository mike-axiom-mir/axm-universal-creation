# Source-Bound Lighting / Post-Process Look Template Pack

`visual.look.core` is the reusable lighting/look foundation for games, software and visual storytelling.

A convincing look preview is presentation, not authoritative world state. Exposure, tone mapping, grade, fog, bloom, post-process layers, scene bindings and platform variants remain separate editable state.

## Surfaces

- project / look hub
- exposure / tone-map editor
- color-grade editor
- fog / atmosphere editor
- bloom / glare editor
- post-process layer-stack editor
- scene / camera binding editor
- platform / performance variant editor
- comparison / preview
- review / export

## Source-truth contract

- `look-source` — exact look identity, source, version, digest, context and purpose;
- `exposure-state` — exact value/range/adaptation source and context;
- `tone-map-state` — exact operator, parameters, output space and source;
- `color-grade-state` — exact transform source, working/output spaces and intensity;
- `fog-atmosphere-state` — exact density/range/color/scattering source and context;
- `bloom-glare-state` — exact threshold/intensity/radius/quality and source;
- `postprocess-layer` — exact ordered layer identity/parameters/blend/scope/source;
- `scene-look-binding` — exact scene/camera/region target, look identity, source and activation;
- `look-platform-variant` — exact base, deltas, platform/performance/accessibility context;
- `look-export-target` — exact look/binding/color-space/variant/runtime requirements.

## Truth boundary

Color grade and post-process effects do not replace source materials, lights, geometry or environment state. A bright preview does not prove the scene contains brighter lights. Visual similarity does not bind a look to a scene. Performance/accessibility variants must preserve required visibility and state legibility.

This pack proves deterministic structural/editability contracts only. It does not prove physical lighting correctness, calibrated color output, accessibility acceptance, GPU cost, target-engine parity, or aesthetic quality.
