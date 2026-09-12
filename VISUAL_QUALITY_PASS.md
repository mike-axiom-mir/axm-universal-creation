# Visual quality pass — 2026-09-12

The earlier arena and independent-composition page demonstrated mechanisms, but
the user's visual-quality criticism was warranted. This pass changes actual
rendered detail. Passing source checks is not itself evidence of visual quality.

## Reusable arena realization

`browser_arena_visuals.py` is emitted by the existing browser-game capability
(version 0.2.0), with no third-party runtime. It adds projected, depth-sorted
geometry; a raised deck; mechanical enemies and player; a multi-level relay;
material texture from the existing `visual_surface.surface_rows` implementation;
contact shadows; light cues; recoil; and capped, short-lived impact particles.

The canonical game JSON and world-plane rules remain authoritative. Picking
inverts the camera transform at the projectile plane. Backing-pixel resolution
is capped at 2x and does not change world bounds. Reduced-motion preference
suppresses particles and relay pulsing. Decoration adds no collision walls;
lighting is stylized, not a physical simulation. These are reusable renderer
improvements, not newly invented live organs or unrestricted game synthesis.

Reproduce Signal Keep with the request in `examples/requests/create_signal_keep.json`.
This revision uses seven enemies and revised explicit damage/health/ammunition
values. Earlier three-enemy observations in BROWSER_ARENA_USE_LOOP.md describe
the previous version; the private site's comparison route preserves that version.

## Afterlight reference

`examples/browser/lantern` is assistant-authored SVG/CSS/JavaScript: brass shading,
glass reflections, a filament, illumination layers and an intensity control.
Power controls real displayed emission and the dimmer; reduced-motion preference
removes transition/breathing animation. No images, network calls or dependencies
are required. Build through the machine's existing static-project path:

```
python tools/build_afterlight_reference.py creations/afterlight-NEW
```

The driver creates and independently verifies the supplied source exactly. It
explicitly does not claim machine invention or installation of reactive-light.
The prior autonomous-composition experiment and its receipt remain unchanged.
The site adds separate navigation links around the generated/reference content.

## Evidence and limits

- Final full build: 453 tests passed, BUILD_OK (27.369 seconds).
- Focused generated-game suite: 6 tests passed, including Node execution with
  DOM/canvas doubles. Added projection round-trip, elevated picking, 2x backing
  resolution, bounded particles and reset assertions; existing pause-state
  equality also includes animation time and particles.
- Actual Chrome: inspected the rendered textured arena, relay, vehicles and
  silhouettes. Start/fire worked; ammo changed 18 to 17; selected Breaker health
  changed 150 to 120. Repeated screenshots showed moving enemies.
- Actual Chrome: inspected Afterlight unlit and lit; power label, pressed state,
  visible filament/glass/pool and enabled dimmer changed together. Keyboard End
  changed intensity output to 100%; extinguishing disabled the dimmer again.
- No mobile-hardware, audio, sustained performance or complete browser round
  certification. Native browser resizing was not available in this session;
  responsive CSS is implemented but mobile appearance is not browser-verified.
- The renderer and reference improve appearance within narrow authored designs.
  They do not establish independent art direction or universal visual quality.

Truth separates authored design, machine assembly and observed behavior. Agency
keeps start/resume/light controls explicit. Continuity retains canonical game
state and earlier outputs. Wisdom before speed leaves untested claims open and
keeps the change in this chat's existing branch/PR lane.

## Input repair after user play — 2026-09-12

The user reported movement/firing difficulty. Source inspection confirmed that
keyboard input was ignored after focus moved onto another game button, the Fire
button did not suppress touch panning, and movement controls were hidden on wide
viewports. The prior visual evidence did not establish complete playability.

Version 0.2.1 accepts gameplay keys after button focus while preserving native
Space/Enter activation and editable fields. Quick Space taps shoot immediately;
held fire still observes cooldown. Touch movement has a separate input set so
releasing one source cannot cancel a keyboard hold. Game buttons disable touch
panning. Start, firing and movement are grouped above the arena at all widths;
ready/paused movement is explicitly disabled with a Start instruction.

Final full build: 453 tests pass (25.372 seconds), BUILD_OK. New runtime checks
exercise focused-button movement, text-entry isolation, simultaneous touch-state
movement/fire, separate input release and between-frame Space taps. Chrome held
on-screen movement visibly moved the vehicle; firing reduced ammunition. This
cloud mouse-pointer test does not establish Android multi-touch behavior; actual
phone confirmation remains open.

## Reusable rendering efficiency — 2026-09-12

Version 0.2.2 caches the opaque static scenery layer before any units, effects or
HUD are drawn. A later texture load invalidates the cache; reset reuses scenery
without preserving moving objects. Cache allocation failure falls back to direct
drawing once, without repeated allocation attempts. The disposable buffer is
outside game state and cannot modify the specification or simulation. Its maximum
backing size follows the existing viewport and 2x DPR limits: 3840×2160 pixels
(about 31.6 MiB for RGBA pixel storage, excluding browser overhead).

The prior visual pass hardcoded player/tower material paint. Material shades now
derive from each creation's supplied colors, preserving alpha. Geometry, lighting
cues and gameplay rules remain the same.

Evidence: final full build 453 tests passed, BUILD_OK (23.586 seconds). The Node
fixture measures 2,335 Canvas method calls for an uncached static deck versus one
image draw on reuse. This is a command-count reduction, not a browser FPS result.
Additional checks cover delayed texture arrival, cache reuse across reset,
canonical-state equality, alpha preservation, and allocation-failure fallback.
Chrome screenshots showed the textured deck, canonical teal tower paint, movement
and firing without visible stale-unit trails. Reset returned ready with 18/18
ammo and the original target. Larger RTS/tycoon workloads, physical phones and
sustained frame pacing remain unmeasured.
