from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args(argv)


def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for data in (bpy.data.meshes, bpy.data.curves, bpy.data.materials, bpy.data.cameras, bpy.data.lights):
        for block in list(data):
            if block.users == 0:
                data.remove(block)


def material(name: str, color: tuple[float, float, float, float], *, metallic: float = 0.0,
             roughness: float = 0.45, emission: tuple[float, float, float, float] | None = None,
             emission_strength: float = 0.0) -> bpy.types.Material:
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = color
    mat.use_nodes = True
    node = mat.node_tree.nodes.get("Principled BSDF")
    node.inputs["Base Color"].default_value = color
    node.inputs["Metallic"].default_value = metallic
    node.inputs["Roughness"].default_value = roughness
    if not emission:
        noise = mat.node_tree.nodes.new("ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value = 18.0 if metallic > .5 else 9.0
        noise.inputs["Detail"].default_value = 5.0
        noise.inputs["Roughness"].default_value = .72
        color_ramp = mat.node_tree.nodes.new("ShaderNodeValToRGB")
        darker = tuple(max(0.0, channel * .72) for channel in color[:3]) + (1.0,)
        lighter = tuple(min(1.0, channel * 1.08 + .015) for channel in color[:3]) + (1.0,)
        color_ramp.color_ramp.elements[0].position = .20
        color_ramp.color_ramp.elements[0].color = darker
        color_ramp.color_ramp.elements[1].position = .82
        color_ramp.color_ramp.elements[1].color = lighter
        rough_map = mat.node_tree.nodes.new("ShaderNodeMapRange")
        rough_map.inputs["From Min"].default_value = 0.0
        rough_map.inputs["From Max"].default_value = 1.0
        rough_map.inputs["To Min"].default_value = max(.04, roughness - .09)
        rough_map.inputs["To Max"].default_value = min(1.0, roughness + .11)
        bump = mat.node_tree.nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = .055 if metallic > .5 else .035
        bump.inputs["Distance"].default_value = .018
        mat.node_tree.links.new(noise.outputs["Fac"], color_ramp.inputs["Fac"])
        mat.node_tree.links.new(color_ramp.outputs["Color"], node.inputs["Base Color"])
        mat.node_tree.links.new(noise.outputs["Fac"], rough_map.inputs["Value"])
        mat.node_tree.links.new(rough_map.outputs["Result"], node.inputs["Roughness"])
        mat.node_tree.links.new(noise.outputs["Fac"], bump.inputs["Height"])
        mat.node_tree.links.new(bump.outputs["Normal"], node.inputs["Normal"])
    if emission:
        socket = node.inputs.get("Emission Color") or node.inputs.get("Emission")
        if socket:
            socket.default_value = emission
        strength = node.inputs.get("Emission Strength")
        if strength:
            strength.default_value = emission_strength
    return mat


def wedge(name: str, location: tuple[float, float, float], dimensions: tuple[float, float, float],
          mat: bpy.types.Material, *, front_scale: tuple[float, float] = (.78, .82),
          rotation: tuple[float, float, float] = (0, 0, 0), bevel: float = .045) -> bpy.types.Object:
    hx, hy, hz = (value / 2 for value in dimensions)
    fx, fz = front_scale
    cut_x = min(hx * .32, hz * .42)
    cut_z = min(hz * .32, hx * .42)

    def ring(y: float, sx: float, sz: float) -> list[tuple[float, float, float]]:
        x, z, cx, cz = hx * sx, hz * sz, cut_x * sx, cut_z * sz
        return [
            (-x + cx, y, -z), (x - cx, y, -z), (x, y, -z + cz), (x, y, z - cz),
            (x - cx, y, z), (-x + cx, y, z), (-x, y, z - cz), (-x, y, -z + cz),
        ]

    vertices = ring(hy, 1.0, 1.0) + ring(-hy, fx, fz)
    faces = [tuple(reversed(range(8))), tuple(range(8, 16))]
    faces += [(i, (i + 1) % 8, 8 + (i + 1) % 8, 8 + i) for i in range(8)]
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.location = location
    obj.rotation_euler = rotation
    assign(obj, mat)
    return finish_mesh(obj, bevel=bevel * .62, segments=3, smooth=False)


def assign(obj: bpy.types.Object, mat: bpy.types.Material) -> bpy.types.Object:
    if obj.type == "MESH":
        obj.data.materials.append(mat)
    return obj


def finish_mesh(obj: bpy.types.Object, *, bevel: float = 0.0, segments: int = 3, smooth: bool = True) -> bpy.types.Object:
    if obj.type == "MESH" and smooth:
        for polygon in obj.data.polygons:
            polygon.use_smooth = True
    if bevel > 0:
        modifier = obj.modifiers.new("AXM_Bevel", "BEVEL")
        modifier.width = bevel
        modifier.segments = segments
        modifier.limit_method = "ANGLE"
    return obj


def box(name: str, location: tuple[float, float, float], dimensions: tuple[float, float, float],
        mat: bpy.types.Material, *, rotation: tuple[float, float, float] = (0, 0, 0), bevel: float = 0.06,
        segments: int = 3) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    assign(obj, mat)
    return finish_mesh(obj, bevel=bevel * .66, segments=segments, smooth=False)


def sphere(name: str, location: tuple[float, float, float], scale: tuple[float, float, float],
           mat: bpy.types.Material, *, segments: int = 40, rings: int = 24) -> bpy.types.Object:
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    assign(obj, mat)
    return finish_mesh(obj, smooth=True)


def cylinder(name: str, location: tuple[float, float, float], radius: float, depth: float,
             mat: bpy.types.Material, *, rotation: tuple[float, float, float] = (0, 0, 0), vertices: int = 32,
             bevel: float = 0.035) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    assign(obj, mat)
    return finish_mesh(obj, bevel=bevel, segments=3)


def cone(name: str, location: tuple[float, float, float], radius1: float, radius2: float, depth: float,
         mat: bpy.types.Material, *, rotation: tuple[float, float, float] = (0, 0, 0), vertices: int = 32,
         bevel: float = 0.025) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cone_add(vertices=vertices, radius1=radius1, radius2=radius2, depth=depth,
                                    location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    assign(obj, mat)
    return finish_mesh(obj, bevel=bevel, segments=3)


def torus(name: str, location: tuple[float, float, float], major: float, minor: float, mat: bpy.types.Material,
          *, rotation: tuple[float, float, float] = (0, 0, 0), major_segments: int = 48,
          minor_segments: int = 12) -> bpy.types.Object:
    bpy.ops.mesh.primitive_torus_add(major_radius=major, minor_radius=minor, major_segments=major_segments,
                                     minor_segments=minor_segments, location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    assign(obj, mat)
    return finish_mesh(obj, smooth=True)


def beam(name: str, start: tuple[float, float, float], end: tuple[float, float, float], radius: float,
         mat: bpy.types.Material, *, vertices: int = 24) -> bpy.types.Object:
    a, b = Vector(start), Vector(end)
    delta = b - a
    obj = cylinder(name, tuple((a + b) / 2), radius, delta.length, mat, vertices=vertices)
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = delta.to_track_quat("Z", "Y")
    return obj


def cable(name: str, points: list[tuple[float, float, float]], radius: float, mat: bpy.types.Material) -> bpy.types.Object:
    curve = bpy.data.curves.new(name, "CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 2
    curve.bevel_depth = radius
    curve.bevel_resolution = 3
    spline = curve.splines.new("BEZIER")
    spline.bezier_points.add(len(points) - 1)
    for point, value in zip(spline.bezier_points, points):
        point.co = value
        point.handle_left_type = "AUTO"
        point.handle_right_type = "AUTO"
    obj = bpy.data.objects.new(name, curve)
    bpy.context.collection.objects.link(obj)
    curve.materials.append(mat)
    return obj


def add_axiom_details(objects: list[bpy.types.Object], mats: dict[str, bpy.types.Material], rng: random.Random) -> None:
    gunmetal, pale, cyan, amber, dark = mats["gunmetal"], mats["pale"], mats["cyan"], mats["amber"], mats["dark"]
    # Grounded digitigrade legs with layered armor and visible mechanical articulation.
    for side in (-1, 1):
        prefix = "L" if side < 0 else "R"
        hip = (side * 0.82, 0.0, 2.45)
        knee = (side * 1.02, 0.10, 1.48)
        ankle = (side * 0.86, -0.10, 0.55)
        objects += [sphere(f"AX_{prefix}_HIP_JOINT", hip, (.30, .30, .30), dark)]
        objects += [beam(f"AX_{prefix}_THIGH_CORE", hip, knee, .25, gunmetal)]
        objects += [box(f"AX_{prefix}_THIGH_ARMOR", (side * .94, -.03, 1.98), (.55, .52, .90), pale,
                        rotation=(0, side * .18, side * .10), bevel=.09)]
        objects += [sphere(f"AX_{prefix}_KNEE", knee, (.32, .32, .32), gunmetal)]
        objects += [torus(f"AX_{prefix}_KNEE_RING", knee, .31, .055, cyan, rotation=(math.pi / 2, 0, 0))]
        objects += [beam(f"AX_{prefix}_SHIN_CORE", knee, ankle, .21, dark)]
        objects += [box(f"AX_{prefix}_SHIN_ARMOR", (side * .94, -.03, .99), (.52, .60, .78), gunmetal,
                        rotation=(0, side * -.10, side * -.05), bevel=.08)]
        objects += [box(f"AX_{prefix}_FOOT", (side * .84, -.18, .20), (.72, 1.05, .32), dark,
                        rotation=(0, 0, side * .02), bevel=.08)]
        objects += [box(f"AX_{prefix}_TOE_PLATE", (side * .84, -.60, .25), (.65, .42, .18), pale, bevel=.05)]
        for i in range(3):
            objects += [cylinder(f"AX_{prefix}_ANKLE_PISTON_{i}", (side * (.70 + i * .14), -.02, .60), .045,
                                 .72, pale, rotation=(0, side * .12, 0), vertices=16, bevel=.015)]

    # Pelvis, reactor torso, armored breastplate and command sensor head.
    objects += [box("AX_PELVIS", (0, 0, 2.62), (1.85, .95, .66), gunmetal, bevel=.13)]
    objects += [box("AX_PELVIS_FRONT", (0, -.47, 2.65), (1.18, .18, .40), pale, bevel=.05)]
    objects += [sphere("AX_REACTOR_CORE", (0, -.13, 3.42), (.62, .45, .70), cyan, segments=48, rings=32)]
    objects += [torus("AX_REACTOR_CAGE", (0, -.19, 3.42), .73, .075, pale, rotation=(math.pi / 2, 0, 0))]
    objects += [box("AX_TORSO_MAIN", (0, .05, 3.58), (2.30, 1.08, 1.58), gunmetal, bevel=.16)]
    objects += [box("AX_CHEST_PLATE", (0, -.53, 3.68), (1.62, .17, .96), pale,
                    rotation=(math.radians(7), 0, 0), bevel=.08)]
    objects += [box("AX_CHEST_CENTER", (0, -.67, 3.65), (.22, .09, .76), cyan, bevel=.025)]
    objects += [box("AX_NECK", (0, 0, 4.53), (.56, .52, .30), dark, bevel=.07)]
    objects += [box("AX_HEAD", (0, -.03, 4.86), (.88, .74, .55), pale, bevel=.11)]
    objects += [box("AX_VISOR", (0, -.43, 4.90), (.60, .065, .14), cyan, bevel=.025)]
    objects += [cylinder("AX_SENSOR_MAST", (0, .03, 5.35), .07, .68, gunmetal, vertices=20)]
    objects += [sphere("AX_SENSOR_ORB", (0, .03, 5.68), (.14, .14, .14), amber, segments=28, rings=18)]

    # Shoulder architecture and arms.
    for side in (-1, 1):
        prefix = "L" if side < 0 else "R"
        shoulder = (side * 1.48, 0, 4.04)
        elbow = (side * 1.68, .02, 3.10)
        wrist = (side * 1.52, -.08, 2.42)
        objects += [sphere(f"AX_{prefix}_SHOULDER_JOINT", shoulder, (.40, .40, .40), dark)]
        objects += [box(f"AX_{prefix}_PAULDRON", (side * 1.58, -.02, 4.18), (.86, 1.02, .68), pale,
                        rotation=(0, side * .12, side * .10), bevel=.13)]
        objects += [box(f"AX_{prefix}_PAULDRON_STRIPE", (side * 1.60, -.55, 4.18), (.42, .06, .18), amber, bevel=.02)]
        objects += [beam(f"AX_{prefix}_UPPER_ARM", shoulder, elbow, .25, gunmetal)]
        objects += [sphere(f"AX_{prefix}_ELBOW", elbow, (.27, .27, .27), dark)]
        objects += [torus(f"AX_{prefix}_ELBOW_RING", elbow, .26, .045, cyan, rotation=(math.pi / 2, 0, 0))]
        objects += [beam(f"AX_{prefix}_FOREARM", elbow, wrist, .23, gunmetal)]
        objects += [box(f"AX_{prefix}_FOREARM_ARMOR", (side * 1.62, -.05, 2.76), (.55, .66, .66), pale, bevel=.08)]
        objects += [box(f"AX_{prefix}_HAND", wrist, (.38, .46, .30), dark, bevel=.06)]

    # Rail cannon mounted on the right arm, shield/projector on the left.
    objects += [box("AX_RAIL_BODY", (2.05, -.34, 2.82), (.72, 1.65, .54), gunmetal,
                    rotation=(0, 0, 0), bevel=.08)]
    for x in (1.88, 2.22):
        objects += [beam(f"AX_RAIL_{x:.2f}", (x, -.72, 2.84), (x, -2.05, 2.84), .075, pale, vertices=20)]
    objects += [box("AX_RAIL_EMITTER", (2.05, -2.10, 2.84), (.58, .18, .36), cyan, bevel=.04)]
    objects += [cylinder("AX_SHIELD_DISC", (-2.05, -.52, 2.86), .62, .14, pale,
                         rotation=(math.pi / 2, 0, 0), vertices=48, bevel=.06)]
    objects += [torus("AX_SHIELD_RING", (-2.05, -.61, 2.86), .48, .055, cyan,
                      rotation=(math.pi / 2, 0, 0))]
    objects += [sphere("AX_SHIELD_CORE", (-2.05, -.69, 2.86), (.16, .09, .16), amber)]

    # Rear heat vanes, thrusters, vents, bolts, and animated-looking cable language.
    for side in (-1, 1):
        for i in range(3):
            x = side * (.50 + i * .22)
            objects += [box(f"AX_HEAT_VANE_{side}_{i}", (x, .69 + i * .035, 3.70), (.10, .44, .92), dark,
                            rotation=(side * -.12, 0, side * .12), bevel=.025)]
        objects += [cylinder(f"AX_THRUSTER_{side}", (side * .79, .74, 3.18), .25, .62, gunmetal,
                             rotation=(math.pi / 2, 0, 0), vertices=32)]
        objects += [cone(f"AX_THRUSTER_GLOW_{side}", (side * .79, 1.08, 3.18), .18, .08, .18, cyan,
                         rotation=(math.pi / 2, 0, 0), vertices=32)]
        cable_obj = cable(f"AX_CABLE_{side}", [(side * .72, .55, 3.95), (side * 1.10, .77, 3.55),
                                                (side * 1.42, .48, 3.08)], .035, amber)
        objects.append(cable_obj)
    for row in range(4):
        for col in range(5):
            x = (col - 2) * .29
            z = 3.25 + row * .24
            objects += [cylinder(f"AX_CHEST_BOLT_{row}_{col}", (x, -.655, z), .026, .045, dark,
                                 rotation=(math.pi / 2, 0, 0), vertices=12, bevel=.008)]
    for i in range(8):
        x = rng.uniform(-.82, .82)
        objects += [box(f"AX_MICRO_PANEL_{i}", (x, -.682, rng.uniform(3.28, 4.08)),
                        (rng.uniform(.08, .18), .025, rng.uniform(.04, .10)), amber if i % 3 == 0 else dark,
                        bevel=.008, segments=2)]

    # Hero-detail pass: interlocking armor replaces the primitive read with a
    # large/medium/small hierarchy while retaining the deterministic chassis.
    objects += [wedge("AX_HERO_ABDOMEN", (0, -.56, 3.02), (1.30, .30, .64), gunmetal,
                      front_scale=(.72, .68), rotation=(math.radians(-7), 0, 0), bevel=.055)]
    objects += [wedge("AX_HERO_CHEST_L", (-.57, -.70, 3.78), (1.03, .28, 1.10), pale,
                      front_scale=(.76, .86), rotation=(math.radians(5), math.radians(-5), math.radians(-4)), bevel=.06)]
    objects += [wedge("AX_HERO_CHEST_R", (.57, -.70, 3.78), (1.03, .28, 1.10), pale,
                      front_scale=(.76, .86), rotation=(math.radians(5), math.radians(5), math.radians(4)), bevel=.06)]
    objects += [wedge("AX_HERO_REACTOR_WINDOW", (0, -.88, 3.61), (.49, .12, .90), cyan,
                      front_scale=(.72, .82), bevel=.025)]
    objects += [box("AX_HERO_REACTOR_TOP", (0, -.91, 4.10), (.56, .10, .09), amber, bevel=.018)]
    objects += [box("AX_HERO_REACTOR_BOTTOM", (0, -.91, 3.12), (.46, .10, .09), dark, bevel=.018)]
    for side in (-1, 1):
        prefix = "L" if side < 0 else "R"
        objects += [wedge(f"AX_HERO_TORSO_FLANK_{prefix}", (side * 1.06, -.47, 3.68), (.58, .55, 1.30), gunmetal,
                          front_scale=(.62, .76), rotation=(0, side * math.radians(8), side * math.radians(5)), bevel=.055)]
        objects += [wedge(f"AX_HERO_COLLAR_{prefix}", (side * .62, -.38, 4.43), (.91, .45, .34), pale,
                          front_scale=(.74, .66), rotation=(0, side * math.radians(10), side * math.radians(7)), bevel=.045)]
        for slot in range(4):
            objects += [box(f"AX_HERO_VENT_{prefix}_{slot}", (side * 1.18, -.785, 3.40 + slot * .20),
                            (.16, .055, .10), dark, rotation=(0, 0, side * math.radians(5)), bevel=.012)]

        # Angular shoulder carapace with nested armor and a recessed service bay.
        objects += [wedge(f"AX_HERO_SHOULDER_OUTER_{prefix}", (side * 1.70, -.10, 4.24), (.96, 1.18, .86), gunmetal,
                          front_scale=(.68, .74), rotation=(0, side * math.radians(9), side * math.radians(7)), bevel=.07)]
        objects += [wedge(f"AX_HERO_SHOULDER_CAP_{prefix}", (side * 1.72, -.68, 4.26), (.72, .18, .58), pale,
                          front_scale=(.72, .80), rotation=(0, side * math.radians(6), side * math.radians(7)), bevel=.045)]
        objects += [box(f"AX_HERO_SHOULDER_LIGHT_{prefix}", (side * 1.72, -.80, 4.27), (.29, .045, .065), amber, bevel=.012)]
        for slot in range(3):
            objects += [box(f"AX_HERO_SHOULDER_SLOT_{prefix}_{slot}",
                            (side * (1.46 + slot * .12), -.81, 4.03), (.065, .038, .23), dark, bevel=.008)]

        # Layered arm armor, exposed actuator pistons and guarded elbow.
        objects += [wedge(f"AX_HERO_BICEP_{prefix}", (side * 1.58, -.12, 3.58), (.62, .66, .82), gunmetal,
                          front_scale=(.70, .70), rotation=(0, side * math.radians(5), side * math.radians(4)), bevel=.055)]
        objects += [box(f"AX_HERO_BICEP_FACE_{prefix}", (side * 1.59, -.49, 3.58), (.34, .075, .46), pale, bevel=.035)]
        objects += [wedge(f"AX_HERO_FOREARM_COWL_{prefix}", (side * 1.60, -.14, 2.77), (.66, .78, .78), gunmetal,
                          front_scale=(.72, .74), rotation=(0, side * math.radians(4), side * math.radians(3)), bevel=.055)]
        objects += [box(f"AX_HERO_FOREARM_RAIL_{prefix}", (side * 1.78, -.52, 2.77), (.12, .12, .50), pale, bevel=.022)]
        for piston in (-1, 1):
            objects += [beam(f"AX_HERO_ARM_PISTON_{prefix}_{piston}",
                             (side * (1.37 + piston * .07), -.32, 3.35),
                             (side * (1.44 + piston * .07), -.36, 2.95), .035, amber, vertices=16)]

        # Thigh/shin shells and three-part armored feet.
        objects += [wedge(f"AX_HERO_THIGH_FRONT_{prefix}", (side * .95, -.38, 1.98), (.66, .34, 1.02), pale,
                          front_scale=(.68, .82), rotation=(0, side * math.radians(5), side * math.radians(3)), bevel=.052)]
        objects += [wedge(f"AX_HERO_THIGH_SIDE_{prefix}", (side * 1.25, -.02, 1.96), (.24, .58, .80), gunmetal,
                          front_scale=(.62, .76), rotation=(0, side * math.radians(6), 0), bevel=.038)]
        objects += [wedge(f"AX_HERO_KNEE_GUARD_{prefix}", (side * 1.02, -.46, 1.46), (.58, .24, .52), gunmetal,
                          front_scale=(.66, .72), bevel=.045)]
        objects += [box(f"AX_HERO_KNEE_LIGHT_{prefix}", (side * 1.02, -.60, 1.47), (.22, .045, .08), cyan, bevel=.014)]
        objects += [wedge(f"AX_HERO_SHIN_FRONT_{prefix}", (side * .91, -.39, .86), (.60, .30, .88), pale,
                          front_scale=(.62, .78), rotation=(0, side * math.radians(-4), side * math.radians(-2)), bevel=.05)]
        objects += [box(f"AX_HERO_SHIN_CHANNEL_{prefix}", (side * .91, -.56, .86), (.16, .055, .52), dark, bevel=.018)]
        objects += [box(f"AX_HERO_ANKLE_COWL_{prefix}", (side * .84, -.15, .42), (.58, .56, .34), gunmetal, bevel=.06)]
        for toe in (-1, 0, 1):
            objects += [wedge(f"AX_HERO_TOE_{prefix}_{toe}", (side * (.84 + toe * .19), -.69, .17),
                              (.17, .58, .18), pale if toe == 0 else gunmetal,
                              front_scale=(.62, .58), rotation=(0, 0, side * toe * math.radians(3)), bevel=.035)]

    # A compact command sensor cluster prevents the head from reading as a toy face.
    objects += [wedge("AX_HERO_HEAD_FACE", (0, -.44, 4.88), (.70, .18, .36), dark,
                      front_scale=(.72, .70), bevel=.04)]
    for eye in (-1, 1):
        objects += [sphere(f"AX_HERO_OPTIC_{eye}", (eye * .17, -.55, 4.91), (.075, .045, .075), cyan,
                           segments=24, rings=16)]
        objects += [box(f"AX_HERO_OPTIC_GUARD_{eye}", (eye * .17, -.51, 5.05), (.22, .10, .05), pale, bevel=.012)]
    objects += [box("AX_HERO_HEAD_BROW", (0, -.51, 5.12), (.62, .10, .10), gunmetal, bevel=.022)]
    for side in (-1, 1):
        objects += [cylinder(f"AX_HERO_HEAD_DISC_{side}", (side * .48, -.04, 4.88), .18, .12, gunmetal,
                             rotation=(0, math.pi / 2, 0), vertices=32)]
        objects += [torus(f"AX_HERO_HEAD_DISC_RING_{side}", (side * .55, -.04, 4.88), .14, .025, amber,
                          rotation=(0, math.pi / 2, 0), major_segments=32, minor_segments=8)]

    # Rail cannon receives functional coil, cooling, housing and sight details.
    for stage in range(5):
        y = -.86 - stage * .28
        objects += [box(f"AX_HERO_RAIL_HOUSING_{stage}", (2.05, y, 2.84),
                        (.72 - stage * .035, .20, .46 - stage * .025), gunmetal if stage % 2 else pale, bevel=.035)]
        objects += [torus(f"AX_HERO_RAIL_COIL_{stage}", (2.05, y - .09, 2.84), .24 - stage * .01, .028, cyan,
                          rotation=(math.pi / 2, 0, 0), major_segments=32, minor_segments=8)]
    for side in (-1, 1):
        objects += [box(f"AX_HERO_RAIL_SIDE_{side}", (2.05 + side * .32, -1.30, 2.84), (.08, 1.50, .54), dark, bevel=.025)]
    objects += [box("AX_HERO_RAIL_SIGHT", (2.05, -1.36, 3.24), (.22, .48, .18), amber, bevel=.025)]

    # Shield projector gets visible stacked emitter architecture.
    for radius, depth, mat in ((.66, .10, gunmetal), (.53, .075, pale), (.39, .05, cyan)):
        objects += [torus(f"AX_HERO_SHIELD_LAYER_{radius}", (-2.05, -.65 - depth, 2.86), radius, depth, mat,
                          rotation=(math.pi / 2, 0, 0), major_segments=64, minor_segments=12)]
    for i in range(8):
        angle = i * math.tau / 8
        objects += [box(f"AX_HERO_SHIELD_NODE_{i}", (-2.05 + math.cos(angle) * .52, -.80,
                                                      2.86 + math.sin(angle) * .52),
                        (.10, .06, .16), amber if i % 2 else dark, rotation=(0, 0, angle), bevel=.018)]


def add_axiom_hero_v3(objects: list[bpy.types.Object], mats: dict[str, bpy.types.Material], rng: random.Random) -> None:
    """Layered military walker derived from the Axiom faction grammar.

    This builder deliberately avoids the legacy box-body topology. Every major
    mass is assembled from tapered load-bearing volumes and nested armor shells.
    """
    gm, pale, cyan, amber, dark = (mats[k] for k in ("gunmetal", "pale", "cyan", "amber", "dark"))

    # Feet and legs: wide armored stance, separate toes, visible ankle/knee mechanics.
    for side in (-1, 1):
        p = "L" if side < 0 else "R"
        x = side * .73
        for toe in (-1, 0, 1):
            objects.append(wedge(f"AX3_{p}_TOE_{toe}", (x + toe * .18, -.50, .15), (.18, .80, .22),
                                 pale if toe == 0 else gm, front_scale=(.58, .52),
                                 rotation=(0, 0, toe * math.radians(3)), bevel=.026))
        objects.append(wedge(f"AX3_{p}_HEEL", (x, .13, .20), (.72, .68, .32), dark,
                             front_scale=(.72, .64), rotation=(math.radians(-3), 0, 0), bevel=.045))
        ankle = (x, -.02, .48)
        knee = (side * .80, -.02, 1.60)
        hip = (side * .70, .02, 2.68)
        objects.append(sphere(f"AX3_{p}_ANKLE", ankle, (.24, .24, .24), dark, segments=32, rings=20))
        for piston in (-1, 1):
            objects.append(beam(f"AX3_{p}_ANKLE_PISTON_{piston}",
                                (x + piston * .16, -.06, .36), (x + piston * .13, -.04, .78), .035, amber, vertices=16))
        objects.append(beam(f"AX3_{p}_SHIN_CORE", ankle, knee, .19, dark, vertices=32))
        objects.append(sphere(f"AX3_{p}_SHIN_MAIN", (side * .78, -.10, 1.03), (.39, .40, .65), gm,
                              segments=44, rings=28))
        objects.append(wedge(f"AX3_{p}_SHIN_FRONT", (side * .78, -.50, 1.06), (.49, .19, .98), pale,
                             front_scale=(.66, .70), rotation=(0, side * math.radians(-3), 0), bevel=.036))
        objects.append(box(f"AX3_{p}_SHIN_CHANNEL", (side * .78, -.615, 1.02), (.12, .035, .60), dark, bevel=.01))
        objects.append(box(f"AX3_{p}_SHIN_LIGHT", (side * .78, -.64, .76), (.075, .025, .15), cyan, bevel=.008))
        objects.append(sphere(f"AX3_{p}_KNEE_MECH", knee, (.34, .34, .34), dark, segments=36, rings=22))
        objects.append(cylinder(f"AX3_{p}_KNEE_AXLE", knee, .26, .82, gm, rotation=(0, math.pi / 2, 0), vertices=36))
        objects.append(wedge(f"AX3_{p}_KNEE_GUARD", (side * .80, -.40, 1.62), (.64, .30, .62), pale,
                             front_scale=(.58, .62), rotation=(math.radians(-4), 0, 0), bevel=.043))
        objects.append(box(f"AX3_{p}_KNEE_MARK", (side * .80, -.58, 1.65), (.20, .035, .075), amber, bevel=.01))
        objects.append(beam(f"AX3_{p}_THIGH_CORE", knee, hip, .24, dark, vertices=32))
        objects.append(sphere(f"AX3_{p}_THIGH_MAIN", (side * .74, -.02, 2.18), (.47, .45, .64), gm,
                              segments=48, rings=30))
        objects.append(wedge(f"AX3_{p}_THIGH_FRONT", (side * .74, -.48, 2.20), (.56, .18, .84), pale,
                             front_scale=(.68, .74), rotation=(0, side * math.radians(4), 0), bevel=.038))
        objects.append(wedge(f"AX3_{p}_THIGH_OUTER", (side * 1.12, .02, 2.22), (.22, .62, .76), dark,
                             front_scale=(.62, .68), rotation=(0, side * math.radians(8), 0), bevel=.032))
        for piston in (-1, 1):
            objects.append(beam(f"AX3_{p}_KNEE_PISTON_{piston}",
                                (side * (.56 + piston * .07), -.18, 1.74),
                                (side * (.60 + piston * .07), -.15, 2.42), .038, pale, vertices=18))

    # Pelvis, waist bearing and segmented armored abdomen.
    objects.append(sphere("AX3_PELVIS_CORE", (0, .02, 2.72), (1.00, .58, .40), dark,
                          segments=52, rings=32))
    objects.append(wedge("AX3_PELVIS_FRONT", (0, -.58, 2.74), (1.36, .20, .47), gm,
                         front_scale=(.62, .60), bevel=.035))
    objects.append(box("AX3_PELVIS_SIGNAL", (0, -.70, 2.78), (.38, .035, .08), amber, bevel=.012))
    objects.append(torus("AX3_WAIST_BEARING", (0, 0, 3.05), .60, .10, gm, major_segments=64, minor_segments=16))
    objects.append(cylinder("AX3_WAIST_CORE", (0, 0, 3.05), .46, .35, dark, vertices=48))
    for level, (z, width) in enumerate(((3.16, 1.22), (3.35, 1.44), (3.54, 1.68))):
        objects.append(wedge(f"AX3_AB_SEGMENT_{level}", (0, -.16, z), (width, .78, .27), gm,
                             front_scale=(.72, .64), rotation=(math.radians(-4 + level * 2), 0, 0), bevel=.035))
        objects.append(box(f"AX3_AB_SEAM_{level}", (0, -.58, z), (width * .60, .035, .035), dark, bevel=.006))

    # Deep torso volume, separated pectoral armor, collar and exposed cyan reactor.
    objects.append(sphere("AX3_TORSO_CORE", (0, .04, 4.02), (1.42, .76, .94), dark,
                          segments=64, rings=40))
    objects.append(wedge("AX3_CHEST_LEFT", (-.62, -.69, 4.04), (1.23, .24, 1.18), gm,
                         front_scale=(.64, .74), rotation=(math.radians(4), math.radians(-5), math.radians(-3)), bevel=.055))
    objects.append(wedge("AX3_CHEST_RIGHT", (.62, -.69, 4.04), (1.23, .24, 1.18), gm,
                         front_scale=(.64, .74), rotation=(math.radians(4), math.radians(5), math.radians(3)), bevel=.055))
    objects.append(wedge("AX3_CHEST_PLATE_LEFT", (-.65, -.85, 4.04), (.92, .11, .84), pale,
                         front_scale=(.70, .76), rotation=(math.radians(4), math.radians(-5), math.radians(-3)), bevel=.032))
    objects.append(wedge("AX3_CHEST_PLATE_RIGHT", (.65, -.85, 4.04), (.92, .11, .84), pale,
                         front_scale=(.70, .76), rotation=(math.radians(4), math.radians(5), math.radians(3)), bevel=.032))
    objects.append(wedge("AX3_REACTOR", (0, -.92, 3.98), (.54, .14, .92), cyan,
                         front_scale=(.68, .72), bevel=.022))
    for side in (-1, 1):
        objects.append(box(f"AX3_REACTOR_RAIL_{side}", (side * .34, -.92, 3.98), (.09, .08, 1.00), amber, bevel=.015))
        objects.append(wedge(f"AX3_COLLAR_{side}", (side * .70, -.42, 4.73), (1.15, .66, .35), pale,
                             front_scale=(.66, .62), rotation=(math.radians(2), side * math.radians(7), side * math.radians(6)), bevel=.04))
        objects.append(wedge(f"AX3_TORSO_SIDE_{side}", (side * 1.33, -.05, 3.98), (.44, 1.05, 1.20), gm,
                             front_scale=(.58, .72), rotation=(0, side * math.radians(8), 0), bevel=.045))
        for vent in range(5):
            objects.append(box(f"AX3_CHEST_VENT_{side}_{vent}", (side * 1.32, -.61, 3.67 + vent * .17),
                               (.13, .045, .09), dark, rotation=(0, 0, side * math.radians(5)), bevel=.009))

    # Small command head with guarded optics and rear antennae.
    objects.append(cylinder("AX3_NECK", (0, 0, 4.90), .28, .34, dark, vertices=36))
    objects.append(sphere("AX3_HEAD_CORE", (0, -.02, 5.16), (.46, .38, .30), gm,
                          segments=40, rings=24))
    objects.append(wedge("AX3_HEAD_FACE", (0, -.43, 5.16), (.65, .16, .30), dark,
                         front_scale=(.66, .62), bevel=.028))
    for eye in (-1, 1):
        objects.append(sphere(f"AX3_OPTIC_{eye}", (eye * .17, -.535, 5.18), (.075, .045, .075), cyan,
                              segments=24, rings=16))
        objects.append(box(f"AX3_OPTIC_BROW_{eye}", (eye * .17, -.50, 5.32), (.25, .08, .055), pale, bevel=.012))
    objects.append(box("AX3_HEAD_LOWER_SENSOR", (0, -.52, 5.00), (.28, .045, .055), amber, bevel=.009))
    for side in (-1, 1):
        objects.append(cylinder(f"AX3_HEAD_COMMS_{side}", (side * .46, -.02, 5.15), .16, .12, pale,
                                rotation=(0, math.pi / 2, 0), vertices=32))
    objects.append(cylinder("AX3_ANTENNA", (0, .08, 5.70), .045, .88, dark, vertices=16, bevel=.01))
    objects.append(sphere("AX3_ANTENNA_LIGHT", (0, .08, 6.14), (.075, .075, .075), amber, segments=24, rings=16))

    # Shoulders and arms: thick frame, recessed joint mechanics, layered pauldrons.
    for side in (-1, 1):
        p = "L" if side < 0 else "R"
        shoulder = (side * 1.65, -.02, 4.45)
        elbow = (side * 1.78, -.06, 3.44)
        wrist = (side * 1.72, -.16, 2.70)
        objects.append(beam(f"AX3_{p}_CLAVICLE", (side * 1.05, 0, 4.48), shoulder, .22, dark, vertices=28))
        objects.append(sphere(f"AX3_{p}_SHOULDER_JOINT", shoulder, (.42, .42, .42), dark, segments=40, rings=24))
        objects.append(wedge(f"AX3_{p}_PAULDRON_MAIN", (side * 1.82, -.06, 4.58), (1.04, 1.14, .92), gm,
                             front_scale=(.62, .68), rotation=(0, side * math.radians(9), side * math.radians(6)), bevel=.065))
        objects.append(wedge(f"AX3_{p}_PAULDRON_FACE", (side * 1.84, -.68, 4.58), (.78, .18, .64), pale,
                             front_scale=(.64, .70), rotation=(0, side * math.radians(7), side * math.radians(6)), bevel=.04))
        objects.append(box(f"AX3_{p}_PAULDRON_SIGNAL", (side * 1.84, -.79, 4.59), (.28, .035, .07), amber, bevel=.01))
        objects.append(beam(f"AX3_{p}_UPPER_ARM_CORE", shoulder, elbow, .22, dark, vertices=32))
        objects.append(sphere(f"AX3_{p}_BICEP", (side * 1.75, -.04, 3.92), (.40, .39, .50), gm,
                              segments=44, rings=28))
        objects.append(wedge(f"AX3_{p}_BICEP_FACE", (side * 1.75, -.45, 3.92), (.46, .13, .58), pale,
                             front_scale=(.65, .72), bevel=.03))
        objects.append(cylinder(f"AX3_{p}_ELBOW_AXLE", elbow, .26, .74, gm, rotation=(0, math.pi / 2, 0), vertices=36))
        objects.append(torus(f"AX3_{p}_ELBOW_RING", elbow, .27, .045, cyan,
                            rotation=(math.pi / 2, 0, 0), major_segments=40, minor_segments=10))
        objects.append(beam(f"AX3_{p}_FOREARM_CORE", elbow, wrist, .20, dark, vertices=28))
        objects.append(sphere(f"AX3_{p}_FOREARM", (side * 1.74, -.08, 3.03), (.40, .43, .50), gm,
                              segments=44, rings=28))
        objects.append(wedge(f"AX3_{p}_FOREARM_FACE", (side * 1.74, -.52, 3.03), (.48, .14, .58), pale,
                             front_scale=(.64, .68), bevel=.032))
        for piston in (-1, 1):
            objects.append(beam(f"AX3_{p}_ARM_PISTON_{piston}",
                                (side * (1.53 + piston * .06), -.18, 3.60),
                                (side * (1.56 + piston * .06), -.20, 3.18), .035, amber, vertices=16))
        objects.append(wedge(f"AX3_{p}_HAND", wrist, (.52, .54, .34), dark, front_scale=(.62, .62), bevel=.04))

    # Left-side integrated rail cannon: long, tapered and mechanically layered.
    gun_x = -1.78
    objects.append(wedge("AX3_RAIL_CORE", (gun_x, -.30, 1.72), (.62, .84, 3.10), dark,
                         front_scale=(.64, .82), rotation=(math.radians(4), 0, 0), bevel=.055))
    objects.append(wedge("AX3_RAIL_ARMOR", (gun_x, -.76, 1.82), (.48, .16, 2.68), gm,
                         front_scale=(.62, .78), rotation=(math.radians(4), 0, 0), bevel=.035))
    for rail in (-1, 1):
        objects.append(box(f"AX3_RAIL_TRACK_{rail}", (gun_x + rail * .22, -.82, 1.70), (.07, .08, 2.78), pale, bevel=.018))
    for coil in range(7):
        z = .72 + coil * .33
        objects.append(box(f"AX3_RAIL_COIL_{coil}", (gun_x, -.905, z), (.24, .035, .13), cyan, bevel=.01))
    objects.append(wedge("AX3_RAIL_MUZZLE", (gun_x, -.34, .22), (.68, .92, .42), gm,
                         front_scale=(.58, .55), rotation=(math.radians(4), 0, 0), bevel=.045))
    objects.append(box("AX3_RAIL_SIGHT", (gun_x, -.80, 3.28), (.24, .22, .36), amber, bevel=.028))

    # Right forearm energy shield: elongated hexagonal silhouette and emitter stack.
    shield_x = 2.15
    objects.append(wedge("AX3_SHIELD_FRAME", (shield_x, -.66, 3.06), (.82, .22, 1.88), gm,
                         front_scale=(.62, .72), rotation=(0, 0, 0), bevel=.055))
    objects.append(wedge("AX3_SHIELD_ARMOR", (shield_x, -.81, 3.06), (.64, .10, 1.56), pale,
                         front_scale=(.60, .70), bevel=.035))
    objects.append(wedge("AX3_SHIELD_ENERGY", (shield_x, -.90, 3.06), (.45, .055, 1.30), cyan,
                         front_scale=(.58, .68), bevel=.022))
    for notch in (-1, 1):
        objects.append(box(f"AX3_SHIELD_RAIL_{notch}", (shield_x + notch * .30, -.84, 3.06),
                           (.055, .08, 1.52), amber, bevel=.012))

    # Rear power plant, vent stacks and cables provide a readable back view.
    for side in (-1, 1):
        objects.append(wedge(f"AX3_BACK_REACTOR_{side}", (side * .72, .72, 4.04), (.72, .42, 1.08), gm,
                             front_scale=(.62, .72), rotation=(math.radians(-5), side * math.radians(4), 0), bevel=.045))
        objects.append(cylinder(f"AX3_BACK_THRUSTER_{side}", (side * .72, .98, 3.82), .22, .44, dark,
                                rotation=(math.pi / 2, 0, 0), vertices=36))
        objects.append(cone(f"AX3_BACK_GLOW_{side}", (side * .72, 1.23, 3.82), .16, .06, .20, cyan,
                            rotation=(math.pi / 2, 0, 0), vertices=32))
        for vent in range(4):
            objects.append(box(f"AX3_BACK_VENT_{side}_{vent}", (side * (.48 + vent * .13), .87, 4.43),
                               (.075, .18, .48), dark, rotation=(side * math.radians(-4), 0, side * math.radians(3)), bevel=.012))
        objects.append(cable(f"AX3_POWER_CABLE_{side}", [
            (side * .58, .61, 4.52), (side * 1.10, .80, 4.10), (side * 1.46, .50, 3.45)
        ], .035, amber))

    # Small-form pass: panel fasteners and edge light blocks on major masses.
    for row in range(5):
        for column in range(6):
            x = (column - 2.5) * .30
            z = 3.72 + row * .18
            if abs(x) < .32:
                continue
            objects.append(cylinder(f"AX3_CHEST_FASTENER_{row}_{column}", (x, -.925, z), .019, .035, dark,
                                    rotation=(math.pi / 2, 0, 0), vertices=10, bevel=.005))
    for side in (-1, 1):
        p = "L" if side < 0 else "R"
        # Secondary armor tiles break broad surfaces into maintainable modules.
        for tile in range(3):
            objects.append(wedge(f"AX3_{p}_PAULDRON_TILE_{tile}",
                                 (side * (1.57 + tile * .13), -.795, 4.42 + (tile % 2) * .16),
                                 (.11, .035, .22), pale if tile == 1 else gm,
                                 front_scale=(.62, .66), rotation=(0, 0, side * math.radians(5)), bevel=.012))
            objects.append(cylinder(f"AX3_{p}_PAULDRON_BOLT_{tile}",
                                    (side * (1.57 + tile * .13), -.825, 4.30), .016, .025, dark,
                                    rotation=(math.pi / 2, 0, 0), vertices=10, bevel=.004))
        for tile in range(4):
            objects.append(wedge(f"AX3_{p}_THIGH_TILE_{tile}",
                                 (side * (.64 + (tile % 2) * .20), -.585, 1.92 + (tile // 2) * .36),
                                 (.17, .038, .24), gm if tile % 2 else pale,
                                 front_scale=(.60, .64), rotation=(0, 0, side * math.radians(2)), bevel=.012))
            objects.append(wedge(f"AX3_{p}_SHIN_TILE_{tile}",
                                 (side * (.67 + (tile % 2) * .20), -.625, .79 + (tile // 2) * .30),
                                 (.15, .038, .20), gm if tile % 2 else pale,
                                 front_scale=(.58, .62), rotation=(0, 0, side * math.radians(-2)), bevel=.010))
        for channel in (-1, 1):
            objects.append(beam(f"AX3_{p}_LEG_HYDRAULIC_{channel}",
                                (side * (.53 + channel * .055), .12, .72),
                                (side * (.58 + channel * .055), .15, 1.42), .027, amber, vertices=14))
            objects.append(beam(f"AX3_{p}_ARM_HYDRAULIC_{channel}",
                                (side * (1.50 + channel * .055), .18, 3.02),
                                (side * (1.54 + channel * .055), .20, 3.72), .027, pale, vertices=14))
    for i in range(12):
        side = -1 if i % 2 == 0 else 1
        objects.append(box(f"AX3_EDGE_LIGHT_{i}", (side * rng.uniform(.42, 1.28), -.90, rng.uniform(3.64, 4.52)),
                           (.055, .025, .10), cyan if i % 3 else amber, bevel=.008))


def add_mir_details(objects: list[bpy.types.Object], mats: dict[str, bpy.types.Material], rng: random.Random) -> None:
    ivory, brass, rose, cyan, magenta, dark = (mats[k] for k in ("ivory", "brass", "rose", "cyan", "magenta", "dark"))
    # Slender biomechanical legs with nested ceramic shells.
    for side in (-1, 1):
        prefix = "L" if side < 0 else "R"
        hip = (side * .62, 0, 2.30)
        knee = (side * .77, -.05, 1.36)
        ankle = (side * .62, -.12, .43)
        objects += [sphere(f"MIR_{prefix}_HIP", hip, (.27, .27, .27), brass)]
        objects += [beam(f"MIR_{prefix}_THIGH", hip, knee, .18, dark)]
        objects += [sphere(f"MIR_{prefix}_THIGH_SHELL", (side * .70, -.01, 1.84), (.32, .28, .58), ivory)]
        objects[-1].rotation_euler[1] = side * .12
        objects += [torus(f"MIR_{prefix}_KNEE_HALO", knee, .29, .045, cyan, rotation=(math.pi / 2, 0, 0))]
        objects += [sphere(f"MIR_{prefix}_KNEE", knee, (.19, .19, .19), rose)]
        objects += [beam(f"MIR_{prefix}_SHIN", knee, ankle, .15, brass)]
        objects += [sphere(f"MIR_{prefix}_SHIN_SHELL", (side * .68, -.08, .88), (.25, .23, .50), ivory)]
        objects += [box(f"MIR_{prefix}_FOOT", (side * .61, -.28, .15), (.48, .74, .22), dark, bevel=.11)]
        objects += [sphere(f"MIR_{prefix}_TOE_PEARL", (side * .61, -.61, .18), (.18, .24, .12), cyan)]

    # Pelvis, living core, rib cage, head and petal crown.
    objects += [sphere("MIR_PELVIS", (0, 0, 2.48), (.93, .58, .48), ivory, segments=48, rings=30)]
    objects += [torus("MIR_PELVIS_RING", (0, -.08, 2.49), .70, .065, brass, rotation=(math.pi / 2, 0, 0))]
    objects += [sphere("MIR_LIVING_CORE", (0, -.24, 3.42), (.55, .40, .68), magenta, segments=48, rings=32)]
    objects += [sphere("MIR_TORSO", (0, .02, 3.57), (1.08, .62, 1.17), ivory, segments=56, rings=36)]
    for side in (-1, 1):
        for i in range(4):
            z = 3.10 + i * .31
            objects += [beam(f"MIR_RIB_{side}_{i}", (side * .12, -.50, z), (side * (.72 + i * .045), -.35, z + .12),
                             .065, brass, vertices=20)]
    objects += [torus("MIR_CHEST_HALO", (0, -.58, 3.62), .54, .055, cyan, rotation=(math.pi / 2, 0, 0))]
    objects += [sphere("MIR_NECK", (0, 0, 4.63), (.30, .28, .35), brass)]
    objects += [sphere("MIR_HEAD", (0, -.05, 4.98), (.48, .40, .58), ivory, segments=48, rings=32)]
    objects += [sphere("MIR_FACE_LIGHT", (0, -.42, 5.00), (.20, .07, .27), cyan, segments=36, rings=20)]
    for i in range(7):
        angle = math.radians(-70 + i * (140 / 6))
        x = math.sin(angle) * .58
        z = 5.19 + math.cos(angle) * .58
        petal = sphere(f"MIR_CROWN_PETAL_{i}", (x, .06, z), (.14, .09, .44), rose, segments=32, rings=20)
        petal.rotation_euler[1] = -angle
        objects.append(petal)

    # Petal shoulders and articulated arms.
    for side in (-1, 1):
        prefix = "L" if side < 0 else "R"
        shoulder = (side * 1.18, 0, 4.05)
        elbow = (side * 1.46, -.02, 3.18)
        wrist = (side * 1.32, -.14, 2.48)
        objects += [sphere(f"MIR_{prefix}_SHOULDER_CORE", shoulder, (.30, .30, .30), brass)]
        for i, offset in enumerate((-.22, 0, .22)):
            petal = sphere(f"MIR_{prefix}_SHOULDER_PETAL_{i}",
                           (side * (1.32 + abs(offset) * .35), offset, 4.16 + abs(offset) * .20),
                           (.23, .48, .56), ivory, segments=40, rings=24)
            petal.rotation_euler[1] = side * (.38 + offset * .22)
            petal.rotation_euler[2] = side * offset
            objects.append(petal)
        objects += [beam(f"MIR_{prefix}_UPPER_ARM", shoulder, elbow, .17, brass)]
        objects += [sphere(f"MIR_{prefix}_ELBOW", elbow, (.23, .23, .23), rose)]
        objects += [torus(f"MIR_{prefix}_ELBOW_HALO", elbow, .29, .035, magenta, rotation=(math.pi / 2, 0, 0))]
        objects += [beam(f"MIR_{prefix}_FOREARM", elbow, wrist, .15, dark)]
        shell = sphere(f"MIR_{prefix}_FOREARM_SHELL", (side * 1.40, -.08, 2.83), (.24, .29, .48), ivory)
        shell.rotation_euler[1] = side * .10
        objects.append(shell)
        objects += [sphere(f"MIR_{prefix}_HAND", wrist, (.23, .20, .20), brass)]

    # Sanctuary spear and petal shield.
    objects += [beam("MIR_SPEAR_SHAFT", (1.58, -.30, .45), (1.58, -.30, 4.25), .075, brass, vertices=24)]
    objects += [cone("MIR_SPEAR_TIP", (1.58, -.30, 4.57), .20, .015, .70, ivory, vertices=32)]
    objects += [sphere("MIR_SPEAR_CORE", (1.58, -.34, 3.75), (.18, .13, .25), magenta)]
    for i in range(5):
        angle = i * math.tau / 5
        petal = sphere(f"MIR_SPEAR_PETAL_{i}", (1.58 + math.cos(angle) * .30, -.30, 3.75 + math.sin(angle) * .30),
                       (.10, .055, .28), cyan if i % 2 else rose, segments=28, rings=18)
        petal.rotation_euler[1] = angle
        objects.append(petal)
    objects += [torus("MIR_SHIELD_OUTER", (-1.77, -.52, 2.96), .73, .075, brass, rotation=(math.pi / 2, 0, 0), major_segments=64)]
    objects += [torus("MIR_SHIELD_INNER", (-1.77, -.58, 2.96), .48, .045, cyan, rotation=(math.pi / 2, 0, 0))]
    objects += [sphere("MIR_SHIELD_CORE", (-1.77, -.63, 2.96), (.18, .08, .18), magenta)]
    for i in range(8):
        angle = i * math.tau / 8
        x = -1.77 + math.cos(angle) * .57
        z = 2.96 + math.sin(angle) * .57
        petal = sphere(f"MIR_SHIELD_PETAL_{i}", (x, -.55, z), (.12, .06, .32), ivory, segments=28, rings=18)
        petal.rotation_euler[1] = angle
        objects.append(petal)

    # Flowing energy filaments make the faction's organic motion language visible.
    for side in (-1, 1):
        for i in range(3):
            y = .34 + i * .08
            objects.append(cable(f"MIR_FILAMENT_{side}_{i}", [
                (side * .45, y, 4.18 - i * .09),
                (side * (.88 + i * .08), y + .28, 3.58 - i * .12),
                (side * (.74 + i * .10), y + .48, 2.92 - i * .16),
            ], .025 + i * .005, cyan if i % 2 == 0 else magenta))
    for i in range(10):
        angle = i * math.tau / 10
        objects += [sphere(f"MIR_ORBITAL_PEARL_{i}", (math.cos(angle) * 1.14, .20, 3.58 + math.sin(angle) * 1.02),
                           (.055, .055, .055), cyan if i % 2 else magenta, segments=20, rings=12)]


def apply_modifiers_and_convert(objects: list[bpy.types.Object]) -> list[bpy.types.Object]:
    result: list[bpy.types.Object] = []
    for obj in list(objects):
        if obj.type == "CURVE":
            bpy.context.view_layer.objects.active = obj
            obj.select_set(True)
            bpy.ops.object.convert(target="MESH")
            obj.select_set(False)
        if obj.type != "MESH":
            continue
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
        for modifier in list(obj.modifiers):
            try:
                bpy.ops.object.modifier_apply(modifier=modifier.name)
            except RuntimeError:
                pass
        obj.select_set(False)
        result.append(obj)
    return result


def select_only(objects: list[bpy.types.Object]) -> None:
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.hide_set(False)
        obj.hide_render = False
        obj.select_set(True)
    if objects:
        bpy.context.view_layer.objects.active = objects[0]


def export_glb(path: Path, objects: list[bpy.types.Object]) -> None:
    select_only(objects)
    bpy.ops.export_scene.gltf(
        filepath=str(path), export_format="GLB", use_selection=True, export_apply=True,
        export_materials="EXPORT", export_yup=True, export_cameras=False, export_lights=False,
    )


def duplicate_lod(objects: list[bpy.types.Object], ratio: float, suffix: str) -> list[bpy.types.Object]:
    duplicates = []
    for source in objects:
        duplicate = source.copy()
        duplicate.data = source.data.copy()
        duplicate.name = f"{source.name}_{suffix.upper()}"
        bpy.context.collection.objects.link(duplicate)
        if ratio < .999 and len(duplicate.data.polygons) > 80:
            modifier = duplicate.modifiers.new(f"AXM_{suffix}_Decimate", "DECIMATE")
            modifier.ratio = ratio
            modifier.use_collapse_triangulate = True
            bpy.context.view_layer.objects.active = duplicate
            duplicate.select_set(True)
            try:
                bpy.ops.object.modifier_apply(modifier=modifier.name)
            finally:
                duplicate.select_set(False)
        duplicates.append(duplicate)
    return duplicates


def remove_objects(objects: list[bpy.types.Object]) -> None:
    for obj in objects:
        bpy.data.objects.remove(obj, do_unlink=True)


def mesh_stats(objects: list[bpy.types.Object]) -> dict[str, int]:
    vertices = sum(len(obj.data.vertices) for obj in objects if obj.type == "MESH")
    triangles = 0
    for obj in objects:
        if obj.type != "MESH":
            continue
        obj.data.calc_loop_triangles()
        triangles += len(obj.data.loop_triangles)
    return {"objects": len(objects), "vertices": vertices, "triangles": triangles}


def collisions(asset_id: str, mats: dict[str, bpy.types.Material]) -> list[bpy.types.Object]:
    collision = mats["collision"]
    if asset_id.startswith("axiom"):
        return [
            box("UCX_AXIOM_TORSO", (0, 0, 3.55), (2.45, 1.18, 1.75), collision, bevel=0),
            box("UCX_AXIOM_PELVIS", (0, 0, 2.55), (1.95, 1.05, .75), collision, bevel=0),
            box("UCX_AXIOM_LEFT_LEG", (-.92, 0, 1.25), (.72, .74, 2.35), collision, bevel=0),
            box("UCX_AXIOM_RIGHT_LEG", (.92, 0, 1.25), (.72, .74, 2.35), collision, bevel=0),
            box("UCX_AXIOM_WEAPON", (2.04, -.95, 2.82), (.78, 2.65, .62), collision, bevel=0),
        ]
    return [
        box("UCX_MIR_TORSO", (0, 0, 3.55), (2.30, 1.25, 2.20), collision, bevel=0),
        box("UCX_MIR_PELVIS", (0, 0, 2.48), (1.75, 1.12, .75), collision, bevel=0),
        box("UCX_MIR_LEFT_LEG", (-.68, 0, 1.20), (.58, .62, 2.25), collision, bevel=0),
        box("UCX_MIR_RIGHT_LEG", (.68, 0, 1.20), (.58, .62, 2.25), collision, bevel=0),
        box("UCX_MIR_SPEAR", (1.58, -.30, 2.50), (.40, .40, 4.50), collision, bevel=0),
    ]


def setup_render(resolution: int, transparent: bool) -> tuple[bpy.types.Object, bpy.types.Object]:
    scene = bpy.context.scene
    # Blender 5.2 exposes Eevee under BLENDER_EEVEE; older 4.x builds used
    # BLENDER_EEVEE_NEXT. Prefer the runtime's actual enum, not a version guess.
    try:
        scene.render.engine = "BLENDER_EEVEE"
    except TypeError:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = resolution
    scene.render.resolution_y = resolution
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = transparent
    scene.render.image_settings.color_depth = "8"
    scene.render.image_settings.compression = 32
    scene.world.color = (.004, .007, .013)
    world = scene.world
    world.use_nodes = True
    background = world.node_tree.nodes.get("Background")
    background.inputs["Color"].default_value = (.004, .008, .018, 1)
    background.inputs["Strength"].default_value = .22

    ground_mat = material("ENV_Ground", (.012, .019, .030, 1), metallic=.22, roughness=.30)
    bpy.ops.mesh.primitive_plane_add(size=30, location=(0, 0, -.01))
    ground = bpy.context.object
    ground.name = "RENDER_GROUND"
    assign(ground, ground_mat)

    bpy.ops.object.camera_add(location=(9, -11, 6.8))
    camera = bpy.context.object
    camera.name = "RENDER_CAMERA"
    camera.data.lens = 62
    scene.camera = camera

    light_specs = [
        ("KEY", (5.5, -5.5, 8.5), (0.62, 0.82, 1.0), 1550, 5.5),
        ("RIM", (-5.5, 1.5, 6.5), (0.1, 0.72, 1.0), 1250, 4.0),
        ("FILL", (2.5, 4.5, 4.0), (1.0, 0.40, 0.16), 900, 3.5),
        ("TOP", (0, 0, 10.5), (0.68, 0.76, 1.0), 1000, 3.0),
    ]
    for name, location, color, energy, size in light_specs:
        data = bpy.data.lights.new(name, "AREA")
        data.energy = energy
        data.color = color
        data.shape = "DISK"
        data.size = size
        obj = bpy.data.objects.new(name, data)
        bpy.context.collection.objects.link(obj)
        obj.location = location
        obj.rotation_euler = (0, 0, 0)
        obj.rotation_euler = ((Vector((0, 0, 3.0)) - obj.location).to_track_quat("-Z", "Y").to_euler())
    return camera, ground


def point_camera(camera: bpy.types.Object, degrees: float, *, radius: float = 10.2, height: float = 5.2) -> None:
    angle = math.radians(degrees)
    camera.location = (math.sin(angle) * radius, -math.cos(angle) * radius, height)
    target = Vector((0, 0, 2.65))
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    args = parse_args()
    request_path = Path(args.request).resolve()
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    request = json.loads(request_path.read_text(encoding="utf-8"))
    asset_id = request["asset_id"]
    rng = random.Random(int(request.get("seed", 0)))
    clear_scene()

    mats = {
        "gunmetal": material("AX_Gunmetal", (.025, .038, .050, 1), metallic=.95, roughness=.31),
        "pale": material("AX_PaleCeramicArmor", (.34, .39, .41, 1), metallic=.66, roughness=.28),
        "cyan": material("AX_ElectricCyan", (.006, .12, .18, 1), metallic=.20, roughness=.20,
                         emission=(.00, .48, .72, 1), emission_strength=3.2),
        "amber": material("AX_SignalAmber", (.22, .055, .004, 1), metallic=.20, roughness=.25,
                          emission=(.72, .11, .008, 1), emission_strength=2.5),
        "ivory": material("MIR_IvoryCeramic", (.86, .79, .66, 1), metallic=.08, roughness=.20),
        "brass": material("MIR_Brass", (.42, .21, .055, 1), metallic=.97, roughness=.21),
        "rose": material("MIR_RoseGold", (.54, .19, .17, 1), metallic=.90, roughness=.24),
        "magenta": material("MIR_ResonanceMagenta", (.30, .008, .19, 1), metallic=.12, roughness=.16,
                            emission=(1.0, .015, .46, 1), emission_strength=5.5),
        "dark": material("AXM_DarkMechanism", (.018, .024, .032, 1), metallic=.76, roughness=.36),
        "collision": material("AXM_CollisionDebug", (.80, .02, .02, .35), metallic=0, roughness=1),
    }
    objects: list[bpy.types.Object] = []
    if asset_id == "axiom-bastion-frame":
        add_axiom_hero_v3(objects, mats, rng)
    elif asset_id == "mir-sanctuary-keeper":
        add_mir_details(objects, mats, rng)
    else:
        raise ValueError(f"unsupported asset_id: {asset_id}")
    objects = apply_modifiers_and_convert(objects)

    exports: dict[str, dict] = {}
    lod0_path = output / f"{asset_id}_LOD0.glb"
    export_glb(lod0_path, objects)
    exports["lod0"] = {"path": lod0_path.name, **mesh_stats(objects), "sha256": sha(lod0_path), "bytes": lod0_path.stat().st_size}

    for lod_name, ratio in (("lod1", .48), ("lod2", .18)):
        duplicated = duplicate_lod(objects, ratio, lod_name)
        path = output / f"{asset_id}_{lod_name.upper()}.glb"
        export_glb(path, duplicated)
        exports[lod_name] = {"path": path.name, **mesh_stats(duplicated), "sha256": sha(path), "bytes": path.stat().st_size}
        remove_objects(duplicated)

    collision_objects = collisions(asset_id, mats)
    collision_path = output / f"{asset_id}_COLLISION.glb"
    export_glb(collision_path, collision_objects)
    exports["collision"] = {"path": collision_path.name, **mesh_stats(collision_objects), "sha256": sha(collision_path), "bytes": collision_path.stat().st_size}
    for obj in collision_objects:
        obj.hide_render = True
        obj.hide_set(True)

    camera, ground = setup_render(request["render"]["resolution"], request["render"]["transparent"])
    render_proofs = []
    for angle in request["render"]["angles_degrees"]:
        point_camera(camera, float(angle))
        path = output / f"{asset_id}_view_{int(angle):03d}.png"
        bpy.context.scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        render_proofs.append({"angle_degrees": angle, "path": path.name, "sha256": sha(path), "bytes": path.stat().st_size})

    blend_path = output / f"{asset_id}.blend"
    select_only(objects)
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))

    manifest = {
        "schema": "axm.3d-asset-manifest/v0.1",
        "truth_status": "GEOMETRY_EXPORTED_AND_MULTI_ANGLE_RENDERED",
        "asset_id": asset_id,
        "faction": request["faction"],
        "archetype": request["archetype"],
        "meters_per_unit": 1.0,
        "source": {"path": blend_path.name, "sha256": sha(blend_path), "bytes": blend_path.stat().st_size},
        "exports": exports,
        "materials": sorted({slot.material.name for obj in objects for slot in obj.material_slots if slot.material}),
        "render_proofs": render_proofs,
        "quality_claim": "Rendered vertical-slice evidence; final AAA acceptance remains a visual review decision.",
    }
    (output / "asset-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"status": "AXM_3D_FORGE_COMPLETE", "asset_id": asset_id, "output": str(output), "exports": exports}, indent=2))


if __name__ == "__main__":
    main()
