"""Four original throwable utilities and a telescoping curved Borrowed Wall."""
import argparse,hashlib,json,math,sys
from pathlib import Path
import bpy,bmesh
from mathutils import Vector,Quaternion
sys.path.insert(0,str(Path(__file__).resolve().parent))
import axm_fortress_dangerous_drops as d
b=d.b;a=d.a;s=d.s;f=d.f;w=d.w;t=d.t
xyz=d.xyz;empty=d.empty;box=d.box;cylinder=d.cylinder;annulus=d.annulus;profile=d.profile

def spin(part,axis='local Y',count=48,limit=2*math.pi):return d.spin(part,axis,count,limit)
def slide(part,distance,count=12):return {'part':part,'motion':'translation','axis':'local Y','samples':[distance*i/count for i in range(count+1)],'travel_m':[0,distance]}
def orient(obj,angle):
    q=Quaternion(Vector(xyz((0,1,0))),angle);obj.location=q@obj.location;obj.rotation_mode='QUATERNION';obj.rotation_quaternion=q@obj.rotation_euler.to_quaternion();return obj
def markers(root,grip,effect):
    empty('Grip',grip,root);empty('Contact',(0,0,0),root);empty('EffectOrigin',effect,root)
def orb(name,p,radius,material,parent):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=20,ring_count=12,radius=radius,location=xyz(p));o=f.finish(bpy.context.object,name,material,parent)
    for face in o.data.polygons:face.use_smooth=True
    return o

def velcro_sun():
    root=empty('VelcroSunRoot')
    cylinder('AdhesiveContact',(0,.004,0),.079,.008,'Rubber',root,'Y',24)
    cylinder('SunCoreHousing',(0,.026,0),.086,.035,'Dark',root,'Y',24)
    annulus('CoreCeramicSeat',(0,.044,0),.052,.037,.015,'Ceramic',root,steps=24)
    orb('BrightPullEmitter',(0,.061,0),.039,'Energy',root)
    halo=empty('Halo',(0,.064,0),root)
    annulus('RotatingPullHalo',(0,0,0),.071,.056,.013,'Accent',halo,steps=32)
    for i in range(3):
        angle=i*2*math.pi/3
        orient(box('HaloPole',(0,0,.073),(.023,.011,.008),'Energy',halo,.001),angle)
        orient(profile('SunLobe',[(-.003,.008),(.094,.008),(.108,.031),(.095,.057),(.083,.061),(.079,.032),(-.003,.027)],.047,'Ceramic',root,edge=.003),angle)
        orient(box('LobeWarning',(0,.036,.101),(.020,.019,.008),'Accent',root,.002),angle)
    for x in (-.023,.023):box('RearChargeContact',(x,.028,-.084),(.013,.018,.008),'Steel',root,.001)
    markers(root,(0,.030,-.039),(0,.107,0))
    return root,[spin('Halo')]

def petal_geometry(parent,angle):
    # Narrow tips allow all four petals to close around the lift emitter.
    sections=[(0,0,.038),(.038,-.010,.058),(.083,-.035,.038),(.104,-.044,.012)]
    verts=[]
    for y,z,width in sections:
        for x,dy in [(-width/2,-.003),(width/2,-.003),(width/2,.003),(-width/2,.003)]:verts.append(xyz((x,y+dy,z)))
    faces=[(3,2,1,0),(12,13,14,15)]
    for level in range(3):
        for i in range(4):faces.append((level*4+i,level*4+(i+1)%4,(level+1)*4+(i+1)%4,(level+1)*4+i))
    mesh=bpy.data.meshes.new('LiftPetal');mesh.from_pydata(verts,[],faces);mesh.update();bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(mesh);bm.free();obj=bpy.data.objects.new('LiftPetal',mesh);bpy.context.collection.objects.link(obj);orient(s.bevel(f.finish(obj,'LiftPetal','Ceramic',parent),.001),angle)
    orient(box('PetalLiftTrace',(0,.040,-.006),(.019,.031,.006),'Accent',parent,.001),angle)

