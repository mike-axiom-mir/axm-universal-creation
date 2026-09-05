"""Original traversable fortress bridge and rooftop station; coordinates below are glTF XYZ."""
import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import axm_fortress_pack as f
import axm_fortress_detail as d
import axm_fortress_weapons as w


def xyz(v):
    return (v[0], -v[2], v[1])


def empty(name, p=(0, 0, 0), parent=None):
    return f.empty(name, xyz(p), parent)


def box(name, p, size, mat, parent, bevel=.025):
    # Millimeter surface marks do not need rounded volume; small chamfers use one segment.
    obj=f.box(name, xyz(p), (size[0], size[2], size[1]), mat, parent, bevel if bevel>.018 else 0)
    if .005<bevel<=.018:
        mod=obj.modifiers.new('Small machined chamfer','BEVEL');mod.width=f.bevel_width(obj,bevel);mod.segments=1
        bpy.context.view_layer.objects.active=obj;bpy.ops.object.modifier_apply(modifier=mod.name)
    return obj


def shell(name, p, width, depth, height, mat, parent, chamfer=.12, taper=.92):
    return d.shell(name, xyz(p), width, depth, height, mat, parent, chamfer, taper, .025)


def cylinder(name, p, radius, length, mat, parent, axis='Y', sides=12, bevel=.015):
    bpy.ops.mesh.primitive_cylinder_add(vertices=sides, radius=radius, depth=length, location=xyz(p))
    obj = f.finish(bpy.context.object, name, mat, parent, 0)
    if bevel>.006:
        mod=obj.modifiers.new('Turned rim','BEVEL');mod.width=f.bevel_width(obj,bevel);mod.segments=1
        bpy.context.view_layer.objects.active=obj;bpy.ops.object.modifier_apply(modifier=mod.name)
    if axis == 'X':
        obj.rotation_euler.y = math.pi / 2
    elif axis == 'Z':
        obj.rotation_euler.x = math.pi / 2
    return obj


def beam(name, a, b, width, depth, mat, parent):
    a, b = Vector(xyz(a)), Vector(xyz(b))
    obj = f.box(name, (a+b)/2, (width, depth, (b-a).length), mat, parent, min(width, depth)*.15)
    obj.rotation_euler = (b-a).to_track_quat('Z', 'Y').to_euler()
    return obj


def top_text(label, p, size, parent, mat='amber'):
    curve = bpy.data.curves.new('DeckStencil', 'FONT')
    curve.body = label
    curve.size = size
    curve.align_x = 'CENTER'
    curve.extrude = .0003
    obj = bpy.data.objects.new('DeckStencil', curve)
    bpy.context.collection.objects.link(obj)
    obj.location = xyz(p)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.ops.object.convert(target='MESH')
    f.finish(obj, 'DeckStencil', mat, parent)


