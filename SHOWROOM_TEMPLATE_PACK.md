# Editable 3D Showroom / Gallery Template Pack

`visual.showroom.core` is a source-first presentation foundation for vehicles, products, props and other 3D objects. It is intended to be reusable by game garages, loadout/inspection views, product galleries and comparison tools.

## Surfaces

- project / showroom hub
- hero object stage
- orbit / camera editor
- material / paint editor
- object variant editor
- annotation / callout editor
- side-by-side comparison
- detail / inspection view
- turntable / showcase-motion editor
- review / export

## Source-first contracts

- `showroom-object` preserves exact source asset identity/version.
- `orbit-rig` preserves exact target, pivot and allowed orbit range.
- `camera-preset` keeps projection/lens/transform explicit.
- `material-slot` binds an exact object part to an exact material source.
- `variant-option` preserves exact variant identity, properties and availability/source state.
- `object-annotation` binds content to an exact object/component/local anchor.
- `comparison-object` preserves exact object/variant references and comparable fields.
- `turntable-state` is derived presentation state around an exact object target.
- `measurement-callout` preserves value, unit and source.
- `showroom-export-target` keeps output requirements visible.

## Truth boundary

A convincing showroom preview is not evidence that geometry, scale, materials, specifications, availability or rendering quality are correct. Unknown/missing state remains explicit. Presentation transforms, camera motion and turntable motion never replace source asset state.

The deterministic proof can establish responsive layout and structural/editability contracts. It does not prove renderer fidelity, 3D geometry correctness, physical scale, material realism, lighting quality, product availability or aesthetic acceptance.
