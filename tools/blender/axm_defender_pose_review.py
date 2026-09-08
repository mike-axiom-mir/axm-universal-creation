"""Apply attributable glTF local transforms; inspect actual imported suit vertices."""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
import bpy
from mathutils import Quaternion,Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
import axm_fortress_defender as s


def main():
    p=argparse.ArgumentParser();p.add_argument('--asset',required=True);p.add_argument('--poses',required=True);p.add_argument('--output',required=True);p.add_argument('--render',action='store_true')
    args=p.parse_args(sys.argv[sys.argv.index('--')+1:]);asset=Path(args.asset).resolve();poses=Path(args.poses).resolve();out=Path(args.output).resolve();out.mkdir(parents=True,exist_ok=True)
    source=json.loads(poses.read_text(encoding='utf-8-sig'))
    sha=hashlib.sha256(asset.read_bytes()).hexdigest();assert sha==source['source_sha256'],'Pose data was generated against another asset'
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(asset))
    basis=Quaternion((1,0,0),math.pi/2)
    report={'asset_sha256':sha,'animation_sha256':source['animation_sha256'],'pose_file_sha256':hashlib.sha256(poses.read_bytes()).hexdigest(),'scope':'Six static poses, exact game local transforms; cross-parent hard-material triangle crossings. Excludes Flex, VisorAmber and same-segment assembly overlaps; no skin, motion sweep, first-person or containment certification.','cases':[]}
    if args.render:scene,cam,_,_=s.w.setup_scene(s.d.bounds())
    for case in source['cases']:
        for name,data in case['joint_transforms'].items():
            obj=bpy.data.objects[name];obj.location=s.xyz(data['position']);q=data['quaternion_xyzw']
            obj.rotation_mode='QUATERNION';obj.rotation_quaternion=basis@Quaternion((q[3],q[0],q[1],q[2]))@basis.inverted()
            obj.scale=(data['scale'][0],data['scale'][2],data['scale'][1])
        bpy.context.view_layer.update();b=s.d.bounds();bounds={'min':[b[0][0],b[2][0],-b[1][1]],'max':[b[0][1],b[2][1],-b[1][0]]}
        delta=max(abs(bounds[k][i]-case['body_bounds'][k][i]) for k in ('min','max') for i in range(3))
        assert delta<.00002,(case['name'],'Blender/game vertex bounds disagree',delta)
        row={'name':case['name'],'body_bounds':bounds,'game_bounds_max_delta_m':delta,'rigid_intersections':s.rigid_intersections(),'hand_errors':case['hand_errors']};report['cases'].append(row)
        print(json.dumps(row),flush=True)
        if args.render:
            aim=Vector(tuple((lo+hi)/2 for lo,hi in b));a=math.radians(40)
            cam.data.ortho_scale=2.5;cam.location=aim+Vector((math.sin(a),-math.cos(a),.34))*4;cam.rotation_euler=(aim-cam.location).to_track_quat('-Z','Y').to_euler()
            scene.render.filepath=str(out/f"runtime-{case['name']}.png");bpy.ops.render.render(write_still=True)
    (out/'runtime-pose-review.json').write_text(json.dumps(report,indent=2))


if __name__=='__main__':main()
