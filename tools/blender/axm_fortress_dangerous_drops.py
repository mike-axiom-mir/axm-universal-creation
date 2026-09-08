"""Roomspinner and Burrow Choir: original meter/Y-up/+Z assets, rigid parts."""
import argparse, hashlib, json, math, sys
from pathlib import Path
import bpy, bmesh
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
import axm_fortress_tourist as t
b=t.b;a=t.a;s=t.s;f=t.f;d=t.d;w=t.w
xyz=t.xyz;empty=t.empty;box=t.box;cylinder=t.cylinder;annulus=t.annulus;profile=t.profile

def grips(root):
    b.grips(root)
    for o in root.children:
        if o.type=='MESH' and o.name.startswith(('PrimaryGrip','SupportGrip')):
            for v in o.data.vertices:v.co.z*=.36 if v.co.z<0 else .58
        if o.type=='MESH' and o.name.startswith(('PrimaryTread','SupportTread')):o.location.z*=.58;o.scale.z=.58
        if o.name=='PrimaryHeel':o.location.z=-.028;o.location.y-=.016;o.scale.y=.60
    profile('LoadKeel',[(-.024,.216),(-.024,.229),(.670,.229),(.780,.254),(.820,.240),(.754,.214)],.112,'Steel',root,edge=.002)

def sight(root,x,y,z):
    empty('Sight',(x,y,z),root)
    for sign in (-1,1):
        box('SightEar',(x+sign*.026,y-.010,z),(.012,.042,.045),'Dark',root,.003)
        box('SightIndex',(x+sign*.026,y+.006,z-.025),(.008,.008,.006),'Energy',root,.001)
    box('SightFoot',(x,y-.037,z),(.069,.014,.070),'Steel',root,.002)

def spin(part,axis='local Z',samples=60,limit=2*math.pi):
    return {'part':part,'axis':axis,'motion':'rotation','samples':[i*limit/samples for i in range(samples+1)],'rotation_radians':[0,limit]}

