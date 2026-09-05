"""Original reactor-response suit with explicit rigid hinges, zero-rest glTF transforms."""
import argparse
import json
import math
import sys
from pathlib import Path
import bpy
import bmesh
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

sys.path.insert(0,str(Path(__file__).resolve().parent))
import axm_fortress_pack as f
import axm_fortress_detail as d
import axm_fortress_weapons as w
from axm_mesh_profiles import octagon


def xyz(p):return (p[0],-p[2],p[1])


def bevel(obj,width,segments=1):
    if width:
        mod=obj.modifiers.new('Armor edge','BEVEL');mod.width=f.bevel_width(obj,width);mod.segments=segments
        bpy.context.view_layer.objects.active=obj;bpy.ops.object.modifier_apply(modifier=mod.name)
    return obj


def box(name,p,size,mat,parent,edge=.005):
    return bevel(f.box(name,xyz(p),(size[0],size[2],size[1]),mat,parent,0),edge)


def sphere(name,p,size,mat,parent):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=12,ring_count=8,radius=1,location=xyz(p))
    obj=bpy.context.object;obj.scale=(size[0],size[2],size[1])
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    for face in obj.data.polygons:face.use_smooth=True
    return f.finish(obj,name,mat,parent)


def cylinder(name,p,radius,length,mat,parent,axis='Y',sides=12):
    bpy.ops.mesh.primitive_cylinder_add(vertices=sides,radius=radius,depth=length,location=xyz(p))
    obj=bevel(f.finish(bpy.context.object,name,mat,parent),min(.006,radius*.15))
    if axis=='X':obj.rotation_euler.y=math.pi/2
    if axis=='Z':obj.rotation_euler.x=math.pi/2
    return obj


def loft(name,levels,mat,parent,edge=.008):
    # Each level is (Y, width X, depth Z, forward Z offset, optional X offset).
    sections=[]
    for level in levels:
        y,width,depth,z,*tail=level;x=tail[0] if tail else 0
        sections.append((y,[(a+x,b-z) for a,b in octagon(width,depth,min(width,depth)*.24)]))
    return d.prism(name,sections,mat,parent,edge)


def plate(name,outline,front,depth,mat,parent,edge=.005):
    # Authored shield silhouette in local XY, extruded through Z.
    verts=[xyz((x,y,z)) for z in (front-depth,front) for x,y in outline];n=len(outline)
    faces=[tuple(reversed(range(n))),tuple(range(n,2*n))]
    faces.extend((i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n))
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update()
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(mesh);bm.free()
    obj=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(obj)
    return bevel(f.finish(obj,name,mat,parent),edge,2)


def band(name,low,high,rx,rz,forward,mat,parent):
    n=13;verts=[]
    for inset in (0,.008):
        for y in (low,high):
            for i in range(n):
                a=math.radians(-58+116*i/(n-1))
                verts.append(xyz(((rx-inset)*math.sin(a),y,(rz-inset)*math.cos(a)+forward)))
    faces=[]
    for i in range(n-1):
        faces.extend([(i,i+1,n+i+1,n+i),(2*n+i,3*n+i,3*n+i+1,2*n+i+1),
                      (i,2*n+i,2*n+i+1,i+1),(n+i,n+i+1,3*n+i+1,3*n+i)])
    faces.extend([(0,n,3*n,2*n),(n-1,3*n-1,4*n-1,2*n-1)])
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update()
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(mesh);bm.free()
    obj=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(obj)
    return bevel(f.finish(obj,name,mat,parent),.002)


def materials():
    f.M={
      'Ceramic':f.material('Ceramic',(.58,.65,.65),.18),
      'Flex':f.material('Flex',(.021,.032,.039),.06),
      'Steel':f.material('Steel',(.20,.27,.30),.78),
      'TeamColor':f.material('TeamColor',(.035,.25,.48),.22),
      'VisorAmber':f.material('VisorAmber',(.74,.34,.035),.28,.45)}
    f.M['Flex'].node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.72
    f.M['Ceramic'].node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.38
    f.M['VisorAmber'].node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.22


