"""Original meter-scale fortress props; Blender is the explicit export/render compiler.

Run: blender -b --python axm_fortress_pack.py -- --output DIRECTORY
No textures or external assets. Reusable bevel, radial and articulation primitives.
"""
import argparse
import json
import math
import sys
from pathlib import Path
import bpy
from mathutils import Vector


def material(name, color, metal=0.0, emission=0.0):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1)
    m.use_nodes = True
    p = m.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value = (*color, 1)
    p.inputs['Metallic'].default_value = metal
    p.inputs['Roughness'].default_value = .34 if metal else .55
    p.inputs['Emission Color'].default_value = (*color, 1)
    p.inputs['Emission Strength'].default_value = emission
    return m


def empty(name, loc=(0, 0, 0), parent=None):
    o = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(o)
    o.parent = parent
    o.location = loc
    return o


def finish(o, name, mat, parent, bevel=0):
    o.name = name
    o.data.materials.append(M[mat])
    if bevel:
        mod = o.modifiers.new('Machined edge', 'BEVEL')
        # Thin cylinders and lofts can reach Blender's overlap clamp before
        # half their bounding dimension. Respect the shortest source edge so
        # bevel faces retain real area instead of collapsing at the clamp.
        shortest = min((o.data.vertices[e.vertices[0]].co - o.data.vertices[e.vertices[1]].co).length
                       for e in o.data.edges)
        mod.width = min(bevel, shortest * .45)
        mod.segments = 2
        bpy.context.view_layer.objects.active = o
        bpy.ops.object.modifier_apply(modifier=mod.name)
    o.parent = parent
    return o


def box(name, loc, size, mat='steel', parent=None, bevel=.04):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.object
    o.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return finish(o, name, mat, parent, bevel)


def cyl(name, loc, radius, depth, mat='steel', parent=None, vertices=16):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=loc)
    return finish(bpy.context.object, name, mat, parent, .025)


def ring(name, z, radius, tube, mat, parent):
    bpy.ops.mesh.primitive_torus_add(major_segments=32, minor_segments=6,
        location=(0, 0, z), major_radius=radius, minor_radius=tube)
    return finish(bpy.context.object, name, mat, parent)


def reactor():
    r = empty('ReactorRoot')
    cyl('Foundation', (0, 0, .22), 2.5, .44, parent=r)
    cyl('LowerPressureVessel', (0, 0, .85), 1.85, .8, parent=r)
    cyl('EnergyCore', (0, 0, 3), 1.05, 4, 'cyan', r, 24)
    for z in (1.1, 2.0, 3.1, 4.2, 5.1):
        ring('ContainmentRing', z, 1.42, .12, 'silver', r)
    for i in range(8):
        a = i * math.tau / 8
        x, y = 1.82 * math.cos(a), 1.82 * math.sin(a)
        o = box('ContainmentSpine', (x, y, 3), (.38, .5, 4.6), parent=r)
        o.rotation_euler.z = a
        o = box('SpinePowerStrip', (x*1.12, y*1.12, 3.2), (.07, .25, 2.9), 'cyan', r, .01)
        o.rotation_euler.z = a
        for z in (.65, 5.25):
            o = box('SpineClamp', (x, y, z), (.7, .75, .38), 'amber', r)
            o.rotation_euler.z = a
    cyl('UpperPressureCap', (0, 0, 5.55), 1.95, .5, parent=r)
    cyl('Crown', (0, 0, 5.9), 1.25, .2, 'silver', r)
    for i in range(12):
        a=i*math.tau/12
        o=box('CrownCoolingSlot',(1.5*math.cos(a),1.5*math.sin(a),5.82),(.36,.09,.04),'dark',r,.006)
        o.rotation_euler.z=a
    return r


