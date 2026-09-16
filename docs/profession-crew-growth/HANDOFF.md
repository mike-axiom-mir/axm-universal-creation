# UC profession crew growth lane

User request: bring suitable Profession Fabric specialists and workflows into UC,
with deterministic learning/growth like the space-adventure crew, then conduct
eight hourly UC improvement activations. Preserve the existing machine and roots.

Repository: `mike-axiom-mir/axm-universal-creation`
Working branch: `chatgpt/profession-crew-growth`
One chat/task lane: retain this branch and one active PR; do not scatter duplicate
lanes. Initial PR #143 merged while manual cycle 001 was in progress. A merged
PR cannot receive a new diff, so cycle 001 needs a successor PR on this branch.

## Current execution status

The requested hourly task was **not created**: the scheduler reported all 20
active task slots occupied. No existing task was paused or replaced. Mike then
requested one cycle now. RUN_001.md records that manual cycle; no autonomous
continuation is active and no eight-cycle completion is claimed.

Manual cycle 001 connects the existing static GLB target evidence gate to live
capability routing and professional stations. Job requirements are separate from
the submitted packet. Missing evidence names its owning profession. Packets are
validated, not independently reproduced, and never grant crew practice.

## Initial implementation

- 18 pinned original professional bodies/workflow data, bundled offline.
- Source: Profession Fabric `941bd05007eb5cd88e773e66c858c62cf9de38a9`.
- Simulator pattern inspected at `dd3b2b6d773151573a2b305a4858ea7f87408f78`;
  no simulator reward/promotion/ledger code transplanted.
- `profession-crew` / `profession-workflow` live capability.
- Job planning uses the existing stepwise contract validator.
- Existing specialist tournament accepts `profession_workflow`; professional
  contracts and practice enter actual team packets without changing old roles,
  team voting, or interpreting votes as competence.
- Automatic adapters: basic projects, verify-project, text, JSON, procedural GLB.
- Scoped persistent practice; a project failure makes the next matching project
  use preflight before writing its destination. Actual demo proves this behavior.
- Atomic crew state, OS-managed writer lock, idempotent run IDs, interrupted-job
  hold, no duplicate experience, runtime/catalog/context invalidation.

## Continue from current evidence

Read AGENTS.md, PROFESSION_CREWS.md, newest main, this lane, open PRs and latest
reports before each activation. Initial main was `49ef11ca...`; before publication
main advanced to `87f93e1a...` with a static-asset target evidence gate. That update
was fetched and neighboring tests passed; do not rebuild it. PR #141 (aftertouch)
and #140 (physics) were separate open lanes during this implementation. Recheck.

Choose one worthwhile bounded improvement based on the current gap, implement it,
run real relevant evidence, and append a concise activation record with exact
revision, changed behavior, commands, result and remaining ceilings. Do not use
unverified historical emails/claims as current repository evidence. No-change is
preferable to duplicate work. Preserve source licenses and original role status.

Priority candidates (adaptive order; these are not completion claims):

1. Completed in manual cycle 001: bind the existing target-evidence gate to a real
   GLB station, preserving packet validation versus independently executed tests.
2. Add the next useful real animation or richer asset adapter, using UC's existing
   render/motion/runtime machinery and actual artifact checks.
3. Connect with the aftertouch chamber if that lane is actually available; avoid
   duplicating its seven rounds or promoting its submitted judgments into facts.
4. Improve profession/skill fit from explicit capability needs, with representative
   mismatch and handoff tests; keep weak keyword inference visible.
5. Improve cold recovery/portable crew state using UC snapshots and explicit
   migration. Do not introduce a mandatory machine ledger or hash authority.
6. Turn observed recurring defects into bounded reusable checks or repair
   proposals; test corrected work and unseen contexts. Never silently overwrite
   accepted sources or creative intent.
7. Inspect real rendered outputs for quality claims. Source/GLB tests alone cannot
   certify visuals, motion, material quality, gameplay or professional mastery.
8. Integrate, retest and summarize achieved changes and the next genuine gap.

Do not spawn subagents unless explicitly authorized by the active instructions.
The requested specialists are machinery inside UC; role cards are not claims that
ChatGPT agents ran. Publish code/evidence in this lane with the connected GitHub
API; browser sign-in is unnecessary. Do not merge unrelated PRs or quietly change
canon. Report any access/test blocker exactly. Maintain concise user updates.

## Verification commands

```sh
PYTHONPATH=src:tests python -m unittest test_profession_crew test_profession_target_evidence test_stepwise_workflow test_specialist_tournament test_machine test_procedural_3d test_static_asset_target_evidence -q
python tools/profession_crew_demo.py
git diff --check
```

Initial local environment: Python 3.12.14 on Linux. Initial final selected suite:
61 tests passed. A wheel built and cold-imported all 18 bundled professions.
Initial PR #143's Python 3.11/3.13 crew CI passed before its merge. Manual cycle
001 passed 77 selected tests locally; its own remote checks must be read fresh.
The full UC suite, Windows, actual rendered quality, live gameplay, animation,
audio and autonomous cognitive specialists were not verified by this lane.

Do not infer future execution from this handoff. There is no active schedule for
this lane. Stop after the requested manual cycle unless Mike requests more.
