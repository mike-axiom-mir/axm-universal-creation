# Visual Template / Archetype Fabric

Universal Creation contains one deterministic library of **known visual archetypes** between low-level format scaffolds and finished products. Templates are editable structural starting points, not finished art and not automatic canon.

The public module remains `axm_uc.visual_templates`. Explicit extension packs now cover games/product plumbing, creative editors, comics, AXM system surfaces, key art, cards/decks, cinematic overlays, video/broadcast overlays, evidence-aware diagrams, world-map/lore-atlas editing and branching visual novels. Sticker Fabric remains the immutable/versioned registry bridge. Mathematical work can enrich declared ratios/ranges through `math_hooks` without replacing template identity.

## Current v11 candidate census

- **136 reusable visual/state primitives**
- **19 coherent style systems**
- **174 responsive screen archetypes**
- **17 whole-product archetypes**
- **191 exact screen/product definitions** when explicitly installed into Sticker Registry

Every major family provides compact, standard and wide normalized layouts. Unknown requested variants fail rather than silently falling back.

## Product foundations

The catalog retains the merged game, creative-editor, comic, AXM-system, key-art, card/deck, cinematic, broadcast, diagram and atlas products, and adds `visual.novel.core`.

## Branching visual-novel foundation

`visual.novel.core` provides ten source-first surfaces:

- project / narrative hub;
- scene / background editor;
- character staging editor;
- dialogue / voice-reference editor;
- choice / condition editor;
- branch graph editor;
- runtime state / flag inspector;
- narrative history / decision log;
- save / checkpoint editor;
- review / export.

Its `visual.novel.story` style is replaceable. Narrative source truth remains explicit:

- `scene-background` keeps source identity separate from crop/transform;
- `character-stage` keeps exact character identity, pose, expression, source and placement;
- `dialogue-block` preserves exact speaker, text and voice/audio reference;
- `choice-option` requires exact choice id, label, destination and conditions;
- `branch-node` preserves exact node identity and incoming/outgoing references;
- `story-flag` preserves flag name, value and source/change point;
- `history-entry` preserves ordered observed/imported/derived history;
- `save-checkpoint` binds exact restorable story state and digest;
- `scene-transition` remains derived between exact source/destination states;
- `novel-export-target` keeps branch/assets/text/state requirements visible.

A convincing rendered scene does not prove that a character is present, dialogue was spoken, a choice exists, or a branch is reachable. Unknown or unresolved runtime state remains visible rather than being fabricated.

## Registry and identity

Every built-in screen/product can be wrapped as an immutable Sticker definition. Definitions use exact id/version/digest identity; there is no floating `latest`, silent upgrade or automatic canon.

## CLI

```sh
axm-visual-templates catalog
axm-visual-templates show visual.novel.core
axm-visual-templates render visual.novel.core creations/visual-novel --width 1920 --height 1080
```

Preview/export remains derived inspection output, never authoritative source.

## Evidence gate

```sh
python -m unittest discover -s tests -p 'test_visual_templates.py' -v
python tools/visual_template_proof.py /new/output/path
```

The v11 gate requires:

- exact census: 19 styles / 136 primitives / 174 screens / 17 products;
- all 174 screens stay within six representative viewport shapes;
- exact product screen order and flows resolve across those viewports;
- parseable galleries for all prior proof products plus `visual.novel.core`;
- all 191 screen/product definitions install through Sticker Registry;
- scene/background source, exact character identity/pose/expression, dialogue speaker/text/voice refs, choice targets/conditions, branch node/edge identity, flags, history sequence/source and save state/digest remain present;
- prior atlas/diagram/broadcast/cinematic/card/key-art/comic/game/AXM source boundaries remain intact;
- copy safety, strict variant rejection, invalid-geometry rejection and exact Sticker-slot binding remain intact.

## Truth boundary

Current evidence proves deterministic structural/editability contracts only. It does **not** prove story quality, branch correctness, character continuity, voice performance, localization quality, save compatibility across future versions or aesthetic acceptance.

Consuming products must provide real project/runtime state. Unknown, unresolved, unavailable and incompatible state stays distinguishable. Richer editable source remains authoritative over previews/exports.
