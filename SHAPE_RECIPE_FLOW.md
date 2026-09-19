# Shape Recipe Flow

Universal Creation can now turn a small data recipe into an explicit deterministic
3D scene. The recipe carries named numbers, nested loops, conditions and numeric
expressions. Compilation expands those instructions into the existing closed
`axm.procedural-3d/v0.1` primitive grammar; the established publisher then emits
and independently re-parses the exact GLB bytes.

This is the bounded recipe-flow idea brought across from MorphTile, not the
MorphTile engine embedded inside UC. The behavioral donor is pinned to
`mike-axiom-mir/axm-morphtile@efc3e95eb31450b8f65bec81fbf5c2edb85ca3a5`,
`core/morphtile.js`. The implementation here is native Python fitted to UC's
existing capability, error, publication and evidence boundaries. The owner
directed this integration; the resulting UC contribution remains under UC's
repository license.

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

## Bounds and truth boundary

- Recipe bodies nest at most eight levels and inspect at most 4,000 nodes.
- UC's current receiver emits at most 128 primitives. A larger declared recipe
  budget does not raise that receiver limit.
- Supported shapes are `box`, `cylinder`, and `pyramid` because those are the
  existing UC primitive contract. Other MorphTile shapes return a typed HOLD.
- Nonzero rotation returns `HOLD_SHAPE_RECIPE_ROTATION_UNSUPPORTED`; the current
  UC primitive receiver cannot preserve it, so the compiler never drops it.
- Unknown variables/operators, malformed nodes, empty output and excessive work
  return typed HOLD details before any file is published.
- A successful result proves deterministic expansion, exact GLB publication and
  bounded decoded-geometry validation. It does not prove rendered appearance,
  aesthetic quality, physics, collision, animation or target-engine import.

The recipe, its canonical SHA-256, effective budgets, generated part count and
pinned donor provenance remain visible in the creation receipt. Named numbers
therefore create a family of shapes without becoming hidden runtime state.
