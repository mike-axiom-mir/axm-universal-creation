# Creator-parts retention

Universal Creation grows from reusable causes, not from a pile of end products.

For a successful creation, source authority consists of the explicit intent,
bounded controls, part definitions, material/effect recipes, assembly graph,
motion, exact dependency pins, executable capability version and verification
evidence required to reproduce or reshape the work. A PNG, movie, GLB or other
export is a realization of that state. It may be retained for delivery or
regression comparison, but it is not machine growth by itself.

The parallel creator now publishes `parts-index.json` beside `stickers.sqlite`.
The index exposes every successful task root, including unselected candidates;
the registry retains the exact definitions and bytes. `library.json` remains the
portable dependency closure for the selected result.

It also publishes `atom-library.json`. This is a semantic novelty gate rather
than a file-hash list. Identity labels and color/tint/palette values are removed
from atom identity. A differently colored copy of the same geometry is retained
as an exact realization variant but does not count as growth. Geometry/topology,
attachments, behavior, assembly and effect topology may create new atoms;
material structure is tracked separately from color overrides. The first member
of an equivalence group is its canonical atom, and later equivalents point back
to it.

The runtime growth loop is:

`propose parts or recipes -> assemble -> execute -> verify -> accept or reject -> retain accepted causes -> reuse`

Human controls and optional AI orchestration operate on the same retained state.
AI may suggest intent, selections or new bounded recipes, but it is not the owner
of the construction capability. Rejected candidates may remain evidence, but do
not silently become canonical reusable parts. Cosmetic variants do not inflate
the growth count.

This contract is implemented for parallel creation and the high-level surface
creator that routes through it. Other UC exporters must adopt an equivalent
source-closure contract before claiming that their output contributes to runtime
self-growth.


## Default source retention on source-first 3D routes

The live source-first 3D routes now retain construction state beside the realization by default:

- `procedural-3d-asset` retains the exact supplied procedural/surface specification;
- `shape-recipe-asset` retains the original MorphTile-inspired recipe, expanded specification and donor provenance;
- `form-pattern-asset` retains the freeform profile/loft/revolve/tube recipe plus semantic part index;
- `character-recipe-asset` retains the whole character recipe, race/body-family identity, sockets, clothing regions, material intent and compiled geometry.

These routes write a sibling `<asset>.glb.source.json` using `axm.creator-source/v1`.
The sidecar is source authority for replay/reshaping; the GLB is a realization.
Publication is coupled: if source retention fails, the newly written GLB is rolled
back rather than silently leaving an end product whose construction causes were lost.

This does not rewrite older specialist exporters into one format. Existing authored
character/vehicle paths that already retain editable `.blend` sources, manifests,
builder code and verification evidence continue to use those stronger specialist
source records. A legacy exporter that retains only an end product still may not
claim runtime self-growth until it adopts equivalent source closure.

Source retention is not automatic CANON. It preserves what was made and how; admission
to a reusable global library remains a separate explicit decision.
