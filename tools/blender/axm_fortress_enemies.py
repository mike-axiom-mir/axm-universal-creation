"""Original heavy Breacher and low sprung Hunter; rigid animation nodes only."""
import argparse,json,math,sys
from pathlib import Path
import bpy
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
import axm_fortress_pack as f
import axm_fortress_detail as d
import axm_fortress_weapons as w


def beam(name,a,b,width,depth,material,parent):
    a,b=Vector(a),Vector(b)
    o=f.box(name,(a+b)/2,(width,depth,(b-a).length),material,parent,min(width,depth)*.13)
    o.rotation_euler=(b-a).to_track_quat('Z','Y').to_euler()
    return o


def axle(name,loc,radius,length,material,parent):
    o=f.cyl(name,loc,radius,length,material,parent,16);o.rotation_euler.y=math.pi/2
    return o


def breacher():
    root=f.empty('BreacherRoot');body=f.empty('Body',(0,0,1.1),root)
    d.shell('ChestCarapace',(0,0,.13),1.32,.78,.75,'steel',body,.21,.8,.045)
    d.shell('ShoulderMantle',(0,.03,.67),1.52,.79,.3,'silver',body,.16,.86,.035)
    d.shell('Abdomen',(0,0,-.21),.72,.54,.37,'dark',body,.1,.85,.025)
    d.shell('RecessedHead',(0,-.055,.87),.52,.49,.31,'dark',body,.09,.75,.025)
    f.box('ThreatVisor',(0,-.307,1.03),(.35,.035,.071),'red',body,.009)
    # Exposed amber power stack deliberately centered on the broad chest.
    d.shell('PowerBay',(0,-.395,.32),.52,.12,.41,'dark',body,.055,1,.014)
    for i in range(4):f.box('PowerCell',(0,-.472,.38+i*.079),(.40,.055,.036),'amber',body,.008)
    f.empty('WeakPoint',(0,-.51,.50),body)
    for s in (-1,1):
        d.shell('ChestCheek',(s*.46,-.35,.25),.3,.16,.43,'silver',body,.065,.83,.02)
        d.shell('ShoulderGuard',(s*.77,.025,.44),.39,.59,.42,'steel',body,.11,.86,.025)
        beam('UpperArm',(s*.76,.02,.41),(s*.85,-.12,-.12),.27,.3,'dark',body)
    # Heavy right battering assembly: axial piston and broad reinforced impact shoe.
    for y,radius,depth,mat in [(-.34,.25,.44,'steel'),(-.58,.18,.21,'silver'),(-.74,.30,.16,'dark')]:
        o=f.cyl('RamCylinder',(.85,y,-.11),radius,depth,mat,body,24);o.rotation_euler.x=math.pi/2
    d.shell('BatteringFace',(.85,-.84,-.35),.57,.10,.5,'silver',body,.09,.94,.025)
    for x in (.64,1.06):f.box('RamWearStrip',(x,-.905,-.1),(.068,.025,.35),'dark',body,.008)
    beam('RamBrace',(.7,-.1,.16),(.72,-.69,.15),.08,.09,'amber',body)
    # Left arm is a compact suppressive gun, distinguishable from the ram.
    o=f.cyl('ArmGun',(-.84,-.33,-.13),.16,.47,'steel',body,16);o.rotation_euler.x=math.pi/2
    f.box('GunAperture',(-.84,-.578,-.13),(.18,.035,.1),'red',body,.008)
    f.empty('Muzzle',(-.84,-.60,-.13),body)
    d.shell('RearGenerator',(0,.46,.2),.78,.27,.53,'dark',body,.09,.85,.025)
    for z in (.29,.4,.51,.62):f.box('GeneratorFin',(0,.607,z),(.62,.036,.04),'silver',body,.008)
    for s,name in [(-1,'LegLeft'),(1,'LegRight')]:
        leg=f.empty(name,(s*.38,0,1.04),root)
        beam('Thigh',(0,0,-.06),(s*.06,.06,-.43),.29,.32,'dark',leg)
        axle('Knee',(s*.07,-.02,-.48),.18,.34,'silver',leg)
        d.shell('Shin',(s*.07,-.04,-.9),.36,.35,.4,'steel',leg,.07,.9,.02)
        d.shell('Foot',(s*.07,-.15,-1.04),.43,.69,.2,'dark',leg,.09,.92,.02)
    return root,{'Body':'torso rigid pivot','LegLeft':'left hip local X swing','LegRight':'right hip local X swing','Muzzle':'left arm gun origin','WeakPoint':'amber chest power stack'}


