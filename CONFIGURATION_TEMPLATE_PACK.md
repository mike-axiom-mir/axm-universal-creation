# Editable Vehicle / Game-Equipment Configuration Template Pack

`visual.configuration.core` is a source-first configuration foundation for game vehicles, mounted equipment, loadouts and other socket/attachment-driven assets. It is designed to reuse the showroom/garage work while keeping actual configuration state separate from presentation.

## Surfaces

- project / configuration hub
- base asset / configuration identity editor
- socket / mount graph editor
- attachment / compatibility editor
- configuration builder
- stat / evidence editor
- exploded / detail presentation editor
- material / paint / finish editor
- configuration comparison
- review / export

## Source-first contracts

- `config-base-asset` preserves exact base identity, source/version and configuration schema.
- `config-socket` preserves exact parent, anchor, type and constraints.
- `config-attachment` preserves exact item identity/source/version and compatible socket types.
- `compatibility-rule` keeps involved IDs, condition and source explicit.
- `configuration-state` preserves exact base + socket-to-attachment bindings and digest.
- `configuration-stat` preserves value, unit/context, source and derivation status.
- `exploded-part` is derived presentation around an exact part/attachment reference and parent.
- `configuration-material` preserves exact part-to-material/paint source bindings.
- `configuration-comparison` preserves exact configuration references and shared dimensions.
- `configuration-export-target` keeps required configuration, evidence and provenance state visible.

## Truth boundary

A part that visually fits a mount is not evidence that it is compatible. A stat bar is not evidence of a measured gameplay value. An exploded view is not source geometry. Compatibility, socket identity, bindings, stat source/derivation and material source remain explicit.

This pack is intended for fictional/game equipment and vehicle configuration. It models game/product state and presentation structure; it is not a real-world weapon engineering or construction system.

The deterministic proof can establish responsive geometry and structural/editability contracts. It does not prove physical fit, real-world engineering, gameplay balance, asset quality, renderer fidelity or aesthetic acceptance.
