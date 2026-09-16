"""Bounded Blender worker. Launched by mesh_production, never imported by UC.

Only generated JSON and embedded GLB inputs are accepted by the parent. No
download, .blend intake, arbitrary script request or dependency installation.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
from pathlib import Path
import struct
import sys
import zlib

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree


def write_json(path, value):
    Path(path).write_text(json.dumps(value, sort_keys=True, indent=2)+"\n", encoding="utf-8")


def png(path, size, data):
    def chunk(kind, payload):
        return struct.pack(">I",len(payload))+kind+payload+struct.pack(">I",zlib.crc32(kind+payload)&0xffffffff)
    raw = b"".join(b"\0"+data[y*size*3:(y+1)*size*3] for y in range(size))
    Path(path).write_bytes(b"\x89PNG\r\n\x1a\n"+chunk(b"IHDR",struct.pack(">IIBBBBB",size,size,8,2,0,0,0))+chunk(b"IDAT",zlib.compress(raw,9))+chunk(b"IEND",b""))


def strip_png_metadata(path):
    body = path.read_bytes()
    offset,parts = 8,[body[:8]]
    while offset < len(body):
        size = struct.unpack_from(">I",body,offset)[0]
        kind = body[offset+4:offset+8]
        end = offset+12+size
        if kind in (b"IHDR",b"IDAT",b"IEND"):
            parts.append(body[offset:end])
        offset = end
    path.write_bytes(b"".join(parts))


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = 30
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.seed = 0
    scene.cycles.use_animated_seed = False
    scene.cycles.use_denoising = False
    scene.render.threads_mode = "FIXED"
    scene.render.threads = 2
    return scene


def unwrap(request, output):
    source = request["specification"]
    result = copy.deepcopy(source)
    resolution,padding = request["resolution"],request["padding_px"]
    margin = padding/resolution
    reset()
    for original, group in zip(source["primitives"],result["primitives"]):
        # Weld exact coincident positions for chart adjacency, retaining the
        # original corner normals/colors and triangle order in the derivative.
        vertices, lookup, remap = [], {}, []
        scale, location = original.get("size",[1,1,1]),original.get("translation",[0,0,0])
        for p in original["positions"]:
            key = tuple(p)
            if key not in lookup:
                lookup[key] = len(vertices)
                vertices.append([p[k]*scale[k]+location[k] for k in range(3)])
            remap.append(lookup[key])
        ids = original["indices"]
        faces = [[remap[v] for v in ids[i:i+3]] for i in range(0,len(ids),3)]
        mesh = bpy.data.meshes.new(group["id"])
        mesh.from_pydata(vertices,[],faces)
        mesh.update()
        obj = bpy.data.objects.new(group["id"],mesh)
        bpy.context.collection.objects.link(obj)
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.uv.smart_project(angle_limit=math.radians(request["angle_limit_degrees"]),
                                 island_margin=0.,correct_aspect=False,scale_to_bounds=True)
        bpy.ops.uv.pack_islands(rotate=True,scale=True,merge_overlap=False,
                                rotate_method="AXIS_ALIGNED",shape_method="AABB",
                                margin_method="FRACTION",margin=2*margin/(1-2*margin))
        bpy.ops.object.mode_set(mode="OBJECT")
        uv = mesh.uv_layers.active.data
        # A separate atlas-border reserve; it also leaves a conservative gap
        # between charts after the shrink. Independent native checks confirm it.
        coordinates = [[margin+(1-2*margin)*uv[loop].uv[k] for k in range(2)]
                       for poly in mesh.polygons for loop in poly.loop_indices]
        for key in ("positions","normals","colors"):
            if key in original:
                group[key] = [original[key][i] for i in ids]
        group["indices"] = list(range(len(ids)))
        # glTF's image convention uses the opposite V direction to Blender UVs.
        group["texcoords"] = [[u,1-v] for u,v in coordinates]
        bpy.data.objects.remove(obj,do_unlink=True)
    write_json(output/"surface.json",result)
    return {"operation":"unwrap","groups":len(result["primitives"]),"algorithm":"Blender Smart UV Project + fraction-margin packing"}


def import_asset(path):
    before = set(bpy.context.scene.objects)
    bpy.ops.import_scene.gltf(filepath=str(path),import_pack_images=True)
    objects = [o for o in bpy.context.scene.objects if o not in before]
    helpers = {b.custom_shape for o in objects if o.type == "ARMATURE" for b in o.pose.bones if b.custom_shape}
    return [o for o in objects if o.type == "MESH" and o not in helpers]


def projection_coverage(low,high,size,cage,distance):
    """Independent ray coverage; a missed Cycles normal can be neutral blue.

    Contract: start at low position + normal*cage, cast inward by cage+distance.
    Count unique interior texels. A neutral normal is never treated as hit proof.
    """
    high.data.calc_loop_triangles()
    tree = BVHTree.FromPolygons([high.matrix_world @ v.co for v in high.data.vertices],
                               [tuple(t.vertices) for t in high.data.loop_triangles],all_triangles=True)
    mesh = low.data
    mesh.calc_loop_triangles()
    uv = mesh.uv_layers.active.data
    matrix = low.matrix_world
    normal_matrix = matrix.to_3x3().inverted().transposed()
    covered,hits,visits = set(),set(),0
    for triangle in mesh.loop_triangles:
        coords = [uv[i].uv*size for i in triangle.loops]
        a,b,c = coords
        determinant = (b.y-c.y)*(a.x-c.x)+(c.x-b.x)*(a.y-c.y)
        if abs(determinant)<1e-9:
            continue
        points = [matrix @ mesh.vertices[i].co for i in triangle.vertices]
        normals = [(normal_matrix @ mesh.corner_normals[i].vector).normalized() for i in triangle.loops]
        for y in range(max(0,int(min(p.y for p in coords))),min(size,int(max(p.y for p in coords))+1)):
            for x in range(max(0,int(min(p.x for p in coords))),min(size,int(max(p.x for p in coords))+1)):
                visits += 1
                if visits > 8_000_000:
                    raise ValueError("projection coverage raster budget exceeded")
                u = ((b.y-c.y)*(x+.5-c.x)+(c.x-b.x)*(y+.5-c.y))/determinant
                v = ((c.y-a.y)*(x+.5-c.x)+(a.x-c.x)*(y+.5-c.y))/determinant
                w = 1-u-v
                if min(u,v,w)<=1e-6:
                    continue
                index = (size-1-y)*size+x
                covered.add(index)
                point = points[0]*u+points[1]*v+points[2]*w
                normal = (normals[0]*u+normals[1]*v+normals[2]*w).normalized()
                hit,_,_,_ = tree.ray_cast(point+normal*cage,-normal,cage+distance)
                if hit is not None:
                    hits.add(index)
    return {"covered_texels":len(covered),"unhit_texels":len(covered-hits),
            "contract":"low + normal*cage, inward ray length cage + max_ray_distance"}


def bake(request, output):
    scene = reset()
    scene.cycles.samples = request["samples"]
    lows = import_asset(request["asset"])
    highs = import_asset(request["high_asset"]) if request.get("high_asset") else []
    high_by_name = {obj.name.removesuffix(".001"):obj for obj in highs}
    size = request["size"]
    scene.render.bake.margin = request["margin_px"]
    scene.render.bake.use_clear = True
    scene.render.bake.normal_space = "TANGENT"
    scene.render.bake.normal_r,scene.render.bake.normal_g,scene.render.bake.normal_b = "POS_X","POS_Y","POS_Z"
    scene.render.bake.cage_extrusion = request["cage_extrusion"]
    scene.render.bake.max_ray_distance = request["max_ray_distance"]
    rows = []
    for obj in lows:
        name = obj.name
        row = {"id":name}
        for role in ("ao","normal") if highs else ("ao",):
            for h in highs:
                h.hide_render = role == "ao"
            bpy.ops.object.select_all(action="DESELECT")
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
            selected = role == "normal"
            scene.render.bake.use_selected_to_active = selected
            if selected:
                if name not in high_by_name:
                    raise ValueError("high-detail mesh must match each low group id: "+name)
                high_by_name[name].hide_render = False
                high_by_name[name].select_set(True)
                row["projection"] = projection_coverage(obj,high_by_name[name],size,request["cage_extrusion"],request["max_ray_distance"])
            image = bpy.data.images.new("AXM_BAKE_"+name+role,width=size,height=size,alpha=False,float_buffer=True)
            image.colorspace_settings.name = "Non-Color"
            nodes = []
            for slot in obj.material_slots:
                material = slot.material
                material.use_nodes = True
                node = material.node_tree.nodes.new("ShaderNodeTexImage")
                node.image = image
                material.node_tree.nodes.active = node
                nodes.append((material,node))
            bpy.ops.object.bake(type="NORMAL" if selected else "AO")
            pixels = list(image.pixels)
            data = bytearray()
            # Blender images are bottom-up; GLB/native PNGs are top-down.
            for y in reversed(range(size)):
                for x in range(size):
                    at = (y*size+x)*4
                    data.extend(round(max(0.,min(1.,pixels[at+c]))*255) for c in range(3))
            filename = name+"-"+role+".png"
            png(output/filename,size,bytes(data))
            row[role] = filename
            for material,node in nodes:
                material.node_tree.nodes.remove(node)
            bpy.data.images.remove(image)
        rows.append(row)
    return {"operation":"bake","groups":rows,"samples":request["samples"],"size":size,
            "normal_transfer":"selected-to-active tangent +Y" if highs else "not requested"}


def geometry(meshes):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    positions, triangles, bindings = [],0,[]
    for obj in meshes:
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        mesh.calc_loop_triangles()
        triangles += len(mesh.loop_triangles)
        for vertex in mesh.vertices:
            p = evaluated.matrix_world @ vertex.co
            positions.append([p.x,p.z,-p.y])  # back to glTF Y-up metres
        evaluated.to_mesh_clear()
        for slot in obj.material_slots:
            material = slot.material
            images = [n.image for n in material.node_tree.nodes if n.type == "TEX_IMAGE" and n.image] if material and material.use_nodes else []
            # glTF images are lazy: pixels access forces decoding before
            # has_data can truthfully describe the imported image.
            decoded = all(len(im.pixels) == im.size[0]*im.size[1]*4 and im.has_data and min(im.size)>0 for im in images)
            bindings.append({"object":obj.name,"images":len(images),"decoded_images":decoded,
                             "uv_layers":len(obj.data.uv_layers)})
    if not positions or any(not math.isfinite(v) for p in positions for v in p):
        raise ValueError("target import has empty or nonfinite geometry")
    return {"triangles":triangles,"bounds_m":{"min":[min(p[k] for p in positions) for k in range(3)],
                                             "max":[max(p[k] for p in positions) for k in range(3)]},
            "materials":bindings,"vertices":len(positions)}


def select_clip(name,time):
    found = name is None
    for obj in bpy.context.scene.objects:
        animation = obj.animation_data
        if animation:
            actions = [(track.name,strip.action) for track in animation.nla_tracks for strip in track.strips if strip.action]
            if animation.action:
                actions.append((animation.action.name,animation.action))
            animation.action = None
            for track in animation.nla_tracks:
                track.mute = True
            if name is not None:
                match = [action for label,action in actions if label == name or action.name == name or action.name.startswith(name+"_")]
                if match:
                    animation.action = match[0]
                    found = True
        if obj.type == "ARMATURE":
            for bone in obj.pose.bones:
                bone.matrix_basis.identity()
    if not found:
        raise ValueError("target could not select imported clip: "+str(name))
    frame = time*bpy.context.scene.render.fps
    bpy.context.scene.frame_set(int(frame),subframe=frame-int(frame))
    bpy.context.view_layer.update()


def lighting(scene,request,center,extent):
    scene.world = bpy.data.worlds.new("AXM studio environment")
    scene.world.use_nodes = True
    tree = scene.world.node_tree
    bg = tree.nodes.get("Background")
    bg.inputs["Strength"].default_value = request["environment_strength"]
    # Directional environment gradients are evaluated by Cycles for diffuse and
    # glossy rays. Area sources produce actual reflected highlights and shadows.
    coord = tree.nodes.new("ShaderNodeTexCoord")
    separate = tree.nodes.new("ShaderNodeSeparateXYZ")
    ramp = tree.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = .05
    ramp.color_ramp.elements[0].color = (.025,.035,.055,1)
    ramp.color_ramp.elements[1].position = .8
    ramp.color_ramp.elements[1].color = (.32,.43,.62,1)
    tree.links.new(coord.outputs["Normal"],separate.inputs[0])
    tree.links.new(separate.outputs["Z"],ramp.inputs[0])
    tree.links.new(ramp.outputs["Color"],bg.inputs["Color"])
    for name,offset,color,power,scale in [
        ("warm-key",(-2.4,-3.0,3.5),(1.,.78,.53),650,2.4),
        ("cool-strip",(2.5,.3,2.6),(.48,.72,1.),850,1.8),
        ("top-softbox",(0,1.8,4.),(1.,.96,.87),450,2.5)]:
        data = bpy.data.lights.new(name,"AREA")
        data.energy = power*extent*extent
        data.color = color
        data.shape = "RECTANGLE"
        data.size = scale*extent
        data.size_y = .4*extent
        obj = bpy.data.objects.new(name,data)
        scene.collection.objects.link(obj)
        obj.location = center+Vector(offset)*extent
        obj.rotation_euler = (center-obj.location).to_track_quat("-Z","Y").to_euler()
    floor_z = request["floor_z"]
    bpy.ops.mesh.primitive_plane_add(size=extent*200,location=(center.x,center.y,floor_z-.008*extent))
    floor = bpy.context.object
    floor.name = "inspection-floor"
    material = bpy.data.materials.new("inspection-floor")
    material.use_nodes = True
    material.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (.065,.085,.11,1)
    material.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = .42
    floor.data.materials.append(material)


def target(request,output):
    scene = reset()
    meshes = import_asset(request["asset"])
    select_clip(None,0.)
    initial = geometry(meshes)
    snapshots = []
    # Reimport for each pose: the observation cannot inherit transforms from a
    # prior animation or a renderer's retained state.
    for pose in request["poses"]:
        scene = reset()
        meshes = import_asset(request["asset"])
        select_clip(pose.get("clip"),pose.get("time_s",0.))
        snapshots.append({**pose,"geometry":geometry(meshes)})
    if request["render"]:
        for index,pose in enumerate(request["views"]):
            scene = reset()
            meshes = import_asset(request["asset"])
            select_clip(pose.get("clip"),pose.get("time_s",0.))
            g = geometry(meshes)
            lo,hi = g["bounds_m"]["min"],g["bounds_m"]["max"]
            center = Vector(((lo[0]+hi[0])/2,-(lo[2]+hi[2])/2,(lo[1]+hi[1])/2))
            extent = max(hi[k]-lo[k] for k in range(3))
            lighting(scene,{**request,"floor_z":lo[1]},center,extent)
            scene.cycles.samples = request["samples"]
            scene.cycles.use_denoising = request["denoise"]
            scene.cycles.max_bounces = 6
            scene.cycles.glossy_bounces = 4
            scene.render.resolution_x,scene.render.resolution_y = request["width"],request["height"]
            scene.render.resolution_percentage = 100
            scene.render.image_settings.file_format = "PNG"
            scene.render.image_settings.color_mode = "RGB"
            scene.render.image_settings.color_depth = "8"
            scene.view_settings.view_transform = "AgX"
            camera = bpy.data.objects.new("inspection-camera",bpy.data.cameras.new("inspection-camera"))
            scene.collection.objects.link(camera)
            yaw,elevation = pose["yaw"],pose["elevation"]
            direction = Vector((math.sin(yaw)*math.cos(elevation),-math.cos(yaw)*math.cos(elevation),math.sin(elevation)))
            camera.location = center+direction*extent*4
            camera.rotation_euler = (center-camera.location).to_track_quat("-Z","Y").to_euler()
            camera.data.type = "ORTHO"
            camera.data.ortho_scale = extent*1.5*max(1,request["width"]/request["height"])
            scene.camera = camera
            scene.render.filepath = str(output/f"view-{index:02d}.png")
            # Object coverage distinguishes an actual asset render from an
            # attractive but empty floor/environment image.
            for obj in meshes:
                obj.pass_index = 1
            bpy.context.view_layer.use_pass_object_index = True
            scene.use_nodes = True
            tree = scene.node_tree
            layer = next(n for n in tree.nodes if n.type == "R_LAYERS")
            mask = tree.nodes.new("CompositorNodeMath")
            mask.operation = "GREATER_THAN"
            mask.inputs[1].default_value = .5
            tree.links.new(layer.outputs["IndexOB"],mask.inputs[0])
            file_node = tree.nodes.new("CompositorNodeOutputFile")
            file_node.base_path = str(output)
            file_node.file_slots[0].path = f"coverage-{index:02d}-"
            file_node.format.file_format = "PNG"
            file_node.format.color_mode = "RGB"
            file_node.format.color_depth = "8"
            tree.links.new(mask.outputs[0],file_node.inputs[0])
            bpy.ops.render.render(write_still=True)
            strip_png_metadata(Path(scene.render.filepath))
            mask_path = next(output.glob(f"coverage-{index:02d}-*.png"))
            destination = output/f"coverage-{index:02d}.png"
            mask_path.rename(destination)
            strip_png_metadata(destination)
    return {"operation":"target","import":initial,"poses":snapshots,"rendered_views":request["views"] if request["render"] else [],
            "renderer":"Cycles CPU", "lighting":"directional environment + three reflected area sources", "view_transform":"AgX",
            "denoise":request["denoise"]}


def main():
    request_path = Path(sys.argv[sys.argv.index("--")+1])
    request = json.loads(request_path.read_text(encoding="utf-8"))
    output = Path(request["output"])
    result = {"unwrap":unwrap,"bake":bake,"target":target}[request["operation"]](request,output)
    result.update(blender_version=bpy.app.version_string,blender_build=bpy.app.build_hash.decode(),
                  worker_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    write_json(output/"worker-result.json",result)


if __name__ == "__main__":
    main()
