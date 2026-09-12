# RTS plate-directed geometry reconstruction

The previous catalog finishing pass changed surfaces while retaining the old
simple geometry. The user rejected the resulting style drift. This route adds
new authored geometry for 82 catalog designs and retains the separate detailed
workshop recipe as the 83rd design.

These are **static authored approximations**, not an exact image-to-mesh system.
The reference plates constrain visible construction and survivor/comedy motifs;
the code still simplifies shapes, clothing, clutter, proportions and materials.
Hidden surfaces are inferred. A green structural test does not establish visual
fidelity. No new descriptive organs are counted as executable by this change.

## Executable hands

Use the pinned Blender Python environment described in the workshop documentation.
The scripts import `bpy`; they do not require an AI service or network access.
Outputs must be new directories. The font currently used by the family runner is
`/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf`.

```sh
python tools/blender/axm_rts_vehicle_forge.py --output VEHICLES --resolution 1000
python tools/blender/axm_rts_plate_forge.py --output OTHER --families buildings industry defenses equipment crew world utilities --resolution 1000
```

The vehicle runner supports `--only ASSET_ID ...`; the family runner supports
both `--families` and `--only`. The family runner intentionally excludes the
workshop: preserve the accepted workshop source/export or invoke its existing
`axm_rts_workshop.py` recipe separately.

- Vehicles: two-wheel hand cart, motorcycle trike, open buggy, passenger/cargo
  bodies, crawler tracks, articulated crane shapes, drill, ambulance equipment.
  The cab construction includes framed glass, cowl, recovery winch, guards,
  suspension, tanks, hinges, tied cargo and roof racks.
- Buildings/industry: corrugated shells, bowed roofs, layered rooms, windows,
  equipment, planted beds, livestock, tanks, mine head and collection systems.
- Defenses: hollow bathtub turret and duck, separate car doors, refrigerators,
  traffic signs, sandbags, tower, spotlights and barriers.
- Equipment: receiver/stock/barrel assemblies, rotary barrel cluster, engine,
  auger, trusses, detector, containment cell and running gear.
- Crew: large heads, faces, clothing, gloves, boots, backpacks and role gear.
- World: broken masonry, bridge gap, settlement rooms/balconies, gate, railway,
  crater, reactor, dish and standing anomaly rings.

Each asset retains editable individual objects in a `.blend`, exports a
material-batched GLB and decimated lower-detail GLB, then imports the GLB into a
fresh scene before rendering. `verify_rts_batch.verify` independently decodes
positions, indices, normals, UVs and embedded images. The per-asset report records
that structural evidence. It does not certify visual equivalence.

## Lossless compact distribution

```sh
python tools/blender/pack_rts_shared.py --sources VEHICLES OTHER --output COMPACT
```

This optional packer relocates geometry buffers byte-for-byte into `.bin` files
and identical embedded images into a shared content-addressed `textures` folder.
Every relocated buffer and image is checked from the written files. Node,
material, mesh, skin and animation metadata remain unchanged by the packer.
Keep each `.gltf`, its `.bin`, and the relative `../../textures` directory together.
The packer accepts the nested per-asset output layout; a separately retained
workshop can be staged under its own asset directory before packing.

Regression tests cover relocation offsets, reuse of an identical image across
assets, rejection of truncated GLBs, and refusal to overwrite corrupt shared
image content. This is file-size reduction by deduplication, not remeshing or
lossy texture compression.

## Runtime and continuity boundaries

The **new authored models are static**. They do not inherit the previous pack's
rigid animation channels, sockets or coarse colliders. Preserve that earlier
pack; do not silently replace a working gameplay assembly with a static model.
Use the new geometry as a visual child and fit the game's existing movement,
collision and navigation components. The Blender files retain editable parts.
Neither browser execution, target-RTS integration nor measured frame rate is
claimed. Studio lights/cameras are preview context, not an engine lighting setup.

The four-root fit is concrete: Truth keeps static/approximate status explicit;
Agency follows the supplied plates instead of substituting a realism goal;
Continuity retains earlier deliveries and the accepted workshop; Wisdom Before
Speed checks actual exports and corrects visible construction faults rather than
using test counts or texture detail as a claim of exact likeness.
