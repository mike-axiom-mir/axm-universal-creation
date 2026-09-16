# AXM Native Visual Engine

Universal Creation now has two complementary visual execution paths rather than forcing every visual task through Blender.

## 1. Blender forge — authoring and final proof

`tools/blender/axm_blender_pro.py` is an additive shared helper layer for the existing `bpy` forge scripts. It centralizes:

- preview, lookdev, hero, and proof render profiles;
- deterministic Cycles seed and bounce settings;
- AgX color management;
- reusable world setup;
- aimed cameras;
- a reusable three-point area-light rig;
- Principled PBR material creation;
- structural pre-render scene validation;
- deterministic proof-angle generation and truth-bounded receipts;
- an `apply_native_scene(...)` bridge that realizes the native scene contract in Blender.

It does **not** claim visual quality from structure alone. Rendered review remains required.

## 2. Native visual engine — fast coded visuals

`src/axm_uc/native_visual_engine.py` compiles a small inspectable scene contract into a self-contained WebGL2 page. It has no external JavaScript dependencies and can be opened locally after generation.

Current runtime features:

- scene graph with boxes, spheres, cylinders, and planes;
- position, rotation, scale, visibility;
- PBR-inspired base color / metallic / roughness / emissive materials;
- ambient, directional, and point lights;
- perspective camera;
- mouse/touch orbit and wheel zoom;
- spin, bob, and orbit procedural animation;
- tone mapping, fog, depth testing, back-face culling;
- deterministic scene hashing and build receipts;
- explicit truth boundary: this is a real-time preview/runtime, not a replacement for Blender final asset authoring.

## Run the native demo

```bash
axm-native-visual --demo --output out/native-visual-demo
```

Then open `out/native-visual-demo/index.html` in a WebGL2-capable browser.

For a custom scene:

```bash
axm-native-visual --scene my-scene.json --output out/my-scene
```

## Machine routing

The runtime is also registered as live capability `AXM-CAP-NATIVE-VISUAL-RUNTIME`, so Universal Creation can route creation kinds such as `native-visual-scene`, `native-visual-runtime`, `coded-visual-scene`, and `webgl-visual-preview` through its normal capability store. Supported operations are `inspect`, `compile`, `bundle`, and `demo`.

This is deliberately path-explicit and refuses to write into the protected live machine body. Non-empty output directories require explicit `replace=true`.

## Why both matter

The native runtime gives the Machine a cheap, fast visual scratchpad for composition, lighting, material direction, motion, and camera iteration. Blender remains the deeper authoring and export path for high-detail geometry, textures, rigs, GLB, and artifact-bound proof. The included native-to-Blender bridge maps that same scene contract into `bpy`, so a fast preview can graduate into deeper authoring without silently rebuilding its camera, transforms, basic materials, or light layout.

The bridge claims shared state, **not pixel parity**. WebGL and Blender remain different renderers, and final visual acceptance still requires rendered evidence.
