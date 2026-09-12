"""Reference catalog -> deterministic articulated GLBs -> transactional RTS pack.

The surface encoder remains authoritative for geometry. This bounded assembly
layer adds explicit local pivots, rigid animation and engine-neutral handoff data.
"""
from __future__ import annotations
import base64
import copy
import hashlib
import json
import io
import zipfile
import math
import struct
from pathlib import Path
from .procedural_3d import build_glb, verify_glb
from .rts_recipes import build_reference_mesh
from .rts_mesh import SalvageMesh

DATA=Path(__file__).parent/'data'

def catalog():
 return json.loads((DATA/'rts/catalog.json').read_text(encoding='utf-8'))

def unpack_glb(raw):
 if len(raw)<28 or struct.unpack_from('<4sII',raw)!=(b'glTF',2,len(raw)):raise ValueError('invalid GLB header')
 n,kind=struct.unpack_from('<II',raw,12)
 if kind!=0x4e4f534a or n%4 or 28+n>len(raw):raise ValueError('invalid GLB JSON')
 doc=json.loads(raw[20:20+n]);size,kind=struct.unpack_from('<II',raw,20+n)
 if kind!=0x004e4942 or 28+n+size!=len(raw):raise ValueError('invalid GLB binary')
 return doc,bytearray(raw[28+n:28+n+doc['buffers'][0]['byteLength']])

def pack_glb(doc,blob):
 doc=copy.deepcopy(doc);doc['buffers'][0]['byteLength']=len(blob)
 js=json.dumps(doc,sort_keys=True,separators=(',',':'),allow_nan=False).encode();js+=b' '*((-len(js))%4)
 blob=bytes(blob);blob+=b'\0'*((-len(blob))%4)
 return struct.pack('<4sII',b'glTF',2,28+len(js)+len(blob))+struct.pack('<II',len(js),0x4e4f534a)+js+struct.pack('<II',len(blob),0x004e4942)+blob

def read_accessor(doc,blob,index):
 a=doc['accessors'][index];v=doc['bufferViews'][a['bufferView']]
 width={'SCALAR':1,'VEC3':3,'VEC4':4}[a['type']];code={5126:'f',5123:'H'}[a['componentType']]
 fmt='<'+code*width;size=struct.calcsize(fmt);offset=v.get('byteOffset',0)+a.get('byteOffset',0)
 if offset+size*a['count']>v.get('byteOffset',0)+v['byteLength'] or offset+size*a['count']>len(blob):raise ValueError('accessor out of bounds')
 return [struct.unpack_from(fmt,blob,offset+i*size) for i in range(a['count'])]

def articulated_glb(f,name):
 spec=f.surface_spec(name)
 for group in spec['primitives']:
  pivot=f.pivots[group['id'].split('__')[0]]
  group['positions']=[[p[i]-pivot[i] for i in range(3)] for p in group['positions']]
 built=build_glb(spec);doc,blob=unpack_glb(built['body'])
 motion_by_clip={}
 for i,node in enumerate(doc['nodes']):
  component,mat=node['name'].split('__');node['translation']=list(f.pivots[component]);node['extras']={'component':component}
  if mat=='glow':doc['materials'][i]['emissiveFactor']=[1,.56,.14]
  if mat=='cyan':doc['materials'][i]['emissiveFactor']=[.06,.78,.84]
  motion=f.motion.get(component)
  if motion:motion_by_clip.setdefault(motion['clip'],[]).append((i,motion))
 def accessor(values,shape):
  while len(blob)%4:blob.append(0)
  offset=len(blob);width={'SCALAR':1,'VEC4':4}[shape]
  blob.extend(b''.join(struct.pack('<'+'f'*width,*v) for v in values));view=len(doc['bufferViews'])
  doc['bufferViews'].append({'buffer':0,'byteOffset':offset,'byteLength':len(blob)-offset})
  idx=len(doc['accessors']);a={'bufferView':view,'componentType':5126,'count':len(values),'type':shape}
  if shape=='SCALAR':a.update(min=[min(v[0] for v in values)],max=[max(v[0] for v in values)])
  doc['accessors'].append(a);return idx
 for clip,channels in sorted(motion_by_clip.items()):
  anim={'name':clip,'samplers':[],'channels':[]};cache={}
  for node,m in channels:
   key=json.dumps(m,sort_keys=True)
   if key not in cache:
    n=len(m['angles']);times=[(m['duration']*j/(n-1),) for j in range(n)];axis=m['axis'];le=math.sqrt(sum(v*v for v in axis))
    values=[tuple(v/le*math.sin(a/2) for v in axis)+(math.cos(a/2),) for a in m['angles']]
    sam=len(anim['samplers']);anim['samplers'].append({'input':accessor(times,'SCALAR'),'output':accessor(values,'VEC4'),'interpolation':'LINEAR'});cache[key]=sam
   anim['channels'].append({'sampler':cache[key],'target':{'node':node,'path':'rotation'}})
  doc.setdefault('animations',[]).append(anim)
 assembly={'schema':'axm.rts-rigid-assembly/v0.1','pivots':f.pivots,'motion':f.motion,'sockets':f.sockets}
 doc['extras']['axmAssembly']=assembly
 doc['extras']['axmAssemblySha256']=hashlib.sha256(json.dumps(assembly,sort_keys=True,separators=(',',':')).encode()).hexdigest()
 body=pack_glb(doc,blob);verification=verify_articulated_glb(body)
 return body,verification

