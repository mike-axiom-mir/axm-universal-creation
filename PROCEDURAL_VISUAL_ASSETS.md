# Procedural Visual Asset Forge

This layer turns visual vocabulary into **real generated assets**. It is deterministic, local, offline and dependency-free.

It does not claim that a material name is physically simulated. It generates inspectable raster/vector/mesh assets and PBR-style channel maps from explicit parameters and seeds.

## What it actually generates

| Family | Executable generators | Output |
|---|---|---|
| Textures | noise, smooth-noise, grain, checker, stripes, diagonal-stripes, dots, grid, brick, tile, wood, marble, stone, concrete, brushed-metal, hammered-metal, fabric, carbon-fiber, leather, paper, terrain, camouflage, circuit, sci-fi-panel, hex, terrazzo, scales | PNG |
| Gradients | linear, radial, conic, diamond, reflected, stepped, sunset, aurora, neon, metallic, heatmap, holographic | PNG |
| Materials | wood, stone, concrete, iron, steel, copper, gold, plastic, rubber, glass, fabric, leather, ceramic, emissive, sci-fi | directory with albedo, roughness, metallic, height, normal, AO, emissive, opacity PNGs + material.json |
| Fixtures / parts | button, knob, slider, toggle, panel, vent, grille, handle, hinge, bracket, bolt, rivet, screw, washer, gear, pipe, elbow, window, light, gauge, badge, screen, port | SVG; many also OBJ |
| Decals | arrow, chevron, warning, hazard-stripes, target, crosshair, panel-lines, serial-label, circuit-trace, scratch, crack, drip | SVG |
| Palettes | analogous, complementary, split-complementary, triadic, tetradic, monochrome, warm, cool, earth, neon | palette.json + swatches.svg |
| Kits | starter, full | generated directory + SHA-256 manifest |

Every item in this table is exercised by the test suite. The catalog is not aspirational inventory.

## Installed command

```bash
axm-assets catalog
axm-assets generate texture wood creations/wood.png --seed 42 --size 512
axm-assets generate gradient holographic creations/holo.png --size 512
axm-assets generate material steel creations/material-steel --seed 7 --size 512
axm-assets generate fixture gear creations/gear.svg
axm-assets generate fixture gear creations/gear.obj --format obj
axm-assets generate decal hazard-stripes creations/hazard.svg
axm-assets generate palette triadic creations/palette --seed 12 --count 8
axm-assets kit creations/visual-kit --profile starter --seed 100
```

From a source checkout without installing the package, the same CLI is available with:

```bash
PYTHONPATH=src python -m axm_uc.visual_assets_cli catalog
```

## Python use

```python
from axm_uc.visual_assets import generate_asset, generate_kit

generate_asset(
    category="texture",
    kind="concrete",
    path="creations/concrete.png",
    seed=123,
    size=512,
)

generate_kit("creations/full-visual-kit", profile="full", seed=123, size=128)
```

The machine-friendly `operate_visual_assets(root, inputs)` adapter is also exposed in the module, so capability or organ wiring can call the same generator rather than reimplementing it.

## Composition model

The useful unit is not just an image. A generated asset can be assembled as:

`shape + part + texture + material channels + gradient/palette + decal + lighting/shading metadata + behavior elsewhere in the creation system`

That lets Universal Creation reuse deterministic pieces instead of regenerating every visible object from scratch.

## Truth boundary

- Same kind + parameters + seed produces deterministic bytes under the same Python semantics.
- PNG writing uses Python standard library only.
- OBJ fixtures are lightweight procedural geometry, not production-sculpted meshes.
- PBR-style maps are useful renderer inputs, not measurements of real-world material physics.
- No internet, AI model, stock asset, external texture pack or hidden service is used.
- This PR exposes a callable adapter and CLI; automatic routing through `UniversalCreationMachine.create()` is not claimed until a capability manifest/builtin binding is explicitly installed.
