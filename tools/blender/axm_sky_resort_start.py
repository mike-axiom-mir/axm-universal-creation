"""Forge the Inverted Water Sanctuary opening-world miniature.

The supplied images are visual-direction references only.  This deterministic
builder retains editable construction parts, an addressable rigid skeleton,
loopable art-directed water geometry, portable GLBs, LODs and collision.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import random
import sys

import bpy
from mathutils import Vector

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import axm_blender_forge as geo
from axm_hero_motion import clean_triangles, rig
from axm_oops_character import reset_pose
from axm_hero_surfaces import surface
from axm_salvage_surfaces import pbr_material, solid


ASSET_ID = "inverted-water-sanctuary-start-v1"
SCHEMA = "axm.uc.inverted-water-sanctuary/v1"
FPS = 30
CLIPS = [
    ("Sanctuary_Idle", 8.0, True),
    ("Watershield_Pulse", 5.0, True),
    ("Arrival_Awakening", 4.0, False),
]
WATER_PROFILES = ("prop", "world-study")
FLOW_PACKET_COUNT = 6
WATER_ASCENT_TURNS = {"A": 1.68, "B": 1.50, "C": 1.86}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def transparent_material(name: str, color: str, alpha: float, emission_strength: float = 0.0,
                         transmission: float = 0.0, roughness: float = .18) -> bpy.types.Material:
    """Create a portable alpha material with a richer Blender preview response."""
    mat = solid(name, color, 0.0, roughness, emission_strength)
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    rgb = mat.diffuse_color[:3]
    mat.diffuse_color = (*rgb, alpha)
    bsdf.inputs["Alpha"].default_value = alpha
    transmission_socket = bsdf.inputs.get("Transmission Weight") or bsdf.inputs.get("Transmission")
    if transmission_socket:
        transmission_socket.default_value = transmission
    ior = bsdf.inputs.get("IOR")
    if ior:
        ior.default_value = 1.333
    coat = bsdf.inputs.get("Coat Weight")
    if coat:
        coat.default_value = .28
    try:
        mat.surface_render_method = "BLENDED"
    except Exception:
        try:
            mat.blend_method = "BLEND"
        except Exception:
            pass
    mat.use_transparency_overlap = False
    return mat


def opaque_water_material(name: str, color: str, emission_strength: float = 0.0,
                          roughness: float = .10) -> bpy.types.Material:
    """Glossy portable water for self-overlapping animated sheets.

    Alpha-blended helical sheets reveal triangle ordering in common real-time
    renderers.  The primary liquid body therefore stays opaque and glossy;
    transparency is reserved for non-self-overlapping lagoon and ocean planes.
    """
    mat = solid(name, color, .02, roughness, emission_strength)
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    coat = bsdf.inputs.get("Coat Weight")
    if coat:
        coat.default_value = .42
    coat_roughness = bsdf.inputs.get("Coat Roughness")
    if coat_roughness:
        coat_roughness.default_value = .045
    ior = bsdf.inputs.get("IOR")
    if ior:
        ior.default_value = 1.333
    return mat


def world_water_material(name: str, color: str, alpha: float, transmission: float,
                         emission_strength: float, roughness: float) -> bpy.types.Material:
    """Layered translucent water that remains portable through glTF.

    Moderate alpha and transmission reveal foam and flow tracers without making
    stacked ribbons disappear.  Back-face transparency is disabled because the
    solidified sheets already contain authored inner surfaces; rendering another
    implicit transparent back layer only amplifies sorting artifacts.
    """
    mat = transparent_material(name, color, alpha, emission_strength,
                               transmission, roughness)
    mat.show_transparent_back = False
    mat.use_transparency_overlap = False
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    coat = bsdf.inputs.get("Coat Weight")
    if coat:
        coat.default_value = .36
    coat_roughness = bsdf.inputs.get("Coat Roughness")
    if coat_roughness:
        coat_roughness.default_value = .035
    return mat


class DioramaAuthor:
    """Small adapter matching UC's retained rigid-rig compiler contract."""

    def __init__(self, output: Path, water_profile: str = "prop"):
        self.output = output
        self.water_profile = water_profile
        self.parts: list[bpy.types.Object] = []
        self.bones: dict[str, tuple[tuple[float, float, float], tuple[float, float, float], str | None]] = {}
        self.current = "Root"
        textures = output / "textures"
        if water_profile == "world-study":
            rising_water = world_water_material(
                "Sanctuary_Rising_Water_Translucent", "#0b83b4", .58, .48, .025, .055)
            light_water = world_water_material(
                "Sanctuary_Water_Light_Translucent", "#4cddf5", .40, .68, .12, .045)
            flow_glint = world_water_material(
                "Sanctuary_Upcurrent_Glint", "#b8f8ff", .66, .22, .72, .075)
        else:
            rising_water = opaque_water_material("Sanctuary_Rising_Water", "#168fc0", .06, .09)
            light_water = opaque_water_material("Sanctuary_Water_Light", "#52dfff", .28, .12)
            flow_glint = light_water
        self.mat = {
            "obsidian": surface(textures, "Sanctuary_Obsidian_Plinth", "#111922", "steel", 512),
            "basalt": pbr_material(textures, "Sanctuary_Wet_Basalt", "#354750", "stone", 512),
            "rock": pbr_material(textures, "Sanctuary_Volcanic_Rock", "#59645f", "stone", 512),
            "sand": pbr_material(textures, "Sanctuary_Beach_Stone", "#d9c89d", "soil", 512),
            "green": pbr_material(textures, "Sanctuary_Living_Green", "#3e7b4d", "cloth", 512),
            "green_light": pbr_material(textures, "Sanctuary_Young_Green", "#72a85a", "cloth", 512),
            "ivory": surface(textures, "Sanctuary_Ivory", "#d9e4dc", "metal", 512),
            "gold": surface(textures, "Sanctuary_Sun_Gold", "#b8843c", "steel", 512),
            "wood": pbr_material(textures, "Sanctuary_Palm_Wood", "#5b3c24", "wood", 512),
            "deep_ocean": transparent_material("Sanctuary_Deep_Ocean", "#082c4a", .82, .05, .18, .13),
            "lagoon": transparent_material("Sanctuary_Lagoon", "#20b9c7", .74, .18, .42, .08),
            "water": rising_water,
            "water_light": light_water,
            "flow_glint": flow_glint,
            "foam": opaque_water_material("Sanctuary_Foam", "#d9fbff", .34, .31),
            "cloud": transparent_material("Sanctuary_Cloud", "#dbeaf0", .15, 0, 0, 1.0),
            "crystal": transparent_material("Sanctuary_Crystal", "#4bdfff", .72, 2.2, .30, .08),
            "warm": solid("Sanctuary_Warm_Window", "#ffd38a", .0, .25, 3.5),
            "dark": solid("Sanctuary_Deep_Recess", "#071018", .2, .24, 0),
            "collision": solid("Sanctuary_Collision_Debug", "#ff00aa", 0, .9, 0),
        }

    def bone(self, name, head, tail, parent=None):
        self.bones[name] = (tuple(head), tuple(tail), parent)

    def bind(self, obj, bone=None, category="structure"):
        obj["axm_bone"] = bone or self.current
        obj["axm_category"] = category
        self.parts.append(obj)
        return obj

    def box(self, name, center, dimensions, material="basalt", *, bevel=.04,
            rotation=(0, 0, 0), bone=None, category="structure"):
        return self.bind(geo.box(name, center, dimensions, self.mat[material], rotation=rotation,
                                 bevel=bevel, segments=3), bone, category)

    def ball(self, name, center, scale, material="basalt", *, segments=24, rings=16,
             bone=None, category="structure"):
        return self.bind(geo.sphere(name, center, scale, self.mat[material],
                                    segments=segments, rings=rings), bone, category)

    def cyl(self, name, center, radius, depth, material="basalt", *, axis=(0, 0, 1),
            vertices=24, bone=None, category="structure", bevel=.018):
        obj = geo.cylinder(name, center, radius, depth, self.mat[material], vertices=vertices,
                           bevel=min(bevel, radius * .20))
        obj.rotation_mode = "QUATERNION"
        obj.rotation_quaternion = Vector(axis).to_track_quat("Z", "Y")
        return self.bind(obj, bone, category)

    def cone(self, name, center, radius1, radius2, depth, material="basalt", *, vertices=24,
             bone=None, category="structure"):
        return self.bind(geo.cone(name, center, radius1, radius2, depth, self.mat[material],
                                  vertices=vertices, bevel=min(.025, max(radius1, radius2) * .07)),
                         bone, category)

    def ring(self, name, center, major, minor, material="gold", *, normal=(0, 0, 1),
             major_segments=64, minor_segments=10, bone=None, category="structure"):
        obj = geo.torus(name, center, major, minor, self.mat[material],
                        major_segments=major_segments, minor_segments=minor_segments)
        obj.rotation_mode = "QUATERNION"
        obj.rotation_quaternion = Vector(normal).to_track_quat("Z", "Y")
        return self.bind(obj, bone, category)

    def beam(self, name, start, end, radius, material="basalt", *, vertices=16,
             bone=None, category="structure"):
        return self.bind(geo.beam(name, start, end, radius, self.mat[material], vertices=vertices),
                         bone, category)

    def cable(self, name, points, radius, material="foam", *, bone=None, category="structure"):
        return self.bind(geo.cable(name, [tuple(point) for point in points], radius,
                                   self.mat[material]), bone, category)

    def mesh(self, name, vertices, faces, material, *, bone=None, category="structure",
             solidify=0.0, smooth=True):
        mesh = bpy.data.meshes.new(name + "_Mesh")
        mesh.from_pydata([tuple(value) for value in vertices], [], faces)
        mesh.update()
        obj = bpy.data.objects.new(name, mesh)
        bpy.context.collection.objects.link(obj)
        obj.data.materials.append(self.mat[material])
        if solidify:
            modifier = obj.modifiers.new("Authored sheet thickness", "SOLIDIFY")
            modifier.thickness = solidify
            modifier.offset = 0
        if smooth:
            for polygon in mesh.polygons:
                polygon.use_smooth = True
        return self.bind(obj, bone, category)


