"""Build 07: three original buyable weapons and a reused magazine sentry.

Authoring coordinates below are meters, Y-up, +Z-forward. Blender conversion
is isolated in helpers. No textures, skins, animation clips or LODs are authored.
"""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
import bpy
import bmesh
from mathutils import Vector, Quaternion
sys.path.insert(0,str(Path(__file__).resolve().parent))
import axm_fortress_sidearms as a
s=a.s;f=a.f;d=a.d;w=a.w
box=a.box;empty=a.empty;xyz=a.xyz;annulus=a.annulus


def cylinder(name,p,radius,length,mat,parent,axis='Y',sides=12):
    # Thin emitter lenses must keep real side faces after beveling.
    bpy.ops.mesh.primitive_cylinder_add(vertices=sides,radius=radius,depth=length,location=xyz(p))
    obj=s.bevel(f.finish(bpy.context.object,name,mat,parent),min(.006,radius*.15,length*.20))
    if axis=='X':obj.rotation_euler.y=math.pi/2
    if axis=='Z':obj.rotation_euler.x=math.pi/2
    return obj


def profile(name,outline,width,mat,parent,x=0,edge=.006):
    """Extrude a shaped Z/Y side silhouette through X, with true depth."""
    verts=[xyz((xx,y,z)) for xx in (x-width/2,x+width/2) for z,y in outline];n=len(outline)
    faces=[tuple(reversed(range(n))),tuple(range(n,2*n))]
    faces.extend((i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n))
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update()
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(mesh);bm.free()
    obj=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(obj)
    return s.bevel(f.finish(obj,name,mat,parent),edge)


def axial(name,sections,mat,parent,steps=20):
    # z, center-y, radius-x, radius-y; contiguous elliptical barrel sections.
    verts=[]
    for z,y,rx,ry in sections:
        verts.extend(xyz((rx*math.cos(2*math.pi*i/steps),y+ry*math.sin(2*math.pi*i/steps),z)) for i in range(steps))
    faces=[tuple(reversed(range(steps))),tuple(range((len(sections)-1)*steps,len(sections)*steps))]
    for level in range(len(sections)-1):
        for i in range(steps):j=(i+1)%steps;faces.append((level*steps+i,level*steps+j,(level+1)*steps+j,(level+1)*steps+i))
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update()
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(mesh);bm.free()
    obj=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(obj)
    for p in mesh.polygons:p.use_smooth=len(p.vertices)==4
    return f.finish(obj,name,mat,parent)


def magazine(parent):
    # EXACT shared geometry in rifle Magazine and sentry SentryPitch local space.
    profile('MagazineShell',[(-.124,-.059),(-.124,.043),(-.093,.077),(.065,.077),(.112,.039),(.100,-.068),(-.079,-.081)],.132,'Accent',parent,edge=.009)
    for sign in (-1,1):
        profile('MagazineArmor',[(-.109,-.044),(-.106,.039),(-.081,.059),(.047,.059),(.084,.030),(.077,-.047),(-.074,-.062)],.010,'Ceramic',parent,x=sign*.073,edge=.004)
        for i in range(3):box('RoundWitness',(sign*.080,.018,-.071+i*.043),(.006,.021,.014),'Energy',parent,.001)
        cylinder('MagazinePitchBearing',(sign*.082,0,0),.022,.012,'Steel',parent,'X',16)
    profile('FeedSpine',[(-.103,.082),(.040,.082),(.064,.069),(-.103,.069)],.069,'Steel',parent,edge=.002)
    cylinder('MagazineMicrobarrel',(0,.009,.133),.025,.069,'Steel',parent,'Z',16)
    annulus('MagazineMouth',(0,.009,.172),.029,.016,.016,'Dark',parent,'Z',20)
    cylinder('MagazineEmitter',(0,.009,.174),.012,.003,'Energy',parent,'Z',16)


def grips(root):
    a.common(root)
    for x,z in [(0,-.010),(.055,.163)]:
        box('KnuckleBowMount',(x,.213,z),(.045,.040,.024),'Steel',root,.003)


