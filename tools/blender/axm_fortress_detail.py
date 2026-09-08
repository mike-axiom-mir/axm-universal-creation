"""Fortress architectural and first-person detail kit. Original parametric source."""
import argparse
import json
import math
import sys
from pathlib import Path
import bpy
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
import axm_fortress_pack as f
from axm_mesh_profiles import octagon


def prism(name, sections, mat, parent, bevel=.02):
    """Loft matching XY perimeter sections along Z, with deliberate silhouette."""
    verts=[(x,y,z) for z,poly in sections for x,y in poly]
    n=len(sections[0][1]); faces=[tuple(reversed(range(n)))]
    for j in range(len(sections)-1):
        for i in range(n): faces.append((j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i))
    faces.append(tuple(range((len(sections)-1)*n,len(sections)*n)))
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update()
    o=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(o)
    bpy.context.view_layer.objects.active=o;o.select_set(True)
    return f.finish(o,name,mat,parent,bevel)


def shell(name,loc,w,d,h,mat,parent,chamfer=.2,taper=.9,bevel=.025):
    o=prism(name,[(0,octagon(w,d,chamfer)),(h*.72,octagon(w,d,chamfer)),(h,octagon(w*taper,d*taper,chamfer*taper))],mat,parent,bevel)
    o.location=loc
    return o


def bolt(name,loc,parent,r=.055):
    o=f.cyl(name,loc,r,.035,'silver',parent,6);o.rotation_euler.x=math.pi/2
    return o


def face_text(body,loc,size,parent,mat='silver',name='Marking'):
    cu=bpy.data.curves.new(name,'FONT');cu.body=body;cu.size=size;cu.extrude=.0005;cu.align_x='CENTER'
    o=bpy.data.objects.new(name,cu);bpy.context.collection.objects.link(o)
    o.location=loc;o.rotation_euler=(math.pi/2,0,0)
    bpy.context.view_layer.objects.active=o;bpy.ops.object.select_all(action='DESELECT');o.select_set(True)
    bpy.ops.object.convert(target='MESH');f.finish(o,name,mat,parent)


def gate(sector='N / 01'):
    root=f.empty('GateRoot');shutter=f.empty('Shutter',parent=root)
    # All frame structure is outside the 10 x 5 meter clear opening.
    for s in (-1,1):
        shell('Foot', (s*5.5,0,0),1,2.1,.65,'dark',root,chamfer=.12)
        shell('LoadColumn',(s*5.5,0,.25),.94,1.55,5.3,'steel',root,chamfer=.15,taper=.94)
        shell('ColumnArmor',(s*5.5,-.78,.75),.8,.2,3.9,'silver',root,chamfer=.08,taper=.85)
        f.box('RecessedPowerTrench',(s*5.5,-.904,2.8),(.24,.045,3.6),'dark',root,.012)
        f.box('PowerConduit',(s*5.5,-.935,2.8),(.065,.025,3.35),'cyan',root,.006)
        for z in (1,2.1,3.2,4.3):
            f.box('ConduitClamp',(s*5.5,-.965,z),(.38,.06,.13),'steel',root,.018)
        for z in (.8,4.55):
            for dx in (-.26,.26): bolt('ColumnFastener',(s*5.5+dx,-.92,z),root)
        # Outer rail is visible from the reverse side as well.
        f.box('ShutterGuide',(s*5.04,.18,2.5),(.06,.3,5),'dark',root,.01)
        shell('ServiceBox',(s*5.5,.78,1.1),.8,.3,1.25,'amber',root,.07)
    shell('Header',(0,0,5),12,1.7,2,'steel',root,.35,.98,.04)
    f.box('HeaderInset',(0,-.862,5.83),(8.3,.08,.88),'dark',root,.07)
    for s in (-1,1):
        f.box('HeaderBand',(s*4.65,-.91,5.8),(1,.12,.44),'amber',root,.04)
    face_text(sector,(0,-.923,5.60),.48,root)
    f.box('ClearanceLight',(0,-.9,5.10),(8.3,.09,.07),'cyan',root,.012)
    for x in (-4,-2,0,2,4):
        shell('RoofRib',(x,0,6.65),.55,1.65,.33,'silver',root,.12,.85)
    # Closed rest state. Translation by -5.15 meters opens below the floor.
    f.box('ShutterBacking',(0,.08,2.5),(9.96,.24,5),'dark',shutter,.02)
    for row in range(5):
        z=.5+row
        for s in (-1,1):
            shell('DoorPanel',(s*2.48,-.02,z-.46),4.88,.35,.91,'steel',shutter,.12,.97,.035)
            f.box('PanelInset',(s*2.48,-.21,z),(4.35,.035,.49),'silver' if row%2==0 else 'steel',shutter,.07)
            for x in (s*.27,s*4.63): bolt('PanelLock',(x,-.25,z),shutter,.045)
        f.box('DoorSpine',(0,-.27,z),(.19,.14,.8),'dark',shutter,.015)
    for s in (-1,1):
        for i in range(5):
            mark=f.box('ServiceStripe',(s*(2+i*.36),-.26,.42),(.18,.02,.44),'amber',shutter,.008)
            mark.rotation_euler.y=-.45
    face_text('KEEP',(-1,-.31,2.23),.24,shutter,'amber')
    face_text('CLEAR',(1,-.31,2.23),.24,shutter,'amber')
    for z in (.5,1.5,2.5,3.5,4.5):
        f.box('RearDoorRib',(0,.235,z),(9.5,.09,.16),'steel',shutter,.025)
    for s in (-1,1):
        f.box('RearSpine',(s*2.8,.29,2.5),(.24,.12,4.75),'silver',shutter,.025)
        for z in (1,4):
            bolt('RearLock',(s*2.8,.375,z),shutter,.08)
        f.box('RearHeaderService',(s*3.1,.86,5.85),(3.5,.10,.88),'dark',root,.06)
        for i in range(4):
            f.box('HeaderCoolingFin',(s*3.1,.925,5.57+i*.17),(3.1,.045,.06),'silver',root,.012)
    face_text(sector,(0,-.932,6.33),.19,root,'amber')
    return root,{'Shutter':{'translation_y_closed':0,'translation_y_open':-5.15,'animation':'procedural translation; no clip'}},[12,7,2.1]


