"""Sample current game suit/first-person solvers against imported rigid weapon geometry."""
import argparse,hashlib,json,math,sys
from pathlib import Path
import bpy
from mathutils import Quaternion,Vector
from mathutils.geometry import intersect_ray_tri
sys.path.insert(0,str(Path(__file__).resolve().parent))
import axm_fortress_dangerous_drops as t

def main():
 p=argparse.ArgumentParser();p.add_argument('--defender',required=True);p.add_argument('--launcher',required=True);p.add_argument('--poses',required=True);p.add_argument('--output',required=True);p.add_argument('--render',action='store_true');p.add_argument('--source-blend');args=p.parse_args(sys.argv[sys.argv.index('--')+1:]);out=Path(args.output).resolve();out.mkdir(parents=True,exist_ok=True)
 source=json.loads(Path(args.poses).read_text());manifest=json.loads(Path(args.launcher).with_name('manifest.json').read_text());sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();assert sha(args.defender)==source['defender_sha256'] and sha(args.launcher)==source['launcher_sha256']
 report={k:v for k,v in source.items() if k!='cases'};report['scope']='16 settled world poses plus 24 camera-space aim/reload/recoil samples, each with sampled rigid-part configurations. Triangle surface crossings, not continuous collision or containment certification. Only wrist/glove contacts with Rubber grips allowed. First-person mount uses agreed authored Sight registration, with no motion sway or revive assist.';report['cases']=[]
 basis=Quaternion((1,0,0),math.pi/2)
 def apply(o,data):
  o.location=t.xyz(data['position']);q=data['quaternion_xyzw'];o.rotation_mode='QUATERNION';o.rotation_quaternion=basis@Quaternion((q[3],q[0],q[1],q[2]))@basis.inverted();o.scale=(data['scale'][0],data['scale'][2],data['scale'][1])
 def wrist(o):
  while o:
   if o.name in ('WristRight','WristLeft'):return True
   o=o.parent
  return False
 for context in ('world','first-person'):
  bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(Path(args.defender).resolve()));body=[o for o in bpy.context.scene.objects if o.type=='MESH']
  subset=[c for c in source['cases'] if c['context']==context];joints={n:bpy.data.objects[n] for n in subset[0]['joint_transforms']}
  if context=='first-person':
   keep=set()
   for side in ('Left','Right'):
    sh=joints['Shoulder'+side];sh.parent=None;keep.add(sh);keep.update(sh.children_recursive)
   for o in list(bpy.context.scene.objects):
    if o not in keep:bpy.data.objects.remove(o,do_unlink=True)
   body=[o for o in bpy.context.scene.objects if o.type=='MESH']
  if args.source_blend:
   with bpy.data.libraries.load(str(Path(args.source_blend).resolve())) as (src,dst):dst.objects=src.objects
   for o in dst.objects:bpy.context.collection.objects.link(o)
  else:bpy.ops.import_scene.gltf(filepath=str(Path(args.launcher).resolve()))
  weapon=[o for o in bpy.context.scene.objects if o.type=='MESH' and o not in body];root=bpy.data.objects[manifest['root']]
  moving={spec['part']:(bpy.data.objects[spec['part']],spec) for spec in manifest['motions']};rests={n:(o.location.copy(),o.rotation_euler.to_quaternion()) for n,(o,spec) in moving.items()}
  configurations=[('rest',{})]
  if manifest['asset']=='roomspinner':configurations.extend((f'gimbal-{i}',{'GravityGimbal':i*math.pi/2,'ForceDial':i*math.pi/2}) for i in (1,2,3))
  else:configurations.extend((f'bay-extract-{z}',{n:z for n in moving}) for z in (.15,.60))
  for case in subset:
   for name,trs in case['joint_transforms'].items():apply(joints[name],trs)
   apply(root,case['weapon'])
   for label,values in configurations:
    for n,(o,spec) in moving.items():t.b.animate(o,spec,values.get(n,0),*rests[n])
    bpy.context.view_layer.update();wt={o:t.a.tree(o) for o in weapon};hits=[];contacts=[]
    for o in body:
     bt=t.a.tree(o)
     for obj,tr in wt.items():
      overlap=bt.overlap(tr)
      if not overlap:continue
      row={'body':o.name,'body_parent':o.parent.name,'weapon':obj.name,'triangle_pairs':len(overlap)}
      if o.parent.name.startswith('Elbow'):
       points=[]
       for ia,ib in overlap:
        pa=[o.matrix_world@o.data.vertices[i].co for i in o.data.polygons[ia].vertices];pb=[obj.matrix_world@obj.data.vertices[i].co for i in obj.data.polygons[ib].vertices]
        for edges,face in ((pa,pb),(pb,pa)):
         for k,start in enumerate(edges):
          delta=edges[(k+1)%len(edges)]-start
          for j in range(1,len(face)-1):
           hit=intersect_ray_tri(face[0],face[j],face[j+1],delta,start,True)
           if hit is not None and (hit-start).length<=delta.length+1e-7:
            v=root.matrix_world.inverted()@hit;points.append((v.x,v.z,-v.y))
       if points:row['crossing_bounds_weapon_gltf_m']=[[min(p[k] for p in points),max(p[k] for p in points)] for k in range(3)]
      (contacts if wrist(o) and obj.active_material.name.split('.')[0]=='Rubber' else hits).append(row)
    row={'name':case['name'],'context':context,'moving_configuration':label,'hand_errors':case['hand_errors'],'non_grip_intersections':hits,'intended_grip_contacts':contacts};report['cases'].append(row)
    if hits:print(json.dumps(row),flush=True)
    if args.render and label=='rest' and case['name'] in ('standing-pitch0-recoil0','crouch-pitch0-recoil0','standing-pitch1.25-recoil0','standing-pitch-1.25-recoil0','view-aim0-reload0-recoil0','view-aim1-reload0-recoil0','view-aim0-reload0.5-recoil0'):
     scene,cam,center,span=t.w.setup_scene(t.d.bounds());scene.cycles.samples=24
     if context=='first-person':
      cam.data.type='PERSP';cam.data.sensor_fit='VERTICAL';cam.data.lens=cam.data.sensor_height/(2*math.tan(math.radians(70)/2));cam.location=(0,0,0);cam.rotation_euler=Vector(t.xyz((0,0,-1))).to_track_quat('-Z','Y').to_euler()
     else:
      cam.location=center+Vector((1,-1,.45))*3;cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();q=cam.rotation_euler.to_quaternion();projected=[q.inverted()@(o.matrix_world@v.co-center) for o in body+weapon for v in o.data.vertices];lo=[min(v[i] for v in projected) for i in (0,1)];hi=[max(v[i] for v in projected) for i in (0,1)];cam.location+=q@Vector(((lo[0]+hi[0])/2,(lo[1]+hi[1])/2,0));cam.data.ortho_scale=max(hi[0]-lo[0],(hi[1]-lo[1])*scene.render.resolution_x/scene.render.resolution_y)*1.14
     scene.render.filepath=str(out/(case['name']+'.png'));bpy.ops.render.render(write_still=True)
 (out/'body-review.json').write_text(json.dumps(report,indent=2));print(json.dumps({'samples':len(report['cases']),'non_grip_hit_cases':sum(bool(c['non_grip_intersections']) for c in report['cases']),'max_hand_error_m':max(e for c in report['cases'] for e in c['hand_errors'].values())}),flush=True)
 assert all(not c['non_grip_intersections'] for c in report['cases']);assert max(e for c in report['cases'] for e in c['hand_errors'].values())<.025

if __name__=='__main__':main()
