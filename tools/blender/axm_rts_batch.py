"""Offline batch surface/edge finishing of the complete RTS recipe catalog.

Preserves the original node transforms, animation accessors and assembly data.
This is a shared finishing pass, not 82 bespoke workshop rebuilds.
Run with the pinned Blender Python runtime; no service or network is used.
"""
import argparse
import copy
import hashlib
import json
import math
import shutil
import struct
import sys
from pathlib import Path
import bpy
import bmesh
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from axm_uc.rts_mesh import PALETTE
from axm_uc.rts_foundry import catalog, unpack_glb, pack_glb, read_accessor
from axm_salvage_surfaces import write_maps

HARD={'iron','rust','tin','paint','signal','ivory','red'}
KINDS={'canvas':'cloth','cloth':'cloth','darkcloth':'cloth','wood':'wood',
       'rubber':'rubber','concrete':'stone','soil':'soil','tin':'steel',
       'skin':'cloth','leaf':'cloth','leaflight':'cloth','glass':'steel'}


def append_view(doc,blob,data):
    blob.extend(b'\0'*((-len(blob))%4));offset=len(blob);blob.extend(data)
    doc.setdefault('bufferViews',[]).append({'buffer':0,'byteOffset':offset,'byteLength':len(data)})
    return len(doc['bufferViews'])-1


def array(doc,blob,values,shape,integer=False):
    a=np.asarray(values,dtype='<u4' if integer else '<f4')
    view=append_view(doc,blob,a.tobytes())
    entry={'bufferView':view,'componentType':5125 if integer else 5126,'count':len(a),'type':shape}
    if shape=='VEC3':entry.update(min=a.min(0).tolist(),max=a.max(0).tolist())
    doc['accessors'].append(entry);return len(doc['accessors'])-1


def texture(doc,blob,path):
    view=append_view(doc,blob,path.read_bytes())
    doc.setdefault('images',[]).append({'bufferView':view,'mimeType':'image/png','name':path.stem})
    doc.setdefault('textures',[]).append({'source':len(doc['images'])-1})
    return {'index':len(doc['textures'])-1}


def palette(directory):
    result={}
    for name,(color,metal,rough) in PALETTE.items():
        if name in {'glow','cyan'}:continue
        maps=write_maps(directory,name,color,KINDS.get(name,'metal'),256)
        # Single packed ORM image uses standard glTF channels: G roughness/B metal.
        r=np.array(Image.open(maps['roughness']))[:,:,0]
        m=np.array(Image.open(maps['metallic']))[:,:,0]
        if name in {'skin','leaf','leaflight'}:m[:]=0
        packed=np.stack([np.full_like(r,255),r,m],-1)
        target=directory/(name+'_orm.png');Image.fromarray(packed).save(target)
        result[name]={'basecolor':maps['basecolor'],'normal':maps['normal'],'orm':target}
    return result


def finish_geometry(positions,indices,material):
    mesh=bpy.data.meshes.new('temporary finish')
    mesh.from_pydata(positions,[],np.array(indices,dtype=int).reshape(-1,3).tolist())
    bm=bmesh.new();bm.from_mesh(mesh)
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-6)
    bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=1e-7)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    # Dissolve coplanar triangle diagonals before beveling real hard edges.
    if material in HARD:
        bmesh.ops.dissolve_limit(bm,angle_limit=.002,verts=list(bm.verts),edges=list(bm.edges),use_dissolve_boundaries=False)
        bm.normal_update()
        edges=[e for e in bm.edges if e.is_manifold and e.calc_face_angle(0)>.52]
        if edges:
            ext=np.ptp(np.asarray(positions),axis=0).max()
            bmesh.ops.bevel(bm,geom=edges,offset=min(.012,max(.001,ext*.004)),segments=2,affect='EDGES',clamp_overlap=True)
    bmesh.ops.triangulate(bm,faces=list(bm.faces));bm.normal_update()
    bad=[f for f in bm.faces if f.calc_area()<1e-11]
    if bad:bmesh.ops.delete(bm,geom=bad,context='FACES_ONLY')
    # Per-corner planar UVs prevent shared-edge projection discontinuities.
    pos=[];norm=[];uv=[]
    for f in bm.faces:
        coords=[np.array(v.co,dtype=float) for v in f.verts]
        normal=np.cross(coords[1]-coords[0],coords[2]-coords[0]);length=np.linalg.norm(normal)
        if length<1e-10:continue
        normal=tuple(normal/length);axis=max(range(3),key=lambda j:abs(normal[j]));axes=((1,2),(0,2),(0,1))[axis]
        for v in f.verts:
            p=tuple(v.co);pos.append(p);norm.append(normal);uv.append((p[axes[0]]*.9,p[axes[1]]*.9))
    bm.free();bpy.data.meshes.remove(mesh)
    if not pos:raise ValueError('Finishing removed all geometry')
    return pos,norm,uv,list(range(len(pos)))


