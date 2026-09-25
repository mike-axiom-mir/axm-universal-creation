# Reuse simulation experience in creation

Status: proposed applications of an existing method; documentation only.
Inspected source: `08cd56220b927ff03432122c4470031597f9f697`.

[Shared method and measured neural example](https://github.com/mike-axiom-mir/axm-state-research/blob/main/docs/SIMULATION_AS_REUSABLE_EXPERIENCE.md).

UC already has three useful entry points: [paint-channel simulation](../SIMULATION_TO_REALITY.md),
[intent-directed construction search](INTENT_DIRECTED_SEARCH.md), and
[typed workflow discovery](WORKFLOW_DISCOVERY.md). Start with those contracts.
The [workflow implementation](../src/axm_uc/workflow_discovery.py) and
[simulation implementation](../src/axm_uc/simulation.py) remain their owners.

## First useful comparison

Choose a real creation request with a measurable failure, such as insufficient
texture density or a deformation bound. Freeze a small development set and
separate confirmation requests. Compare the present planner, fixed operator
ordering and seeded candidate ordering under equal execution budgets. Preserve
failed dependency closures and source-quality limits; a larger baked atlas
cannot invent source detail.

Retain the winning controls, operators, dependency graph and executable versions
in the existing caller-owned workflow memory. Rebuild in a fresh output
directory and remeasure the actual artifact. Keep preview and measured asset
bound to the same producer. Render and inspect finalists when the goal is visual.

## Neural experiment boundary

The [separate UC neural lab](https://github.com/mike-axiom-mir/axm-uc-neural/blob/a8d1e766ebed88153054392c02de0c78ae2d31e0/docs/UC_SIMULATION_LAB.md)
already learns one canvas-fitting mapping using the real fit function, with
persistent save/resume. Its three distributions are one capability. This note
does not install that adapter into this repository or establish a general
creative learner.

New capability families could expose existing geometry, material, motion or
workflow operators through bounded adapters. Compatibility and held-out benefit
must be demonstrated separately. Keep [creator parts](../AGENTS.md) as growth
memory: appearance-only variants do not count as new capability. Follow
[Self-Growth](../SELF_GROWTH.md); simulation volume is not a global growth goal.
