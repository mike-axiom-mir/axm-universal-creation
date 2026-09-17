# Indexed surface eligibility observer

`axm_uc.indexed_surface_eligibility` is a bounded, observer-only contract for deciding whether an explicitly described render vertex domain can be considered for attribute-aware indexing.

It does **not** rewrite geometry, select a product representation, promise visual equality, or claim runtime savings.

## Input

Schema: `axm.indexed-surface-lineage/v0.1`.

Required identities:

- `source_identity`
- `surface_identity`

Required source domain:

- `vertex_count`
- triangle `indices`

Required render domain:

- `vertex_count`
- triangle `indices`
- per-vertex `channels`
- `source_vertex_indices` whenever the render domain is expanded or remapped
- explicit `protected_split_ids` whenever the render domain is expanded or remapped; `null` explicitly declares that no extra non-attribute split identity is required for that render vertex

Supported channels in v0.1 are `POSITION`, `NORMAL`, `TEXCOORD_0`, `TANGENT`, `COLOR_0`, `JOINTS_0`, and `WEIGHTS_0`. Unknown channels return `NOT_EVALUATED_UNSUPPORTED_CHANNEL` rather than being ignored.

### Candidate identity policy

The optional `candidate_identity_policy` keeps the conservative historical behavior by default:

- `SOURCE_VERTEX_AND_ATTRIBUTES` — default. Source-vertex lineage participates in the candidate key, so distinct source vertices are never merged merely because their declared render attributes match.
- `ATTRIBUTES_AND_PROTECTED_SPLITS` — explicit diagnostic mode for triangle-corner or other receiver domains where the caller wants to ask whether exact declared render tuples permit indexing across distinct source vertex identities. In this mode `protected_split_ids` is mandatory for every render vertex, including explicit `null` entries where the caller declares that no extra non-attribute split identity is required.

The second policy is an **observer question**, not an authorization to weld semantic/source topology. Product/source owners still own whether cross-source deduplication is meaningful or acceptable.

## Output

Schema: `axm.indexed-surface-eligibility-report/v0.1`.

The report keeps source and render domain identities separate and returns deterministic digests, an exact topology-lineage receipt, the selected `candidate_identity_policy`, a render-vertex-to-candidate map, candidate indices, position-coincident split diagnostics, cross-source candidate diagnostics, and explicit non-claims.

Important states include:

- `PRESERVE_SOURCE_INDEXING` — the declared render domain exactly reproduces the source triangle-corner stream and no smaller candidate exists under the selected identity policy.
- `POST_ATTRIBUTE_TUPLE_DEDUP_CANDIDATE` — exact supported attribute tuples plus protected split identity permit a smaller candidate index domain under the selected policy. This is only a structural candidate.
- `HOLD_TOPOLOGY_LINEAGE_MISMATCH` — mapping the render triangle-corner stream through `source_vertex_indices` does not exactly reproduce `source.indices`, so the observer cannot claim this render domain descends from the supplied source topology.
- `HOLD_ATTRIBUTE_SEAM_AMBIGUITY` — an expanded/remapped render domain omitted the explicit protected-split declaration required by this observer.
- `HOLD_CROSS_SOURCE_SPLIT_DECLARATION_REQUIRED` — cross-source tuple evaluation was requested without an explicit `protected_split_ids` declaration.
- `NOT_EVALUATED_UNSUPPORTED_CHANNEL` — a present channel is outside the bounded supported set.

`render_domain_state` is reported separately. `RENDER_DOMAIN_SPLIT_REQUIRED` means the declared source->render lineage requires more candidate render identities than the source vertex domain after exact supported attributes and protected split IDs are respected. `RENDER_DOMAIN_CROSS_SOURCE_DEDUP_CANDIDATE` means the explicit cross-source policy found one or more candidate identities spanning distinct source vertices.

## Exactness rules

- No tolerance-based welding is performed.
- The render triangle-corner stream, mapped back through `source_vertex_indices`, must exactly equal `source.indices`; reordered or changed topology is held rather than inferred equivalent.
- Full supported per-vertex tuples are used, never position alone.
- `SOURCE_VERTEX_AND_ATTRIBUTES` keeps source-vertex lineage in the candidate key.
- `ATTRIBUTES_AND_PROTECTED_SPLITS` removes source-vertex identity from the candidate key only when explicitly requested and only after an explicit protected-split declaration is supplied.
- Explicit protected split IDs participate in the candidate key even when all supported attributes are identical.
- Expanded/remapped domains without an explicit protected-split list are held rather than guessed.
- Cross-source candidate groups are reported separately so a storage candidate cannot silently masquerade as source-topology equivalence.
- Candidate maps are diagnostic output only; this module never emits a replacement mesh.

## Boundary

A structural PASS does not establish rendered equality, shader/tangent-space equivalence, target-engine determinism, memory savings, FPS improvement, target-device behavior, semantic vertex-weld validity, product adoption, CANON, or production readiness. Each receiving owner must rerun its own exact A/B evidence before adopting a representation change.