def foldback():
    root=empty('FoldbackRoot');grips(root)
    profile('LoadBearingReceiver',[(-.39,.233),(-.39,.341),(-.313,.385),(-.148,.385),(-.081,.348),(.272,.348),(.354,.286),(.290,.218),(-.26,.218)],.151,'Steel',root,.0,.010)
    for sign in (-1,1):
        profile('ReceiverSkin',[(-.368,.260),(-.368,.324),(-.304,.365),(-.15,.365),(-.083,.323),(.235,.323),(.287,.289),(.246,.244),(-.259,.244)],.018,'Ceramic',root,sign*.082,.008)
        profile('ForearmCheek',[(.243,.253),(.290,.329),(.490,.326),(.565,.301),(.510,.260)],.026,'Accent',root,sign*.053,.007)
        for i in range(4):box('CoolingLouvre',(sign*.070,.294,.306+i*.047),(.009,.021,.013),'Dark',root,.002)
    profile('ShoulderPad',[(-.411,.235),(-.411,.359),(-.388,.370),(-.373,.344),(-.373,.237)],.178,'Rubber',root,edge=.004)
    cylinder('BurstBarrel',(0,.292,.470),.030,.364,'Dark',root,'Z',20)
    annulus('MuzzleCollar',(0,.292,.639),.046,.031,.030,'Steel',root,'Z',24)
    annulus('BurstBrake',(0,.292,.676),.040,.022,.041,'Ceramic',root,'Z',24)
    cylinder('BurstLens',(0,.292,.694),.017,.003,'Energy',root,'Z',16)
    empty('Muzzle',(0,.292,.705),root);a.sight(root,.432,-.10,base=.363)
    box('MagazineDock',(-.102,.317,.026),(.048,.116,.186),'Dark',root,.010)
    mag=empty('Magazine',(-.216,.315,.028),root);magazine(mag)
    box('EjectPaddle',(-.106,.383,-.067),(.035,.025,.045),'Accent',root,.006)
    for i in range(3):box('BurstSelector',(.096,.307,-.077+i*.023),(.008,.017,.012),'Energy',root,.001)
    return root,[{'part':'Magazine','motion':'translation','axis':'local X','samples':[0,-.025,-.05,-.1,-.2,-.35], 'travel_m':[0,-.35], 'notes':'Subtract from rest X to eject; hide Magazine after deployment. Reattach at rest on reload.'}]


def slopcaster():
    root=empty('SlopcasterRoot');grips(root)
    profile('PressureCradle',[(-.165,.219),(-.152,.286),(-.052,.285),(.09,.249),(.31,.249),(.478,.228),(.401,.212)],.200,'Steel',root,edge=.007)
    axial('PressureReservoir',[(-.115,.372,.059,.064),(-.089,.379,.107,.119),(-.025,.395,.132,.142),(.075,.395,.130,.139),(.125,.386,.090,.092)],'Ceramic',root)
    axial('PistonBladder',[(.095,.386,.091,.091),(.132,.426,.094,.094),(.291,.426,.094,.094),(.321,.380,.087,.087)],'Dark',root)
    for z in (-.046,.056):annulus('ReservoirBand',(0,.395,z),.143,.134,.025,'Accent',root,'Z',28)
    chamber=empty('CompressionChamber',(0,.426,.196),root)
    annulus('MovingPressureCollar',(0,0,0),.144,.105,.038,'Steel',chamber,'Z',28)
    for i in range(8):
        angle=2*math.pi*i/8
        obj=box('PressureLug',(.151*math.cos(angle),.151*math.sin(angle),0),(.027,.022,.037),'Accent',chamber,.003);obj.rotation_euler.y=-angle
    annulus('CompressionIndex',(0,0,.023),.143,.117,.009,'Energy',chamber,'Z',28)
    axial('GlobNozzleHousing',[(.299,.380,.108,.110),(.335,.374,.139,.131),(.422,.368,.131,.122),(.568,.357,.086,.087),(.620,.357,.079,.079)],'Ceramic',root)
    annulus('NozzleSeal',(0,.357,.619),.093,.061,.025,'Dark',root,'Z',28)
    annulus('NozzleLip',(0,.357,.645),.098,.066,.026,'Accent',root,'Z',28)
    cylinder('GlobEmitter',(0,.357,.638),.058,.003,'Energy',root,'Z',24)
    empty('Muzzle',(0,.357,.669),root)
    # Side-mounted pressure gauge reads from the rear; its bracket is attached.
    box('GaugeBracket',(0,.541,-.027),(.080,.060,.055),'Steel',root,.008)
    cylinder('PressureGauge',(0,.575,-.032),.055,.029,'Dark',root,'Z',24)
    annulus('GaugeRim',(0,.575,-.05),.056,.043,.009,'Steel',root,'Z',24)
    cylinder('GaugeDial',(0,.575,-.051),.041,.006,'Accent',root,'Z',24)
    obj=box('GaugeNeedle',(0,.585,-.056),(.008,.047,.006),'Energy',root,.001);obj.rotation_euler.y=-.45
    for sign in (-1,1):
        profile('PressureTie',[(.310,.270),(.362,.283),(.480,.293),(.488,.254),(.375,.233)],.019,'Steel',root,sign*.111,.004)
    a.sight(root,.680,-.10,base=.509)
    return root,[{'part':'CompressionChamber','motion':'translation','axis':'local Z','samples':[i*.004 for i in range(11)],'travel_m':[0,.040],'notes':'Add 0..0.040 m to rest Z while charging; return to rest when glob releases.'}]


