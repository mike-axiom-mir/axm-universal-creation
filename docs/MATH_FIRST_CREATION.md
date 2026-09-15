# Math-first creation

Universal Creation resolves declarative mathematical families before a creation
request reaches an adapter or renderer.

`math family -> variant/overrides -> dimensional derivation -> constraints -> numeric bindings -> UniversalCreationMachine.create`

Use:

```sh
axm-math-create --catalog
axm-math-create request.json
```

A request may provide an inline `family` or one local `family_id`. Exactly one is
required. Built-in family IDs are resolved from UC's own installation; they do
not fetch Sticker Fabric, a network service, or external data.

Example:

```json
{
  "schema": "axm.math-create/v1",
  "family_id": "motion.linear",
  "overrides": {"distance": 100, "duration": 10},
  "template": {
    "kind": "json-file",
    "direction": "create unit-aware motion state",
    "inputs": {
      "path": "creations/motion.json",
      "value": {"speed_mps": 0, "speed_kmh": 0}
    }
  },
  "bindings": {
    "speed_mps": ["inputs", "value", "speed_mps"],
    "speed_kmh": ["inputs", "value", "speed_kmh"]
  }
}
```

The result is derived through the unit system, so the two outputs are `10 m/s`
and `36 km/h`; this is not a duplicated hand-authored conversion table inside
the creation request.

## Dimension-aware math

Units are operational, not labels. The local registry currently supports common
metric length/area/volume, mass, time, angles/rotations, frequency, linear and
angular speed, acceleration, force, pressure, energy, power, dimensionless
values/counts/percentages, and screen pixels.

Compatible values convert through a shared base representation. Expressions
carry dimension exponents, so invalid operations such as adding metres to
seconds fail closed. Trigonometric functions require an angle. A unit-bearing
`quantity` expression makes dimensional cancellation explicit where needed.

## Truth propagation

An exact equation does not upgrade its evidence. If a radius is measured, an
exact circumference relation remains an exact **relation**, while the resulting
circumference is still classified as measured. Derived records include their
input dependencies and the weakest applicable truth state.

Input uncertainty is preserved and converted to base units. General uncertainty
propagation is not implemented yet, and that limit is stated in every result.

## Local relation families

The first built-in library contains:

- `geometry.circle`
- `geometry.box`
- `motion.linear`
- `motion.constant_acceleration`
- `waves.periodic`
- `rotation.wheel`
- `mechanism.gear_pair`
- `layout.aspect`

These are relation-first families. Their reference inputs are deliberately not
presented as population averages, legal standards, vehicle norms, road norms,
human norms, or industrial dimensions. Empirical and standardized real-world
families should be added separately with explicit provenance.

## Binding boundary

Math bindings may only replace numeric locations already present in the normal
UC request template. They cannot silently create a new structure or replace a
text/object target. After binding, the ordinary machine performs its existing
capability routing and output evidence checks.

## Truth boundary

Dimension compatibility and declared equations are now checked. That does **not**
establish material mechanics, actual collision/physics behavior, environmental
conditions, manufacturability, rendered quality, ergonomics, or real-world
safety. Idealized relationships state the assumption in their source metadata.

UC carries its own local compatible implementation. The external
`axm-sticker-fabric` repository may share and grow the contract, but UC does not
contact or depend on it at runtime.