def daisy():
    root=empty('UpsieDaisyRoot')
    cylinder('DaisySole',(0,.007,0),.066,.014,'Rubber',root,'Y',20)
    cylinder('LiftAccumulator',(0,.026,0),.065,.025,'Dark',root,'Y',20)
    annulus('LiftCrown',(0,.041,0),.054,.030,.014,'Accent',root,steps=24)
    cylinder('UpwardEmitter',(0,.048,0),.026,.025,'Energy',root,'Y',20)
    motions=[]
    for i in range(4):
        angle=i*math.pi/2;petal=empty('Petal'+str(i+1),(.060*math.sin(angle),.049,.060*math.cos(angle)),root);petal_geometry(petal,angle)
        orient(cylinder('PetalAxle',(0,0,0),.0045,.044,'Accent',petal,'X',8),angle)
        # Fixed, exposed hinge journals sit outside the moving leaf width.
        for sign in (-1,1):
            o=cylinder('PetalJournal',(sign*.028,.049,.060),.008,.010,'Steel',root,'X',8);orient(o,angle)
            orient(box('PetalJournalFoot',(sign*.028,.036,.059),(.009,.021,.023),'Steel',root,.001),angle)
        axis='local X' if i%2==0 else 'local Z';sign=1 if i in (0,3) else -1
        spec=spin(petal.name,axis,19,sign*math.radians(95));spec['notes']='0 = closed; endpoint = open. Axis and sign follow the authored tangent hinge. Preserve all other rotations.';motions.append(spec)
    markers(root,(0,.026,-.030),(0,.081,0))
    return root,motions

def biscuit():
    root=empty('PanicBiscuitRoot')
    box('BiscuitSeal',(0,.037,0),(.118,.058,.158),'Dark',root,.010)
    for sign in (-1,1):
        profile('BiscuitCase',[(-.071,.012),(-.079,.025),(-.073,.063),(.051,.072),(.077,.056),(.077,.019),(.057,.010)],.017,'Ceramic',root,sign*.056,.004)
        for z in (-.061,.061):cylinder('CaseFoot',(sign*.049,.006,z),.010,.012,'Rubber',root,'Y',8)
    box('PrioritySwitch',(0,.069,.044),(.046,.011,.026),'Accent',root,.002)
    box('VerySeriousDisplay',(0,.069,-.041),(.065,.009,.035),'Steel',root,.002)
    for i in range(3):box('PriorityMeter',(-.018+i*.018,.075,-.041),(.009,.005,.021),'Energy',root,.001)
    cylinder('BeaconPedestal',(0,.078,.006),.027,.026,'Steel',root,'Y',16)
    cylinder('FixedAntennaStem',(0,.112,.006),.013,.068,'Steel',root,'Y',12)
    lift=empty('BeaconLift',(0,.106,.006),root)
    annulus('TelescopingBeaconSleeve',(0,.028,0),.020,.0145,.071,'Dark',lift,steps=16)
    cylinder('BeaconLowerCap',(0,.068,0),.036,.012,'Accent',lift,'Y',16)
    cylinder('PriorityBeacon',(0,.086,0),.030,.025,'Energy',lift,'Y',20)
    cylinder('BeaconRainHat',(0,.105,0),.040,.015,'Ceramic',lift,'Y',16)
    for i in range(3):
        angle=i*2*math.pi/3
        orient(box('BeaconGuard',(0,.087,.034),(.009,.043,.007),'Steel',lift,.001),angle)
    empty('Grip',(0,.035,-.043),root);empty('Contact',(0,0,0),root);empty('EffectOrigin',(0,.116,0),lift)
    return root,[slide('BeaconLift',.025,10)]

