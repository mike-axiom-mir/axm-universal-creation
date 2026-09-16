# Source-Bound Camera / Shot Reference Template Pack

`visual.camera.core` is the reusable camera/shot foundation for games, software, cinematics and visual storytelling.

Camera presentation is not world truth. Rigs, targets, lenses, framing guides, constraints, transitions, runtime ownership and platform variants remain separate editable state.

## Surfaces

- project / shot hub
- camera rig editor
- target / framing editor
- lens / projection / FOV editor
- movement / collision / occlusion constraint editor
- camera transition editor
- runtime binding editor
- platform / accessibility variant editor
- shot comparison preview
- review / export

## Source-truth contract

- `camera-source` — exact camera/shot identity, source, version, owner/context and purpose;
- `camera-rig` — exact parent/pivot/transform/source and ownership;
- `camera-target` — exact target/anchor/source and tracking status;
- `lens-state` — exact projection, lens/FOV/aperture/focus values and source units;
- `framing-guide` — exact viewport/aspect/target guide and source;
- `camera-transition` — exact from/to states, trigger, duration/curve and ownership;
- `camera-constraint` — exact subject/rule/source/status for motion/collision/occlusion;
- `camera-runtime-binding` — exact gameplay/cinematic state to camera binding with source/authority;
- `camera-platform-variant` — exact base, deltas, platform/input/accessibility context;
- `camera-export-target` — exact rig/lens/target/transition/binding requirements.

## Truth boundary

Preview framing never moves world objects or rewrites authoritative transforms. A cinematic-looking shot does not imply gameplay camera ownership or input authority. Lens/FOV values are never inferred solely from appearance. Visual similarity does not create a target or runtime binding. Platform/accessibility variants must preserve required targeting, orientation and semantic feedback.

This pack proves deterministic structural/editability contracts only. It does not prove camera feel, motion comfort, collision behavior, target-engine parity, gameplay suitability or aesthetic quality.
