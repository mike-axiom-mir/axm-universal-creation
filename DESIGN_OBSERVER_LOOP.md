# Design Fabric Rendered Observer Loop

Design Fabric v0.5 keeps one evidence loop inside AXM Universal Creation:

`Design Genome -> design plan -> browser render -> runtime/pixel observation -> integrated judgment -> repair direction -> explicit repair -> render again`

This remains inside `AXM-CAP-DESIGN-FABRIC`. It is an observer/evidence layer, not another general creation machine.

## Render observation contract

Schema:

`axm.design-render-observation/v0.1`

Every observation is bound to one exact `plan_digest` and one attributed observer. Screenshot, DOM, runtime-probe, pixel, model, and human evidence can therefore meet in one judgment flow without becoming one undifferentiated truth claim.

## Browser runtime probe

Schema:

`axm.browser-runtime-probe/v0.1`

The optional local Chromium-compatible browser bridge still captures real screenshot and DOM bytes. v0.5 additionally attempts a bounded nonvisual runtime probe on a temporary instrumented copy of the requested local HTML. The original project file is not rewritten.

When the browser actually emits the runtime marker, the capture can retain:

- horizontal overflow from document width versus viewport width;
- programmatic focus visibility using computed outline/shadow evidence;
- opaque rendered text contrast where foreground/background can be resolved without guessing through transparency or gradients;
- motion duration signals and a second reduced-motion run when required;
- runtime JavaScript/console error receipts;
- bounded DOM accessibility heuristics such as missing `alt`, missing observed control names, duplicate ids, landmark counts, heading counts, and control counts.

The runtime JSON is materialized beside screenshot and DOM evidence and receives an exact digest.

### Runtime truth boundary

This is not a full browser automation or accessibility suite.

Programmatic focus is not complete keyboard/tab-order proof. The accessibility findings are DOM heuristics, not a browser accessibility tree. The probe does not click controls, submit forms, perform destructive actions, or claim broad interaction coverage. Complex composited contrast remains unproven.

Reduced-motion evidence is conservative. PASS is emitted only when no motion is observed or an actual duration reduction is observed during the reduced-motion run. Equal duration stays unproven because motion may instead be reduced by travel distance or another mechanism.

If the browser/page prevents the probe marker from appearing, runtime evidence stays HOLD rather than being invented.

## Screenshot observer

The deterministic PNG observer remains a separate evidence class. It verifies bounded PNG structure and measures dimensions, colors, luminance, alpha, and neighboring RGB variation. Those pixel facts can feed Design Genome provenance and exact viewport-integrity checks.

Pixel statistics do not become component semantics, text identity, layout quality, or aesthetic truth.

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

Real browser measurements can now move overflow, focus, reduced-motion, and rendered-contrast gates out of HOLD when evidence exists. Interaction and perceptual gates stay HOLD until their own evidence exists.

A PASS is narrow evidence for one exact plan and observation set, not a universal claim of beauty, originality, accessibility, or correctness.

## Repair direction

Failed or held gates still produce bounded repair direction instead of silent source rewriting:

`evidence -> repair direction -> explicit bounded patch -> existing verification -> browser render -> fresh evidence`

No layer accepts its own repair.

## Current frontier

The next useful observer growth is:

1. bounded keyboard traversal and non-destructive interaction recipes;
2. real browser accessibility-tree capture;
3. explicit interaction/runtime error receipts tied to those recipes;
4. an attributed model or human visual observer for hierarchy/spacing/coherence;
5. before/after repair-comparison receipts.

That turns the current camera plus reflexes into a fuller optic nerve while keeping measurement, preference, execution, and acceptance separate.