def verify_articulated_glb(body):
 report=verify_glb(body);doc,blob=unpack_glb(body)
 assembly=doc['extras']['axmAssembly']
 if hashlib.sha256(json.dumps(assembly,sort_keys=True,separators=(',',':')).encode()).hexdigest()!=doc['extras']['axmAssemblySha256']:raise ValueError('assembly digest mismatch')
 bounds=[]
 for node in doc['nodes']:
  component=node['extras']['component'];pivot=assembly['pivots'][component]
  if node['translation']!=pivot or node['scale']!=[1,1,1]:raise ValueError('component bind transform mismatch')
  if any(not math.isfinite(v) for v in pivot):raise ValueError('non-finite pivot')
  p=doc['meshes'][node['mesh']]['primitives'][0]
  bounds.extend(tuple(row[i]+pivot[i] for i in range(3)) for row in read_accessor(doc,blob,p['attributes']['POSITION']))
 seen_clips=set()
 for clip in doc.get('animations',[]):
  if clip['name'] in seen_clips:raise ValueError('duplicate animation')
  seen_clips.add(clip['name']);targets=set()
  for channel in clip['channels']:
   target=channel['target'];idx=target['node']
   if type(idx)!=int or not 0<=idx<len(doc['nodes']) or target['path']!='rotation' or idx in targets:raise ValueError('invalid animation target')
   targets.add(idx);s=clip['samplers'][channel['sampler']]
   times=[t[0] for t in read_accessor(doc,blob,s['input'])];values=read_accessor(doc,blob,s['output'])
   if len(times)!=len(values) or len(times)<2 or times[0]!=0 or not all(math.isfinite(t) for t in times) or any(b<=a for a,b in zip(times,times[1:])):raise ValueError('invalid animation times')
   if any(len(q)!=4 or not all(math.isfinite(v) for v in q) or abs(sum(v*v for v in q)-1)>1e-5 for q in values):raise ValueError('invalid rotation quaternion')
   m=assembly['motion'][doc['nodes'][idx]['extras']['component']]
   if m['clip']!=clip['name'] or abs(times[-1]-m['duration'])>1e-5:raise ValueError('animation and assembly disagree')
 report.update(bounds={'min':[min(p[i] for p in bounds) for i in range(3)],'max':[max(p[i] for p in bounds) for i in range(3)]},clips=sorted(seen_clips),components=len(assembly['pivots']),animation_validation='Decoded time/quaternion/target checks; rigid articulation, no skinned deformation',animation_channels=sum(len(a['channels']) for a in doc.get('animations',[])))
 return report