def bridge():
    root = empty('BridgeRoot')
    collision=[]
    deck = empty('Deck', parent=root)
    lights = empty('StatusLights', parent=deck)
    empty('DeckClosed', (0, 0, 0), root)
    empty('DeckRetracted', (12, 0, 0), root)
    # Nominal slab envelope is exact. Recessed seams sit below the walking plane.
    box('StructuralSlab', (0, -.375, 0), (12, .55, 10), 'dark', deck, 0)
    for s in (-1, 1):
        box('EndFrame', (s*5.86, -.05, 0), (.28, .10, 10), 'silver', deck, .01)
        box('SideFrame', (0, -.05, s*4.86), (11.44, .10, .28), 'silver', deck, .01)
    for ix in range(6):
        x = -5.72 + (ix+.5)*(11.44/6)
        for iz in range(5):
            z = -4.72 + (iz+.5)*(9.44/5)
            box('ReplaceableDeckPanel', (x, -.05, z), (1.865, .10, 1.846), 'steel', deck, .012)
            for dx in (-.80, .80):
                for dz in (-.78, .78):
                    cylinder('FlushPanelBolt', (x+dx, -.012, z+dz), .034, .024, 'silver', deck, sides=6, bevel=.004)
            # Drainage slots remain dark in the shallow panel seam plane.
            for dz in (-.36, 0, .36):
                box('TractionSlot', (x, -.0015, z+dz), (.58, .002, .021), 'dark', deck, .001)
    # Structural depth reads from below and from the gap. Everything moves with Deck.
    for s in (-1, 1):
        z = s*4.67
        box('LowerChord', (0, -1.45, z), (11.8, .17, .28), 'silver', deck, .025)
        box('UpperChord', (0, -.68, z), (11.8, .13, .28), 'steel', deck, .02)
        for i in range(6):
            x = -5+i*2
            beam('WarrenTruss', (x-.84, -1.36, z), (x+.84, -.77, z), .12, .16, 'steel', deck)
            box('GirderGusset', (x-.84, -1.21, z+s*.09), (.27, .43, .035), 'amber', deck, .014)
            for y in (-1.33, -1.08):
                cylinder('GussetBolt', (x-.86, y, z+s*.12), .046, .028, 'silver', deck, axis='Z', sides=6, bevel=.004)
        # Negative-Z service opening aligns with the lower stair after X+12 travel.
        segments=[(-6,-3.5),(.5,6)] if s<0 else [(-5.9,5.9)]
        for lo,hi in segments:
            center=(lo+hi)/2;length=hi-lo
            box('Handrail', (center, 1.09, s*4.8), (length, .12, .2), 'silver', deck, .018)
            box('KneeRail', (center, .52, s*4.8), (length, .09, .16), 'steel', deck, .015)
            box('ToeGuard', (center, .12, s*4.8), (length, .24, .15), 'dark', deck, .012)
        posts=(-5.86,-3.65,.65,2.35,4.1,5.86) if s<0 else (-5.75,-3.45,-1.15,1.15,3.45,5.75)
        for x in posts:
            box('RailPost', (x, .515, s*4.8), (.16, 1.03, .2), 'steel', deck, .015)
            box('RailWarningPlate', (x, .86, s*4.81), (.24, .26, .17), 'amber', deck, .015)
            box('DeckWarningLight', (x, .89, s*4.715), (.14, .055, .015), 'cyan', lights, .006)
        box('GuideRunner', (0, -.43, s*4.90), (11.8, .22, .16), 'silver', deck, .02)
        for x in (-4, 0, 4):
            cylinder('UnderslungActuator', (x, -.93, s*3.94), .15, 1.4, 'dark', deck, axis='X')
            cylinder('ActuatorRod', (x+.77, -.93, s*3.94), .075, .50, 'silver', deck, axis='X')
    for x in (-5.6, -1.8, 1.8, 5.6):
        box('CrossMember', (x, -.91, 0), (.23, .45, 9.0), 'steel', deck, .025)
    for x in (-5.5, 5.5):
        for z in (-3.6, -2.6, -1.6, -.6, .6, 1.6, 2.6, 3.6):
            box('WarningTick', (x, .0008, z), (.18, .001, .47), 'amber', deck, .0003)
    # Stencil is only submillimeter above walking top, not raised gameplay geometry.
    top_text('E / 02', (0, .0008, .30), .60, deck)
    # Static outer-end plant stays outboard of the 10 m playable strip.
    for s in (-1, 1):
        prior=set(bpy.context.scene.objects)
        z = s*5.83
        shell('MotorFoundation', (8.45, -.68, z), 3.0, 1.55, .30, 'dark', root, .22, .98)
        shell('DriveHousing', (8.50, -.39, z), 2.6, 1.23, 1.26, 'steel', root, .25, .85)
        shell('DriveArmorCap', (8.50, .69, z), 2.56, 1.15, .29, 'amber', root, .21, .85)
        box('ServicePanel', (8.50, .27, z+s*.615), (1.70, .57, .035), 'dark', root, .045)
        for x in (7.85, 8.17, 8.49, 8.81, 9.13):
            box('CoolingLouver', (x, .26, z+s*.644), (.17, .42, .035), 'silver', root, .015)
        cylinder('MotorEndCap', (9.83, .18, z), .39, .09, 'silver', root, axis='X', sides=16)
        cylinder('MotorHub', (9.89, .18, z), .16, .08, 'dark', root, axis='X', sides=12)
        box('GuideNose', (6.66, -.37, s*5.30), (1.73, .28, .38), 'silver', root, .035)
        box('GuideJaw', (5.93, -.36, s*5.06), (.25, .38, .10), 'dark', root, .02)
        beam('GuideBrace', (7.3, -.50, s*5.9), (5.95, -.50, s*5.31), .18, .18, 'steel', root)
        collision.append(collision_box('StaticDriveNegativeZ' if s<0 else 'StaticDrivePositiveZ',
                         [o for o in bpy.context.scene.objects if o not in prior]))
    return root, {
        'placement_world_xyz_m': [38, 0, 0],
        'Deck': {'closed_local_x': 0, 'retracted_local_x': 12, 'walkable_top_y': 0,
                 'collision_footprint_xz': [[-6, 6], [-5, 5]], 'nominal_slab_y': [-.65, 0]},
        'StatusLights': {'parent': 'Deck', 'purpose': 'tint descendant emissive material; clone material per independent instance'},
        'rails': {'centers_z': [-4.8, 4.8], 'height_y': [0, 1.15], 'thickness_z': .2,
                  'negative_z_segments_x': [[-6,-3.5],[.5,6]], 'negative_z_opening_x': [-3.5,.5],
                  'negative_z_opening_world_x_retracted': [46.5,50.5], 'positive_z_continuous': True},
        'DeckClosed': [0, 0, 0], 'DeckRetracted': [12, 0, 0],
        'static_collision_boxes': collision,
    }


