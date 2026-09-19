# Shape Recipe Flow

Universal Creation can now turn a small data recipe into an explicit deterministic
3D scene. The recipe carries named numbers, nested loops, conditions, numeric
expressions, reusable shape definitions, per-use settings and position-driven
paint. Compilation expands those instructions into the existing closed
`axm.procedural-3d/v0.1` primitive grammar; the established publisher then emits
and independently re-parses the exact GLB bytes.

This is the bounded recipe-flow idea brought across from MorphTile, not the
MorphTile engine embedded inside UC. The behavioral donor is pinned to
`mike-axiom-mir/axm-morphtile@13d83a2b2c0d12644442d3d9e45bcbe0af19876a`,
`core/morphtile.js`, with the original recipe behavior traced to
`379098956c4da962b70ad68b60ea1bb8a75f5028`. The donor's v0.4 format contract
and cross-implementation vectors are named in the receipt as `docs/FORMAT.md`
and `conformance/vectors.json`. The implementation here is native Python fitted
to UC's existing capability, error, publication and evidence boundaries. The
owner directed this integration; the resulting UC contribution remains under
UC's repository license.

The UC route deliberately carries only the recipe behavior it can prove. It
does not embed MorphTile's world-defined-word evaluator, written-motion runtime,
portable-kit importer, or tile-authored interface interpreter. Those are
separate capabilities, not hidden behavior inside a deterministic GLB export.

## Live route

Use creation kind `shape-recipe-asset` (also `recipe-glb-asset` or
`invented-shape-asset`) with `path`, `recipe`, and optional `replace` inputs.

```json
{
  "kind": "shape-recipe-asset",
  "inputs": {
    "path": "creations/lattice.glb",
    "recipe": {
      "schema": "axm.shape-recipe/v0.1",
      "name": "Row",
      "vars": {"count": 8, "gap": 0.5},
      "parts": [{
        "repeat": ["var", "count"],
        "as": "i",
        "body": [{
          "shape": "box",
          "size": [0.2, 0.2, 0.2],
          "pos": [["*", ["var", "gap"], ["var", "i"]], 0, 0]
        }]
      }]
    }
  }
}
```

Expression operators are `var`, `+`, `-`, `*`, `/`, `%`, `min`, `max`,
`floor`, `==`, `!=`, `<`, `>`, `<=`, `>=`, `and`, `or`, `not`, and `if`.
Loop scopes also expose `<name>_of` and `<name>_at`.

## Shapes made from shapes

An optional `definitions` object keeps reusable shape bodies inside the recipe.
A part can then use a definition more than once and change only declared numbers
for that use:

```json
{
  "schema": "axm.shape-recipe/v0.1",
  "name": "Two adjustable rails",
  "definitions": {
    "rail": {
      "vars": {"count": 3, "gap": 1},
      "parts": [{
        "repeat": ["var", "count"],
        "as": "i",
        "body": [{
          "shape": "box",
          "size": [0.4, 0.2, 0.3],
          "pos": [["*", ["var", "gap"], ["var", "i"]], 0, 0]
        }]
      }]
    }
  },
  "paint": {
    "vars": {"span": 4},
    "color": [["min", 1, ["max", 0, ["/", ["+", ["var", "x"], 2], ["var", "span"]]]], 0.25, 0.8]
  },
  "parts": [
    {"use": "rail", "with": {"count": 2}},
    {"use": "rail", "with": {"count": 4}, "pos": [0, 2, 0], "scale": 0.5}
  ]
}
```

Changing the `rail` definition reaches every use. The `with` values are applied
only to that use and never mutate the definition. A definition may itself use
another definition, within the composition bound.

`paint.color` contains three or four expressions over `x`, `y`, `z` and its own
named numbers. UC evaluates those expressions at each generated primitive's
center and writes the resulting material colour into the explicit expanded
specification. This creates position-driven colour across assemblies. It does
not claim MorphTile's finer per-triangle painting.

## Bounds and truth boundary

- Recipe bodies nest at most eight levels and inspect at most 4,000 nodes.
- A recipe carries at most 64 definitions and composition descends through at
  most four definition levels. Missing names, cycles and undeclared `with`
  settings return typed HOLD details.
- UC's current receiver emits at most 128 primitives. A larger declared recipe
  budget does not raise that receiver limit.
- Supported shapes are `box`, `cylinder`, and `pyramid` because those are the
  existing UC primitive contract. Other MorphTile shapes return a typed HOLD.
- Nonzero rotation returns `HOLD_SHAPE_RECIPE_ROTATION_UNSUPPORTED`; the current
  UC primitive receiver cannot preserve it, so the compiler never drops it.
- Unknown variables/operators, malformed nodes, empty output and excessive work
  return typed HOLD details before any file is published.
- Position paint is evaluated per primitive center, not per triangle or vertex.
- A successful result proves deterministic expansion, exact GLB publication and
  bounded decoded-geometry validation. It does not prove rendered appearance,
  aesthetic quality, physics, collision, animation or target-engine import.

The recipe, its canonical SHA-256, effective budgets, generated part count and
pinned donor provenance remain visible in the creation receipt. Named numbers
therefore create a family of shapes without becoming hidden runtime state.