def polar(radius: float, angle: float, z: float) -> tuple[float, float, float]:
    return (radius * math.cos(angle), radius * math.sin(angle), z)


def build_bones(h: DioramaAuthor) -> None:
    h.bone("Root", (0, 0, 0), (0, 0, .4))
    h.bone("LowerIsland", (0, 0, .45), (0, 0, 1.05), "Root")
    h.bone("VolcanoCore", (0, 0, 2.20), (0, 0, 2.75), "LowerIsland")
    for suffix in ("A", "B", "C"):
        h.bone(f"WaterSpiral.{suffix}", (0, 0, 3.10), (0, 0, 3.62), "Root")
        if h.water_profile == "world-study":
            for packet_index in range(FLOW_PACKET_COUNT):
                h.bone(f"WaterFlow.{suffix}.{packet_index}", (0, 0, 3.10), (0, 0, 3.62),
                       f"WaterSpiral.{suffix}")
    h.bone("UpperIsland", (0, 0, 7.15), (0, 0, 7.70), "Root")
    for suffix in ("A", "B", "C"):
        h.bone(f"WaterShield.{suffix}", (0, 0, 8.05), (0, 0, 8.55), "UpperIsland")
    h.bone("Cascades", (0, 0, 7.55), (0, 0, 8.00), "UpperIsland")
    h.bone("Sanctuary", (0, 0, 8.18), (0, 0, 8.80), "UpperIsland")
    h.bone("ArrivalGate", (0, -4.25, 8.02), (0, -4.25, 8.72), "UpperIsland")
    h.bone("Socket_Bus_Arrival", (0, -5.25, 8.04), (0, -5.25, 8.55), "ArrivalGate")
    h.bone("CloudBank", (0, 0, 6.00), (0, 0, 6.50), "Root")


def irregular_island(h: DioramaAuthor, name: str, radius: float, top_z: float, mid_z: float,
                     bottom_z: float, material: str, seed: int, bone: str, category: str,
                     segments: int = 64):
    rng = random.Random(seed)
    radii = [radius * (1 + rng.uniform(-.10, .10) + .035 * math.sin(i * .73)) for i in range(segments)]
    vertices = [(0, 0, top_z)]
    for i, value in enumerate(radii):
        angle = math.tau * i / segments
        vertices.append((value * math.cos(angle), value * math.sin(angle), top_z + .04 * math.sin(angle * 3)))
    for i, value in enumerate(radii):
        angle = math.tau * i / segments
        vertices.append((value * .91 * math.cos(angle), value * .91 * math.sin(angle), mid_z + .10 * math.sin(angle * 5)))
    for i, value in enumerate(radii):
        angle = math.tau * i / segments
        taper = .34 + .13 * (1 + math.sin(angle * 4 + .7))
        vertices.append((value * taper * math.cos(angle), value * taper * math.sin(angle), bottom_z + .10 * math.cos(angle * 3)))
    vertices.append((0, 0, bottom_z - .28))
    faces = []
    for i in range(segments):
        n = (i + 1) % segments
        faces.append((0, 1 + i, 1 + n))
        faces.append((1 + i, 1 + segments + i, 1 + segments + n, 1 + n))
        faces.append((1 + segments + i, 1 + 2 * segments + i, 1 + 2 * segments + n, 1 + segments + n))
        faces.append((1 + 2 * segments + i, len(vertices) - 1, 1 + 2 * segments + n))
    return h.mesh(name, vertices, faces, material, bone=bone, category=category, smooth=False)


def helical_ribbon(h: DioramaAuthor, name: str, phase: float, width: float, turns: float,
                   material: str, bone: str, category: str, segments: int = 220):
    vertices = []
    centerline = []
    for index in range(segments + 1):
        t = index / segments
        angle = phase + math.tau * turns * t
        radius = .72 + 1.55 * math.sin(math.pi * t) ** 1.10 + .16 * math.sin(angle * 2.0)
        z = 3.02 + 4.12 * t + .11 * math.sin(angle * 1.5)
        centerline.append(Vector(polar(radius, angle, z)))
        half = width * (.58 + .42 * math.sin(math.pi * t)) / 2
        vertices.append(polar(max(.24, radius - half), angle, z - .06 * math.cos(angle)))
        vertices.append(polar(radius + half, angle, z + .06 * math.cos(angle)))
    faces = [(2 * i, 2 * i + 1, 2 * i + 3, 2 * i + 2) for i in range(segments)]
    obj = h.mesh(name, vertices, faces, material, bone=bone, category=category, solidify=.035)
    return obj, centerline


