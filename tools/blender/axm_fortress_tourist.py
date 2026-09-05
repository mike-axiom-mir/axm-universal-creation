"""Original Tourist launcher and piloted missile, Y-up meter contracts."""
import argparse,json,hashlib,math,sys
from pathlib import Path
import bpy,bmesh
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
import axm_fortress_buyables as b
a=b.a;s=b.s;f=b.f;d=b.d;w=b.w
xyz=b.xyz;empty=b.empty;box=b.box;cylinder=b.cylinder;annulus=b.annulus;profile=b.profile
AXIS=(-.075,.460)


def clean_meshes():
    # Resolve sub-micrometer bevel slivers before float32 glTF serialization.
    for obj in bpy.context.scene.objects:
        if obj.type!='MESH':continue
        bm=bmesh.new();bm.from_mesh(obj.data)
        bmesh.ops.remove_doubles(bm,verts=bm.verts,dist=5e-7)
        bmesh.ops.dissolve_degenerate(bm,edges=bm.edges,dist=5e-7)
        bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(obj.data);bm.free();obj.data.update()


def shell_arc(name,sections,low,high,material,parent):
    # z, outer-radius, inner-radius; hollow protective petals around launch axis.
    steps=8;verts=[]
    for z,outer,inner in sections:
        for r in (outer,inner):
            for i in range(steps+1):
                theta=math.radians(low+(high-low)*i/steps)
                verts.append(xyz((AXIS[0]+r*math.cos(theta),AXIS[1]+r*math.sin(theta),z)))
    n=steps+1;stride=2*n;faces=[]
    for k in range(len(sections)-1):
        start=k*stride;next=start+stride
        for i in range(steps):
            faces.extend([(start+i,next+i,next+i+1,start+i+1),(start+n+i,start+n+i+1,next+n+i+1,next+n+i)])
        faces.extend([(start,start+n,next+n,next),(start+n-1,next+n-1,next+stride-1,start+stride-1)])
    for start in (0,(len(sections)-1)*stride):
        for i in range(steps):faces.append((start+i,start+i+1,start+n+i+1,start+n+i))
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update()
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(mesh);bm.free()
    obj=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(obj)
    return s.bevel(f.finish(obj,name,material,parent),.003)


def launcher():
    root=empty('TouristLauncherRoot');b.grips(root)
    # Short grip inserts stop before the forearm seals in the settled game poses.
    for obj in root.children:
        if obj.type=='MESH' and obj.name.startswith(('PrimaryGrip','SupportGrip')):
            for v in obj.data.vertices:v.co.z*=.36 if v.co.z<0 else .58
        if obj.type=='MESH' and obj.name.startswith(('PrimaryTread','SupportTread')):obj.location.z*=.58;obj.scale.z=.58
        if obj.name=='PrimaryHeel':obj.location.z=-.028;obj.location.y-=.016;obj.scale.y=.60
    grip_parts=set(root.children)
    profile('LaunchCradle',[(-.025,.219),(-.015,.224),(.270,.224),(.730,.224),(.890,.260),(1.100,.260),(1.090,.216),(.010,.216)],.111,'Steel',root,edge=.002)
    cradle=bpy.data.objects['LaunchCradle']
    annulus('LaunchTube',(AXIS[0],AXIS[1],.270),.183,.164,.970,'Dark',root,'Z',32)
    # Three shaped armor petals leave the guidance mechanism visibly exposed.
    for low,high in [(12,112),(132,228),(250,348)]:
        shell_arc('RearTubeArmor',[(-.255,.191,.184),(-.200,.211,.186),(.040,.205,.187)],low,high,'Ceramic',root)
        shell_arc('ForwardTubeArmor',[(.275,.205,.187),(.340,.214,.187),(.700,.208,.187),(.800,.190,.184)],low,high,'Ceramic',root)
    for z in (-.258,.808):annulus('TubeBumper',(AXIS[0],AXIS[1],z),.202,.165,.025,'Steel',root,'Z',32)
    annulus('LaunchIndex',(AXIS[0],AXIS[1],.826),.195,.173,.010,'Accent',root,'Z',32)
    empty('Muzzle',(AXIS[0],AXIS[1],.841),root)
    ring=empty('GuidanceRing',(AXIS[0],AXIS[1],.155),root)
    annulus('GuidanceRotor',(0,0,0),.211,.191,.091,'Accent',ring,'Z',32)
    annulus('GuidanceField',(0,0,.053),.214,.197,.009,'Energy',ring,'Z',32)
    for i in range(3):
        angle=i*2*math.pi/3
        obj=box('RotorEncoder',(.217*math.cos(angle),.217*math.sin(angle),0),(.011,.023,.068),'Steel',ring,.002);obj.rotation_euler.y=-angle
    # Offset sighting pod: an open optical channel, with range hardware beneath it.
    sx=.235;sy=.590;sz=-.145
    empty('Sight',(sx,sy,sz),root)
    cylinder('PodCantilever',(.150,.515,-.092),.025,.214,'Steel',root,'X',16)
    profile('PodKeel',[(-.228,.483),(-.196,.545),(-.080,.548),(.053,.508),(.040,.484)],.112,'Dark',root,sx,.006)
    for sign in (-1,1):
        profile('SightPodCheek',[(-.214,.528),(-.212,.591),(-.190,.610),(-.117,.610),(.028,.570),(.028,.529)],.015,'Ceramic',root,sx+sign*.044,.003)
        box('SightIndex',(sx+sign*.041,sy,sz-.035),(.009,.009,.009),'Energy',root,.001)
    cylinder('Rangefinder',(sx,.519,.060),.032,.036,'Steel',root,'Z',20)
    annulus('RangefinderHood',(sx,.519,.085),.037,.022,.022,'Dark',root,'Z',20)
    cylinder('GuidanceOptic',(sx,.519,.091),.017,.005,'Energy',root,'Z',16)
    profile('PodControlPlate',[(-.226,.486),(-.226,.520),(-.218,.530),(-.193,.514),(-.195,.486)],.095,'Accent',root,sx,.003)
    for j in range(3):box('LinkStatus',(sx-.027+j*.027,.526,-.225),(.012,.008,.007),'Energy',root,.001)
    for x in (-.163,.018):
        profile('CradleGusset',[(.470,.238),(.520,.294),(.578,.310),(.642,.252)],.019,'Steel',root,x,.003)
    # Advance the heavy tube assembly clear of head/forearm aim envelopes.
    for obj in root.children:
        if obj not in grip_parts and obj!=cradle:obj.location.y-=.420
    return root,[{'part':'GuidanceRing','axis':'local Z','motion':'rotation','samples':[i*2*math.pi/120 for i in range(120)],'rotation_radians':[0,2*math.pi],'notes':'Free rotation about local Z. Preserve rest translation (-.075,.460,.575), unit scale and all other rotations.'}]


