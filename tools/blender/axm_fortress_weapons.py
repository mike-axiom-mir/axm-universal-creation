"""Bounded Relay Rifle / Pinball Cannon assets and unchanged Rebounder sight study."""
import argparse
import json
import math
import sys
from pathlib import Path
import bpy
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
import axm_fortress_pack as f
import axm_fortress_detail as d


def sphere(name,loc,size,material,parent):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24,ring_count=12,radius=1,location=loc)
    o=bpy.context.object;o.scale=size
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    for p in o.data.polygons:p.use_smooth=True
    return f.finish(o,name,material,parent)


def hoop(name,loc,radius,tube,material,parent,axis='Y'):
    bpy.ops.mesh.primitive_torus_add(major_segments=32,minor_segments=8,major_radius=radius,minor_radius=tube,location=loc)
    o=bpy.context.object
    if axis=='Y':o.rotation_euler.x=math.pi/2
    for p in o.data.polygons:p.use_smooth=True
    return f.finish(o,name,material,parent)


def handle(root,front=.14):
    f.empty('Grip',(0,front,.07),root)
    d.shell('GripArmor',(0,front,-.18),.105,.135,.29,'rubber',root,.025,.9,.005)
    for z in (-.12,-.075,-.03):f.box('GripBand',(0,front+.073,z),(.089,.014,.015),'dark',root,.003)
    d.shell('GripHeel',(0,front,-.19),.124,.15,.028,'silver',root,.025,1,.005)
    f.box('GuardFloor',(0,front-.075,-.08),(.03,.21,.025),'silver',root,.005)
    f.box('GuardFront',(0,front-.17,-.015),(.03,.025,.12),'silver',root,.005)
    f.box('Trigger',(0,front-.065,.005),(.025,.025,.08),'dark',root,.004)


def relay():
    r=f.empty('RelayRoot');handle(r)
    # Narrow fork with elevated orb lattice and underslung pulse capacitor.
    d.shell('Keel',(0,-.13,.08),.15,.9,.095,'steel',r,.025,.91,.007)
    d.shell('RearReceiver',(0,.16,.17),.17,.28,.13,'silver',r,.035,.88,.007)
    orb=f.empty('OrbChamber',(0,-.10,.255),r)
    sphere('ContainedOrb',(0,0,0),(.083,.116,.083),'violet',orb)
    for y in (-.105,.105):hoop('FieldCollar',(0,y,0),.105,.017,'silver',orb)
    for s in (-1,1):
        d.shell('ResonatorRail',(s*.08,-.36,.13),.044,.57,.105,'steel',r,.012,.9,.006)
        f.box('PhaseStrip',(s*.08,-.36,.237),(.012,.49,.009),'cyan',r,.002)
        f.box('LatticeSpine',(s*.107,-.10,.255),(.025,.24,.024),'silver',r,.004)
        for j in range(4):
            f.box('ResonatorVane',(s*.115,-.28-j*.076,.17),(.045,.038,.058),'silver',r,.005)
    # Small circular precision beam aperture within a compact wedge nose.
    d.shell('BeamNose',(0,-.67,.105),.2,.135,.18,'silver',r,.029,.85,.008)
    o=f.cyl('BeamLens',(0,-.742,.205),.032,.018,'cyan',r,32);o.rotation_euler.x=math.pi/2
    hoop('BeamBaffle',(0,-.75,.205),.045,.011,'dark',r)
    f.empty('Muzzle',(0,-.766,.205),r)
    sphere('PulseReservoir',(0,-.25,.07),(.063,.20,.055),'dark',r)
    # Offset optic avoids the orb silhouette; this is a frame, no fake glass plane.
    f.empty('Sight',(0,.23,.41),r)
    for s in (-1,1):f.box('OpticUpright',(s*.045,.21,.36),(.014,.035,.115),'dark',r,.003)
    f.box('OpticBridge',(0,.21,.415),(.106,.035,.014),'silver',r,.003)
    f.box('OpticBase',(0,.21,.303),(.115,.05,.025),'steel',r,.004)
    f.box('ReticleProjector',(0,.237,.326),(.014,.008,.013),'cyan',r,.002)
    d.face_text('RELAY / 07',(0,.309,.21),.02,r,'cyan')
    bpy.context.object.rotation_euler.z=math.pi
    return r,{'Grip':'hand anchor','Muzzle':'beam/orb projectile origin','OrbChamber':'local Y axial animation optional','Sight':'optic sightline marker'}