def shield_ribbon(h: DioramaAuthor, name: str, phase: float, base_radius: float, width: float,
                  material: str, bone: str, category: str, segments: int = 256):
    vertices = []
    crest = []
    for index in range(segments):
        angle = math.tau * index / segments
        wave = .24 * math.sin(angle * 5 + phase) + .10 * math.sin(angle * 11 - phase)
        z = 8.03 + .26 * math.sin(angle * 3 + phase) + .05 * math.sin(angle * 13)
        inner = base_radius - width / 2 + wave * .30
        outer = base_radius + width / 2 + wave
        vertices.append(polar(inner, angle, z - .16 - .06 * math.sin(angle * 7)))
        vertices.append(polar(outer, angle, z + .18 + .08 * math.sin(angle * 4 + phase)))
        crest.append(Vector(polar(outer, angle, z + .20)))
    faces = []
    for i in range(segments):
        n = (i + 1) % segments
        faces.append((2 * i, 2 * i + 1, 2 * n + 1, 2 * n))
    obj = h.mesh(name, vertices, faces, material, bone=bone, category=category, solidify=.045)
    crest.append(crest[0])
    return obj, crest


def palm(h: DioramaAuthor, prefix: str, center: tuple[float, float, float], scale: float,
         bone: str, angle: float, category="vegetation") -> None:
    base = Vector(center)
    lean = Vector((math.cos(angle) * .16 * scale, math.sin(angle) * .16 * scale, .58 * scale))
    p1 = base + lean
    p2 = p1 + Vector((math.cos(angle + .25) * .11 * scale,
                      math.sin(angle + .25) * .11 * scale, .54 * scale))
    crown = p2 + Vector((math.cos(angle + .45) * .08 * scale,
                         math.sin(angle + .45) * .08 * scale, .43 * scale))
    h.beam(prefix + " trunk lower", base, p1, .070 * scale, "wood", vertices=12,
           bone=bone, category=category)
    h.beam(prefix + " trunk middle", p1, p2, .058 * scale, "wood", vertices=12,
           bone=bone, category=category)
    h.beam(prefix + " trunk crown", p2, crown, .047 * scale, "wood", vertices=12,
           bone=bone, category=category)
    h.ball(prefix + " crown heart", crown, (.12 * scale,) * 3, "green", segments=16, rings=10,
           bone=bone, category=category)
    for leaf_index in range(8):
        leaf_angle = angle + leaf_index * math.tau / 8
        mid = crown + Vector((math.cos(leaf_angle) * .35 * scale,
                              math.sin(leaf_angle) * .35 * scale, .07 * scale))
        tip = crown + Vector((math.cos(leaf_angle) * .72 * scale,
                              math.sin(leaf_angle) * .72 * scale, -.13 * scale))
        h.cable(f"{prefix} frond {leaf_index:02d}", [crown, mid, tip], .036 * scale,
                "green_light" if leaf_index % 2 else "green", bone=bone, category=category)
        for side in (-1, 1):
            tangent = Vector((-math.sin(leaf_angle), math.cos(leaf_angle), 0))
            side_tip = mid.lerp(tip, .50) + tangent * side * .15 * scale
            h.cable(f"{prefix} leaflet {leaf_index:02d} {side:+d}", [mid, side_tip],
                    .018 * scale, "green", bone=bone, category=category)
    for coconut_index in range(3):
        a = angle + coconut_index * math.tau / 3
        point = crown + Vector((math.cos(a) * .10 * scale, math.sin(a) * .10 * scale, -.10 * scale))
        h.ball(f"{prefix} seed {coconut_index:02d}", point, (.050 * scale,) * 3, "wood",
               segments=12, rings=8, bone=bone, category=category)


def portal_ruin(h: DioramaAuthor, prefix: str, center: Vector, scale: float, angle: float,
                bone: str, intact: float = 1.0) -> None:
    tangent = Vector((-math.sin(angle), math.cos(angle), 0))
    up = Vector((0, 0, 1))
    for side in (-1, 1):
        foot = center + tangent * side * .30 * scale
        height = scale * (1.05 if side > 0 else .92 + .10 * intact)
        h.cyl(f"{prefix} pillar {side:+d}", foot + up * height / 2, .095 * scale, height,
              "ivory", vertices=16, bone=bone, category="ruins", bevel=.012)
        h.ring(f"{prefix} pillar collar {side:+d}", foot + up * height * .78, .13 * scale,
               .026 * scale, "gold", bone=bone, category="ruins", major_segments=20, minor_segments=6)
    blocks = max(3, round(7 * intact))
    for index in range(blocks):
        a = math.pi * index / 6
        point = center + tangent * (math.cos(a) * .30 * scale) + up * (.82 + math.sin(a) * .30) * scale
        h.box(f"{prefix} arch stone {index:02d}", point, (.18 * scale, .16 * scale, .18 * scale),
              "ivory", bevel=.025 * scale, rotation=(0, 0, angle), bone=bone, category="ruins")


def pavilion(h: DioramaAuthor, prefix: str, center: Vector, scale: float, bone: str,
             angle: float) -> None:
    h.cyl(prefix + " terrace", center + Vector((0, 0, .04 * scale)), .42 * scale,
          .08 * scale, "sand", vertices=32, bone=bone, category="resort_architecture")
    for index in range(6):
        a = angle + index * math.tau / 6
        foot = center + Vector((math.cos(a) * .29 * scale, math.sin(a) * .29 * scale, .10 * scale))
        h.cyl(f"{prefix} column {index:02d}", foot + Vector((0, 0, .28 * scale)),
              .032 * scale, .56 * scale, "ivory", vertices=12, bone=bone,
              category="resort_architecture", bevel=.006)
        h.ball(f"{prefix} lamp {index:02d}", foot + Vector((0, 0, .48 * scale)),
               (.035 * scale,) * 3, "warm", segments=10, rings=6, bone=bone,
               category="resort_light")
    h.cone(prefix + " roof lower", center + Vector((0, 0, .64 * scale)), .52 * scale,
           .16 * scale, .28 * scale, "ivory", vertices=32, bone=bone,
           category="resort_architecture")
    h.cone(prefix + " roof crown", center + Vector((0, 0, .89 * scale)), .17 * scale,
           0, .35 * scale, "gold", vertices=24, bone=bone, category="resort_architecture")


