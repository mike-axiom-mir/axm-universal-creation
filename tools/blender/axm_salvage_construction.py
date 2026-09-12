"""Small composable Blender construction operations for salvage architecture.

Z-up in editable source; standard Blender glTF exporter converts to Y-up.
"""
import math
import random
import bpy
from mathutils import Vector
from axm_blender_forge import box, cylinder, cone, torus, cable, beam, sphere


def mesh(name, verts, faces, mat, uv=None, smooth=False):
    data=bpy.data.meshes.new(name);data.from_pydata(verts,[],faces);data.update()
    ob=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(ob);data.materials.append(mat)
    tex=data.uv_layers.new(name='UVMap')
    for p in data.polygons:
        p.use_smooth=smooth
        axis=max(range(3),key=lambda i:abs(p.normal[i]))
        axes=((1,2),(0,2),(0,1))[axis]
        for l in p.loop_indices:
            vi=data.loops[l].vertex_index;v=data.vertices[vi].co
            tex.data[l].uv=uv[vi] if uv else (v[axes[0]],v[axes[1]])
    return ob


def corrugated(name, center, width, height, material, rotation=0, seed=1):
    """A bent corrugated sheet with actual profile, thickness and bounded dents."""
    rng=random.Random(seed);phase=rng.random()*6
    nx=max(18,int(width*72));nz=8;verts=[];uv=[]
    for j in range(nz+1):
        v=j/nz
        for i in range(nx+1):
            u=i/nx;x=(u-.5)*width;z=(v-.5)*height
            profile=.026*math.cos(u*width*math.tau*6)
            dent=.035*math.sin(u*13+phase)*math.sin(v*5)*math.sin(math.pi*u)
            verts.append((x,profile+dent,z));uv.append((u*width*.8,v*height*.8))
    faces=[]
    for j in range(nz):
        for i in range(nx):
            a=j*(nx+1)+i;faces.append((a,a+1,a+nx+2,a+nx+1))
    ob=mesh(name,verts,faces,material,uv);ob.location=center;ob.rotation_euler.z=rotation
    sol=ob.modifiers.new('Rolled sheet thickness','SOLIDIFY');sol.thickness=.014
    return ob


def cloth(name, corners, mat, sag=.22, subdivisions=(32,24), flutter=.022, tile=(1,1), edge_sag=0, corner_folds=0):
    """Four pinned corners with sag, unequal folds, seam-ready sample function."""
    a,b,c,d=[Vector(v) for v in corners];nx,ny=subdivisions
    def point(u,v):
        p=(a*(1-u)+b*u)*(1-v)+(c*(1-u)+d*u)*v
        p.z-=sag*math.sin(math.pi*u)*math.sin(math.pi*v)+edge_sag*math.sin(math.pi*u)*v**3
        p.z+=flutter*math.sin(u*math.pi*12+v*3)*math.sin(math.pi*u)*(.3+.7*v)
        p.z+=corner_folds*math.sin(math.pi*v)*(math.sin(v*19+u*8)*math.exp(-u*5)+.7*math.sin(v*23-u*8)*math.exp(-(1-u)*5))
        p.y+=flutter*.65*math.sin(u*9+v*15)*math.sin(math.pi*v)
        return tuple(p)
    verts=[point(i/nx,j/ny) for j in range(ny+1) for i in range(nx+1)]
    uvs=[(i/nx*tile[0],(1-j/ny)*tile[1]) for j in range(ny+1) for i in range(nx+1)]
    faces=[]
    for j in range(ny):
        for i in range(nx):
            q=j*(nx+1)+i;faces.append((q,q+1,q+nx+2,q+nx+1))
    ob=mesh(name,verts,faces,mat,uvs,True)
    mod=ob.modifiers.new('Canvas thickness','SOLIDIFY');mod.thickness=.008
    return ob,point


def flange(name, center, radius, mat, boltmat, axis=(0,0,1)):
    normal=Vector(axis).normalized();ob=cylinder(name,center,radius,.055,mat,vertices=32,bevel=.008)
    ob.rotation_mode='QUATERNION';ob.rotation_quaternion=normal.to_track_quat('Z','Y')
    tangent=normal.cross(Vector((0,1,0)))
    if tangent.length<.1:tangent=normal.cross(Vector((1,0,0)))
    tangent.normalize();other=normal.cross(tangent)
    for j in range(8):
        a=j*math.tau/8;p=Vector(center)+radius*.78*(math.cos(a)*tangent+math.sin(a)*other)
        b=cylinder(name+' bolt',tuple(p),.024,.078,boltmat,vertices=6,bevel=.002)
        b.rotation_mode='QUATERNION';b.rotation_quaternion=ob.rotation_quaternion