def pinball():
    r=f.empty('PinballRoot');handle(r,.19)
    # Squat breech with a broad planar launch deck and large underside puck carousel.
    d.shell('Breech',(0,.055,.055),.36,.42,.17,'steel',r,.06,.9,.012)
    d.shell('LaunchDeck',(0,-.255,.075),.38,.44,.10,'silver',r,.055,.95,.009)
    carousel=f.empty('PuckCarousel',(0,.015,.25),r)
    for i in range(3):
        f.cyl('StoredPuck',(0,0,i*.033),.143,.022,'violet' if i==1 else 'silver',carousel,48)
    f.cyl('PuckHub',(0,0,.099),.044,.035,'dark',carousel,16)
    # C-shaped cage remains open toward the feeding end, unlike the slender Relay.
    for i in range(9):
        a=math.radians(-85+i*170/8)
        x,y=.187*math.sin(a),.015+.187*math.cos(a)
        o=d.shell('FeedCage',(x,y,.16),.055,.07,.24,'amber',r,.013,.93,.006);o.rotation_euler.z=-a
    for s in (-1,1):
        d.shell('PlanarRail',(s*.155,-.29,.12),.065,.46,.125,'amber',r,.018,.88,.009)
        f.box('RailWearFace',(s*.114,-.295,.20),(.018,.40,.07),'dark',r,.004)
        f.box('PuckGuide',(s*.11,-.30,.221),(.013,.36,.012),'violet',r,.002)
        for j in range(3):
            f.box('RailHeatSink',(s*.2,-.19-j*.095,.16),(.039,.05,.07),'steel',r,.006)
    d.shell('MuzzleApron',(0,-.51,.08),.42,.095,.07,'dark',r,.025,1,.008)
    f.empty('Muzzle',(0,-.568,.211),r)
    # Front supporting hand grip is separate from the pistol grip.
    d.shell('Foregrip',(0,-.21,-.02),.25,.19,.082,'rubber',r,.03,.86,.008)
    for s in (-1,1):
        f.box('ChargeWindow',(s*.181,.07,.16),(.012,.16,.052),'violet',r,.003)
    f.empty('Sight',(0,.235,.42),r)
    f.box('RearSightBase',(0,.205,.337),(.15,.045,.035),'dark',r,.005)
    for s in (-1,1):
        f.box('RearSightEar',(s*.065,.205,.39),(.025,.045,.095),'steel',r,.005)
        f.box('SightIndex',(s*.065,.23,.407),(.012,.008,.022),'violet',r,.002)
    d.face_text('BANK / 12',(0,-.564,.097),.029,r,'amber')
    return r,{'Grip':'hand anchor','Muzzle':'puck projectile origin','PuckCarousel':'local Y rotation','Sight':'open rear sight marker'}


def setup_scene(bounds):
    scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=32
    scene.render.resolution_x=1100;scene.render.resolution_y=850;scene.render.resolution_percentage=100
    world=bpy.data.worlds.new('InspectionWorld');scene.world=world;world.use_nodes=True
    world.node_tree.nodes['Background'].inputs[0].default_value=(.075,.09,.12,1)
    span=max(b-a for a,b in bounds);center=Vector(tuple((a+b)/2 for a,b in bounds))
    for vec,energy in [((1,-1,1.5),1000),((-1,-.2,.8),450),((.2,1,1),900)]:
        bpy.ops.object.light_add(type='AREA',location=center+Vector(vec)*span)
        o=bpy.context.object;o.data.energy=energy*span*span/12;o.data.size=span
        o.rotation_euler=(center-o.location).to_track_quat('-Z','Y').to_euler()
    bpy.ops.object.camera_add();cam=bpy.context.object;scene.camera=cam;cam.data.type='ORTHO';cam.data.ortho_scale=span*1.65
    return scene,cam,center,span


