"""Independent binary glTF decoder; requires NumPy."""
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


