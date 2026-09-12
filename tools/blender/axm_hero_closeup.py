"""Close-up face/cloth/boot passes; real fur geometry and an authored iris map."""
import math
import random
import bpy
import bmesh
import numpy as np
from PIL import Image
from mathutils import Vector
from mathutils.bvhtree import BVHTree
import axm_blender_forge as geo


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


def lower_jaw(h):
    """A cheek-to-cheek jaw arc and rooted tongue, rather than stacked ovals.

    The jaw shares the cavity's head/jaw blend. Its upper ends disappear inside
    the cheeks, while its front stays beside the cavity's curved lower edge.
    The tongue is a closed longitudinal volume with a recessed dorsal groove;
    its hidden root extends into the mouth instead of resting on the chin.
    """
    vs=[];fs=[];uv=[];rows=80;ring=32
    for j in range(rows+1):
        u=j/rows;a=math.pi-.18+u*(math.pi+.36)
        ca,sa=math.cos(a),math.sin(a)
        cx=.222*ca;cy=-.225+.100*ca*ca;cz=1.478+.111*sa
        radial=.030+.014*abs(ca);depth=.072-.006*abs(ca)
        for i in range(ring):
            b=math.tau*i/ring;c,s=math.cos(b),math.sin(b)
            vs.append((cx+ca*radial*c,cy+depth*s,cz+sa*radial*c))
            uv.append((u,i/ring))
    for j in range(rows):
        for i in range(ring):
            a=j*ring+i;b=j*ring+(i+1)%ring
            fs.append((a,b,b+ring,a+ring))
    fs.extend([tuple(reversed(range(ring))),tuple(rows*ring+i for i in range(ring))])
    jaw=h.mesh('Continuous cheek-to-cheek lower jaw',vs,fs,'fur','Jaw',uv)
    jaw['axm_mouth']=True
    # Fine short tufts follow the front/outer jaw surface and its skin blend.
    rng=random.Random(471003);fv=[];ff=[]
    for _ in range(2200):
        u=rng.uniform(.06,.94);a=math.pi-.18+u*(math.pi+.36)
        ca,sa=math.cos(a),math.sin(a);b=rng.uniform(-math.pi*.70,math.pi*.10)
        c,s=math.cos(b),math.sin(b);radial=.030+.014*abs(ca);depth=.072-.006*abs(ca)
        p=Vector((.222*ca+ca*radial*c,-.225+.100*ca*ca+depth*s,1.478+.111*sa+sa*radial*c))
        normal=Vector((ca*c,s,sa*c)).normalized();flow=Vector((ca*.4,0,-1))
        tangent=normal.cross(flow).normalized();length=rng.uniform(.002,.0045);w=.00035
        k=len(fv);fv.extend([tuple(p-tangent*w),tuple(p+tangent*w),tuple(p+normal*length*.4+flow*length)])
        ff.append((k,k+1,k+2))
    fuzz=h.mesh('Short lower jaw fur',fv,ff,'fur','Jaw');fuzz['axm_mouth']=True
    vs=[(0,-.135,1.478)];fs=[];uv=[(.5,0)];rows=32;ring=48
    for j in range(1,rows):
        u=j/rows;q=math.sin(math.pi*u);width=.077*q**.55;thickness=.033*q**.5
        cy=-.195-.149*u;cz=1.472-.048*u+.008*math.sin(math.pi*u)
        for i in range(ring):
            a=math.tau*i/ring;x=width*math.cos(a)
            z=cz+thickness*math.sin(a)
            z-=.0018*math.exp(-(x/.009)**2)*q*max(0,math.sin(a))**8
            vs.append((x,cy,z));uv.append((i/ring,u))
    for i in range(ring):fs.append((0,1+(i+1)%ring,1+i))
    for j in range(rows-2):
        for i in range(ring):
            a=1+j*ring+i;b=1+j*ring+(i+1)%ring
            fs.append((a,b,b+ring,a+ring))
    tip=len(vs);vs.append((0,-.344,1.424));uv.append((.5,1))
    last=1+(rows-2)*ring
    for i in range(ring):fs.append((last+i,last+(i+1)%ring,tip))
    h.mesh('Rooted curled tongue',vs,fs,'tongue','Tongue',uv)


def face(h):
    remove(h,'Upper smiling muzzle');remove(h,'Lower tooth');remove(h,'Soft smiling chin')
    remove(h,'Dark mouth interior');remove(h,'Lower smile lip');remove(h,'Tongue')
    # An inward bowl gives a true shaded cavity instead of a convex dark blob
    # in front of the cut mouth. The tongue has its own articulated root.
    # The perimeter follows the curved face, rather than placing a flat oval
    # in front of it. Its lower vertices blend onto the jaw during animation.
    vs=[(0,-.135,1.478)];fs=[];n=64;rows=12
    for j in range(1,rows+1):
        r=j/rows
        for i in range(n):
            a=math.tau*i/n
            edge_y=-.30+.168*math.cos(a)**2
            vs.append((.207*r*math.cos(a),-.135*(1-r*r)+edge_y*r*r,1.478+.102*r*math.sin(a)))
    for i in range(n):fs.append((0,1+(i+1)%n,1+i))
    for j in range(rows-1):
        a=1+j*n;b=a+n
        for i in range(n):k=(i+1)%n;fs.append((a+i,a+k,b+k,b+i))
    interior=h.mesh('Concave mouth cavity',vs,fs,'mouth','Head');interior['axm_mouth']=True
    # Shape the collar around the open mouth instead of moving the mouth
    # forward to conceal intersecting torso geometry.
    cutter=geo.sphere('Temporary throat clearance',(0,-.12,1.465),(.27,.28,.17),h.mat['mouth'],segments=48,rings=24)
    for part in h.parts:
        if part.name.startswith(('Barrel torso padded underlayer','Curved yellow breastplate shaped forged shell')):
            geo.select_only([part]);bpy.context.view_layer.objects.active=part
            mod=part.modifiers.new('Throat clearance','BOOLEAN');mod.operation='DIFFERENCE';mod.object=cutter
            bpy.ops.object.modifier_apply(modifier=mod.name)
        if part.name.startswith('Chest AXM raised emblem'):part.location.z-=.045
    bpy.data.objects.remove(cutter,do_unlink=True)
    lower_jaw(h)
    h.current='Head'
    for s in [-1,1]:h.ball('Furry smiling muzzle',(s*.085,-.238,1.611),(.129,.09,.048),'fur',segments=48,rings=24)
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
            z=1.451-.042*s-.075*s*s-v*(.095-.027*s)+.004*math.sin(u*49)*v*v
            vs.append((x,y,z));uv.append((u,v))
    for j in range(m):
        for i in range(n):q=j*(n+1)+i;fs.append((q,q+1,q+n+2,q+n+1))
    ob=h.mesh('Draped scarf with folds',vs,fs,'red','Chest',uv)
    so=ob.modifiers.new('Scarf fabric gauge','SOLIDIFY');so.thickness=.004
    for i in range(40):
        u=(i+.5)/40;s=math.sin(math.pi*u);x=(u-.5)*.59;y=-.055-.21*s
        z=1.451-.042*s-.075*s*s-(.095-.027*s)
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
