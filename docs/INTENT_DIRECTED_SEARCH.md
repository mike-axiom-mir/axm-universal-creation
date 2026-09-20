# Intent-directed headless construction search

UC can now vary freeform geometry, fitted rigs, skin fields and reach/walk controls
without rendering every trial. A successful search retains the construction that
met the declared measurements, along with enough information to reproduce the
search and reuse its settings. Runtime search uses the standard library only.

This builds on the existing form compiler, character-performance compiler,
two-bone solver, GLB decoder, mesh measurements and semantic atom classifier.
The older paint-channel simulation remains available for its own purpose.

## Run

```sh
PYTHONPATH=src python -m axm_uc create examples/construction-search/vessel.json
PYTHONPATH=src python -m axm_uc create examples/construction-search/broader-walker.json
PYTHONPATH=src python -m axm_uc create examples/construction-search/deformation-repair.json
PYTHONPATH=src python tools/construction_search_demo.py /tmp/uc-search-proof --plot
```

Each request writes a **new** output directory. It contains `search.json`; a passing
search also writes `winner.glb` and its retained creator-source sidecar. Existing
outputs are refused. The demo adds measured timings, warm-start comparisons and an
optional plot of actual decoded vertices. Only plotting requires matplotlib.

The attached monolith checkpoint inspected for this build contained UC commit
`78b16c01b543733688d7d036552b63679c87c10b`. Work continued from current GitHub main
`4af36911bfc86500d3c731dc25123d18260bc21c`, preserving the newer character machinery.
The archive itself was not rewritten or promoted to current UC.

## Make intent executable

`search` uses `axm.construction-search/v0.1`:

| Field | Contract |
| --- | --- |
| `intent` | Human-readable purpose, retained unchanged. |
| `recipe` | A form-pattern or character recipe. |
| `controls` | One to eight named controls, each with existing field `paths` and 1..33 ordered `values`. |
| `criteria` | One to sixteen known metrics with `min` and/or `max`; optional positive `scale` normalizes violations during search. |
| `budget` | Maximum `candidates` (1..256), `validations` (1..32), and `validation_samples` (17..257). |
| `motion_probe` | Optional clip, cycles (1..4), foot-part mapping, up axis and ground-plane height. Required for motion criteria. |
| `warm_starts` | Optional prior settings, within current controls. Every reused setting is measured again. |

For example, one control can set the same value on symmetric parts:

```json
{"id":"leg-weight-falloff",
 "paths":[["performance","bindings","left-upper","segment_weights","falloff"],
          ["performance","bindings","right-upper","segment_weights","falloff"]],
 "values":[1,2,4,8]}
```

Paths may change geometry and performance construction only. They must exist and
must not overlap. Values may be numeric parameters, vectors, or complete bounded
construction options accepted by the receiving compiler. No arbitrary expression,
shell command or generated program is executed. A human, deterministic upstream
system or optional AI can translate prose into this same contract.

Available geometry metrics are X/Y/Z extent, surface area, vertex count and triangle
count. Motion metrics are target error, maximum bend, minimum triangle-area ratio,
maximum edge-length ratio, whole-foot contact drift, ground penetration and peak
foot lift. The reported peak lift is the lowest observed peak among the declared
feet. Missing contact or swing coverage remains missing evidence. Unknown metrics
are rejected: an unsupported aesthetic goal cannot silently become a passing score.

## Search order and stopping

1. Try supplied warm starts, then the recipe's current option tuple (first option
   when the current value is outside the supplied list).
2. Traverse neighboring option tuples, prioritizing neighbors of candidates with
   smaller normalized criterion violations. Ties use stable insertion order.
3. Compile cheap geometry and reject exact geometric misses before motion work.
4. Evaluate promising motion candidates at nine coarse query times.
5. Verify coarse passes at the denser requested times, using decoded output.
   At the end, use remaining validation slots on the best unresolved coarse
   candidates too: a coarse grid can miss a useful swing peak.
6. Stop when all declared criteria pass dense validation, or a budget/finite option
   space is exhausted. A budget failure does not publish a winner.

The budgets count work, not elapsed wall time. This preserves search order across
faster/slower machines. Timings belong to the demo's observations, not to the
acceptance decision. Search does not claim an optimal solution; the first verified
acceptable candidate is enough for this contract. Increasing a budget expands the
search effort, not the meaning of its checks.

“Confident” is represented as explicit passed measurements and their scope, with
`probability: null`. Repeating the same observations does not manufacture a
statistical confidence percentage. Finite option-space exhaustion concerns only
the declared options, never all possible shapes.

## Continuous performance and deformation repair

`CharacterController(recipe).sample(clip, elapsed_s, vertices=True)` solves the
retained two-bone construction at the exact supplied time. It uses the existing
GLB pose decoder's validated local transform overrides, then its ordinary world
transform and skin evaluation. The underlying GLB bytes remain unchanged.

For walking, phase may pass one: support targets advance by plant identity while
root travel accumulates across cycles. Query order does not matter, and there is no
hidden wall clock. Reach remains a bounded one-shot performance. Unreachable or
ambiguous poses between baked keys are refused when queried.

The `character-controller` / `character-performance-probe` live route accepts
`path`, `recipe`, `clip`, and increasing `times`, with optional `feet`, `up_axis`
and `ground_height_m`. It retains the recipe, solved transforms and measurements.

The deformation example varies skin-field falloff and softness while preserving
form geometry. It measures triangle-area compression and edge stretch in bent
poses, and retains fields that pass the declared limits. This is a concrete
construction correction, not a claim of anatomical or volume-preserving skinning.

**Baked GLB playback and runtime control are distinct realizations.** A normal GLB
player still interpolates the exported keys. It does not automatically execute UC's
controller. Use the retained recipe with the controller for query-time contacts;
do not apply the controller's root travel a second time.

## Growth and boundaries

The report retains intent, options, constraints, stop reason, trial settings,
failures, measured winner, exact recipe, semantic signature and warm-start settings.
Renames and color-only variants are handled by the existing semantic atom
classifier rather than counted as new construction. Invalid candidates are not
used to suppress later valid alternatives. A saved result is a reusable growth
candidate; existing acceptance/deduplication still governs library admission.

The same machinery can search additional shapes by supplying different form
recipes and controls. New measurement families require real evaluators. Headless
execution does not establish physics, dynamic balance, collision, self-intersection,
unsampled deformation extrema, shaded-normal correctness, artistic quality or
external-engine compatibility. Render only the useful finalists for visual review;
retain those observations separately from numerical acceptance.

Next useful extensions are bounded collision/clearance probes, multiple terrain
scenarios, richer objective trade-offs and accepted-candidate retrieval from the
existing reusable library. These can extend the present controller and search;
they do not require replacing the construction model.