def ghostline():
    root=empty('GhostlineRoot');grips(root)
    profile('PhaseKeel',[(-.294,.231),(-.268,.341),(-.167,.362),(-.075,.313),(.233,.281),(.321,.233),(.198,.212),(-.239,.212)],.106,'Steel',root,edge=.008)
    for sign in (-1,1):
        profile('PhaseStock',[(-.286,.251),(-.258,.326),(-.173,.342),(-.074,.292),(.078,.271),(.052,.243),(-.224,.232)],.015,'Ceramic',root,sign*.060,.005)
        profile('SplitRail',[(.223,.278),(.279,.355),(.760,.347),(.915,.309),(.917,.280),(.779,.283),(.294,.270)],.032,'Ceramic',root,sign*.057,.005)
        profile('RailInset',[(.322,.319),(.745,.317),(.841,.301),(.328,.294)],.008,'Dark',root,sign*.077,.002)
        box('PhaseTrace',(sign*.057,.350,.525),(.010,.009,.390),'Energy',root,.002)
        profile('PanelEmitterWing',[(.410,.289),(.451,.362),(.553,.354),(.615,.300),(.573,.281)],.016,'Accent',root,sign*.104,.004)
        box('EmitterWingMount',(sign*.082,.299,.50),(.038,.027,.153),'Steel',root,.004)
        box('PanelEmitterEdge',(sign*.116,.328,.511),(.009,.017,.084),'Energy',root,.002)
    cylinder('PhaseNeedle',(0,.383,.137),.014,.225,'Dark',root,'Z',16)
    profile('PhaseBreech',[(-.060,.284),(-.060,.376),(-.030,.405),(.030,.405),(.032,.283)],.080,'Dark',root,edge=.008)
    coil=empty('PhaseCoil',(0,.383,.166),root)
    annulus('PhaseHalo',(0,0,0),.067,.024,.068,'Accent',coil,'Z',28)
    annulus('PhaseField',(0,0,.039),.068,.047,.010,'Energy',coil,'Z',28)
    for i in range(3):
        angle=2*math.pi*i/3
        o=box('PhasePole',(.074*math.cos(angle),.074*math.sin(angle),0),(.020,.022,.058),'Steel',coil,.003);o.rotation_euler.y=-angle
    for z in (.116,.224):
        annulus('PhaseStator',(0,.383,z),.096,.017,.012,'Steel',root,'Z',28)
        box('StatorFoot',(0,.279,z),(.051,.043,.038),'Steel',root,.004)
    for z in (.242,.768):box('RailCrossBrace',(0,.281,z),(.146,.017,.029),'Steel',root,.003)
    empty('Muzzle',(0,.317,.929),root);a.sight(root,.505,-.126,base=.340)
    return root,[{'part':'PhaseCoil','motion':'rotation','axis':'local Z','samples':[i*2*math.pi/60 for i in range(60)],'rotation_radians':[0,2*math.pi],'notes':'Rotate freely around local Z for charge/phase feedback. Temporary phase panel is runtime geometry.'}]


