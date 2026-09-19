# Direction routing and temporary candidate instances

UC now distinguishes a route that can technically emit something from a route
that is sufficient for the requested outcome. Ordinary-language direction is
normalized into `axm.direction-contract/v0.1` with explicit purpose,
deliverables, medium, dimensionality, motion, subjects, environment,
interaction, platform/use, quality bar, editability, reusable assets,
provenance, constraints, verification and ambiguity.

The router reads current live capability manifests. It does not maintain another
capability registry. Each candidate route is classified as:

- `COMPATIBLE_AND_SUFFICIENT`
- `COMPATIBLE_BUT_INSUFFICIENT`
- `INCOMPATIBLE`
- `UNKNOWN_HOLD`

A produced artifact is not success when required contract features or inputs are
missing. A high-quality 3D/editable/reusable request therefore cannot silently
fall through to Paintgun's deterministic SVG/static-web route. The route remains
visible as compatible visual machinery, but its declared limitations and missing
3D requirements keep it insufficient.

Use a JSON direction request without an internal creation kind:

```json
{
  "prompt": "Build a high-quality 3D demonstration with editable reusable assets"
}
```

Run it with `axm-uc direct request.json`, or pass the same body to
`axm-uc create`. The result is either an executed sufficient exact route or an
honest `DIRECTION_HOLD` with the manifest-grounded production graph, exact
missing requirements and missing route inputs. Bounded language extraction is
not presented as general semantic understanding.

## Temporary candidate overlay

When the missing piece is bounded, `candidate_instance` may supply one to four
candidate manifests representing an initial attempt and explicit repairs. UC:

1. creates an isolated workspace under `creations/` or at an external path;
2. tests each detached candidate against the continuing canonical capabilities;
3. preserves every failed attempt and test receipt;
4. invokes only the first candidate that passes its request-shaped tests;
5. records execution and disposition;
6. hashes the live manifest set before and after to prove the overlay did not
   install, register, route or otherwise mutate canonical UC.

Supported dispositions are `discard`, `retain-artifact-only`,
`retain-recipe-outside-canon`, `generalize-reusable-candidate` and
`propose-admission`. Retaining or proposing a candidate is not admission. A
reusable capability can enter live UC only through the existing candidate test,
review and adoption/merge gates.

Candidate execution without independent artifact verification returns
`HOLD_ARTIFACT_NOT_INDEPENDENTLY_VERIFIED` even when it wrote an artifact. That is
intentional: successful execution is not the same as verified delivery.
