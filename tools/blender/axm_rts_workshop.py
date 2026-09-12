"""Reference-led workshop model, retained source and fresh-import render review.

This is an authored interpretation of 1000000415.png, not image reconstruction.
Build with Blender Python 4.3: python axm_rts_workshop.py --output NEW_DIRECTORY.
"""
import argparse
import hashlib
import json
import math
import random
import sys
from pathlib import Path
import bpy
import bmesh
from mathutils import Vector
from axm_blender_forge import box, cylinder, cone, torus, cable, beam, sphere, select_only, export_glb
from axm_salvage_construction import mesh, corrugated, cloth, flange, barrel, crate, lantern, plant, physically_scaled_uv
from axm_salvage_surfaces import pbr_material, solid, banner_material


def materials(out,font):
    specs={'teal':('#326970','metal'),'blue':('#305362','metal'),'ivory':('#9b9c87','metal'),
      'iron':('#454746','metal'),'steel':('#adb1a8','steel'),'brass':('#a38a51','metal'),
      'rust':('#8e4b29','metal'),'red':('#9e392d','metal'),'yellow':('#b59039','metal'),
      'wood':('#9d7850','wood'),'tarp':('#355f70','cloth'),'tarp_light':('#527884','cloth'),
      'stone':('#9d9b83','stone'),'soil':('#4d4939','soil'),'rubber':('#252b29','rubber')}
    m={k:pbr_material(out/'textures',k,c,t,512) for k,(c,t) in specs.items()}
    m['emission']=solid('warm-glass','#ffbc50',rough=.2,emission=5)
    m['black']=solid('printed-charcoal','#252b26',rough=.88)
    m['leaf']=solid('leaf-sage','#697a38',rough=.9)
    m['banner']=banner_material(out/'textures',font)
    return m


def foundation(m):
    rng=random.Random(23)
    box('buried soil foundation',(0,.15,.07),(5.45,4.25,.14),m['soil'],bevel=.12)
    # Uneven individual paving slabs, thin joints, edge damage and moss tufts.
    for i in range(10):
        for j in range(8):
            x=-2.48+i*.55;y=-1.8+j*.55;z=.16+rng.uniform(-.009,.012)
            box('foundation paver',(x,y,z),(.533+rng.uniform(-.01,.01),.531,.16),m['stone'],rotation=(0,0,rng.uniform(-.015,.015)),bevel=.023)
    for j in range(65):
        a=rng.random()*math.tau;r=rng.uniform(.87,1.03);x=math.cos(a)*2.65*r;y=.15+math.sin(a)*2.1*r
        ob=sphere('broken edge aggregate',(x,y,.17),(rng.uniform(.02,.095),rng.uniform(.02,.09),rng.uniform(.015,.055)),m['stone'],segments=7,rings=4)
        ob.rotation_euler=(rng.random(),rng.random(),rng.random())
    for i,c in enumerate([(-2.35,-1.71,.25),(2.35,-1.73,.25),(-2.60,.4,.24),(1.2,2.0,.24),(2.5,1.3,.24),(-.5,-1.96,.24)]):plant('weeds in joints',c,m,i)


