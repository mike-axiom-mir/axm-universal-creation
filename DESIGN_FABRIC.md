# Design Fabric v0.1

Design Fabric upgrades **AXM Universal Creation** with a reusable design-knowledge layer. It is not a new top-level creation machine and it is not a final `make it pretty` pass.

The intended placement is inside creation:

`goal -> software plan + design plan -> components/assets -> composition -> structural/visual evidence -> repair -> creation`

The existing Asset Atom body remains the ingredient layer. Paintgun, Vector Cells, Chameleon, simulation, and future renderers remain expression/state machinery. Design Fabric adds the missing grammar layer that answers questions such as:

- which visual tokens belong together;
- which component semantics and states are available;
- how layout changes across viewports;
- what motion language is allowed;
- which material/surface signals define the visual language;
- what evidence is still missing before a design-quality claim is justified.

## Why this is an upgrade, not a separate machine

Universal Creation already owns the creation goal and the final artifact. A separate general design machine would duplicate planning, project creation, state, and routing.

Design Fabric instead becomes a specialist organ with one live capability surface:

`AXM-CAP-DESIGN-FABRIC`

The first version provides four linked bodies:

`Reference Lens -> Design Genome -> Composer -> Design Judge`

A fifth operation can materialize the resulting genome, plan, and judgment as a validated ordinary creation.

## 1. Reference Lens

The current Reference Lens observes **local UTF-8 source that the caller explicitly points at**. It does not fetch websites, Figma documents, external libraries, or proprietary source.

Supported source signals currently include:

- CSS custom properties;
- color literals;
- recurring lengths;
- border radii;
- font-family declarations;
- motion durations;
- media-query width breakpoints;
- material/surface signals such as shadows, blur, and gradients;
- CSS class selector frequency;
- interaction pseudo-state signals such as hover and focus;
- HTML tag frequency;
- ARIA attribute presence.

Every observed file receives a SHA-256 content receipt in the observation body. The body gets its own canonical observation digest.

### Truth boundary

This is **source observation**, not visual perception.

`.button:hover` is evidence that a selector has a hover state. It is not evidence that the selector is semantically a button, that the hover state is beautiful, or that the rendered control is accessible.

That distinction is retained explicitly in the data rather than being silently filled in.

## 2. Design Genome

The Design Genome is the canonical reusable representation:

`axm.design-genome/v0.1`

It contains:

- colors;
- spacing tokens;
- radius tokens;
- typography tokens;
- custom design tokens;
- layout breakpoints and principles;
- component descriptions;
- semantic component roles;
- component tags;
- interactive states;
- motion durations and easing tokens;
- reduced-motion strategy;
- material/surface signals and principles;
- explicit quality gates;
- provenance.

The genome is deliberately not tied to Figma, React, HTML, Three.js, one AI model, or one renderer. Those can become adapters around the canonical representation.

### Derived genomes do not pretend to know more than the reference lens saw

When v0.1 derives a genome from local source:

- source colors may become reusable observed color tokens;
- source breakpoints may become reusable layout signals;
- class selectors may become **component candidates**;
- pseudo-states may become observed component-state signals;
- semantic component roles remain empty unless another explicit source supplies them;
- reduced-motion strategy remains `unknown` unless supplied;
- visual quality remains unobserved.

AXM's own design-quality policy is marked separately as:

`AXM_DESIGN_FABRIC_DEFAULT_NOT_REFERENCE_DERIVED`

This prevents a reference design from silently becoming the authority for AXM's accessibility or quality floor.

## 3. Composer

The Composer binds a genome to an explicit design request.

Current requests can declare:

- creation goal;
- required semantic component roles;
- exact component ids;
- target viewports;
- exact foreground/background color-token pairs to test.

Selection is deterministic. A role is fulfilled only by a component that explicitly declares that role. There is no hidden semantic guesser in this generation.

The composition rule is:

> Reuse grammar and component semantics. Do not copy a reference page composition by default.

This lets a professional reference contribute spacing rhythm, color/material language, motion signals, states, and component knowledge without requiring AXM to reproduce the original page layout.

## 4. Design Judge

The first Design Judge is intentionally narrow and testable. It currently produces gates for:

- requested role/component coverage;
- focus-state evidence on selected interactive components;
- responsive breakpoint evidence when several viewports are requested;
- reduced-motion strategy;
- explicit text-contrast pairs.

Opaque hexadecimal color pairs use the WCAG relative-luminance contrast formula. Alpha colors are not silently treated as opaque.

A gate can be:

- `PASS` when the required evidence is present and satisfies the rule;
- `FAIL` when evidence proves the rule is violated;
- `HOLD` when the required evidence has not actually been observed.

The whole judgment only reports `PASS` when every current gate passes.

### A structural PASS is not an aesthetic claim

v0.1 still marks these as unobserved:

- rendered visual hierarchy;
- screenshot similarity or originality;
- real browser interaction;
- subjective aesthetic quality;
- runtime animation smoothness.

Future browser, screenshot, Figma, image, or learned observers can supply those observations later. They should plug into the same evidence loop rather than rewriting the genome format around one provider.

## 5. Materialization

A complete genome + request can be materialized as:

```text
design-output/
├── design.genome.json
├── design.plan.json
└── design.judgment.json
```

The three files are published through the existing deterministic project builder and exact file-set/JSON validation. Materialization is an ordinary creation and cannot rewrite the live machine body.

This means design state can travel with a creation as machine-readable state instead of being lost inside screenshots, prompts, or one designer's memory.

## Live operations

The live capability handles:

| Creation kind | Operation | Purpose |
| --- | --- | --- |
| `inspect-design-fabric` | `inspect-schema` | Inspect current Design Fabric schemas, operations, and truth boundaries. |
| `observe-design-reference` | `observe-project` | Observe bounded local source signals. |
| `derive-design-genome` | `derive-genome` | Turn an observation into a reusable genome candidate without semantic overclaiming. |
| `validate-design-genome` | `validate-genome` | Fail closed on malformed/unsupported genome state. |
| `compose-design-plan` | `compose-plan` | Bind explicit roles, components, viewports, tokens, motion, and materials into a plan. |
| `judge-design-plan` | `judge-plan` | Produce deterministic PASS/FAIL/HOLD evidence. |
| `materialize-design-plan` | `materialize` | Publish the genome, plan, and judgment as validated descriptors. |

## Relationship to the visual stack

The intended body now looks like:

```text
Universal Creation
│
├── creation/anatomy/planning
├── Design Fabric
│   ├── Reference Lens
│   ├── Design Genome
│   ├── Composer
│   └── Design Judge
│
├── Asset Atom Fabric
│   └── reusable visual ingredients
│
├── Vector Cells / Chameleon / simulation
│   └── inspectable visual state and adaptation
│
└── Paintgun / future renderers
    └── materialized expression
```

No layer is required to pretend to be another one.

## What comes next

The useful next growth is **observer adapters**, not another design ontology.

Possible later adapters:

`browser screenshot -> observed hierarchy/layout evidence`

`Figma or open design document -> structured component/token evidence`

`image reference -> model-assisted observations with explicit model/source receipt`

`running interface -> interaction/performance/accessibility observation`

Those adapters should produce evidence that can be attached to or compared with a Design Genome. The canonical genome stays local and provider-neutral.

After that, the repair loop can become richer:

`compose -> render -> observe -> judge -> explicit gap -> repair candidate -> re-render`

That is the point where visual quality can become a real closed loop rather than a prompt adjective.
