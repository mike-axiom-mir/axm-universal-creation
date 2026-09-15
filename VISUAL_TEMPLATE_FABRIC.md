# Visual Template / Archetype Fabric

Universal Creation contains one deterministic library of **known visual archetypes** between low-level format scaffolds and finished products. Templates are editable structural starting points, not finished art and not automatic canon.

The public module remains `axm_uc.visual_templates`. Explicit extension packs cover games/product plumbing, creative editors, comics, AXM system surfaces, key art, cards/decks, cinematic/broadcast overlays, diagrams, atlas/map editing, branching narrative, 3D showroom, music, presentation/explainers, character reference, equipment configuration, source-bound UI motion and brand/identity systems. Sticker Fabric remains the immutable/versioned registry bridge. Mathematical work can enrich declared ratios/ranges through `math_hooks` without replacing template identity.

## Current v18 candidate census

- **206 reusable visual/state primitives**
- **26 coherent style systems**
- **244 responsive screen archetypes**
- **24 whole-product archetypes**
- **268 exact screen/product definitions** when explicitly installed into Sticker Registry

Every major family provides compact, standard and wide normalized layouts. Unknown requested variants fail rather than silently falling back.

## Source-bound brand / identity foundation

`visual.brand.core` provides ten identity-system surfaces:

- project / identity hub;
- marks and lockups editor;
- typography editor;
- icon-family editor;
- identity-token editor;
- clearspace / usage-rule editor;
- identity-variant editor;
- brand application editor;
- review / rule audit;
- export matrix.

Its `visual.brand.identity` style is replaceable. Identity source remains explicit:

- `brand-asset-source` preserves exact mark/logo/wordmark source, version, digest and provenance state;
- `brand-lockup` preserves exact asset references, relative layout and approved-use status;
- `brand-type-role` preserves exact font source/style plus semantic role;
- `brand-icon-family` preserves family identity/source/version and exact member references;
- `brand-token` preserves exact value, context/unit, source and usage role;
- `brand-clearspace-rule` preserves exact target and measurement basis;
- `brand-usage-rule` preserves exact subject, context, status and source;
- `brand-application` remains a derived application bound to exact identity inputs;
- `brand-variant` preserves base identity, deltas, intended context and availability;
- `brand-export-target` keeps exact asset/token/rule/format/provenance requirements visible.

A polished mockup never becomes canonical identity merely because it looks convincing. Visual similarity does not merge identity assets. Clearspace rules require explicit measurement basis, and exceptions/restricted variants remain visible.

## Registry and identity

Every built-in screen/product can be wrapped as an immutable Sticker definition. Definitions use exact id/version/digest identity; there is no floating `latest`, silent upgrade or automatic canon.

## CLI

```sh
axm-visual-templates catalog
axm-visual-templates show visual.brand.core
axm-visual-templates render visual.brand.core creations/brand --width 1920 --height 1080
```

Preview/export remains derived inspection output, never authoritative source.

## Evidence gate

```sh
python -m unittest discover -s tests -p 'test_visual_templates.py' -v
python tools/visual_template_proof.py /new/output/path
```

The v18 gate requires:

- exact census: 26 styles / 206 primitives / 244 screens / 24 products;
- all 244 screens stay within six representative viewport shapes;
- exact product screen order and flows resolve across those viewports;
- parseable galleries for all prior proof products plus `visual.brand.core`;
- all 268 screen/product definitions install through Sticker Registry;
- exact identity asset/source/provenance, lockup layout/status, font role/source, icon membership, token value/context, clearspace measurement basis, usage rule status, application binding and variant-base contracts remain present;
- prior motion/configurator/character/presentation/music/showroom/visual-novel/atlas/diagram/broadcast/cinematic/card/key-art/comic/game/AXM boundaries remain intact;
- copy safety, strict variant rejection, invalid-geometry rejection and exact Sticker-slot binding remain intact.

## Truth boundary

Current evidence proves deterministic structural/editability contracts only. It does **not** prove trademark clearance, font/icon licensing, legal rights, market effectiveness, visual quality or accessibility acceptance.

Consuming products must supply real identity/provenance state. Unknown, restricted, deprecated and exception states remain distinguishable. Richer editable source remains authoritative over applications/previews/exports.
