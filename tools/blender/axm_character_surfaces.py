"""Machine-owned, portable surface baking for rigid game characters.

The source shaders are authored here. Export textures are baked into unique UVs;
no Blender-only noise, curvature, or bump node is required by the game engine.
"""
from __future__ import annotations

import json
from pathlib import Path
import time

import bpy
import numpy as np


def linear_rgb(rgb):
    return tuple((c / 255 / 12.92 if c / 255 <= .04045 else ((c / 255 + .055) / 1.055) ** 2.4)
                 for c in rgb) + (1,)


def authored_material(name, rgb, roughness, metallic):
    material = bpy.data.materials.new("SOURCE_" + name)
    material.use_nodes = True
    nodes, links = material.node_tree.nodes, material.node_tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    shader = nodes.new("ShaderNodeBsdfPrincipled")
    links.new(shader.outputs[0], output.inputs["Surface"])
    geometry = nodes.new("ShaderNodeNewGeometry")

    def noise(scale, detail=2, vector=None):
        node = nodes.new("ShaderNodeTexNoise")
        node.inputs["Scale"].default_value = scale
        node.inputs["Detail"].default_value = detail
        links.new(vector or geometry.outputs["Position"], node.inputs["Vector"])
        return node.outputs["Fac"]

    def math(operation, a, b=0):
        node = nodes.new("ShaderNodeMath")
        node.operation = operation
        for index, value in enumerate((a, b)):
            if isinstance(value, (int, float)):
                node.inputs[index].default_value = value
            else:
                links.new(value, node.inputs[index])
        return node.outputs[0]

    def ramp(source, points):
        node = nodes.new("ShaderNodeValToRGB")
        elements = node.color_ramp.elements
        for element in list(elements)[2:]:
            elements.remove(element)
        for index, (position, color) in enumerate(points):
            element = elements[index] if index < 2 else elements.new(position)
            element.position, element.color = position, color
        links.new(source, node.inputs[0])
        return node.outputs[0]

    base = linear_rgb(rgb)
    variation = noise(19, 3)
    color = ramp(variation, [(.18, tuple(c * .88 for c in base[:3]) + (1,)),
                             (.82, base)])
    paint = name in {"Ceramic", "PetrolTeal", "SafetyCoral"}
    # Pointiness concentrates abrasion on convex manufactured edges. Noise
    # interrupts the rim, avoiding identical painted outlines on every part.
    edge = math("MULTIPLY", math("MAXIMUM", math("SUBTRACT", geometry.outputs["Pointiness"], .513), 0), 10)
    chips = math("MULTIPLY", edge, math("GREATER_THAN", noise(410, 2), .56))
    position=nodes.new("ShaderNodeSeparateXYZ")
    links.new(geometry.outputs["Position"],position.inputs[0])
    scratches_vector = nodes.new("ShaderNodeVectorMath")
    scratches_vector.operation = "MULTIPLY"
    scratches_vector.inputs[1].default_value = (95, 4, 280)
    links.new(geometry.outputs["Position"], scratches_vector.inputs[0])
    scratches = math("MULTIPLY", math("GREATER_THAN", noise(1, 1, scratches_vector.outputs[0]), .76), .25)
    if name=="PetrolTeal":
        # Boot-toe abrasion has a causal placement, not uniform dirt everywhere.
        toe=math("MULTIPLY",math("LESS_THAN",position.outputs["Y"],-.17),
                 math("LESS_THAN",position.outputs["Z"],.135))
        rubbed=math("MULTIPLY",toe,math("GREATER_THAN",noise(145,2),.64))
        scratches=math("ADD",scratches,math("MULTIPLY",rubbed,.7))
    if name=="Ceramic":
        # Small interrupted casing scuffs, concentrated on the outer head rim.
        rim=math("MULTIPLY",math("GREATER_THAN",math("ABSOLUTE",position.outputs["X"]),.14),
                 math("GREATER_THAN",position.outputs["Z"],1.09))
        scratches=math("ADD",scratches,math("MULTIPLY",rim,math("MULTIPLY",
                  math("GREATER_THAN",noise(160,2),.70),.45)))
    wear = math("MINIMUM", math("ADD", chips, scratches), .55) if paint else math("MULTIPLY", variation, .12)
    mix = nodes.new("ShaderNodeMixRGB")
    mix.blend_type = "MIX"
    links.new(wear, mix.inputs[0])
    links.new(color, mix.inputs[1])
    mix.inputs[2].default_value = linear_rgb((141, 137, 122)) if paint else base
    links.new(mix.outputs[0], shader.inputs["Base Color"])
    rough = math("ADD", roughness / 255 - .07, math("MULTIPLY", noise(145, 2), .14))
    metal = math("ADD", metallic / 255, math("MULTIPLY", wear, .62 if paint else 0))
    links.new(rough, shader.inputs["Roughness"])
    links.new(metal, shader.inputs["Metallic"])
    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = .12 if paint else .08
    bump.inputs["Distance"].default_value = .0002 if paint else .00012
    links.new(noise(220, 2), bump.inputs["Height"])
    links.new(bump.outputs[0], shader.inputs["Normal"])
    # Sockets saved by node name, not live handles, for the bake stages.
    material["bake_color"] = mix.name
    material["bake_roughness"] = rough.node.name
    material["bake_metallic"] = metal.node.name
    return material


