# Visual Creation Grammar v0.1

This layer turns visual prompt vocabulary into a small deterministic composition grammar instead of adding one organ per fashionable slash-command.

It extends the executable procedural visual forge already present in this PR. It does not replace the existing texture, material, pigment, sprite, mesh, vector, palette, gradient, decal, or fixture generators.

## Why this exists

Many useful visual instructions are combinations of the same underlying dimensions:

`subject + decomposition + camera + information + commercial intent + style + environment + time`

For example, `explodedview` is represented as:

`decomposition=exploded + camera=isometric`

and `texturefocus` becomes:

`style=texture-focus + camera=macro`

The aliases remain convenient vocabulary, but they are not separate capability organs.

## Executable grammar axes

The current compiler exposes:

- decomposition: assembled, exploded, cutaway, cross-section, xray, anatomy, ingredient/layer breakdown, deconstructed
- camera: hero, isometric, top-down, macro, studio, cinematic, close-up, motion-freeze
- information: none, infographic, labelled diagram, comparison, before/after, feature callouts
- commercial intent: showcase, lineup, menu, price card, product/promo poster, billboard, magazine ad, packaging
- style: neutral, concept art, blueprint, minimalist, editorial, moody, vibrant, monochrome, retrofuturistic, texture-focus, brand-led, typography-led, abstract, food
- environment: neutral, studio, lifestyle, custom scene, floating, levitating, splash

The original 50 visual shortcut ideas from the research intake are represented as aliases over these axes.

## Scene director

Every compiled recipe now contains a scene-director plan with:

- focus subject
- camera sequence
- lighting direction
- atmosphere direction
- environment notes
- stable layer ordering

This is a plan, not renderer execution.

## Temporal grammar

A visual request can opt into an eight-beat temporal structure:

`opener -> setup -> first-action -> turning-point -> progress -> unique-angle -> final-action -> reveal`

A caller supplies the total duration. The compiler deterministically divides that duration into exact millisecond ranges.

This gives later animation, video, tutorial, cinematic, trailer, and storyboard machinery a shared temporal vocabulary without hard-coding one video editor.

## Creation quality loop

Every recipe carries a non-authoritative quality-loop plan:

`REFERENCE -> GRAMMAR -> BUILD -> RENDER -> INSPECT -> GAP -> GENERALIZE -> REPLAY`

Important boundaries:

- a reference is not quality proof
- a render receipt is not visual-quality proof
- a gap must come from observed evidence
- a game-specific repair should be generalized only when evidence supports a reusable capability
- no stage automatically installs, promotes, merges, or changes the machine

This makes the "largest remaining prototype gap" pattern explicit without pretending the compiler itself can see or judge a rendered result.

## Generator hints

The compiler maps each recipe to reusable forge families such as:

- mesh
- vector-part
- surface
- pigment
- material
- palette
- gradient
- sprite

Hints are planning evidence only. They do not execute the generators.

## Machine use

Python:

```python
from axm_uc.visual_creation_grammar import compile_visual_recipe

recipe = compile_visual_recipe({
    "subject": "robotic globe",
    "aliases": ["3drender", "retrofuturistic", "texturefocus"],
    "temporal": {"enabled": True, "duration_seconds": 10},
})
```

CLI:

```bash
axm-assets grammar-catalog
axm-assets plan examples/visual-request.json
```

Bridge:

```python
operate_visual_expansion(root, {
    "operation": "plan",
    "request": {
        "subject": "modular machine",
        "aliases": ["explodedview", "cinematicshot"]
    }
})
```

## Truth boundary

This module does not:

- infer visual semantics from arbitrary natural-language prompts
- download or execute prompt libraries
- render a scene
- move a camera
- evaluate beauty, usability, realism, fun, or AAA quality
- fetch references
- auto-promote a discovered gap
- grant execution or merge authority

It compiles explicit structured intent into a deterministic, inspectable recipe that other creation machinery can use.
