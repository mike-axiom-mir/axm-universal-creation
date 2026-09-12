"""Independent decoded-GLB inspection and software depth-buffer previews.

Optional authoring tool requires numpy and Pillow, not needed by the foundry.
Reads exported files, including rigid animations; never substitutes reference art.
"""
import argparse
import hashlib
import json
import math
import struct
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont


def decode(path,clip=None,phase=0):
 raw=path.read_bytes();assert struct.unpack_from('<4sII',raw)==(b'glTF',2,len(raw))
 n,typ=struct.unpack_from('<II',raw,12);assert typ==0x4e4f534a
 d=json.loads(raw[20:20+n]);length,typ=struct.unpack_from('<II',raw,20+n);assert typ==0x004e4942
 blob=raw[28+n:];assert len(blob)==length
 def acc(ref):
  a=d['accessors'][ref];v=d['bufferViews'][a['bufferView']];width={'SCALAR':1,'VEC3':3,'VEC4':4}[a['type']];dt={5126:'<f4',5123:'<u2'}[a['componentType']]
  off=v.get('byteOffset',0)+a.get('byteOffset',0);size=np.dtype(dt).itemsize*a['count']*width
  assert off+size<=v.get('byteOffset',0)+v['byteLength']<=len(blob)
  a=np.frombuffer(blob,dtype=dt,count=a['count']*width,offset=off).reshape(-1,width).astype(float);assert np.isfinite(a).all();return a
 rotations={}
 if clip:
  a=next(a for a in d['animations'] if a['name']==clip)
  for ch in a['channels']:
   s=a['samplers'][ch['sampler']];ts=acc(s['input']).ravel();vs=acc(s['output']);t=phase*ts[-1];k=max(0,min(len(ts)-2,int(np.searchsorted(ts,t,side='right')-1)));f=(t-ts[k])/(ts[k+1]-ts[k]);a0=vs[k];b=vs[k+1];dot=a0@b
   if dot<0:b=-b;dot=-dot
   if dot>.9995:q=a0*(1-f)+b*f
   else:
    theta=np.arccos(min(1,dot));q=(a0*np.sin((1-f)*theta)+b*np.sin(f*theta))/np.sin(theta)
   q=q/np.linalg.norm(q);rotations[ch['target']['node']]=q
 polys=[];colors=[];emissions=[]
 for i,node in enumerate(d['nodes']):
  q=rotations.get(i,node.get('rotation',[0,0,0,1]));x,y,z,w=q
  R=np.array([[1-2*y*y-2*z*z,2*x*y-2*z*w,2*x*z+2*y*w],[2*x*y+2*z*w,1-2*x*x-2*z*z,2*y*z-2*x*w],[2*x*z-2*y*w,2*y*z+2*x*w,1-2*x*x-2*y*y]])
  for p in d['meshes'][node['mesh']]['primitives']:
   v=acc(p['attributes']['POSITION']);idx=acc(p['indices']).astype(int).ravel().reshape(-1,3);assert idx.min()>=0 and idx.max()<len(v)
   normals=acc(p['attributes']['NORMAL']);tri=v[idx];cross=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]);assert np.all(np.sum(cross*normals[idx].mean(1),axis=1)>0)
   vv=(v*np.array(node.get('scale',[1,1,1])))@R.T+np.array(node.get('translation',[0,0,0]));polys.append(vv[idx]);mat=d['materials'][p['material']]
   vc=acc(p['attributes']['COLOR_0'])[idx,:3].mean(1) if 'COLOR_0' in p['attributes'] else np.ones((len(idx),3));assert np.all((vc>=0)&(vc<=1))
   colors.append(vc*np.array(mat['pbrMetallicRoughness']['baseColorFactor'][:3]));emissions.append(np.repeat([mat.get('emissiveFactor',[0,0,0])],len(idx),axis=0))
 return np.concatenate(polys),np.concatenate(colors),np.concatenate(emissions),d