def bastion():
    r=f.empty('BastionRoot')
    shell('Foundation',(0,0,0),6,6,.42,'dark',r,.8,.99,.05)
    shell('PressureBody',(0,0,.3),5.85,5.85,2.8,'steel',r,.72,.91,.06)
    shell('RoofShoulder',(0,0,2.95),5.9,5.9,.7,'silver',r,.8,.85,.04)
    shell('RecessedRoof',(0,0,3.57),4.9,4.9,.14,'dark',r,.45,1,.02)
    shell('Hatch',(0,0,3.71),2.1,2.1,.25,'steel',r,.4,.96,.025)
    # Four authored faces rotate as units; component structure remains explicit.
    for i in range(4):
        side=f.empty(f'Face_{i}',parent=r);side.rotation_euler.z=i*math.pi/2
        shell('InsetFrame',(0,-2.85,.73),3.8,.13,1.78,'dark',side,.16,.94,.025)
        shell('ServicePanel',(0,-2.96,.91),3.37,.11,1.4,'steel',side,.18,.94,.03)
        f.box('VentRecess',(0,-3.026,1.73),(2.5,.012,.74),'dark',side,.06)
        for j in range(5):
            f.box('VentLouver',(0,-3.04,1.46+j*.13),(2.28,.045,.055),'silver',side,.012)
        for x in (-1.72,1.72):
            f.box('PowerSlot',(x,-2.96,1.77),(.18,.08,1.63),'dark',side,.014)
            f.box('PowerStrip',(x,-3.01,1.79),(.047,.035,1.42),'cyan',side,.006)
        for x in (-1.45,1.45):
            for z in (1.03,2.22): bolt('PanelScrew',(x,-3.04,z),side,.042)
        face_text('SERVICE / 04',(0,-3.04,1.12),.15,side,'amber')
        for s in (-1,1):
            shell('CornerBrace',(s*2.14,-2.46,.35),.53,.54,2.45,'steel',side,.09,.78,.04)
            f.box('BraceMark',(s*2.14,-2.742,.76),(.35,.024,.19),'amber',side,.015)
    for x in (-1.7,1.7):
        for y in (-1.7,1.7):
            f.cyl('RoofLatch',(x,y,3.77),.13,.13,'amber',r,8)
    bpy.context.view_layer.update()
    for face in [o for o in r.children if o.type=='EMPTY']:
        for child in list(face.children):
            world=child.matrix_world.copy();child.parent=r;child.matrix_world=world
    return r,{},[6.12,3.96,6.12]