def sentry():
    root=empty('FoldbackSentryRoot')
    cylinder('MountingSole',(0,.012,0),.089,.024,'Rubber',root,'Y',24)
    cylinder('MountingPlinth',(0,.038,0),.079,.027,'Steel',root,'Y',24)
    for z in (-.085,.085):
        box('FootCrossmember',(0,.035,z),(.179,.030,.033),'Steel',root,.004)
    motions=[]
    for sign in (-1,1):
        for z,label in [(-.085,'Rear'),(.085,'Front')]:
            x=sign*.110;name='Foot'+('Left' if sign>0 else 'Right')+label
            cylinder('FootAxle',(x,.035,z),.008,.056,'Steel',root,'Z',12)
            for dz in (-.023,.023):box('AxlePedestal',(sign*.101,.035,z+dz),(.023,.019,.009),'Steel',root,.002)
            foot=empty(name,(x,.035,z),root)
            annulus('FootHinge',(0,0,0),.017,.0095,.024,'Accent',foot,'Z',16)
            shape=[(-.020,-.012),(-.020,.010),(.022,.010),(.034,-.011),(.024,-.024),(-.022,-.024)]
            # Shape is Z/Y; extrusion produces an outward rib, clear of the base.
            profile('SupportFoot',shape,.075,'Steel',foot,sign*.055,.002)
            box('ContactPad',(sign*.087,-.023,0),(.047,.024,.061),'Rubber',foot,.003)
            motions.append({'part':name,'motion':'rotation','axis':'local Z','samples':[sign*math.radians(i*5) for i in range(16)],'folded_radians':sign*math.radians(75),'deployed_radians':0,'notes':'Exported deployed. Animate folded rotation to zero for unfolding.'})
    yaw=empty('SentryYaw',(0,.380,0),root)
    cylinder('YawTurret',(0,-.315,0),.065,.019,'Steel',yaw,'Y',24)
    box('YawBridge',(0,-.304,0),(.230,.024,.073),'Steel',yaw,.004)
    for sign in (-1,1):
        profile('PitchFork',[(-.028,-.293),(-.028,-.004),(-.009,.016),(.020,.003),(.030,-.263),(.043,-.291)],.019,'Ceramic',yaw,sign*.106,.004)
        cylinder('PitchAxle',(sign*.104,0,0),.013,.028,'Steel',yaw,'X',16)
    pitch=empty('SentryPitch',(0,0,0),yaw);magazine(pitch)
    empty('Muzzle',(0,.009,.188),pitch)
    motions[:0]=[{'part':'SentryYaw','motion':'rotation','axis':'local Y','samples':[i*math.pi/12 for i in range(24)],'rotation_radians':[-math.pi,math.pi],'notes':'Yaw around mounting normal. Root local +Y points away from floor/wall.'},
                {'part':'SentryPitch','motion':'rotation','axis':'local X','samples':[-1.5+i*.05 for i in range(43)],'rotation_radians':[-1.5,.6],'notes':'Local +X hinge. Positive rotation pitches +Z muzzle toward -Y; use negative angle to elevate away from a mounting wall.'}]
    return root,motions


SPECS={'foldback-rifle':(foldback,(.075,.245,.435),(.10,.57,.90)),
       'slopcaster':(slopcaster,(.48,.38,.065),(.57,.86,.095)),
       'ghostline':(ghostline,(.25,.19,.44),(.23,.66,.94)),
       'foldback-sentry':(sentry,(.075,.245,.435),(.10,.57,.90))}


def animate(obj,spec,value,loc,rot):
    obj.location=loc;obj.rotation_mode='QUATERNION';obj.rotation_quaternion=rot
    axis=Vector(xyz({'local X':(1,0,0),'local Y':(0,1,0),'local Z':(0,0,1)}[spec['axis']]))
    if spec['motion']=='rotation':obj.rotation_quaternion=Quaternion(axis,value)@rot
    else:obj.location+=axis*value