def hunter():
    root=f.empty('HunterRoot');body=f.empty('Body',(0,0,.74),root)
    # Crouched wedge torso with forward optical prow and low folded legs.
    d.shell('LowCarapace',(0,.02,0),.89,.77,.4,'steel',body,.17,.7,.028)
    d.shell('ForwardProw',(0,-.43,.13),.61,.38,.28,'silver',body,.1,.74,.022)
    f.box('SensorRecess',(0,-.627,.285),(.51,.035,.12),'dark',body,.012)
    f.box('RedSensor',(0,-.651,.286),(.4,.027,.058),'red',body,.008)
    f.empty('WeakPoint',(0,-.67,.286),body)
    f.box('SensorBrow',(0,-.48,.48),(.39,.33,.04),'steel',body,.017)
    # Two thin dorsal blades rather than the Breacher's broad shoulder mass.
    for s in (-1,1):
        blade=d.shell('DorsalVane',(s*.29,.24,.16),.065,.35,.36,'silver',body,.016,.78,.009)
        blade.rotation_euler.x=-.12
        axle('HipCover',(s*.50,.13,.02),.18,.18,'dark',body)
    for y in (.21,.32,.43):f.box('SpinalHeatFin',(0,y,.35),(.3,.045,.04),'dark',body,.008)
    # Compact under-prow emitter stays below the red sensor, with a real muzzle marker.
    o=f.cyl('Emitter',(0,-.41,.075),.095,.43,'dark',body,16);o.rotation_euler.x=math.pi/2
    f.box('EmitterLens',(0,-.636,.075),(.13,.03,.07),'red',body,.007)
    f.empty('Muzzle',(0,-.662,.075),body)
    # Fixed crouched rest stance. Each rigid hip controls its complete spring leg.
    for s,name in [(-1,'LegLeft'),(1,'LegRight')]:
        leg=f.empty(name,(s*.51,.08,.73),root)
        beam('UpperSpring',(0,0,0),(s*.25,.31,-.21),.17,.2,'steel',leg)
        axle('RearKnee',(s*.25,.31,-.21),.13,.21,'dark',leg)
        beam('LowerSpring',(s*.25,.30,-.21),(s*.20,-.24,-.55),.13,.16,'steel',leg)
        beam('SpringStrut',(s*.11,.17,-.02),(s*.14,-.20,-.46),.055,.065,'dark',leg)
        d.shell('SplitToe',(s*.20,-.30,-.73),.28,.59,.18,'dark',leg,.07,.78,.017)
        for dx in (-.085,.085):f.box('ToeRunner',(s*.20+dx,-.47,-.615),(.039,.22,.026),'steel',leg,.005)
    return root,{'Body':'torso rigid pivot','LegLeft':'left folded leg local X swing','LegRight':'right folded leg local X swing','Muzzle':'under-prow emitter','WeakPoint':'red frontal sensor'}


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True)
    args=p.parse_args(sys.argv[sys.argv.index('--')+1:]);out=Path(args.output).resolve();out.mkdir(parents=True,exist_ok=False)
    reports=[]
    for name,builder in [('breacher',breacher),('hunter',hunter)]:
        bpy.ops.wm.read_factory_settings(use_empty=True);d.materials();f.M['red']=f.material('red',(.85,.018,.009),.1,2)
        root,contract=builder();bpy.context.view_layer.update();f.batch_static_meshes();before=d.bounds()
        meshes=[o for o in bpy.context.scene.objects if o.type=='MESH'];tris=0
        for o in meshes:o.data.calc_loop_triangles();tris+=len(o.data.loop_triangles)
        assert tris<=20000 and len(meshes)<=12,(name,tris,len(meshes))
        path=out/name;path.mkdir()
        bpy.ops.export_scene.gltf(filepath=str(path/f'{name}.glb'),export_format='GLB',export_yup=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(path/f'{name}.blend'))
        bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
        bpy.ops.import_scene.gltf(filepath=str(path/f'{name}.glb'));after=d.bounds()
        assert max(abs(before[i][j]-after[i][j]) for i in range(3) for j in range(2))<.001
        bpy.context.view_layer.update()
        nodes={n:{'purpose':description,'position_gltf_world_m':[bpy.data.objects[n].matrix_world.translation.x,bpy.data.objects[n].matrix_world.translation.z,-bpy.data.objects[n].matrix_world.translation.y]} for n,description in contract.items()}
        reports.append({'asset':name,'triangles':tris,'primitives':len(meshes),
            'dimensions_gltf_xyz_m':[after[0][1]-after[0][0],after[2][1]-after[2][0],after[1][1]-after[1][0]],
            'bounds_blender_xyz':after,'nodes':nodes,'roundtrip':'vertex bounds and named pivots PASS'})
        w.render_views(path)
    (out/'manifest.json').write_text(json.dumps({'units':'meters','up':'Y','forward':'+Z','assets':reports,
        'limitations':['Rigid hip pivots only; no animation clips or skin','No collision or weak-point damage code','Feet need game-specific stance and ground contact logic','No AAA or target-game performance certification']},indent=2))


if __name__=='__main__':main()
