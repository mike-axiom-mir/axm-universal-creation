# Standalone donor absorption — 2026-09-12

This pass inspected four current default-branch snapshots. It is a focused donor
survey, not a complete audit of all AXM repos or their open branches.

| Source | Snapshot | Candidate / decision |
|---|---|---|
| Axm-game-assets | d6a930251e4a99f1f98365b8d01fc968025b1fd9 | Absorbed woven fabric fields and the exact noise/PNG helpers they use. |
| axm-material-surface-fabric | c5ed5b09be88e13031b89977d392b3088d659e4a | Premade layer composer and portable material conformance are promising next donors. Composer needs its asset pack/render path assessed; do not call it installed here. |
| axm-framestate | 60ea68ba72e4ad4df8dc5746c6bb18fcd6569a34 | Integer timeline sampling is small and reusable; renderer/resume work carries broader project/media dependencies. Inspected, not absorbed. |
| axm-machine-voice | b77f6d083db2951d19e082e712fdaa3061ced956 | Grounded outcome/conflict/need reporting may improve creation diagnostics. README-level review only; no voice code imported. |

## Runnable addition

```
PYTHONPATH=src python -m axm_uc fabric creations/woven-fabric --size 256 --seed 7
```

Produces seven local PNG maps, a map gallery, and a material manifest through the
existing `mixed-media-project` machine capability. No Game Assets checkout,
network, Pillow, Node, external engine or package dependency is needed. Python's
standard library is sufficient. Existing target directories are not overwritten.

The Python `fabric_request` API also accepts `FabricSpec` with RGB color, warp and
weft thread counts, weave depth, roughness, fiber noise and thickness hint. Size
is bounded to 16..1024; seed to 0..2147483647. These are current implementation
bounds, not architectural limits. The CLI exposes size/seed; advanced material
parameters are currently Python API only.

ORM stores ambient occlusion, roughness and metallic in RGB respectively. The
fabric is nonmetallic. Thickness is a normalized authored proxy, not a measured
thickness. No seamless tile, physical cloth fidelity, rendered shading or
production material quality is asserted by these maps.

## Source integrity

Donor: https://github.com/mike-axiom-mir/Axm-game-assets/tree/d6a930251e4a99f1f98365b8d01fc968025b1fd9

`native_fabric_material.py` supplies the weave fields. `native_pbr.py` supplies only
`_hash2`, `_smoothstep`, `value_noise`, `fbm`, `_png_chunk`, and `png_bytes`.
Adapted local files are `fabric_material.py` and `fabric_noise.py`. The donor's
direct filesystem writer was replaced by UC's existing validated transactional
project request. Strict numeric/size checks were added. Original field math was
preserved. Apache-2.0 license and source SHA-256 values are retained under
`third_party/game-assets/`. No donor governance or runtime architecture is copied.

## Evidence and boundaries

At size 32, seed 7, every raw map exactly matched the pinned donor executed in
this environment. Recorded donor vectors make this regression reproducible
without a donor checkout. Tests additionally cover repeatability, seed variation,
channel dimensions, nonmetallic ORM, invalid parameters, machine-generated map
hashes, and refusal to overwrite an existing project. A 64px color map was viewed;
that is not a shaded material or a visual-quality certification. Cross-platform
floating-point byte identity is not established by this single-environment test.

Truth: exact source and output claims are bounded. Agency: explicit invocation,
parameters and no automatic overwrite. Continuity: source license/digests,
compatible machine writer and donor vectors retained. Wisdom before speed:
absorb one usable operation with its small dependency closure; keep the remaining
candidates visible rather than copying whole machines without integration.