def build():
    nodes={};contract={}
    def joint(name,parent,p):
        obj=f.empty(name,xyz(p),nodes.get(parent));nodes[name]=obj
        contract[name]={'parent':parent,'translation_gltf_m':list(p),'rotation_xyzw':[0,0,0,1],'scale':[1,1,1]}
        return obj
    joint('DefenderRoot',None,(0,0,0))
    pelvis=joint('Pelvis','DefenderRoot',(0,.90,0))
    torso=joint('Torso','Pelvis',(0,.18,0))
    head=joint('Head','Torso',(0,.43,0))
    for suffix,s in [('Left',1),('Right',-1)]:
        joint('Shoulder'+suffix,'Torso',(s*.34,.34,0))
        joint('Elbow'+suffix,'Shoulder'+suffix,(0,-.30,0))
        joint('Wrist'+suffix,'Elbow'+suffix,(0,-.28,0))
        joint('GripSocket'+suffix,'Wrist'+suffix,(0,-.08,0))
        joint('Hip'+suffix,'Pelvis',(s*.16,-.02,0))
        joint('Knee'+suffix,'Hip'+suffix,(0,-.42,0))
        joint('Ankle'+suffix,'Knee'+suffix,(0,-.42,0))
    # Fitted abdomen and load belt, leaving femoral hinges free at the sides.
    loft('WaistUndersuit',[(-.085,.31,.235,0),(.0,.37,.255,0),(.085,.29,.235,0),(.13,.27,.22,0)],'Flex',pelvis)
    loft('PelvicBelt',[(.09,.37,.27,0),(.14,.355,.26,0),(.15,.30,.24,0)],'Ceramic',pelvis,.007)
    plate('BeltCenter',[(-.065,.095),(.065,.095),(.052,.155),(-.052,.155)],.151,.028,'Ceramic',pelvis)
    for s in (-1,1):
        box('BeltRecess',(s*.108,.12,.137),(.047,.028,.015),'Flex',pelvis,.004)
        # Short floating fauld protects the groin without a long rigid skirt.
        plate('HipApron',[(s*.012,-.025),(s*.058,-.01),(s*.067,.084),(s*.010,.087)],.116,.025,'Ceramic',pelvis,.006)
    # Shaped thorax; ceramic plates overlap only their own dark undersuit.
    loft('ThoracicUndersuit',[(-.035,.265,.22,0),(.075,.34,.25,0),(.25,.45,.255,0),(.37,.38,.20,0),(.40,.25,.17,0)],'Flex',torso)
    for s in (-1,1):
        outline=[(s*.018,.12),(s*.15,.10),(s*.178,.245),(s*.155,.345),(s*.04,.36)]
        plate('PectoralCeramic',outline,.163,.046,'Ceramic',torso,.014)
        plate('LowerRibPlate',[(s*.03,.045),(s*.147,.04),(s*.175,.11),(s*.033,.12)],.137,.029,'Ceramic',torso,.008)
        plate('ChestIdentity',[(s*.05,.22),(s*.145,.205),(s*.158,.277),(s*.136,.31),(s*.05,.325)],.174,.009,'TeamColor',torso,.004)
        for y in (.063,.091):box('AbdominalBellows',(s*.073,y,.148),(.105,.012,.012),'Flex',torso,.002)
        cylinder('ClavicleJoint',(s*.267,.34,0),.042,.145,'Flex',torso,axis='X')
    cylinder('NeckSeal',(0,.414,0),.063,.10,'Flex',torso,sides=16)
    collar=loft('CollarRim',[(.359,.28,.22,0),(.387,.26,.20,0),(.40,.20,.17,0)],'Ceramic',torso,.006)
    # Sweep the rear collar down, retaining its surface around the neck recess.
    # A horizontal solid rim otherwise meets the helmet when the head looks up
    # relative to a deeply folded torso.
    for v in collar.data.vertices:
        rear=max(0,min(1,(.08+v.co.y)/.16));v.co.z-=.085*rear
    cylinder('ChestCoupling',(0,.155,.163),.027,.028,'Steel',torso,axis='Z',sides=12)
    for y in (.205,.245,.285):box('SternumCatch',(0,y,.151),(.023,.018,.022),'Steel',torso,.004)
    # Asymmetric rescue equipment and a compact back-mounted capacitor.
    loft('PackShockMount',[(-.005,.29,.11,-.157),(.30,.30,.13,-.174),(.355,.22,.105,-.17)],'Flex',torso,.009)
    loft('CapacitorHousing',[(.025,.28,.17,-.216),(.29,.30,.18,-.227),(.34,.245,.14,-.216)],'Ceramic',torso,.009)
    cylinder('CapacitorSpine',(.142,.178,-.246),.044,.263,'Steel',torso,sides=12)
    for y in (.052,.304):cylinder('CapacitorCap',(.142,y,-.246),.050,.029,'Flex',torso,sides=12)
    plate('BackIdentity',[(-.113,.07),(.081,.07),(.105,.265),(-.108,.283)],-.322,.008,'TeamColor',torso,.008)
    box('PackServiceInset',(-.055,.039,-.307),(.14,.032,.025),'Steel',torso,.006)
    for x in (-.09,-.05,-.01):box('PackLatch',(x,.040,-.326),(.016,.021,.019),'Flex',torso,.003)
    loft('RescueCanister',[(-.01,.075,.11,.016),(.15,.08,.10,.016),(.18,.064,.083,.016)],'Steel',torso,.006).location.x=-.234
    box('RescueCanisterStrap',(-.234,.078,.067),(.080,.032,.018),'Flex',torso,.003)
    # Human helmet profile: rounded crown, compact amber eye band, cheek protection.
    loft('HelmetShell',[(.025,.19,.20,-.009),(.07,.255,.255,-.010),(.20,.265,.258,-.017),(.263,.205,.20,-.021),(.29,.10,.095,-.025)],'Ceramic',head,.009)
    band('VisorGasket',.122,.194,.145,.148,.023,'Flex',head)
    band('AmberVisor',.135,.181,.137,.152,.026,'VisorAmber',head)
    plate('RespiratorChin',[(-.086,.034),(.086,.034),(.11,.072),(.073,.116),(-.073,.116),(-.11,.072)],.158,.039,'Ceramic',head,.011)
    for x in (-.048,-.024,0,.024,.048):box('BreatherSlot',(x,.070,.181),(.009,.031,.008),'Flex',head,.002)
    for s in (-1,1):
        cylinder('HelmetEarSeal',(s*.127,.10,-.009),.050,.021,'Flex',head,axis='X',sides=12)
        cylinder('EarCeramicCap',(s*.14,.10,-.009),.037,.015,'Ceramic',head,axis='X',sides=12)
    # Segment-specific materials keep the whole suit at 35 draw primitives.
    for suffix,s in [('Left',1),('Right',-1)]:
        upper=nodes['Shoulder'+suffix];fore=nodes['Elbow'+suffix];hand=nodes['Wrist'+suffix]
        thigh=nodes['Hip'+suffix];shin=nodes['Knee'+suffix];boot=nodes['Ankle'+suffix]
        sphere('ShoulderGasket',(0,0,0),(.067,.068,.067),'Flex',upper)
        loft('UpperSleeve',[(-.273,.092,.105,0),(-.19,.108,.117,0),(-.05,.12,.12,0),(.015,.105,.105,0)],'Flex',upper,.004)
        loft('DeltoidCup',[(-.075,.14,.145,-.004,s*.025),(.025,.155,.155,-.008,s*.031),(.063,.118,.125,-.007,s*.029)],'Ceramic',upper,.012)
        plate('ShoulderIdentity',[(s*-.04,-.055),(s*.063,-.055),(s*.091,.021),(s*.025,.049),(s*-.049,.025)],.080,.012,'TeamColor',upper,.006)
        loft('BicepPlate',[(-.208,.090,.064,.045),(-.145,.110,.082,.045),(-.09,.110,.078,.042)],'Ceramic',upper,.007)
        sphere('ElbowSeal',(0,0,0),(.051,.054,.051),'Flex',fore)
        cylinder('ElbowAxle',(0,0,0),.037,.114,'Flex',fore,axis='X',sides=12)
        loft('ForearmSleeve',[(-.265,.075,.084,0),(-.10,.090,.11,0),(-.025,.085,.095,0)],'Flex',fore,.003)
        loft('ForearmCeramic',[(-.205,.080,.095,.015),(-.145,.108,.132,.018),(-.085,.110,.125,.014)],'Ceramic',fore,.009)
        for y in (-.17,-.145):box('ForearmSeam',(0,y,.086),(.078,.008,.008),'Flex',fore,.002)
        # Closed gloves have a rounded palm, four curled fingers and an opposed thumb.
        sphere('WristSeal',(0,0,0),(.039,.035,.043),'Flex',hand)
        sphere('GlovePalm',(0,-.068,-.045),(.051,.059,.022),'Flex',hand)
        for i in range(4):
            y=-.033-i*.024
            sphere('FingerKnuckle',(s*.028,y,.032),(.031,.012,.023),'Flex',hand)
            sphere('CurledFinger',(s*-.012,y,.043),(.031,.011,.018),'Flex',hand)
            sphere('FingerTip',(s*-.039,y,.022),(.015,.010,.020),'Flex',hand)
        sphere('OpposedThumb',(s*-.046,-.041,-.010),(.022,.027,.025),'Flex',hand)
        sphere('ThumbTip',(s*-.032,-.067,.006),(.021,.018,.024),'Flex',hand)
        plate('GloveBackplate',[(-.036,-.11),(.036,-.11),(.043,-.062),(.025,-.038),(-.025,-.038),(-.043,-.062)],-.069,.011,'Ceramic',hand,.007)
        # Legs retain a dark gap around each knee and ankle hinge.
        sphere('HipSeal',(0,-.025,0),(.083,.083,.09),'Flex',thigh)
        loft('ThighUndersuit',[(-.374,.121,.127,0),(-.25,.153,.165,0),(-.065,.18,.187,0),(-.008,.149,.163,0)],'Flex',thigh,.005)
        # Front coverage keeps its silhouette; hidden rear wrap is relieved so
        # the two armor shells can fold past each other around the knee.
        loft('ThighCeramic',[(-.334,.112,.065,.0555),(-.26,.162,.085,.0685),(-.112,.174,.085,.0655)],'Ceramic',thigh,.01)
        for y in (-.19,-.22):box('ThighServiceSeam',(0,y,.111),(.107,.010,.009),'Flex',thigh,.002)
        sphere('KneeSeal',(0,0,0),(.063,.065,.061),'Flex',shin)
        cylinder('KneeAxle',(0,0,0),.038,.137,'Flex',shin,axis='X',sides=12)
        plate('KneeShield',[(-.063,-.055),(.063,-.055),(.080,.026),(.043,.064),(-.043,.064),(-.080,.026)],.103,.038,'Ceramic',shin,.01)
        loft('ShinUndersuit',[(-.386,.078,.09,0),(-.24,.10,.13,0),(-.05,.116,.13,0)],'Flex',shin,.004)
        loft('TibialPlate',[(-.232,.087,.038,.048),(-.17,.127,.060,.065),(-.075,.136,.054,.0595)],'Ceramic',shin,.009)
        for y in (-.18,-.21):
            face=.095+(y+.17)*(.028/.062)
            box('TibialRecess',(0,y,face+.001),(.057,.012,.008),'Flex',shin,.002)
        sphere('AnkleSeal',(0,.008,0),(.043,.045,.050),'Flex',boot)
        loft('BootSole',[(-.04,.154,.31,.063),(-.012,.157,.316,.064),(.018,.148,.299,.063)],'Flex',boot,.005)
        cap=loft('BootUpper',[(.012,.138,.275,.058),(.070,.139,.253,.054),(.108,.093,.145,.014)],'Ceramic',boot,.012)
        # A sloped ceramic toe leaves the sole footprint intact and clears the
        # shin during deep ankle flexion, while retaining a closed toe cap.
        for v in cap.data.vertices:
            toe=max(0,min(1,(-v.co.y-.10)/.085));height=max(0,min(1,(v.co.z-.012)/.058))
            v.co.z-=.03*toe*height
        for z in (.030,.066,.102):box('BootInstepGroove',(0,.093,z),(.083,.010,.014),'Flex',boot,.002)
        box('BootHeelSeam',(0,.037,-.093),(.111,.035,.015),'Flex',boot,.004)
    return nodes,contract


