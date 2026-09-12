"""Execute the authored workshop recipe through UC's transactional project path."""
from __future__ import annotations
import base64
import hashlib
import json
from pathlib import Path

from .procedural_3d import build_glb, verify_glb
from .survivor_workshop import workshop_spec


def workshop_request(path):
    binaries, items, previews = {}, [], []
    for lod in ("near", "far"):
        spec = workshop_spec(lod)
        built = build_glb(spec)
        verification = verify_glb(built["body"], expected_spec_digest=built["specification_sha256"])
        filename = "building-workshop-a" + ("-lod1" if lod == "far" else "") + ".glb"
        digest = hashlib.sha256(built["body"]).hexdigest()
        encoded = base64.b64encode(built["body"]).decode("ascii")
        binaries[filename] = {"encoding": "base64", "content": encoded,
                              "media_type": "model/gltf-binary", "sha256": digest}
        positions = [p for group in spec["primitives"] for p in group["positions"]]
        low = [min(p[axis] for p in positions) for axis in range(3)]
        high = [max(p[axis] for p in positions) for axis in range(3)]
        items.append({"id": "building-workshop-a", "lod": lod, "path": filename,
                      "sha256": digest, "bytes": len(built["body"]),
                      "specification_sha256": built["specification_sha256"],
                      "triangles": verification["triangles"], "material_groups": verification["materials"],
                      "bounds": {"min": low, "max": high}, "verification": verification})
        previews.append({"lod": lod, "glb": encoded, "triangles": verification["triangles"],
                         "center": [(a+b)/2 for a,b in zip(low,high)],
                         "span": max(b-a for a,b in zip(low,high)) * .65})
    root = Path(__file__).parent
    sources = {name: hashlib.sha256((root/name).read_bytes()).hexdigest() for name in
               ("surface_geometry.py", "survivor_workshop.py", "procedural_3d.py", "workshop_project.py", "data/surface_viewer.html")}
    manifest = {"schema": "axm.uc.survivor-workshop/v0.1", "status": "CREATED",
                "units": "meters", "up": "+Y", "forward": "+Z", "items": items,
                "markers": {"entrance": [0, 0, 3], "fabrication-output": [.7, 0, 1.5]},
                "recipe": {"id": "survivor-workshop", "version": "1.0.0", "source_sha256": sources,
                           "authorship": "Assistant-authored workshop v03 recipe, integrated as deterministic UC source; no downloaded artwork"},
                "appearance": "Scalar metallic/roughness materials multiplied by linear vertex weather colors",
                "boundaries": {"browser_observed_by_generation": False, "target_game_imported": False,
                               "collision_generated": False, "textures_or_uvs_generated": False,
                               "animation_generated": False, "performance_measured": False}}
    page = (root/"data/surface_viewer.html").read_text().replace("__ASSET_DATA__", json.dumps(previews, separators=(",", ":")))
    return {"kind": "mixed-media-project", "direction": "Build the authored survivor workshop with verified surface geometry",
            "inputs": {"path": str(path), "project_type": "static-web", "binary_files": binaries,
                       "text_files": {"index.html": page, "manifest.json": json.dumps(manifest, indent=2),
                                      "README.txt": "Open index.html to inspect both exported GLBs offline. Drag or use arrow keys to orbit; scroll or use +/- to zoom.\nRegenerate with: PYTHONPATH=src python -m axm_uc survivor-workshop OUTPUT\nThe geometry and material colors are authored, deterministic UC source. Bounds include canopy and ropes. Markers are metadata, not collision. No game installation, texture UVs, animation, automatic artistic judgment or measured device budget is implied.\n"},
                       "checks": [{"type": "file-exists", "path": name} for name in (*binaries, "manifest.json", "index.html")]}}
