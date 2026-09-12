"""Small visual proofs from the exported GLB, including actual moving clips."""
import argparse
import json
import math
from pathlib import Path

import bpy
from mathutils import Vector
from axm_hero_motion import studio
from verify_chaos_hero import action_set,find_action


def load(directory,resolution):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps=30
    bpy.context.scene.render.use_persistent_data=True
    bpy.ops.import_scene.gltf(filepath=str(directory/'AXM_Chaos_Hero.glb'))
    arm=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
    camera=studio(resolution);camera.location=(2.3,-7,2.75)
    camera.rotation_euler=(Vector((0,0,1.12))-camera.location).to_track_quat('-Z','Y').to_euler()
    bpy.context.scene.render.fps=30
    return arm,camera


def main():
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True)
    p.add_argument('--mode',choices=['poses','motion','hero','rear'],default='poses');p.add_argument('--resolution',type=int,default=480)
    p.add_argument('--preview-fps',type=int,default=24)
    args=p.parse_args();out=args.directory;arm,cam=load(out,args.resolution);scene=bpy.context.scene
    if not 1<=args.preview_fps<=60:raise ValueError('Preview FPS must be between 1 and 60')
    clips=json.loads((out/'character-manifest.json').read_text())['animations']
    if args.mode in {'hero','rear'}:
        action_set(arm,find_action('Hero_Pose' if args.mode=='hero' else 'Idle_Relaxed'))
        scene.frame_set(1);scene.cycles.samples=40
        if args.mode=='hero':
            cam.data.type='PERSP';cam.data.lens=70
            cam.location=(-1.7,-5.5,1.62)
            cam.rotation_euler=(Vector((0,0,1.20))-cam.location).to_track_quat('-Z','Y').to_euler()
        if args.mode=='rear':
            bpy.data.objects['PREVIEW_cyclorama'].hide_render=True
            cam.location=(-2.8,7,2.7);cam.rotation_euler=(Vector((0,0,1.12))-cam.location).to_track_quat('-Z','Y').to_euler()
        scene.render.filepath=str(out/(args.mode+'.png'));bpy.ops.render.render(write_still=True)
    elif args.mode=='poses':
        folder=out/'pose-check';folder.mkdir(exist_ok=True);scene.cycles.samples=8;cam.data.ortho_scale=3.35
        for clip in clips:
            action_set(arm,find_action(clip['name']));f=(clip['frames']-1)*(.55 if not clip['loop'] else .25)
            scene.frame_set(int(f),subframe=f-int(f));scene.render.filepath=str(folder/(clip['name']+'.png'))
            bpy.ops.render.render(write_still=True)
    else:
        folder=out/'motion-frames';folder.mkdir(exist_ok=True);scene.cycles.samples=8
        sequence=[('Hero_Pose',1.0),('Walk_Forward',1.2),('Run_Forward',.8),('Wrench_Attack',1.1),('Repair_Loop',1.2),('Wave',2.2),('Celebrate',2.4)]
        count=0;segments=[]
        for name,seconds in sequence:
            action=find_action(name);action_set(arm,action);start=count
            n=round(seconds*args.preview_fps)
            for j in range(n):
                f=action.frame_range[0]+j/max(1,n-1)*(action.frame_range[1]-action.frame_range[0])
                scene.frame_set(int(f),subframe=f-int(f));scene.render.filepath=str(folder/f'{count:04d}.png')
                bpy.ops.render.render(write_still=True);count+=1
            segments.append({'name':name,'first_frame':start,'last_frame':count-1})
        (out/'motion-sequence.json').write_text(json.dumps({'fps':args.preview_fps,'segments':segments,'source':'Freshly imported GLB; rendered sampled animation, not image generation.'},indent=2)+'\n')
    print('RENDER_COMPLETE',args.mode,flush=True)


if __name__=='__main__':main()
