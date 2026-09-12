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