def station():
    root = empty('RelayStationRoot')
    collision=[]
    lights = empty('LandmarkLights', parent=root)
    empty('RoofSocket', (1.5, 4.2, 0), root)
    empty('RoofEntranceLeft', (-4.5, 4.2, 4), root)
    empty('RoofEntranceRight', (-1, 4.2, 4), root)
    shell('ArmoredFoundation', (0, 0, 0), 9, 8, .48, 'dark', root, .55, .98)
    shell('PressureHull', (0, .40, 0), 8.55, 7.52, 3.38, 'steel', root, .55, .95)
    shell('UpperCornice', (0, 3.52, 0), 8.9, 7.9, .41, 'silver', root, .30, .99)
    # Roof is a full rectangular landing plane. Flush panels reveal shallow seams.
    box('RoofSlab', (0, 4.005, 0), (9, .37, 8), 'dark', root, .015)
    for ix in range(5):
        for iz in range(4):
            box('RoofPlate', (-3.60+ix*1.8, 4.195, -3+iz*2), (1.77, .01, 1.97), 'steel', root, .003)
    # Four corner armor columns, grounded below the roof line.
    for sx in (-1, 1):
        for sz in (-1, 1):
            shell('CornerButtress', (sx*3.89, .3, sz*3.36), .65, .69, 3.22, 'silver', root, .14, .77)
            box('ColumnHazardBand', (sx*3.89, .9, sz*3.72), (.44, .18, .035), 'amber', root, .008)
    # Front entrance and relay control bay remain within the base footprint.
    shell('FrontDoorFrame', (-1.75, .48, 3.72), 2.64, .32, 2.80, 'dark', root, .15, .94)
    box('SealedDoor', (-1.75, 1.86, 3.897), (2.23, 2.40, .08), 'silver', root, .06)
    box('DoorSplit', (-1.75, 1.86, 3.943), (.055, 2.24, .014), 'dark', root, .004)
    for y in (.95, 2.75):
        box('DoorBrace', (-1.75, y, 3.954), (1.96, .09, .015), 'steel', root, .008)
    box('FrontControlRecess', (1.88, 2.06, 3.76), (2.18, 1.43, .22), 'dark', root, .10)
    box('ControlDisplay', (1.65, 2.23, 3.881), (1.31, .60, .022), 'cyan', lights, .025)
    for i in range(3):
        box('ControlKey', (1.28+i*.35, 1.63, 3.892), (.15, .12, .04), 'amber', root, .012)
    for x in (.97, 2.78):
        for y in (1.49, 2.62):
            cylinder('ControlFastener', (x, y, 3.90), .045, .026, 'silver', root, axis='Z', sides=6, bevel=.004)
    d.face_text('N / RELAY', xyz((1.65, 3.02, 3.89)), .24, root, 'amber')
    # Side plates, cooling louvers and discrete conduits use several scales of detail.
    for s in (-1, 1):
        for z in (-2.15, 0, 2.15):
            box('SideArmorCassette', (s*4.22, 1.94, z), (.13, 2.35, 1.80), 'dark', root, .06)
            for i in range(5):
                box('SideLouver', (s*4.301, 1.34+i*.29, z), (.065, .105, 1.46), 'silver', root, .015)
            for dz in (-.75, .75):
                for y in (1.0, 2.89):
                    cylinder('SidePanelBolt', (s*4.342, y, z+dz), .040, .024, 'amber', root, axis='X', sides=6, bevel=.004)
        box('RearConduitRecess', (s*2.9, 2.12, -3.78), (.31, 2.46, .12), 'dark', root, .024)
        box('RearConduit', (s*2.9, 2.12, -3.857), (.07, 2.12, .027), 'cyan', lights, .007)
    box('RearServiceCassette', (0, 2.03, -3.77), (3.5, 1.88, .20), 'dark', root, .09)
    for y in (1.42, 1.74, 2.06, 2.38, 2.70):
        box('RearServiceFin', (0, y, -3.892), (3.12, .11, .042), 'silver', root, .015)
    # Partial cover: never cross the ramp landing x[-4.5,-1], z=+4.
    for x in (-2.8, 0, 2.8):
        cover=shell('RearParapet', (x, 4.2, -3.75), 2.45, .42, .93, 'dark', root, .12, .94)
        armor=box('ParapetArmor', (x, 4.65, -3.514), (2.13, .55, .045), 'silver', root, .06)
        collision.append(collision_box(f'RearCover_{x}',[cover,armor]))
    for z in (-2.25, .35):
        cover=shell('LeftParapet', (-4.27, 4.2, z), .40, 2.02, .82, 'dark', root, .09, .95)
        collision.append(collision_box(f'LeftCover_{z}',[cover]))
    for z in (-1.80, 2.15):
        cover=shell('RightParapet', (4.27, 4.2, z), .40, 2.66, .92, 'dark', root, .09, .95)
        collision.append(collision_box(f'RightCover_{z}',[cover]))
    cover=shell('FrontRightCover', (1.78, 4.2, 3.73), 5.08, .45, .78, 'dark', root, .14, .95)
    armor=box('FrontCoverArmor', (1.78, 4.61, 3.974), (4.69, .44, .035), 'silver', root, .04)
    collision.append(collision_box('FrontRightCover',[cover,armor]))
    # Low rooftop relay landmark is at the rear, keeping the central roof open.
    prior=set(bpy.context.scene.objects)
    shell('RelayPlinth', (-.10, 4.2, -2.74), 1.25, 1.0, .25, 'silver', root, .20, .85)
    cylinder('RelayCore', (-.10, 4.76, -2.74), .22, .66, 'violet', lights, sides=24)
    for x in (-.57, .37):
        shell('RelayFin', (x, 4.38, -2.74), .12, .71, .75, 'silver', root, .025, .72)
    cylinder('RelayCap', (-.10, 5.148, -2.74), .32, .16, 'dark', root, sides=16)
    cylinder('RelayBeacon', (-.10, 5.238, -2.74), .19, .024, 'cyan', lights, sides=20, bevel=.003)
    collision.append(collision_box('RearRelayUnit',[o for o in bpy.context.scene.objects if o not in prior]))
    # Flush weapon socket marker: game owns the terminal/weapon attached here.
    for i in range(16):
        angle=i*math.tau/16
        mark=box('SocketIndex', (1.5+.70*math.cos(angle), 4.2006, .70*math.sin(angle)), (.14, .001, .047), 'amber', root, .0002)
        mark.rotation_euler.z=-angle
    top_text('RELAY', (1.5, 4.2006, 1.05), .26, root, 'silver')
    return root, {'placement_world_xyz_m': [13, 0, -47], 'base_footprint_xz': [[-4.5, 4.5], [-4, 4]],
                  'roof_top_y': 4.2, 'RoofSocket': [1.5, 4.2, 0],
                  'entrance': {'front_z': 4, 'x': [-4.5, -1], 'unobstructed_above_y': 4.2},
                  'maximum_cover_top_y': 5.25, 'LandmarkLights': 'cyan and violet emissive descendants',
                  'roof_collision_boxes': collision, 'RoofSocket_collision': None}