def wall_device():
    root=empty('BorrowedWallDeviceRoot')
    box('ProjectorCase',(0,.035,0),(.144,.055,.174),'Dark',root,.012)
    for sign in (-1,1):
        box('CaseArmor',(sign*.071,.038,0),(.014,.053,.135),'Ceramic',root,.004)
        for z in (-.061,.061):box('ContactFoot',(sign*.052,.005,z),(.031,.010,.028),'Rubber',root,.002)
    for i in range(3):
        box('FoldedArchitecturePlate',(0,.064+i*.016,-.008+i*.011),(.120-i*.011,.012,.151-i*.020),'Ceramic' if i!=1 else 'Accent',root,.003)
        box('PlateEndIndex',(.056-i*.0055,.064+i*.016,.047-i*.004),(.006,.007,.018),'Energy',root,.001)
    lift=empty('ProjectorLift',(0,.120,.018),root)
    box('ProjectionAperture',(0,0,0),(.082,.018,.056),'Accent',lift,.003)
    box('ArchitectureLens',(0,.012,0),(.074,.006,.038),'Energy',lift,.001)
    for sign in (-1,1):
        cylinder('ProjectorGuide',(sign*.050,.113,.018),.0055,.073,'Steel',root,'Y',12)
        annulus('GuideBushing',(sign*.050,0,0),.010,.0065,.018,'Steel',lift,steps=12)
    empty('Grip',(0,.036,-.038),root);empty('Contact',(0,0,0),root);empty('EffectOrigin',(0,.025,0),lift);empty('CollapseDirection',(0,0,.160),root)
    return root,[slide('ProjectorLift',.026,13)]

def wall():
    root=empty('BorrowedWallRoot');motions=[]
    empty('Contact',(0,0,0),root);empty('EffectOrigin',(0,.900,0),root);empty('CollapseDirection',(0,0,1.20),root)
    for i in range(7):
        theta=(i-3)*.16;angle=-theta;x=5.3*math.sin(theta);z=5.3*(1-math.cos(theta));bay=empty('WallBay'+str(i+1),(x,0,z),root)
        orient(box('LowerArmor',(0,.345,0),(.817,.610,.062),'Ceramic',bay,.012),angle)
        orient(box('FloorChassis',(0,.038,-.060),(.831,.076,.278),'Steel',bay,.010),angle)
        orient(box('LowerFieldInset',(0,.338,.036),(.637,.237,.012),'Dark',bay,.004),angle)
        for j in range(3):orient(box('LowerIdentity',(-.074+j*.074,.331,.045),(.043,.032,.009),'Energy',bay,.002),angle)
        for label,y,zoff,travel,edge_mat in [('Mid',.610,-.080,-.490,'Dark'),('Top',1.180,-.160,-1.060,'Accent')]:
            pos=Quaternion(Vector(xyz((0,1,0))),angle)@Vector(xyz((0,y,zoff)));tier=empty('Bay'+str(i+1)+label,(pos.x,pos.z,-pos.y),bay)
            orient(box(label+'Armor',(0,.305,0),(.817,.630,.062),'Ceramic',tier,.012),angle)
            for sign in (-1,1):orient(box('TierEdge',(sign*.387,.305,.037),(.023,.593,.010),edge_mat,tier,.003),angle)
            orient(box('TierTopRail',(0,.605,.036),(.746,.024,.010),edge_mat,tier,.002),angle)
            spec=slide(tier.name,travel,14);spec['notes']='0 = fully deployed; negative local Y retracts vertically into the lower chassis. Independent tiers preserve their authored X/Z offsets and rotation. No horizontal motion.';motions.append(spec)
    for sign in (-1,1):
        end=empty('EndSupport'+('Right' if sign>0 else 'Left'),(sign*2.937,0,.787),root)
        box('EndFoot',(0,.045,0),(.120,.090,.494),'Steel',end,.014)
        box('EndFootLink',(-sign*.095,.020,-.050),(.240,.040,.120),'Steel',end,.004)
        profile('EndBrace',[(-.195,.080),(-.183,.190),(-.076,.639),(.024,.678),(.115,.635),(.190,.080)],.084,'Ceramic',end,edge=.009)
        box('EndWarning',(0,.363,.035),(.097,.157,.024),'Accent',end,.004)
    return root,motions