def motion_check(spec):
    obj=bpy.data.objects[spec['part']];moving=[o for o in obj.children_recursive if o.type=='MESH'];all_meshes=[o for o in bpy.context.scene.objects if o.type=='MESH'];static=[o for o in all_meshes if o not in moving]
    loc=obj.location.copy();rot=obj.rotation_euler.to_quaternion() if obj.rotation_mode!='QUATERNION' else obj.rotation_quaternion.copy();rows=[]
    for value in spec['samples']:
        animate(obj,spec,value,loc,rot);bpy.context.view_layer.update();trees={o:a.tree(o) for o in all_meshes};hits=[]
        for p in moving:
            for q in static:
                pairs=trees[p].overlap(trees[q])
                if pairs:hits.append({'moving':p.name,'static':q.name,'pairs':len(pairs)})
        rows.append({'value':value,'intersections':hits})
    obj.location=loc;obj.rotation_quaternion=rot;bpy.context.view_layer.update();return rows


def marker_report(root):
    result={}
    for obj in [root]+list(root.children_recursive):
        if obj.type!='EMPTY':continue
        p=obj.location;v=obj.matrix_world.translation
        result[obj.name]={'parent':obj.parent.name if obj.parent else None,'translation_gltf_m':[p.x,p.z,-p.y],'world_translation_gltf_m':[v.x,v.z,-v.y],'rotation_gltf_xyzw':[0,0,0,1],'scale':[1,1,1]}
    return result


def render_views(out,is_sentry,defender):
    scene,cam,center,span=w.setup_scene(d.bounds());scene.cycles.samples=24;cam.data.ortho_scale=span*1.90
    for label,angle in [('front',28),('side',95)]:
        angle=math.radians(angle);cam.location=center+Vector((math.sin(angle),-math.cos(angle),.48))*span*2;cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(out/f'preview-{label}.png');bpy.ops.render.render(write_still=True)
    if is_sentry:
        cam.location=center+Vector((1,1,.40))*span*2;cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler()
    else:
        cam.data.type='PERSP';cam.data.lens=32;sight=bpy.data.objects['Sight'].matrix_world.translation
        eye=(.30,sight.z+.08,-sight.y-.85);aim=(0,sight.z-.06,.20)
        cam.location=xyz(eye);cam.rotation_euler=(Vector(xyz(aim))-cam.location).to_track_quat('-Z','Y').to_euler()
    scene.render.filepath=str(out/'preview-rear-eye.png');bpy.ops.render.render(write_still=True)
    if not is_sentry:
        sight=bpy.data.objects['Sight'].matrix_world.translation.copy();cam.data.lens=36;cam.location=sight+Vector(xyz((0,0,-.70)));cam.rotation_euler=Vector(xyz((0,0,1))).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(out/'preview-sight.png');bpy.ops.render.render(write_still=True)
        a.load_gloves(defender);bounds=d.bounds();center=Vector(tuple((a+b)/2 for a,b in bounds));span=max(b-a for a,b in bounds)
        cam.data.type='ORTHO';cam.data.ortho_scale=span*1.85;cam.location=center+Vector((1,1,.50))*span*2;cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(out/'preview-grip-study.png');bpy.ops.render.render(write_still=True)
    else:
        for spec in sentry_motion_specs():
            obj=bpy.data.objects[spec['part']];animate(obj,spec,spec['folded_radians'],obj.location.copy(),obj.rotation_quaternion.copy())
        bpy.context.view_layer.update();scene.render.filepath=str(out/'preview-folded.png');bpy.ops.render.render(write_still=True)


