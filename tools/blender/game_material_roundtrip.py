"""Bounded real-Blender material proof; run build and verify in separate processes.

python tools/blender/game_material_roundtrip.py build /new/output
python tools/blender/game_material_roundtrip.py verify /new/output

Requires bpy 4.3, numpy<2 (bpy ABI), Pillow. No service or AI. Verification reads
embedded GLB PNG bytes independently before Blender re-import; it does not infer
visual acceptance from JSON. Output is a material test scene, not a game asset.
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
from axm_uc.game_material_styles import FAMILIES, FINISHES, generate_game_material


def digest_sources(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted((root / 'maps').rglob('*')) if p.is_file()}


def presentation(bpy, root, filename):
    from mathutils import Vector
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 24
    scene.cycles.use_denoising = True
    scene.render.threads_mode = 'FIXED'
    scene.render.threads = 4
    scene.render.resolution_x = 1440
    scene.render.resolution_y = 1500
    scene.render.resolution_percentage = 100
    scene.view_settings.view_transform = 'AgX'
    scene.world = bpy.data.worlds.new('Proof world')
    scene.world.color = (.18, .18, .18)
    bpy.ops.object.camera_add(location=(2.55, -3.4, 20))
    camera = bpy.context.object
    camera.rotation_euler = ((Vector((2.55, -3.4, 0)) - camera.location).to_track_quat('-Z', 'Y').to_euler())
    camera.data.type = 'ORTHO'
    camera.data.ortho_scale = 10.3
    scene.camera = camera
    for loc, power, size in [((-2, 3, 8), 1400, 5), ((7, -5, 5), 650, 4)]:
        bpy.ops.object.light_add(type='AREA', location=loc)
        light = bpy.context.object
        light.data.energy, light.data.shape, light.data.size = power, 'DISK', size
        light.rotation_euler = ((Vector((2.5, -3, 0)) - light.location).to_track_quat('-Z', 'Y').to_euler())
    mat = bpy.data.materials.new('Proof lettering')
    mat.diffuse_color = (.72, .77, .83, 1)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = (.72, .77, .83, 1)
    shader.inputs['Roughness'].default_value = 1
    def text(body, location, size, align='CENTER'):
        curve = bpy.data.curves.new('Label', 'FONT')
        curve.body, curve.size, curve.align_x = body, size, align
        obj = bpy.data.objects.new('Label', curve)
        scene.collection.objects.link(obj)
        obj.location = location
        obj.data.materials.append(mat)
    text('AXM  /  MATERIAL REALIZATION', (2.55, 1.35, 0), .27)
    text('Same fields. Four finishes. Actual glTF PBR textures.', (2.55, 1.0, 0), .14)
    for col, finish in enumerate(FINISHES):
        text(finish.name, (col * 1.7, .64, 0), .13)
    for row, family in enumerate(FAMILIES):
        for col in range(4):
            text(family, (col * 1.7, -row * 1.45 - .63, 0), .12)
    text('Surface proof, not full art direction or target-engine acceptance.', (2.55, -8.22, 0), .13)
    bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, -.3))
    floor = bpy.data.materials.new('Proof background')
    floor.diffuse_color = (.022, .03, .046, 1)
    floor.use_nodes = True
    floor.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value = (.022, .03, .046, 1)
    floor.node_tree.nodes.get('Principled BSDF').inputs['Roughness'].default_value = .85
    bpy.context.object.data.materials.append(floor)
    scene.render.image_settings.file_format = 'PNG'
    scene.render.filepath = str(root / filename)


def build(root):
    import bpy
    root.mkdir(parents=True, exist_ok=False)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    objects = []
    for row, family in enumerate(FAMILIES):
        for col, finish in enumerate(FINISHES):
            key = family + '__' + finish.name
            folder = root / 'maps' / key
            generate_game_material(folder, family, 128, 471, finish.name)
            source_bytes = {p.name: p.read_bytes() for p in folder.iterdir() if p.is_file()}
            mat = blender_game_material(folder, key)
            assert source_bytes == {p.name: p.read_bytes() for p in folder.iterdir() if p.is_file()}
            bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24, radius=.48,
                                                location=(col * 1.7, -row * 1.45, 0))
            obj = bpy.context.object
            obj.name = key
            obj.scale.z = .5
            bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
            # Planar front mapping avoids a UV pole misrepresenting cloth/grain
            # as radial rings. This proof is viewed from +Z, not a hero UV unwrap.
            uv = obj.data.uv_layers.active.data
            for loop in obj.data.loops:
                position = obj.data.vertices[loop.vertex_index].co
                uv[loop.index].uv = (position.x / .96 + .5, position.y / .96 + .5)
            obj.data.materials.append(mat)
            for polygon in obj.data.polygons:
                polygon.use_smooth = True
            objects.append(obj)
    before = digest_sources(root)
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects:
        obj.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(root / 'material-proof.glb'), export_format='GLB',
                              use_selection=True, export_extras=True, export_image_format='AUTO')
    if before != digest_sources(root):
        raise AssertionError('source material maps changed')
    (root / 'source-digests.json').write_text(json.dumps(before, indent=2) + '\n')
    presentation(bpy, root, 'source.png')
    bpy.ops.wm.save_as_mainfile(filepath=str(root / 'material-proof.blend'))
    bpy.ops.render.render(write_still=True)


def verify(root):
    from PIL import Image
    import bpy
    data = (root / 'material-proof.glb').read_bytes()
    magic, version, length = struct.unpack_from('<4sII', data)
    assert (magic, version, length) == (b'glTF', 2, len(data))
    json_length, chunk = struct.unpack_from('<II', data, 12)
    assert chunk == 0x4E4F534A
    doc = json.loads(data[20:20 + json_length])
    start = 20 + json_length
    binary_length, chunk = struct.unpack_from('<II', data, start)
    assert chunk == 0x004E4942
    binary = data[start + 8:start + 8 + binary_length]
    def image_for(texture):
        image = doc['images'][doc['textures'][texture['index']]['source']]
        assert image.get('mimeType') == 'image/png' and 'uri' not in image
        view = doc['bufferViews'][image['bufferView']]
        offset = view.get('byteOffset', 0)
        return Image.open(io.BytesIO(binary[offset:offset + view['byteLength']])).convert('RGB')
    assert len(doc['materials']) == len(FAMILIES) * len(FINISHES)
    receipts = []
    for material in doc['materials']:
        folder = root / 'maps' / material['name']
        bundle = load_material_bundle(folder)
        pbr = material['pbrMetallicRoughness']
        assert pbr.get('metallicFactor', 1) == 1
        assert pbr.get('roughnessFactor', 1) == 1
        assert pbr.get('baseColorFactor', [1, 1, 1, 1]) == [1, 1, 1, 1]
        assert material['normalTexture'].get('scale', 1) == 1
        assert material['occlusionTexture'].get('strength', 1) == 1
        for key, texture in [('base_color', pbr['baseColorTexture']),
                             ('orm', pbr['metallicRoughnessTexture']),
                             ('orm', material['occlusionTexture']),
                             ('normal', material['normalTexture'])]:
            expected = Image.open(io.BytesIO(bundle['pngs'][key])).convert('RGB')
            actual = image_for(texture)
            assert actual.size == expected.size == (128, 128)
            if key == 'normal' and bundle['normal_convention'] == 'tangent -Y':
                r, g, b = expected.split()
                expected = Image.merge('RGB', (r, g.point(lambda value: 255 - value), b))
            differences = [abs(a - b) for a, b in zip(actual.tobytes(), expected.tobytes())]
            assert max(differences) == 0, (material['name'], key, max(differences))
        assert all(texture.get('wrapS', 10497) == 10497 and texture.get('wrapT', 10497) == 10497
                   for texture in doc.get('samplers', []))
        receipts.append({'material': material['name'], 'embedded_pixels': 'exact',
                         'source_normal': bundle['normal_convention'], 'export_normal': 'tangent +Y'})
    assert digest_sources(root) == json.loads((root / 'source-digests.json').read_text())
    # Editable source must reopen without its transient decode paths.
    bpy.ops.wm.open_mainfile(filepath=str(root / 'material-proof.blend'))
    for receipt in receipts:
        material = bpy.data.materials[receipt['material']]
        textures = {node.label: node.image for node in material.node_tree.nodes if node.type == 'TEX_IMAGE'}
        assert set(textures) == {'base_color', 'orm', 'normal'}
        assert all(image.packed_file is not None for image in textures.values())
        assert textures['base_color'].colorspace_settings.name == 'sRGB'
        assert all(textures[key].colorspace_settings.name == 'Non-Color' for key in ('orm', 'normal'))
    # Fresh Blender state in a separate invocation, independent of the build scene.
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(root / 'material-proof.glb'))
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
    assert len(meshes) == 24 and len(bpy.data.materials) == 24
    for material in bpy.data.materials:
        assert material['axm_realized_normal_convention'] == 'tangent +Y'
        nodes = material.node_tree.nodes
        images = [node.image for node in nodes if node.type == 'TEX_IMAGE']
        assert any(image.colorspace_settings.name == 'sRGB' for image in images)
        assert sum(image.colorspace_settings.name == 'Non-Color' for image in images) >= 2
        assert any(node.type == 'NORMAL_MAP' and node.space == 'TANGENT' for node in nodes)
    presentation(bpy, root, 'reimport.png')
    bpy.ops.render.render(write_still=True)
    source = Image.open(root / 'source.png').convert('RGB').tobytes()
    restored = Image.open(root / 'reimport.png').convert('RGB').tobytes()
    mae = sum(abs(a - b) for a, b in zip(source, restored)) / len(source)
    assert mae < 2, ('unexpected source/reimport render divergence', mae)
    report = {'schema': 'axm.material-roundtrip-proof/v0.1', 'blender': bpy.app.version_string,
              'glb_sha256': hashlib.sha256(data).hexdigest(), 'materials': receipts,
              'reimported_meshes': len(meshes), 'source_immutable': True, 'blend_reopened_packed_images': 72,
              'render_mean_absolute_byte_difference': mae,
              'limits': 'Material spheres only; no engine gameplay, animation, performance, cel shader or full style acceptance.'}
    (root / 'verification.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['build', 'verify'])
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    (build if args.mode == 'build' else verify)(args.output.resolve())
