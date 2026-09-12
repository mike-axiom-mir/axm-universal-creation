"""Close-up face/cloth/boot passes; real fur geometry and an authored iris map."""
import math
import random
import bpy
import bmesh
import numpy as np
from PIL import Image
from mathutils import Vector
from mathutils.bvhtree import BVHTree


def remove(h,prefix):
    for o in list(h.parts):
        if o.name.startswith(prefix):h.parts.remove(o);bpy.data.objects.remove(o,do_unlink=True)


def iris(h):
    remove(h,'Brown iris');remove(h,'Iris radial fleck')
    size=512;y,x=np.mgrid[0:size,0:size]/(size-1)*2-1;r=np.sqrt(x*x+y*y);a=np.arctan2(y,x)
    rng=np.random.default_rng(471)
    fibres=.5+.5*np.sin(a*124+2*np.sin(a*29)+r*17)
    secondary=.5+.5*np.cos(a*253+r*21)
    color=np.zeros((size,size,3))
    v=.60+.30*fibres+.10*secondary+.07*rng.random((size,size))
    for i,c in enumerate([.42,.22,.09]):color[...,i]=c*v
    limbal=np.clip((r-.78)/.16,0,1);color*=1-.73*limbal[...,None]
    ring=np.exp(-((r-.52)/.06)**2);color+=ring[...,None]*np.array([.09,.027,.005])
    path=h.output/'textures'/'Hero_BrownIris.png';Image.fromarray(np.uint8(np.clip(color,0,1)*255)).save(path)
    mat=bpy.data.materials.new('Hero_radial_brown_iris');mat.use_nodes=True
    shader=mat.node_tree.nodes.get('Principled BSDF');shader.inputs['Roughness'].default_value=.17
    tex=mat.node_tree.nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(path));tex.image.pack()
    mat.node_tree.links.new(tex.outputs['Color'],shader.inputs['Base Color']);h.mat['eye_detail']=mat
    vs=[];uv=[];fs=[];n=96;rows=16
    for j in range(rows+1):
        radius=j/rows
        for i in range(n+1):
            angle=math.tau*i/n;c=math.cos(angle)*radius;s=math.sin(angle)*radius
            vs.append((-.145+.061*c,-.356-.019*math.sqrt(max(0,1-radius*radius)),1.775+.065*s));uv.append(((c+1)/2,(s+1)/2))
    for j in range(rows):
        for i in range(n):q=j*(n+1)+i;fs.append((q,q+1,q+n+2,q+n+1))
    h.mesh('Detailed brown iris',vs,fs,'eye_detail','Eye',uv)
    h.ball('Small secondary eye glint',(-.12,-.379,1.762),(.004,.002,.004),'white','Eye',12,8)


def face(h):
    remove(h,'Upper smiling muzzle');remove(h,'Lower tooth');remove(h,'Soft smiling chin')
    remove(h,'Dark mouth interior');remove(h,'Lower smile lip');remove(h,'Tongue')
    # An inward bowl gives a true shaded cavity instead of a convex dark blob
    # in front of the cut mouth. The tongue has its own articulated root.
    # Keep the inner surface ahead of the high breastplate/neck junction.
    vs=[(0,-.257,1.478)];fs=[];n=64;rows=12
    for j in range(1,rows+1):
        r=j/rows
        for i in range(n):
            a=math.tau*i/n
            vs.append((.233*r*math.cos(a),-.257-.048*r*r,1.478+.108*r*math.sin(a)))
    for i in range(n):fs.append((0,1+(i+1)%n,1+i))
    for j in range(rows-1):
        a=1+j*n;b=a+n
        for i in range(n):k=(i+1)%n;fs.append((a+i,a+k,b+k,b+i))
    h.mesh('Concave mouth cavity',vs,fs,'mouth','Head')
    h.ball('Curled smiling tongue',(0,-.286,1.421),(.093,.084,.039),'tongue','Tongue',48,24)
    h.line('Tongue central groove',[(0,-.363,1.436),(0,-.333,1.452),(0,-.294,1.460)],.0015,'skin','Tongue')
    h.current='Head'
    for s in [-1,1]:h.ball('Furry smiling muzzle',(s*.085,-.238,1.611),(.129,.09,.048),'fur',segments=48,rings=24)
    h.ball('Sculpted soft chin',(0,-.231,1.374),(.223,.110,.064),'fur','Jaw',48,24)
    socket=next(o for o in h.parts if o.name.startswith('Right eye socket'))
    socket.scale=(.90,.95,.91)
    iris(h)
    # Short bent tufts across the actual cream head. Material and eyes remain
    # separately editable; neither the reference photo nor a billboard is used.
    remove(h,'Short sculpted cream fur');rng=random.Random(471002);vs=[];fs=[]
    for i in range(34000):
        a=rng.uniform(0,math.tau);z=rng.uniform(-1,1);q=math.sqrt(1-z*z)
        n=Vector((q*math.cos(a),q*math.sin(a),z));p=Vector((n.x*.364,n.y*.266-.005,1.699+n.z*.333))
        if p.z>2.015:continue
        if p.y<-.03 and abs(p.x)<.245 and p.z<1.65:continue
        flow=Vector((0,0,-1));flow-=n*flow.dot(n)
        if flow.length<.1:flow=Vector((1,0,0))
        flow.normalize();tangent=n.cross(flow).normalized()
        length=rng.uniform(.004,.009);width=rng.uniform(.0004,.0008)
        tip=p+n*length*.45+flow*length
        base=len(vs)
        vs.extend([tuple(p-tangent*width),tuple(p+tangent*width),tuple(tip),tuple(p+n*width)])
        fs.extend([(base,base+1,base+2),(base+1,base+3,base+2),(base+3,base,base+2)])
    h.mesh('Dense short cream fur',vs,fs,'fur','Head')