def rebounder():
    r=f.empty('RebounderRoot');grip=f.empty('Grip',(0,.14,.07),r)
    # Compact receiver, offset power cell and exposed horizontal coin rotor.
    shell('Receiver',(0,-.02,.08),.18,.58,.12,'steel',r,.045,.85,.009)
    shell('GripArmor',(0,.16,-.18),.105,.13,.29,'dark',r,.025,.93,.006)
    for i in range(5):
        f.box('GripTread',(0,.230,-.13+i*.034),(.082,.012,.011),'rubber',r,.002)
    shell('Heel',(0,.16,-.19),.12,.145,.035,'silver',r,.025,1,.004)
    # Curved rotor containment in plan: split ring leaves a feeding channel forward.
    rotor=f.empty('DiscRotor',(0,-.045,.22),r)
    for i in range(3):
        o=f.cyl('EnergyCoin',(0,0,i*.024),.101,.013,'cyan' if i==1 else 'silver',rotor,48)
        # small cylinder bevel is clamped to avoid changing thin disc scale.
    for i in range(16):
        a=math.radians(35+i*290/15)
        o=f.box('RotorClamp',(.139*math.sin(a),.139*math.cos(a),.23),(.026,.035,.085),'amber' if i%5==0 else 'steel',r,.005)
        o.rotation_euler.z=-a
    f.cyl('RotorHub',(0,-.045,.302),.032,.038,'dark',r,16)
    # Broad fork accelerator makes the disc weapon readable in first person.
    for s in (-1,1):
        rail=shell('AcceleratorRail',(s*.065,-.24,.145),.053,.37,.084,'silver',r,.012,.86,.006)
        f.box('RailChannel',(s*.065,-.27,.234),(.018,.29,.012),'dark',r,.002)
        f.box('RailEnergy',(s*.065,-.26,.245),(.009,.23,.006),'cyan',r,.001)
        f.box('MuzzleJaw',(s*.065,-.425,.185),(.073,.045,.072),'dark',r,.009)
        for j in range(3):
            f.box('CoolingTooth',(s*.096,-.18-j*.063,.177),(.024,.035,.035),'steel',r,.004)
    f.empty('Muzzle',(0,-.453,.186),r)
    # Functional side energy cell, cap and service lettering.
    cell=f.cyl('PowerCell',(.125,.12,.10),.043,.21,'amber',r,24);cell.rotation_euler.x=math.pi/2
    for y in (.012,.225):
        o=f.cyl('CellCap',(.125,y,.10),.048,.025,'dark',r,16);o.rotation_euler.x=math.pi/2
    f.box('TriggerGuardFloor',(0,.06,-.083),(.034,.2,.025),'silver',r,.004)
    f.box('TriggerGuardFront',(0,-.03,-.02),(.034,.025,.12),'silver',r,.004)
    f.box('Trigger',(0,.055,.003),(.025,.029,.08),'dark',r,.004)
    shell('RearSight',(0,.19,.203),.105,.045,.055,'dark',r,.013,.83,.004)
    for s in (-1,1):f.box('SightDot',(s*.036,.213,.24),(.009,.005,.009),'cyan',r,.001)
    face_text('RB / 02',(0,-.316,.115),.022,r,'amber')
    return r,{'Grip':{'purpose':'hand attachment'},'Muzzle':{'purpose':'projectile origin'},'DiscRotor':{'axis':'local Y','purpose':'procedural rotor motion'}},[.34,.53,.75]


def materials():
    f.M={k:f.material(k,c,m,e) for k,c,m,e in [
        ('steel',(.08,.115,.15),.75,0),('dark',(.019,.028,.037),.55,0),
        ('silver',(.32,.4,.45),.8,0),('amber',(.62,.27,.035),.5,0),
        ('cyan',(.018,.62,.85),.15,1.8),('rubber',(.018,.02,.022),0,0)]}
    f.M['dark'].node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.65
    f.M['rubber'].node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.9


def bounds():
    bpy.context.view_layer.update()
    # Rotated aggregate bounding boxes overestimate joined geometry. Measure vertices.
    pts=[o.matrix_world@v.co for o in bpy.context.scene.objects if o.type=='MESH' for v in o.data.vertices]
    return [[min(p[i] for p in pts),max(p[i] for p in pts)] for i in range(3)]