def main_structure(m):
    # A closed left utility bay and an open right working bay, not one empty cube.
    for x in [-2.1,-.53,2.08]:
        for y in [-.7,1.60]:
            box('weathered structural post',(x,y,1.69),(.115,.115,2.92),m['iron'],bevel=.021)
            box('post footplate',(x,y,.31),(.25,.23,.07),m['rust'],bevel=.011)
            for dx in [-.082,.082]:cylinder('anchor bolt',(x+dx,y,.36),.027,.065,m['steel'],vertices=6,bevel=.002)
    for y in [-.72,1.62]:
        box('left upper load beam',(-1.33,y,3.12),(1.78,.13,.13),m['iron'],bevel=.018)
        box('working bay upper beam',(.80,y,2.93 if y<0 else 3.20),(2.68,.11,.10),m['iron'],bevel=.014)
        box('lower sill',(0,y,.40),(4.42,.13,.12),m['iron'],bevel=.016)
    for x in [-2.11,-.54,2.10]:box('roof runner',(x,.4,3.15),(.09,2.65,.10),m['iron'],bevel=.018)
    for k in range(6):corrugated('rear mismatched corrugation',(-1.76+k*.71,1.6,1.78),.73,2.53,m[['teal','blue','ivory','teal','iron','teal'][k]],seed=k)
    for k in range(3):corrugated('left side sheets',(-2.1,-.28+k*.76,1.73),.79,2.52,m['teal' if k!=1 else 'blue'],math.pi/2,k+12)
    # Left front has the sign on real panels, visible service door and latch.
    for k in range(2):corrugated('utility front corrugation',(-1.71+k*.72,-.74,1.74),.75,2.48,m['ivory'],seed=k+20)
    box('utility door top',(-1.35,-.78,2.99),(1.55,.10,.085),m['iron'],bevel=.012)
    for x in [-2.03,-.59]:box('door upright',(x,-.79,1.71),(.08,.065,2.60),m['iron'],bevel=.012)
    for x in [-1.86,-.71]:
        for z in [.55,1.4,2.65]:
            box('door hinge',(x,-.835,z),(.105,.06,.12),m['brass'],bevel=.012)
    cable('door pull',[(-.79,-.91,1.43),(-.84,-1.02,1.43),(-.84,-1.02,1.19),(-.79,-.91,1.19)],.022,m['steel'])
    # Right wall is partial with exposed framing and a deep view inside.
    for k in range(3):corrugated('right side service wall',(2.08,-.23+k*.76,1.24),.79,1.63,m['teal' if k%2 else 'blue'],math.pi/2,k+28)
    for y in [-.62,.5,1.56]:
        box('right wall trim',(2.12,y,1.46),(.065,.065,2.05),m['rust'],bevel=.012)
    # Offset patch sheets and riveted overlap seams.
    for x,z,w,h in [(-1.88,.82,.31,.46),(-.82,2.58,.31,.35),(-1.8,2.81,.29,.22)]:
        box('repair patch plate',(x,-.83,z),(w,.035,h),m['teal'],rotation=(0,math.radians(3),0),bevel=.01)
        for dx in [-w*.37,w*.37]:
            for dz in [-h*.36,h*.36]:cylinder('patch rivet',(x+dx,-.86,z+dz),.017,.022,m['brass'],rotation=(math.pi/2,0,0),vertices=8,bevel=.002)
    for x in [-2.05,-.59,2.1]:
        for z in [.58,1.05,1.65,2.40,2.97]:cylinder('frame face bolt',(x,-.82,z),.023,.035,m['steel'],rotation=(math.pi/2,0,0),vertices=6,bevel=.003)
    # Top solid left bay and ragged salvage over rear half of working bay.
    for k in range(2):
        x=-1.72+k*.74
        box('overlapping utility roof panel',(x,.71,3.19+.012*math.sin(k)),(.81,1.96,.05),m['teal' if k%2 else 'iron'],rotation=(0,.009*math.sin(k),0),bevel=.014)
    # Keep the banner small enough to reveal construction around it.
    cloth('banner GOOD STUFF',[(-1.84,-.899,2.76),(-.91,-.913,2.73),(-1.84,-.945,1.18),(-.91,-.973,1.14)],m['banner'],sag=.018,subdivisions=(16,28),flutter=.012)
    for x in [-1.83,-.93]:torus('banner eyelet',(x,-.932,2.70),.025,.007,m['brass'],rotation=(math.pi/2,0,0),major_segments=12,minor_segments=6)


