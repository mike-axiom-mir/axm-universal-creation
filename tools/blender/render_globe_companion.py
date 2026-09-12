"""Render the exported companion, optionally beside the existing hero."""
import argparse,json,math
from pathlib import Path
import bpy
from mathutils import Vector
from axm_hero_motion import studio
from verify_chaos_hero import action_set,find_action

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);p.add_argument('--hero',type=Path);p.add_argument('--motion',action='store_true');p.add_argument('--resolution',type=int,default=900);a=p.parse_args()
    bpy.ops.wm.read_factory_settings(use_empty=True);scene=bpy.context.scene;scene.render.fps=30
    bpy.ops.import_scene.gltf(filepath=str(a.directory/'AXM_Globe_Companion.glb'))
    arm=next(o for o in scene.objects if o.type=='ARMATURE');action_set(arm,find_action('Hover_Idle'));scene.frame_set(0)
    cam=studio(a.resolution);scene.cycles.samples=24;scene.render.use_persistent_data=True
    arm.location=(0,0,.82);target=Vector((0,0,.75));cam.location=(1.3,-4,1.5);cam.data.ortho_scale=1.14
    if a.hero:
        before=set(scene.objects);bpy.ops.import_scene.gltf(filepath=str(a.hero));hero=next(o for o in scene.objects if o not in before and o.type=='ARMATURE')
        action_set(hero,find_action('Hero_Pose'));scene.frame_set(1);arm.location=(.90,0,2.30)
        target=Vector((.25,0,1.35));cam.location=(2,-7,3);cam.data.ortho_scale=3.25
    cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
    if a.motion:
        scene.cycles.samples=8;folder=a.directory/'motion-frames';folder.mkdir(exist_ok=True)
        for i in range(24):
            f=i*30/12;scene.frame_set(int(f),subframe=f-int(f));scene.render.filepath=str(folder/f'{i:04d}.png');bpy.ops.render.render(write_still=True)
        (a.directory/'motion.json').write_text(json.dumps({'fps':12,'frames':24,'clip':'Hover_Idle','source':'Fresh exported GLB; offline rendered frames.'})+'\n')
    else:
        scene.render.filepath=str(a.directory/('together.png' if a.hero else 'companion.png'));bpy.ops.render.render(write_still=True)