def missile():
    root=empty('TouristMissileRoot')
    b.axial('MissileBody',[(-.413,0,.061,.061),(-.337,0,.091,.091),(.175,0,.091,.091),(.325,0,.073,.073),(.466,0,.029,.029),(.529,0,.003,.003)],'Ceramic',root,16)
    annulus('GuidanceBelt',(0,0,.147),.097,.088,.052,'Dark',root,'Z',16)
    annulus('ArmingBand',(0,0,-.092),.095,.088,.025,'Accent',root,'Z',16)
    # Fixed swept fins fit inside the launcher bore, as well as the collision envelope.
    for i in range(4):
        angle=math.pi/4+i*math.pi/2
        fin=profile('TailFin',[(-.347,.076),(-.347,.140),(-.199,.156),(.018,.087),(-.099,.076)],.012,'Accent',root,edge=.002);fin.rotation_euler.y=-angle
        light=box('FinGuidanceStrip',(-.104*math.sin(angle),.104*math.cos(angle),-.232),(.016,.007,.085),'Steel',root,.001);light.rotation_euler.y=-angle
    annulus('ExhaustBell',(0,0,-.421),.070,.040,.029,'Steel',root,'Z',16)
    cylinder('EngineCore',(0,0,-.421),.029,.005,'Energy',root,'Z',12)
    # Small lateral guidance windows remain below the fixed radial envelope.
    for sign in (-1,1):box('NavigationWindow',(sign*.093,0,.146),(.008,.018,.027),'Energy',root,.001)
    empty('Camera',(0,.020,.600),root);empty('Exhaust',(0,0,-.449),root)
    return root,[]