def measured(objects=None):
    bpy.context.view_layer.update()
    points=[obj.matrix_world@v.co for obj in (objects if objects is not None else bpy.context.scene.objects)
            if obj.type=='MESH' for v in obj.data.vertices]
    bounds=[[min(p[i] for p in points), max(p[i] for p in points)] for i in range(3)]
    return [bounds[0], bounds[2], [-bounds[1][1], -bounds[1][0]]]


def descendants(root):
    return [root, *root.children_recursive]


def collision_box(name, objects):
    b=measured(objects)
    return {'name':name,'bounds_gltf_xyz_m':b,
            'game_box_local':{'x':sum(b[0])/2,'z':sum(b[2])/2,'w':b[0][1]-b[0][0],
                              'd':b[2][1]-b[2][0],'bottom':b[1][0],'h':b[1][1]}}


def render(out, name):
    # Imported assets only. Bridge comparison shares one fixed camera and framing.
    if name=='east-bridge':
        deck=bpy.data.objects['Deck']
        closed=d.bounds()
        deck.location.x=12
        opened=d.bounds()
        both=[[min(closed[i][0],opened[i][0]),max(closed[i][1],opened[i][1])] for i in range(3)]
        scene,cam,center,span=w.setup_scene(both)
        cam.data.ortho_scale=span*1.28
        cam.location=center+Vector((.90,-1.05,.72))*span
        cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler()
        for offset,state in [(0,'closed'),(12,'open')]:
            deck.location.x=offset
            scene.render.filepath=str(out/f'preview-{state}.png')
            bpy.ops.render.render(write_still=True)
        deck.location.x=0
        center=Vector((2,0,-.1));cam.data.ortho_scale=21.5
        bpy.ops.object.light_add(type='AREA',location=(0,2,-8))
        fill=bpy.context.object;fill.data.energy=1500;fill.data.size=9
        fill.rotation_euler=(center-fill.location).to_track_quat('-Z','Y').to_euler()
        cam.location=center+Vector((-12,15,-9))
        cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler()
        scene.render.filepath=str(out/'preview-underside.png');bpy.ops.render.render(write_still=True)
    else:
        scene,cam,center,span=w.setup_scene(d.bounds());cam.data.ortho_scale=span*1.82
        for angle,label in [(25,'front'),(205,'rear')]:
            a=math.radians(angle);cam.location=center+Vector((math.sin(a),-math.cos(a),.87))*span*1.7
            cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler()
            scene.render.filepath=str(out/f'preview-{label}.png');bpy.ops.render.render(write_still=True)
        cam.location=(0,0,24);cam.rotation_euler=(0,0,0);cam.data.ortho_scale=12.5
        scene.render.filepath=str(out/'preview-roof.png');bpy.ops.render.render(write_still=True)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True)
    parser.add_argument('--render-existing',action='store_true',help='refresh previews from existing GLBs without rewriting geometry')
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    out=Path(args.output).resolve()
    if args.render_existing:
        for name in ('east-bridge','north-relay-station'):
            bpy.ops.wm.read_factory_settings(use_empty=True)
            path=out/name;bpy.ops.import_scene.gltf(filepath=str(path/f'{name}.glb'))
            render(path,name)
        return
    out.mkdir(parents=True,exist_ok=False)
    reports=[]
    for name,builder,cap in [('east-bridge',bridge,35000),('north-relay-station',station,30000)]:
        bpy.ops.wm.read_factory_settings(use_empty=True);d.materials()
        f.M['violet']=f.material('violet',(.29,.035,.8),.15,2)
        root,contract=builder();bpy.context.view_layer.update()
        # Validate authored surfaces before batching removes their individual names.
        if name=='east-bridge':
            slab=measured([bpy.data.objects['StructuralSlab']])
            expected=[[-6,6],[-.65,-.10],[-5,5]]
            assert max(abs(slab[i][j]-expected[i][j]) for i in range(3) for j in range(2))<.001
            for obj in descendants(bpy.data.objects['Deck']):
                if obj.type!='MESH':continue
                b=measured([obj])
                assert not (b[1][1]>.151 and b[0][1]>-3.499 and b[0][0]<.499 and b[2][1]>-4.901 and b[2][0]<-4.699), obj.name
        else:
            # No raised geometry in the entire front-left ramp landing strip.
            for obj in bpy.context.scene.objects:
                if obj.type!='MESH':continue
                for v in obj.data.vertices:
                    p=obj.matrix_world@v.co;x,y,z=p.x,p.z,-p.y
                    assert not (-4.5-.001<x<-1+.001 and 3.3<z<=4.01 and y>4.202), (obj.name,x,y,z)
        f.batch_static_meshes();before=measured();meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']
        tris=0
        for obj in meshes:obj.data.calc_loop_triangles();tris+=len(obj.data.loop_triangles)
        assert tris<cap and len(meshes)<=12,(name,tris,len(meshes))
        path=out/name;path.mkdir()
        bpy.ops.export_scene.gltf(filepath=str(path/f'{name}.glb'),export_format='GLB',export_yup=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(path/f'{name}.blend'))
        bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
        bpy.ops.import_scene.gltf(filepath=str(path/f'{name}.glb'));after=measured()
        assert max(abs(before[i][j]-after[i][j]) for i in range(3) for j in range(2))<.001
        report={'asset':name,'triangles':tris,'primitives':len(meshes),'bounds_gltf_xyz_m':after,
                'dimensions_gltf_xyz_m':[b-a for a,b in after],'contract':contract,'roundtrip':'vertex bounds PASS within 1 mm'}
        if name=='east-bridge':
            deck=bpy.data.objects['Deck'];closed=measured(descendants(deck))
            assert abs(closed[0][0]+6)<.001 and abs(closed[0][1]-6)<.001
            assert abs(closed[2][0]+5)<.001 and abs(closed[2][1]-5)<.001
            assert closed[1][0]>=-2 and closed[1][1]<=1.151
            deck.location.x=12;opened=measured(descendants(deck));deck.location.x=0
            assert abs(opened[0][0]-closed[0][0]-12)<.001
            report['Deck_closed_bounds_gltf_xyz_m']=closed;report['Deck_open_bounds_gltf_xyz_m']=opened
            report['StatusLights_parent']=bpy.data.objects['StatusLights'].parent.name
            assert report['StatusLights_parent']=='Deck'
        else:
            assert after[0][0]>=-4.501 and after[0][1]<=4.501 and after[2][0]>=-4.001 and after[2][1]<=4.001
            assert abs(after[1][0])<.001 and after[1][1]<=5.251
            bpy.context.view_layer.update();p=bpy.data.objects['RoofSocket'].matrix_world.translation
            report['RoofSocket_gltf_xyz_m']=[p.x,p.z,-p.y]
            assert (Vector(report['RoofSocket_gltf_xyz_m'])-Vector((1.5,4.2,0))).length<.001
        reports.append(report)
        (out/'manifest.json').write_text(json.dumps({'units':'meters','up':'Y','assets':reports},indent=2))
        render(path,name)
    (out/'manifest.json').write_text(json.dumps({'units':'meters','up':'Y','assets':reports,
      'limitations':['Rigid Deck translation only; no clips or simulated telescoping hydraulics','No collisions, ramps or bypass meshes','Material factors and geometry, no textures/LODs','Gameplay and performance verification belong to integration']},indent=2))
    (out/'collision-contract.json').write_text(json.dumps({
      'units':'meters','coordinates':'local glTF Y-up; add root placement to obtain world coordinates',
      'game_box_note':'h is absolute LOCAL TOP Y, not height; translate bottom and h by root Y',
      'east-bridge':{'placement_world_xyz_m':[38,0,0],'static_boxes':reports[0]['contract']['static_collision_boxes'],
                     'rails':reports[0]['contract']['rails'],
                     'Deck_and_rails':'Use the exact deck footprint. Split negative-Z rail into X[-6,-3.5] and X[.5,6]; positive-Z rail continuous. Translate all rail colliders by Deck local X.'},
      'north-relay-station':{'placement_world_xyz_m':[13,0,-47],'roof_boxes':reports[1]['contract']['roof_collision_boxes'],
                             'RoofSocket':[1.5,4.2,0],'RoofSocket_collision':None,
                             'base':'Use existing 9x8 base with roof top Y4.2; front-left roof entry remains open'}},indent=2))


if __name__=='__main__':
    main()
