# Reference-led workshop polish

The first 83-design collection exported valid meshes but missed the supplied
illustrations' visual standard. This is a focused correction for the improvised
workshop, not a declaration that all 83 designs are now polished.

The execution hand reuses `tools/blender/axm_blender_forge.py` and adds reusable
construction and surface operations: bent corrugated sheet, tensioned and folded
cloth, fitted repairs, flanged pipework, lantern assemblies, plank crates,
material texture compilation and material-based export batching. These operations
are called by an explicit authored workshop recipe. They do not infer unseen
geometry automatically.

## Run from a complete checkout

Supply a Python 3.11 environment with `bpy==4.3.0`, `numpy==1.26.4` and Pillow
installed. This was the runtime exercised here. The core UC installation remains
standard-library only; the command does not install anything or contact a service.
The font is an explicit local input. On the tested Linux host:

```bash
PYTHONPATH=src python -m axm_uc rts-workshop-polish OUTPUT \
  --python /path/to/blender-python/bin/python \
  --font /usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf \
  --resolution 1100 --samples 48
```

The command builds in temporary staging and publishes only after Blender exits
successfully and the expected asset/render files match their recorded hashes.
An existing destination is refused. Output includes editable packed Blender
source, embedded-texture near/far GLBs, actual fresh-import renders and receipts.
A rendering failure is not a successful publication. A source checkout is required;
this optional tool-backed hand is not included in the small Python wheel.

## What changed perceptually

The reference has a closed service bay on the left, a deep open workshop on the
right, an asymmetric canopy, raised chimney and dish, dense working furniture,
layered salvage and warm practical lights. Those relationships guide the new
geometry. Materials use generated original base-color, normal, roughness and
metallic images. Typography is authored onto its own UV-mapped banner. Reference
image pixels are never used to fake building geometry.

The first review exposed a cloth/roof intersection and overlarge uniform wear.
The next pass removed the conflicting hard roof, reduced the material relief,
softened wood grain, raised and sagged the canopy correctly, and increased the
interior practical lights. The final pass adds corner folds and a conforming cloth
repair patch. Actual GLB re-import is reviewed, not only the native source scene.

## Evidence and boundaries

`verify_rts_workshop.py` independently reads GLB accessors, indices, UVs, normals,
embedded image bytes, material batches, bounds and the lower-detail triangle
reduction. It rejects missing textures, invalid geometry and leaked review-floor
geometry. It does not turn mesh counts into aesthetic quality claims.

The preview is a Cycles CPU render. The GLB retains actual textures and geometry;
the game must provide suitable lighting, shadows, practical lights and tone mapping.
Studio staging is deliberately excluded. This is a static building, not an
animated construction sequence. There is no measured target-game FPS, in-game
import observation, automatic perceptual acceptance, or exact concept-match claim.
Finer wear and authored cloth shaping remain opportunities for later iterations.

## Root review

Truth: technical export checks and visual comparisons are separate; the earlier
visual failure is preserved rather than renamed a success. Agency: the user gets
a separate asset and editable source, without silent edits to their RTS project.
Continuity: previous recipes and the 83-design pack remain available, while this
path reuses the existing Blender forge. Wisdom before speed: one reference-led
asset is examined before multiplying the new treatment across the collection.

Integration is supported when the source regression suite and fresh-export
checks pass. Root fit does not certify the entire collection's visual quality or
replace the user's acceptance of their game assets.
