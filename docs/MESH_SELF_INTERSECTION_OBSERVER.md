# Mesh Self-Intersection Observer v0

`axm_uc.mesh_self_intersection.inspect_triangle_self_intersections()` is a separate opt-in geometric observer for bounded indexed triangle meshes.

It exists because edge incidence and exact-source vertex-fan connectivity do not prove that spatially nonadjacent triangles avoid intersecting. The observer stays separate from `inspect_mesh_topology()` because pairwise geometric inspection has a different work bound and must not silently inherit the topology inspector's 131,072-triangle ceiling as a safe quadratic scan size.

## Placement and provenance

The neutral need was independently demonstrated in two receiving domains before this UC placement:

- `mike-axiom-mir/axm-animal-design` at commit `feb4b24cd36bcc879173138d240754f71db34834`, path `src/axm_animal_design/self_intersection.py`;
- `mike-axiom-mir/axm-character-design` at commit `eae6d296867ecaa40e8f5c3f1fe37d8e3019541e`, path `src/axm_character_design/self_intersection.py`.

Those repositories are used here as requirement and geometric-method precedent only. Their local PASS/FAIL results are not inherited. The UC implementation is independently written and re-tested in UC rather than copying either receiving-domain source.

Historical Animal and Character receipts remain truthful for their exact local implementations. A receiving lane that wants to claim the shared UC successor must pin the UC commit it actually consumes and rerun its own domain evidence.

## Input contract

The observer accepts:

- finite XYZ `positions`, bounded by the shared UC ceiling of 131,072 source vertices;
- a flat indexed-triangle `indices` stream, bounded by 131,072 triangles;
- finite positive `epsilon`, default `1e-9`;
- `max_examples`, from 0 through 16;
- `max_triangle_pair_checks`, default 250,000 and hard-capped at 2,000,000.

Malformed points, non-integer/out-of-range indices, collapsed-by-index triangles, and geometrically degenerate triangles fail closed when a complete scan is within budget.

## Bounded-work contract

The current observer uses an all-unordered-pairs source-triangle scan with AABB rejection before the more expensive triangle-overlap predicates. AABB rejection reduces geometric predicate work, but it does not remove the need to visit each unordered triangle pair.

Therefore the observer computes the exact pair count `n * (n - 1) / 2` before starting the quadratic scan. If that count exceeds the requested budget, it returns:

`HOLD_TRIANGLE_PAIR_BUDGET_EXCEEDED`

with `inspection_complete=false`, zero pair checks performed, `self_intersection_pair_count=null`, and no partial-prefix PASS/FAIL claim. The caller may choose a larger budget only up to the hard ceiling. This is an evidence/work bound, not a performance benchmark.

On a budget HOLD, source points and the index stream are validated for type/range/bounds, but triangle degeneracy is intentionally not geometrically evaluated. The HOLD report says so explicitly rather than implying a stronger validation pass occurred.

## What a complete scan measures

For every unordered triangle pair within budget:

1. pairs sharing an exact source vertex index are excluded as topological neighbours;
2. non-overlapping AABBs are rejected;
3. remaining pairs are tested for finite-float triangle overlap, including a coplanar 2D projection path;
4. total intersections are counted and only bounded deterministic examples are retained.

A complete clean result is:

`PASS_NO_NONADJACENT_SELF_INTERSECTIONS`

A complete detected result is:

`SELF_INTERSECTIONS_DETECTED`

Both are observations, not repair or acceptance authority.

## Truth boundary

This observer does **not** establish:

- adjacent-triangle fold-over/contact semantics;
- seam-welded geometric equivalence;
- exact-arithmetic computational-geometry robustness for every degeneracy or coordinate scale;
- continuous/deformed self-intersection freedom;
- collision-system behaviour;
- rig/deformation correctness;
- visual quality;
- gameplay correctness;
- permission to split, weld, delete, move, or otherwise repair mesh geometry;
- mesh adoption, CANON, game readiness, or production readiness.

The predicates use finite Python `float` arithmetic and caller-visible epsilon thresholds. A consumer needing stronger robustness must establish that separately rather than upgrading this receipt by interpretation.

## Integration boundary

`inspect_mesh_topology()` remains unchanged and still does not run self-intersection geometry automatically. This prevents a new quadratic observer from silently changing the cost or semantics of existing asset pipelines and historical topology receipts.

Consumers opt in explicitly to this observer and retain authority for their own acceptance policy. UC reports geometric facts and bounded HOLD states; it does not encode how many intersections a particular Animal, Character, game asset, collision mesh, or production product may accept.
