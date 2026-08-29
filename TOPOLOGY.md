# AXM Universal Creation — Anatomy / Kernel Topology

This file describes current machine structure. It is not an activity log and it does not manufacture dependency history.

## Why this layer exists

The broad Universal Creation Map and the smaller implementation kernel serve different roles:

- the **master anatomy** describes a wide vocabulary of possible atoms, components, and organs;
- the **core kernel** describes a much smaller implementation-oriented dependency skeleton.

The master anatomy is intentionally not rewritten with guessed dependencies. Instead, the runtime builds an inspectable crosswalk when evidence is strong enough and traverses only dependencies that are actually declared in the kernel.

## Measured baseline

Current verified repository state:

| Measure | Current value |
| --- | ---: |
| Master anatomy records | 2,165 |
| Master dependency edges | 0 |
| Master relationship edges | 0 |
| Core-kernel records | 100 |
| Core dependency edges | 175 |
| Core dependency edges resolving to another core record | 175 |
| Core unresolved dependency edges | 0 |
| Master records with a traversable exact crosswalk | 104 |
| Ambiguous exact crosswalks | 0 |
| Master records left unresolved | 2,061 |
| Core records reached by at least one exact master crosswalk | 94 |
| Core records without an exact master crosswalk | 6 |

These numbers are regression-tested in `tests/test_topology.py`.

## Crosswalk rule

A master record becomes a **traversable kernel seed** only when:

1. its normalized name exactly matches a core-kernel record name; and
2. both records have the same anatomy level (`atom`, `component`, or `organ`); and
3. the match resolves to exactly one core record.

That produces:

`DETERMINISTIC_EXACT_CROSSWALK`

This is intentionally conservative. It allows the machine to use topology without quietly promoting similarity into fact.

### Weaker correspondences

For unresolved selected anatomy, the runtime may show candidate correspondences using visible token/source overlap. Those candidates are explicitly:

- non-traversable;
- suggestions only;
- not dependency edges;
- not proof of equivalence.

They exist so a human, AI, or later learned matcher can inspect where a bridge *might* exist without changing current truth.

## Example

The master component:

`AXM-02-DATA-MATH-C-012-graph`

has an exact crosswalk to:

`AXM-CORE-C-006-graph`

The kernel graph declares dependencies on:

- `AXM-CORE-A-028-node-reference`
- `AXM-CORE-A-029-edge`
- `AXM-CORE-A-022-relation-predicate`

The runtime can therefore traverse that declared dependency path instead of stopping at the lexical word `graph`.

By contrast, a record such as `scene graph` can be suggested as related to the core graph, but is not traversed through it unless a stronger explicit correspondence is established.

## Planner behavior

`axm-uc plan` still reports its matcher truth as:

`DETERMINISTIC_LEXICAL_BASELINE`

The lexical matcher has not become semantic intelligence. Kernel topology is returned as a separate object with its own truth status:

`DETERMINISTIC_CROSSWALK_PLUS_DECLARED_KERNEL_GRAPH`

When selected anatomy has an exact crosswalk, the planner can now report a `kernel-backed-unimplemented-path` and show the declared dependency nodes behind it.

This is more informative than a flat lookup while still preserving the distinction between:

- **anatomy exists**;
- **kernel topology exists**;
- **a live executable capability exists**.

The first two do not imply the third.

## Inspect it

```bash
PYTHONPATH=src python -m axm_uc topology
PYTHONPATH=src python -m axm_uc topology --master-id AXM-02-DATA-MATH-C-012-graph --depth 4
PYTHONPATH=src python -m axm_uc topology --core-id AXM-CORE-C-006-graph --depth 4
PYTHONPATH=src python -m axm_uc plan examples/requests/plan_graph.json --per-level 8
```

The verified graph example currently crosses into the kernel and traverses declared dependencies. A broader graph planning request in the verification run selected five kernel seeds and reached seventeen kernel nodes.

## Current boundary

This topology layer does **not**:

- edit the 2,165 master records;
- infer arbitrary dependency edges;
- turn candidate suggestions into facts;
- claim that kernel records are implemented/live;
- claim semantic understanding;
- require a neural model.

Its job is narrower: expose and use the dependency structure that already exists, wherever the broad anatomy can be connected to it without inventing a bridge.
