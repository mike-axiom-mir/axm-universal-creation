# Source-backed known measures

Pure mathematics and sourced real-world reference values are different evidence classes. Universal Creation keeps them separate.

`axm.known-measure/v1` records a quantity together with its truth state, basis, scope, source authority/title/URL/locator, retrieval date, and caveats. The first seed is intentionally small:

- `si.speed_of_light_vacuum` — 299792458 m/s, an SI defining value from BIPM;
- `convention.standard_gravity` — 9.80665 m/s2, the conventional standard gravity from CGPM/BIPM;
- `convention.standard_atmosphere` — 101325 Pa, an exact defined reference conversion documented by NIST;
- `convention.astronomical_unit` — 149597870700 m, the IAU-defined astronomical unit.

The records are local snapshots. Creation does not fetch the network, so the machine stays deterministic/offline and source updates remain explicit repository changes.

## Using a known measure

`axm.math-create/v1` accepts `measure_overrides` in addition to numeric `overrides`:

```json
{
  "schema": "axm.math-create/v1",
  "family_id": "motion.constant_acceleration",
  "measure_overrides": {"acceleration": "convention.standard_gravity"},
  "overrides": {"initial_velocity": 0, "duration": 1},
  "template": {
    "kind": "json-file",
    "direction": "create sourced motion state",
    "inputs": {"path": "creations/gravity.json", "value": {"final_velocity": 0}}
  },
  "bindings": {"final_velocity": ["inputs", "value", "final_velocity"]}
}
```

A known measure may only target an already-declared math parameter and must have compatible dimensions. A numeric override and a known-measure override cannot target the same parameter.

The resulting parameter is marked `selected_by: known_measure` and retains its full known-measure record. Derived values inherit the parameter truth through the existing math engine.

Catalog installed records with:

```sh
axm-math-create --measure-catalog
```

## Truth boundary

An exact definition or convention is exact about that definition or convention. It is not automatically a measurement of a particular object or location. For example, standard gravity is not a claim about local gravity, standard atmosphere is not current local air pressure, and the astronomical unit is not an instantaneous Sun-Earth distance.