def cloth(h):
    remove(h,'Folded red scarf');h.current='Chest';n,m=64,10;vs=[];fs=[];uv=[]
    for j in range(m+1):
        v=j/m
        for i in range(n+1):
            u=i/n;s=math.sin(math.pi*u)
            x=(u-.5)*.59;y=-.055-.21*s+.010*math.sin(u*29+v*4)*math.sin(math.pi*v)
            z=1.451-.042*s-v*(.095-.027*s)+.004*math.sin(u*49)*v*v
            vs.append((x,y,z));uv.append((u,v))
    for j in range(m):
        for i in range(n):q=j*(n+1)+i;fs.append((q,q+1,q+n+2,q+n+1))
    ob=h.mesh('Draped scarf with folds',vs,fs,'red','Chest',uv)
    so=ob.modifiers.new('Scarf fabric gauge','SOLIDIFY');so.thickness=.004
    for i in range(40):
        u=(i+.5)/40;s=math.sin(math.pi*u);x=(u-.5)*.59;y=-.055-.21*s
        z=1.451-.042*s-(.095-.027*s)
        h.line('Scarf frayed hem',[(x,y,z+.003),(x+.001,y-.001,z-.006)],.0008,'red')
    # The rear mark follows the actual cloth triangles; it cannot float off a
    # guessed plane or slice through a fold. Skin weights still follow cape Z.
    cape=next(o for o in h.parts if o.name.startswith('Weighted red survivor cape'))
    mark=next(o for o in h.parts if o.name.startswith('Cape AXM applique'))
    mark.modifiers.clear()
    bm=bmesh.new();bm.from_mesh(mark.data)
    bmesh.ops.triangulate(bm,faces=list(bm.faces))
    bmesh.ops.subdivide_edges(bm,edges=list(bm.edges),cuts=6,use_grid_fill=True)
    bm.to_mesh(mark.data);bm.free()
    tree=BVHTree.FromPolygons([v.co for v in cape.data.vertices],[p.vertices[:] for p in cape.data.polygons])
    # Project beyond the final solidified cloth, not merely its middle surface.
    clearance=abs(cape.modifiers['Cape cloth thickness'].thickness)+.004
    for vertex in mark.data.vertices:
        hit=tree.ray_cast(Vector((vertex.co.x,2,vertex.co.z)),Vector((0,-1,0)))
        if hit[0] is None:raise ValueError('Cape emblem outside authored fabric')
        vertex.co.y=hit[0].y+clearance
    mark.data.update()


def boots(h):
    remove(h,'Heavy toe cap');remove(h,'Boot insignia')
    for s,side in [(-1,'R'),(1,'L')]:
        bone='Foot.'+side;x=s*.28
        source=next(o for o in h.parts if o.name=='Sculpted boot '+side)
        source.data.update();center=Vector((x,-.10,.15));vs=[]
        for vertex in source.data.vertices:
            normal=vertex.normal.copy()
            if normal.dot(vertex.co-center)<0:normal=-normal
            vs.append(tuple(vertex.co+normal*.009))
        fs=[tuple(p.vertices) for p in source.data.polygons if p.center.y<-.20 and p.center.z>.035]
        ob=h.mesh('Conformal curved toe shield',vs,fs,'iron',bone)
        so=ob.modifiers.new('Toe shield gauge','SOLIDIFY');so.thickness=.004
        # The boundary is derived from the same surface, so a revised boot
        # cannot leave its cap or trim intersecting an independently guessed loft.
        edges={}
        for face_indices in fs:
            for a,b in zip(face_indices,face_indices[1:]+face_indices[:1]):
                edge=tuple(sorted((a,b)));edges[edge]=edges.get(edge,0)+1
        boundary=[edge for edge,count in edges.items() if count==1]
        while boundary:
            a,b=boundary.pop();chain=[a,b]
            while True:
                found=next((i for i,e in enumerate(boundary) if chain[-1] in e),None)
                if found is None:break
                edge=boundary.pop(found);chain.append(edge[1] if edge[0]==chain[-1] else edge[0])
                if chain[-1]==chain[0]:break
            h.line('Conformal toe trim',[vs[i] for i in chain],.003,'steel',bone)


def finish(h):
    face(h);cloth(h);boots(h)