def turret():
    r = empty('TurretRoot')
    cyl('AnchoredBase', (0, 0, .15), 1, .3, parent=r)
    cyl('ServoPedestal', (0, 0, .64), .51, .75, 'silver', r)
    for x in (-.7, .7):
        box('AnchorShoe', (x, 0, .21), (.35, 1.2, .42), 'amber', r)
    yaw = empty('TurretYaw', (0, 0, 1.15), r)
    cyl('YawBearing', (0, 0, 0), .67, .22, 'dark', yaw)
    for x in (-.48, .48):
        box('ArmoredYoke', (x, 0, .38), (.22, .7, .8), 'amber', yaw)
    pitch = empty('TurretPitch', (0, 0, .5), yaw)
    box('Receiver', (0, 0, .12), (.75, .85, .56), parent=pitch)
    box('TopArmor', (0, .06, .56), (.84, .75, .18), 'amber', pitch)
    for x in (-.24, .24):
        o = cyl('Barrel', (x, -.75, .12), .13, 1.15, 'dark', pitch, 12)
        o.rotation_euler.x = math.pi/2
        box('MuzzleShroud', (x, -1.25, .12), (.32, .28, .33), 'silver', pitch)
        box('MuzzleAperture', (x, -1.398, .12), (.18, .015, .16), 'dark', pitch, .005)
    box('TargetSensor', (0, -.43, .48), (.28, .035, .12), 'cyan', pitch, .01)
    empty('Muzzle', (0, -1.43, .12), pitch)
    for i in range(5):
        box('ReceiverCoolingFin',(0,.44,.02+i*.075),(.55,.035,.027),'dark',pitch,.004)
    for s in (-1,1):
        for i in range(3):
            box('SideVent',(s*.596,-.18+i*.16,.37),(.015,.08,.30),'dark',yaw,.004)
        cyl('PitchAxle',(s*.61,0,.5),.13,.06,'silver',yaw,12).rotation_euler.y=math.pi/2
    return r


def drone():
    r = empty('DroneRoot')
    body = empty('DroneBody', (0, 0, 1.14), r)
    box('WedgeHull', (0, 0, .18), (.98, .75, .72), parent=body, bevel=.15)
    box('DorsalArmor', (0, .04, .66), (.64, .65, .25), 'silver', body, .09)
    box('ThreatVisor', (0, -.393, .37), (.68, .04, .12), 'red', body, .01)
    box('LowerJaw', (0, -.34, -.09), (.72, .3, .2), 'dark', body)
    for s in (-1, 1):
        limb = empty('LegLeft' if s < 0 else 'LegRight', (s*.48, .02, -.08), body)
        o=box('UpperLeg', (s*.08, .03, -.28), (.25, .29, .6), 'dark', limb)
        o.rotation_euler.y = s*-.2
        cyl('KneeHousing', (s*.14, 0, -.51), .18, .25, 'amber', limb, 12).rotation_euler.x=math.pi/2
        box('ShinArmor', (s*.13, -.02, -.73), (.29, .31, .4), 'steel', limb)
        box('StabilizerFoot', (s*.13, -.14, -.96), (.34, .59, .2), 'dark', limb)
        box('ShoulderPlate', (s*.63, 0, .27), (.27, .63, .52), 'amber', body)
        o=cyl('ArmCannon', (s*.64, -.42, -.02), .13, .64, 'dark', body, 12)
        o.rotation_euler.x=math.pi/2
        box('CannonMuzzle', (s*.64, -.75, -.02), (.2, .025, .2), 'red', body, .01)
    box('RearPowerPack',(0,.47,.18),(.6,.24,.57),'dark',body,.06)
    for i in range(4):
        box('RearHeatFin',(0,.602,-.01+i*.13),(.49,.035,.05),'silver',body,.007)
    return r


def batch_static_meshes():
    """Join by material AND articulation parent; retain all mechanical pivots."""
    groups={}
    for o in list(bpy.context.scene.objects):
        if o.type=='MESH': groups.setdefault((o.parent,o.data.materials[0].name),[]).append(o)
    for (parent,mat),objects in groups.items():
        bpy.ops.object.select_all(action='DESELECT')
        for o in objects: o.select_set(True)
        bpy.context.view_layer.objects.active=objects[0]
        bpy.ops.object.join()
        objects[0].name=f'{parent.name}_{mat}'


