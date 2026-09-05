# Static asset spatial contracts

Reactor Fortress work exposed a gap between an export existing and its actual geometry fitting the game. The old `inspect-glb` surface decodes metadata: mesh counts, accessor counts and material names. The new `3d-contract-review` operation reads binary positions and triangle indices, composes the selected scene's node transforms, and checks an explicit spatial contract. It can identify an oversize part, missing attachment point or unproven collision triangle before integration.

This is a reusable machine tool, available through the visual CLI, the existing visual expansion bridge, and an optional check in `3d-forge`. It is an outside-builder contribution informed by actual creation work. It does not establish autonomous invention, renderer import, visual quality, runtime collision, or adoption into `main`.

## Use

Set `PYTHONPATH=src`, then run:

```text
python -m axm_uc.visual_assets_cli 3d-contract-review model.glb contract.json
python -m axm_uc.visual_assets_cli 3d-forge request.json NEW_OUTPUT --spatial-contract contract.json
```

The review command is read-only and prints its report. Exit 0 means PASS; exit 2 means FAIL or HOLD. Invalid caller contracts raise an error before the asset is opened. The forge option validates the contract before starting Blender, checks actual LOD0 output, writes `static-contract-review.json`, and includes it in the forge receipt. A requested failed, unsupported or stale-artifact contract review prevents technical acceptance. Supplying no contract preserves the existing workflow. Existing visual review remains separate and required for visual acceptance.

The bridge takes `operation: "3d-contract-review"`, an explicit local `artifact_path` (relative to the supplied root if not absolute), and a `contract` object. The existing `3d-forge` bridge accepts `spatial_contract`. No external buffers are fetched and no state/learning profile is written by the review. A creator may use the exact findings to change source, rebuild and review new bytes.

```json
{
  "schema": "axm.static-asset-contract/v0.1",
  "bounds": {"min": [-1, 0, -0.5], "max": [1, 1.65, 0.5]},
  "floor_y": 0,
  "tolerance_m": 0.00002,
  "require_root_identity": true,
  "max_triangles": 5000,
  "max_primitives": 12,
  "markers": {"Contact": [0, 0, 0]},
  "collision_boxes": [{"min": [-1, 0, -0.5], "max": [1, 1.65, 0.5]}]
}
```

Only `schema` is mandatory. Omitted checks remain unclaimed; an explicitly supplied collision-box list must be nonempty. The schema rejects unknown fields, malformed vectors, reversed bounds, nonfinite numbers and boolean budgets. All coordinates are transformed scene XYZ in metres, with Y up. `floor_y` compares the lowest rendered vertex with the requested floor. Marker names must identify exactly one reachable node, and its transformed origin must match the supplied position within tolerance.

The report binds the exact GLB bytes and normalized contract by SHA256. These identify the reviewed artifact and request; they introduce no machine-wide logging or hash-baseline requirement. Findings preserve node index/name, primitive and triangle index where applicable. All findings are counted by code; the first 32 detailed examples are retained to bound the report. Later kinds of failure remain visible in `finding_counts` even when earlier triangles fill the examples. `PASS` means the supported geometry meets the supplied checks. `FAIL` means malformed data or a violated/unproven check. `HOLD` means a required feature or work budget is outside this implementation's reviewed subset.

## Geometry and collision proof

The decoder supports one embedded GLB buffer, float32 POSITION vectors, uint8/16/32 index accessors, interleaved positions, nonindexed triangles, matrix or TRS node transforms, negative/nonuniform scale and repeated mesh instances. Counts and bounds describe rendered triangle instances in the default scene, using scene 0 when no default is specified. Unreferenced mesh data is not treated as rendered geometry. Accessor min/max metadata never substitutes for binary positions.

For each triangle, all three vertices must lie inside one proposed axis-aligned convex box. This proves that the whole triangle is enclosed by that box. It is a sufficient, conservative test: a triangle spanning adjacent boxes may be unproven even when their union covers it. `COLLISION_COVERAGE_UNPROVEN` does not claim an exact uncovered surface area. The report does not prove that boxes contain no extra air, that different meshes do not intersect, or that a game uses these boxes correctly. Degenerate triangles have cross-product length at most 1e-12 square metres.

Skins, animation, morph targets, sparse accessors, extended/compressed geometry, external buffers and required extensions outside the small accepted subset produce HOLD. A static bind pose is never reported as a reviewed animation. Container/range/graph validation is bounded but is not a full glTF conformance validator. Limits are 128MiB input, 10,000 reachable nodes, two million elements per accessor/four million decoded elements total, one million triangle instances and five million triangle-box pairs. Unsupported cases never receive a partial PASS.

