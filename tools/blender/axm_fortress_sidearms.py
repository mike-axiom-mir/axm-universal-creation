"""Original identity sidearms, explicit glTF grip contract and bounded clearance probes."""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
import bpy
import bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).resolve().parent))
import axm_fortress_defender as s
f=s.f;d=s.d;w=s.w
G=(0,.07,-.14);SUPPORT=(.055,.07,.08)
box=s.box;cylinder=s.cylinder;xyz=s.xyz


def materials(accent,energy):
    f.M={k:f.material(k,c,m,e) for k,c,m,e in [
      ('Ceramic',(.52,.60,.61),.26,0),('Steel',(.13,.20,.24),.78,0),
      ('Dark',(.025,.039,.045),.40,0),('Rubber',(.016,.022,.026),.03,0),
      ('Accent',accent,.43,0),('Energy',energy,.15,1.3)]}
    f.M['Rubber'].node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.82
    f.M['Ceramic'].node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.36


def empty(name,p=(0,0,0),parent=None):return f.empty(name,xyz(p),parent)


def annulus(name,p,outer,inner,depth,mat,parent,axis='Y',steps=32):
    verts=[]
    for along in (-depth/2,depth/2):
        for radius in (outer,inner):
            for i in range(steps):
                a=2*math.pi*i/steps;x=radius*math.cos(a);y=radius*math.sin(a)
                verts.append(xyz((x,along,y) if axis=='Y' else (x,y,along)))
    faces=[];n=steps
    for i in range(n):
        j=(i+1)%n;faces.extend([(i,j,n+j,n+i),(2*n+i,3*n+i,3*n+j,2*n+j),(i,2*n+i,2*n+j,j),(n+i,n+j,3*n+j,3*n+i)])
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update()
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(mesh);bm.free()
    o=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(o);o.location=xyz(p)
    return s.bevel(f.finish(o,name,mat,parent),.0015)


def common(root):
    empty('Grip',G,root);empty('SupportGrip',SUPPORT,root)
    # The fixed gloves use the grip position plus 8 cm Y as the wrist position.
    # Upper supports sweep forward around those wrist seals.
    for label,p,h in [('Primary',G,.18),('Support',SUPPORT,.125)]:
        x,y,z=p
        s.loft(label+'Grip',[(-.055 if label=='Primary' else -.015,.050,.043,z),(.085,.052,.045,z),(.108,.044,.040,z+.005)],'Rubber',root,.004).location.x=x
        for j in range(4):
            yy=.015+j*.023
            box(label+'Tread',(x,yy,z-.024),(.044,.007,.007),'Rubber',root,.001)
        # A front knuckle bow carries the receiver load around the fixed fist;
        # its heel connection passes below the fingers, not through the wrist.
        reach=.13 if label=='Primary' else .083
        s.loft(label+'Neck',[(-.013,.032,reach+.028,z+reach/2),(.003,.032,reach+.028,z+reach/2),(.026,.026,.022,z+reach),(.207,.034,.024,z+reach)],'Steel',root,.003).location.x=x
        box(label+'Heel',(x,-.055 if label=='Primary' else -.02,z),(.057,.024,.054),'Ceramic',root,.005)
    # Open trigger pocket ahead of the rear hand, clear of the support glove.
    box('TriggerGuardFloor',(0,-.005,-.060),(.022,.018,.135),'Steel',root,.003)
    box('TriggerGuardFront',(0,.046,.004),(.022,.11,.018),'Steel',root,.003)
    box('TriggerLever',(0,.067,-.057),(.012,.043,.012),'Dark',root,.002)
    box('TriggerHingeLink',(0,.093,-.033),(.014,.014,.062),'Dark',root,.002)


def sight(root,y,z=-.045,base=.295):
    empty('Sight',(0,y,z),root)
    for sign in (-1,1):
        top=y-.044
        box('SightPedestal',(sign*.033,(base+top)/2,z),(.015,top-base+.006,.036),'Steel',root,.002)
        box('SightEar',(sign*.033,y-.025,z),(.014,.047,.036),'Dark',root,.003)
        box('SightIndex',(sign*.033,y-.004,z-.020),(.008,.008,.006),'Energy',root,.001)


