"""Deterministic, embedded PBR surfaces for the reference workshop.

Uses original procedural pixels, not source-picture projection. Images are
explicit shader inputs so exported glTF preserves the same material machinery.
"""
import hashlib
import math
from pathlib import Path
import bpy
import numpy as np
from PIL import Image, ImageDraw, ImageFont


def srgb(hexcolor):
    a = np.array([int(hexcolor[i:i+2], 16)/255 for i in (1,3,5)])
    return a


def noise(size, seed, grid):
    rng = np.random.default_rng(seed)
    im = Image.fromarray((rng.random((grid, grid))*255).astype('uint8'))
    return np.asarray(im.resize((size, size), Image.Resampling.BICUBIC)).astype(float)/255


def write_maps(directory, name, color, kind='metal', size=1024):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    seed=int(hashlib.sha256(name.encode()).hexdigest()[:8],16)
    y,x=np.mgrid[0:size,0:size]/size
    broad=noise(size,seed,12);mid=noise(size,seed+1,64);fine=noise(size,seed+2,384)
    grain=np.random.default_rng(seed+3).random((size,size))
    base=srgb(color)[None,None,:]*(.72+.30*broad[...,None]+.10*fine[...,None])
    rough=np.full((size,size),.59);metal=np.full((size,size),.70);height=.025*fine
    if kind=='metal':
        # Paint-loss islands, dark oxide halo and directional streaking.
        field=.51*broad+.37*mid+.12*fine
        chip=np.clip((field-.67)*16,0,1)
        halo=np.clip((field-.63)*13,0,1)
        streak=noise(size,seed+9,96)
        rust=np.stack([.16+.13*mid,.066+.045*fine,.028+.020*fine],axis=-1)
        base=base*(1-.38*halo[...,None])*(1-chip[...,None])+rust*chip[...,None]
        scratch=(grain>.997)*(mid>.44)
        base=np.where(scratch[...,None],np.array([.49,.47,.39]),base)
        rough=.43+.27*chip+.15*mid
        metal=.72*(1-chip)+.20*chip
        height=.04*fine-.08*chip+.004*grain
    elif kind=='steel':
        base*=.84+.22*np.sin(y*math.tau*230)[...,None]**2
        rough=.28+.25*mid;metal[:]=.90;height=.015*fine
    elif kind=='wood':
        rings=.5+.5*np.sin((x+ .019*np.sin(y*11)+.008*broad)*180)
        base*=.79+.16*rings[...,None]+.13*mid[...,None]
        cracks=(rings<.018)&(broad>.58)
        base[cracks]*=.42;rough=.75+.20*fine;metal[:]=0;height=.018*rings+.014*mid
    elif kind=='cloth':
        weave=(np.sin(x*math.tau*210)*np.sin(y*math.tau*210))*.5+.5
        base*=.80+.15*weave[...,None]+.22*mid[...,None]
        base*=1-.19*np.clip((broad-.55)*6,0,1)[...,None]
        rough=.88+.10*mid;metal[:]=0;height=.025*weave+.012*fine
    elif kind in ('stone','soil'):
        base*=.88+.15*mid[...,None]+.045*grain[...,None]
        rough=.82+.15*fine;metal[:]=0;height=.030*mid+.009*fine
    elif kind=='rubber':
        base*=.8+.2*fine[...,None];rough=.72+.20*mid;metal[:]=0;height=.04*fine
    # Differentiate material relief from macro geometry; no displacement claims.
    gy,gx=np.gradient(height)
    nx=-gx*size*.025;ny=-gy*size*.025;nz=np.ones_like(nx)
    normal=np.stack([nx,ny,nz],axis=-1);normal/=np.linalg.norm(normal,axis=-1)[...,None]
    channels={'basecolor':np.clip(base,0,1),'roughness':np.repeat(rough[...,None],3,axis=2),
              'metallic':np.repeat(metal[...,None],3,axis=2),'normal':normal*.5+.5}
    out={}
    for role,data in channels.items():
        p=directory/f'{name}_{role}.png';Image.fromarray(np.uint8(np.clip(data,0,1)*255)).save(p);out[role]=p
    return out


def pbr_material(directory,name,color,kind='metal',size=512):
    paths=write_maps(directory,name,color,kind,size)
    mat=bpy.data.materials.new(name);mat.use_nodes=True
    nodes=mat.node_tree.nodes;links=mat.node_tree.links;bsdf=nodes.get('Principled BSDF')
    for role,path in paths.items():
        image=bpy.data.images.load(str(path),check_existing=True)
        image.colorspace_settings.name='sRGB' if role=='basecolor' else 'Non-Color';image.pack()
        tex=nodes.new('ShaderNodeTexImage');tex.image=image;tex.extension='REPEAT';tex.label=role
        if role=='normal':
            n=nodes.new('ShaderNodeNormalMap');n.inputs['Strength'].default_value=.38
            links.new(tex.outputs['Color'],n.inputs['Color']);links.new(n.outputs['Normal'],bsdf.inputs['Normal'])
        else:links.new(tex.outputs['Color'],bsdf.inputs[{'basecolor':'Base Color','roughness':'Roughness','metallic':'Metallic'}[role]])
    mat.diffuse_color=tuple(srgb(color))+(1,)
    return mat


def solid(name,color,metal=0,rough=.5,emission=0):
    m=bpy.data.materials.new(name);m.use_nodes=True;b=m.node_tree.nodes.get('Principled BSDF')
    c=tuple(srgb(color));c=tuple(v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in c)+(1,)
    b.inputs['Base Color'].default_value=c;b.inputs['Metallic'].default_value=metal;b.inputs['Roughness'].default_value=rough
    if emission:b.inputs['Emission Color'].default_value=c;b.inputs['Emission Strength'].default_value=emission
    return m


def banner_material(directory, font_path):
    # Authored typography decal; no pixels from the supplied sheet are copied.
    size=1024;maps=write_maps(directory,'workshop-banner','#cfbea0','cloth',size)
    im=Image.open(maps['basecolor']).convert('RGB');d=ImageDraw.Draw(im)
    font=ImageFont.truetype(str(font_path),145)
    for j,line in enumerate(['GOOD','STUFF','LIVES','LONGER']):
        box=d.textbbox((0,0),line,font=font);w=box[2]-box[0]
        d.text(((size-w)/2,110+j*164),line,font=font,fill='#272c27',stroke_width=1)
    d.ellipse((414,814,610,1010),fill='#c9972d',outline='#413d29',width=4)
    for x in (467,551):d.ellipse((x-8,861,x+8,887),fill='#343829')
    d.arc((449,865,577,954),0,180,fill='#343829',width=9)
    im.save(maps['basecolor'])
    m=bpy.data.materials.new('workshop-banner');m.use_nodes=True;n=m.node_tree.nodes;l=m.node_tree.links;b=n.get('Principled BSDF')
    for role in ('basecolor','normal'):
        img=bpy.data.images.load(str(maps[role]),check_existing=False);img.colorspace_settings.name='sRGB' if role=='basecolor' else 'Non-Color';img.pack()
        t=n.new('ShaderNodeTexImage');t.image=img;t.extension='EXTEND'
        if role=='basecolor':l.new(t.outputs['Color'],b.inputs['Base Color'])
        else:
            nm=n.new('ShaderNodeNormalMap');nm.inputs['Strength'].default_value=.35;l.new(t.outputs['Color'],nm.inputs['Color']);l.new(nm.outputs['Normal'],b.inputs['Normal'])
    b.inputs['Roughness'].default_value=.95
    return m
