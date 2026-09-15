# Software GLB preview

`axm_uc.software_glb_preview` renders a bounded embedded GLB to a deterministic RGB PNG with no GPU, browser, Blender, NumPy, or Pillow dependency. It samples supported GLB animation through the existing offline pose runtime, then rasterizes decoded triangles with orthographic framing, depth, backface culling, material factors, vertex colour, emissive factors, and simple two-light shading.

```bash
axm-assets software-glb-preview model.glb preview.png --yaw 0.72 --elevation 0.38
axm-assets software-glb-preview animated.glb frame.png --clip AssemblyMotion --time 0.5
```

The receipt binds the image to source bytes and reports pose, bounds, triangle counts, visible triangles, and bounded raster work. This is inspection evidence—not a claim of PBR parity, texture fidelity, target-engine import, continuous playback, artistic quality, or runtime performance.