def world_frame(direction,normal):
    z=-direction.normalized();x=normal.normalized();y=z.cross(x).normalized();x=y.cross(z).normalized()
    return Matrix(((x.x,y.x,z.x),(x.y,y.y,z.y),(x.z,y.z,z.z))).to_quaternion()


def ik(chain,target,pole):
    upper,lower,end=[bpy.data.objects[n] for n in chain]
    bpy.context.view_layer.update();start=upper.matrix_world.translation.copy();target=Vector(xyz(target))
    direction=target-start;distance=direction.length;l1=lower.location.length;l2=end.location.length
    assert abs(l1-l2)+.0001<distance<l1+l2-.0001,(chain,distance,l1,l2)
    direction.normalize();hint=Vector(xyz(pole));hint=(hint-direction*hint.dot(direction)).normalized()
    along=(l1*l1-l2*l2+distance*distance)/(2*distance);height=math.sqrt(max(0,l1*l1-along*along))
    elbow=start+direction*along+hint*height
    first=(elbow-start).normalized();second=(target-elbow).normalized();normal=first.cross(second).normalized()
    # Pick a consistent local-X hinge sign, retaining a single elbow/knee bend axis.
    if normal.x<0:normal=-normal
    q1=world_frame(first,normal);q2=world_frame(second,normal)
    upper.rotation_mode='QUATERNION';upper.rotation_quaternion=upper.parent.matrix_world.to_quaternion().inverted()@q1
    lower.rotation_mode='QUATERNION';lower.rotation_quaternion=q1.inverted()@q2
    end.rotation_mode='QUATERNION';end.rotation_quaternion=q2.inverted()
    bpy.context.view_layer.update()