def barrel(name,c,mats,paint='teal',r=.30,h=.82):
    x,y,z=c;cylinder(name,(x,y,z+h/2),r,h,mats[paint],vertices=32,bevel=.025)
    for k in (.05,.28,.72,.95):torus(name+' pressed bead',(x,y,z+h*k),r+.006,.013,mats['steel'],major_segments=32,minor_segments=6)
    cylinder(name+' recessed lid',(x,y,z+h+.006),r*.94,.014,mats[paint],vertices=32,bevel=.002)
    cylinder(name+' bung',(x+r*.47,y,z+h+.018),.048,.025,mats['iron'],vertices=10,bevel=.004)


def crate(name,c,mats,w=.9,d=.62,h=.65):
    x,y,z=c
    box(name+' dark interior',(x,y,z+h*.46),(w*.95,d*.95,h*.90),mats['iron'],bevel=.012)
    for yy in [-d/2,d/2]:
        for j in range(4):box(name+' board',(x,y+yy,z+h*(j+.5)/4),(w,.055,h/4-.014),mats['wood'],bevel=.015)
        for xx in [-w*.40,w*.40]:
            box(name+' upright',(x+xx,y+yy*1.07,z+h/2),(.075,.05,h+.055),mats['wood'],bevel=.01)
            for zz in [.08,h-.08]:cylinder(name+' nail',(x+xx,y+yy*1.13,z+zz),.015,.01,mats['steel'],rotation=(math.pi/2,0,0),vertices=8,bevel=.001)
    for i in range(5):box(name+' lid plank',(x-w/2+(i+.5)*w/5,y,z+h),(w/5-.012,d,.05),mats['wood'],bevel=.009)


def lantern(name,c,mats,scale=1):
    x,y,z=c;s=scale
    cylinder(name+' luminous glass',(x,y,z),.088*s,.29*s,mats['emission'],vertices=24,bevel=.01)
    for dz,r in [(-.19,.13),(-.16,.105),(.17,.14),(.21,.10)]:
        cylinder(name+' cap',(x,y,z+dz*s),r*s,.035*s,mats['brass'],vertices=24,bevel=.009)
    cone(name+' hood',(x,y,z+.245*s),.14*s,.055*s,.075*s,mats['iron'],vertices=24,bevel=.008)
    for j in range(6):
        a=math.tau*j/6;dx=.105*s*math.cos(a);dy=.105*s*math.sin(a)
        beam(name+' cage',(x+dx,y+dy,z-.17*s),(x+dx,y+dy,z+.18*s),.009*s,mats['iron'],vertices=6)
    torus(name+' handle',(x,y,z+.33*s),.065*s,.010*s,mats['iron'],rotation=(math.pi/2,0,0),major_segments=20,minor_segments=6)
    light=bpy.data.lights.new(name+' practical','POINT');light.energy=75*s;light.color=(1,.48,.14);light.shadow_soft_size=.13*s
    ob=bpy.data.objects.new(name+' practical',light);bpy.context.collection.objects.link(ob);ob.location=(x,y-.18*s,z-.02*s)
    # Outside the opaque emissive shell: the lamp can illuminate its surroundings.
    ob['export_note']='Render practical; intensity must be matched by the game lighting setup.'


def plant(name,c,mats,seed=1,scale=1):
    rng=random.Random(seed);x,y,z=c
    for j in range(7):
        a=j*2.4;l=rng.uniform(.14,.35)*scale;dx,dy=math.cos(a),math.sin(a)
        verts=[(x,y,z),(x+dx*l*.4-dy*l*.13,y+dy*l*.4+dx*l*.13,z+l*.5),
               (x+dx*l,y+dy*l,z+l*.55),(x+dx*l*.4+dy*l*.13,y+dy*l*.4-dx*l*.13,z+l*.5),
               (x+dx*l*.4,y+dy*l*.4,z+l*.6)]
        ob=mesh(name,verts,[(0,1,4),(1,2,4),(2,3,4),(3,0,4)],mats['leaf'])
        so=ob.modifiers.new('Leaf thickness','SOLIDIFY');so.thickness=.002


def physically_scaled_uv(objects):
    """Project hard surface materials in object dimensions; preserve cloth UVs."""
    for obj in objects:
        if obj.type!='MESH' or not obj.data.uv_layers or obj.get('preserve_uv'):continue
        layer=obj.data.uv_layers.active
        if obj.name.startswith(('tarp','banner','patch-cloth')):continue
        extent=max(obj.dimensions)
        factor=max(.08,min(5,extent/1.1))
        salt=int.from_bytes(obj.name.encode()[:4],'little')%97/97
        for loop in layer.data:loop.uv=loop.uv*factor+Vector((salt,salt*.63))