def roof_canopy(m):
    # Two different fabric spans; gravity sag lives between tensioned corners.
    corners=[(-.63,1.14,3.72),(2.34,1.20,3.62),(-.60,-1.51,3.30),(2.38,-1.36,3.43)]
    ob,pt=cloth('tarp main tensioned roof',corners,m['tarp'],sag=.12,flutter=.047,tile=(2,2),edge_sag=.24,corner_folds=.095)
    for u in [0,.34,.69,1]:
        cable('canvas stitched seam',[pt(u,j/32) for j in range(33)],.009,m['tarp_light'])
    for v in [0,1]:cable('canvas bound hem',[pt(j/40,v) for j in range(41)],.017,m['tarp_light'])
    # Scalloped valance hangs from front edge and exposes two glowing lamps.
    top=[Vector(pt(i/32,1)) for i in range(33)];verts=[];uv=[]
    for row in range(7):
        v=row/6
        for i,p in enumerate(top):
            u=i/32;drop=(.20+.08*math.sin(u*math.pi*3)**2)*v
            verts.append(tuple(p+Vector((0,-.025*v, -drop))));uv.append((u*2,1-v*.3))
    faces=[]
    for j in range(6):
        for i in range(32):q=j*33+i;faces.append((q,q+1,q+34,q+33))
    mesh('tarp scalloped front valance',verts,faces,m['tarp'],uv,True)
    # Small separate blue tarp drapes over left roof edge like the source.
    cloth('tarp left hanging strip',[(-1.15,-.48,3.30),(-.56,-.42,3.34),(-1.08,-.84,2.62),(-.51,-.80,2.68)],m['tarp_light'],sag=.08,flutter=.025)
    for p in corners:
        a=Vector(p);foot=(a.x*.98,a.y*.98,.3)
        beam('canopy steel support',foot,tuple(a+Vector((0,0,.10))),.035,m['iron'],vertices=12)
        torus('canopy collar',tuple(a),.055,.013,m['brass'],major_segments=16,minor_segments=6)
        cable('canopy tie rope',[tuple(a),tuple(a+Vector((.12,-.12,-.20))),(a.x*1.04,a.y*1.12,.38)],.012,m['wood'])
    # Repair patch follows actual roof curvature rather than floating above it.
    verts=[];uv=[]
    for j in range(9):
        for i in range(9):
            u=.57+i*.16/8;v=.35+j*.18/8
            verts.append(tuple(Vector(pt(u,v))+Vector((0,0,.009))));uv.append((i/8*.4,j/8*.4))
    faces=[]
    for j in range(8):
        for i in range(8):q=j*9+i;faces.append((q,q+1,q+10,q+9))
    mesh('patch-cloth fitted roof repair',verts,faces,m['tarp_light'],uv,True)



