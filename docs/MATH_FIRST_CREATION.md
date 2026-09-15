# Math-first creation

Universal Creation can now resolve declarative mathematical families before a
creation request reaches an adapter or renderer.

The live path is:

`math family -> variant/overrides -> derived quantities -> constraints -> numeric bindings -> UniversalCreationMachine.create`

Use the installed command:

```sh
axm-math-create request.json
```

The request schema is `axm.math-create/v1`:

```json
{
  "schema": "axm.math-create/v1",
  "family": {
    "schema": "axm.math-family/v1",
    "id": "wheel",
    "parameters": {
      "radius": {
        "unit": "m",
        "min": 0.2,
        "max": 1.0,
        "default": 0.5,
        "truth": "measured",
        "uncertainty": 0.002,
        "source": "measured family"
      }
    },
    "variants": {"compact": {"radius": 0.35}},
    "derived": {
      "circumference": {
        "unit": "m",
        "truth": "exact",
        "expr": {"op": {"name": "mul", "args": [{"const": "tau"}, {"param": "radius"}]}}
      }
    },
    "constraints": []
  },
  "variant": "compact",
  "template": {
    "kind": "json-file",
    "direction": "create inspectable math-resolved design state",
    "inputs": {
      "path": "creations/wheel.json",
      "value": {"radius": 0.0, "circumference": 0.0}
    }
  },
  "bindings": {
    "radius": ["inputs", "value", "radius"],
    "circumference": ["inputs", "value", "circumference"]
  }
}
```

Bindings may only replace numeric locations that already exist in the creation
template. They cannot silently create new fields or replace text/objects. The
ordinary machine still performs its own capability routing and output evidence.

## Why this layer exists

When a relationship is known, UC should derive it instead of asking a renderer or
model to make a visually plausible guess. Named families can encode known size
ranges and variants; constraints can reject incompatible combinations; exact or
measured provenance stays separate from estimated and creative values.

This is a substrate for later geometry, animation, materials, structures,
mechanisms, acoustics, lighting and other mathematical creation domains. It is
not a claim that all of those domains are implemented in this first slice.

## Truth boundary

`axm.math-family/v1` intentionally does not yet perform dimensional algebra or
unit conversion. A result proves only that declared numeric expressions and
constraints were evaluated. It does not prove physical realism,
manufacturability, collision correctness, rendered quality, ergonomics, or
real-world safety.

UC carries its own local compatible implementation. The external
`axm-sticker-fabric` repository may share and grow the same contract, but UC does
not contact or depend on it at runtime.
