# Game materials in Blender and glTF

This is an **opt-in surface realization adapter**, not a replacement for the
hero, globe or trike generators, and not a complete art-direction system.
The realistic finish and original donor fields remain selectable and unchanged.

## Use

Generate a bundle using the existing portable CLI, then assign it in Blender:

```sh
axm-assets game-material painted-metal out/comic-paint --finish comic-salvage --seed 471
```

```python
from axm_uc.game_material_bridge import blender_game_material

material = blender_game_material("out/comic-paint", name="SalvageArmor")
mesh_object.data.materials.append(material)  # caller supplies its own UV-mapped mesh
```

UC's `src` must be on Blender's Python path (or the package installed there).
Validation uses only the standard library; importing this module does not import
Blender. Calling `blender_game_material` requires `bpy`. The adapter does not
install a runtime, unwrap geometry or replace existing object materials.

## Export contract

- Base color: sRGB image connected to Principled Base Color.
- Packed ORM: Non-Color image; red to the recognized glTF Occlusion socket,
  green to roughness, blue to metallic. AO is not baked into albedo. Blender's
  ordinary preview does not evaluate that export-only AO socket.
- Normal: Non-Color image, tangent-space Normal Map, strength 1. The finish's
  authored normal strength is already in the pixels; no second attenuation.
- Metal/fabric donor normals encode downward image Y. The adapter flips only
  the green channel in a new packed image for glTF/Blender tangent +Y. Other
  families keep their original normals. Source PNGs are never rewritten.
- All three runtime images are packed into the editable material. Height,
  separate scalar maps and fabric thickness remain in the source bundle;
  height is not displacement and must not silently regenerate styled normals.
- Material extras retain family, finish, original convention and manifest hash.
  Keep the original bundle alongside the `.blend` when archiving a creation.

New manifests explicitly identify normal direction. Existing v0.1 manifests
with the original inherited-donor wording remain accepted for the six known
families. Unknown schemas, conventions, maps, channel/color-space mismatches,
path traversal, linked files, changed digests, PNG CRC/chunk errors and excessive
dimensions/scanline data are rejected before creating Blender resources. This
is a bounded UC-generated PNG reader, **not an arbitrary image importer** or a
substitute for a sandbox around hostile third-party media.

## Reproducible proof

```sh
python -m unittest discover -s tests -p 'test_game_material*.py' -v
# In an isolated Python 3.11 environment with bpy 4.3.0, numpy 1.26.4, Pillow:
python tools/blender/game_material_roundtrip.py build /new/output
python tools/blender/game_material_roundtrip.py verify /new/output
```

The two invocations are separate processes. Build refuses an existing output
directory. Verify deliberately overwrites that proof's re-import render/report.
The tested runtime was Blender 4.3.0 on Linux, with Pillow 12.3.0. Blender's Python
wheel required NumPy <2 here; no cross-version compatibility is claimed.

The proof generates 24 small, front-planar-UV material samples (six families ×
four finishes), original PNG bundles, packed editable `.blend`, actual GLB,
source and re-imported Cycles stills, source digests and a verification receipt.
Its independent GLB decoder checks every embedded base/ORM/normal PNG pixel,
normal conversion, texture factors, explicit AO and repeat sampler state. It
reopens the `.blend` and checks 72 packed images/color spaces, then starts with
an empty Blender scene, re-imports the GLB, checks materials and renders again.

The initial spherical UVs distorted woven cloth and wood into radial rings.
Visual inspection caused a switch to front-planar UVs and clearer label spacing.
That is a proof-scene repair, not an automatic UV-unwrapping capability.

The exporter reports an unavailable optional Draco library; compression is not
requested. It also reports shared sampler selection for ORM/AO; this adapter
uses matching sampler settings and the GLB inspection verifies repeat wrapping.
Neither warning is hidden or converted into a claim of compressed delivery.

## Limits and next work

The graphic-toon option is flatter **PBR surface data**, not exported cel lighting.
The rendered samples show reduced highlight/detail response and directional
paint marks; several finish differences remain subtle under this lighting.
There are no rigs, animation clips or LODs in this material proof, deliberately.
No performance benchmark, target-engine gameplay test, hero UV/deformation test,
seamless tiling or mesh-aware edge wear is claimed.

Next: layered paint and exposed substrate with protected readable areas, followed
by expressive form controls. Retain this export test as a regression gate when
those material mechanisms change.
