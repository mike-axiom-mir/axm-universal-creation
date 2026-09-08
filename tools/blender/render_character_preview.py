"""Render motion from the exported GLB, not from an unexported source scene."""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector

sys.path.insert(0,str(Path(__file__).resolve().parent))
from axm_oops_character import studio


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--glb",required=True)
    parser.add_argument("--output",required=True)
    parser.add_argument("--clip",default="Wave")
    parser.add_argument("--resolution",type=int,default=480)
    parser.add_argument("--samples",type=int,default=0,help="positive count renders evenly spaced review stills instead of a movie sequence")
    args=parser.parse_args(sys.argv[sys.argv.index("--")+1:])
    output=Path(args.output).resolve()
    output.mkdir(parents=True,exist_ok=False)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps=30
    bpy.ops.import_scene.gltf(filepath=str(Path(args.glb).resolve()))
    arm=next(obj for obj in bpy.context.scene.objects if obj.type=="ARMATURE")
    for bone in arm.pose.bones:
        if bone.custom_shape:
            bone.custom_shape.hide_render=True
    action=bpy.data.actions.get(args.clip)
    if action is None:
        raise ValueError(f"missing imported clip {args.clip}")
    arm.animation_data.action=action
    arm.animation_data.action_slot=action.slots[0]
    camera=studio(args.resolution)
    camera.data.ortho_scale=1.94
    camera.location=(1.50,-3.80,1.8)
    camera.rotation_euler=(Vector((0,0,.76))-camera.location).to_track_quat("-Z","Y").to_euler()
    scene=bpy.context.scene
    scene.cycles.samples=8
    # Sample every second 30-fps frame: exact 15-fps playback speed.
    first,last=action.frame_range
    frames=list(range(round(first),round(last),2))
    if args.samples:
        if args.samples<2:
            raise ValueError("--samples requires at least 2 frames")
        frames=[round(first+(last-first)*i/(args.samples-1)) for i in range(args.samples)]
    for index,frame in enumerate(frames):
        scene.frame_set(frame)
        scene.render.filepath=str(output/f"frame-{index:04d}.png")
        bpy.ops.render.render(write_still=True)
    (output/"motion-proof.json").write_text(json.dumps({
        "source_glb":str(Path(args.glb).resolve()),
        "source_sha256":hashlib.sha256(Path(args.glb).read_bytes()).hexdigest(),
        "clip":args.clip,"frames":len(frames),"fps":None if args.samples else 15,
        "sampled_source_frames":frames,
        "truth":"Rendered from a fresh import of the exported GLB animation."
    },indent=2)+"\n",encoding="utf-8")


if __name__=="__main__":
    main()
