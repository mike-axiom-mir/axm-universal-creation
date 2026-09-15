# Source-Bound HUD Theme / Skin Template Pack

`visual.hud.core` is the reusable HUD foundation for games and interactive products.

A polished HUD preview is not gameplay truth. Components, data bindings, layout anchors, readability rules, platform/input variants, alert semantics and themes remain separate editable state.

## Surfaces

- project / HUD hub
- component library
- layout / anchor editor
- data-binding editor
- readability editor
- alerts / feedback editor
- platform / input variant editor
- theme / skin editor
- comparison / preview
- review / export

## Source-truth contract

- `hud-source` — exact HUD family identity, source, version, digest and owning context;
- `hud-component` — exact component identity/role/source and semantic purpose;
- `hud-layout-anchor` — exact component region/viewport constraints and source state;
- `hud-data-binding` — exact subject/field/source/freshness/fallback state;
- `hud-readability-rule` — exact target/context/threshold/evidence source;
- `hud-safe-region` — exact viewport/platform/source and safe margins;
- `hud-alert-state` — exact semantic alert source, severity, feedback channels and acknowledgement state;
- `hud-platform-variant` — exact base, deltas, device/input context and availability;
- `hud-theme-variant` — exact base theme plus token/component deltas and context;
- `hud-export-target` — exact component/binding/layout/readability/platform/provenance requirements.

## Truth boundary

Screen position does not create a data binding. A meter looking full does not prove the underlying value is full. Icon shape or color alone cannot carry critical gameplay meaning. Theme/skin changes do not rewrite source gameplay state. Platform variants must preserve required semantic feedback and readability.

This pack proves deterministic structural/editability contracts only. It does not prove gameplay correctness, real-device readability, accessibility acceptance, input ergonomics, target-engine rendering or aesthetic quality.
