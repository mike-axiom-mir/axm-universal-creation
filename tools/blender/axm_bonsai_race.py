from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import bpy
from mathutils import Vector

ASSET_ID = "axm-bonsai-race-v0-1"
SCHEMA = "axm.uc.bonsai-race-character/v0.1"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def clear_scene() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)


def mat(name: str, color, metallic=0.0, roughness=0.55, emission=None, emission_strength=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = (*color, 1.0)
    bsdf.inputs['Metallic'].default_value = metallic
    bsdf.inputs['Roughness'].default_value = roughness
    if emission is not None:
        bsdf.inputs['Emission Color'].default_value = (*emission, 1.0)
        bsdf.inputs['Emission Strength'].default_value = emission_strength
    return m


def smooth(obj):
    if obj.type == 'MESH':
        for poly in obj.data.polygons:
            poly.use_smooth = True
    return obj


def uv(name, loc, scale, material, segments=24, rings=16):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings, location=loc)
    o = bpy.context.object
    o.name = name
    o.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o.data.materials.append(material)
    return smooth(o)


def ico(name, loc, scale, material, subdivisions=1):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=subdivisions, location=loc)
    o = bpy.context.object
    o.name = name
    o.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o.data.materials.append(material)
    return smooth(o)


def cube(name, loc, scale, material, bevel=0.04):
    bpy.ops.mesh.primitive_cube_add(location=loc)
    o = bpy.context.object
    o.name = name
    o.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel:
        mod = o.modifiers.new('soft_edges', 'BEVEL')
        mod.width = bevel
        mod.segments = 3
        bpy.context.view_layer.objects.active = o
        bpy.ops.object.modifier_apply(modifier=mod.name)
    o.data.materials.append(material)
    return smooth(o)


def cyl_between(name, a, b, radius, material, vertices=12):
    a, b = Vector(a), Vector(b)
    vec = b - a
    length = vec.length
    mid = (a + b) * 0.5
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=length, location=mid)
    o = bpy.context.object
    o.name = name
    o.rotation_mode = 'QUATERNION'
    o.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(vec.normalized())
    o.data.materials.append(material)
    return smooth(o)


def torus(name, loc, major, minor, material, rot=(0,0,0)):
    bpy.ops.mesh.primitive_torus_add(major_radius=major, minor_radius=minor, major_segments=32, minor_segments=8, location=loc, rotation=rot)
    o = bpy.context.object
    o.name = name
    o.data.materials.append(material)
    return smooth(o)


def cone(name, loc, radius1, radius2, depth, material, vertices=20):
    bpy.ops.mesh.primitive_cone_add(vertices=vertices, radius1=radius1, radius2=radius2, depth=depth, location=loc)
    o = bpy.context.object
    o.name = name
    o.data.materials.append(material)
    return smooth(o)


def leaf(name, loc, scale, material, rot=(0,0,0)):
    o = ico(name, loc, scale, material, subdivisions=1)
    o.rotation_euler = rot
    return o


def curve_line(name, points, bevel, material):
    cu = bpy.data.curves.new(name + '_curve', 'CURVE')
    cu.dimensions = '3D'
    cu.bevel_depth = bevel
    cu.bevel_resolution = 3
    sp = cu.splines.new('BEZIER')
    sp.bezier_points.add(len(points)-1)
    for bp, p in zip(sp.bezier_points, points):
        bp.co = p
        bp.handle_left_type = 'AUTO'
        bp.handle_right_type = 'AUTO'
    o = bpy.data.objects.new(name, cu)
    bpy.context.collection.objects.link(o)
    o.data.materials.append(material)
    return o