def views(target,is_missile,defender):
    if not is_missile:b.render_views(target,False,defender);return
    scene,cam,center,span=w.setup_scene(d.bounds());scene.cycles.samples=24;cam.data.ortho_scale=span*1.8
    for label,vector in [('front',(.8,-1,.55)),('side',(1,.1,.35)),('rear',(.6,1,.45))]:
        cam.location=center+Vector(vector)*span*2;cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(target/f'preview-{label}.png');bpy.ops.render.render(write_still=True)
    cam.data.type='PERSP';cam.data.lens=28;cam.location=bpy.data.objects['Camera'].matrix_world.translation;cam.rotation_euler=Vector(xyz((0,0,1))).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(target/'preview-camera.png');bpy.ops.render.render(write_still=True)


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--defender',required=True);p.add_argument('--no-render',action='store_true');p.add_argument('--render-existing',action='store_true');p.add_argument('--only',choices=['tourist-launcher','tourist-missile']);args=p.parse_args(sys.argv[sys.argv.index('--')+1:]);out=Path(args.output).resolve();out.mkdir(parents=True,exist_ok=True);reports=[]
    for name,builder in [('tourist-launcher',launcher),('tourist-missile',missile)]:
        if args.only and args.only!=name:continue
        target=out/name;path=target/f'{name}.glb';is_missile=name=='tourist-missile';bpy.ops.wm.read_factory_settings(use_empty=True)
        if args.render_existing:bpy.ops.import_scene.gltf(filepath=str(path));views(target,is_missile,args.defender);continue
        target.mkdir();a.materials((.55,.13,.065),(.12,.63,.76));root,motions=builder();clean_meshes();bpy.context.view_layer.update();before=d.bounds()
        hands=a.hand_check(args.defender) if not is_missile else None;checks=[{'part':spec['part'],'samples':b.motion_check(spec)} for spec in motions]
        (target/'source-checks.json').write_text(json.dumps({'hands':hands,'motion':checks},indent=2));bpy.ops.wm.save_as_mainfile(filepath=str(target/f'{name}.blend'))
        print(json.dumps({'asset':name,'hands':hands['obstructions'] if hands else [],'motion_hits':[r for check in checks for r in check['samples'] if r['intersections']][:4]}),flush=True)
        assert not hands or not hands['obstructions'];assert all(not row['intersections'] for c in checks for row in c['samples'])
        f.batch_static_meshes();meshes=[o for o in bpy.context.scene.objects if o.type=='MESH'];triangles=0
        for o in meshes:o.data.calc_loop_triangles();triangles+=len(o.data.loop_triangles)
        assert triangles<=(2200 if is_missile else 8000) and len(meshes)<=(6 if is_missile else 12),(name,triangles,len(meshes))
        root_name=root.name;bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',export_yup=True)
        bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False);bpy.ops.import_scene.gltf(filepath=str(path));root=bpy.data.objects[root_name];bpy.context.view_layer.update();after=d.bounds()
        assert max(abs(before[i][j]-after[i][j]) for i in range(3) for j in range(2))<1e-5
        imported_hands=a.hand_check(args.defender,batched=True) if hands else None;checks=[{'part':spec['part'],'samples':b.motion_check(spec)} for spec in motions]
        assert not imported_hands or not imported_hands['obstructions'];assert all(not row['intersections'] for c in checks for row in c['samples'])
        rays={};direction=Vector(xyz((0,0,1)))
        for marker in (['Camera'] if is_missile else ['Muzzle','Sight']):
            origin=bpy.data.objects[marker].matrix_world.translation.copy()
            if marker=='Sight':origin-=direction*.70
            hit,_,_,_,obj,_=bpy.context.scene.ray_cast(bpy.context.evaluated_depsgraph_get(),origin,direction,distance=2)
            rays[marker]={'forward_ray_occluded':hit,'object':obj.name if hit else None}
        assert not any(r['forward_ray_occluded'] for r in rays.values()),(name,rays)
        bounds=[after[0],after[2],[-after[1][1],-after[1][0]]]
        report={'asset':name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'triangles':triangles,'primitives':len(meshes),'bounds_gltf_xyz_m':bounds,'dimensions_gltf_xyz_m':[hi-lo for lo,hi in bounds],'nodes':b.marker_report(root),'motions':motions,'motion_checks':checks,'hand_check':hands,'imported_hand_check':imported_hands,'axis_checks':rays}
        if is_missile:
            points=[o.matrix_world@v.co for o in bpy.context.scene.objects if o.type=='MESH' for v in o.data.vertices];report['max_radial_m']=max(math.hypot(p.x,p.z) for p in points);assert report['max_radial_m']<=.20 and bounds[2][0]>=-.45 and bounds[2][1]<=.55
        (target/'manifest.json').write_text(json.dumps(report,indent=2));reports.append(report);print(json.dumps({'asset':name,'status':'EXPORT_CHECKS_PASS','triangles':triangles,'primitives':len(meshes)}),flush=True)
        if not args.no_render:views(target,is_missile,args.defender)
    if not args.render_existing:(out/'manifest.json').write_text(json.dumps({'units':'meters','up':'Y','forward':'+Z','assets':reports,'scope':'Source and fresh-import geometry, glove and sampled-ring checks. No runtime-camera or continuous motion certification.'},indent=2))


if __name__=='__main__':main()
