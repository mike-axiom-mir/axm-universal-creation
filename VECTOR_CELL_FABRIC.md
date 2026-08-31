# Vector Cell Fabric

Vector Cell Fabric is the first AXM visual substrate built around **stable cells rather than fixed pixels or one fixed vector drawing**.

A cell keeps one identity while its visible expression may deliberately change with an explicit observation scale or named choice.

The current loop is:

`stable cell body -> explicit observation scale + choice -> exact representation selection -> merge or split -> Paintgun thought -> simulation -> reality materialization`

## Why cells

A raster pixel is one sampled output value. A normal vector asset stores geometry that can be rasterized at different resolutions.

A Vector Cell goes one level higher. It can own:

- stable identity and role;
- local transform;
- several explicit scale-bound representations;
- optional choice-specific representations;
- child cells;
- Paintgun shape, material, color, light, shade and skin state in expression representations.

The cell is not the pixels that eventually appear on a display. It is an inspectable visual state that can choose one known expression before rasterization.

## Merge and split

A representation has one of two modes.

### `expression`

The cell emits one or more Paintgun objects directly.

If that cell also has children, those children are intentionally collapsed for this representation. The receipt records how many child cells were merged out of the active expression.

### `children`

The parent emits no direct object. Its child cells are resolved instead.

This is the first deterministic merge/split rule:

`coarse observation -> parent expression`

`fine observation -> same parent identity -> child cells`

No child detail is invented. Close detail must already exist as explicit cells and representations.

## Chameleon by choice

Scale is not the only selector.

A representation may declare a list of named `choices`. When the caller supplies that choice, an exact choice-specific representation wins over the generic representation at the same scale.

Example:

`panel + medium scale + default -> normal panel`

`panel + medium scale + selected -> highlighted panel`

The cell ID remains `panel` in both cases.

This makes adaptation explicit rather than hidden. The machine can know *why* a different expression was selected.

## Exact resolution

For every active cell, exactly one representation must match the supplied scale and choice.

Zero matches or ambiguous matches are errors. The fabric does not guess.

The resolution receipt exposes:

- fabric digest;
- observation scale and choice;
- cell path;
- selected representation ID;
- representation mode;
- merge/split counts;
- resolved Paintgun-object count;
- exact final thought and digest;
- cinematic SVG projection.

## Paintgun and simulation

Vector Cell Fabric does not create a second renderer.

The resolved cell body becomes an ordinary composition-complete Paintgun thought. That means it can immediately enter the existing loop:

`Vector Cells -> Paintgun thought -> simulate until NO_KNOWN_IMPROVEMENTS -> Paintgun specialist -> exact materialized scene`

The same final thought/projection digest boundary therefore remains in force.

## Resolution independence, carefully stated

Vector geometry can be evaluated at different output sizes without storing a separate pixel image for every size. Rasterization still happens when the result reaches a raster display or output surface.

This does **not** mean infinite physical detail.

Textures, raster effects, physical simulation, browser output, display resolution and human perception can still impose limits.

Vector Cell Fabric adds adaptive structural detail on top of vector geometry. It does not abolish the observation boundary.

## Current v0 boundaries

- maximum 512 visited cells;
- maximum nesting depth 16;
- local translation and uniform scale are implemented;
- rect, circle, ellipse and polygon geometry can be transformed;
- SVG path expressions are allowed only when no cell transform needs to rewrite their path data;
- every emitted object must satisfy the existing Paintgun grammar;
- representation intervals and choices are supplied explicitly;
- no learned LOD invention exists yet;
- no physical equivalence claim is made between merged and split expressions.

## Existing anatomy

This implementation deliberately reuses anatomy already present in the Universal Creation Map rather than inventing a parallel ontology:

- `AXM-11-3D-SPATIAL-C-021-scene-graph`
- `AXM-11-3D-SPATIAL-A-043-level-of-detail-threshold`
- `AXM-11-3D-SPATIAL-C-028-level-of-detail-group`
- `AXM-11-3D-SPATIAL-O-006-level-of-detail-generator`

The live simulation capability currently implements the LOD-group seam and uses the scene-graph seam. Future evidence may justify activating more of that existing anatomy.
