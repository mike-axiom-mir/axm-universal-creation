"""Reference-directed hovering AXM companion; real geometry and baked skin."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import random
import bpy
from mathutils import Vector
from axm_chaos_hero import Hero
from axm_hero_motion import rig,clean_triangles
from axm_oops_character import reset_pose
import axm_blender_forge as geo
from axm_salvage_surfaces import solid

CLIPS=[('Hover_Idle',2,True),('Follow_Flight',1,True),('Inspect',2,True),
       ('Wave',2,True),('Repair',1.5,True),('Duck_Celebrate',2,True),
       ('Startle',1,False),('Power_Down',2,False)]


def front(x,z):
    return -.205*math.sqrt(max(.08,1-(x/.25)**2-(z/.245)**2))-.009


def build(h):
    h.bone('Root',(0,0,0),(0,0,.1))
    h.bone('Body',(0,0,0),(0,0,.1),'Root')
    h.bone('Rotor',(0,0,.29),(0,0,.36),'Body')
    h.bone('Thruster',(0,0,-.24),(0,0,-.32),'Body')
    for side,s in [('L',-1),('R',1)]:
        h.bone('Arm.'+side,(s*.225,0,-.07),(s*.30,-.03,-.12),'Body')
        h.bone('Hand.'+side,(s*.30,-.03,-.12),(s*.36,-.08,-.08),'Arm.'+side)
        h.bone('Eye.'+side,(s*.075,-.20,.025),(s*.075,-.20,.075),'Body')
    h.bone('Duck',(-.34,-.14,-.14),(-.34,-.14,-.04),'Hand.L')
    h.bone('Tool',(.34,-.07,-.06),(.34,-.07,.16),'Hand.R')
    h.bone('Sign',(.34,-.07,-.11),(.34,-.07,-.36),'Hand.R')
    h.current='Body'
    shell=h.ball('Egg-shaped ivory hull',(0,0,0),(.25,.205,.245),'ivory',segments=64,rings=48)
    cut=h.box('Temporary visor cut',(0,-.22,.025),(.366,.28,.284),'iron',.068)
    geo.select_only([shell]);bpy.context.view_layer.objects.active=shell
    m=shell.modifiers.new('Recessed screen aperture','BOOLEAN');m.operation='DIFFERENCE';m.object=cut
    bpy.ops.object.modifier_apply(modifier=m.name);h.parts.remove(cut);bpy.data.objects.remove(cut,do_unlink=True)
    # Curved rounded-square screen and concentric structural bezel.
    n=96;rows=14;vs=[(0,front(0,.025),.025)];fs=[]
    edge=[]
    for j in range(1,rows+1):
        r=j/rows
        for i in range(n):
            a=math.tau*i/n;c,s=math.cos(a),math.sin(a)
            x=.179*math.copysign(abs(c)**.5,c)*r;z=.025+.138*math.copysign(abs(s)**.5,s)*r
            vs.append((x,front(x,z),z))
            if j==rows:edge.append((x,front(x,z)-.002,z))
    for i in range(n):fs.append((0,1+i,1+(i+1)%n))
    for j in range(rows-1):
        for i in range(n):a=1+j*n+i;b=1+j*n+(i+1)%n;fs.append((a,a+n,b+n,b))
    h.mesh('Convex smoked visor',vs,fs,'lens')
    h.line('Inset graphite gasket',edge+[edge[0]],.014,'iron')
    h.line('Machined visor bezel',[(x*1.04,y+.004,.025+(z-.025)*1.045) for x,y,z in edge+[edge[0]]],.006,'teal')
    for s,side in [(-1,'L'),(1,'R')]:
        pts=[(-.038,-.014),(-.011,.059),(.011,.059),(.038,-.014),(.020,-.014),(0,.039),(-.020,-.014)]
        vs=[(s*.075+x,front(s*.075+x,z)-.014,z) for x,z in pts]
        ob=h.mesh('Angular cyan happy eye '+side,vs,[tuple(range(len(vs)))],'cyan','Eye.'+side,smooth=False)
        m=ob.modifiers.new('Raised eye glyph','SOLIDIFY');m.thickness=.003
    for x,z in [(-.145,.12),(.145,.12),(-.14,-.08),(.14,-.08)]:
        h.ball('Screen status LED',(x,front(x,z)-.012,z),(.004,.003,.004),'cyan',segments=12,rings=8)
    # Real seams, shell fasteners and localized paint chips on the curved hull.
    for a in [-.9,.9,2.5]:
        pts=[]
        for i in range(33):
            t=.2+i/32*2.7;pts.append((.251*math.sin(t)*math.sin(a),.207*math.sin(t)*math.cos(a),.246*math.cos(t)))
        h.line('Hull assembly seam',pts,.0018,'iron')
    rng=random.Random(47147)
    for i in range(140):
        a=rng.uniform(0,math.tau);z=rng.uniform(-.92,.92);q=math.sqrt(1-z*z)
        p=Vector((.251*q*math.cos(a),.206*q*math.sin(a),.246*z))
        if p.y<-.05 and abs(p.x)<.194 and -.132<p.z<.18:continue
        normal=Vector((p.x/.251**2,p.y/.206**2,p.z/.246**2)).normalized()
        t=normal.cross(Vector((0,0,1))).normalized();v=normal.cross(t)
        size=rng.uniform(.0015,.0055);pts=[tuple(p+t*math.cos(k*math.tau/5)*size+v*math.sin(k*math.tau/5)*size*.5) for k in range(5)]
        h.mesh('Exposed paint chip',pts,[tuple(range(5))],'iron')
    for x,z in [(-.185,.14),(.185,.14),(-.145,-.175),(.145,-.175),(0,.207)]:
        y=front(x,z);h.bolt('Hull fastener',(x,y,z),.006)
    h.logo('Gold AXM hull emblem',(0,-.159,-.186),.070,'brass')
    for s in [-1,1]:
        h.cyl('Side bearing',(s*.246,0,.005),.065,.035,'iron',(s,0,0),48)
        h.ring('Side brass collar',(s*.266,0,.005),.052,.006,'brass',(s,0,0))
        h.cyl('Side bearing cap',(s*.269,0,.005),.040,.009,'steel',(s,0,0),32)
    h.plate('Rear battery access',(0,.205,.005),(.19,.018,.15),'teal')
    for z in [-.05,-.025,0,.025,.05]:h.box('Rear vent',(0,.218,z),(.13,.010,.007),'iron',.002)
    # Rotor with four swept, cambered blades and exposed mast hardware.
    h.cyl('Rotor base',(0,0,.245),.043,.028,'iron',v=48)
    h.cyl('Rotor mast',(0,0,.285),.015,.07,'steel')
    h.current='Rotor';h.ball('Rotor yellow hub',(0,0,.33),(.036,.036,.024),'yellow')
    for k in range(4):
        a=k*math.pi/2;pts=[]
        for radius,side,z in [(.028,-.009,.326),(.27,-.020,.335),(.32,.002,.336),(.12,.016,.332),(.028,.009,.326)]:
            pts.append((radius*math.cos(a)-side*math.sin(a),radius*math.sin(a)+side*math.cos(a),z))
        ob=h.mesh('Swept rotor blade',pts,[(0,1,2,3,4)],'steel');sol=ob.modifiers.new('Blade gauge','SOLIDIFY');sol.thickness=.002
    # Articulated, visibly mechanical arms and fingers.
    for s,side in [(-1,'L'),(1,'R')]:
        h.current='Arm.'+side
        h.ball('Shoulder joint',(s*.22,0,-.075),(.038,.038,.038),'iron')
        h.beam('Arm piston',(s*.23,0,-.075),(s*.30,-.03,-.12),.022,'steel')
        h.beam('Arm yellow guard',(s*.23,-.018,-.07),(s*.286,-.048,-.112),.012,'yellow')
        h.current='Hand.'+side;h.ball('Wrist joint',(s*.30,-.03,-.12),(.031,.03,.031),'iron')
        h.box('Palm',(s*.34,-.07,-.085),(.064,.045,.058),'iron',.014)
        for i in range(3):
            x=s*.34+(i-1)*.020
            h.beam('Finger knuckle',(x,-.095,-.107),(x,-.113,-.07),.010,'steel')
            h.ball('Finger tip',(x,-.107,-.056),(.009,.012,.014),'iron')
    h.current='Duck';h.duck((-.35,-.155,-.105),1.65,'Duck')
    h.ring('Duck crown band',(-.35,-.168,-.005),.027,.005,'brass',(0,0,1),'Duck')
    for k in range(5):
        a=k*math.tau/5;x=-.35+.026*math.cos(a);y=-.168+.026*math.sin(a)
        h.beam('Crown point',(x,y,-.006),(x*0+(-.35+.032*math.cos(a)),-.168+.032*math.sin(a),.02),.004,'brass')
        h.ball('Crown bead',(-.35+.032*math.cos(a),-.168+.032*math.sin(a),.022),(.005,.005,.005),'brass',segments=12,rings=8)
    h.current='Tool';x=.34;y=-.07
    h.box('Wrench handle',(x,y,.045),(.027,.020,.23),'brass',.007)
    h.ring('Wrench handle loop',(x,y,-.086),.025,.007,'steel')
    pts=[(-.040,0),(-.052,.049),(-.041,.076),(-.027,.076),(-.027,.035),(.027,.035),(.027,.076),(.041,.076),(.052,.049),(.040,0)]
    ob=h.mesh('Open wrench head',[(x+a,y,.16+b) for a,b in pts],[tuple(range(len(pts)))],'steel',smooth=False)
    m=ob.modifiers.new('Forged tool thickness','SOLIDIFY');m.thickness=.018
    m=ob.modifiers.new('Wrench edge bevel','BEVEL');m.width=.003;m.segments=3
    h.logo('Wrench AXM',(x,y-.012,.181),.03,'cyan')
    h.current='Sign'
    for start,x in [((.319,-.07,-.115),.26),((.36,-.06,-.10),.42)]:
        h.line('Sign hanging cord',[start,(x,-.016,-.25)],.0025,'leather')
    vs=[(.235,-.02,-.24),(.445,-.02,-.24),(.45,-.01,-.51),(.345,-.015,-.485),(.24,-.02,-.52)]
    ob=h.mesh('Crooked canvas sign',vs,[(0,1,2,3,4)],'ivory');m=ob.modifiers.new('Sign gauge','SOLIDIFY');m.thickness=.004
    h.text('Sign joke','GOOD\nTOOLS\nWORSE\nCHOICES',(.341,-.026,-.357),.028,'ink','Sign')
    h.smile((.343,-.027,-.45),.016,'Sign')
    h.current='Body'
    h.cyl('Thruster housing',(0,0,-.235),.077,.060,'iron',v=48)
    h.ring('Thruster heat collar',(0,0,-.26),.065,.007,'steel',(0,0,1))
    for a in range(8):
        t=a*math.tau/8;h.box('Cooling vane',(.068*math.cos(t),.068*math.sin(t),-.239),(.010,.010,.055),'brass',.002)
    h.current='Thruster'
    h.mat['ion']=solid('Globe blue ion plume','#1274ff',0,.25,2)
    h.cyl('Blue engine core',(0,0,-.272),.049,.01,'cyan',v=40)
    for k in range(5):
        a=k*math.tau/5
        ob=geo.cone('Ion exhaust',(.029*math.cos(a),.029*math.sin(a),-.325),.002,.013,.10,h.mat['ion'],vertices=16)
        h.bind(ob,'Thruster')


def animate(arm):
    rows=[];scene=bpy.context.scene;scene.render.fps=30
    for name,seconds,loop in CLIPS:
        arm.animation_data_create();action=bpy.data.actions.new(name);arm.animation_data.action=action;action.use_fake_user=True
        end=round(seconds*30)
        for frame in range(end+1):
            reset_pose(arm);b=arm.pose.bones;t=frame/end;p=math.tau*t;e=math.sin(math.pi*t)**2
            b['Root'].location.y=.018*math.sin(p)
            b['Body'].rotation_euler.x=.025*math.sin(p)
            b['Rotor'].rotation_euler.y=math.tau*4*seconds*t
            b['Sign'].rotation_euler.x=.09*math.sin(p+.4)
            b['Sign'].rotation_euler.z=.035*math.sin(p)
            b['Thruster'].scale=(1,1+.15*math.sin(p*2),1)
            blink=max(0,1-abs(t-.77)/.06)
            for side in ['L','R']:b['Eye.'+side].scale.y=1-.92*blink
            if name=='Follow_Flight':b['Body'].rotation_euler.x=.18+.025*math.sin(p);b['Sign'].rotation_euler.x=.22+.05*math.sin(p)
            if name=='Inspect':b['Body'].rotation_euler.z=.30*math.sin(p);b['Body'].rotation_euler.x=.09*math.sin(p)
            if name=='Wave':b['Arm.R'].rotation_euler.y=.30*e;b['Hand.R'].rotation_euler.z=.35*math.sin(p*2)*e
            if name=='Repair':b['Arm.R'].rotation_euler.x=.28*math.sin(p);b['Tool'].rotation_euler.x=.30*math.sin(p)
            if name=='Duck_Celebrate':b['Arm.L'].rotation_euler.y=-.40*e;b['Duck'].rotation_euler.y=.16*math.sin(p*2)
            if name=='Startle':b['Root'].location.y=.10*e;b['Body'].rotation_euler.x=-.16*e
            if name=='Power_Down':
                b['Root'].location.y=-.12*t;b['Body'].rotation_euler.x=.18*t
                b['Rotor'].rotation_euler.y=math.tau*4*seconds*(t-.5*t*t)
                b['Thruster'].scale=(1-.9*t,1-.95*t,1-.9*t)
                for side in ['L','R']:b['Eye.'+side].scale.y=1-.92*t
            for bone in b:
                for channel in ['location','rotation_euler','scale']:bone.keyframe_insert(channel,frame=frame,group=bone.name)
        for fc in action.fcurves:
            for k in fc.keyframe_points:k.interpolation='LINEAR'
        rows.append({'name':name,'seconds':seconds,'frames':end+1,'fps':30,'loop':loop})
    arm.animation_data.action=None;reset_pose(arm);return rows


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);args=p.parse_args();out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    bpy.ops.wm.read_factory_settings(use_empty=True);h=Hero(out);build(h);arm,mesh=rig(h);arm.name='AXM_Globe_Rig';mesh.name='AXM_Globe_Companion'
    arm['binding']='Rigid articulated hull, arms, eyes, rotor, duck, tool and hinged sign.'
    clips=animate(arm);exports={}
    for name,ratio in [('AXM_Globe_Companion',1),('AXM_Globe_Companion_LOD1',.45)]:
        target=mesh
        if ratio<1:
            target=mesh.copy();target.data=mesh.data.copy();bpy.context.collection.objects.link(target);target.modifiers.clear()
            geo.select_only([target]);bpy.context.view_layer.objects.active=target;m=target.modifiers.new('LOD','DECIMATE');m.ratio=ratio;bpy.ops.object.modifier_apply(modifier=m.name);clean_triangles(target)
            m=target.modifiers.new('Skin','ARMATURE');m.object=arm
        geo.select_only([arm,target]);bpy.context.view_layer.objects.active=arm;path=out/(name+'.glb')
        bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,export_skins=True,export_animations=True,export_animation_mode='ACTIONS',export_force_sampling=True,export_yup=True,export_extras=True,export_tangents=True)
        target.data.calc_loop_triangles();exports[name]={'path':path.name,'triangles':len(target.data.loop_triangles),'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
        if ratio<1:bpy.data.objects.remove(target,do_unlink=True)
    arm.animation_data.action=bpy.data.actions['Hover_Idle'];bpy.context.scene.frame_set(0)
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'AXM_Globe_Companion.blend'),compress=True)
    data={'asset_id':'axm-globe-companion','exports':exports,'bones':[{'name':n,'parent':v[2]} for n,v in h.bones.items()],'animations':clips,
          'origin':'Body centre; metres; glTF Y-up, +Z forward.','hero_offset_gltf_m':[.90,2.30,0],
          'integration':'Play Hover_Idle or Follow_Flight while an engine positions the root beside the hero. No target-game AI/controller installed.',
          'reference':'1000000471.png supplied illustration; hidden rear surfaces interpreted.',
          'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (out/'companion-manifest.json').write_text(json.dumps(data,indent=2)+'\n');print('COMPANION_COMPLETE',flush=True)


if __name__=='__main__':main()