def build_display_and_lower_island(h: DioramaAuthor) -> None:
    h.current = "Root"
    h.cyl("Obsidian display plinth", (0, 0, -.06), 5.55, .32, "obsidian", vertices=96,
          category="display_plinth", bevel=.06)
    h.ring("Display plinth gold inlay", (0, 0, .09), 5.13, .035, "gold",
           major_segments=128, minor_segments=10, category="display_plinth")
    h.cyl("Miniature deep-ocean plane", (0, 0, .17), 5.05, .12, "deep_ocean", vertices=128,
          category="ocean", bevel=.02)
    for index in range(72):
        angle = index * math.tau / 72
        radius = 4.05 + .58 * math.sin(angle * 3 + .2) + .22 * math.sin(angle * 7)
        start = Vector(polar(radius - .45, angle, .25))
        end = Vector(polar(radius + .20, angle + .08, .26 + .035 * math.sin(angle * 4)))
        h.cable(f"Ocean current trace {index:03d}", [start, start.lerp(end, .55) + Vector((0, 0, .025)), end],
                .012 if index % 3 else .019, "water_light", category="ocean_detail")

    h.current = "LowerIsland"
    irregular_island(h, "Lower island beach shelf", 3.65, .47, .27, .12, "sand", 7801,
                     "LowerIsland", "lower_island", 72)
    irregular_island(h, "Lower island living rock", 3.22, .69, .34, .05, "basalt", 7802,
                     "LowerIsland", "lower_island", 72)
    h.cyl("Lower island lagoon edge", (0, 0, .54), 3.35, .06, "lagoon", vertices=96,
          bone="LowerIsland", category="lower_lagoon", bevel=.02)

    h.current = "VolcanoCore"
    # Layered eroded volcano; the top remains an open crater rather than a capped cone.
    for index, (radius, depth, z) in enumerate(((2.35, 1.02, 1.08), (1.92, .92, 1.66),
                                                (1.43, .86, 2.17), (.98, .72, 2.63))):
        h.cone(f"Volcano eroded mantle {index:02d}", (0, 0, z), radius, radius * .69, depth,
               "rock" if index % 2 else "basalt", vertices=64, bone="VolcanoCore", category="volcano")
    h.ring("Volcano crater rim", (0, 0, 3.02), .69, .17, "basalt", major_segments=80,
           minor_segments=16, bone="VolcanoCore", category="volcano")
    h.cyl("Volcano luminous water well", (0, 0, 2.98), .57, .12, "water_light", vertices=64,
          bone="VolcanoCore", category="water_source", bevel=.02)
    for index in range(36):
        angle = index * math.tau / 36
        radius = 1.05 + .92 * (index % 5) / 5
        z = .72 + .32 * (index % 4)
        h.cone(f"Volcano buttress {index:03d}", polar(radius, angle, z + .24),
               .20 + .05 * (index % 3), .035, .72 + .18 * (index % 4),
               "basalt" if index % 2 else "rock", vertices=12, bone="VolcanoCore", category="volcano_detail")
        if index % 3 == 0:
            h.cable(f"Volcano spring {index:03d}", [Vector(polar(radius * .82, angle, z + .44)),
                    Vector(polar(radius * 1.02, angle + .04, z + .08))], .035,
                    "water_light", bone="VolcanoCore", category="lower_cascade")

    # Shore ruins and intentional broken portals provide history without creating a crossing.
    for index in range(10):
        angle = index * math.tau / 10 + .18
        center = Vector(polar(2.75 + .18 * math.sin(index * 1.7), angle, .70))
        portal_ruin(h, f"Lower ruin portal {index:02d}", center, .52 + .10 * (index % 3), angle,
                    "LowerIsland", .62 if index % 4 == 0 else 1.0)
    for index in range(22):
        angle = index * math.tau / 22 + .10
        radius = 2.15 + .52 * ((index * 7) % 11) / 11
        point = polar(radius, angle, .70)
        palm(h, f"Lower palm {index:02d}", point, .34 + .06 * (index % 4),
             "LowerIsland", angle + .4)
    for index in range(28):
        angle = index * math.tau / 28
        radius = 3.30 + .22 * math.sin(index * 2.1)
        h.cone(f"Lower shore rock {index:02d}", polar(radius, angle, .57 + .10 * (index % 3)),
               .10 + .04 * (index % 3), .018, .32 + .08 * (index % 4), "basalt",
               vertices=10, bone="LowerIsland", category="shore_detail")


def build_water_ascent(h: DioramaAuthor) -> None:
    configs = [
        ("A", 0.0, 1.08, 1.68, "water"),
        ("B", math.tau / 3, .82, 1.50, "water_light"),
        ("C", math.tau * 2 / 3, .60, 1.86, "water"),
    ]
    for suffix, phase, width, turns, material in configs:
        bone = f"WaterSpiral.{suffix}"
        _, points = helical_ribbon(h, f"Reverse water ribbon {suffix}", phase, width, turns,
                                   material, bone, "water_vortex")
        for offset_index, offset in enumerate((-.16, .16)):
            foam_points = []
            for index, point in enumerate(points[::3]):
                angle = phase + math.tau * turns * (index * 3 / 220)
                tangent = Vector((-math.sin(angle), math.cos(angle), .20)).normalized()
                foam_points.append(point + tangent * offset)
            h.cable(f"Reverse water foam rail {suffix} {offset_index:02d}", foam_points,
                    .022 if suffix == "A" else .016, "foam", bone=bone, category="water_foam")
        for droplet_index in range(22):
            t = (droplet_index + .35) / 22
            angle = phase + math.tau * turns * t + (.36 if droplet_index % 2 else -.28)
            radius = .85 + 1.62 * math.sin(math.pi * t) ** 1.12 + .20 * (droplet_index % 3)
            z = 3.0 + 4.14 * t + .16 * math.sin(droplet_index * 1.9)
            scale = .032 + .018 * (droplet_index % 4)
            h.ball(f"Suspended ascent droplet {suffix} {droplet_index:02d}", polar(radius, angle, z),
                   (scale, scale * .72, scale * 1.55), "foam", segments=10, rings=7,
                   bone=bone, category="water_droplet")
        if h.water_profile == "world-study":
            for packet_index in range(FLOW_PACKET_COUNT):
                packet_bone = f"WaterFlow.{suffix}.{packet_index}"
                base_t = (packet_index + .5) / FLOW_PACKET_COUNT
                tracer_points = []
                for bead_index in range(5):
                    sample_t = base_t + (bead_index - 2) * .012
                    angle = phase + math.tau * turns * sample_t
                    radius = (.72 + 1.55 * math.sin(math.pi * sample_t) ** 1.10 +
                              .16 * math.sin(angle * 2.0))
                    z = 3.02 + 4.12 * sample_t + .11 * math.sin(angle * 1.5)
                    point = Vector(polar(radius + .025, angle, z))
                    tracer_points.append(point)
                    if bead_index in (0, 2, 4):
                        bead_scale = .030 + .010 * (bead_index == 2)
                        h.ball(f"Upcurrent tracer {suffix} {packet_index} bead {bead_index}", point,
                               (bead_scale, bead_scale, bead_scale * 1.55), "flow_glint",
                               segments=10, rings=7, bone=packet_bone,
                               category="water_flow_tracer")
                h.cable(f"Upcurrent tracer {suffix} {packet_index} streak", tracer_points,
                        .014 if suffix == "A" else .011, "flow_glint", bone=packet_bone,
                        category="water_flow_tracer")
    # Dense inner core makes the reverse flow read as volume at miniature scale.
    for index in range(8):
        phase = index * math.tau / 8
        points = []
        for step in range(42):
            t = step / 41
            angle = phase + math.tau * (1.25 + .08 * (index % 3)) * t
            radius = .31 + .68 * math.sin(math.pi * t) ** 1.45 + .06 * math.sin(index * 2.2)
            points.append(Vector(polar(radius, angle, 3.04 + 4.05 * t)))
        h.cable(f"Reverse water inner filament {index:02d}", points,
                .018 if index % 4 == 0 else .011, "foam" if index % 4 == 0 else "water_light",
                bone=f"WaterSpiral.{('A', 'B', 'C')[index % 3]}", category="water_filament")


