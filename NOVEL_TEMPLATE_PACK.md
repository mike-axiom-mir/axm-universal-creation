# Editable Visual-Novel / Branching Narrative Template Pack

`visual.novel.core` is a source-first visual-novel and branching narrative foundation inside the existing AXM Visual Template Fabric.

## Surfaces

- project / narrative hub
- scene / background editor
- character staging editor
- dialogue / voice-reference editor
- choice / condition editor
- branch graph editor
- runtime state / flag inspector
- narrative history / decision log
- save / checkpoint editor
- review / export

## Source-first contracts

The pack keeps story meaning separate from presentation:

- `scene-background` keeps exact source identity separate from crop/transform.
- `character-stage` keeps character identity, pose, expression, source and placement explicit.
- `dialogue-block` keeps exact speaker, text and voice/audio reference.
- `choice-option` keeps exact choice id, label, destination and availability conditions.
- `branch-node` keeps exact node identity and edge references.
- `story-flag` keeps flag name, value and change/source state inspectable.
- `history-entry` keeps ordered event/dialogue/choice history with source.
- `save-checkpoint` binds an exact restorable state identity and digest.
- `scene-transition` remains derived between exact source/destination states.
- `novel-export-target` keeps included assets/text/branch/state requirements visible.

## Truth boundary

A convincing scene does not prove that a character is present, that dialogue was spoken, that a choice exists, or that a branch is reachable. Runtime state must come from real project/runtime state. Unknown or unresolved flags/targets remain visible rather than being fabricated.

The deterministic proof can establish structural/editability contracts and responsive geometry. It does not establish story quality, branch correctness, character continuity, voice performance, localization quality, save compatibility across future versions or aesthetic acceptance.