def pipes_and_roof(m):
    # Back-right smokestack with flange joints, straps and a separate rain cap.
    x,y=1.48,1.22
    cylinder('stove chimney',(x,y,3.20),.16,2.90,m['iron'],vertices=32,bevel=.015)
    for z in [2.4,3.33,4.13]:flange('chimney flange',(x,y,z),.195,m['steel'],m['iron'])
    cylinder('chimney rain cap',(x,y,4.75),.235,.07,m['steel'],vertices=32,bevel=.018)
    for a in [0,math.pi/2,math.pi,3*math.pi/2]:
        beam('rain cap spacer',(x+.18*math.cos(a),y+.18*math.sin(a),4.54),(x+.18*math.cos(a),y+.18*math.sin(a),4.74),.014,m['iron'],vertices=8)
    for z in [2.9,3.4]:beam('chimney wall brace',(x,y,z),(2.12,y,z-.13),.027,m['rust'],vertices=12)
    # Bent coolant loop to the right: readable pipe/elbow/valve hierarchy.
    cable('exterior return pipe',[(2.30,1.0,.55),(2.30,1.0,3.66),(2.30,.40,3.66),(2.30,.37,2.65)],.065,m['brass'])
    for z in [1.1,2.45,3.4]:flange('return pipe union',(2.30,1.0,z),.105,m['iron'],m['steel'])
    torus('service valve wheel',(2.34,.76,1.44),.15,.017,m['red'],rotation=(math.pi/2,0,0),major_segments=24,minor_segments=6)
    for a in [0,math.pi/2,math.pi,3*math.pi/2]:beam('valve spoke',(2.34,.76,1.44),(2.34+.14*math.cos(a),.76,1.44+.14*math.sin(a)),.009,m['red'],vertices=6)
    # Satellite bowl: tilted toward front-left, with a feed strut and bracket.
    parent=bpy.data.objects.new('satellite assembly',None);bpy.context.collection.objects.link(parent)
    verts=[];uv=[];segments=40;rings=12;r=.48
    for j in range(rings+1):
        rad=.003+(r-.003)*j/rings
        for i in range(segments):
            a=i*math.tau/segments;verts.append((rad*math.cos(a),rad*math.sin(a),rad*rad*.7));uv.append((i/segments,j/rings))
    faces=[]
    for j in range(rings):
        for i in range(segments):a=j*segments+i;b=j*segments+(i+1)%segments;faces.append((a,b,b+segments,a+segments))
    dish=mesh('satellite bowl',verts,faces,m['ivory'],uv,True);dish.parent=parent
    sol=dish.modifiers.new('Dish sheet','SOLIDIFY');sol.thickness=.017
    rim=torus('satellite rim',(0,0,r*r*.7),r,.015,m['steel'],major_segments=40,minor_segments=6);rim.parent=parent
    for a in [0,math.tau/3,math.tau*2/3]:
        b=beam('satellite feed support',(r*.95*math.cos(a),r*.95*math.sin(a),r*r*.7),(0,0,.60),.014,m['iron'],vertices=8);b.parent=parent
    b=cylinder('satellite feed',(0,0,.61),.044,.1,m['iron'],vertices=16,bevel=.008);b.parent=parent
    parent.location=(-1.70,.19,3.37);parent.rotation_euler=(math.radians(42),math.radians(-20),math.radians(-18))
    beam('satellite mounting pole',(-1.7,.2,3.16),(-1.7,.2,3.44),.065,m['iron'],vertices=16)
    # Small rear hoist, wires and a battered battery box, matching roof clutter.
    for xx in [-.38,-.22]:beam('rear roof hoist upright',(xx,1.3,3.25),(xx,.90,3.98),.042,m['rust'],vertices=12)
    beam('rear roof hoist crosspiece',(-.45,.86,3.98),(.3,.40,3.66),.055,m['iron'],vertices=12)
    torus('hoist pulley',(-.12,.78,3.91),.10,.024,m['brass'],rotation=(math.pi/2,0,0),major_segments=24,minor_segments=8)
    cable('roof cable hanging',[(-1.5,.22,3.5),(-.65,.60,3.32),(-.1,.80,3.87)],.013,m['rubber'])
    box('roof battery box',(-.95,.90,3.45),(.8,.48,.40),m['iron'],bevel=.04)
    for xx in [-1.2,-1.06,-.92,-.78]:
        cylinder('battery terminal',(xx,.92,3.7),.04,.12,m['brass'],vertices=12,bevel=.007)
    cable('battery lead',[(-1.2,.92,3.73),(-1.5,.5,3.51),(-1.9,1.0,3.3)],.016,m['red'])