def build_upper_island(h: DioramaAuthor) -> None:
    h.current = "UpperIsland"
    irregular_island(h, "Upper sanctuary underside", 3.76, 7.78, 7.15, 6.46,
                     "basalt", 9101, "UpperIsland", "upper_island", 80)
    irregular_island(h, "Upper sanctuary garden shelf", 3.48, 7.98, 7.76, 7.42,
                     "green", 9102, "UpperIsland", "upper_island", 80)
    h.cyl("Upper sanctuary beach halo", (0, 0, 7.94), 3.58, .12, "sand", vertices=112,
          bone="UpperIsland", category="upper_beach", bevel=.028)
    h.cyl("Upper sanctuary lagoon", (0, 0, 8.05), 2.56, .10, "lagoon", vertices=112,
          bone="UpperIsland", category="upper_lagoon", bevel=.02)
    h.ring("Upper lagoon ivory promenade", (0, 0, 8.11), 2.72, .10, "ivory",
           major_segments=112, minor_segments=12, bone="UpperIsland", category="resort_path")
    h.ring("Upper outer garden path", (0, 0, 8.08), 3.20, .075, "sand",
           major_segments=112, minor_segments=10, bone="UpperIsland", category="resort_path")

    # Jagged hanging geology stays readable from the rear and from below.
    for index in range(42):
        angle = index * math.tau / 42
        radius = 2.35 + .80 * ((index * 11) % 17) / 17
        length = .30 + .68 * ((index * 7) % 13) / 13
        h.cone(f"Upper underside fang {index:03d}", polar(radius, angle, 7.25 - length / 2),
               .13 + .04 * (index % 4), .015, length, "basalt" if index % 2 else "rock",
               vertices=12, bone="UpperIsland", category="underside_geology")
        if index % 4 == 0:
            h.ball(f"Upper underside crystal {index:03d}", polar(radius, angle, 7.03 - length),
                   (.055, .055, .16), "crystal", segments=12, rings=8,
                   bone="UpperIsland", category="underside_crystal")

    # Radial resort pavilions, gardens and palms; no external crossing geometry.
    for index in range(12):
        angle = index * math.tau / 12 + math.pi / 12
        center = Vector(polar(2.93, angle, 8.12))
        pavilion(h, f"Resort pavilion {index:02d}", center, .54 + .06 * (index % 3),
                 "UpperIsland", angle)
    for index in range(30):
        angle = index * math.tau / 30 + .07
        radius = 2.13 + .95 * ((index * 13) % 23) / 23
        palm(h, f"Upper palm {index:02d}", polar(radius, angle, 8.13),
             .27 + .05 * (index % 5), "UpperIsland", angle + .25)
    for index in range(36):
        angle = index * math.tau / 36
        radius = 1.10 + 1.12 * ((index * 5) % 19) / 19
        scale = .05 + .022 * (index % 3)
        h.ball(f"Lagoon garden shrub {index:02d}", polar(radius, angle, 8.16),
               (scale * 1.3, scale, scale), "green_light" if index % 4 == 0 else "green",
               segments=12, rings=8, bone="UpperIsland", category="garden_detail")


def build_sanctuary(h: DioramaAuthor) -> None:
    h.current = "Sanctuary"
    # Central sanctuary rises from continuous terraces—there are deliberately no steps.
    for index, (radius, depth, z, material) in enumerate(((1.16, .16, 8.20, "ivory"),
                                                          (.94, .14, 8.34, "gold"),
                                                          (.73, .16, 8.47, "ivory"))):
        h.cyl(f"Sanctuary continuous plinth {index:02d}", (0, 0, z), radius, depth,
              material, vertices=64, bone="Sanctuary", category="sanctuary_architecture", bevel=.025)
    for index in range(10):
        angle = index * math.tau / 10
        center = Vector(polar(.76, angle, 8.53))
        h.cyl(f"Sanctuary colonnade {index:02d}", center + Vector((0, 0, .42)), .065,
              .84, "ivory", vertices=16, bone="Sanctuary", category="sanctuary_architecture", bevel=.012)
        h.ring(f"Sanctuary capital {index:02d}", center + Vector((0, 0, .80)), .095,
               .022, "gold", bone="Sanctuary", category="sanctuary_detail",
               major_segments=20, minor_segments=6)
        h.ball(f"Sanctuary lantern {index:02d}", center + Vector((0, 0, .61)),
               (.035, .035, .08), "warm", segments=12, rings=8, bone="Sanctuary",
               category="sanctuary_light")
    h.cyl("Sanctuary central tower", (0, 0, 9.22), .42, 1.64, "ivory", vertices=40,
          bone="Sanctuary", category="sanctuary_architecture", bevel=.04)
    h.ring("Sanctuary crown halo", (0, 0, 9.68), .54, .055, "gold", major_segments=72,
           minor_segments=10, bone="Sanctuary", category="sanctuary_detail")
    h.cone("Sanctuary central crystal", (0, 0, 10.05), .34, 0, 1.18, "crystal", vertices=8,
           bone="Sanctuary", category="sanctuary_crystal")
    for index in range(6):
        angle = index * math.tau / 6 + math.pi / 6
        foot = Vector(polar(.72, angle, 8.52))
        h.cyl(f"Sanctuary side spire {index:02d}", foot + Vector((0, 0, .66)), .16,
              1.20, "ivory", vertices=24, bone="Sanctuary", category="sanctuary_architecture", bevel=.02)
        h.cone(f"Sanctuary side spire cap {index:02d}", foot + Vector((0, 0, 1.46)),
               .22, 0, .72, "gold" if index % 2 else "crystal", vertices=18,
               bone="Sanctuary", category="sanctuary_architecture")
        for rib_index in range(3):
            a = angle + (rib_index - 1) * .11
            h.beam(f"Sanctuary flying rib {index:02d} {rib_index:02d}",
                   foot + Vector((0, 0, .35)), Vector(polar(.24, a, 9.38)), .026,
                   "gold", bone="Sanctuary", category="sanctuary_detail")
    for index in range(18):
        angle = index * math.tau / 18
        h.ball(f"Sanctuary reflection jewel {index:02d}", polar(.98, angle, 8.47 + .10 * math.sin(angle * 3)),
               (.034, .034, .06), "crystal", segments=10, rings=6, bone="Sanctuary",
               category="sanctuary_crystal")