def set_pose(name):
    for obj in bpy.context.scene.objects:
        if obj.type=='EMPTY':obj.rotation_mode='XYZ';obj.rotation_euler=(0,0,0)
    bpy.data.objects['Pelvis'].location=xyz((0,.9,0))
    if name=='bent-knee':
        for node,deg in [('HipLeft',-40),('KneeLeft',75),('AnkleLeft',-35),('ShoulderLeft',15),('ShoulderRight',-15)]:
            bpy.data.objects[node].rotation_euler.x=math.radians(deg)
    elif name=='aim':
        ik(('ShoulderRight','ElbowRight','WristRight'),(-.12,1.36,.36),(-.2,-1,1))
        ik(('ShoulderLeft','ElbowLeft','WristLeft'),(.04,1.34,.45),(.2,-1,1))
    elif name=='revive':
        bpy.data.objects['Pelvis'].location=xyz((0,.54,0))
        bpy.data.objects['Torso'].rotation_euler.x=math.radians(20)
        ik(('HipRight','KneeRight','AnkleRight'),(-.16,.112,-.30),(0,0,1))
        # Kneeling instep rests on the floor; the boot follows plantar flexion.
        ankle=bpy.data.objects['AnkleRight'];ankle.rotation_quaternion=ankle.parent.matrix_world.to_quaternion().inverted()@Matrix.Rotation(math.pi,4,'X').to_quaternion()
        ik(('HipLeft','KneeLeft','AnkleLeft'),(.16,.04,.34),(0,0,1))
        ik(('ShoulderRight','ElbowRight','WristRight'),(-.03,.71,.43),(-.3,-1,.7))
        ik(('ShoulderLeft','ElbowLeft','WristLeft'),(.24,.80,.42),(.4,-1,.4))
    bpy.context.view_layer.update()