def frame_meshes(camera, margin=1.12):
    """Fit the actual posed mesh projection, including an underground shutter."""
    bpy.context.view_layer.update()
    q=camera.rotation_euler.to_quaternion()
    pts=[q.inverted()@(o.matrix_world@v.co) for o in bpy.context.scene.objects if o.type=='MESH' for v in o.data.vertices]
    lo=[min(p[i] for p in pts) for i in (0,1)];hi=[max(p[i] for p in pts) for i in (0,1)]
    eye=q.inverted()@camera.location
    camera.location+=q@Vector(((lo[0]+hi[0])/2-eye.x,(lo[1]+hi[1])/2-eye.y,0))
    render=bpy.context.scene.render
    camera.data.ortho_scale=max(hi[0]-lo[0],(hi[1]-lo[1])*render.resolution_x/render.resolution_y)*margin


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True)
    p.add_argument('--sector-variants',action='store_true',help='only E/02, S/03, W/04 gates; identical architecture')
    p.add_argument('--architecture-repair',action='store_true',help='all four sector gates and bastion with the current geometry fixes')
    args=p.parse_args(sys.argv[sys.argv.index('--')+1:]);out=Path(args.output).resolve();out.mkdir(parents=True,exist_ok=False)
    report=[]
    builders=[('east-gate',lambda:gate('E / 02')),('south-gate',lambda:gate('S / 03')),('west-gate',lambda:gate('W / 04'))] if args.sector_variants else [('north-gate',gate),('corner-bastion',bastion),('rebounder',rebounder)]
    if args.architecture_repair:
        builders=[('north-gate',gate),('east-gate',lambda:gate('E / 02')),('south-gate',lambda:gate('S / 03')),('west-gate',lambda:gate('W / 04')),('corner-bastion',bastion)]
    for name,builder in builders:
        bpy.ops.wm.read_factory_settings(use_empty=True);materials()
        root,contract,_=builder();bpy.context.view_layer.update();f.batch_static_meshes()
        original=bounds();triangles=0
        for o in bpy.context.scene.objects:
            if o.type=='MESH':o.data.calc_loop_triangles();triangles+=len(o.data.loop_triangles)
        assert triangles<=35000,(name,triangles)
        target=out/name;target.mkdir()
        bpy.ops.export_scene.gltf(filepath=str(target/f'{name}.glb'),export_format='GLB',export_yup=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(target/f'{name}.blend'))
        bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
        bpy.ops.import_scene.gltf(filepath=str(target/f'{name}.glb'))
        actual=bounds();assert max(abs(original[i][j]-actual[i][j]) for i in range(3) for j in range(2))<.001
        assert all(bpy.data.objects.get(n) for n in contract)
        report.append({'asset':name,'triangles':triangles,'bounds_blender_xyz':actual,
            'dimensions_gltf_xyz_m':[actual[0][1]-actual[0][0],actual[2][1]-actual[2][0],actual[1][1]-actual[1][0]],
            'nodes':contract,'up':'Y','forward':'+Z','roundtrip':'bounds and named pivots PASS'})
        # Render from a fresh import, centered on actual geometry, close enough for shape inspection.
        scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=32
        scene.render.resolution_x=1100;scene.render.resolution_y=850;scene.render.resolution_percentage=100
        world=bpy.data.worlds.new('InspectionWorld');scene.world=world;world.use_nodes=True
        world.node_tree.nodes['Background'].inputs[0].default_value=(.085,.1,.12,1)
        span=max(v[1]-v[0] for v in actual);center=Vector(tuple((a+b)/2 for a,b in actual))
        for vec,energy in [((1,-1,1.5),850),((-1,-.4,.7),500),((.5,1,1.1),900)]:
            bpy.ops.object.light_add(type='AREA',location=center+Vector(vec)*span)
            o=bpy.context.object;o.data.energy=energy*span*span/12;o.data.size=span
            o.rotation_euler=(center-o.location).to_track_quat('-Z','Y').to_euler()
        bpy.ops.object.camera_add();cam=bpy.context.object;scene.camera=cam;cam.data.type='ORTHO';cam.data.ortho_scale=span*1.28
        for angle in (25,205):
            a=math.radians(angle);cam.location=center+Vector((math.sin(a),-math.cos(a),.6))*span*1.7
            cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler()
            scene.render.filepath=str(target/f'preview-{angle}.png');bpy.ops.render.render(write_still=True)
        if name.endswith('-gate'):
            bpy.data.objects['Shutter'].location.z=-5.15
            a=math.radians(25);cam.location=center+Vector((math.sin(a),-math.cos(a),.4))*span*1.7
            cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler()
            frame_meshes(cam)
            scene.render.filepath=str(target/'preview-open.png');bpy.ops.render.render(write_still=True)
    (out/'manifest.json').write_text(json.dumps({'assets':report,'truth':'fresh-import structure verified; in-game quality review pending'},indent=2))


if __name__=='__main__':main()