SPECS={'velcro-sun':(velcro_sun,(.83,.31,.035),(.96,.64,.11),4000,12),'upsie-daisy':(daisy,(.39,.15,.59),(.17,.73,.90),4000,16),'panic-biscuit':(biscuit,(.69,.43,.065),(1,.065,.025),4000,12),'borrowed-wall-device':(wall_device,(.065,.28,.48),(.15,.65,.83),4000,12),'borrowed-wall':(wall,(.065,.28,.48),(.15,.65,.83),12000,40)}

def mesh_bounds(objects):
    points=[o.matrix_world@v.co for o in objects if o.type=='MESH' for v in o.data.vertices]
    return [[min(p[i] for p in points),max(p[i] for p in points)] for i in range(3)]
def gltf_bounds(bounds):return [bounds[0],bounds[2],[-bounds[1][1],-bounds[1][0]]]
def contract_bounds(root,motions):
    initial=gltf_bounds(mesh_bounds(root.children_recursive));union=[p.copy() for p in initial];states=[]
    for spec in motions:
        o=bpy.data.objects[spec['part']];loc=o.location.copy();rot=o.rotation_quaternion.copy()
        for value in spec['samples']:
            b.animate(o,spec,value,loc,rot);bpy.context.view_layer.update();bb=gltf_bounds(mesh_bounds(root.children_recursive))
            for i in range(3):union[i][0]=min(union[i][0],bb[i][0]);union[i][1]=max(union[i][1],bb[i][1])
        o.location=loc;o.rotation_quaternion=rot
    bpy.context.view_layer.update()
    return initial,union

