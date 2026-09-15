# Math-first creation

Universal Creation can now resolve declarative mathematical families before a creation request reaches an adapter or renderer.

`math family -> variant/overrides -> derived quantities -> constraints -> numeric bindings -> UniversalCreationMachine.create`

Use `axm-math-create request.json`.

A family declares bounded parameters, named variants, derived quantities and explicit constraints. Bindings may only replace numeric locations that already exist in the creation template; they cannot silently create new fields or replace text/objects. The ordinary machine still performs its own capability routing and output evidence.

When a relationship is known, UC should derive it instead of asking a renderer or model to make a visually plausible guess. Named families can encode known size ranges and variants; constraints can reject incompatible combinations; exact or measured provenance stays separate from estimated and creative values.

This is a substrate for later geometry, animation, materials, structures, mechanisms, acoustics, lighting and other mathematical creation domains. It is not a claim that all of those domains are implemented in this first slice.

## Truth boundary

`axm.math-family/v1` intentionally does not yet perform dimensional algebra or unit conversion. A result proves only that declared numeric expressions and constraints were evaluated. It does not prove physical realism, manufacturability, collision correctness, rendered quality, ergonomics, or real-world safety.

UC carries its own local compatible implementation. The external `axm-sticker-fabric` repository may share and grow the same contract, but UC does not contact or depend on it at runtime.