def workshop_interior(m):
    # Back shelves stand behind a substantial used workbench, visible through bay.
    for z in [.75,1.4,2.1,2.66]:box('interior shelf',(.76,1.34,z),(2.15,.45,.075),m['wood'],bevel=.016)
    for xx in [-.28,1.77]:box('shelf upright',(xx,1.38,1.68),(.065,.075,2.05),m['iron'],bevel=.01)
    rng=random.Random(42)
    for j in range(16):
        x=-.13+(j%5)*.38;y=1.34;z=[.80,1.45,2.15,2.71][j//5]
        if j%3:
            cylinder('shelf parts can',(x,y,z+.11),rng.uniform(.065,.12),.22,m[['red','ivory','teal','brass'][j%4]],vertices=16,bevel=.012)
            cylinder('can lid',(x,y,z+.225),.09,.022,m['steel'],vertices=16,bevel=.003)
        else:box('parts storage drawer',(x,y,z+.13),(.26,.27,.25),m['iron'],bevel=.024)
    # Solid bench top is made of multiple rounded, worn hardwood boards.
    for j in range(4):box('bench plank',(.69,-.50+j*.19,1.14),(2.20,.182,.125),m['wood'],bevel=.025)
    for x in [-.27,1.61]:
        for y in [-.44,.10]:
            box('bench angle-iron leg',(x,y,.71),(.08,.08,.90),m['iron'],rotation=(0,math.radians(3 if x<0 else -3),0),bevel=.01)
        box('bench stretcher',(x,-.15,.52),(.075,.69,.065),m['rust'],bevel=.008)
    box('bench bottom shelf',(.7,-.1,.50),(1.92,.56,.05),m['wood'],bevel=.014)
    crate('underbench parts',(.62,-.10,.53),m,w=.76,d=.48,h=.39)
    # Vise with jaw plates, shaft, tommy bar and swivel base.
    cylinder('vise swivel',(.15,-.56,1.24),.18,.09,m['iron'],vertices=24,bevel=.015)
    box('vise body',(.15,-.57,1.39),(.34,.30,.20),m['blue'],bevel=.035)
    for x in [.02,.28]:box('vise jaw',(x,-.57,1.53),(.07,.29,.06),m['steel'],bevel=.009)
    beam('vise threaded spindle',(.15,-.61,1.35),(.15,-.99,1.35),.026,m['steel'],vertices=12)
    beam('vise handle',(.15,-1.00,1.18),(.15,-1.00,1.50),.018,m['steel'],vertices=10)
    # Pegboard tools behind the bench; each has metal head plus grip.
    box('tool board',(.25,1.03,2.27),(1.02,.035,.88),m['wood'],bevel=.015)
    for i in range(4):
        x=-.1+i*.23
        beam('hanging tool shank',(x,.976,1.98),(x,.976,2.45),.016,m['steel'],vertices=8)
        box('tool grip',(x,.970,2.06),(.06,.05,.18),m['red' if i%2 else 'wood'],bevel=.02)
        if i%2:torus('spanner open ring',(x,.964,2.47),.060,.017,m['steel'],rotation=(math.pi/2,0,0),major_segments=16,minor_segments=6)
        else:box('hammer head',(x,.963,2.47),(.18,.065,.075),m['steel'],bevel=.016)
    # Task-lamp arm, lamps and their actual warm light inside the bay.
    beam('task lamp stem',(1.36,.13,1.20),(1.38,.17,1.75),.026,m['iron'],vertices=12)
    beam('task lamp elbow',(1.38,.17,1.75),(1.05,-.14,1.95),.025,m['iron'],vertices=12)
    cone('task lamp shade',(1.03,-.16,1.95),.16,.055,.12,m['brass'],vertices=24,bevel=.009)
    lantern('interior lamp',(.62,.55,2.51),m,.86)
    for x,z in [(-.35,2.47),(1.96,2.62)]:
        beam('lantern hanger',(x,-1.20,3.02),(x,-1.20,z+.3),.010,m['iron'],vertices=6)
        lantern('canopy lantern',(x,-1.20,z),m,.93)
    # Bench objects: can, spanner, bolts, stacked plates and cable reel.
    cylinder('oil can',(.87,-.19,1.33),.11,.25,m['red'],vertices=24,bevel=.014)
    cable('oil can spout',[(.87,-.19,1.46),(.90,-.24,1.55),(1.02,-.26,1.59)],.016,m['brass'])
    box('bench tray',(1.4,-.48,1.23),(.41,.32,.045),m['iron'],bevel=.014)
    for j in range(7):cylinder('tray nuts',(1.24+(j%3)*.11,-.56+(j//3)*.085,1.26),.025,.035,m['steel'],vertices=6,bevel=.002)
    for x in [.42,.68]:box('loose plate',(x,-.53,1.222),(.16,.28,.012),m['steel'],rotation=(0,0,.2),bevel=.003)
    # Leaning ladder on the edge between sign bay and workspace.
    for x in [-.60,-.24]:beam('ladder wooden rail',(x,-1.25,.28),(x,-.53,2.86),.032,m['wood'],vertices=10)
    for j in range(8):
        t=(j+.6)/8;z=.3+2.46*t;y=-1.25+.72*t
        beam('ladder rung',(-.60,y,z),(-.24,y,z),.027,m['wood'],vertices=10)


def foreground(m):
    barrel('left fuel drum',(-2.15,-1.17,.26),m,r=.28,h=.87)
    barrel('right workshop drum',(2.10,-.9,.26),m,'ivory',r=.27,h=.72)
    crate('front supplies',(-1.34,-1.39,.26),m,w=.87,d=.61,h=.56)
    cylinder('service cylinder',(-.68,-1.04,.67),.13,.81,m['iron'],vertices=24,bevel=.025)
    torus('service cylinder collar',(-.68,-1.04,1.04),.13,.018,m['steel'],major_segments=24,minor_segments=6)
    cylinder('service valve',(-.68,-1.04,1.16),.044,.14,m['brass'],vertices=12,bevel=.008)
    mesh('fuel warning triangle',[(-2.26,-1.452,.75),(-2.04,-1.452,.75),(-2.15,-1.452,.94)],[(0,1,2)],m['yellow'])
    # Tool chest: nested panels, lid seam, corner protectors and two brass latches.
    x,y,z=1.35,-1.52,.26
    box('red toolbox',(x,y,z+.26),(.90,.49,.49),m['red'],bevel=.055)
    box('toolbox lid',(x,y,z+.54),(.94,.52,.12),m['red'],bevel=.026)
    for xx in [x-.29,x+.29]:
        box('toolbox latch',(xx,y-.272,z+.44),(.055,.032,.17),m['brass'],bevel=.009)
        box('toolbox corner strap',(xx,y,z+.54),(.042,.54,.14),m['iron'],bevel=.007)
    cable('toolbox handle',[(x-.17,y,z+.61),(x-.17,y,z+.73),(x+.17,y,z+.73),(x+.17,y,z+.61)],.026,m['iron'])
    # A pair of upright compressed-gas bottles with cap and a looped rubber hose.
    for j in range(2):
        xx=-.34+j*.22;yy=.83
        cylinder('gas bottle',(xx,yy,.74),.105,.80,m['teal' if j else 'rust'],vertices=24,bevel=.03)
        sphere('bottle shoulder',(xx,yy,1.13),(.105,.105,.105),m['teal' if j else 'rust'],segments=20,rings=12)
        cylinder('bottle valve',(xx,yy,1.25),.036,.13,m['brass'],vertices=12,bevel=.008)
    cable('gas hose',[(-.3,.83,1.25),(-.65,.62,1.0),(-.65,.51,.32),(-.2,.20,.28),(.2,.17,.4)],.018,m['rubber'])
    # A reclaimed tire with sidewall rings and inset spokes.
    torus('spare tire',(-2.15,.32,.62),.285,.105,m['rubber'],rotation=(math.pi/2,0,.12),major_segments=36,minor_segments=12)
    cylinder('spare hub',(-2.15,.31,.62),.20,.14,m['iron'],rotation=(math.pi/2,0,0),vertices=24,bevel=.016)
    for a in [j*math.tau/12 for j in range(12)]:
        box('tire tread',(-2.15+.373*math.sin(a),.32,.62+.373*math.cos(a)),(.085,.15,.033),m['rubber'],rotation=(0,a,0),bevel=.008)
    # A small outside side bench with canisters.
    box('side shelf',(2.24,.30,1.38),(.48,1.2,.07),m['wood'],bevel=.018)
    for yy in [-.08,.27,.60]:
        cylinder('side canister',(2.24,yy,1.54),.075,.26,m['brass'],vertices=16,bevel=.01)
    # Small debris is clustered at edges; entrance stays clear.
    for j,(x,y) in enumerate([(-2.35,-.63),(-1.98,1.90),(.4,1.93),(2.38,-.3)]):
        box('loose salvage offcut',(x,y,.31),(.20,.13,.09),m['rust'],rotation=(0,.1,j),bevel=.014)


def point(obj,target):obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()


def setup_render(resolution,samples):
    scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=samples
    scene.cycles.use_denoising=True;scene.cycles.seed=42;scene.cycles.max_bounces=6
    scene.render.threads_mode='FIXED';scene.render.threads=8
    scene.render.resolution_x=resolution;scene.render.resolution_y=resolution;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG';scene.render.film_transparent=False
    scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast'
    world=scene.world or bpy.data.worlds.new('World');scene.world=world;world.use_nodes=True
    world.node_tree.nodes['Background'].inputs['Color'].default_value=(.055,.09,.12,1)
    world.node_tree.nodes['Background'].inputs['Strength'].default_value=.35
    floor=solid('render floor','#122f39',rough=.92)
    box('REVIEW ground',(0,0,-.05),(200,200,.1),floor,bevel=0)
    for name,loc,color,power,size in [('KEY',(-3,-4,8),(1,.86,.64),1250,5),('RIM',(4,3,7),(.45,.73,1),1750,4),('FILL',(2,-4,5),(.63,.80,1),350,5)]:
        data=bpy.data.lights.new(name,'AREA');data.energy=power;data.color=color;data.shape='DISK';data.size=size
        ob=bpy.data.objects.new('REVIEW '+name,data);bpy.context.collection.objects.link(ob);ob.location=loc;point(ob,(0,0,1.6))
    data=bpy.data.cameras.new('Review camera');cam=bpy.data.objects.new('REVIEW camera',data);bpy.context.collection.objects.link(cam);scene.camera=cam
    cam.data.type='ORTHO';cam.data.ortho_scale=7.3;cam.location=(7,-11,7.0);point(cam,(0,.10,2.2))
    return cam


def clean_mesh(obj):
    """Remove sub-micron-area collapsed triangles after evaluated modifiers.

    This is an export repair, not relaxed validation. UVs and material indices
    survive triangulation; meaningful surfaces are preserved.
    """
    bm=bmesh.new();bm.from_mesh(obj.data)
    bmesh.ops.triangulate(bm,faces=list(bm.faces))
    bad=[f for f in bm.faces if f.calc_area()<5e-10]
    if bad:bmesh.ops.delete(bm,geom=bad,context='FACES_ONLY')
    loose=[v for v in bm.verts if not v.link_faces]
    if loose:bmesh.ops.delete(bm,geom=loose,context='VERTS')
    bm.to_mesh(obj.data);bm.free();obj.data.update()
    return len(bad)


def convert_and_batch():
    # Preserve editable objects in .blend; GLBs batch geometry by material for
    # practical draw-call counts. All modifiers become actual exported geometry.
    candidates=[o for o in bpy.context.scene.objects if o.type in ('MESH','CURVE')]
    deps=bpy.context.evaluated_depsgraph_get();batch={}
    for obj in candidates:
        ev=obj.evaluated_get(deps);data=bpy.data.meshes.new_from_object(ev,preserve_all_data_layers=True,depsgraph=deps)
        if not data.materials:continue
        mat=data.materials[0];group=batch.setdefault(mat.name,[])
        clone=bpy.data.objects.new('baked '+obj.name,data);bpy.context.collection.objects.link(clone);clone.matrix_world=obj.matrix_world.copy();group.append(clone)
        obj.hide_render=True;obj.hide_set(True)
    results=[]
    for name,group in batch.items():
        select_only(group);bpy.ops.object.join();ob=bpy.context.object;ob.name='workshop / '+name;ob['collapsed_triangles_removed']=clean_mesh(ob);results.append(ob)
    return results


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--font',type=Path,default=Path('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'))
    p.add_argument('--resolution',type=int,default=1100);p.add_argument('--samples',type=int,default=64);p.add_argument('--preview-only',action='store_true');p.add_argument('--source-blend',type=Path);args=p.parse_args()
    out=args.output.resolve()
    if out.exists():raise SystemExit('Refusing to overwrite output; choose a new iteration directory')
    if not args.font.is_file():raise SystemExit('Provide an available font file with --font')
    out.mkdir(parents=True)
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    if args.source_blend:
        bpy.ops.wm.open_mainfile(filepath=str(args.source_blend.resolve()))
    else:
        m=materials(out,args.font)
        for f in [foundation,main_structure,roof_canopy,pipes_and_roof,workshop_interior,foreground]:
            print('BUILD',f.__name__,flush=True);f(m)
        objects=[o for o in bpy.context.scene.objects if o.type=='MESH'];physically_scaled_uv(objects)
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'workshop-editable.blend'))
    if args.preview_only:
        cam=setup_render(args.resolution,args.samples)
        bpy.context.scene.render.filepath=str(out/'workshop-source.png');bpy.ops.render.render(write_still=True)
        return
    # Exclude review staging from the asset and retain practical light positions
    # in metadata rather than exporting an inseparable studio rig.
    for o in list(bpy.context.scene.objects):
        if o.name.startswith('REVIEW '):bpy.data.objects.remove(o,do_unlink=True)
    lights=[{'name':o.name,'position_source_z_up':list(o.location),'color':list(o.data.color),'watts':o.data.energy} for o in bpy.context.scene.objects if o.type=='LIGHT']
    batches=convert_and_batch();export_glb(out/'improvised-workshop.glb',batches)
    stats={'collapsed_triangles_removed':sum(o.get('collapsed_triangles_removed',0) for o in batches),'batches':len(batches),'triangles':sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in batches)}
    # Retain source high model and separately decimate a lower-detail version.
    for ob in batches:
        if len(ob.data.polygons)>20:
            mod=ob.modifiers.new('RTS lower detail','DECIMATE');mod.ratio=.36
            select_only([ob]);bpy.ops.object.modifier_apply(modifier=mod.name)
            clean_mesh(ob)
    export_glb(out/'improvised-workshop-lod1.glb',batches)
    from verify_rts_workshop import verify
    inspections={name:verify(out/name) for name in ['improvised-workshop.glb','improvised-workshop-lod1.glb']}
    assert inspections['improvised-workshop-lod1.glb']['triangles']<inspections['improvised-workshop.glb']['triangles']
    (out/'glb-inspection.json').write_text(json.dumps(inspections,indent=2)+'\n')
    # Independent import for truthful final renders; no source-only shader tricks.
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    for o in list(bpy.data.objects):bpy.data.objects.remove(o,do_unlink=True)
    bpy.ops.import_scene.gltf(filepath=str(out/'improvised-workshop.glb'))
    imported=[o for o in bpy.context.scene.objects if o.type=='MESH'];assert imported
    # Restore practical light positions recorded from authored source.
    for l in lights:
        data=bpy.data.lights.new(l['name'],'POINT');data.energy=l['watts'];data.color=l['color'];data.shadow_soft_size=.13
        ob=bpy.data.objects.new(l['name'],data);bpy.context.collection.objects.link(ob);ob.location=l['position_source_z_up']
    cam=setup_render(args.resolution,args.samples)
    views=[]
    for name,loc,target,scale in [('hero',(7,-11,7),(0,.10,2.2),7.3),('rear',(-8,10,7),(0,.1,2.1),7.3),('detail',(4,-9,4.8),(.6,-.2,1.7),4.4)]:
        cam.location=loc;point(cam,target);cam.data.ortho_scale=scale
        bpy.context.scene.render.filepath=str(out/f'workshop-{name}.png');bpy.ops.render.render(write_still=True);views.append(f'workshop-{name}.png')
    digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    report={'schema':'axm.rts-workshop-polish/v0.1','asset':'improvised-workshop','reference':'1000000415.png','reference_sha256':'4e154be2ff7451318b09abc6d2153297ab9f1b51bae4ad94599d5901dfd7368f','geometry':stats,
      'units':'meters','glb_up':'Y','glb_forward':'+Z','source_up':'Z','source_forward':'-Y','source_runtime':bpy.app.version_string,
      'source_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),Path(__file__).with_name('axm_salvage_construction.py'),Path(__file__).with_name('axm_salvage_surfaces.py')]},'font_sha256':digest(args.font),'fresh_import_meshes':len(imported),'practical_lights':lights,'render_views':views,
      'artifacts':{f.name:{'bytes':f.stat().st_size,'sha256':digest(f)} for f in out.iterdir() if f.is_file()},
      'scope':'Reference-led authored 3D interpretation. Fresh GLB import with Cycles CPU render. No target RTS integration or performance certification. Review ground, camera and studio lighting are not asset geometry.'}
    (out/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print('COMPLETE',json.dumps(stats),flush=True)

if __name__=='__main__':main()
