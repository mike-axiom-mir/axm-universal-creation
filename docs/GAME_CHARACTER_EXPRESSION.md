# Game character expressions and stances

`axm_uc.game_character_expression` derives explicit static face expressions
and storytelling stances from a renderer-neutral `axm.surface-3d/v0.1` mesh.
It requires caller-authored component roles, sides, parent relationships and
pivots; it never guesses a face or skeleton from shape.

## Available controls

Expressions affect only declared eyes, brows and mouths:

- `neutral`
- `curious`
- `mischief`
- `alarmed`
- `determined`

Stances compose rigid transforms through the declared parent tree:

- `neutral`
- `mechanic-ready`
- `comic-sneak`
- `victory`

Non-uniform eye and mouth changes transform existing authored normals with an
inverse-transpose matrix instead of rebuilding them. This retains deliberate
smooth/flat shading. The capability does not change materials, so realistic PBR
and every opt-in render realization remain independently selectable.

## Identity contract

At least one caller-declared identity component is required. All protected
identity components must share one parent transform. They cannot receive local
expression or stance transforms, but may follow that parent's rigid pose. The
derivation verifies:

- each protected component's radial shape signature around its authored pivot;
- pairwise distances between protected identity pivots;
- pairwise spacing between authored eye pivots;
- the validity of the actual derived GLB.

These checks preserve explicitly declared rigid identity relationships. They do
not establish perceptual character recognition in general, topology suitable
for skinning, deformation quality, contact, collision or gameplay readability.

## Usage

```sh
axm-assets character-expression-catalog
axm-assets character-expression request.json output/mischief \
  --expression mischief --stance comic-sneak
```

The request contains exactly `mesh` and `parts`. Publication is transactional,
refuses overwrite, and emits canonical `source.json`, `realization.json`, a
`character-expression.json` receipt and an actual `asset.glb`.

The Blender proof in `tools/blender/character_expression_roundtrip.py` combines
four checked poses with the existing portable painted realization, re-imports
all GLBs into a fresh scene and renders both source and re-imported states. Its
receipt is `docs/evidence/character-expression-roundtrip-2026-09-13.json`.

## Truth boundary

This is static geometry posing. It creates no skeleton, skin weights,
animation clips, transitions or runtime controller. It does not prove contacts,
collision clearance, engine compatibility, game-distance readability or
performance. Animation timing and weight remain the next separate capability.