def pinprick():
    root=empty('PinprickRoot');common(root)
    box('Receiver',(0,.227,.09),(.133,.050,.35),'Steel',root,.016)
    box('RearCeramicBreech',(0,.272,-.036),(.135,.066,.092),'Ceramic',root,.014)
    for sign in (-1,1):
        box('BreechSeam',(sign*.073,.259,.025),(.012,.034,.15),'Dark',root,.003)
        box('RepulsionRail',(sign*.051,.328,.387),(.036,.058,.360),'Ceramic',root,.006)
        box('RailWinding',(sign*.051,.358,.377),(.014,.010,.272),'Energy',root,.002)
        box('PinJaw',(sign*.051,.327,.566),(.047,.066,.026),'Steel',root,.005)
    cylinder('PinAxis',(0,.340,.361),.017,.418,'Dark',root,'Z',16)
    cylinder('PinEmitter',(0,.340,.572),.011,.017,'Energy',root,'Z',16)
    empty('Muzzle',(0,.340,.592),root)
    # Exposed eight-pole accumulator spins around the launch direction (+Z).
    rotor=empty('CoilRotor',(0,.340,.105),root)
    for i in range(8):
        a=i*math.pi/4
        o=box('MagnetShoe',(.064*math.cos(a),.064*math.sin(a),0),(.024,.026,.125),'Accent',rotor,.004);o.rotation_euler.y=-a
        o=box('CoilIndex',(.079*math.cos(a),.079*math.sin(a),0),(.007,.018,.080),'Energy',rotor,.001);o.rotation_euler.y=-a
    for z in (.026,.184):annulus('AccumulatorEnd',(0,.340,z),.088,.025,.016,'Steel',root,'Z')
    for z in (.026,.184):box('StatorCradle',(0,.265,z),(.090,.035,.027),'Steel',root,.004)
    for sign in (-1,1):box('RailFoot',(sign*.051,.278,.244),(.035,.072,.055),'Steel',root,.004)
    box('RailCrossTie',(0,.329,.233),(.140,.026,.030),'Steel',root,.004)
    # A side cassette exposes a three-pin accumulation ladder.
    box('PinCassette',(-.106,.288,.045),(.053,.076,.197),'Dark',root,.008)
    box('CassetteMount',(-.076,.275,-.031),(.035,.038,.038),'Steel',root,.004)
    for i in range(3):
        box('CassettePin',(-.135,.291,-.024+i*.063),(.009,.051,.017),'Ceramic',root,.002)
        box('PinCharge',(-.142,.313,-.024+i*.063),(.009,.011,.018),'Energy',root,.001)
    sight(root,.465,-.036)
    return root,{'part':'CoilRotor','axis':'local Z','motion':'rotation','samples':[i*math.pi/8 for i in range(16)]}


