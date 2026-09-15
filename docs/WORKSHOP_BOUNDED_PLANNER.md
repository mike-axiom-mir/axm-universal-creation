# Workshop Bounded Planner v0.1

Universal Creation now has enough deterministic workshop instruments to stop treating the first constructible answer as the answer.

The bounded planner composes four existing layers:

1. Design Workshop sketch intent,
2. exact reusable 3D sticker definitions,
3. actual triangle-geometry calipers,
4. actual rest-pose clearance/contact evidence.

It searches or accepts candidate sticker pools, assembles bounded combinations in an ephemeral registry, measures them, rejects candidates that do not satisfy all requested evidence gates, and selects the smallest explicit numeric size-error result. An incumbent assembly can be supplied as a continuity baseline; a passing incumbent survives unless a candidate strictly improves the numeric objective.

## Why this exists

Adding creative capabilities does not imply that the next generated asset is better than the previous one. A machine can gain more tools while still making a worse choice about which tool/output to keep.

The planner adds selection pressure without inventing a universal quality score:

`candidate parts -> temporary assembly -> actual measurement -> reject or accept -> compare accepted evidence -> preserve incumbent or select strict improvement -> optional explicit retention`

The first objective is intentionally narrow. It can protect structural progress. It cannot truthfully decide that one asset is prettier, more expressive, more cinematic, more readable, or more fun from geometry alone.

## Candidate sources

Every sketch part has one planner slot. A slot uses exactly one candidate source.

### Explicit pins

The caller may supply 1..8 exact immutable sticker pins.

```json
{
  "part": "wheel-front-left",
  "candidates": [
    {"id": "wheel-a", "version": 1, "digest": "..."},
    {"id": "wheel-b", "version": 3, "digest": "..."}
  ]
}
```

### Registry query

The caller may instead define a bounded exact metadata query.

```json
{
  "part": "wheel-front-left",
  "query": {
    "adapter": null,
    "socket": "mount",
    "tag": "wheel",
    "limit": 8
  }
}
```

At least one of adapter/socket/tag must be constrained. UC scans at most 512 matching registry rows. Results are filtered to 3D stickers, converted to exact pins, sorted deterministically, and truncated to the declared slot limit before any candidate construction begins.

A name or tag is discovery evidence only. It is not proof that a sticker is semantically correct for the intended role.

## Bounded combinations

v0.1 permits:

- at most 32 sketch parts/slots,
- at most 8 exact candidates per slot,
- at most 256 Cartesian candidate assemblies.

A request whose resolved product exceeds 256 fails closed before candidate construction.

## Ephemeral construction

Preview does not save trial assemblies in the user's source sticker registry.

UC creates a temporary SQLite registry, copies only the exact dependency closure required by the resolved candidates/incumbent, and creates deterministic temporary assemblies there. Nested assemblies and multiplied stickers remain ordinary exact dependencies and are therefore evaluated normally.

The source registry remains unchanged during preview.

## Evidence gates

Every candidate is measured by the existing Workshop geometry comparator. If a clearance companion plan is supplied, that plan is also measured.

A candidate is accepted only when:

- the combined sketch/placement/actual-size geometry report is `PASS`, and
- every supplied clearance/contact requirement is `PASS`.

`FAIL` and `HOLD` are both non-selected evidence states. The planner does not convert missing evidence into success.

## Objective

The v0.1 objective is closed and explicit:

```json
{
  "kind": "minimize-size-error",
  "require_all_evidence_pass": true,
  "incumbent_policy": "strict-improvement"
}
```

Among fully passing candidates UC compares:

1. maximum absolute XYZ part-size error in metres,
2. total absolute XYZ part-size error in metres,
3. exact selection signature only as a deterministic tie-break between new candidates.

Clearance is a gate rather than a hidden optimization direction. A candidate does not get extra points merely for creating excessive empty space.

## Incumbent protection

An optional exact saved assembly pin may be supplied as `incumbent`.

If the incumbent passes all requested evidence gates, a candidate replaces it only when the candidate has a strictly smaller numeric `(max size error, total size error)` tuple.

Equal evidence is not improvement. The incumbent stays selected.

If the incumbent is not PASS, a fully passing candidate may be selected as a recovery. If no passing replacement exists, the incumbent remains the retained baseline and the planner reports HOLD rather than pretending it found an improvement.

This rule is specifically designed to prevent capability growth from silently becoming output regression.

## Explicit retention

`preview-workshop-plan` is read-only with respect to candidate assemblies.

`retain-workshop-plan` repeats the exact planning evidence and then:

- performs no write if the protected incumbent remains selected, or
- creates one new immutable ordinary assembly sticker when a passing new candidate is selected and the caller supplied explicit output identity/version/provenance.

The selected child pins are preserved. Prior sticker versions are not rewritten.

The retained assembly is measured again after publication. Retention is evidence-bearing state, not CANON authority.

## Human / script / machine parity

The live capability operations are:

- `inspect-workshop-planner`
- `preview-workshop-plan`
- `retain-workshop-plan`

The same underlying functions are available through `axm-sticker-create` JSON operations:

- `preview_workshop_plan`
- `retain_workshop_plan`

## Truth boundary

The planner does **not** currently judge:

- rendered visual quality,
- expression or emotional readability,
- aesthetics/style,
- gameplay feel,
- physical strength,
- swept-animation clearance,
- target-engine quality,
- semantic correctness inferred from prose/tags.

Those can become separate evidence gates later. They should not be smuggled into a geometry score.

The intended next growth path is to feed bound rendered/user-review evidence into the same retain-or-reject loop, so a visually worse candidate can be rejected without pretending geometry already proves visual quality.
