# Complete RTS catalog finishing

The user accepted the workshop and requested the remaining assets while reducing
iteration cost. This offline batch hand applies the same procedural surface
vocabulary to the existing 82 other authored recipes. It preserves the accepted
workshop as a separately authored asset.

This is a shared finishing pass, **not 82 bespoke workshop-quality rebuilds**.
The recipes remain simpler in geometry and composition than the workshop. The
route adds embedded PBR imagery, planar UV coordinates and bounded two-segment
bevels on hard material edges. It does not claim exact plate reconstruction.

Run with the pinned Python/Blender environment from the workshop instructions:

```sh
python tools/blender/axm_rts_batch.py --source ORIGINAL_PACK --output NEW_PACK --workshop ACCEPTED_WORKSHOP
python tools/blender/verify_rts_batch.py NEW_PACK ORIGINAL_PACK
python tools/blender/render_rts_batch.py NEW_PACK
```

The first command refuses an existing destination and validates requested source
assets before generating. `--only` supports a bounded sample; a partial run has
`complete: false`. A completed manifest is written only at the end. Progress
records preserve partial work without calling it a complete delivery.

Original node transforms, rigid animation structures, sample bytes and assembly
metadata remain intact. Independent verification compares decoded animation
samples and pivots/sockets, validates geometry/UVs/normals/embedded images, and
requires fewer triangles in each lower-detail model. Original coarse colliders
are retained except for the separately rebuilt workshop, which has no collider.

Family contact sheets are rendered from fresh GLB imports. They are static
evidence, not animation playback, target-game testing, performance measurement or
equal quality certification. No neural generation service or network is used.

Root review: Truth requires distinct quality-route labels; Agency retains the
user's accepted workshop and leaves game adoption explicit; Continuity retains
the original pack, animation and assembly data; Wisdom before speed requires
decoded output checks before distribution despite the lower-cost batch route.