def views(target,name,motions):
    scene,cam,center,span=w.setup_scene(d.d.bounds());scene.cycles.samples=24;cam.data.ortho_scale=span*(1.32 if name=='borrowed-wall' else 1.65)
    def frame():
        q=cam.rotation_euler.to_quaternion();pts=[q.inverted()@(o.matrix_world@v.co) for o in bpy.context.scene.objects if o.type=='MESH' for v in o.data.vertices];lo=[min(p[k] for p in pts) for k in (0,1)];hi=[max(p[k] for p in pts) for k in (0,1)];eye=q.inverted()@cam.location
        cam.location+=q@Vector(((lo[0]+hi[0])/2-eye.x,(lo[1]+hi[1])/2-eye.y,0));cam.data.ortho_scale=max(hi[0]-lo[0],(hi[1]-lo[1])*scene.render.resolution_x/scene.render.resolution_y)*1.16
    for label,vector in [('front',(.75,-1,.7)),('side',(1,.12,.42)),('rear',(.55,1,.65))]:
        cam.location=center+Vector(vector)*span*2;cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();frame();scene.render.filepath=str(target/f'preview-{label}.png');bpy.ops.render.render(write_still=True)
    if motions:
        for spec in motions:
            o=bpy.data.objects[spec['part']];b.animate(o,spec,spec['samples'][-1] if spec['motion']=='translation' or name=='upsie-daisy' else math.pi/3,o.location.copy(),o.rotation_quaternion.copy())
        bpy.context.view_layer.update();cam.location=center+Vector((.75,-1,.7))*span*2;cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();frame();scene.render.filepath=str(target/'preview-active.png');bpy.ops.render.render(write_still=True)

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--only',choices=list(SPECS));p.add_argument('--no-render',action='store_true');p.add_argument('--render-existing',action='store_true');args=p.parse_args(sys.argv[sys.argv.index('--')+1:]);out=Path(args.output).resolve();out.mkdir(parents=True,exist_ok=True)
    for name,(builder,accent,energy,tri_budget,prim_budget) in SPECS.items():
        if args.only and args.only!=name:continue
        target=out/name;path=target/(name+'.glb');bpy.ops.wm.read_factory_settings(use_empty=True)
        if args.render_existing:
            data=json.loads((target/'manifest.json').read_text());bpy.ops.import_scene.gltf(filepath=str(path));views(target,name,data['motions']);continue
        target.mkdir();a.materials(accent,energy);root,motions=builder();t.clean_meshes();bpy.context.view_layer.update();before=d.d.bounds();checks=[{'part':spec['part'],'samples':b.motion_check(spec)} for spec in motions]
        (target/'source-checks.json').write_text(json.dumps({'motion':checks},indent=2));bpy.ops.wm.save_as_mainfile(filepath=str(target/(name+'.blend')));print(json.dumps({'asset':name,'hits':[r for c in checks for r in c['samples'] if r['intersections']][:3]}),flush=True);assert all(not r['intersections'] for c in checks for r in c['samples'])
        collision_boxes=None
        if name=='borrowed-wall':
            collision_boxes=[];static_roots=[o for o in root.children if o.type=='EMPTY' and (o.name.startswith('WallBay') or o.name.startswith('EndSupport'))]
            for o in static_roots:
                bb=gltf_bounds(mesh_bounds(o.children_recursive));collision_boxes.append({'part':o.name,'bounds_gltf_xyz_m':bb,'game_box_local':{'x':sum(bb[0])/2,'z':sum(bb[2])/2,'w':bb[0][1]-bb[0][0],'d':bb[2][1]-bb[2][0],'bottom':0,'h':bb[1][1]}})
            # Preserve editable groups in the saved .blend, then share static
            # material batches across bays in the runtime export.
            for o in list(root.children_recursive):
                if o.type=='MESH' and o.parent in static_roots:
                    matrix=o.matrix_world.copy();o.parent=root;o.matrix_world=matrix
            bpy.context.view_layer.update()
        f.batch_static_meshes();meshes=[o for o in root.children_recursive if o.type=='MESH'];triangles=0
        for o in meshes:o.data.calc_loop_triangles();triangles+=len(o.data.loop_triangles)
        print(json.dumps({'asset':name,'triangles':triangles,'primitives':len(meshes)}),flush=True);assert triangles<=tri_budget and len(meshes)<=prim_budget
        root_name=root.name;bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',export_yup=True)
        bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False);bpy.ops.import_scene.gltf(filepath=str(path));root=bpy.data.objects[root_name];bpy.context.view_layer.update();after=d.d.bounds();assert max(abs(before[i][j]-after[i][j]) for i in range(3) for j in range(2))<1e-5
        checks=[{'part':spec['part'],'samples':b.motion_check(spec)} for spec in motions];assert all(not r['intersections'] for c in checks for r in c['samples'])
        bounds,swept=contract_bounds(root,motions);assert bounds[1][0]>=-1e-6 and swept[1][0]>=-1e-6
        nodes=b.marker_report(root);points=[o.matrix_world@v.co for o in root.children_recursive if o.type=='MESH' for v in o.data.vertices]
        report={'asset':name,'root':root_name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'triangles':triangles,'primitives':len(meshes),'triangle_budget':tri_budget,'primitive_budget':prim_budget,'bounds_gltf_xyz_m':bounds,'sampled_motion_bounds_gltf_xyz_m':swept,'rest_origin_sphere_radius_m':max(p.length for p in points),'nodes':nodes,'motions':motions,'motion_checks':checks,'grip_scope':'Authored mounting marker only; single-hand throwable pose is a game integration contract, not a closed-glove contact certification.'}
        if collision_boxes:report['conservative_deployed_collision_boxes']=collision_boxes
        (target/'manifest.json').write_text(json.dumps(report,indent=2));print(json.dumps({'asset':name,'status':'EXPORT_CHECKS_PASS'}),flush=True)
        if not args.no_render:views(target,name,motions)

if __name__=='__main__':main()