def build_shield_and_cascades(h: DioramaAuthor) -> None:
    # A substantial toroidal body keeps the boundary oceanic at a distance;
    # the irregular sheet layers and foam below break its primitive regularity.
    h.ring("Sanctuary boundary deep body", (0, 0, 8.05), 4.18, .34, "water",
           major_segments=160, minor_segments=24, bone="WaterShield.A", category="water_shield")
    h.ring("Sanctuary boundary bright body", (0, 0, 8.11), 4.42, .18, "water_light",
           major_segments=160, minor_segments=18, bone="WaterShield.B", category="water_shield")
    configs = [
        ("A", 0.0, 4.12, 1.00, "water"),
        ("B", 1.7, 4.34, .78, "water_light"),
        ("C", 3.4, 4.54, .60, "water"),
    ]
    for suffix, phase, radius, width, material in configs:
        bone = f"WaterShield.{suffix}"
        _, crest = shield_ribbon(h, f"Sanctuary water boundary {suffix}", phase, radius,
                                 width, material, bone, "water_shield")
        h.cable(f"Sanctuary boundary foam crest {suffix}", crest, .040 if suffix == "A" else .027,
                "foam", bone=bone, category="shield_foam")
        for spray_index in range(30):
            angle = spray_index * math.tau / 30 + phase * .23
            r = radius + width * .48 + .12 * math.sin(spray_index * 2.4)
            z = 8.30 + .24 * math.sin(angle * 3 + phase)
            scale = .026 + .018 * (spray_index % 4)
            h.ball(f"Boundary spray {suffix} {spray_index:02d}", polar(r, angle, z),
                   (scale * 1.4, scale, scale * .7), "foam", segments=10, rings=7,
                   bone=bone, category="shield_spray")

    h.current = "Cascades"
    cascade_angles = [.18, .72, 1.46, 2.18, 2.92, 3.58, 4.26, 5.02, 5.72]
    for index, angle in enumerate(cascade_angles):
        radius = 3.22 + .16 * math.sin(index * 1.7)
        start = Vector(polar(radius, angle, 7.99))
        end = Vector(polar(radius * .86, angle + .08, 6.86 - .18 * (index % 3)))
        control = start.lerp(end, .55) + Vector((math.cos(angle) * .12, math.sin(angle) * .12, .08))
        h.cable(f"Upper waterfall body {index:02d}", [start, control, end], .075 + .015 * (index % 3),
                "water_light", bone="Cascades", category="waterfall")
        for rail in (-1, 1):
            tangent = Vector((-math.sin(angle), math.cos(angle), 0))
            h.cable(f"Upper waterfall foam {index:02d} {rail:+d}",
                    [start + tangent * rail * .055, control + tangent * rail * .055,
                     end + tangent * rail * .035], .017, "foam", bone="Cascades",
                    category="waterfall_foam")
        for drop in range(5):
            t = (drop + .6) / 6
            point = start.lerp(end, t) + Vector((.05 * math.sin(drop * 2 + angle), 0, 0))
            h.ball(f"Upper waterfall droplet {index:02d} {drop:02d}", point,
                   (.025, .020, .055), "foam", segments=8, rings=6,
                   bone="Cascades", category="waterfall_foam")


def build_arrival_gate(h: DioramaAuthor) -> None:
    h.current = "ArrivalGate"
    center = Vector((0, -3.83, 8.18))
    h.cyl("Arrival landing disc", (0, -3.52, 8.13), .58, .12, "ivory", vertices=48,
          bone="ArrivalGate", category="arrival_gate", bevel=.025)
    h.ring("Arrival landing light", (0, -3.52, 8.20), .46, .028, "crystal",
           major_segments=56, minor_segments=8, bone="ArrivalGate", category="arrival_light")
    for side in (-1, 1):
        x = side * .52
        h.cyl(f"Arrival portal pylon {side:+d}", (x, -3.88, 8.76), .095, 1.26,
              "ivory", vertices=20, bone="ArrivalGate", category="arrival_gate", bevel=.018)
        h.cone(f"Arrival portal crown {side:+d}", (x, -3.88, 9.55), .16, 0, .46,
               "gold", vertices=20, bone="ArrivalGate", category="arrival_gate")
        for collar_index, z in enumerate((8.38, 8.82, 9.18)):
            h.ring(f"Arrival pylon collar {side:+d} {collar_index:02d}", (x, -3.88, z),
                   .13, .022, "gold", major_segments=20, minor_segments=6,
                   bone="ArrivalGate", category="arrival_detail")
    # Vertical portal: a layered luminous aperture set into the water boundary.
    h.ring("Arrival portal ivory frame", (0, -3.90, 8.88), .62, .105, "ivory", normal=(0, 1, 0),
           major_segments=72, minor_segments=14, bone="ArrivalGate", category="arrival_gate")
    h.ring("Arrival portal gold trim", (0, -3.96, 8.88), .49, .045, "gold", normal=(0, 1, 0),
           major_segments=72, minor_segments=10, bone="ArrivalGate", category="arrival_detail")
    h.ring("Arrival portal photon aperture", (0, -4.02, 8.88), .39, .035, "crystal", normal=(0, 1, 0),
           major_segments=72, minor_segments=10, bone="ArrivalGate", category="arrival_light")
    for index in range(12):
        angle = index * math.tau / 12
        h.ball(f"Arrival route datum {index:02d}", (math.cos(angle) * .39, -4.04,
               8.88 + math.sin(angle) * .39), (.025, .025, .025), "warm",
               segments=10, rings=6, bone="ArrivalGate", category="arrival_detail")
    # The socket bone is the authoritative integration point for the separate bus asset.
    h.ball("Arrival socket marker", (0, -5.22, 8.88), (.055, .055, .055), "crystal",
           segments=12, rings=8, bone="Socket_Bus_Arrival", category="arrival_socket")
    for index in range(3):
        h.ring(f"Arrival approach guide {index:02d}", (0, -4.54 - index * .32, 8.88),
               .20 - index * .035, .016, "crystal", normal=(0, 1, 0), major_segments=32,
               minor_segments=6, bone="Socket_Bus_Arrival", category="arrival_socket")


def build_cloud_bank(h: DioramaAuthor) -> None:
    h.current = "CloudBank"
    rng = random.Random(11027)
    for index in range(76):
        angle = rng.uniform(0, math.tau)
        radius = rng.uniform(2.6, 5.4)
        z = rng.choice((2.82, 6.35, 7.15)) + rng.uniform(-.30, .30)
        # Keep the center water silhouette open by biasing clouds toward the outside.
        if z > 6 and radius < 3.6:
            radius += 1.0
        scale = rng.uniform(.14, .34)
        h.ball(f"Cloud wisp {index:03d}", polar(radius, angle, z),
               (scale * rng.uniform(1.35, 2.1), scale, scale * rng.uniform(.55, .85)),
               "cloud", segments=16, rings=10, bone="CloudBank", category="cloud")


def build(h: DioramaAuthor) -> None:
    build_bones(h)
    build_display_and_lower_island(h)
    build_water_ascent(h)
    build_upper_island(h)
    build_sanctuary(h)
    build_shield_and_cascades(h)
    build_arrival_gate(h)


def keyframe_bones(arm, frame: int) -> None:
    for bone in arm.pose.bones:
        bone.keyframe_insert("location", frame=frame, group=bone.name)
        bone.keyframe_insert("rotation_euler", frame=frame, group=bone.name)
        bone.keyframe_insert("scale", frame=frame, group=bone.name)


def animate_flow_packets(bones, progress: float, reveal: float = 1.0) -> None:
    """Send a visible pulse upward through tracer packets fixed to the helix.

    Rigid bones cannot follow a changing spline radius without leaving the water
    corridor.  The geometry therefore stays embedded in the authored sheet and
    a staggered scale envelope carries the directional cue upward.  This is
    deterministic motion language for a future world, not a fluid-simulation claim.
    """
    for suffix in WATER_ASCENT_TURNS:
        for packet_index in range(FLOW_PACKET_COUNT):
            name = f"WaterFlow.{suffix}.{packet_index}"
            bone = bones.get(name)
            if bone is None:
                continue
            base_t = (packet_index + .5) / FLOW_PACKET_COUNT
            distance = abs(((base_t - progress + .5) % 1.0) - .5)
            pulse = max(0.0, 1.0 - distance / .24)
            pulse = pulse * pulse * (3.0 - 2.0 * pulse)
            scale = max(.001, reveal * (.018 + .982 * pulse))
            bone.scale = (scale, scale, scale)