def make_materials():
    return {
        'bark': mat('Bark', (0.23, 0.10, 0.035), roughness=0.78),
        'bark_light': mat('FaceWood', (0.53, 0.28, 0.11), roughness=0.68),
        'bark_dark': mat('DarkWood', (0.10, 0.042, 0.018), roughness=0.82),
        'leaf': mat('LeafGreen', (0.12, 0.33, 0.08), roughness=0.72),
        'leaf_light': mat('YoungLeaf', (0.30, 0.52, 0.13), roughness=0.68),
        'moss': mat('Moss', (0.15, 0.27, 0.055), roughness=0.92),
        'cream': mat('Linen', (0.54, 0.43, 0.27), roughness=0.86),
        'cloth': mat('ForestCloth', (0.11, 0.18, 0.085), roughness=0.86),
        'leather': mat('Leather', (0.16, 0.065, 0.025), roughness=0.7),
        'bronze': mat('Bronze', (0.30, 0.13, 0.035), metallic=0.7, roughness=0.34),
        'eye': mat('EyeAmber', (0.32, 0.10, 0.018), metallic=0.0, roughness=0.18),
        'pupil': mat('Pupil', (0.005, 0.003, 0.002), roughness=0.12),
        'white': mat('EyeHighlight', (0.93, 0.79, 0.48), roughness=0.22),
        'glow': mat('LanternGlow', (0.65, 0.21, 0.02), roughness=0.2, emission=(1.0, 0.26, 0.03), emission_strength=6.0),
    }


