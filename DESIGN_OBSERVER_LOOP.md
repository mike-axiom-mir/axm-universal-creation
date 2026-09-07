# Design Fabric Rendered Observer Loop

Design Fabric v0.8 keeps one evidence loop inside AXM Universal Creation:

`Design Genome -> design plan -> browser render -> runtime/pixel/interaction observation -> integrated judgment -> repair direction -> explicit transactional repair -> fresh render/judgment -> bound before/after comparison -> repair-cycle receipt`

This remains inside `AXM-CAP-DESIGN-FABRIC`. It is an observer/evidence layer, not another general creation machine.

## Render observation contract

Schema:

`axm.design-render-observation/v0.1`

Every observation is bound to one exact `plan_digest` and one attributed observer. Screenshot, DOM, runtime, interaction, pixel, model, and human evidence can meet in one judgment flow without becoming one undifferentiated truth claim.

## Browser runtime probe

Schema:

`axm.browser-runtime-probe/v0.1`

The optional local Chromium-compatible browser bridge captures real screenshot and DOM bytes and attempts a bounded nonvisual runtime probe on a temporary instrumented copy of the requested local HTML. The original project file is not rewritten.

When the browser actually emits the runtime marker, the capture can retain:

- horizontal overflow from document width versus viewport width;
- programmatic focus visibility using computed outline/shadow evidence;
- opaque rendered text contrast where foreground/background can be resolved without guessing through transparency or gradients;
- motion duration signals and a second reduced-motion run when required;
- runtime JavaScript/console error receipts;
- bounded DOM accessibility heuristics such as missing `alt`, missing observed control names, duplicate ids, landmark counts, heading counts, and control counts.

Every browser invocation receives a fresh temporary user-data directory. This prevents the observer from intentionally sharing the caller's ordinary cookies/localStorage/session state, but is not claimed as an operating-system sandbox.

### Runtime truth boundary

Programmatic focus is not complete keyboard/tab-order proof. The accessibility findings are DOM heuristics, not a browser accessibility tree. Complex composited contrast remains unproven.

Reduced-motion evidence is conservative. PASS is emitted only when no motion is observed or an actual duration reduction is observed during the reduced-motion run. Equal duration stays unproven because motion may instead be reduced by travel distance or another mechanism.

If the browser/page prevents the probe marker from appearing, runtime evidence stays HOLD rather than being invented.

## Explicit bounded interaction recipes

Schema:

`axm.browser-interaction-probe/v0.1`

The browser observer can execute caller-authored recipes instead of inventing an autonomous interaction crawl.

A recipe contains an id and bounded steps. v0.8 supports:

- `focus` on an exact CSS selector;
- `activate` on an exact CSS selector only when `allow_synthetic_activation=true` is explicitly supplied.

Synthetic activation is restricted to visible button-like controls: `button`, `summary`, `role=button`, checkbox/radio inputs, and button inputs. Arbitrary links are outside the activation contract. Form submission is intercepted and blocked by the temporary probe.

For each step the evidence can retain the selector, action, status, bounded before/after control state, whether state changed, and any probe error. When at least one recipe was requested and the marker is observed, `interaction_error_count` enters the existing integrated judgment.

### Interaction truth boundary

This is **not** real keyboard traversal and does not create trusted human input events. `HTMLElement.click()` is synthetic browser execution. A PASS means only that the exact requested recipes completed without recorded probe errors for the exact selectors and viewport.

It does not prove discoverability, usability, correct tab order, assistive-technology behavior, or that the requested product behavior was semantically the right behavior.

## Screenshot observer

The deterministic PNG observer remains a separate evidence class. It verifies bounded PNG structure and measures dimensions, colors, luminance, alpha, and neighboring RGB variation. Those pixel facts can feed Design Genome provenance and exact viewport-integrity checks.

Pixel statistics do not become component semantics, text identity, layout quality, or aesthetic truth.

## Before/after repair comparison

Schema:

`axm.design-render-comparison/v0.1`

A repair cycle can compare one exact before screenshot with one exact after screenshot.

Before comparison, Design Fabric re-reads both PNG files and verifies that each byte digest matches the screenshot artifact declared by its corresponding render-observation receipt. Only then does it measure:

- changed-pixel count and fraction;
- mean and maximum RGB L1 delta;
- mean alpha delta;
- mean encoded-luminance delta;
- an up-to-8x8 regional change grid.

Different raster dimensions produce HOLD rather than silent resampling.

The comparison deliberately does **not** say the new image is better. Pixel change, visual improvement, semantic correctness, and regression are different truth classes.

## Attributed visual assessment

Higher-level perceptual questions remain attributed observations:

- visual hierarchy;
- spacing consistency;
- component coherence;
- other visual judgments that cannot currently be reduced to deterministic facts.

A human, model, browser agent, or another explicitly identified observer can provide those assessments with confidence, basis, tool/model identity, plan digest, and screenshot/artifact digests.

## Integrated judgment

The rule stays simple:

`any FAIL -> FAIL`

`otherwise any HOLD -> HOLD`

`otherwise -> PASS`

Real browser measurements can move overflow, focus, reduced-motion, rendered-contrast, and explicit interaction-error gates out of HOLD when their own evidence exists. Perceptual gates stay separate until an attributed observer supplies them.

A PASS is narrow evidence for one exact plan and observation set, not a universal claim of beauty, originality, accessibility, or correctness.

## Repair direction

Failed or held gates produce bounded repair direction instead of silent source rewriting:

`evidence -> repair direction -> explicit bounded patch -> existing transactional repair/verification -> browser render -> fresh evidence -> before/after comparison`

No Design Fabric layer accepts its own repair.

## Repair-cycle continuity receipt

Schema:

`axm.design-repair-cycle-receipt/v0.1`

v0.8 can now bind a complete observed repair lane without performing or approving the repair itself. The receipt requires:

1. the exact pre-repair integrated judgment;
2. the Design Fabric repair plan whose `source_judgment_digest` matches it;
3. a published, validation-passed `OBSERVED_TRANSACTIONAL_PROJECT_REPAIR` result from existing Universal Creation repair machinery;
4. the exact pre-repair and post-repair render-observation receipts;
5. the bound before/after render comparison;
6. the exact post-repair integrated judgment.

Every link is digest-checked. A mismatch fails closed.

The cycle records overall FAIL/HOLD/PASS movement and per-gate transitions such as `TOWARD_PASS`, `UNCHANGED`, or `AWAY_FROM_PASS`. That is evidence-state movement only. Even a post-repair PASS does not become an automatic claim that the interface is beautiful, semantically correct, accepted by a human, or finished.

The repair-cycle recorder does not rewrite source. It consumes the evidence emitted by the already-existing transactional repair boundary and gives the whole loop one deterministic continuity digest.

## Current frontier

The next useful observer growth is:

1. real keyboard traversal evidence rather than programmatic focus;
2. browser accessibility-tree capture;
3. richer non-destructive interaction state assertions while keeping recipes explicit;
4. an attributed model or human visual observer for hierarchy/spacing/coherence;
5. eventually using accumulated repair-cycle receipts as evidence for which repair strategies worked in which context, without silently turning history into policy or taste.

The camera now has pixel sensing, runtime reflexes, explicit bounded interaction probes, repair-delta memory, and an end-to-end continuity receipt. The remaining work is deeper semantics and stronger attributed perception, not pretending every measurable signal is taste.