def animate(arm) -> list[dict]:
    arm.animation_data_create()
    rows = []
    bones = arm.pose.bones
    for clip_name, seconds, loop in CLIPS:
        end = round(seconds * FPS)
        action = bpy.data.actions.new(clip_name)
        action.use_fake_user = True
        arm.animation_data.action = action
        for frame in range(end + 1):
            reset_pose(arm)
            # Author loops with a byte-for-byte equivalent terminal pose.  A
            # mathematically equivalent 2pi rotation may import through a
            # different quaternion branch and create a visible loop seam.
            t = 0.0 if loop and frame == end else frame / end
            phase = math.tau * t
            if clip_name == "Sanctuary_Idle":
                # These bones point upward, so their local Y axis is world Z.
                # Rotating local Z tips the complete water sheets sideways; local
                # Y keeps each authored volume anchored while carrying foam and
                # droplets around the intended vertical flow axis.
                bones["WaterSpiral.A"].rotation_euler.y = phase
                bones["WaterSpiral.B"].rotation_euler.y = -phase
                bones["WaterSpiral.C"].rotation_euler.y = phase
                bones["WaterShield.A"].rotation_euler.y = phase
                bones["WaterShield.B"].rotation_euler.y = -phase
                bones["WaterShield.C"].rotation_euler.y = phase
                bones["UpperIsland"].location.z = .055 * math.sin(phase)
                bones["UpperIsland"].rotation_euler.x = .008 * math.sin(phase)
                bones["Cascades"].location.z = .035 * math.sin(phase * 2 + .4)
                bones["Sanctuary"].scale = (1 + .012 * math.sin(phase * 2),) * 3
                bones["ArrivalGate"].scale = (1 + .025 * math.sin(phase * 3),) * 3
                bones["Socket_Bus_Arrival"].location.y = .08 * math.sin(phase)
                bones["CloudBank"].rotation_euler.y = phase * .08
                animate_flow_packets(bones, t)
            elif clip_name == "Watershield_Pulse":
                # Calm, axis-locked circulation: one revolution per five-second
                # loop, with only a very small breathing offset.  Large sheet
                # tilts and waterfall stretching read as loose tentacles rather
                # than water, so those transforms intentionally stay neutral.
                bones["WaterSpiral.A"].rotation_euler.y = phase
                bones["WaterSpiral.B"].rotation_euler.y = -phase
                bones["WaterSpiral.C"].rotation_euler.y = phase
                shield_breathe = .010 * math.sin(phase * 2)
                bones["WaterShield.A"].scale = (1 + shield_breathe, 1 + shield_breathe, 1)
                bones["WaterShield.B"].scale = (1 - shield_breathe, 1 - shield_breathe, 1)
                bones["WaterShield.A"].rotation_euler.y = phase
                bones["WaterShield.B"].rotation_euler.y = -phase
                bones["WaterShield.C"].rotation_euler.y = phase
                bones["ArrivalGate"].scale = (1 + .025 * math.sin(phase) ** 4,) * 3
                bones["CloudBank"].rotation_euler.y = -phase * .06
                animate_flow_packets(bones, t)
            else:
                ease = t * t * (3 - 2 * t)
                water_scale = .18 + .82 * ease
                for suffix, direction in zip(("A", "B", "C"), (1, -1, 1)):
                    bones[f"WaterSpiral.{suffix}"].scale = (water_scale,) * 3
                    bones[f"WaterSpiral.{suffix}"].rotation_euler.y = direction * phase * (1 + .5 * ease)
                    shield_scale = .12 + .88 * ease
                    bones[f"WaterShield.{suffix}"].scale = (shield_scale, shield_scale, .30 + .70 * ease)
                    bones[f"WaterShield.{suffix}"].rotation_euler.y = direction * phase * .45
                bones["UpperIsland"].location.z = -.36 * (1 - ease)
                bones["Cascades"].scale = (ease, ease, max(.05, ease))
                bones["Sanctuary"].scale = (.55 + .45 * ease,) * 3
                bones["ArrivalGate"].scale = (.25 + .75 * ease,) * 3
                bones["Socket_Bus_Arrival"].location.y = .48 * (1 - ease)
                bones["CloudBank"].scale = (.70 + .30 * ease,) * 3
                animate_flow_packets(bones, t, ease)
            keyframe_bones(arm, frame)
        for curve in action.fcurves:
            for point in curve.keyframe_points:
                point.interpolation = "BEZIER" if clip_name == "Arrival_Awakening" else "LINEAR"
        rows.append({"name": clip_name, "seconds": seconds, "frames": end + 1,
                     "fps": FPS, "loop": loop})
    arm.animation_data.action = None
    reset_pose(arm)
    return rows


def export_glb(path: Path, arm, mesh) -> None:
    geo.select_only([arm, mesh])
    bpy.context.view_layer.objects.active = arm
    bpy.ops.export_scene.gltf(
        filepath=str(path), export_format="GLB", use_selection=True,
        export_skins=True, export_animations=True, export_animation_mode="ACTIONS",
        export_force_sampling=True, export_yup=True, export_extras=True,
        export_tangents=True, export_materials="EXPORT",
    )


def build_collision(h: DioramaAuthor, output: Path) -> dict:
    objects = []
    collision = h.mat["collision"]
    objects.append(geo.cylinder("UCX_DISPLAY_PLINTH", (0, 0, -.05), 5.55, .34, collision,
                                vertices=16, bevel=0))
    objects.append(geo.cylinder("UCX_LOWER_ISLAND", (0, 0, .38), 3.65, .72, collision,
                                vertices=16, bevel=0))
    objects.append(geo.cone("UCX_VOLCANO", (0, 0, 1.82), 2.35, .58, 2.65, collision,
                            vertices=16, bevel=0))
    objects.append(geo.cylinder("UCX_UPPER_ISLAND", (0, 0, 7.44), 3.80, 1.55, collision,
                                vertices=16, bevel=0))
    objects.append(geo.cylinder("UCX_SANCTUARY", (0, 0, 9.18), 1.20, 2.20, collision,
                                vertices=16, bevel=0))
    objects.append(geo.cylinder("UCX_ARRIVAL_PAD", (0, -3.52, 8.17), .62, .20, collision,
                                vertices=12, bevel=0))
    geo.select_only(objects)
    path = output / "Inverted_Water_Sanctuary_UCX.glb"
    bpy.ops.export_scene.gltf(filepath=str(path), export_format="GLB", use_selection=True,
                              export_yup=True, export_materials="NONE")
    stats = {"path": path.name, "objects": len(objects), "bytes": path.stat().st_size,
             "sha256": sha256(path)}
    collection = bpy.data.collections.new("COLLISION_editable")
    bpy.context.scene.collection.children.link(collection)
    for obj in objects:
        for old in list(obj.users_collection):
            old.objects.unlink(obj)
        collection.objects.link(obj)
    collection.hide_render = True
    collection.hide_viewport = True
    return stats


def parts_index(h: DioramaAuthor) -> dict:
    rows = []
    for obj in h.parts:
        triangles = 0
        if obj.type == "MESH":
            obj.data.calc_loop_triangles()
            triangles = len(obj.data.loop_triangles)
        rows.append({
            "name": obj.name,
            "type": obj.type,
            "category": obj.get("axm_category"),
            "controlling_bone": obj.get("axm_bone"),
            "materials": [material.name for material in getattr(obj.data, "materials", [])],
            "triangles": triangles,
        })
    return {
        "schema": "axm.uc.creator-parts-index/v0.2",
        "asset_id": ASSET_ID,
        "semantic_deduplication": "Appearance-only variants remain material overrides, not new geometry atoms.",
        "parts": rows,
    }