def flat_arrow(name,parent,z,r0=.135,r1=.198,mat='Energy'):
    # Planar XY arrow points local +Y; closed extrusion through Z.
    outline=[(-.014,r0),(.014,r0),(.014,r1-.026),(.035,r1-.026),(0,r1),(-.035,r1-.026),(-.014,r1-.026)]
    verts=[xyz((x,y,zz)) for zz in (z-.004,z+.004) for x,y in outline];n=len(outline)
    faces=[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update()
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(mesh);bm.free()
    o=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(o);return f.finish(o,name,mat,parent)

def roomspinner():
    root=empty('RoomspinnerRoot');grips(root)
    for sign in (-1,1):
        profile('GravityYoke',[(.315,.228),(.337,.370),(.411,.464),(.650,.470),(.739,.395),(.727,.334),(.647,.409),(.431,.412),(.389,.340),(.380,.228)],.039,'Ceramic',root,sign*.249,.006)
        box('YokeInsulator',(sign*.249,.299,.359),(.047,.036,.047),'Accent',root,.004)
        for j in range(3):box('YokeStatus',(sign*.273,.374+j*.020,.407+j*.014),(.007,.008,.022),'Energy',root,.001)
    center=(0,.464,.561)
    annulus('FixedGimbalRace',center,.235,.214,.057,'Steel',root,'Z',40)
    g=empty('GravityGimbal',center,root)
    annulus('GravityMovingRing',(0,0,0),.207,.158,.043,'Accent',g,'Z',40)
    annulus('FieldRing',(0,0,-.026),.197,.182,.006,'Energy',g,'Z',40)
    flat_arrow('ForceArrowRear',g,-.033)
    flat_arrow('ForceArrowFront',g,.032)
    for j in range(8):
        angle=j*math.pi/4
        o=box('GimbalIndex',(.202*math.cos(angle),.202*math.sin(angle),0),(.012,.023,.038),'Steel',g,.001);o.rotation_euler.y=-angle
    # A short hollow launch throat is visibly separate from the spinning field ring.
    annulus('AnchorLaunchBore',(0,.464,.630),.098,.079,.338,'Dark',root,'Z',24)
    for z in (.465,.795):annulus('BoreArmorRim',(0,.464,z),.111,.080,.026,'Ceramic',root,'Z',24)
    annulus('AnchorMouth',(0,.464,.816),.103,.082,.011,'Energy',root,'Z',24)
    for z in (.437,.754):
        profile('BoreSaddle',[(z-.020,.229),(z-.018,.385),(z+.020,.385),(z+.020,.229)],.056,'Steel',root,edge=.003)
    empty('Muzzle',(0,.464,.839),root)
    # Rear-facing force control sits on its own raised cantilever.
    profile('ControlCantilever',[(.361,.276),(.390,.276),(.429,.438),(.416,.500),(.393,.496)],.055,'Steel',root,.260,.004)
    cylinder('ForceDialBacking',(.260,.462,.379),.057,.017,'Dark',root,'Z',24)
    dial=empty('ForceDial',(.260,.462,.354),root)
    cylinder('ForceDialFace',(0,0,0),.048,.020,'Accent',dial,'Z',24)
    flat_arrow('ForceDialPointer',dial,-.015,.006,.041,'Energy')
    for j in range(6):
        an=j*math.pi/3;o=box('DialKnurl',(.049*math.cos(an),.049*math.sin(an),0),(.008,.014,.016),'Accent',dial,.001);o.rotation_euler.y=-an
    sight(root,.340,.608,.367)
    box('SightMast',(.340,.548,.376),(.019,.078,.025),'Ceramic',root,.003)
    box('SightCrossarm',(.300,.512,.380),(.110,.017,.028),'Steel',root,.002)
    return root,[spin('GravityGimbal',samples=120),spin('ForceDial',samples=48)]

def anchor():
    root=empty('GravityAnchorRoot')
    cylinder('ContactShoe',(0,.012,0),.106,.024,'Steel',root,'Y',24)
    cylinder('AnchorFieldCore',(0,.051,0),.092,.053,'Dark',root,'Y',24)
    annulus('AnchorFluxRing',(0,.080,0),.092,.067,.010,'Energy',root,steps=24)
    for i in range(3):
        an=i*2*math.pi/3
        o=profile('ContactToe',[(-.024,.004),(.148,.004),(.163,.026),(.124,.048),(.035,.042),(-.024,.032)],.055,'Ceramic',root,edge=.003);o.rotation_euler.z=-an
        o=box('ToeIndex',(0,.035,.131),(.028,.010,.020),'Accent',root,.002)
        v=Vector(xyz((0,.035,.131)));v.rotate(__import__('mathutils').Quaternion((0,0,1),-an));o.location=v;o.rotation_euler.z=-an
    profile('DirectionWedge',[(-.092,.082),(-.078,.126),(.028,.126),(.107,.096),(.078,.083)],.063,'Accent',root,edge=.004)
    # Horizontal arrow on the upper surface points +Z, tangent to contact plane.
    arrow=flat_arrow('SidewaysForceCue',root,0,.000,.118,'Energy')
    arrow.rotation_euler.x=math.pi/2;arrow.location=xyz((0,.134,-.061))
    empty('Contact',(0,0,0),root);empty('ForceDirection',(0,0,.210),root);empty('SurfaceNormal',(0,.200,0),root)
    # Compact unit-scale anchor fits the 79 mm launch-bore radius even with its
    # flight origin at the contact plane, rather than scaling it in game.
    for o in root.children:
        o.location*=.48
        if o.type=='MESH':
            for v in o.data.vertices:v.co*=.48
    return root,[]

def drill(parent,detail=True):
    b.axial('DrillCore',[(0,0,.070,.070),(.028,0,.067,.067),(.125,0,.018,.018),(.151,0,.002,.002)],'Steel' if detail else 'Accent',parent,16 if detail else 12)
    steps=24 if detail else 12
    for start in range(3):
        verts=[]
        for j in range(steps+1):
            k=j/steps;z=.007+k*.132;r=.072*(1-k)+.008*k;an=start*2*math.pi/3+k*math.pi*2
            for dr,da in [(0,-.085),(.010*(1-k)+.001,0),(0,.085)]:verts.append(xyz(((r+dr)*math.cos(an+da),(r+dr)*math.sin(an+da),z)))
        faces=[(2,1,0),tuple(range(steps*3,steps*3+3))]
        for j in range(steps):
            for q in range(3):faces.append((j*3+q,j*3+(q+1)%3,(j+1)*3+(q+1)%3,(j+1)*3+q))
        mesh=bpy.data.meshes.new('HelicalCutter');mesh.from_pydata(verts,[],faces);mesh.update();bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(mesh);bm.free()
        o=bpy.data.objects.new('HelicalCutter',mesh);bpy.context.collection.objects.link(o);f.finish(o,'HelicalCutter','Accent',parent)

def burrower():
    root=empty('BurrowerRoot')
    b.axial('HunterBody',[(-.192,0,.043,.043),(-.166,0,.065,.065),(.057,0,.065,.065),(.099,0,.057,.057)],'Ceramic',root,16)
    annulus('HunterSeal',(0,0,.059),.068,.058,.034,'Dark',root,'Z',16)
    rotor=empty('DrillRotor',(0,0,.107),root);drill(rotor)
    cylinder('TailDrive',(0,0,-.195),.035,.009,'Steel',root,'Z',16)
    cylinder('TailSignal',(0,0,-.201),.020,.005,'Energy',root,'Z',12)
    motions=[spin('DrillRotor',samples=72)]
    for i in range(4):
        an=i*math.pi/2;fin=empty('Fin'+str(i+1),(-.074*math.sin(an),.074*math.cos(an),-.092),root)
        o=profile('FoldingSteeringFin',[(-.084,.003),(-.086,.014),(-.012,.016),(.010,.003)],.022,'Accent',fin,edge=.001);o.rotation_euler.y=-an
        # A rigid axle runs between two fixed journal seats; 1.5 mm end gaps.
        def hinge_cylinder(label,px,length,radius,parent,material):
            obj=b.axial(label,[(-length/2,0,radius,radius),(length/2,0,radius,radius)],material,parent,8)
            from mathutils import Quaternion
            orient=Quaternion(Vector(xyz((0,0,1))),an)
            obj.rotation_mode='QUATERNION';obj.rotation_quaternion=orient@Quaternion(Vector(xyz((0,1,0))),math.pi/2)
            off=orient@Vector(xyz((px,0,0)));obj.location=off+(Vector(xyz((-.074*math.sin(an),.074*math.cos(an),-.092))) if parent==root else Vector())
        hinge_cylinder('FinAxle',0,.039,.006,fin,'Accent')
        for sign in (-1,1):
            hinge_cylinder('FinJournal',sign*.026,.010,.009,root,'Steel')
            from mathutils import Quaternion
            orient=Quaternion(Vector(xyz((0,0,1))),an);off=orient@Vector(xyz((sign*.026,-.006,0)))+Vector(xyz((-.074*math.sin(an),.074*math.cos(an),-.092)))
            obj=box('FinJournalFoot',(0,0,0),(.008,.019,.017),'Steel',root,.001);obj.location=off;obj.rotation_mode='QUATERNION';obj.rotation_quaternion=orient
        spec=spin(fin.name,'local X' if i%2==0 else 'local Y',samples=12,limit=math.radians(60)*(1 if i<2 else -1));spec['notes']='0 = stowed; endpoint = deployed. Preserve the other local rotations and rest position.';motions.append(spec)
    empty('Nose',(0,0,.268),root);empty('Trail',(0,0,-.212),root)
    return root,motions

CELLS=[(-.132,.443,.620),(.132,.443,.620),(0,.662,.620)]
def choir():
    root=empty('BurrowChoirRoot');grips(root)
    profile('ChoirBackbone',[(.232,.229),(.302,.708),(.356,.757),(.387,.706),(.314,.229)],.057,'Steel',root,edge=.004)
    for i,(x,y,z) in enumerate(CELLS,1):
        annulus('CellSleeve',(x,y,.529),.112,.100,.332,'Dark',root,'Z',20)
        for zz in (.354,.706):annulus('CellCeramicLip',(x,y,zz),.122,.100,.030,'Ceramic',root,'Z',20)
        annulus('CellLockRing',(x,y,.409),.117,.112,.025,'Accent',root,'Z',20)
        # Two-material, closed-fin loaded proxy; a separately detailed hunter flies after firing.
        bay=empty('Bay'+str(i),(x,y,z),root)
        b.axial('LoadedHunter',[(-.192,0,.043,.043),(-.166,0,.065,.065),(.057,0,.065,.065),(.099,0,.057,.057)],'Steel',bay,12)
        nose=empty('LoadedDrill'+str(i),(0,0,.107),bay);drill(nose,False)
        # A three-step rear identifier remains visible in empty/loaded states.
        for j in range(i):box('CellIdentity',(x+(j-(i-1)/2)*.019,y+.082,.330),(.010,.009,.007),'Energy',root,.001)
        empty('Muzzle'+str(i),(x,y,.898),root)
        for sign in (-1,1):
            profile('CellArmorRail',[(.430,y-.025),(.455,y+.049),(.629,y+.049),(.678,y+.018),(.641,y-.013)],.020,'Ceramic',root,x+sign*.115,.003)
    for sign in (-1,1):
        profile('TrioCradle',[(.474,.228),(.481,.358),(.570,.358),(.665,.258),(.689,.229)],.044,'Steel',root,sign*.132,.003)
    box('DeliveryManifold',(0,.279,.547),(.306,.047,.079),'Accent',root,.006)
    sight(root,.345,.637,.368)
    profile('SightBracket',[(.345,.336),(.376,.336),(.402,.600),(.348,.600)],.023,'Steel',root,.345,.003)
    box('SightCradleTie',(.239,.339,.364),(.223,.024,.046),'Steel',root,.002)
    empty('Muzzle',(0,.515,.898),root)
    specs=[{'part':'Bay'+str(i),'motion':'translation','axis':'local Z','samples':[j*.025 for j in range(25)],'travel_m':[0,.600],'notes':'Rest translation = loaded; hide this root and all descendants for empty. Optional straight +Z extraction; never rotate the bay. LoadedDrill children are visual proxies, not independently animated.'} for i in (1,2,3)]
    return root,specs

SPECS={'roomspinner':(roomspinner,(.58,.175,.050),(.26,.68,.95),10000,14),'gravity-anchor':(anchor,(.58,.175,.050),(.26,.68,.95),2200,6),'burrow-choir':(choir,(.060,.335,.280),(.90,.52,.080),10000,15),'burrower':(burrower,(.060,.335,.280),(.90,.52,.080),2800,12)}

def views(target,name,defender,motions):
    # All previews are rendered from the exported, freshly reimported GLB.
    scene,cam,center,span=w.setup_scene(d.bounds());scene.cycles.samples=24;cam.data.ortho_scale=span*1.6
    for label,vector in [('front',(.8,-1,.65)),('side',(1,.1,.38)),('rear',(.65,1,.55))]:
        cam.location=center+Vector(vector)*span*2;cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(target/f'preview-{label}.png');bpy.ops.render.render(write_still=True)
    if name in ('roomspinner','burrow-choir'):
        cam.data.type='PERSP';cam.data.lens=36;cam.location=bpy.data.objects['Sight'].matrix_world.translation+Vector(xyz((0,0,-.7)));cam.rotation_euler=Vector(xyz((0,0,1))).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(target/'preview-sight.png');bpy.ops.render.render(write_still=True)
    if name=='burrow-choir':
        for i in (1,2,3):
            for o in bpy.data.objects['Bay'+str(i)].children_recursive:o.hide_render=True
        cam.data.type='ORTHO';cam.data.ortho_scale=span*1.6;cam.location=center+Vector((.8,-1,.65))*span*2;cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(target/'preview-empty.png');bpy.ops.render.render(write_still=True)
    if name=='burrower':
        for spec in motions[1:]:
            obj=bpy.data.objects[spec['part']];b.animate(obj,spec,spec['samples'][-1],obj.location.copy(),obj.rotation_quaternion.copy())
        bpy.context.view_layer.update();scene.render.filepath=str(target/'preview-deployed.png');bpy.ops.render.render(write_still=True)

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--defender',required=True);p.add_argument('--only',choices=list(SPECS));p.add_argument('--no-render',action='store_true');p.add_argument('--render-existing',action='store_true');args=p.parse_args(sys.argv[sys.argv.index('--')+1:]);out=Path(args.output).resolve();out.mkdir(parents=True,exist_ok=True)
    for name,(builder,accent,energy,tri_budget,prim_budget) in SPECS.items():
        if args.only and args.only!=name:continue
        target=out/name;path=target/(name+'.glb');bpy.ops.wm.read_factory_settings(use_empty=True)
        if args.render_existing:
            manifest=json.loads((target/'manifest.json').read_text());bpy.ops.import_scene.gltf(filepath=str(path));views(target,name,args.defender,manifest['motions']);continue
        target.mkdir();a.materials(accent,energy);root,motions=builder();t.clean_meshes();bpy.context.view_layer.update();before=d.bounds();is_weapon=name in ('roomspinner','burrow-choir')
        hands=a.hand_check(args.defender) if is_weapon else None;checks=[{'part':spec['part'],'samples':b.motion_check(spec)} for spec in motions]
        (target/'source-checks.json').write_text(json.dumps({'hands':hands,'motion':checks},indent=2));bpy.ops.wm.save_as_mainfile(filepath=str(target/(name+'.blend')))
        print(json.dumps({'asset':name,'hands':hands['obstructions'] if hands else [],'motion_hits':[r for check in checks for r in check['samples'] if r['intersections']][:3]}),flush=True)
        assert not hands or not hands['obstructions'];assert all(not r['intersections'] for c in checks for r in c['samples'])
        f.batch_static_meshes();meshes=[o for o in bpy.context.scene.objects if o.type=='MESH'];triangles=0
        for o in meshes:o.data.calc_loop_triangles();triangles+=len(o.data.loop_triangles)
        print(json.dumps({'asset':name,'triangles':triangles,'primitives':len(meshes)}),flush=True);assert triangles<=tri_budget and len(meshes)<=prim_budget,(triangles,len(meshes))
        root_name=root.name;bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',export_yup=True)
        bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False);bpy.ops.import_scene.gltf(filepath=str(path));root=bpy.data.objects[root_name];bpy.context.view_layer.update();after=d.bounds()
        assert max(abs(before[i][j]-after[i][j]) for i in range(3) for j in range(2))<1e-5
        imported=a.hand_check(args.defender,batched=True) if hands else None;checks=[{'part':spec['part'],'samples':b.motion_check(spec)} for spec in motions]
        assert not imported or not imported['obstructions'];assert all(not r['intersections'] for c in checks for r in c['samples'])
        rays={};direction=Vector(xyz((0,0,1)))
        for marker in (['Sight','Muzzle']+(['Muzzle1','Muzzle2','Muzzle3'] if name=='burrow-choir' else []) if is_weapon else []):
            origin=bpy.data.objects[marker].matrix_world.translation.copy()
            if marker=='Sight':origin-=direction*.7
            hit,_,_,_,obj,_=bpy.context.scene.ray_cast(bpy.context.evaluated_depsgraph_get(),origin,direction,distance=2);rays[marker]={'forward_ray_occluded':hit,'object':obj.name if hit else None}
        assert not any(r['forward_ray_occluded'] for r in rays.values()),rays
        bounds=[after[0],after[2],[-after[1][1],-after[1][0]]];points=[o.matrix_world@v.co for o in bpy.context.scene.objects if o.type=='MESH' for v in o.data.vertices]
        report={'asset':name,'root':root_name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'triangles':triangles,'primitives':len(meshes),'triangle_budget':tri_budget,'primitive_budget':prim_budget,'bounds_gltf_xyz_m':bounds,'dimensions_gltf_xyz_m':[hi-lo for lo,hi in bounds],'max_radial_xy_m':max(math.hypot(p.x,p.z) for p in points),'nodes':b.marker_report(root),'motions':motions,'motion_checks':checks,'hand_check':hands,'imported_hand_check':imported,'axis_checks':rays}
        (target/'manifest.json').write_text(json.dumps(report,indent=2));print(json.dumps({'asset':name,'status':'EXPORT_CHECKS_PASS'}),flush=True)
        if not args.no_render:views(target,name,args.defender,motions)

if __name__=='__main__':main()