def build_character(out: Path):
    clear_scene()
    M = make_materials()
    parts = []

    for side, x in [('L', -0.14), ('R', 0.14)]:
        parts.append(cyl_between(f'leg_{side}', (x, 0.00, 0.18), (x*0.9, 0.00, 0.54), 0.10, M['bark']))
        parts.append(uv(f'root_foot_{side}', (x, -0.055, 0.09), (0.17, 0.23, 0.075), M['bark_dark'], 20, 12))
        for i, dx in enumerate((-0.08, 0, 0.08)):
            parts.append(cyl_between(f'root_toe_{side}_{i}', (x+dx*0.7, -0.12, 0.08), (x+dx, -0.29, 0.045), 0.025, M['bark_dark'], 8))

    parts.append(cone('trunk_body', (0, 0, 0.66), 0.27, 0.22, 0.48, M['bark'], 24))
    parts.append(uv('chest_growth', (0, -0.015, 0.75), (0.29, 0.22, 0.30), M['bark_light'], 28, 18))

    parts.append(uv('head', (0, -0.015, 1.08), (0.39, 0.31, 0.34), M['bark_light'], 32, 20))
    parts.append(curve_line('brow_L', [(-0.23, -0.294, 1.18), (-0.13, -0.327, 1.22), (-0.03, -0.31, 1.19)], 0.017, M['bark_dark']))
    parts.append(curve_line('brow_R', [(0.03, -0.31, 1.19), (0.13, -0.327, 1.22), (0.23, -0.294, 1.18)], 0.017, M['bark_dark']))
    for side, x in [('L', -0.14), ('R', 0.14)]:
        parts.append(uv(f'eye_{side}', (x, -0.301, 1.115), (0.092, 0.040, 0.108), M['eye'], 28, 16))
        parts.append(uv(f'pupil_{side}', (x, -0.338, 1.11), (0.037, 0.014, 0.055), M['pupil'], 20, 12))
        parts.append(uv(f'eye_glint_{side}', (x-0.018, -0.353, 1.145), (0.014, 0.006, 0.018), M['white'], 12, 8))
    parts.append(curve_line('smile', [(-0.11, -0.322, 0.985), (0.0, -0.35, 0.958), (0.11, -0.322, 0.985)], 0.012, M['bark_dark']))

    crown_branches = [
        ((0,0,1.31),(-0.03,0.01,1.65),0.065),
        ((-0.05,0,1.45),(-0.34,0.02,1.66),0.050),
        ((0.03,0,1.48),(0.34,0.00,1.69),0.048),
        ((-0.03,0.02,1.58),(-0.25,0.06,1.86),0.040),
        ((0.10,0.02,1.60),(0.26,0.03,1.88),0.038),
    ]
    for i,(a,b,r) in enumerate(crown_branches):
        parts.append(cyl_between(f'crown_branch_{i}', a, b, r, M['bark_dark'], 10))

    clusters = [(-0.34,0.02,1.69),(-0.19,0.03,1.78),(0.0,0.02,1.70),(0.21,0.02,1.80),(0.37,0.01,1.69),(-0.24,0.05,1.90),(0.26,0.04,1.94),(0.03,0.03,1.95)]
    for ci,(cx,cy,cz) in enumerate(clusters):
        for j in range(5):
            a = (ci*1.91 + j*2.41)
            dx = math.cos(a)*0.105
            dy = math.sin(a)*0.045
            dz = (j-2)*0.035
            material = M['leaf_light'] if (ci+j)%4==0 else M['leaf']
            parts.append(leaf(f'leaf_{ci}_{j}', (cx+dx,cy+dy,cz+dz), (0.105,0.035,0.055), material, rot=(0.2*j, 0.45, a)))

    for i,(x,z) in enumerate([(-0.22,0.82),(0.20,0.95),(-0.08,1.34),(0.18,1.43)]):
        parts.append(ico(f'moss_{i}', (x,-0.20,z), (0.065,0.03,0.045), M['moss'], 2))

    arm_defs = {
        'L': ((-0.23,-0.01,0.83),(-0.46,-0.02,0.68),(-0.51,-0.04,0.46)),
        'R': ((0.23,-0.01,0.83),(0.46,-0.00,0.70),(0.50,-0.03,0.50)),
    }
    for side,(shoulder,elbow,hand) in arm_defs.items():
        parts.append(cyl_between(f'upper_arm_{side}', shoulder, elbow, 0.065, M['bark'], 10))
        parts.append(cyl_between(f'forearm_{side}', elbow, hand, 0.052, M['bark'], 10))
        parts.append(uv(f'hand_{side}', hand, (0.075,0.06,0.085), M['bark_dark'], 16, 10))
        sx = -1 if side=='L' else 1
        for f in range(3):
            start=(hand[0]+sx*(f-1)*0.016,hand[1]-0.02,hand[2]-0.01)
            end=(start[0]+sx*(f-1)*0.010,start[1]-0.055,start[2]-0.055-0.012*f)
            parts.append(cyl_between(f'finger_{side}_{f}',start,end,0.010,M['bark_dark'],7))

    parts.append(torus('scarf_ring', (0,0,0.86), 0.26, 0.055, M['cloth'], rot=(0,0,0)))
    parts.append(cone('linen_tunic', (0,0,0.59), 0.285, 0.23, 0.45, M['cream'], 24))
    parts.append(cone('green_overcloth', (0,-0.005,0.51), 0.30, 0.24, 0.34, M['cloth'], 24))
    parts.append(torus('belt', (0,0,0.62), 0.255, 0.026, M['leather']))
    parts.append(leaf('leaf_brooch', (-0.16,-0.29,0.84), (0.052,0.015,0.085), M['bronze'], rot=(0.1,0.0,-0.45)))

    parts.append(cube('pouch_L', (-0.24,-0.11,0.56), (0.09,0.06,0.10), M['leather'], 0.025))
    parts.append(cube('pouch_R', (0.24,-0.10,0.57), (0.075,0.05,0.085), M['leather'], 0.02))
    parts.append(cube('backpack', (0,0.22,0.76), (0.20,0.09,0.25), M['leather'], 0.04))
    bpy.ops.mesh.primitive_cylinder_add(vertices=20, radius=0.085, depth=0.38, location=(0,0.31,1.02), rotation=(0,math.pi/2,0))
    bedroll=bpy.context.object
    bedroll.name='bedroll'
    bedroll.data.materials.append(M['cloth'])
    parts.append(bedroll)

    parts.append(cyl_between('staff_main', (-0.64,-0.03,0.08),(-0.61,0.00,1.63),0.038,M['bark_dark'],10))
    parts.append(cyl_between('staff_hook', (-0.61,0.00,1.63),(-0.49,-0.01,1.78),0.030,M['bark_dark'],9))
    parts.append(cyl_between('staff_hook_tip', (-0.49,-0.01,1.78),(-0.38,-0.015,1.70),0.024,M['bark_dark'],8))
    parts.append(torus('lantern_ring', (-0.48,-0.02,1.48), 0.085, 0.012, M['bronze'], rot=(math.pi/2,0,0)))
    parts.append(cyl_between('lantern_chain',(-0.48,-0.02,1.61),(-0.48,-0.02,1.52),0.009,M['bronze'],7))
    parts.append(uv('lantern_glow',(-0.48,-0.02,1.40),(0.075,0.075,0.10),M['glow'],18,12))
    parts.append(torus('lantern_cage_top',(-0.48,-0.02,1.47),0.080,0.009,M['bronze']))
    parts.append(torus('lantern_cage_bottom',(-0.48,-0.02,1.33),0.070,0.009,M['bronze']))
    for k in range(4):
        ang=math.pi*0.5*k
        x=-0.48+math.cos(ang)*0.065
        y=-0.02+math.sin(ang)*0.065
        parts.append(cyl_between(f'lantern_bar_{k}',(x,y,1.34),(x,y,1.46),0.006,M['bronze'],6))

    for i,(x,y,z) in enumerate([(-0.11,-0.05,0.37),(0.10,-0.03,0.43),(-0.03,0.02,0.29)]):
        parts.append(leaf(f'body_leaf_{i}',(x,y,z),(0.045,0.014,0.07),M['leaf_light'],rot=(0.3,0.4,i)))

    bpy.context.scene.unit_settings.system = 'METRIC'
    bpy.context.scene.unit_settings.scale_length = 1.0

    out.mkdir(parents=True, exist_ok=False)
    blend = out / 'bonsai-race-v0.1.blend'
    glb = out / 'bonsai-race-v0.1.glb'
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    bpy.ops.object.select_all(action='DESELECT')
    for obj in bpy.context.scene.objects:
        if obj.type in {'MESH','CURVE'}:
            obj.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(glb), export_format='GLB', export_yup=True, export_apply=True, use_selection=True)

    mesh_objects=[o for o in bpy.context.scene.objects if o.type=='MESH']
    tri_count=sum(len(p.vertices)-2 for o in mesh_objects for p in o.data.polygons)
    manifest={
        'schema': SCHEMA,
        'asset_id': ASSET_ID,
        'status': 'STRUCTURE_EXPORTED_VISUAL_REVIEW_REQUIRED',
        'units': 'meters',
        'files': {'blend': blend.name, 'glb': glb.name},
        'counts': {'mesh_objects': len(mesh_objects), 'triangles_source_estimate': tri_count, 'materials': len(bpy.data.materials)},
        'design': {
            'race_role': 'first signature nature race for untitled layer-RPG pet project',
            'body_rule': 'small bonsai-tree person; not a potted plant and not a forced druid/class',
            'features': ['compact rooted legs','warm expressive face','asymmetric bonsai canopy','moss and leaves','race-specific layered clothing','backpack','twisted staff','hanging lantern'],
            'working_name_only': 'Branfolk',
        },
        'provenance': {
            'creator': 'Mike - Axiom/Mir with OpenAI',
            'basis': 'authored deterministic UC interpretation of the conversation concept image; no automatic image-to-3D claim',
            'uc_base': 'e1316efdfdce96ca9e11ab71c37bd747b757fb0a',
        },
        'limitations': [
            'static character asset: no rig, skin weights, animation or game controller is claimed in v0.1',
            'unseen surfaces and exact geometry are authored interpretations of the visual concept',
            'race clothing compatibility is not yet implemented or verified',
            'visual similarity requires human review of fresh-import renders',
            'target-engine runtime/performance is not tested by this builder',
        ],
    }
    (out/'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    receipt={
        'schema': 'axm.uc.creation-receipt/v0.1',
        'asset_id': ASSET_ID,
        'glb_sha256': sha256(glb),
        'blend_sha256': sha256(blend),
        'builder': 'tools/blender/axm_bonsai_race.py',
        'deterministic_authored_recipe': True,
        'acceptance': 'VISUAL_REVIEW_REQUIRED',
    }
    (out/'receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    return manifest


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--output', required=True)
    args=ap.parse_args()
    manifest=build_character(Path(args.output))
    print(json.dumps(manifest, indent=2))


if __name__=='__main__':
    main()
