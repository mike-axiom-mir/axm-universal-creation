"""Independent binary glTF decoder and Tourist contract checks; requires NumPy."""
import hashlib,json,struct,sys
from pathlib import Path
import numpy as np

class GLB:
 def __init__(self,path):
  self.raw=path.read_bytes();magic,version,total=struct.unpack_from('<III',self.raw);assert (magic,version,total)==(0x46546c67,2,len(self.raw))
  offset=12
  while offset<len(self.raw):
   size,kind=struct.unpack_from('<II',self.raw,offset);chunk=self.raw[offset+8:offset+8+size];offset+=8+size
   if kind==0x4e4f534a:self.doc=json.loads(chunk)
   elif kind==0x004e4942:self.binary=chunk
  self.names={n['name']:i for i,n in enumerate(self.doc['nodes'])};assert len(self.names)==len(self.doc['nodes'])
  self.parents={child:i for i,n in enumerate(self.doc['nodes']) for child in n.get('children',[])}
 def accessor(self,i):
  a=self.doc['accessors'][i];v=self.doc['bufferViews'][a['bufferView']];dt={5126:'<f4',5125:'<u4',5123:'<u2',5121:'u1'}[a['componentType']];w={'SCALAR':1,'VEC3':3,'VEC2':2,'VEC4':4}[a['type']];size=np.dtype(dt).itemsize
  return np.ndarray((a['count'],w),dtype=dt,buffer=self.binary,offset=v.get('byteOffset',0)+a.get('byteOffset',0),strides=(v.get('byteStride',size*w),size)).copy()
 def local(self,i):
  n=self.doc['nodes'][i]
  if 'matrix' in n:return np.array(n['matrix']).reshape(4,4).T
  x,y,z,w=n.get('rotation',[0,0,0,1]);m=np.eye(4);m[:3,:3]=np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],[2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],[2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]])@np.diag(n.get('scale',[1,1,1]));m[:3,3]=n.get('translation',[0,0,0]);return m
 def points(self,start,skip_first=False):
  rows=[]
  def visit(i,parent,first=False):
   n=self.doc['nodes'][i];world=parent@(np.eye(4) if first and skip_first else self.local(i))
   if 'mesh' in n:
    for p in self.doc['meshes'][n['mesh']]['primitives']:
     pos=self.accessor(p['attributes']['POSITION']);points=(world@np.column_stack((pos,np.ones(len(pos)))).T).T[:,:3];rows.append((self.doc['materials'][p['material']]['name'],points))
   for child in n.get('children',[]):visit(child,world)
  visit(self.names[start],np.eye(4),True);return rows

EXPECTED={
 'tourist-launcher':('TouristLauncherRoot',8000,12,{'Grip':(0,.07,-.14),'SupportGrip':(.055,.07,.08),'Muzzle':(-.075,.460,1.261),'Sight':(.235,.590,.275),'GuidanceRing':(-.075,.460,.575)}),
 'tourist-missile':('TouristMissileRoot',2200,6,{'Camera':(0,.020,.600),'Exhaust':(0,0,-.449)})}
out=Path(sys.argv[1]);reports={}
for name,(root,tri_budget,prim_budget,markers) in EXPECTED.items():
 folder=out/name;g=GLB(folder/f'{name}.glb');doc=g.doc;manifest=json.loads((folder/'manifest.json').read_text())
 assert not any(doc.get(k) for k in ('textures','images','skins','animations','cameras'));assert all('uri' not in b for b in doc['buffers'])
 assert doc['scenes'][doc.get('scene',0)]['nodes']==[g.names[root]];assert np.allclose(g.local(g.names[root]),np.eye(4),atol=1e-7)
 assert len(doc['materials'])<=6 and all(m.get('alphaMode','OPAQUE')=='OPAQUE' for m in doc['materials'])
 for key,pos in markers.items():
  n=doc['nodes'][g.names[key]];assert 'mesh' not in n;assert g.parents[g.names[key]]==g.names[root]
  assert np.allclose(n.get('translation',[0,0,0]),pos,atol=1e-7);assert np.allclose(n.get('rotation',[0,0,0,1]),[0,0,0,1],atol=1e-7);assert np.allclose(n.get('scale',[1,1,1]),[1,1,1],atol=1e-7)
 triangles=primitives=0
 for mesh in doc['meshes']:
  for p in mesh['primitives']:
   assert p.get('mode',4)==4;pos=g.accessor(p['attributes']['POSITION']);norm=g.accessor(p['attributes']['NORMAL']);ix=g.accessor(p['indices']).ravel()
   assert np.isfinite(pos).all() and np.isfinite(norm).all() and len(norm)==len(pos);assert np.allclose(np.linalg.norm(norm,axis=1),1,atol=.001)
   assert len(ix)%3==0 and ix.max()<len(pos);triangles+=len(ix)//3;primitives+=1
   tri=pos[ix.reshape(-1,3)];areas=np.linalg.norm(np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]),axis=1);assert np.all(areas>1e-12),(name,mesh.get('name'),int((areas<=1e-12).sum()))
 assert triangles<=tri_budget and primitives<=prim_budget;assert (triangles,primitives)==(manifest['triangles'],manifest['primitives'])
 pts=np.concatenate([p for _,p in g.points(root)]);bounds=np.column_stack((pts.min(0),pts.max(0)));assert np.allclose(bounds,manifest['bounds_gltf_xyz_m'],atol=1e-5)
 assert all(not row['intersections'] for check in manifest['motion_checks'] for row in check['samples']);assert all(not v['forward_ray_occluded'] for v in manifest['axis_checks'].values())
 if name=='tourist-launcher':
  assert not manifest['hand_check']['obstructions'] and not manifest['imported_hand_check']['obstructions'];assert manifest['imported_hand_check']['grip_surface_contacts']
  assert markers['Muzzle'][2]>bounds[2,1]
 else:
  radial=float(np.linalg.norm(pts[:,:2],axis=1).max());assert radial<=.20 and bounds[2,0]>=-.45 and bounds[2,1]<=.55;assert abs(radial-manifest['max_radial_m'])<1e-6
  assert markers['Camera'][2]>bounds[2,1] and markers['Exhaust'][2]<bounds[2,0]
 sha=hashlib.sha256(g.raw).hexdigest();assert sha==manifest['sha256']
 reports[name]={'status':'PASS','sha256':sha,'blend_sha256':hashlib.sha256((folder/f'{name}.blend').read_bytes()).hexdigest(),'bytes':len(g.raw),'triangles':triangles,'primitives':primitives,'opaque_materials':len(doc['materials']),'bounds_gltf_xyz_m':bounds.tolist(),'markers':markers,'valid_unit_normals_nondegenerate_triangles':True,'max_radial_m':radial if name=='tourist-missile' else None}
(out/'verification.json').write_text(json.dumps(reports,indent=2)+'\n');print(json.dumps(reports,indent=2))
