# Procedural Visual Asset Forge — Expansion v0.2

This expansion stays in the same visual-asset PR/lane and adds executable generation families beside the original forge. It is additive: the proven v0.1 texture/material/fixture generators remain intact.

The local installation does not yet have a final authoritative filemap, so this layer is deliberately **path-explicit**. Callers choose where generated output goes. `operate_visual_expansion(root, inputs)` resolves relative paths without inventing a permanent local directory contract.

## Added executable families

| Family | Count | Output |
|---|---:|---|
| Procedural surfaces | 51 | PNG |
| Smart pigments | 18 | PBR-style PNG maps + 12 smart-mask PNGs + pigment.json |
| Sprite families | 24 | transparent PNG sprite sheet + JSON metadata |
| Modular 3D mesh parts | 32 | OBJ |
| Vector parts / trims / emblems | 30 | SVG |
| Expansion kits | starter/full | directory + SHA-256 manifest |

Every advertised family is exercised by `tests/test_visual_expanded.py`.

## Smart pigment engine

A pigment is not a flat fill. Each pigment preset combines a procedural surface grammar with material parameters and deterministic condition masks.

Current pigment families:

- painted-metal
- bare-metal
- oxidized-copper
- worn-plastic
- polished-plastic
- cloth-dye
- leather-stain
- ceramic-glaze
- stone-mineral
- neon-coat
- rubberized-coat
- military-paint
- weathered-wall-paint
- enchanted-pigment
- reactor-coat
- biotech-pigment
- vehicle-enamel
- industrial-powdercoat

Each pigment pack emits the PBR-style channels:

- albedo
- roughness
- metallic
- height
- normal
- ambient occlusion
- emissive
- opacity

It also emits separate deterministic smart masks:

- edge-wear
- cavity-dirt
- rust
- dust
- moisture
- crack
- peel
- scorch
- moss
- snow
- streak
- sun-fade

The caller can vary `age`, `damage`, `moisture`, `seed`, `scale`, and `size`. The masks remain separate files so a future renderer, game engine, shader graph, or material compositor can decide how strongly to use them rather than receiving one permanently baked texture.

This is the deterministic counterpart of modern smart-material / smart-mask workflows. It does not claim physically measured pigment chemistry or geometry-aware curvature from an external 3D renderer. The current masks are generated from the declared procedural surface field and explicit parameters.

## New surface families

Natural and geological surfaces include bark, moss, lichen, mud, sand, snow, ice, lava crust, obsidian, granite, slate, limestone, clay, cracked earth, wet soil, grass patch, and leaf litter.

Built-world surfaces include roof tile, plaster, stucco, asphalt, painted wall, wallpaper, porcelain, frosted glass, dirty glass, rusted steel, oxidized copper, galvanized steel, rubber tread, foam, and insulation.

Machine and speculative surfaces include spaceship hull, mech armor, energy panel, hologram grid, reactor skin, shield field, cyber grid, nanofiber weave, warning panel, data lattice, alien alloy, and biotech membrane.

Pattern surfaces include chain link, quilt, zigzag, labyrinth, ornamental, wave, and spiral grammars.

## Sprites

The forge can now create transparent deterministic sprite sheets for:

bot, worker, soldier, vehicle, tank, drone, turret, tree, rock, crystal, crate, barrel, pickup, building, spaceship, creature, orb, effect-burst, projectile, shield, coin, heart, star, and portal.

Sprite generation accepts `frame_size`, `frames`, `columns`, and `seed`. A neighboring JSON file records the frame layout.

These are procedural reusable sprite primitives, not claims of hand-authored production animation.

## 3D modular parts

OBJ generation now includes:

wall, floor, roof, stair, column, arch, door, window-frame, pipe, vent, crate, barrel, rock, crystal, tree-trunk, branch, bolt, plate, armor-panel, wheel, gear, turret-base, antenna, rail, fence, road-block, greeble, console, beam, bracket, socket, and thruster.

The generated meshes are lightweight deterministic geometry intended as building blocks, blockout/game pieces, procedural composition inputs, or seeds for later refinement. They are not presented as production-sculpted or physically engineered models.

## Vector parts

SVG generation now includes borders, trims, ornaments, runes, panel/cable/pipe strips, hazard and road markings, fantasy carvings, Celtic/geometric motifs, circuit/greeble/riveted strips, frames, emblems, vines, crystals, icons, glyphs, arrow sets, target rings, and grid overlays.

## CLI examples

```bash
axm-assets catalog
axm-assets generate surface bark creations/bark.png --seed 42 --size 512
axm-assets generate pigment military-paint creations/military --seed 9 --size 512 --age .8 --damage .6 --moisture .3
axm-assets generate sprite bot creations/bot.png --seed 7 --frame-size 32 --frames 8 --columns 4
axm-assets generate mesh armor-panel creations/armor.obj --seed 4
axm-assets generate vector-part circuit-strip creations/circuit-strip.svg --seed 4
axm-assets expansion-kit creations/visual-expansion --profile starter --seed 100
```

## Composition direction

The forge can now hand later creation systems a much richer deterministic stack:

`shape / mesh + vector part + surface + pigment + smart masks + material channels + palette / gradient + decal + sprite / animation metadata`

That means a later object builder does not need to regenerate every visible atom from zero. It can assemble, parameterize, age, recolor, damage, or reuse inspectable pieces.

## Truth boundary

- No internet, model call, stock texture service, Pillow, NumPy, or hidden asset service is required.
- Same generator, parameters, seed, and Python semantics are deterministic.
- Smart masks are procedural condition maps, not measured real-world material chemistry or renderer-derived curvature maps.
- OBJ parts are lightweight procedural geometry.
- Sprite sheets are procedural primitives rather than production animation claims.
- No final local filemap is asserted yet. Output paths remain caller-selected until the local system layout is actually known.