def sentry_motion_specs():
    return [{'part':'Foot'+side+label,'motion':'rotation','axis':'local Z','folded_radians':sign*math.radians(75)} for side,sign in [('Left',1),('Right',-1)] for label in ['Rear','Front']]


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--defender',required=True);p.add_argument('--no-render',action='store_true');p.add_argument('--render-existing',action='store_true');p.add_argument('--only',choices=list(SPECS));args=p.parse_args(sys.argv[sys.argv.index('--')+1:])
    out=Path(args.output).resolve();out.mkdir(parents=True,exist_ok=True);reports=[]
    for name,(builder,accent,energy) in SPECS.items():
        if args.only and name!=args.only:continue
        target=out/name;path=target/f'{name}.glb';bpy.ops.wm.read_factory_settings(use_empty=True)
        if args.render_existing:bpy.ops.import_scene.gltf(filepath=str(path));render_views(target,name=='foldback-sentry',args.defender);continue
        target.mkdir(exist_ok=False);a.materials(accent,energy);root,motions=builder();bpy.context.view_layer.update();before=d.bounds()
        hands=a.hand_check(args.defender) if name!='foldback-sentry' else None
        bpy.ops.wm.save_as_mainfile(filepath=str(target/f'{name}.blend'))
        source_motion=[{'part':spec['part'],'samples':motion_check(spec)} for spec in motions]
        # Save failures too, so the concrete geometry contacts can be repaired.
        (target/'source-checks.json').write_text(json.dumps({'hands':hands,'motion':source_motion},indent=2))
        print(json.dumps({'asset':name,'hands':hands['obstructions'] if hands else [],'motion_hits':[row for r in source_motion for row in r['samples'] if row['intersections']]}),flush=True)
        assert not hands or not hands['obstructions'],(name,'glove obstruction')
        assert all(not row['intersections'] for r in source_motion for row in r['samples']),(name,'motion obstruction')
        f.batch_static_meshes();meshes=[o for o in bpy.context.scene.objects if o.type=='MESH'];triangles=0
        for o in meshes:o.data.calc_loop_triangles();triangles+=len(o.data.loop_triangles)
        assert triangles<=10000 and len(meshes)<=(24 if name=='foldback-sentry' else 14),(name,triangles,len(meshes))
        bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',export_yup=True);root_name=root.name
        bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False);bpy.ops.import_scene.gltf(filepath=str(path));root=bpy.data.objects[root_name];bpy.context.view_layer.update();after=d.bounds()
        assert max(abs(before[i][j]-after[i][j]) for i in range(3) for j in range(2))<1e-5
        imported_hands=a.hand_check(args.defender,batched=True) if hands else None
        checks=[{'part':spec['part'],'samples':motion_check(spec)} for spec in motions]
        assert not imported_hands or not imported_hands['obstructions']
        assert all(not row['intersections'] for r in checks for row in r['samples']),(name,'imported motion obstruction')
        rays={};direction=Vector(xyz((0,0,1)))
        for marker in (['Muzzle'] if name=='foldback-sentry' else ['Muzzle','Sight']):
            origin=bpy.data.objects[marker].matrix_world.translation.copy()
            if marker=='Sight':origin-=direction*.15
            hit,_,_,_,obj,_=bpy.context.scene.ray_cast(bpy.context.evaluated_depsgraph_get(),origin,direction,distance=2)
            rays[marker]={'forward_ray_occluded':hit,'object':obj.name if hit else None}
        assert not any(row['forward_ray_occluded'] for row in rays.values()),(name,rays)
        report={'asset':name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'triangles':triangles,'primitives':len(meshes),'bounds_gltf_xyz_m':[after[0],after[2],[-after[1][1],-after[1][0]]],'nodes':marker_report(root),'motions':motions,'motion_checks':checks,'hand_check':hands,'imported_hand_check':imported_hands,'axis_checks':rays}
        report['dimensions_gltf_xyz_m']=[hi-lo for lo,hi in report['bounds_gltf_xyz_m']]
        (target/'manifest.json').write_text(json.dumps(report,indent=2));reports.append(report);print(json.dumps({'asset':name,'triangles':triangles,'primitives':len(meshes),'status':'EXPORT_CHECKS_PASS'}),flush=True)
        if not args.no_render:render_views(target,name=='foldback-sentry',args.defender)
    if not args.render_existing:(out/'manifest.json').write_text(json.dumps({'units':'meters','up':'Y','forward':'+Z','assets':reports,'scope':'Source/fresh-import static glove and sampled rigid motion checks; forward geometry rays. No runtime camera or continuous sweep certification.'},indent=2))


if __name__=='__main__':main()
