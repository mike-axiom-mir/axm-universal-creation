# Source-Bound Environment / Level Reference Template Pack

`visual.environment.core` is the reusable environment/reference foundation for game levels, locations, biomes and production boards.

A reference board helps humans and machines reason about a world; it does not become authoritative level geometry merely because it looks convincing.

## Surfaces

- project / location hub
- environment identity board
- zone / layout editor
- scale / measurement editor
- modular kit / prop editor
- material / surface editor
- lighting / weather / time reference editor
- traversal / gameplay annotation editor
- environment / biome variant editor
- review / export

## Source-truth contract

- `environment-source` — exact environment/location identity, source, version, digest and scope;
- `environment-zone` — exact zone geometry/source/status;
- `environment-measurement` — value, unit, source and precision/assumption state;
- `modular-environment-piece` — exact kit identity, source, connection semantics and transform;
- `environment-prop` — exact prop identity, source, placement context and gameplay/visual status;
- `environment-material` — exact target/material/source/context;
- `environment-lighting-state` — source, time, weather and exposure/state;
- `traversal-reference` — exact target/type/source/status;
- `environment-variant` — exact base, deltas, context and source;
- `environment-export-target` — exact source-coverage, measurement, material, prop, lighting and annotation requirements.

## Truth boundary

Perspective imagery alone does not establish physical scale. Visual proximity does not establish gameplay linkage. A traversal arrow, hazard region or spawn-like mark is only authoritative when bound to real project state. Lighting/weather references are state references, not hidden changes to the base environment. Derived boards and exports never replace richer world/project state.

This pack proves deterministic structural/editability contracts only. It does not prove final level geometry, collision, navigation, gameplay quality, physical scale, lighting correctness, performance or aesthetic acceptance.