def render_views(out):
    scene,cam,center,span=setup_scene(d.bounds())
    for angle in (25,205):
        a=math.radians(angle);cam.location=center+Vector((math.sin(a),-math.cos(a),.7))*span*1.7
        cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler()
        scene.render.filepath=str(out/f'preview-{angle}.png');bpy.ops.render.render(write_still=True)


def rebounder_sight(out,source):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(source))
    scene,cam,center,span=setup_scene(d.bounds());cam.data.type='PERSP';cam.data.lens=42
    eye=Vector((0,.8,.273));aim=Vector((0,-4,.273))
    cam.location=eye;cam.rotation_euler=(aim-eye).to_track_quat('-Z','Y').to_euler()
    # Diagram marker is explicitly separate from the unchanged imported asset.
    d.materials();f.M['target']=f.material('target',(.15,.65,.65))
    hoop('SightStudyTarget',(0,-4,.273),.15,.008,'target',None)
    scene.render.filepath=str(out/'rebounder-rear-eye.png');bpy.ops.render.render(write_still=True)
    result,loc,normal,idx,obj,matrix=scene.ray_cast(bpy.context.evaluated_depsgraph_get(),eye,Vector((0,-1,0)),distance=3)
    return {'source':str(source),'unchanged_geometry':True,'eye_blender_xyz':list(eye),
        'axis_blender':[0,-1,0],'center_ray_occluded':result,'hit_object':obj.name if result else None,
        'hit_blender_xyz':list(loc) if result else None,'scope':'one geometry-space sightline; not the game ADS camera'}


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--rebounder',required=True)
    args=p.parse_args(sys.argv[sys.argv.index('--')+1:]);out=Path(args.output).resolve();out.mkdir(parents=True,exist_ok=False)
    reports=[]
    for name,builder in [('relay-rifle',relay),('pinball-cannon',pinball)]:
        bpy.ops.wm.read_factory_settings(use_empty=True);d.materials();f.M['violet']=f.material('violet',(.31,.045,.8),.1,1.8)
        root,nodes=builder();bpy.context.view_layer.update();f.batch_static_meshes();before=d.bounds()
        meshes=[o for o in bpy.context.scene.objects if o.type=='MESH'];tris=0
        for o in meshes:o.data.calc_loop_triangles();tris+=len(o.data.loop_triangles)
        assert tris<=25000 and len(meshes)<=10,(name,tris,len(meshes))
        path=out/name;path.mkdir()
        bpy.ops.export_scene.gltf(filepath=str(path/f'{name}.glb'),export_format='GLB',export_yup=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(path/f'{name}.blend'))
        bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
        bpy.ops.import_scene.gltf(filepath=str(path/f'{name}.glb'));after=d.bounds()
        assert max(abs(before[i][j]-after[i][j]) for i in range(3) for j in range(2))<.001
        assert all(bpy.data.objects.get(n) for n in nodes)
        reports.append({'asset':name,'triangles':tris,'primitives':len(meshes),
            'dimensions_gltf_xyz_m':[after[0][1]-after[0][0],after[2][1]-after[2][0],after[1][1]-after[1][0]],
            'nodes':nodes,'roundtrip':'vertex bounds and named nodes PASS'})
        render_views(path)
    sight=rebounder_sight(out,Path(args.rebounder))
    (out/'manifest.json').write_text(json.dumps({'up':'Y','forward':'+Z','units':'meters','assets':reports,'rebounder_sight_study':sight,
        'limitations':['No target-game ADS test','Material factors only; no authored texture maps','No weapon clips/hand rig/LOD/colliders']},indent=2))


if __name__=='__main__':main()
