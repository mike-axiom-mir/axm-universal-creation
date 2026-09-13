"""Build and independently verify one layered-paint GLB material proof.

Run build and verify as separate bpy 4.3 processes. The proof contrasts intact
paint, an attributed wear proposal, and the same proposal after a protected-logo
veto. It is a static integration specimen, not a complete game prop.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
from axm_uc.game_material_bridge import blender_game_material, load_material_bundle
from axm_uc.game_material_styles import WearLayer, generate_game_material, protected_regions_mask


SURFACES = ('intact', 'exposed', 'protected')


def authored_wear_proposal(size):
    """A proof-only UV mask: borders, diagonal scrape and three chips."""
    result = bytearray()
    for y in range(size):
        v = (y + .5) / size
        for x in range(size):
            u = (x + .5) / size
            border = max(0, 1 - min(u, v, 1 - u, 1 - v) / .085)
            diagonal = max(0, 1 - abs(v - (.20 + u * .62)) / .026)
            chips = max(max(0, 1 - ((u - cx) ** 2 + (v - cy) ** 2) ** .5 / radius)
                        for cx, cy, radius in ((.22, .68, .09), (.72, .32, .07), (.82, .74, .055)))
            result.append(round(min(1, max(border, diagonal * .92, chips * .8)) * 255))
    return bytes(result)


def scene_setup(bpy, root, output_name):
    from mathutils import Vector
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 28
    scene.cycles.use_denoising = True
    scene.render.threads_mode = 'FIXED'
    scene.render.threads = 4
    scene.render.resolution_x, scene.render.resolution_y = 1500, 820
    scene.render.resolution_percentage = 100
    scene.view_settings.view_transform = 'AgX'
    scene.world = bpy.data.worlds.new('Wear proof world')
    scene.world.color = (.025, .03, .045)
    bpy.ops.object.camera_add(location=(0, -14, 1.25))
    camera = bpy.context.object
    camera.rotation_euler = ((Vector((0, 0, .2)) - camera.location).to_track_quat('-Z', 'Y').to_euler())
    camera.data.lens = 48
    scene.camera = camera
    for location, power, size in [((-4, -4, 7), 1050, 4.5), ((5, -2, 4), 800, 3.5), ((0, 4, 6), 650, 3)]:
        bpy.ops.object.light_add(type='AREA', location=location)
        lamp = bpy.context.object
        lamp.data.energy, lamp.data.shape, lamp.data.size = power, 'DISK', size
        lamp.rotation_euler = ((Vector((0, 0, 0)) - lamp.location).to_track_quat('-Z', 'Y').to_euler())
    scene.render.image_settings.file_format = 'PNG'
    scene.render.filepath = str(root / output_name)


def solid_material(bpy, name, color, metallic, roughness):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    shader = material.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = (*color, 1)
    shader.inputs['Metallic'].default_value = metallic
    shader.inputs['Roughness'].default_value = roughness
    return material


def add_label(bpy, body, location, size, material, extrude=.014):
    curve = bpy.data.curves.new(body, 'FONT')
    curve.body, curve.align_x, curve.align_y = body, 'CENTER', 'CENTER'
    curve.size, curve.extrude, curve.bevel_depth = size, extrude, .005
    obj = bpy.data.objects.new(body, curve)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = location
    obj.rotation_euler = (1.57079632679, 0, 0)
    obj.data.materials.append(material)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.convert(target='MESH')
    obj.select_set(False)
    return obj


def build(root):
    import bpy
    root.mkdir(parents=True, exist_ok=False)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    size, proposal = 256, authored_wear_proposal(256)
    protection = protected_regions_mask(size, [(.27, .25, .73, .75)])
    layer = WearLayer(amount=1, substrate_rgb=(88, 98, 104), substrate_roughness=.38,
                      substrate_metallic=1, edge_normal_strength=.012)
    generate_game_material(root / 'maps' / 'intact', 'painted-metal', size, 471, 'comic-salvage')
    generate_game_material(root / 'maps' / 'exposed', 'painted-metal', size, 471, 'comic-salvage',
                           layer=layer, wear_mask=proposal,
                           wear_mask_source='authored-proof-panel-regions')
    generate_game_material(root / 'maps' / 'protected', 'painted-metal', size, 471, 'comic-salvage',
                           layer=layer, wear_mask=proposal, protected_mask=protection,
                           wear_mask_source='authored-proof-panel-regions',
                           protected_mask_source='authored-proof-logo-safe-zone')
    source_digests = {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
                      for path in sorted((root / 'maps').rglob('*')) if path.is_file()}
    materials = {name: blender_game_material(root / 'maps' / name, 'WearProof_' + name)
                 for name in SURFACES}
    dark = solid_material(bpy, 'Raised readable mark', (.018, .022, .027), .75, .32)
    bolt = solid_material(bpy, 'Fasteners', (.13, .16, .18), .88, .24)
    objects = []
    for index, name in enumerate(SURFACES):
        x = (index - 1) * 3.35
        bpy.ops.mesh.primitive_cube_add(location=(x, 0, .1), scale=(1.42, .16, 1.52))
        panel = bpy.context.object
        panel.name = 'Panel_' + name
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        bevel = panel.modifiers.new('Rolled armor edge', 'BEVEL')
        bevel.width, bevel.segments = .13, 5
        bpy.context.view_layer.objects.active = panel
        bpy.ops.object.modifier_apply(modifier=bevel.name)
        # Proof-camera planar mapping. This is deliberately not claimed as a
        # general unwrap or mesh-curvature wear solution.
        for loop in panel.data.loops:
            position = panel.data.vertices[loop.vertex_index].co
            panel.data.uv_layers.active.data[loop.index].uv = (position.x / 2.84 + .5,
                                                               position.z / 3.04 + .5)
        panel.data.materials.append(materials[name])
        objects.append(panel)
        for dx in (-1.17, 1.17):
            for dz in (-1.25, 1.25):
                bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=.10, depth=.08,
                                                    location=(x + dx, -.22, .1 + dz),
                                                    rotation=(1.57079632679, 0, 0))
                fastener = bpy.context.object
                fastener.name = 'Fastener'
                fastener.data.materials.append(bolt)
                objects.append(fastener)
        objects.append(add_label(bpy, 'M', (x, -.22, .13), 1.25, dark, .025))
    label = solid_material(bpy, 'Caption', (.72, .77, .83), .05, .9)
    add_label(bpy, 'INTACT', (-3.35, -.24, 1.98), .24, label)
    add_label(bpy, 'EXPOSED', (0, -.24, 1.98), .24, label)
    add_label(bpy, 'PROTECTED MARK', (3.35, -.24, 1.98), .21, label)
    add_label(bpy, 'SAME WEAR PROPOSAL  /  PROTECTION VETOES DAMAGE', (0, -.24, -1.93), .19, label)
    scene_setup(bpy, root, 'source.png')
    bpy.ops.wm.save_as_mainfile(filepath=str(root / 'layered-wear-proof.blend'))
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.export_scene.gltf(filepath=str(root / 'layered-wear-proof.glb'), export_format='GLB',
                              use_selection=True, export_extras=True, export_image_format='AUTO')
    current = {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
               for path in sorted((root / 'maps').rglob('*')) if path.is_file()}
    assert current == source_digests
    (root / 'source-digests.json').write_text(json.dumps(source_digests, indent=2) + '\n')
    bpy.ops.render.render(write_still=True)


def glb_document(path):
    data = path.read_bytes()
    magic, version, length = struct.unpack_from('<4sII', data)
    assert (magic, version, length) == (b'glTF', 2, len(data))
    json_length, json_kind = struct.unpack_from('<II', data, 12)
    assert json_kind == 0x4E4F534A
    doc = json.loads(data[20:20 + json_length])
    offset = 20 + json_length
    binary_length, binary_kind = struct.unpack_from('<II', data, offset)
    assert binary_kind == 0x004E4942
    return data, doc, data[offset + 8:offset + 8 + binary_length]


def verify(root):
    from PIL import Image
    import bpy
    data, doc, binary = glb_document(root / 'layered-wear-proof.glb')
    materials = {material['name']: material for material in doc['materials']}
    exact = []
    for name in SURFACES:
        bundle = load_material_bundle(root / 'maps' / name)
        material = materials['WearProof_' + name]
        pbr = material['pbrMetallicRoughness']
        textures = [('base_color', pbr['baseColorTexture']), ('orm', pbr['metallicRoughnessTexture']),
                    ('orm', material['occlusionTexture']), ('normal', material['normalTexture'])]
        for key, texture in textures:
            image = doc['images'][doc['textures'][texture['index']]['source']]
            view = doc['bufferViews'][image['bufferView']]
            offset = view.get('byteOffset', 0)
            actual = Image.open(io.BytesIO(binary[offset:offset + view['byteLength']])).convert('RGB')
            expected = Image.open(io.BytesIO(bundle['pngs'][key])).convert('RGB')
            if key == 'normal' and bundle['normal_convention'] == 'tangent -Y':
                r, g, b = expected.split()
                expected = Image.merge('RGB', (r, g.point(lambda value: 255 - value), b))
            assert actual.tobytes() == expected.tobytes(), (name, key)
        exact.append(name)
    exposed = Image.open(io.BytesIO(load_material_bundle(root / 'maps' / 'protected')['pngs']['exposed_mask'])).convert('L')
    protection = Image.open(io.BytesIO(load_material_bundle(root / 'maps' / 'protected')['pngs']['protection_mask'])).convert('L')
    for exposure, protected in zip(exposed.tobytes(), protection.tobytes()):
        if protected == 255:
            assert exposure == 0
    source_digests = json.loads((root / 'source-digests.json').read_text())
    current = {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
               for path in sorted((root / 'maps').rglob('*')) if path.is_file()}
    assert current == source_digests
    bpy.ops.wm.open_mainfile(filepath=str(root / 'layered-wear-proof.blend'))
    assert sum(image.packed_file is not None for image in bpy.data.images) == 9
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(root / 'layered-wear-proof.glb'))
    for name in SURFACES:
        material = bpy.data.materials['WearProof_' + name]
        assert material['axm_realized_normal_convention'] == 'tangent +Y'
    scene_setup(bpy, root, 'reimport.png')
    bpy.ops.render.render(write_still=True)
    source = Image.open(root / 'source.png').convert('RGB').tobytes()
    restored = Image.open(root / 'reimport.png').convert('RGB').tobytes()
    mae = sum(abs(a - b) for a, b in zip(source, restored)) / len(source)
    assert mae < 2, mae
    report = {'schema': 'axm.layered-wear-roundtrip/v0.1', 'blender': bpy.app.version_string,
              'glb_sha256': hashlib.sha256(data).hexdigest(), 'runtime_maps_exact': exact,
              'protected_pixels_have_zero_exposure': True, 'source_maps_immutable': True,
              'blend_packed_images': 9, 'source_reimport_render_mae': mae,
              'limits': 'Static material integration specimen; no animation, LOD, engine gameplay, performance, automatic UVs or mesh-derived wear acceptance.'}
    (root / 'verification.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('build', 'verify'))
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    (build if args.mode == 'build' else verify)(args.output.resolve())