def render(output, root, span):
    world=bpy.data.worlds.new('Studio')
    bpy.context.scene.world=world
    world.use_nodes=True
    world.node_tree.nodes['Background'].inputs[0].default_value=(.07,.09,.12,1)
    ground=box('PreviewGround',(0,0,-.10),(200,200,.1),'dark',bevel=0)
    for loc, energy, size in [((4,-5,9),1800,7),((-5,-2,4),1400,6),((2,5,7),2200,5)]:
        bpy.ops.object.light_add(type='AREA',location=loc)
        l=bpy.context.object
        l.data.energy=energy
        l.data.shape='DISK'
        l.data.size=size
        l.rotation_euler=(Vector((0,0,span*.35))-l.location).to_track_quat('-Z','Y').to_euler()
    bpy.ops.object.camera_add()
    camera=bpy.context.object
    camera.data.type='ORTHO'
    camera.data.ortho_scale=span*1.4
    scene=bpy.context.scene
    scene.camera=camera
    scene.render.engine='CYCLES'
    scene.cycles.samples=24
    scene.render.resolution_x=800
    scene.render.resolution_y=800
    scene.render.resolution_percentage=100
    for angle in (35,215):
        a=math.radians(angle)
        camera.location=(span*1.6*math.sin(a),-span*1.6*math.cos(a),span*.95)
        camera.rotation_euler=(Vector((0,0,span*.42))-camera.location).to_track_quat('-Z','Y').to_euler()
        scene.render.filepath=str(output/f'preview-{angle}.png')
        bpy.ops.render.render(write_still=True)


def main():
    global M
    p=argparse.ArgumentParser()
    p.add_argument('--output',required=True)
    args=p.parse_args(sys.argv[sys.argv.index('--')+1:])
    out=Path(args.output).resolve()
    out.mkdir(parents=True,exist_ok=False)
    reports=[]
    for name, builder, span in [('reactor',reactor,6),('turret',turret,2.5),('assault-drone',drone,2)]:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        M={k:material(k,c,m,e) for k,c,m,e in [
            ('steel',(.075,.11,.15),.8,0),('dark',(.018,.025,.035),.6,0),
            ('silver',(.28,.35,.4),.8,0),('amber',(.55,.20,.02),.5,0),
            ('cyan',(.01,.65,.9),.1,3),('red',(.95,.035,.012),.1,2)]}
        root=builder()
        bpy.context.view_layer.update()
        batch_static_meshes()
        meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']
        points=[o.matrix_world @ Vector(c) for o in meshes for c in o.bound_box]
        bounds=[[min(v[i] for v in points),max(v[i] for v in points)] for i in range(3)]
        triangles=0
        for o in meshes:
            o.data.calc_loop_triangles()
            triangles+=len(o.data.loop_triangles)
        if triangles>=15000: raise ValueError('triangle budget exceeded')
        target=out/name
        target.mkdir()
        bpy.ops.export_scene.gltf(filepath=str(target/f'{name}.glb'),export_format='GLB',export_yup=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(target/f'{name}.blend'))
        report={'asset':name,'triangles':triangles,'bounds_blender_xyz':bounds,
            'dimensions_gltf_xyz_m':[bounds[0][1]-bounds[0][0],bounds[2][1]-bounds[2][0],bounds[1][1]-bounds[1][0]],
            'nodes':[o.name for o in bpy.context.scene.objects],'forward_gltf':'+Z'}
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete(use_global=False)
        bpy.ops.import_scene.gltf(filepath=str(target/f'{name}.glb'))
        bpy.context.view_layer.update()
        actual=[o for o in bpy.context.scene.objects if o.type=='MESH']
        pts=[o.matrix_world @ Vector(c) for o in actual for c in o.bound_box]
        restored=[[min(v[i] for v in pts),max(v[i] for v in pts)] for i in range(3)]
        if max(abs(bounds[i][j]-restored[i][j]) for i in range(3) for j in range(2))>0.001:
            raise ValueError('GLB reimport changed bounds')
        names={o.name for o in bpy.context.scene.objects}
        required={'turret':['TurretYaw','TurretPitch','Muzzle'],'assault-drone':['DroneBody','LegLeft','LegRight']}.get(name,['ReactorRoot'])
        if not all(n in names for n in required): raise ValueError('Missing exported pivots')
        report['roundtrip_bounds_and_pivots']='PASS'
        report['render_source']='fresh GLB import'
        reports.append(report)
        render(target,None,span)
    (out/'manifest.json').write_text(json.dumps({'units':'meters','up':'Y','assets':reports,
        'limitations':['No animation clips or physics colliders','Rigid drone leg pivots only','No target-engine performance certification']},indent=2))


if __name__=='__main__': main()
