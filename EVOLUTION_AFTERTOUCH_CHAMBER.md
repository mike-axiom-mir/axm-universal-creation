# Seven-Round Evolution + Deep Aftertouch Chamber

UC uses this bounded path:

`brief -> parallel creative teams -> simulate/test/observe -> diagnose -> repair -> re-test -> independently judge -> keep two -> repeat x7 -> retain two finalists with evidence`

The chamber lives in `src/axm_uc/evolution_aftertouch.py`; richer media evidence is provided by `src/axm_uc/aftertouch_media_observers.py`. The live capability is `AXM-CAP-EVOLUTION-AFTERTOUCH`.

## Fixed seven rounds

1. **Foundation** — structure, function, interfaces, feasibility.
2. **Composition** — shape, layout, hierarchy and whole-result arrangement.
3. **Detail** — secondary/tertiary construction and detail density.
4. **Experience** — actual use/play/interaction, readability and recovery.
5. **Stress** — edge cases, bad inputs, collisions, load, failure/retry and regression pressure.
6. **Creative elevation** — search beyond the obvious local optimum while preserving proven working behavior.
7. **Deep aftertouch** — structural, functional, visual, experience, context, adversarial and polish passes followed by re-test.

Every completed round keeps **exactly two** judged survivors and binds both forward as parents. No early collapse to one branch is allowed.

## Real self-observation adapters

The chamber does not treat source validity as equivalent to experienced output. `self-test-candidate` routes applicable artifacts into existing UC evidence machinery.

### 3D / GLB

For `3d`, `3d-asset`, `glb`, `game-asset`, `animated-3d` and `animated-3d-asset`, UC reuses the existing pure-Python GLB game-pose runtime. It can directly observe:

- bounded GLB validity and exact source digest;
- nodes, clips, skins, primitives and vertex counts;
- static and sampled animated world transforms;
- sampled skinned vertex positions and geometry bounds;
- real movement across sampled animation times;
- required named socket nodes and their scene-space positions;
- animation-presence requirements when requested.

That is **real 3D structural/pose evidence**, not a render. Materials, shading, engine playback, collision clearance, gameplay-distance readability, visual quality, experience and polish remain HOLD/NOT_TESTED until an applicable observer supplies those facts.

### Playable browser games

For `game`, `browser-game`, `playable-game` and `offline-browser-game`, UC first runs the normal project verifier, then can reuse the existing offline headless-browser observer. With a local Chromium-compatible executable it can directly collect:

- actual browser execution of the local game;
- real screenshot bytes and DOM/runtime artifacts;
- runtime JavaScript error counts;
- viewport overflow and other bounded runtime measurements;
- explicit focus/interaction recipes;
- optional bounded synthetic activation of visible button-like controls, only when the caller explicitly authorizes it;
- reset/recovery interaction evidence when the expected controls exist.

For UC's bounded browser arena, default recipes recognize the existing session/fire/target/reload/reset controls. Focus-only observation remains HOLD for experience; activation-authorized recipes may PASS the exact tested interaction path when no probe errors occur.

A screenshot existing is **not** an aesthetic PASS. The visual lane stays HOLD until a perceptual observer actually judges the rendered result. Runtime interaction also does not pretend to be a complete human playtest.

## Truth boundary

Missing browser executors, unsupported GLB features, unavailable interaction paths, perceptual quality and any other unobserved claim remain explicit HOLD/NOT_TESTED. The system never converts missing evidence into success.

The final evidence gate still spans structural, functional, visual, experience, context, adversarial and polish. Even an all-PASS packet means only that the declared evidence lanes passed; it is not perfection or human acceptance.

## Authority boundary

The chamber never auto-accepts a finalist, auto-merges it, auto-canonizes it, or gives winning specialists hidden authority. Both finalists stay inspectable with lineage and evidence for an explicit later choice or continuation.

## Operations

- `inspect`
- `prepare`
- `advance-round`
- `self-test-candidate`

A normal machine request routes with `kind: "creative-evolution-chamber"` or the other handles declared in the capability manifest.
