# Visual Use Learning v0.1

The visual forge can now improve its next structured recipe from evidence gathered when an asset is actually used.

The loop is:

`plan -> build/render -> inspect real artifact -> record exact-context lesson -> replay lesson in the next plan`

This closes the previous gap between the visual grammar's quality-loop plan and the chameleon body's reality-feedback direction.

## What is learned

`axm-assets learn-use observation.json` updates one compact current profile under `state/visual-use-profile.json`.

The profile retains:

- use counts per exact context;
- pass/fail counts for named technical and observed criteria;
- active exact-context lessons and their bounded request patches;
- evidence digests needed to reject duplicate observations.

It does not retain raw prompts, images, or a chronological activity log.

Lessons may add:

- inspection criteria;
- output constraints;
- avoid rules;
- scene defaults;
- technical requirements.

An explicit request remains authoritative. A learned scene value fills a missing field but does not overwrite an explicitly supplied field.

## Technical PNG proof

`axm-assets inspect-png asset.png` validates the PNG container and decodes 8-bit non-interlaced grayscale-alpha/RGBA scanlines to report real alpha extrema and transparent-pixel counts.

This means a painted gray-and-white checkerboard can no longer pass as transparency merely because a preview looks transparent.

## Adaptive replay

```bash
axm-assets plan-adaptive request.json --state-root .
```

The request must include `context_key`. Only lessons from that exact key are applied. One faction, renderer, camera, scale, or asset class does not silently become a universal rule.

## Truth boundary

- Technical inspection can prove the PNG facts it decodes; it cannot judge beauty, faction identity, readability, fun, or AAA quality.
- Qualitative criteria remain supplied observations with named provenance.
- A lesson changes future request composition in the same context; it does not rewrite source, install an organ, merge a branch, or grant itself global authority.
- Repeated evidence may support a later generalized capability, but generalization remains a separate explicit design change.
