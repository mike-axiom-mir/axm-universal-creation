# Editable Presentation / Explainer Template Pack

`visual.presentation.core` is a source-first presentation and explainer foundation for game manuals, demos, product storytelling, reports, college/teaching material and AXM explanations.

## Surfaces

- project / presentation hub
- page editor
- narrative outline / section editor
- content block editor
- figure / reusable-artifact editor
- source / citation / evidence editor
- emphasis / layout variants
- speaker notes / review
- sequence / transition preview
- export matrix

## Source-first contracts

- `presentation-page` preserves exact page identity, role and order.
- `content-block` keeps content type, exact content/source and semantic role explicit.
- `source-footnote` binds an exact claim/figure/block target to source and evidence status.
- `figure-frame` preserves exact embedded source/caption identity.
- `presentation-section` preserves ordered page membership.
- `emphasis-cue` may change presentation emphasis but cannot rewrite source meaning.
- `speaker-note` remains non-rendered note state bound to an exact target/source.
- `embed-binding` preserves exact reusable artifact identity/version/view.
- `presentation-transition` remains derived between exact ordered pages and cannot change page order.
- `presentation-export-target` keeps page range/aspect/assets/source/provenance requirements visible.

## Truth boundary

A polished slide/page is not evidence that its claims are true or adequately sourced. Layout, emphasis, sequencing and transitions may shape communication but cannot create evidence or silently alter included source meaning. Embedded diagrams, key art, atlas/showroom views and other artifacts keep exact identity/version/view bindings.

The deterministic proof can establish responsive layout and structural/editability contracts. It does not prove claim truth, source reliability, audience understanding, speaking quality, accessibility compliance or aesthetic acceptance.
