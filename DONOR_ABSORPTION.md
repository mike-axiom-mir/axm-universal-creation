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

## Second absorption pass

The remaining focused candidates now have local callable implementations:

- FrameState's original integer timeline sampler is retained byte-for-byte in
  `donor_timeline.py`. `timeline_tracks.sample_track` adds strict validation for
  ordered keyframes, scalar bounds and known easing names. CLI:
  `PYTHONPATH=src python -m axm_uc sample-track TRACK.json --frame 15`.
  Linear, smoothstep and hold sampling are executable; no new animation renderer
  is implied. Existing Asset Atom time-based animation schemas are unchanged.
- Machine Voice's core and criterion-outcome producer are retained byte-for-byte
  in `axm_uc.donor_voice`. Call `produce_criterion_outcome` with explicit criterion
  references and observations. Complete positive evidence yields a success
  candidate; one evidenced failed required criterion yields failure; partial
  positive evidence yields no candidate. It does not run tests or authenticate
  supplied evidence. The general UC result format is not silently replaced.
- Material Surface Fabric's pinned composer, metadata pack and conformance
  dependency closure are local under `third_party/material-surface`. Run:
  `node third_party/material-surface/tools/premade-compose.js seed demo`
  to produce a deterministic layer recipe and plan. Run:
  `node third_party/material-surface/tools/material-conformance.js check-material-offer OFFER.json`
  to verify portable offers. These tools need Node but no npm dependencies,
  network or donor checkout. Conformance validates portable bytes and declarations,
  not image quality. The premade binary image pack is NOT included; planning is
  executable but rendering those premades remains unavailable without those bytes.

`third_party/absorption-v2.json` records exact donor commits, source paths,
local destinations and original SHA-256 values. Copied source is unchanged;
validation/CLI adapters and test integration are separate UC code. FrameState's
Apache-2.0 license is included. No LICENSE file was present in the inspected
Material Surface or Machine Voice snapshots; these owned-repo subsets were
brought across under Mike's explicit reuse instruction, with attribution retained
and no invented open-source license grant.

The donor composer and conformance suites pass locally, including their actual
Node CLI checks. UC tests exercise timeline boundaries/invalid inputs and
success/failure/incomplete criterion behavior. These are callable local tools,
not automatically invoked by every creation and not automatic adoption authority.
The survey remains four pinned repositories, not every potentially useful AXM
operation. Larger rendering, full communication routing and character-generation
systems still need their own dependency and integration assessment.
