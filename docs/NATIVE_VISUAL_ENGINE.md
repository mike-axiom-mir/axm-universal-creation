# AXM Native Visual Engine

Universal Creation now separates two things that must not be confused:

1. **AXM-native visual capability** — code owned and executed by AXM without requiring Blender, Godot, Unreal, Krita, GIMP, FFmpeg, or another creative application.
2. **External visual connectors** — optional third-party executables AXM may use when they are installed and explicitly selected.

`native` means the capability still exists when every external connector is absent.

## AXM-native visual runtime

`src/axm_uc/native_visual_engine.py` compiles an inspectable scene contract into a self-contained WebGL2 page. It has no external JavaScript dependency and does not require Blender.

Current runtime features:

- scene graph with boxes, spheres, cylinders, and planes;
- position, rotation, scale, visibility;
- PBR-inspired base color / metallic / roughness / emissive materials;
- ambient, directional, and point lights;
- perspective camera;
- mouse/touch orbit and wheel zoom;
- spin, bob, and orbit procedural animation;
- tone mapping, fog, depth testing, back-face culling;
- deterministic scene hashing and build receipts.

This is real AXM-native code, but it is still an early renderer. It does **not** currently equal the geometry, rigging, simulation, texture, animation, or rendering breadth of mature external creative applications. That missing breadth is a native AXM growth target, not a reason to relabel an external dependency as native.

## Optional external connector boundary

`src/axm_uc/external_visual_tools.py` exposes a truth-labeled connector bus for installed third-party tools:

- Blender
- Godot
- Unreal Engine
- Krita
- GIMP
- ImageMagick
- FFmpeg
- OpenSCAD
- Houdini
- Inkscape

Every connector reports `native=false` and `dependency_class=EXTERNAL_OPTIONAL`. The bus can catalog connectors, inspect PATH availability, run conservative probes where declared, and execute an explicitly selected tool when `allow_execute=true` is supplied.

External execution:

- performs no automatic download or installation;
- never uses a command shell;
- records the resolved executable and argv;
- records return code plus stdout/stderr digests;
- does not treat successful process execution as proof that rendered pixels are visually correct;
- cannot use the protected live Machine body as its execution working directory through the Machine adapter.

The live Machine capability is `AXM-CAP-EXTERNAL-VISUAL-TOOLS`.

## Blender-backed code is external

The existing `tools/blender/...` scripts and `tools/blender/axm_blender_pro.py` remain useful code, but their execution requires Blender/`bpy`. They are therefore **Blender-backed external tooling**, not an AXM-native Blender implementation.

The native scene-to-Blender bridge can preserve shared scene intent when Blender is available. That is an optional conversion path; it does not define the native runtime and does not claim pixel parity.

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

The native runtime is registered as live capability `AXM-CAP-NATIVE-VISUAL-RUNTIME`, routing creation kinds such as `native-visual-scene`, `native-visual-runtime`, `coded-visual-scene`, and `webgl-visual-preview`.

The external connector bus is registered separately as `AXM-CAP-EXTERNAL-VISUAL-TOOLS`, routing `external-visual-tool`, `external-visual-connector`, `visual-tool-bus`, and `third-party-visual-tool`.

That separation is deliberate: the Machine can use external software when useful without treating it as part of AXM's native capability or making the native path disappear when a vendor tool is unavailable.