def collision_contract(asset,bounds):
 family=asset['family'];id=asset['id'];lo,hi=bounds['min'],bounds['max']
 h=max(.1,hi[1]-max(0,lo[1]));w=hi[0]-lo[0];d=hi[2]-lo[2]
 boxes=[]
 def box(c,s,role='solid'):boxes.append({'shape':'box','center':c,'size':s,'role':role})
 if family=='crew':box([0,1.0,0],[.70,2.0,.65],'unit-proxy')
 elif family=='equipment':pass
 elif family=='vehicles':box([0,h*.48,0],[w*.88,h*.88,d*.80],'vehicle-proxy')
 elif id=='spike-gate':
  for x in [-1.7,1.7]:box([x,1.1,0],[.48,2,.6])
  box([0,1.1,0],[2.9,1.8,.45],'gate-closed-only')
 elif id=='regional-scrap-market-gate':
  for x in [-2.1,2.1]:box([x,1.4,0],[1.35,2.4,2])
 elif id in ['rail-checkpoint','bridge-fragment','bridge-kit']:
  if id=='rail-checkpoint':box([1.8,1.4,-.7],[1.5,2.5,1.5])
  elif id=='bridge-fragment':
   for x in [-2,2]:box([x,1.65,0],[.8,3,1.6])
 else:box([(lo[0]+hi[0])*.5,h*.5,(lo[2]+hi[2])*.5],[max(.1,w*.80),h,max(.1,d*.72)],'coarse-placement-proxy')
 return {'schema':'axm.rts-collision/v0.1','basis':'Authored coarse gameplay proxies; no automatic collider fitting or physics-engine test',
  'boxes':boxes,'navigation_polygons_xz':[[[b['center'][0]+sx*b['size'][0]/2,b['center'][2]+sz*b['size'][2]/2] for sx,sz in [(-1,-1),(1,-1),(1,1),(-1,1)]] for b in boxes],
  'conditional_roles':{'gate-closed-only':'Disable when gate is open; animation alone does not change collision'},'equipment_blocks_navigation':False}

def collision_glb(contract,name):
 f=SalvageMesh(True)
 for j,b in enumerate(contract['boxes']):f.box('collision-'+str(j),b['center'],b['size'],'signal')
 if not f.groups:return None
 return build_glb(f.surface_spec(name+'-collision'))['body']

