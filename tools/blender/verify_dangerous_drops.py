"""Independent binary GLB checks, envelope sampling and cross-asset bore contracts."""
import json,hashlib,math,sys
from pathlib import Path
import numpy as np
from axm_glb_reader import GLB

EXPECTED={
 'roomspinner':{'Grip':(0,.07,-.14),'SupportGrip':(.055,.07,.08),'Muzzle':(0,.464,.839),'Sight':(.340,.608,.367),'GravityGimbal':(0,.464,.561),'ForceDial':(.260,.462,.354)},
 'gravity-anchor':{'Contact':(0,0,0),'ForceDirection':(0,0,.1008),'SurfaceNormal':(0,.096,0)},
 'burrow-choir':{'Grip':(0,.07,-.14),'SupportGrip':(.055,.07,.08),'Muzzle':(0,.515,.898),'Sight':(.345,.637,.368),'Bay1':(-.132,.443,.620),'Bay2':(.132,.443,.620),'Bay3':(0,.662,.620),'Muzzle1':(-.132,.443,.898),'Muzzle2':(.132,.443,.898),'Muzzle3':(0,.662,.898)},
 'burrower':{'DrillRotor':(0,0,.107),'Fin1':(0,.074,-.092),'Fin2':(-.074,0,-.092),'Fin3':(0,-.074,-.092),'Fin4':(.074,0,-.092),'Nose':(0,0,.268),'Trail':(0,0,-.212)}}
ROOTS={'roomspinner':'RoomspinnerRoot','gravity-anchor':'GravityAnchorRoot','burrow-choir':'BurrowChoirRoot','burrower':'BurrowerRoot'}
out=Path(sys.argv[1]);reports={}
for name,markers in EXPECTED.items():
 folder=out/name;g=GLB(folder/(name+'.glb'));doc=g.doc;manifest=json.loads((folder/'manifest.json').read_text());root=ROOTS[name]
 assert not any(doc.get(k) for k in ('textures','images','skins','animations','cameras'));assert all('uri' not in b for b in doc['buffers']);assert doc['scenes'][doc.get('scene',0)]['nodes']==[g.names[root]];assert np.allclose(g.local(g.names[root]),np.eye(4),atol=1e-7)
 assert len(doc['materials'])<=6 and all(m.get('alphaMode','OPAQUE')=='OPAQUE' for m in doc['materials'])
 for key,pos in markers.items():
  n=doc['nodes'][g.names[key]];assert 'mesh' not in n and g.parents[g.names[key]]==g.names[root];assert np.allclose(n.get('translation',[0,0,0]),pos,atol=1e-7);assert np.allclose(n.get('rotation',[0,0,0,1]),[0,0,0,1],atol=1e-7);assert np.allclose(n.get('scale',[1,1,1]),[1,1,1],atol=1e-7)
 triangles=primitives=0
 for mesh in doc['meshes']:
  for p in mesh['primitives']:
   assert p.get('mode',4)==4;pos=g.accessor(p['attributes']['POSITION']);norm=g.accessor(p['attributes']['NORMAL']);ix=g.accessor(p['indices']).ravel();assert np.isfinite(pos).all() and np.isfinite(norm).all() and len(norm)==len(pos);assert np.allclose(np.linalg.norm(norm,axis=1),1,atol=.001);assert len(ix)%3==0 and ix.max()<len(pos);triangles+=len(ix)//3;primitives+=1
   tri=pos[ix.reshape(-1,3)];areas=np.linalg.norm(np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]),axis=1);assert np.all(areas>1e-12),(name,mesh.get('name'),int((areas<=1e-12).sum()))
 assert (triangles,primitives)==(manifest['triangles'],manifest['primitives']);assert triangles<=manifest['triangle_budget'] and primitives<=manifest['primitive_budget']
 pts=np.concatenate([p for _,p in g.points(root)]);bounds=np.column_stack((pts.min(0),pts.max(0)));assert np.allclose(bounds,manifest['bounds_gltf_xyz_m'],atol=1e-5);radial=float(np.linalg.norm(pts[:,:2],axis=1).max());assert abs(radial-manifest['max_radial_xy_m'])<1e-6
 assert all(not row['intersections'] for check in manifest['motion_checks'] for row in check['samples']);assert all(not v['forward_ray_occluded'] for v in manifest['axis_checks'].values())
 if manifest['hand_check']:
  for report in (manifest['hand_check'],manifest['imported_hand_check']):
   assert not report['obstructions']
   for side in ('Left','Right'):assert any(side in row['glove'] for row in report['grip_surface_contacts'])
  review=json.loads((folder/'body'/'body-review.json').read_text());assert review['launcher_sha256']==manifest['sha256'];assert all(not c['non_grip_intersections'] for c in review['cases']);assert max(e for c in review['cases'] for e in c['hand_errors'].values())<.025
  assert markers['Muzzle'][2]>bounds[2,1]
 if name=='gravity-anchor':assert abs(bounds[1,0])<1e-7 and radial<.079
 if name=='burrower':assert radial<.100 and markers['Nose'][2]>bounds[2,1] and markers['Trail'][2]<bounds[2,0]
 sweep=[pts];motion_rows=[]
 for spec in manifest['motions']:
  node=doc['nodes'][g.names[spec['part']]];original=json.loads(json.dumps(node));sample_points=[];axis={'local X':0,'local Y':1,'local Z':2}[spec['axis']]
  for value in spec['samples']:
   if spec['motion']=='rotation':q=[0,0,0,math.cos(value/2)];q[axis]=math.sin(value/2);node['rotation']=q
   else:tr=original.get('translation',[0,0,0]).copy();tr[axis]+=value;node['translation']=tr
   point=np.concatenate([p for _,p in g.points(root)]);sample_points.append(point)
  node.clear();node.update(original);union=np.concatenate(sample_points);sweep.append(union);motion_rows.append({'part':spec['part'],'samples':len(sample_points),'bounds_gltf_xyz_m':np.column_stack((union.min(0),union.max(0))).tolist(),'max_radial_xy_m':float(np.linalg.norm(union[:,:2],axis=1).max())})
 union=np.concatenate(sweep);sha=hashlib.sha256(g.raw).hexdigest();assert sha==manifest['sha256']
 reports[name]={'status':'PASS','sha256':sha,'blend_sha256':hashlib.sha256((folder/(name+'.blend')).read_bytes()).hexdigest(),'bytes':len(g.raw),'triangles':triangles,'primitives':primitives,'opaque_materials':len(doc['materials']),'bounds_gltf_xyz_m':bounds.tolist(),'markers':markers,'max_radial_xy_m':radial,'max_radial_xz_m':float(np.linalg.norm(pts[:,[0,2]],axis=1).max()),'sampled_motion_envelopes':motion_rows,'sampled_union_bounds_gltf_xyz_m':np.column_stack((union.min(0),union.max(0))).tolist(),'valid_unit_normals_nondegenerate_triangles':True}
(out/'verification.json').write_text(json.dumps(reports,indent=2)+'\n');print(json.dumps({k:{f:v[f] for f in ('status','triangles','primitives','opaque_materials','max_radial_xy_m')} for k,v in reports.items()},indent=2))