def hot_pocket():
    root=empty('HotPocketRoot');common(root)
    box('ThermalKeel',(0,.227,.126),(.198,.062,.428),'Steel',root,.016)
    box('RearControlBlock',(0,.273,-.031),(.187,.071,.112),'Ceramic',root,.017)
    cylinder('HeatBattery',(0,.389,.171),.107,.247,'Dark',root,'Y',24)
    cylinder('BatteryFoot',(0,.265,.171),.097,.040,'Steel',root,'Y',24)
    cylinder('BatteryCrown',(0,.524,.171),.111,.028,'Ceramic',root,'Y',24)
    annulus('CrownHeatBand',(0,.543,.171),.091,.063,.011,'Accent',root)
    for sign in (-1,1):
        box('BatterySpine',(sign*.102,.389,.171),(.020,.203,.080),'Ceramic',root,.005)
    vents=empty('HeatVents',(0,.385,.171),root)
    for sign in (-1,1):
        for i in range(7):box('VentRib',(sign*.133,-.078+i*.026,0),(.027,.012,.146),'Accent',vents,.003)
        annulus('VentCarrier',(sign*.133,0,-.085),.017,.009,.192,'Steel',vents)
        cylinder('VentGuide',(sign*.133,.394,.086),.0065,.292,'Steel',root,'Y',12)
        box('GuideUpperAnchor',(sign*.113,.544,.086),(.061,.016,.042),'Ceramic',root,.003)
        box('GuideLowerAnchor',(sign*.121,.259,.086),(.067,.027,.046),'Steel',root,.003)
    # A blunt bifurcated heat mouth replaces a long barrel.
    for sign in (-1,1):
        box('MouthCheek',(sign*.096,.315,.416),(.047,.142,.147),'Ceramic',root,.015)
        box('VentCheekSeal',(sign*.074,.315,.426),(.011,.087,.106),'Dark',root,.002)
    box('HeatThroat',(0,.315,.410),(.132,.075,.150),'Dark',root,.009)
    box('MouthRiser',(0,.277,.335),(.170,.075,.058),'Steel',root,.006)
    for i in range(5):box('HeatSlot',(-.044+i*.022,.315,.488),(.009,.047,.008),'Energy',root,.001)
    box('MouthUpper',(0,.393,.420),(.22,.023,.157),'Steel',root,.005)
    box('MouthLower',(0,.242,.430),(.21,.021,.143),'Steel',root,.004)
    empty('Muzzle',(0,.315,.507),root)
    box('TemperaturePanel',(-.096,.284,-.013),(.010,.045,.077),'Dark',root,.003)
    for i in range(4):box('HeatLadder',(-.104,.281,-.039+i*.017),(.007,.010+i*.005,.009),'Energy',root,.001)
    sight(root,.588,-.025)
    return root,{'part':'HeatVents','axis':'local Y','motion':'translation','samples':[0,.0125,.025],'travel_m':[0,.025]}


def return_ticket():
    root=empty('ReturnTicketRoot');common(root)
    box('CatchKeel',(0,.226,.135),(.295,.061,.452),'Steel',root,.016)
    box('RearCatchBlock',(0,.268,-.023),(.261,.045,.120),'Ceramic',root,.010)
    annulus('CatchStator',(0,.271,.210),.205,.160,.030,'Steel',root)
    rotor=empty('DiscRotor',(0,.314,.210),root)
    cylinder('ReturnDisc',(0,0,0),.144,.018,'Accent',rotor,'Y',40)
    annulus('DiscFieldRim',(0,.004,0),.158,.148,.013,'Energy',rotor,steps=40)
    annulus('DiscInnerTrack',(0,.013,0),.104,.086,.008,'Steel',rotor)
    for i in range(4):
        a=math.pi/4+i*math.pi/2
        o=box('ReturnSpoke',(.058*math.sin(a),.014,.058*math.cos(a)),(.018,.009,.063),'Ceramic',rotor,.002);o.rotation_euler.z=-a
    # Open-front catcher surrounds the orbit, without entering its swept disc.
    for i in range(15):
        a=math.radians(43+i*274/14)
        o=box('CatchJaw',(.185*math.sin(a),.302,.210+.185*math.cos(a)),(.027,.090,.047),'Ceramic' if i%3 else 'Accent',root,.005);o.rotation_euler.z=-a
    for sign in (-1,1):
        box('ReturnGuide',(sign*.144,.301,.428),(.044,.064,.185),'Steel',root,.006)
        box('CatchField',(sign*.133,.333,.436),(.014,.010,.124),'Energy',root,.002)
        o=box('OuterCatcherWing',(sign*.214,.284,.336),(.080,.039,.19),'Ceramic',root,.009);o.rotation_euler.z=sign*math.radians(13)
        box('ReturnSensor',(sign*.111,.335,-.042),(.031,.062,.041),'Dark',root,.006)
        box('SensorSocket',(sign*.111,.300,-.042),(.039,.035,.048),'Steel',root,.004)
        box('SensorFace',(sign*.111,.341,-.065),(.017,.021,.006),'Energy',root,.002)
    box('CatchThroat',(0,.250,.444),(.243,.022,.137),'Dark',root,.004)
    empty('Muzzle',(0,.314,.535),root);sight(root,.433,-.04)
    return root,{'part':'DiscRotor','axis':'local Y','motion':'rotation','samples':[i*math.pi/8 for i in range(16)]}


SPECS={
 'pinprick':(pinprick,(.26,.51,.075),(.38,.85,.13)),
 'hot-pocket':(hot_pocket,(.78,.20,.035),(.98,.26,.025)),
 'return-ticket':(return_ticket,(.38,.065,.52),(.64,.12,.93))}