def raster(path,W=430,H=370,yaw=.6,elev=.42,clip=None,phase=0):
 tris,base,emission,d=decode(path,clip,phase)
 right=np.array([math.cos(yaw),0,-math.sin(yaw)]);up=np.array([-math.sin(yaw)*math.sin(elev),math.cos(elev),-math.cos(yaw)*math.sin(elev)]);forward=np.cross(right,up)
 proj=np.stack([tris@right,tris@up,tris@forward],axis=-1);lo=proj[:,:,:2].min((0,1));hi=proj[:,:,:2].max((0,1));scale=min((W-38)/max(.1,hi[0]-lo[0]),(H-35)/max(.1,hi[1]-lo[1]));center=(lo+hi)/2
 proj[:,:,0]=(proj[:,:,0]-center[0])*scale+W/2;proj[:,:,1]=H/2-(proj[:,:,1]-center[1])*scale
 normal=np.cross(tris[:,1]-tris[:,0],tris[:,2]-tris[:,0]);normal/=np.linalg.norm(normal,axis=1)[:,None]
 key=np.array([-.45,.9,.7]);key/=np.linalg.norm(key);rim=np.array([.8,.4,-.5]);rim/=np.linalg.norm(rim)
 shading=.30+.62*np.maximum(0,normal@key)+.20*np.maximum(0,normal@rim)
 colors=np.clip((base*shading[:,None]+emission*.45)**(1/2.2),0,1)
 image=np.zeros((H,W,3),dtype=np.uint8);image[:]=[14,31,38];depth=np.full((H,W),-np.inf)
 visible=0
 for i,(tri,color) in enumerate(zip(proj,colors)):
  if normal[i]@forward<=0:continue
  minx=max(0,int(np.floor(tri[:,0].min())));maxx=min(W-1,int(np.ceil(tri[:,0].max())));miny=max(0,int(np.floor(tri[:,1].min())));maxy=min(H-1,int(np.ceil(tri[:,1].max())))
  if minx>maxx or miny>maxy:continue
  x,y=np.meshgrid(np.arange(minx,maxx+1)+.5,np.arange(miny,maxy+1)+.5);a,b,c=tri;den=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
  if abs(den)<1e-9:continue
  u=((b[1]-c[1])*(x-c[0])+(c[0]-b[0])*(y-c[1]))/den;v=((c[1]-a[1])*(x-c[0])+(a[0]-c[0])*(y-c[1]))/den;w=1-u-v;z=u*a[2]+v*b[2]+w*c[2];dep=depth[miny:maxy+1,minx:maxx+1];mask=(u>=0)&(v>=0)&(w>=0)&(z>dep);dep[mask]=z[mask];image[miny:maxy+1,minx:maxx+1][mask]=(color*255).astype(np.uint8);visible+=int(mask.sum())
 assert visible>0,'blank model render'
 return Image.fromarray(image)


def main():
 p=argparse.ArgumentParser();p.add_argument('pack',type=Path);p.add_argument('--family');args=p.parse_args();root=args.pack
 manifest=json.loads((root/'manifest.json').read_text());pre=root/'previews';pre.mkdir(exist_ok=True)
 font='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf';F=lambda s:ImageFont.truetype(font,s)
 families=list(dict.fromkeys(a['family'] for a in manifest['items']));receipts=[]
 for family in families:
  if args.family and family!=args.family:continue
  items=[a for a in manifest['items'] if a['family']==family];cols=4;rows=math.ceil(len(items)/cols);W,H=420,380
  board=Image.new('RGB',(W*cols,H*rows+138),(14,31,38));draw=ImageDraw.Draw(board);draw.text((26,20),'AXM / '+family.upper(),font=F(29),fill='#e3d4aa');draw.text((26,66),'Actual exported 3D geometry · Brighter People / first edition',font=F(18),fill='#90b2b9')
  for j,item in enumerate(items):
   path=root/item['lods'][0]['path'];assert hashlib.sha256(path.read_bytes()).hexdigest()==item['lods'][0]['sha256']
   img=raster(path,W,H-44,elev=.23 if family=='crew' else .43);x=j%cols*W;y=103+j//cols*H;board.paste(img,(x,y));draw.text((x+16,y+H-41),item['name'],font=F(16),fill='#e5dabb')
   receipts.append({'asset':item['id'],'sha256':item['lods'][0]['sha256'],'render':'software triangle raster with backface culling and depth test'})
  board.save(pre/(family+'.png'));print('Rendered',family,len(items),flush=True)
 # Inspection filmstrip has real clip samples: no inference of browser behavior.
 if not args.family:
  for id,clip in [('crew-worker','walk'),('scrap-buggy','drive'),('bathtub-turret','aim')]:
   path=root/'assets'/id/(id+'.glb');frames=[raster(path,460,420,clip=clip,phase=j/12) for j in range(12)]
   frames[0].save(pre/(id+'-'+clip+'.gif'),save_all=True,append_images=frames[1:],duration=85,loop=0)
  (pre/'render-receipts.json').write_text(json.dumps({'scope':'Decoded mesh rasterization and animation samples, not browser or target RTS execution','items':receipts},indent=2))
if __name__=='__main__':main()
