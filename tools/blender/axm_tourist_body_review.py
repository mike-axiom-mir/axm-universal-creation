"""Inspect imported Tourist against attributable final-v4 suit game poses."""
import argparse,hashlib,json,math,sys
from pathlib import Path
import bpy
from mathutils import Quaternion,Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).resolve().parent))
import axm_fortress_tourist as t

def main():
 p=argparse.ArgumentParser();p.add_argument('--defender',required=True);p.add_argument('--launcher',required=True);p.add_argument('--poses',required=True);p.add_argument('--output',required=True);p.add_argument('--source-blend');p.add_argument('--render',action='store_true');args=p.parse_args(sys.argv[sys.argv.index('--')+1:]);out=Path(args.output).resolve();out.mkdir(parents=True,exist_ok=True)
 source=json.loads(Path(args.poses).read_text());sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
 assert sha(args.defender)==source['defender_sha256'] and sha(args.launcher)==source['launcher_sha256']
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(Path(args.defender).resolve()));body=[o for o in bpy.context.scene.objects if o.type=='MESH'];joints={n:bpy.data.objects[n] for n in source['cases'][0]['joint_transforms']}
 if args.source_blend:
  with bpy.data.libraries.load(str(Path(args.source_blend).resolve())) as (src,dst):dst.objects=src.objects
  for o in dst.objects:bpy.context.collection.objects.link(o)
 else:bpy.ops.import_scene.gltf(filepath=str(Path(args.launcher).resolve()))
 weapon=[o for o in bpy.context.scene.objects if o.type=='MESH' and o not in body];root=bpy.data.objects['TouristLauncherRoot'];basis=Quaternion((1,0,0),math.pi/2)
 def apply(o,data):
  o.location=t.xyz(data['position']);q=data['quaternion_xyzw'];o.rotation_mode='QUATERNION';o.rotation_quaternion=basis@Quaternion((q[3],q[0],q[1],q[2]))@basis.inverted();o.scale=(data['scale'][0],data['scale'][2],data['scale'][1])
 def tree(o):
  return BVHTree.FromPolygons([o.matrix_world@v.co for v in o.data.vertices],[list(p.vertices) for p in o.data.polygons])
 def wrist(o):
  while o:
   if o.name in ('WristRight','WristLeft'):return True
   o=o.parent
  return False
 report={k:v for k,v in source.items() if k!='cases'};report['scope']='16 settled standing/crouching game poses, pitch -1.25 to +1.25 radians and center-aim recoil. Triangle surface crossings only, all body materials; only wrist/glove contact with Rubber grip material excluded. No continuous motion, containment, or runtime-camera certification.';report['cases']=[]
 for case in source['cases']:
  for name,trs in case['joint_transforms'].items():apply(joints[name],trs)
  apply(root,case['weapon']);bpy.context.view_layer.update();wt={o:tree(o) for o in weapon};hits=[];contacts=[]
  for o in body:
   bt=tree(o)
   for w,tr in wt.items():
    overlap=bt.overlap(tr)
    if not overlap:continue
    row={'body':o.name,'body_parent':o.parent.name,'weapon':w.name,'triangle_pairs':len(overlap)}
    if wrist(o) and w.active_material.name.split('.')[0]=='Rubber':contacts.append(row)
    else:hits.append(row)
  row={'name':case['name'],'hand_errors':case['hand_errors'],'non_grip_intersections':hits,'intended_grip_contacts':contacts};report['cases'].append(row);print(json.dumps(row),flush=True)
  if args.render and case['name'] in ('standing-pitch0-recoil0','crouch-pitch0-recoil0','standing-pitch1.25-recoil0','standing-pitch-1.25-recoil0'):
   scene,cam,center,span=t.w.setup_scene(t.d.bounds());scene.cycles.samples=24;offset=Vector((1,-1,.45))*3;cam.location=center+offset;cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler()
   q=cam.rotation_euler.to_quaternion();projected=[q.inverted()@(o.matrix_world@v.co-center) for o in body+weapon for v in o.data.vertices];lo=[min(v[i] for v in projected) for i in (0,1)];hi=[max(v[i] for v in projected) for i in (0,1)]
   cam.location+=q@Vector(((lo[0]+hi[0])/2,(lo[1]+hi[1])/2,0));cam.data.ortho_scale=max(hi[0]-lo[0],(hi[1]-lo[1])*scene.render.resolution_x/scene.render.resolution_y)*1.14
   scene.render.filepath=str(out/(case['name']+'.png'));bpy.ops.render.render(write_still=True)
 (out/'body-review.json').write_text(json.dumps(report,indent=2));assert all(not c['non_grip_intersections'] for c in report['cases']);assert max(e for c in report['cases'] for e in c['hand_errors'].values())<.001

if __name__=='__main__':main()