def bake_character(mesh, output: Path, palette, resolution=2048):
    """Unique-unwrap then bake PBR maps, preserving one export draw call."""
    started = time.monotonic()
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 8
    scene.render.bake.margin = 8
    scene.render.bake.use_clear = True
    scene.render.bake.use_selected_to_active = False
    bpy.ops.object.select_all(action="DESELECT")
    mesh.select_set(True)
    bpy.context.view_layer.objects.active = mesh
    # Smart projection runs on the assembled bind-pose mesh. Its packed islands
    # replace the deliberately shared palette UVs of the lightweight preset.
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=1.15192, island_margin=.004, area_weight=.5,
                             correct_aspect=True, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    mesh.data.uv_layers.active.name = "OOPS_UniqueBakeUV"
    print("OOPS_UNIQUE_UV_READY", flush=True)
    originals = [authored_material(*entry) for entry in palette]
    # Clearing Blender material slots also resets polygon material indices.
    # Preserve the palette mapping before replacing placeholder slots.
    palette_indices = [face.material_index for face in mesh.data.polygons]
    if set(palette_indices) != set(range(len(palette))):
        raise ValueError(f"incomplete character palette before bake: {sorted(set(palette_indices))}")
    mesh.data.materials.clear()
    for mat in originals:
        mesh.data.materials.append(mat)
    for face, index in zip(mesh.data.polygons, palette_indices):
        face.material_index = index
    folder = output / "textures"
    folder.mkdir(exist_ok=True)
    targets = {}
    for role, color_space in (("BaseColor", "sRGB"), ("Roughness", "Non-Color"),
                              ("Metallic", "Non-Color"), ("AO", "Non-Color"), ("Normal", "Non-Color")):
        img = bpy.data.images.new("OOPS_" + role, width=resolution, height=resolution, alpha=False)
        img.colorspace_settings.name = color_space
        for mat in originals:
            nodes = mat.node_tree.nodes
            target = nodes.get("BAKE_TARGET") or nodes.new("ShaderNodeTexImage")
            target.name = "BAKE_TARGET"
            target.image = img
            nodes.active = target
            output_node = next(n for n in nodes if n.type == "OUTPUT_MATERIAL")
            shader = next(n for n in nodes if n.type == "BSDF_PRINCIPLED")
            if role == "Normal":
                mat.node_tree.links.new(shader.outputs[0], output_node.inputs["Surface"])
            else:
                emitter = nodes.get("BAKE_EMISSION") or nodes.new("ShaderNodeEmission")
                emitter.name = "BAKE_EMISSION"
                if role=="AO":
                    ao=nodes.new("ShaderNodeAmbientOcclusion")
                    ao.inputs["Distance"].default_value=.035
                    ao.samples=16
                    ao.only_local=True
                    source=ao.outputs["AO"]
                else:
                    key = {"BaseColor": "bake_color", "Roughness": "bake_roughness", "Metallic": "bake_metallic"}[role]
                    source=nodes[mat[key]].outputs[0]
                mat.node_tree.links.new(source, emitter.inputs["Color"])
                mat.node_tree.links.new(emitter.outputs[0], output_node.inputs["Surface"])
        bpy.ops.object.bake(type="NORMAL" if role == "Normal" else "EMIT")
        img.filepath_raw = str(folder / f"OOPS_{role}.png")
        img.file_format = "PNG"
        img.save()
        targets[role] = img
        print("OOPS_BAKED", role, round(time.monotonic() - started, 1), flush=True)
    # glTF standard packed map: ambient occlusion=R, roughness=G, metal=B.
    size = resolution * resolution * 4
    rough, metal = np.empty(size, dtype=np.float32), np.empty(size, dtype=np.float32)
    targets["Roughness"].pixels.foreach_get(rough)
    targets["Metallic"].pixels.foreach_get(metal)
    pixels = np.ones((resolution * resolution, 4), dtype=np.float32)
    ao_pixels=np.empty(size,dtype=np.float32)
    targets["AO"].pixels.foreach_get(ao_pixels)
    pixels[:,0]=ao_pixels[::4]
    pixels[:, 1], pixels[:, 2] = rough[::4], metal[::4]
    orm = bpy.data.images.new("OOPS_ORM", width=resolution, height=resolution, alpha=False)
    orm.colorspace_settings.name = "Non-Color"
    orm.pixels.foreach_set(pixels.ravel())
    orm.filepath_raw, orm.file_format = str(folder / "OOPS_ORM.png"), "PNG"
    orm.save()
    targets["ORM"] = orm
    result = bpy.data.materials.new("OOPS_Unique_Authored_PBR")
    result.use_nodes = True
    nodes, links = result.node_tree.nodes, result.node_tree.links
    shader = nodes.get("Principled BSDF")
    texture_nodes = {}
    for role in ("BaseColor", "ORM", "Normal"):
        node = nodes.new("ShaderNodeTexImage")
        node.image = targets[role]
        node.image.pack()
        texture_nodes[role] = node
    links.new(texture_nodes["BaseColor"].outputs["Color"], shader.inputs["Base Color"])
    split = nodes.new("ShaderNodeSeparateColor")
    links.new(texture_nodes["ORM"].outputs["Color"], split.inputs[0])
    links.new(split.outputs["Green"], shader.inputs["Roughness"])
    links.new(split.outputs["Blue"], shader.inputs["Metallic"])
    gltf_group=bpy.data.node_groups.new("glTF Material Output", "ShaderNodeTree")
    gltf_group.interface.new_socket(name="Occlusion",in_out="INPUT",socket_type="NodeSocketFloat")
    gltf_node=nodes.new("ShaderNodeGroup")
    gltf_node.node_tree=gltf_group
    links.new(split.outputs["Red"],gltf_node.inputs["Occlusion"])
    normal = nodes.new("ShaderNodeNormalMap")
    links.new(texture_nodes["Normal"].outputs["Color"], normal.inputs["Color"])
    links.new(normal.outputs[0], shader.inputs["Normal"])
    for face in mesh.data.polygons:
        face.material_index = 0
    mesh.data.materials.clear()
    mesh.data.materials.append(result)
    metadata = {"schema": "axm.character-surfaces/v0.1", "resolution": [resolution, resolution],
                "uv_layout": "unique smart-projected islands, 0.004 packing margin",
                "baked": ["base color", "roughness", "metallic", "local ambient occlusion", "tangent-space bump normal"],
                "occlusion": "16-sample local AO, 0.035 meter distance, packed red and linked for glTF",
                "source_palette_indices":sorted(set(palette_indices)),
                "source": "machine-authored procedural curvature wear, paint variation, and micrograin",
                "elapsed_seconds": round(time.monotonic() - started, 2),
                "quality_claim": "surface implementation evidence, not AAA certification"}
    (output / "surface-bake.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return result