def assembly_recipe() -> dict:
    return {
        "schema": "axm.uc.assembly-recipe/v0.2",
        "asset_id": ASSET_ID,
        "non_degradable_invariants": [
            "lower crater remains the visible source of the reverse-water ascent",
            "the ascent visibly blooms into a complete protective water boundary",
            "upper and lower landmasses remain disconnected",
            "no stair, causeway or span assembly is permitted",
            "Socket_Bus_Arrival remains replacement-ready for the separate transit asset",
        ],
        "assembly_order": [
            {"step": 1, "family": "display", "cause": "plinth and ocean establish decorative scale"},
            {"step": 2, "family": "lower_world", "cause": "beach, island, ruins and volcano establish origin"},
            {"step": 3, "family": "reverse_water", "cause": "three ribbons, filaments, foam and droplets establish upward flow"},
            {"step": 4, "family": "upper_world", "cause": "floating geology, lagoon, resort and sanctuary establish destination"},
            {"step": 5, "family": "water_boundary", "cause": "three thick circulating ribbons complete the safe perimeter"},
            {"step": 6, "family": "arrival_gate", "cause": "portal and named socket preserve the only current arrival logic"},
            {"step": 7, "family": "motion", "cause": "rigid bones retain independently editable hydrology and state motion"},
        ],
        "replacement_contract": {
            "socket": "Socket_Bus_Arrival",
            "forward": "local -Y toward the portal",
            "up": "local +Z",
            "note": "The diorama intentionally includes no hero transit vehicle. Attach the separately authored bus here."
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--water-profile", choices=WATER_PROFILES, default="prop")
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    args = parser.parse_args(argv)
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.unit_settings.system = "METRIC"
    bpy.context.scene.unit_settings.scale_length = 1.0
    bpy.context.scene.render.fps = FPS

    author = DioramaAuthor(output, args.water_profile)
    build(author)
    index = parts_index(author)
    (output / "parts-index.json").write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")
    (output / "assembly-recipe.json").write_text(json.dumps(assembly_recipe(), indent=2) + "\n", encoding="utf-8")

    arm, mesh = rig(author)
    arm.name = "Inverted_Water_Sanctuary_Rig"
    arm.data.name = "Inverted_Water_Sanctuary_Skeleton"
    mesh.name = "Inverted_Water_Sanctuary_Surface"
    mesh.data.name = "Inverted_Water_Sanctuary_Mesh"
    arm["asset_id"] = ASSET_ID
    arm["binding"] = "Rigid environment, water-ribbon, sanctuary and arrival-gate parts on an addressable authored skeleton."
    animations = animate(arm)

    exports = {}
    for filename, ratio in [
        ("Inverted_Water_Sanctuary_LOD0.glb", 1.0),
        ("Inverted_Water_Sanctuary_LOD1.glb", .50),
        ("Inverted_Water_Sanctuary_LOD2.glb", .22),
    ]:
        target = mesh
        if ratio < 1:
            target = mesh.copy()
            target.data = mesh.data.copy()
            bpy.context.collection.objects.link(target)
            target.modifiers.clear()
            geo.select_only([target])
            bpy.context.view_layer.objects.active = target
            modifier = target.modifiers.new("UC adaptive realization LOD", "DECIMATE")
            modifier.ratio = ratio
            modifier.use_collapse_triangulate = True
            bpy.ops.object.modifier_apply(modifier=modifier.name)
            clean_triangles(target)
            skin = target.modifiers.new("UC rigid animation skin", "ARMATURE")
            skin.object = arm
        target.data.calc_loop_triangles()
        path = output / filename
        export_glb(path, arm, target)
        exports[filename] = {
            "path": filename,
            "ratio": ratio,
            "triangles": len(target.data.loop_triangles),
            "vertices": len(target.data.vertices),
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        }
        if ratio < 1:
            bpy.data.objects.remove(target, do_unlink=True)

    collision = build_collision(author, output)
    reset_pose(arm)
    arm.animation_data.action = bpy.data.actions["Sanctuary_Idle"]
    bpy.context.scene.frame_set(0)
    blend = output / "Inverted_Water_Sanctuary.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend), compress=True)

    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent.parent
    source_files = [
        Path(__file__).resolve(),
        script_dir / "axm_blender_forge.py",
        script_dir / "axm_hero_motion.py",
        script_dir / "render_sky_resort_start.py",
        script_dir / "verify_sky_resort_start.py",
        repo_root / "examples/requests/forge_sky_resort_start_diorama.json",
    ]
    manifest = {
        "schema": SCHEMA,
        "asset_id": ASSET_ID,
        "status": "STRUCTURE_EXPORTED_VISUAL_REVIEW_REQUIRED",
        "meters_per_unit": 1.0,
        "recommended_decorative_instance_scale": .12,
        "water_profile": args.water_profile,
        "forward_axis": "-Y in Blender; +Z in glTF",
        "source_references": [
            {"filename": "1000001915.png", "sha256": "752c50158fb3926029058415a6a4ad04579035cf2b02a12756ce858fcd75f658"},
            {"filename": "1000001916.png", "sha256": "353866f990416d048a309b558bfd5ac3707286f7b5a1fc3a66cde42cbdbb5d88"},
            {"filename": "1000001920.png", "sha256": "7199e70886c1fb73459f56fbc42c055bd6ed1ed41bb276b28d1c99c5cb1e5380"},
        ],
        "exports": exports,
        "collision": collision,
        "editable_source": {"path": blend.name, "bytes": blend.stat().st_size, "sha256": sha256(blend)},
        "parts_index": "parts-index.json",
        "assembly_recipe": "assembly-recipe.json",
        "construction": {
            "builder": "tools/blender/axm_sky_resort_start.py",
            "request": "examples/requests/forge_sky_resort_start_diorama.json",
            "source_hashes": {str(path.relative_to(repo_root)): sha256(path) for path in source_files},
            "canonical_families": ["lower-volcanic-island", "reverse-water-ascent", "floating-sanctuary", "water-boundary", "arrival-gate"],
            "material_families": [material.name for material in bpy.data.materials if not material.name.startswith("Sanctuary_Collision")],
            "water_realization": (
                "layered alpha/transmission water with foam, droplets and upward tracer packets; not fluid simulation"
                if args.water_profile == "world-study" else
                "opaque glossy ribbon, curve, spray and droplet geometry; not fluid simulation"
            ),
            "deduplication_rule": "Appearance-only variants do not create new reusable atoms.",
        },
        "bones": [{"name": name, "parent": values[2]} for name, values in author.bones.items()],
        "animations": animations,
        "integration_socket": {
            "bone": "Socket_Bus_Arrival",
            "owner": "separate bus-scene asset lane",
            "vehicle_included": False,
        },
        "visual_contract": "examples/requests/forge_sky_resort_start_diorama.json",
        "truth_boundary": [
            "Deterministic authored interpretation; not automatic image-to-3D reconstruction.",
            "Water is loopable art-directed geometry, not physically simulated fluid.",
            "Structural and animation verification do not establish final visual acceptance.",
            "No target-engine gameplay, navigation, networking or finished bus integration claim.",
        ],
    }
    (output / "asset-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print("SKY_RESORT_START_FORGE_COMPLETE", json.dumps({
        "parts": len(index["parts"]), "exports": list(exports), "collision": collision["path"]
    }), flush=True)


if __name__ == "__main__":
    main()