def tree(o):return BVHTree.FromPolygons([o.matrix_world@v.co for v in o.data.vertices],[list(p.vertices) for p in o.data.polygons])


def motion_check(spec):
    moving=bpy.data.objects[spec['part']];meshes=[o for o in bpy.context.scene.objects if o.type=='MESH'];static=[o for o in meshes if o.parent!=moving];animated=[o for o in meshes if o.parent==moving]
    originals=(moving.location.copy(),moving.rotation_euler.copy());rows=[]
    for value in spec['samples']:
        moving.location=originals[0];moving.rotation_euler=originals[1]
        if spec['motion']=='rotation':moving.rotation_euler[2 if spec['axis']=='local Y' else 1]=value
        else:moving.location.z+=value
        bpy.context.view_layer.update();trees={o:tree(o) for o in meshes};hits=[]
        for a in animated:
            for b in static:
                pairs=trees[a].overlap(trees[b])
                if pairs:hits.append({'moving':a.name,'static':b.name,'triangle_pairs':len(pairs)})
        rows.append({'value':value,'intersections':hits})
    moving.location,moving.rotation_euler=originals;bpy.context.view_layer.update()
    return rows


def axis_checks():
    rows={};direction=Vector(xyz((0,0,1)))
    for name in ('Sight','Muzzle'):
        origin=bpy.data.objects[name].matrix_world.translation.copy()
        if name=='Sight':origin-=direction*.15
        hit,location,normal,index,obj,matrix=bpy.context.scene.ray_cast(bpy.context.evaluated_depsgraph_get(),origin,direction,distance=2)
        rows[name]={'forward_ray_occluded':hit,'object':obj.name if hit else None,'scope':'one local +Z geometry ray; not an in-game camera'}
    return rows


def load_gloves(defender):
    prior=set(bpy.context.scene.objects);bpy.ops.import_scene.gltf(filepath=str(defender));created=set(bpy.context.scene.objects)-prior;keep=set()
    for side,p in [('Right',G),('Left',SUPPORT)]:
        wrist=next(o for o in created if o.name=='Wrist'+side);keep.add(wrist);keep.update(wrist.children_recursive)
        wrist.parent=None;wrist.location=xyz((p[0],p[1]+.08,p[2]));wrist.rotation_mode='XYZ';wrist.rotation_euler=(0,0,0);wrist.scale=(1,1,1)
    for o in created-keep:bpy.data.objects.remove(o,do_unlink=True)
    bpy.context.view_layer.update();return keep


def hand_check(defender,batched=False):
    weapons=[o for o in bpy.context.scene.objects if o.type=='MESH'];gloves=load_gloves(defender);hands=[o for o in gloves if o.type=='MESH'];trees={o:tree(o) for o in weapons+hands};allowed=[];obstructions=[]
    for hand in hands:
        for obj in weapons:
            pairs=trees[hand].overlap(trees[obj])
            if not pairs:continue
            row={'glove':hand.name,'weapon_part':obj.name,'polygon_pairs':len(pairs)}
            is_grip=obj.data.materials[0].name.split('.')[0]=='Rubber' if batched else any(obj.name.startswith(n) for n in ('PrimaryGrip','SupportGrip','PrimaryTread','SupportTread'))
            target=allowed if is_grip else obstructions
            target.append(row)
    for o in gloves:bpy.data.objects.remove(o,do_unlink=True)
    return {'defender_sha256':hashlib.sha256(Path(defender).read_bytes()).hexdigest(),'grip_surface_contacts':allowed,'obstructions':obstructions,'scope':'Static final-v4 closed gloves at Grip/SupportGrip + 8cm Y wrists; grip-surface contacts are expected. Not a runtime first-person or articulated trigger-finger test.'}


