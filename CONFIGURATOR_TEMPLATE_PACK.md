# Editable Equipment / Vehicle / Weapon Configurator Template Pack

`visual.configurator.core` is the source-first configuration and presentation foundation for vehicles, weapons, devices, equipment and loadouts.

It is intended for racing garages, shooter loadouts, item inspectors, tech/component views, modular devices and other products where one base object can receive parts, attachments, variants or materials.

## Surfaces

- project / configurator hub
- configurable object stage
- attachment socket editor
- exploded component editor
- configuration stat editor
- variant / material editor
- compatibility rule editor
- configuration comparison
- preset / loadout editor
- review / export

## Source-truth contract

The important state stays separate and editable:

- `configurable-source` — exact object identity, source, version and digest;
- `attachment-socket` — exact socket identity/type/accepted category/status;
- `component-part` — exact component source, parent socket and source transform;
- `compatibility-rule` — exact subject/target/rule/result/status;
- `config-stat-field` — value, unit, source and configuration context/version;
- `configuration-state` — base identity, equipped attachment set, variants and digest;
- `exploded-view-state` — derived presentation offsets only, never source transforms;
- `config-material-variant` — exact target, variant/source and availability state;
- `config-annotation` — exact target plus content/source/status;
- `configurator-export-target` — visible output requirements.

Visual fit is never treated as proof of compatibility. A component appearing close to a socket does not mean it can attach. Unknown compatibility stays unknown; invalid or conditional configurations remain visible.

Exploded views, turntable-like staging, comparison layouts and exports are derived presentation. They may improve understanding but cannot silently modify the authoritative base object or equipped configuration.

## Candidate census after composition

- 24 style systems
- 186 reusable primitives
- 224 responsive screens
- 22 whole-product archetypes
- 246 exact screen/product definitions in Sticker Registry

## Evidence

The dedicated Visual Template Fabric gate must prove the configurator across compact, standard and wide layouts and six representative viewport shapes, install all exact definitions into Sticker Registry, materialize a parseable configurator gallery and retain the source-truth boundaries of prior template families.

This evidence does not prove real-world mechanical compatibility, attachment fit, stat balance, physical measurements, render quality or aesthetic acceptance. Those require consuming-project evidence.