The binary layout and transform conventions follow the [Khronos glTF 2.0 specification](https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html).

## Concrete source and checks

`tools/blender/axm_fortress_terminals.py` retains the six original terminal generators and editable-source/export/import preview workflow. Run it in Blender with `-- --output NEW_DIRECTORY`. `examples/3d-contracts/reactor-overcharge.json` is the actual four-box overcharge proposal, preserving air above its low capacitor banks. Runtime placements, prices, navigation and interaction remain game-specific.

The unit suite executes actual generated binary fixtures, including transformed/interleaved data, repeated instances, false metadata bounds, collision gaps, incorrect markers, malformed indices/ranges, degeneracy, unsupported encodings and read-only CLI/bridge behavior. Forge integration checks that a requested failing contract writes evidence and blocks its acceptance gate. Tests do not claim aesthetic quality.

The first real terminal review rejected all six v1 exports: five contained 80 collapsed triangles and Slopcaster contained 96 (496 total). Existing bounds, markers and collision coverage passed. Thin-part bevels had clamped at half thickness, collapsing their central faces. The generator now caps bevel width at 0.45 times the smallest part dimension. Fresh Blender 5.2.1 exports contain zero degenerate triangles across the same 19,470 triangles, with exactly unchanged bounds, markers and collision boxes. Thirty fresh source/import/camera previews and 31 bounded hub routes were checked separately. Runtime batching still requires its own imported-geometry check.

`examples/3d-contracts/terminal-revision-review.json` records the exact before/after asset identities and result. Reproduce the static review with `python tools/review_terminal_contracts.py --pack EXISTING_TERMINAL_PACK --output NEW_DIRECTORY`. A newly built pack may explicitly reuse a prior collision proposal using `--collision-contract PATH`. Six real exports must pass; each of 24 in-memory envelope/collision/marker/budget mutations must fail with its expected code. The script never changes its input assets. The corrected pack passes all 24 controls. The original rejected pack remains unchanged.

A subsequent bounded repair covers the four sector gates and bastion: 3,216 original collapsed triangles become zero across 106,708 triangles, without changing counts, exact bounds, node hierarchy/local transforms or glTF material definitions. Their thin cylinders and lofts required a bevel cap based on the shortest source edge; bounding thickness alone was insufficient. The shared Fortress primitive now applies that cap, and `axm_fortress_detail.py --architecture-repair` rebuilds these five assets. All 68 sampled shutter states preserve the original envelope. This proof applies to those rebuilt artifacts; other assets using the shared source still require their own rebuild and review. `examples/3d-contracts/architecture-revision-review.json` retains the concrete identities and measurements.

The bridge and rooftop relay station also route their local one-segment chamfer/cylinder helpers through the shared rule. Their 192 original collapsed triangles become zero across an unchanged 27,272 triangles. Exact bounds, semantics and material definitions remain identical; the complete prior collision contract is preserved. All 21 sampled Deck translations from X=0 to X=12 retain their original posed envelope. `examples/3d-contracts/environment-revision-review.json` records the exact artifacts and checks. Together these repaired source exports resolve 3,904 collapsed triangles; character and weapon repairs require their own motion/contact evidence.

The five remaining combat exports now rebuild through `tools/blender/axm_fortress_contact_repair.py`, including Defender's local bevel operation. Their 467 collapsed triangles become zero across the same 57,788 triangles, with exactly preserved envelopes, hierarchy, local transforms, markers and material definitions. This brings the four repair batches to 18 assets and 4,371 corrected source triangles across an unchanged 211,238 triangles. `examples/3d-contracts/contact-revision-review.json` records the concrete source evidence and its limits.

The full existing Rebounder/Defender review passes on their actual imported geometry: 1,392 configurations and 5,568 utility rows. Supplemental contact review exposed two new visible Pinball body intersections, which remained a hold despite static PASS. A separate game-owner proposal shifts only Pinball's carry within shared hand reach, removes those two strict intersections, introduces no new mesh-pair contacts across all 224 supplementary rows, and passes the full Rebounder/Defender scope again. Breacher's 181 sampled production animation frames preserve marker/envelope behavior and introduce no new mesh-pair contacts. Existing non-grip body/weapon findings remain explicitly open; baseline agreement is not complete rig clearance. The reusable machine change is the source bevel correction and honest static review, not automatic game admission or a claim that all pose defects have been solved.

This change fits the four roots by making geometry claims inspectable, leaving spatial requirements and adoption with the caller, preserving existing creation capabilities and source, and returning unresolved conditions before claiming success. It creates no reward, growth score or automatic rewrite/admission loop.
