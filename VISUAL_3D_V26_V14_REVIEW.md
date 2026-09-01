# Axiom v26 / Mir v14 Exact-Context Visual Review

## Evidence boundary

- Source commit: `e31d7036a5aab6695a1aeb03119ac5442d6f0517`
- Workflow run: <https://github.com/mike-axiom-mir/axm-universal-creation/actions/runs/33536097915>
- Workflow artifact: `axiom-v26-mir-v14-exact-context-proof`
- Artifact ZIP SHA-256: `bd8f94d7638f1a01bf551817d087b010ca28b9c1f458e39ef02a0de92decaadc`
- Runtime used for this proof: Ubuntu 24.04, Blender 4.0.2, software OpenGL
- Review method: full-frame static inspection of all four 1024px proof angles for each asset

The Linux render route is proof infrastructure only. It does not replace the retained Windows 5.2.1 runtime bootstrap contract. A passing forge proves technical readiness; it does not award visual acceptance.

## Technical receipts

| Asset | LOD0 triangles | LOD1 | LOD2 | Meshes | Materials | Images / textures | Collision meshes | Technical result |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| Axiom Bastion Frame v26 | 110,412 | 53,192 | 20,436 | 261 | 5 | 15 / 15 | 4 | PASS |
| Mir Sanctuary Keeper v14 | 157,632 | 76,050 | 29,726 | 328 | 6 | 18 / 18 | 4 | PASS |

Both receipts retain `REJECTED_OR_REVIEW_REQUIRED` because their forge-time visual review is `REQUIRED`; export success was not promoted to AAA.

## Static visual inspection receipts

### Axiom v26

Claim: tapered articulated cowls replace repeated rectilinear anatomy and keep surface hardware secondary.

- Bound front proof SHA-256: `910881f4952935c79efe1fac3044c3660f1133643aba9890279e11681f5acbf0`
- Visible improvement: large pale polygonal cowls now cover the chest, upper arms, forearms, thighs, and shins; the old small geometric tile grids no longer define those front masses.
- Visible failure: broad rectangular dark volumes still control much of the side and rear torso, pelvis, arms, and legs. Rear heat-exchanger blocks add another repeated slab cadence.
- Visible failure: the cyan chest element remains a flat luminous insert rather than a compact recessed reactor lens behind a load-bearing cage.
- Exact claim verdict: **FAIL / partial improvement**.
- Overall AAA visual verdict: **FAIL** on `aaa-form-hierarchy`; the other required criteria pass for this bounded review.
- Next retained lesson: carry the cowl language through the complete side/rear silhouette and recess the reactor lens.

### Mir v14

Claim: close the torso with a descending V-shell stack and replace rail-like feet with compact armored hooves.

- Bound front proof SHA-256: `c45efa91c92bf300f734993af9955da1fcbfd61412b9c8f84275cc96f3d9d585`
- Visible pass: four overlapping pointed shells create a closed descending front torso from collar to waist.
- Visible pass: both feet have short load-bearing hoof bodies, compact split toe caps, and braced heel forms; side and rear views do not show presentation-stand rails.
- Exact claim verdict: **PASS**.
- Overall AAA visual verdict: **FAIL** on `aaa-form-hierarchy`: the side/rear torso still reads as many separate petals and thin halo members around a narrow tubular back rather than one dominant sanctuary load hierarchy.
- Next retained lesson: carry the sanctuary shell hierarchy around the rear torso and root the halo into a dominant armored backplane.

## Separation preserved

| Layer | Axiom v26 | Mir v14 |
|---|---|---|
| Forge / decoded GLB technical readiness | PASS | PASS |
| Requested anatomy correction | PARTIAL / FAIL | PASS |
| Artifact-bound AAA visual acceptance | REJECTED | REJECTED |

No asset is labeled AAA from triangle counts, export success, source intent, or automated tests.
