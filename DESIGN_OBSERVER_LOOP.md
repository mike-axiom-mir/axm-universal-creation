# Design Fabric Rendered Observer Loop

Design Fabric v0.2 adds the evidence bridge that v0.1 deliberately left open.

The machine still does **not** pretend that parsing source is the same thing as seeing a rendered interface. Instead it now has a provider-neutral contract through which an authorized external observer can return what was actually observed.

The loop is:

`Design Genome -> design plan -> render outside this module -> external observation receipt -> integrated judgment -> repair direction -> explicit repair -> render again`

This stays inside `AXM-CAP-DESIGN-FABRIC`. It is an observer adapter layer, not a second design ontology or another general creation machine.

## Render observation receipt

Schema:

`axm.design-render-observation/v0.1`

Every observation is bound to one exact `plan_digest` and one attributed observer.

Supported observer kinds are:

- `human`;
- `browser-tool`;
- `model`;
- `test-fixture`;
- `other`.

A receipt may contain one capture per requested viewport. Each capture keeps:

- exact viewport id and dimensions;
- declared artifact digests;
- deterministic measurements;
- attributed perceptual assessments;
- one deterministic capture digest.

Current artifact kinds include screenshots, DOM snapshots, accessibility trees, interaction logs, computed styles, performance traces, and openly labeled other artifacts.

The Design Fabric does not claim to fetch or verify those artifact bytes. A supplied SHA-256 value proves only what the observer declared unless a separate authorized tool actually verifies the bytes.

## Runtime measurements

A capture can currently report bounded measurements for:

- horizontal overflow;
- visible focus behavior;
- reduced-motion behavior;
- minimum rendered text contrast;
- interaction error count.

These are external observations. The deterministic Design Fabric only validates their shape, binds them to the exact plan and viewport, and applies declared gates.

## Perceptual assessments

Visual qualities that cannot be reduced to the current deterministic measurements stay attributed assessments rather than being promoted to objective facts.

The default integrated judgment requests:

- `visual-hierarchy`;
- `spacing-consistency`;
- `component-coherence`.

Each assessment carries:

- `PASS`, `FAIL`, or `HOLD`;
- confidence from `0..1`;
- an explicit basis;
- the observer identity inherited from the observation receipt.

A future vision model, human reviewer, browser agent, or other observer can therefore contribute visual judgment without becoming hidden authority inside the Design Genome.

## Integrated judgment

Schema:

`axm.design-integrated-judgment/v0.1`

The integrated judge combines the original structural Design Judge with external evidence gates for:

- requested viewport coverage;
- screenshot evidence coverage;
- horizontal overflow;
- runtime focus visibility;
- runtime reduced-motion behavior;
- rendered text contrast;
- interaction errors;
- required perceptual assessments.

The status rule remains simple:

`any FAIL -> FAIL`

`otherwise any HOLD -> HOLD`

`otherwise -> PASS`

A PASS is narrow evidence for one exact plan and observation set. It is not a universal claim of beauty, originality, accessibility, or correctness.

## Repair direction

Schema:

`axm.design-repair-plan/v0.1`

A failed or held integrated judgment can produce deterministic repair direction such as:

- responsive-layout repair;
- interaction-state repair;
- motion-policy repair;
- color-system repair;
- interaction-runtime repair;
- visual-composition repair;
- missing observer evidence.

This repair plan does not modify source by itself and cannot accept its own repair.

The intended next connection is existing Universal Creation project-repair machinery:

`repair direction -> explicit bounded source patch -> existing verification -> render again -> fresh observation receipt`

That preserves the separation between **evidence**, **proposed change**, **execution**, and **acceptance**.

## Live operations

| Creation kind | Operation | Result |
| --- | --- | --- |
| `inspect-design-observer` | `inspect-observer` | Inspect observer schemas and truth boundaries. |
| `record-design-render-observation` | `record-render-observation` | Normalize and digest attributed viewport evidence. |
| `judge-rendered-design` | `judge-rendered` | Combine structural and external render evidence. |
| `propose-design-repair` | `propose-repair` | Convert failed/held gates into bounded repair direction. |

## What is still missing

The machine now knows **how to receive eyes**, but this module is not itself the camera.

The next useful implementation is an authorized browser executor that can actually:

1. open the created local interface;
2. render declared viewports;
3. capture screenshot bytes and their real digests;
4. inspect DOM/accessibility/runtime state;
5. exercise bounded interactions;
6. return those observations through the contract above.

A separate vision observer may then evaluate visual hierarchy and coherence from the captured image while retaining its model/version/source receipt.

That produces the fuller loop:

`create -> browser render -> machine evidence + visual observation -> judge -> repair -> browser render -> compare`

No fake eyes are required in the meantime.
