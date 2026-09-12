"""Portable satin paint and fibre surfaces at character close-up scale."""
import hashlib
from pathlib import Path
import bpy
import numpy as np
from PIL import Image
from axm_salvage_surfaces import noise,srgb


def surface(folder,name,color,kind,size=1024):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    seed=int(hashlib.sha256(name.encode()).hexdigest()[:8],16)
    broad=noise(size,seed,9);grain=noise(size,seed+1,220);fine=noise(size,seed+2,480)
    y,x=np.mgrid[0:size,0:size]/size
    rgb=srgb(color)[None,None,:]*(.94+.065*broad[...,None]+.025*grain[...,None])
    rough=np.full((size,size),.44);metal=np.zeros((size,size));height=.0009*fine
    if kind=='metal':
        # Paint remains paint; only minute chips expose conductive metal.
        chip=(.62*grain+.38*fine>.89).astype(float)
        rgb=rgb*(1-chip[...,None])+np.array([.24,.23,.21])*chip[...,None]
        rough=.38+.12*grain+.16*chip;metal=.08+.65*chip;height=.002*fine-.012*chip
    elif kind=='steel':
        brushed=.5+.5*np.sin(y*1850+grain*8)
        rgb*=.91+.10*brushed[...,None]
        rough=.30+.12*grain;metal[:]=.90;height=.0008*brushed
    elif kind=='cloth':
        weave=(np.sin(x*2500)*np.sin(y*2500))*.5+.5
        rgb*=.95+.045*weave[...,None];rough=.83+.10*grain;height=.003*weave
    elif kind=='fur':
        fibres=.5+.5*np.sin(x*2600+np.sin(y*90)*2+grain)
        rgb*=.97+.04*fibres[...,None];rough[:]=.79;height=.0015*fibres
    elif kind=='rubber':rough=.68+.12*grain;height=.0025*fine
    elif kind=='leather':
        pores=(grain<.32).astype(float);rgb*=1-.13*pores[...,None]
        rough=.58+.17*grain;height=.002*grain-.004*pores
    gy,gx=np.gradient(height);n=np.stack([-gx*size*.04,-gy*size*.04,np.ones_like(gx)],axis=-1)
    n/=np.linalg.norm(n,axis=-1)[...,None]
    orm=np.stack([np.ones_like(rough),rough,metal],axis=-1)
    paths={}
    for role,data in [('BaseColor',rgb),('ORM',orm),('Normal',n*.5+.5)]:
        path=folder/(name+'_'+role+'.png');Image.fromarray(np.uint8(np.clip(data,0,1)*255)).save(path);paths[role]=path
    mat=bpy.data.materials.new(name);mat.use_nodes=True;nodes=mat.node_tree.nodes;links=mat.node_tree.links
    bsdf=nodes.get('Principled BSDF')
    for role,path in paths.items():
        tex=nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(path));tex.image.pack()
        if role!='BaseColor':tex.image.colorspace_settings.name='Non-Color'
        if role=='BaseColor':links.new(tex.outputs['Color'],bsdf.inputs['Base Color'])
        elif role=='ORM':
            split=nodes.new('ShaderNodeSeparateColor');links.new(tex.outputs['Color'],split.inputs[0])
            links.new(split.outputs['Green'],bsdf.inputs['Roughness']);links.new(split.outputs['Blue'],bsdf.inputs['Metallic'])
        else:
            normal=nodes.new('ShaderNodeNormalMap');normal.inputs['Strength'].default_value=.32
            links.new(tex.outputs['Color'],normal.inputs['Color']);links.new(normal.outputs['Normal'],bsdf.inputs['Normal'])
    if kind=='fur':
        bsdf.inputs['Subsurface Weight'].default_value=.05
        bsdf.inputs['Sheen Weight'].default_value=.18
    return mat