def rigid_intersections():
    meshes=[o for o in bpy.context.scene.objects if o.type=='MESH' and o.data.materials and o.data.materials[0].name.split('.')[0] not in ('Flex','VisorAmber')]
    trees={o:BVHTree.FromPolygons([o.matrix_world@v.co for v in o.data.vertices],[list(p.vertices) for p in o.data.polygons],all_triangles=False,epsilon=.00001) for o in meshes}
    hits=[]
    for i,a in enumerate(meshes):
        for b in meshes[i+1:]:
            if a.parent==b.parent:continue
            overlap=trees[a].overlap(trees[b])
            if overlap:hits.append({'a':a.name,'b':b.name,'triangle_pairs':len(overlap)})
    return hits


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True)
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:]);out=Path(args.output).resolve();out.mkdir(parents=True,exist_ok=False)
    bpy.ops.wm.read_factory_settings(use_empty=True);materials();nodes,contract=build();bpy.context.view_layer.update()
    source_bounds=d.bounds();f.batch_static_meshes();meshes=[o for o in bpy.context.scene.objects if o.type=='MESH'];triangles=0
    for obj in meshes:obj.data.calc_loop_triangles();triangles+=len(obj.data.loop_triangles)
    assert triangles<=25000 and len(meshes)<=35,(triangles,len(meshes))
    bpy.ops.export_scene.gltf(filepath=str(out/'defender.glb'),export_format='GLB',export_yup=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'defender.blend'))
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=str(out/'defender.glb'));actual=d.bounds()
    assert max(abs(source_bounds[i][j]-actual[i][j]) for i in range(3) for j in range(2))<.001
    assert abs(actual[2][0])<.001 and abs(actual[2][1]-1.8)<.001,actual
    for name,spec in contract.items():
        obj=bpy.data.objects[name]
        assert obj.rotation_euler.to_quaternion().angle<.0001,name
        assert (obj.location-Vector(xyz(spec['translation_gltf_m']))).length<.0001,name
    report={'units':'meters','up':'Y','forward':'+Z','triangles':triangles,'primitives':len(meshes),
            'bounds_gltf_xyz_m':[actual[0],actual[2],[-actual[1][1],-actual[1][0]]],
            'nodes':contract,'roundtrip':'vertex bounds within1mm; all specified rest nodes zero rotation and exact translation',
            'materials':{name:'seat tint identity panels only' if name=='TeamColor' else 'fixed suit material' for name in f.M},'poses':{}}
    scene,cam,center,span=w.setup_scene(actual);cam.data.ortho_scale=2.85
    for pose,angle in [('front',12),('rear',192),('bent-knee',65),('aim',40),('revive',65)]:
        set_pose(pose);hits=rigid_intersections()
        assert not hits,(pose,hits)
        report['poses'][pose]={'rigid_intersections':hits,'note':'soft seals and same-segment layer overlaps excluded'}
        posed=d.bounds();aim=Vector((0,-.08,.9)) if pose!='revive' else Vector((0,-.06,.65))
        a=math.radians(angle);cam.location=aim+Vector((math.sin(a),-math.cos(a),.30))*4
        cam.rotation_euler=(aim-cam.location).to_track_quat('-Z','Y').to_euler()
        scene.render.filepath=str(out/f'preview-{pose}.png');bpy.ops.render.render(write_still=True)
        (out/'manifest.json').write_text(json.dumps(report,indent=2))
    set_pose('front')
    report['limitations']=['Rigid segments only; no skin, animation clips or collision geometry','Material factors and geometry; no textures or LODs','Finger forms are fixed closed grips; game owns hand/weapon alignment','Pose intersection reports are geometric probes, not exhaustive articulation clearance certification']
    (out/'manifest.json').write_text(json.dumps(report,indent=2))


if __name__=='__main__':main()