def render_views(out,defender=None):
    bounds=d.bounds();scene,cam,center,span=w.setup_scene(bounds);cam.data.ortho_scale=span*1.5
    for label,angle in [('front',28),('side',95)]:
        a=math.radians(angle);cam.location=center+Vector((math.sin(a),-math.cos(a),.55))*span*2;cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler()
        scene.render.filepath=str(out/f'preview-{label}.png');bpy.ops.render.render(write_still=True)
    cam.data.type='PERSP';cam.data.lens=36;eye=Vector(xyz((.32,.53,-.80)));aim=Vector(xyz((0,.26,.18)))
    cam.location=eye;cam.rotation_euler=(aim-eye).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(out/'preview-rear-eye.png');bpy.ops.render.render(write_still=True)
    if defender:
        load_gloves(defender);scene.render.filepath=str(out/'preview-grip-study.png');bpy.ops.render.render(write_still=True)


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--no-render',action='store_true');p.add_argument('--render-existing',action='store_true');p.add_argument('--defender')
    args=p.parse_args(sys.argv[sys.argv.index('--')+1:]);out=Path(args.output).resolve();out.mkdir(parents=True,exist_ok=args.render_existing);reports=[]
    for name,(builder,accent,energy) in SPECS.items():
        target=out/name;path=target/f'{name}.glb'
        bpy.ops.wm.read_factory_settings(use_empty=True)
        if args.render_existing:bpy.ops.import_scene.gltf(filepath=str(path));render_views(target,args.defender);continue
        target.mkdir();materials(accent,energy);root,motion=builder();bpy.context.view_layer.update();before=d.bounds()
        hands=hand_check(args.defender) if args.defender else None
        f.batch_static_meshes();meshes=[o for o in bpy.context.scene.objects if o.type=='MESH'];triangles=0
        for o in meshes:o.data.calc_loop_triangles();triangles+=len(o.data.loop_triangles)
        assert triangles<=12000 and len(meshes)<=12,(name,triangles,len(meshes))
        bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',export_yup=True);bpy.ops.wm.save_as_mainfile(filepath=str(target/f'{name}.blend'))
        bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False);bpy.ops.import_scene.gltf(filepath=str(path));after=d.bounds()
        assert max(abs(before[i][j]-after[i][j]) for i in range(3) for j in range(2))<.00001
        for marker,expected in [('Grip',G),('SupportGrip',SUPPORT)]:
            obj=bpy.data.objects[marker];assert (obj.location-Vector(xyz(expected))).length<1e-7 and obj.rotation_euler.to_quaternion().angle<1e-7
        checks=motion_check(motion)
        imported_hands=hand_check(args.defender,batched=True) if args.defender else None
        assert all(not row['intersections'] for row in checks),(name,'moving-part contact',checks)
        assert not hands or not hands['obstructions'],(name,'glove obstruction',hands)
        assert not imported_hands or not imported_hands['obstructions'],(name,'imported glove obstruction',imported_hands)
        rays=axis_checks();assert not any(row['forward_ray_occluded'] for row in rays.values()),(name,rays)
        report={'asset':name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'triangles':triangles,'primitives':len(meshes),'dimensions_gltf_xyz_m':[after[0][1]-after[0][0],after[2][1]-after[2][0],after[1][1]-after[1][0]],'nodes':{k:{'translation_gltf_m':[bpy.data.objects[k].location.x,bpy.data.objects[k].location.z,-bpy.data.objects[k].location.y]} for k in ('Grip','SupportGrip','Muzzle','Sight',motion['part'])},'motion':motion,'motion_checks':checks}
        report['hand_check']=hands
        report['imported_hand_check']=imported_hands
        report['axis_checks']=rays
        report['bounds_gltf_xyz_m']=[after[0],after[2],[-after[1][1],-after[1][0]]]
        (target/'manifest.json').write_text(json.dumps(report,indent=2));reports.append(report)
        print(json.dumps({'asset':name,'triangles':triangles,'primitives':len(meshes),'motion_hits':[x for x in checks if x['intersections']]}),flush=True)
        if hands:print(json.dumps({'asset':name,'hand_obstructions':hands['obstructions']}),flush=True)
        if not args.no_render:render_views(target,args.defender)
    if not args.render_existing:(out/'manifest.json').write_text(json.dumps({'units':'meters','up':'Y','forward':'+Z','assets':reports,'scope':'Fresh GLB imports, sampled rigid-part separation; no runtime game or full continuous sweep claim'},indent=2))


if __name__=='__main__':main()