def finish(source,target,maps):
    doc,blob=unpack_glb(source.read_bytes());old=copy.deepcopy(doc);original=bytes(blob)
    material_ids={};materials=[];triangles=0
    for mesh in doc['meshes']:
        for prim in mesh['primitives']:
            oldmat=old['materials'][prim['material']]['name']
            key=oldmat.split('__')[-1].removesuffix('-material')
            if key not in PALETTE:raise ValueError('Unknown material '+key)
            if key not in material_ids:
                material_ids[key]=len(materials)
                if key in maps:
                    t=maps[key]
                    mat={'name':'AXM '+key,'doubleSided':True,'pbrMetallicRoughness':{'baseColorFactor':[1,1,1,1],'baseColorTexture':texture(doc,blob,t['basecolor']),'metallicRoughnessTexture':texture(doc,blob,t['orm']),'metallicFactor':1,'roughnessFactor':1},'normalTexture':dict(texture(doc,blob,t['normal']),scale=.25)}
                else:
                    mat=copy.deepcopy(old['materials'][prim['material']]);mat['name']='AXM '+key
                materials.append(mat)
            a=prim['attributes'];v=read_accessor(old,original,a['POSITION']);idx=[i[0] for i in read_accessor(old,original,prim['indices'])]
            p,n,uv,ix=finish_geometry(v,idx,key)
            prim['attributes']={'POSITION':array(doc,blob,p,'VEC3'),'NORMAL':array(doc,blob,n,'VEC3'),'TEXCOORD_0':array(doc,blob,uv,'VEC2')}
            prim['indices']=array(doc,blob,ix,'SCALAR',True);prim['material']=material_ids[key];triangles+=len(ix)//3
    doc['materials']=materials
    doc.setdefault('extras',{})['axmBatchFinish']={'version':1,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'scope':'Shared PBR maps, projected UVs, hard-edge bevels. Original authored recipe, rigid animation and node placement retained.'}
    # Original bytes and accessors stay intact, including every animation sample.
    assert doc.get('animations')==old.get('animations') and doc['nodes']==old['nodes']
    assert blob[:len(original)]==original
    target.write_bytes(pack_glb(doc,blob))
    return {'triangles':triangles,'materials':len(materials),'images':len(doc.get('images',[])),
            'animations':[a.get('name') for a in doc.get('animations',[])],
            'animation_source_bytes_preserved':True,'bytes':target.stat().st_size,
            'sha256':hashlib.sha256(target.read_bytes()).hexdigest()}


def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--workshop',type=Path,required=True);p.add_argument('--only',nargs='*');args=p.parse_args()
    if args.output.exists():raise SystemExit('Refusing to overwrite batch')
    assets=catalog()['assets'];selected=[a for a in assets if not args.only or a['id'] in args.only]
    if args.only and set(args.only)!={a['id'] for a in selected}:raise SystemExit('Unknown asset ID')
    # Preflight before creating destination or producing a partial batch.
    for a in selected:
        if a['id']=='improvised-workshop':continue
        for suffix in ['', '-lod1']:
            if not (args.source/'assets'/a['id']/(a['id']+suffix+'.glb')).is_file():raise SystemExit('Missing source '+a['id']+suffix)
    args.output.mkdir(parents=True);maps=palette(args.output/'shared-texture-source');report={}
    for i,a in enumerate(selected):
        key=a['id'];out=args.output/'assets'/key;out.mkdir(parents=True)
        print(f'ASSET {i+1}/{len(selected)} {key}',flush=True)
        if key=='improvised-workshop':
            for f in args.workshop.iterdir():
                if f.is_file() and f.suffix in {'.glb','.blend','.json'}:shutil.copyfile(f,out/f.name)
            report[key]={'family':a['family'],'quality_route':'accepted authored workshop','source':'PR48'};continue
        item={'family':a['family'],'quality_route':'shared recipe finishing','files':{}}
        for suffix in ['', '-lod1']:
            name=key+suffix+'.glb';item['files'][name]=finish(args.source/'assets'/key/name,out/name,maps)
        col=args.source/'assets'/key/(key+'-collision.glb')
        if col.exists():shutil.copyfile(col,out/col.name);item['collision']='Original coarse collider retained; bevel stays within original envelope.'
        report[key]=item
        (args.output/'batch-progress.json').write_text(json.dumps(report,indent=2)+'\n')
    shutil.copyfile(ROOT/'src/axm_uc/data/rts/catalog.json',args.output/'catalog.json')
    manifest={'schema':'axm.rts-batch-finish/v1','complete':len(report)==len(assets),'asset_count':len(report),'assets':report,
              'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'scope':'Shared recipe finishing for remaining assets; workshop remains separately authored. Not equal bespoke detail, exact reconstruction, target engine or FPS certification.'}
    (args.output/'batch-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('BATCH COMPLETE',len(report),flush=True)

if __name__=='__main__':main()
