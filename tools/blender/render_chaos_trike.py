"""Offline stills and motion from the freshly imported exported vehicle GLB."""
import argparse,json
from pathlib import Path
import bpy
from mathutils import Vector
from axm_hero_motion import studio
from verify_chaos_hero import action_set,find_action
p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);p.add_argument('--resolution',type=int,default=950);p.add_argument('--view',choices=['front','rear','motion'],default='front');a=p.parse_args()
bpy.ops.wm.read_factory_settings(use_empty=True);s=bpy.context.scene;s.render.fps=30
bpy.ops.import_scene.gltf(filepath=str(a.directory/'AXM_Chaos_Trike.glb'))
arm=next(o for o in s.objects if o.type=='ARMATURE')
action_set(arm,find_action('Drive_Cycle' if a.view=='motion' else 'Engine_Idle'));s.frame_set(0)
cam=studio(a.resolution);s.cycles.samples=20;s.render.use_persistent_data=True
cam.location=(4.5,-6.5,3.6)
if a.view=='rear':
 arm.rotation_mode='XYZ';arm.rotation_euler.z=3.141592653589793
target=Vector((0,0,1.35));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=3.65
if a.view=='motion':
 s.cycles.samples=6;folder=a.directory/'frames';folder.mkdir(exist_ok=True)
 for i in range(24):
  f=i*30/12;s.frame_set(int(f),subframe=f-int(f));s.render.filepath=str(folder/f'{i:04d}.png');bpy.ops.render.render(write_still=True)
 (a.directory/'motion.json').write_text(json.dumps({'clip':'Drive_Cycle','frames':24,'fps':12,'source':'Offline render of fresh imported GLB'})+'\n')
else:
 s.render.filepath=str(a.directory/(a.view+'.png'));bpy.ops.render.render(write_still=True)
