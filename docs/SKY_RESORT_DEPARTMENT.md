# Sky Resort Start — Department Lane

Scope: PR #232, branch `codex/sky-resort-start-diorama-v1`.

This department owns the opening-world miniature only: lower volcanic island, reverse-water ascent, floating sanctuary, animated water boundary, arrival portal/socket, LODs, collision, materials, animation, and durable evidence.

It does **not** own the separate hero bus, staircase, bridge/causeway, target-engine gameplay, or final world-scale implementation.

## Specialist passes

### 1. Hydrology / material specialist
Improve the `world-study` realization without pretending it is fluid simulation.

Focus:
- transparency and transmission readability;
- layered water depth;
- foam, spray, tracers and thickness variation;
- believable upward flow;
- water/island contact;
- renderer-safe overlap behavior.

Preserve the stable `prop` profile as a reversible baseline.

### 2. Sanctuary / environment detail specialist
Increase authored detail where it improves scale, function and visual life rather than polygon count alone.

Focus:
- geology and shoreline breakup;
- sanctuary architecture and believable infrastructure;
- habitation and scale cues;
- asymmetry, wear and material variation;
- portal/arrival readability.

Hard exclusions remain: no staircase, no bridge/causeway, no embedded hero bus.

### 3. Animation / export specialist
Treat animation as part of the asset contract, not disposable preview media.

Focus:
- exact loop endpoints for looping clips;
- non-zero readable motion for awakening;
- stable independent water/boundary motion;
- fresh-import GLB playback;
- LOD, skin, material and collision integrity;
- motion evidence generated from exported GLBs.

### 4. Persistence / recovery specialist
Make the branch sufficient to recover the asset without relying on a ChatGPT/Work session.

Focus:
- deterministic source scripts;
- request/manifest/parts/assembly receipts;
- reproducible GitHub build workflow;
- uploaded workflow artifacts containing editable source, GLBs, collision, renders and motion frames;
- commit/run identifiers and hashes;
- local pull/rebuild instructions.

## Department integration rule

One writer integrates the branch at a time. Every pass re-fetches the current remote head before editing. Evidence-grounded compatible improvements go into this existing branch and PR; failed, conflicting or visually weaker experiments remain HOLD/evidence rather than replacing the working result.

Do not modify `main` directly.

## Durable recovery path

A push touching this lane triggers `.github/workflows/sky-resort-start-diorama.yml`.

The workflow independently rebuilds both:
- `prop` — stable decorative realization;
- `world-study` — richer transparent/transmission water study.

For each profile it forges, verifies fresh GLB imports, inspects decoded GLB structure, renders multi-angle evidence, renders motion-proof frames, writes a GitHub build receipt, and uploads the complete generated directory as a GitHub Actions artifact.

This means the creation causes live in Git and the generated animation/evidence can be recovered from GitHub Actions even if a chat workspace disappears.

## Pull local

```bash
git fetch origin
git switch codex/sky-resort-start-diorama-v1
git pull --ff-only
```

The branch contains the deterministic creation body. Generated binaries/evidence can either be rebuilt locally with the pinned Python/Blender lane or downloaded from the matching GitHub Actions artifact.