def reference_pack_request(path,asset_ids=None):
 source=catalog();all_assets={a['id']:a for a in source['assets']}
 selected=list(all_assets) if asset_ids is None else list(asset_ids)
 if not selected or len(selected)!=len(set(selected)) or any(id not in all_assets for id in selected):raise ValueError('select unique known reference asset IDs')
 binaries={};items=[]
 def binary(name,body):
  digest=hashlib.sha256(body).hexdigest();binaries[name]={'encoding':'base64','content':base64.b64encode(body).decode(),'sha256':digest,'media_type':'model/gltf-binary'};return digest
 for id in selected:
  asset=all_assets[id];item=dict(asset);item['lods']=[]
  for lod in ('near','far'):
   f=build_reference_mesh(asset,lod);body,check=articulated_glb(f,id+'-'+lod);name=f'assets/{id}/{id}'+('-lod1' if lod=='far' else '')+'.glb'
   digest=binary(name,body);item['lods'].append({'lod':lod,'path':name,'sha256':digest,'bytes':len(body),'verification':check})
   if lod=='near':item['sockets']=f.sockets;item['collision']=collision_contract(asset,check['bounds'])
  proxy=collision_glb(item['collision'],id)
  if proxy:
   name=f'assets/{id}/{id}-collision.glb';item['collision']['path']=name;item['collision']['sha256']=binary(name,proxy)
  items.append(item)
 manifest={'schema':'axm.rts-reference-pack/v0.1','status':'CREATED','units':'meters','up':'+Y','forward':'+Z','origin':'Ground-centered authored origin; props use attachment origin',
  'references':source['references'],'overview_aliases':source['overview_aliases'],'items':items,
  'provenance':'Assistant-authored geometric interpretations of user-supplied sheets; no source pixels baked onto meshes. Hidden sides are inferred.',
  'quality_scope':'Stylized geometric first edition, not a pixel-identical reconstruction or certified final art.',
  'boundaries':{'target_game_imported':False,'browser_observed_by_generation':False,'physics_engine_tested':False,'performance_measured':False,'skinned_characters':False,'uv_textures':False},
  'sources':{n:hashlib.sha256((Path(__file__).parent/n).read_bytes()).hexdigest() for n in ['rts_mesh.py','rts_recipes.py','rts_detail.py','rts_foundry.py','data/rts/catalog.json']}}
 readme='''AXM RTS / BRIGHTER PEOPLE — Reference foundry 0.1

83 distinct designs across eight user-supplied reference sheets.
GLB 2.0, meters, Y up, Z forward. Each item has near and far authored geometry.
Material colors are linear PBR factors with vertex weathering. Lamps and meteor
seams have emissive factors; your game supplies lighting/bloom. Glass is opaque
stylized geometry. No downloaded art, image billboards, textures or UVs.

VIEW: Open index.html. Choose the exported assets folder with the folder picker
(or choose individual GLBs). Select a model and a clip. All processing is local.
No server, account, CDN, model or network is needed.

IMPORT: Load the near GLB with your engine's glTF loader. Choose the -lod1 file
for far views. LOD switching distances are a game decision. Component nodes are
named component__material; keep all nodes of a component together. Crew walk,
vehicle wheel drive, turret aim and selected mechanisms are rigid node animation
clips, not a deforming human skeleton or a full animation set. No root motion.
See manifest.json for every asset, bounds, sockets, clip names and collider proxy.
The separate collision GLB is for physics import only: do not render it. Equipment
has mount sockets and intentionally no navigation obstacle. Most building
colliders are coarse placement proxies, not interiors. Gate collision must be
switched by the game, independently of its open animation. Bridge traversal and
terrain placement require game logic. Resources, health, attacks and pathfinding
remain owned by your RTS. Files have not been installed or tested in that RTS.

REBUILD: PYTHONPATH=src python -m axm_uc rts-reference-pack OUTPUT
Optional: --asset crew-worker --asset bathtub-turret
The output directory must not already exist. The standard transactional mixed
project publisher protects existing projects. catalog.json records all references
and repeated-sheet aliases. Inferred backs/interiors are authored interpretations.
This first edition does not reproduce all fine reference details or sign lettering.
'''
 page=(DATA/'rts/viewer.html').read_text(encoding='utf-8')
 text_files={'index.html':page,'manifest.json':json.dumps(manifest,indent=2),'catalog.json':json.dumps(source,indent=2),'README.txt':readme}
 total=sum(len(base64.b64decode(v['content'])) for v in binaries.values())+sum(len(v.encode()) for v in text_files.values())
 if total>50*1024*1024:
  # A large asset library is a compressed handoff, not an increase to the
  # generic project's publication ceiling. Every GLB was validated above.
  if total>256*1024*1024:raise ValueError('reference archive exceeds 256 MiB unpacked bound')
  stream=io.BytesIO()
  with zipfile.ZipFile(stream,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
   files={n:v.encode() for n,v in text_files.items()}
   files.update({n:base64.b64decode(v['content']) for n,v in binaries.items()})
   for n,body in sorted(files.items()):
    info=zipfile.ZipInfo(n,(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o644<<16;archive.writestr(info,body)
  body=stream.getvalue()
  if len(body)>16*1024*1024:raise ValueError('compressed pack exceeds per-file bound; select a smaller asset subset')
  binaries={'rts-brighter-people-assets.zip':{'encoding':'base64','content':base64.b64encode(body).decode(),'sha256':hashlib.sha256(body).hexdigest(),'media_type':'application/zip'}}
  text_files={'index.html':'<!doctype html><html lang="en"><meta charset="utf-8"><title>AXM RTS 3D assets</title><h1>Brighter People / 83-design foundry</h1><p>Download and extract the asset pack, then open its index.html for the offline model viewer.</p><a href="rts-brighter-people-assets.zip" download>Download the 3D asset pack</a></html>',
   'manifest.json':json.dumps({'schema':'axm.rts-archive-handoff/v0.1','archive':'rts-brighter-people-assets.zip','sha256':hashlib.sha256(body).hexdigest(),'unpacked_bytes':total,'files':len(files),'assets':len(items),'validated_visual_glbs':2*len(items),'contents_manifest':'manifest.json inside archive'},indent=2),
   'README.txt':'Extract rts-brighter-people-assets.zip first. It contains all GLBs, colliders, catalog, manifest and offline viewer.\n'+readme}
 return {'kind':'mixed-media-project','direction':'Build reusable 3D RTS interpretations of the complete survivor reference catalog',
 'inputs':{'path':str(path),'project_type':'static-web','binary_files':binaries,'text_files':text_files,'checks':[{'type':'file-exists','path':n} for n in ['index.html','manifest.json',*binaries]]}}
