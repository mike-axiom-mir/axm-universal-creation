"""Forge the poster-derived Future UC creation-machine game-asset family.

This is a deterministic authored interpretation.  It uses the existing UC
Blender/PBR/rig/export lane and retains editable source parts, construction
metadata, animation clips, LODs and collision.  It does not project the source
picture onto geometry and does not claim character reconstruction.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import random

import bpy
from mathutils import Vector

import axm_blender_forge as geo
from axm_hero_motion import clean_triangles, rig
from axm_oops_character import reset_pose
from axm_hero_surfaces import surface
from axm_salvage_surfaces import pbr_material, solid


ASSET_ID = "future-uc-creation-machine-v1"
SCHEMA = "axm.uc.future-creation-machine/v1"
FPS = 30
CLIPS = [
    ("Forge_Idle", 8.0, True),
    ("Forge_Build_Pulse", 4.0, True),
    ("Dormant_To_Awake", 3.0, False),
]
PYLON_NAMES = [
    "Intent",
    "Simulation",
    "Test_Lanes",
    "Composition",
    "Workflow_Discovery",
    "Growth_Memory",
    "New_Organs",
    "Creation_Output",
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


class ForgeAuthor:
    """Small UC authoring adapter consumed by the retained rigid-rig compiler."""

    def __init__(self, output: Path):
        self.output = output
        self.parts: list[bpy.types.Object] = []
        self.bones: dict[str, tuple[tuple[float, float, float], tuple[float, float, float], str | None]] = {}
        self.current = "Root"
        textures = output / "textures"
        self.mat = {
            "frame": surface(textures, "UC_Obsidian_Frame", "#111923", "steel", 512),
            "titanium": surface(textures, "UC_Aged_Titanium", "#65717c", "steel", 512),
            "porcelain": surface(textures, "UC_Porcelain_Shell", "#d9e3e4", "metal", 512),
            "gold": surface(textures, "UC_Forge_Gold", "#b77a2a", "metal", 512),
            "copper": surface(textures, "UC_Conductive_Copper", "#7f4328", "metal", 512),
            "ceramic_dark": surface(textures, "UC_Ceramic_Heatshield", "#273744", "metal", 512),
            "basalt": pbr_material(textures, "UC_Basalt", "#29313a", "stone", 512),
            "moss": pbr_material(textures, "UC_Living_Moss", "#496a3e", "cloth", 512),
            "moss_light": pbr_material(textures, "UC_Young_Moss", "#72945a", "cloth", 512),
            "rubber": pbr_material(textures, "UC_Transit_Rubber", "#15191e", "rubber", 512),
            "cyan": solid("UC_Photon_Cyan", "#2fd8ff", .12, .18, 5.5),
            "cyan_soft": solid("UC_Soft_Cyan", "#64dff5", .05, .30, 2.1),
            "core_field": solid("UC_Core_Field", "#2798bb", .08, .22, 1.15),
            "amber": solid("UC_Signal_Amber", "#ffb44b", .08, .24, 3.6),
            "dark": solid("UC_Deep_Recess", "#05090f", .45, .24, 0),
            "water": solid("UC_Waterfall_Light", "#4aaeff", .0, .16, 3.0),
            "collision": solid("UC_Collision_Debug", "#ff00aa", 0, .9, 0),
        }
        glass = solid("UC_Deep_Glass", "#0a3a52", .2, .10, .25)
        bsdf = glass.node_tree.nodes.get("Principled BSDF")
        bsdf.inputs["Coat Weight"].default_value = .35
        bsdf.inputs["Coat Roughness"].default_value = .08
        self.mat["glass"] = glass

    def bone(self, name, head, tail, parent=None):
        self.bones[name] = (tuple(head), tuple(tail), parent)

    def bind(self, obj, bone=None, category="structure"):
        obj["axm_bone"] = bone or self.current
        obj["axm_category"] = category
        self.parts.append(obj)
        return obj

    def box(self, name, center, dimensions, material="frame", *, bevel=.04, rotation=(0, 0, 0), bone=None, category="structure"):
        return self.bind(geo.box(name, center, dimensions, self.mat[material], rotation=rotation, bevel=bevel, segments=3), bone, category)

    def ball(self, name, center, scale, material="frame", *, segments=36, rings=24, bone=None, category="structure"):
        return self.bind(geo.sphere(name, center, scale, self.mat[material], segments=segments, rings=rings), bone, category)

    def cyl(self, name, center, radius, depth, material="frame", *, axis=(0, 0, 1), vertices=32, bone=None, category="structure"):
        obj = geo.cylinder(name, center, radius, depth, self.mat[material], vertices=vertices, bevel=min(.025, radius * .16))
        obj.rotation_mode = "QUATERNION"
        obj.rotation_quaternion = Vector(axis).to_track_quat("Z", "Y")
        return self.bind(obj, bone, category)

    def cone(self, name, center, radius1, radius2, depth, material="frame", *, vertices=32, bone=None, category="structure"):
        return self.bind(geo.cone(name, center, radius1, radius2, depth, self.mat[material], vertices=vertices,
                                  bevel=min(.025, max(radius1, radius2) * .08)), bone, category)

    def ring(self, name, center, major, minor, material="frame", *, normal=(0, 0, 1), major_segments=64, minor_segments=12, bone=None, category="structure"):
        obj = geo.torus(name, center, major, minor, self.mat[material], major_segments=major_segments, minor_segments=minor_segments)
        obj.rotation_mode = "QUATERNION"
        obj.rotation_quaternion = Vector(normal).to_track_quat("Z", "Y")
        return self.bind(obj, bone, category)

    def beam(self, name, start, end, radius, material="frame", *, vertices=20, bone=None, category="structure"):
        return self.bind(geo.beam(name, start, end, radius, self.mat[material], vertices=vertices), bone, category)

    def cable(self, name, points, radius, material="frame", *, bone=None, category="structure"):
        return self.bind(geo.cable(name, [tuple(p) for p in points], radius, self.mat[material]), bone, category)


def polar(radius: float, angle: float, z: float) -> tuple[float, float, float]:
    return (radius * math.cos(angle), radius * math.sin(angle), z)


def layered_point(start: Vector, control: Vector, end: Vector, t: float) -> Vector:
    """Sample the authored two-segment energy route without hiding its construction."""
    return start.lerp(control, t * 2) if t <= .5 else control.lerp(end, (t - .5) * 2)


def build_bones(h: ForgeAuthor) -> None:
    h.bone("Root", (0, 0, 0), (0, 0, .4))
    h.bone("Core", (0, 0, 2.80), (0, 0, 3.20), "Root")
    h.bone("Ring_A", (0, 0, 2.80), (.45, 0, 2.80), "Root")
    h.bone("Ring_B", (0, 0, 2.80), (0, .45, 2.80), "Root")
    h.bone("Gantry", (0, 0, 2.80), (0, 0, 3.25), "Root")
    h.bone("Energy", (0, 0, 2.10), (0, 0, 2.55), "Root")
    for index in range(8):
        angle = -math.pi / 2 + index * math.tau / 8
        x, y, z = polar(4.15, angle, .84)
        h.bone(f"Pylon.{index + 1:02d}", (x, y, z), (x, y, z + .38), "Root")
    island_layout = [
        (-5.55, 2.85, .25), (5.75, 2.60, .65), (-5.10, -3.65, -.10),
        (5.45, -3.50, .15), (-1.75, 5.45, .90), (2.10, -5.50, -.45),
    ]
    for index, (x, y, z) in enumerate(island_layout, 1):
        h.bone(f"Island.{index:02d}", (x, y, z), (x, y, z + .4), "Root")
    h.bone("Bus", (-5.65, -1.10, 3.35), (-5.65, -1.10, 3.78), "Root")
    h.bone("BusRotor.L", (-6.30, -1.04, 3.58), (-6.30, -1.04, 3.90), "Bus")
    h.bone("BusRotor.R", (-5.00, -1.04, 3.58), (-5.00, -1.04, 3.90), "Bus")
    h.bone("BusDoor", (-5.65, -1.55, 3.22), (-5.65, -1.55, 3.55), "Bus")


def build_core(h: ForgeAuthor) -> None:
    center = (0, 0, 2.80)
    h.current = "Core"
    h.ball("UC luminous seed envelope", center, (.72, .72, .72), "core_field", segments=64, rings=40, category="core")
    h.ball("UC concentrated inner seed", center, (.39, .39, .39), "cyan", segments=48, rings=32, category="core")
    for angle in range(0, 360, 45):
        a = math.radians(angle)
        p = polar(.59, a, 2.80)
        h.ball(f"Seed aperture {angle:03d}", p, (.08, .08, .08), "amber", segments=18, rings=12, category="core_detail")
    h.ring("Seed equator cage", center, .78, .038, "porcelain", normal=(0, 0, 1), major_segments=80, category="core_detail")
    h.ring("Seed meridian cage", center, .78, .035, "gold", normal=(1, 0, 0), major_segments=80, category="core_detail")
    for z in (2.20, 3.40):
        h.cyl("Seed axial cap", (0, 0, z), .16, .18, "gold", vertices=32, category="core_detail")

    h.current = "Ring_A"
    h.ring("Orbital ring A spine", center, 1.34, .105, "frame", normal=(1, 0, .18), major_segments=96, minor_segments=16, category="orbital_ring")
    h.ring("Orbital ring A trim", center, 1.34, .036, "cyan", normal=(1, 0, .18), major_segments=96, minor_segments=10, category="orbital_light")
    for index in range(16):
        a = index * math.tau / 16
        x = .24 * math.sin(a)
        y = 1.34 * math.cos(a)
        z = 2.80 + 1.34 * math.sin(a)
        h.box(f"Ring A control cassette {index:02d}", (x, y, z), (.19, .26, .13), "titanium", bevel=.025,
              rotation=(a, 0, .12), category="orbital_module")

    h.current = "Ring_B"
    h.ring("Orbital ring B spine", center, 1.62, .095, "gold", normal=(0, 1, -.22), major_segments=112, minor_segments=14, category="orbital_ring")
    h.ring("Orbital ring B energy rail", center, 1.62, .026, "amber", normal=(0, 1, -.22), major_segments=112, minor_segments=8, category="orbital_light")
    for index in range(20):
        a = index * math.tau / 20
        x = 1.62 * math.cos(a)
        y = -.30 * math.sin(a)
        z = 2.80 + 1.62 * math.sin(a)
        h.cyl(f"Ring B radial bearing {index:02d}", (x, y, z), .065, .18, "porcelain", axis=(math.cos(a), 0, math.sin(a)), vertices=18, category="orbital_module")

    h.current = "Gantry"
    h.ring("Main radial gantry", center, 2.04, .15, "frame", normal=(0, 0, 1), major_segments=128, minor_segments=16, category="gantry")
    h.ring("Main gantry porcelain rail", center, 1.88, .055, "porcelain", normal=(0, 0, 1), major_segments=112, minor_segments=10, category="gantry")
    h.ring("Main gantry cyan trace", center, 2.05, .022, "cyan", normal=(0, 0, 1), major_segments=112, minor_segments=8, category="gantry_light")
    for index in range(24):
        a = index * math.tau / 24
        outer = polar(2.12, a, 2.80)
        inner = polar(1.70, a, 2.80)
        h.beam(f"Gantry spoke {index:02d}", inner, outer, .045, "gold" if index % 3 == 0 else "titanium", vertices=14, category="gantry")
        x, y, _ = polar(2.11, a, 2.80)
        h.box(f"Gantry armor tile {index:02d}", (x, y, 2.80), (.28, .20, .26), "porcelain" if index % 2 == 0 else "frame",
              bevel=.032, rotation=(0, 0, a), category="gantry_tile")
        for side in (-1, 1):
            h.cyl(f"Gantry fastener {index:02d} {side:+d}", (x + math.cos(a) * .07, y + math.sin(a) * .07, 2.80 + side * .12), .018, .035,
                  "gold", axis=(0, 0, 1), vertices=10, category="fastener")
    for index in range(8):
        a = index * math.tau / 8
        start = polar(2.00, a, 2.80)
        end = polar(2.72, a, 1.75)
        h.beam(f"Gantry load truss {index:02d}", start, end, .075, "frame", vertices=18, category="gantry")
        h.cyl(f"Gantry docking collar {index:02d}", end, .21, .25, "gold", axis=(math.cos(a), math.sin(a), 0), vertices=32, category="docking")
    h.cyl("Forge lower reactor", (0, 0, 1.12), .46, 2.05, "frame", vertices=48, category="reactor")
    for z, radius in ((.20, .30), (.52, .44), (.86, .51), (1.28, .54), (1.72, .49), (2.02, .38)):
        h.ring(f"Reactor collar {z:.2f}", (0, 0, z), radius, .052, "gold" if int(z * 10) % 2 else "titanium", normal=(0, 0, 1), category="reactor")
    for index in range(12):
        a = index * math.tau / 12
        h.beam(f"Reactor cable {index:02d}", polar(.24, a, .18), polar(.42, a + .08, 2.17), .022, "cyan_soft", vertices=12, category="energy")
    h.cyl("Forge downward beam", (0, 0, -.12), .10, .75, "cyan", vertices=32, category="energy")


def build_core_detail_pass(h: ForgeAuthor) -> None:
    """Add readable close-range mechanisms without changing the accepted silhouette."""
    h.current = "Core"
    for index in range(12):
        a = index * math.tau / 12
        p = Vector(polar(.69, a, 2.80 + .055 * math.sin(a * 2)))
        h.box(
            f"Seed containment petal {index:02d}", p, (.18, .34, .31),
            "porcelain" if index % 3 else "ceramic_dark", bevel=.045,
            rotation=(.08 * math.sin(a), .18 * math.cos(a), a), category="core_armor",
        )
        h.cyl(
            f"Seed petal actuator {index:02d}", Vector(polar(.84, a, 2.80)), .035, .22,
            "copper", axis=(-math.sin(a), math.cos(a), .2), vertices=14, category="core_actuator",
        )
    for index in range(8):
        a = index * math.tau / 8 + math.pi / 8
        low = Vector(polar(.28, a, 2.22))
        waist = Vector(polar(.63, a, 2.52))
        high = Vector(polar(.28, a, 3.38))
        h.beam(f"Seed lower containment rib {index:02d}", low, waist, .025, "gold", vertices=14, category="core_rib")
        h.beam(f"Seed upper containment rib {index:02d}", waist + Vector((0, 0, .56)), high, .025, "titanium", vertices=14, category="core_rib")
        h.ball(f"Seed rib datum light {index:02d}", waist, (.032, .032, .032), "amber", segments=12, rings=8, category="core_light")

    h.current = "Ring_A"
    for index in range(24):
        a = index * math.tau / 24
        p = Vector((.21 * math.sin(a), 1.24 * math.cos(a), 2.80 + 1.24 * math.sin(a)))
        axis = Vector((0, -math.sin(a), math.cos(a)))
        h.cyl(f"Ring A guide roller {index:02d}", p, .043, .13, "copper", axis=axis, vertices=16, category="orbital_bearing")
        if index % 3 == 0:
            h.ball(f"Ring A phase sensor {index:02d}", p + axis * .11, (.035, .035, .035), "cyan", segments=12, rings=8, category="orbital_sensor")

    h.current = "Ring_B"
    for index in range(20):
        a = index * math.tau / 20
        p = Vector((1.52 * math.cos(a), -.23 * math.sin(a), 2.80 + 1.52 * math.sin(a)))
        h.box(
            f"Ring B brake fin {index:02d}", p, (.18, .09, .26),
            "ceramic_dark" if index % 2 else "titanium", bevel=.018,
            rotation=(0, -a, .12 * math.sin(a)), category="orbital_brake",
        )

    h.current = "Gantry"
    for index in range(32):
        a = index * math.tau / 32
        radius = 1.73 if index % 2 else 2.25
        p = Vector(polar(radius, a, 2.80 + (.05 if index % 2 else -.05)))
        h.box(
            f"Gantry service scale {index:02d}", p, (.14, .22, .08),
            "copper" if index % 4 == 0 else "ceramic_dark", bevel=.016,
            rotation=(0, 0, a), category="gantry_service",
        )
    for lane, radius in enumerate((1.76, 2.27)):
        for index in range(16):
            a0 = index * math.tau / 16 + lane * .08
            a1 = a0 + math.tau / 32
            h.cable(
                f"Gantry braided conduit {lane}-{index:02d}",
                [polar(radius, a0, 2.67 + lane * .24), polar(radius, (a0 + a1) / 2, 2.71 + lane * .24), polar(radius, a1, 2.67 + lane * .24)],
                .015, "copper" if lane else "cyan_soft", category="gantry_conduit",
            )

    for index in range(16):
        a = index * math.tau / 16
        h.box(
            f"Reactor heatshield rib {index:02d}", polar(.49, a, 1.18), (.10, .17, 1.28),
            "ceramic_dark" if index % 2 else "titanium", bevel=.025,
            rotation=(0, 0, a), category="reactor_detail",
        )
        if index % 2 == 0:
            h.cable(
                f"Reactor service umbilical {index:02d}",
                [polar(.54, a, .48), polar(.68, a + .09, 1.12), polar(.58, a, 1.88)],
                .024, "copper", category="reactor_conduit",
            )
    for z in (.66, 1.10, 1.54):
        for index in range(8):
            a = index * math.tau / 8 + z * .13
            h.ball(f"Reactor diagnostic light {z:.2f}-{index:02d}", polar(.56, a, z), (.027, .027, .027),
                   "amber" if index % 3 == 0 else "cyan", segments=10, rings=7, category="reactor_light")


def build_hologram(h: ForgeAuthor, index: int, center: Vector, bone: str) -> None:
    x, y, z = center
    material = "cyan" if index not in (3, 6) else "amber"
    if index == 0:
        h.ball("Intent seed", (x, y, z), (.22, .22, .27), material, segments=28, rings=18, bone=bone, category="hologram")
        h.ring("Intent orbit", (x, y, z), .34, .018, "cyan_soft", normal=(1, .2, .5), bone=bone, category="hologram")
    elif index == 1:
        for scale, rotation in ((.26, 0), (.19, .42), (.12, -.36)):
            h.box("Simulation nested lattice", (x, y, z), (scale, scale, scale), material, bevel=.018, rotation=(rotation, rotation, rotation), bone=bone, category="hologram")
    elif index == 2:
        for row in range(3):
            for col in range(3 - row):
                h.box("Test lane cell", (x + (col - (2 - row) / 2) * .17, y, z - .18 + row * .16), (.13, .13, .13), material,
                      bevel=.018, rotation=(0, 0, .12 * (row + col)), bone=bone, category="hologram")
    elif index == 3:
        for k in range(5):
            a = k * math.tau / 5
            h.ball("Composition atom", (x + .24 * math.cos(a), y + .24 * math.sin(a), z), (.075, .075, .075), material,
                   segments=16, rings=10, bone=bone, category="hologram")
            h.beam("Composition bond", (x, y, z), (x + .24 * math.cos(a), y + .24 * math.sin(a), z), .016, "cyan_soft", vertices=10, bone=bone, category="hologram")
        h.ball("Composition nucleus", (x, y, z), (.11, .11, .11), "cyan", segments=18, rings=12, bone=bone, category="hologram")
    elif index == 4:
        points = []
        for k in range(7):
            a = k * math.tau / 7
            points.append((x + .28 * math.cos(a), y + .28 * math.sin(a), z + .08 * math.sin(a * 2)))
        h.cable("Workflow discovery loop", points + [points[0]], .024, material, bone=bone, category="hologram")
        for k, point in enumerate(points):
            h.ball(f"Workflow node {k}", point, (.055, .055, .055), "amber" if k == 3 else "cyan", segments=14, rings=9, bone=bone, category="hologram")
    elif index == 5:
        for ring_index, radius in enumerate((.12, .22, .31)):
            h.ring(f"Growth memory layer {ring_index}", (x, y, z), radius, .018, material, normal=(0, 0, 1), bone=bone, category="hologram")
        h.beam("Growth memory spine", (x, y, z - .30), (x, y, z + .30), .025, "amber", vertices=12, bone=bone, category="hologram")
    elif index == 6:
        h.ball("New organ core", (x, y, z), (.17, .13, .16), material, segments=24, rings=16, bone=bone, category="hologram")
        for k in range(6):
            a = k * math.tau / 6
            h.cable("New organ branch", [(x, y, z), (x + .12 * math.cos(a), y + .12 * math.sin(a), z + .10),
                                          (x + .28 * math.cos(a), y + .28 * math.sin(a), z + .18 * math.sin(a * 2))], .021,
                    "cyan_soft", bone=bone, category="hologram")
            h.ball("New organ socket", (x + .28 * math.cos(a), y + .28 * math.sin(a), z + .18 * math.sin(a * 2)),
                   (.052, .052, .052), material, segments=12, rings=8, bone=bone, category="hologram")
    else:
        h.cyl("Creation output arrow", (x, y, z + .04), .055, .48, material, vertices=16, bone=bone, category="hologram")
        h.cyl("Creation output tip", (x, y, z + .33), .16, .25, material, vertices=20, bone=bone, category="hologram")
        h.ring("Creation output gate", (x, y, z - .24), .27, .028, "amber", normal=(0, 0, 1), bone=bone, category="hologram")


def build_pylons(h: ForgeAuthor) -> None:
    for index, label in enumerate(PYLON_NAMES):
        angle = -math.pi / 2 + index * math.tau / 8
        bone = f"Pylon.{index + 1:02d}"
        x, y, _ = polar(4.15, angle, 0)
        h.current = bone
        h.cyl(f"{label} lower anchor", (x, y, .38), .48, .22, "frame", vertices=48, bone=bone, category="pylon")
        h.cyl(f"{label} gold bearing", (x, y, .53), .43, .10, "gold", vertices=48, bone=bone, category="pylon")
        h.cyl(f"{label} porcelain deck", (x, y, .62), .37, .09, "porcelain", vertices=48, bone=bone, category="pylon")
        h.ring(f"{label} light rim", (x, y, .68), .34, .028, "cyan", normal=(0, 0, 1), bone=bone, category="pylon_light")
        h.cyl(f"{label} hologram projector", (x, y, .78), .17, .18, "titanium", vertices=32, bone=bone, category="pylon")
        outward = Vector((math.cos(angle), math.sin(angle), 0))
        tangent = Vector((-math.sin(angle), math.cos(angle), 0))
        for leg in range(4):
            a = angle + leg * math.tau / 4 + math.pi / 4
            foot = Vector((x + .40 * math.cos(a), y + .40 * math.sin(a), .29))
            shoulder = Vector((x + .27 * math.cos(a), y + .27 * math.sin(a), .67))
            h.beam(f"{label} articulated support {leg}", foot, shoulder, .034, "titanium", vertices=14, bone=bone, category="pylon_support")
            h.ball(f"{label} support joint {leg}", shoulder, (.050, .050, .050), "gold", segments=14, rings=9, bone=bone, category="pylon_joint")
        h.ring(f"{label} focusing coil", (x, y, .88), .235, .018, "copper", normal=(0, 0, 1), bone=bone, category="pylon_coil")
        for prong in range(4):
            a = prong * math.tau / 4 + angle
            start = Vector((x + .20 * math.cos(a), y + .20 * math.sin(a), .84))
            end = Vector((x + .29 * math.cos(a), y + .29 * math.sin(a), 1.04))
            h.beam(f"{label} focusing prong {prong}", start, end, .022, "ceramic_dark", vertices=12, bone=bone, category="pylon_focus")
            h.ball(f"{label} focusing emitter {prong}", end, (.035, .035, .035), "cyan", segments=12, rings=8, bone=bone, category="pylon_focus")
        panel = Vector((x, y, .49)) + outward * .47
        h.box(f"{label} service console", panel, (.10, .31, .27), "ceramic_dark", bevel=.025,
              rotation=(0, 0, angle), bone=bone, category="pylon_console")
        for signal in range(3):
            h.ball(f"{label} console signal {signal}", panel + tangent * ((signal - 1) * .07) + outward * .055,
                   (.022, .022, .022), "amber" if signal == index % 3 else "cyan", segments=10, rings=7,
                   bone=bone, category="pylon_console")
        for k in range(8):
            a = k * math.tau / 8
            h.cyl(f"{label} deck fastener {k}", (x + .30 * math.cos(a), y + .30 * math.sin(a), .71), .017, .028,
                  "gold", vertices=10, bone=bone, category="fastener")
        build_hologram(h, index, Vector((x, y, 1.22)), bone)
        # Structural and energy routes are authored separately so the pylon can be detached.
        h.current = "Energy"
        a0 = Vector(polar(2.28, angle, 1.58))
        a1 = Vector(polar(3.15, angle, 1.06))
        a2 = Vector((x, y, .72))
        h.cable(f"{label} energy path", [a0, a1, a2], .032, "cyan_soft", bone="Energy", category="energy")
        h.cable(f"{label} return path", [a0 + Vector((0, 0, .12)), a1 + Vector((0, 0, .12)), a2 + Vector((0, 0, .12))],
                .013, "amber", bone="Energy", category="energy")
        h.beam(f"{label} conduit spine inner", a0 + Vector((0, 0, -.08)), a1 + Vector((0, 0, -.08)), .024,
               "frame", vertices=12, bone="Energy", category="energy_structure")
        h.beam(f"{label} conduit spine outer", a1 + Vector((0, 0, -.08)), a2 + Vector((0, 0, -.08)), .024,
               "frame", vertices=12, bone="Energy", category="energy_structure")
        for collar in range(1, 6):
            point = layered_point(a0, a1, a2, collar / 6)
            h.cyl(f"{label} conduit isolator {collar}", point, .043, .055, "porcelain", axis=(0, 0, 1), vertices=14,
                  bone="Energy", category="energy_isolator")


def build_island(h: ForgeAuthor, index: int, position: tuple[float, float, float], scale: float, variant: int) -> None:
    x, y, z = position
    bone = f"Island.{index:02d}"
    h.current = bone
    h.cone(f"Island {index} tapered basalt body", (x, y, z), .22 * scale, 1.05 * scale, 1.65 * scale,
           "basalt", vertices=11, bone=bone, category="island")
    h.cone(f"Island {index} fractured upper mantle", (x, y, z + .52 * scale), .72 * scale, 1.10 * scale, .62 * scale,
           "basalt", vertices=13, bone=bone, category="island")
    h.cyl(f"Island {index} moss top", (x, y, z + .86 * scale), 1.06 * scale, .16 * scale, "moss", vertices=16, bone=bone, category="island")
    for crust in range(12):
        a = crust * math.tau / 12 + variant * .11
        radius = (.72 + .18 * ((crust + variant) % 3) / 2) * scale
        cx, cy = x + radius * math.cos(a), y + radius * math.sin(a)
        h.box(f"Island {index} broken rim plate {crust}", (cx, cy, z + .82 * scale + .04 * (crust % 2)),
              ((.28 + .08 * (crust % 3)) * scale, (.22 + .06 * ((crust + 1) % 3)) * scale, .16 * scale),
              "basalt", bevel=.025 * scale, rotation=(.04 * (crust % 2), .07 * ((crust + 1) % 3), a + .18),
              bone=bone, category="island_detail")
    # Underside shards make the hidden surface intentional and readable.
    for shard in range(9):
        a = shard * math.tau / 9 + variant * .17
        radius = (.30 + .45 * ((shard * 37) % 7) / 7) * scale
        sx, sy = x + radius * math.cos(a), y + radius * math.sin(a)
        h.cyl(f"Island {index} underside shard {shard}", (sx, sy, z - .80 * scale), (.10 + .08 * (shard % 3)) * scale,
              (.75 + .45 * ((shard + 1) % 4) / 4) * scale, "basalt", axis=(.15 * math.cos(a), .15 * math.sin(a), 1),
              vertices=7, bone=bone, category="island_detail")
    # Inhabited scale cues: towers, trees, bridge sockets and a waterfall-light ribbon.
    tower_count = 2 + variant % 3
    for tower in range(tower_count):
        a = (tower + .35) * math.tau / tower_count + variant
        tx, ty = x + .46 * scale * math.cos(a), y + .46 * scale * math.sin(a)
        height = (.50 + .16 * ((tower + variant) % 3)) * scale
        h.cyl(f"Island {index} creation spire {tower}", (tx, ty, z + 1.05 * scale + height / 2), .075 * scale, height,
              "porcelain" if tower % 2 == 0 else "gold", vertices=10, bone=bone, category="island_structure")
        h.ball(f"Island {index} spire light {tower}", (tx, ty, z + 1.06 * scale + height), (.06 * scale,) * 3,
               "cyan", segments=14, rings=9, bone=bone, category="island_light")
    for tree in range(6):
        a = tree * math.tau / 6 + .3 * variant
        radius = (.42 + .22 * (tree % 2)) * scale
        tx, ty = x + radius * math.cos(a), y + radius * math.sin(a)
        h.cyl(f"Island {index} tree trunk {tree}", (tx, ty, z + .99 * scale), .025 * scale, .20 * scale, "gold", vertices=8, bone=bone, category="foliage")
        h.ball(f"Island {index} tree crown {tree}", (tx, ty, z + 1.15 * scale), (.12 * scale, .10 * scale, .13 * scale),
               "moss", segments=14, rings=9, bone=bone, category="foliage")
    side = -1 if index % 2 else 1
    wx = x + side * .78 * scale
    h.box(f"Island {index} waterfall light", (wx, y - .02 * scale, z + .10 * scale), (.08 * scale, .05 * scale, 1.35 * scale),
          "water", bevel=.015, bone=bone, category="waterfall")
    h.ring(f"Island {index} bridge socket", (x, y - .82 * scale, z + .97 * scale), .14 * scale, .028 * scale,
           "gold", normal=(0, -1, 0), bone=bone, category="docking")
    # A second detail frequency turns the islands into inhabited production sites.
    for rib in range(8):
        a = rib * math.tau / 8 + variant * .07
        inner = Vector((x + .18 * scale * math.cos(a), y + .18 * scale * math.sin(a), z + .94 * scale))
        outer = Vector((x + .78 * scale * math.cos(a), y + .78 * scale * math.sin(a), z + .93 * scale))
        h.beam(f"Island {index} surface load rib {rib}", inner, outer, .022 * scale, "gold" if rib % 3 == 0 else "titanium",
               vertices=10, bone=bone, category="island_infrastructure")
    for building in range(3):
        a = (building + .22) * math.tau / 3 + variant * .31
        radius = (.26 + .12 * building) * scale
        bx, by = x + radius * math.cos(a), y + radius * math.sin(a)
        height = (.16 + .06 * ((building + variant) % 3)) * scale
        h.box(f"Island {index} workshop {building}", (bx, by, z + 1.00 * scale + height / 2),
              (.18 * scale, .14 * scale, height), "ceramic_dark", bevel=.022 * scale,
              rotation=(0, 0, a), bone=bone, category="island_architecture")
        h.box(f"Island {index} workshop roof {building}", (bx, by, z + 1.02 * scale + height),
              (.22 * scale, .18 * scale, .045 * scale), "porcelain", bevel=.018 * scale,
              rotation=(0, 0, a), bone=bone, category="island_architecture")
        h.ball(f"Island {index} workshop lamp {building}", (bx, by, z + 1.06 * scale + height),
               (.025 * scale,) * 3, "amber", segments=10, rings=7, bone=bone, category="island_light")
    for root in range(5):
        a = root * math.tau / 5 + variant * .21
        h.cable(
            f"Island {index} hanging root conduit {root}",
            [(x + .66 * scale * math.cos(a), y + .66 * scale * math.sin(a), z + .72 * scale),
             (x + .54 * scale * math.cos(a + .12), y + .54 * scale * math.sin(a + .12), z + .15 * scale),
             (x + .28 * scale * math.cos(a - .16), y + .28 * scale * math.sin(a - .16), z - .58 * scale)],
            .018 * scale, "copper", bone=bone, category="island_conduit",
        )
    for crystal in range(6):
        a = crystal * math.tau / 6 + variant * .19
        radius = (.36 + .28 * (crystal % 2)) * scale
        h.cone(f"Island {index} underside photon crystal {crystal}",
               (x + radius * math.cos(a), y + radius * math.sin(a), z - (.46 + .18 * (crystal % 3)) * scale),
               .035 * scale, .075 * scale, .32 * scale, "cyan" if crystal % 3 else "amber", vertices=8,
               bone=bone, category="island_light")


def build_islands(h: ForgeAuthor) -> None:
    layouts = [
        ((-5.55, 2.85, .25), .90), ((5.75, 2.60, .65), .78), ((-5.10, -3.65, -.10), .70),
        ((5.45, -3.50, .15), .82), ((-1.75, 5.45, .90), .58), ((2.10, -5.50, -.45), .66),
    ]
    for index, (position, scale) in enumerate(layouts, 1):
        build_island(h, index, position, scale, index)
    h.current = "Root"
    # The forge has its own inhabited foundation and visible load path.
    h.cone("Forge anchor island", (0, 0, -.75), .58, 2.28, 2.30, "basalt", vertices=15, category="anchor_island")
    h.cone("Forge anchor upper mantle", (0, 0, .04), 1.45, 2.38, .86, "basalt", vertices=17, category="anchor_island")
    h.cyl("Forge anchor moss shelf", (0, 0, .43), 2.22, .22, "moss", vertices=20, category="anchor_island")
    for index in range(20):
        a = index * math.tau / 20
        radius = 1.72 + .25 * (index % 3) / 2
        h.box(f"Anchor fractured rim plate {index:02d}", (radius * math.cos(a), radius * math.sin(a), .43 + .06 * (index % 2)),
              (.48, .34, .23), "basalt", bevel=.035, rotation=(.03 * (index % 3), .05 * ((index + 1) % 3), a + .11),
              category="anchor_detail")
    for index in range(16):
        a = index * math.tau / 16
        radius = 1.55 + .35 * (index % 3) / 2
        h.cyl(f"Anchor underside crystal {index:02d}", (radius * math.cos(a), radius * math.sin(a), -1.78 - .18 * (index % 4)),
              .11 + .03 * (index % 3), .82 + .25 * (index % 5), "basalt", axis=(.18 * math.cos(a), .18 * math.sin(a), 1),
              vertices=8, category="anchor_detail")
    for index in range(12):
        a = index * math.tau / 12
        x, y, _ = polar(1.66, a, 0)
        h.cyl(f"Anchor perimeter beacon {index:02d}", (x, y, .72), .055, .32, "gold", vertices=12, category="anchor_structure")
        h.ball(f"Anchor beacon light {index:02d}", (x, y, .91), (.055, .055, .055), "cyan", segments=14, rings=9, category="anchor_light")


def build_bus(h: ForgeAuthor) -> None:
    base = Vector((-5.65, -1.10, 3.35))
    h.current = "Bus"
    h.ball("Cloud bus pressure hull", base, (1.08, .48, .42), "porcelain", segments=56, rings=32, category="transit")
    h.ball("Cloud bus glass cabin", base + Vector((-.42, -.38, .12)), (.48, .18, .28), "glass", segments=40, rings=24, category="transit")
    h.box("Cloud bus floor spine", base + Vector((0, .03, -.35)), (1.85, .62, .18), "frame", bevel=.09, category="transit")
    for index in range(5):
        x = base.x - .50 + index * .25
        h.box(f"Cloud bus window {index}", (x, base.y - .45, base.z + .07), (.17, .035, .17), "glass", bevel=.035, category="transit")
    h.ring("Cloud bus gold waist", base, 1.04, .045, "gold", normal=(1, 0, 0), major_segments=64, minor_segments=10, category="transit")
    for side, sx in (("L", -1), ("R", 1)):
        rx = base.x + sx * .65
        bone = f"BusRotor.{side}"
        h.current = bone
        h.cyl(f"Cloud bus rotor mast {side}", (rx, base.y + .05, base.z + .52), .055, .36, "frame", vertices=18, bone=bone, category="transit")
        h.ball(f"Cloud bus rotor hub {side}", (rx, base.y + .05, base.z + .72), (.11, .11, .08), "gold", segments=24, rings=14, bone=bone, category="transit")
        for blade in range(4):
            a = blade * math.tau / 4
            end = (rx + .43 * math.cos(a), base.y + .05 + .43 * math.sin(a), base.z + .73)
            h.beam(f"Cloud bus rotor blade {side} {blade}", (rx, base.y + .05, base.z + .73), end, .035, "titanium",
                   vertices=12, bone=bone, category="transit")
    h.current = "Bus"
    for side in (-1, 1):
        h.cyl("Cloud bus ion nacelle", (base.x + side * .72, base.y + .26, base.z - .22), .16, .46, "frame", axis=(0, 1, 0), vertices=24, category="transit")
        h.cyl("Cloud bus ion light", (base.x + side * .72, base.y + .50, base.z - .22), .11, .05, "cyan", axis=(0, 1, 0), vertices=20, category="transit")
    h.current = "BusDoor"
    h.box("Cloud bus sliding door", (base.x + .15, base.y - .49, base.z - .03), (.46, .07, .50), "gold", bevel=.045, bone="BusDoor", category="transit")
    for index in range(8):
        h.cyl(f"Cloud bus hull fastener {index}", (base.x - .78 + index * .22, base.y - .44, base.z - .27), .018, .032,
              "frame", axis=(0, -1, 0), vertices=10, bone="Bus", category="fastener")
    h.current = "Bus"
    for band, offset in enumerate((-.68, -.32, .10, .48, .78)):
        h.ring(f"Cloud bus pressure band {band}", base + Vector((offset, 0, 0)), .46, .022,
               "copper" if band in (1, 3) else "ceramic_dark", normal=(1, 0, 0), major_segments=40, minor_segments=8,
               category="transit_detail")
    for side in (-1, 1):
        rail_y = base.y + side * .49
        h.beam(f"Cloud bus side utility rail {side:+d}", (base.x - .82, rail_y, base.z - .04),
               (base.x + .82, rail_y, base.z - .04), .025, "gold", vertices=12, category="transit_detail")
        for pod in range(3):
            px = base.x - .48 + pod * .48
            h.cyl(f"Cloud bus service pod {side:+d}-{pod}", (px, rail_y, base.z - .19), .07, .18,
                  "ceramic_dark", axis=(0, 1, 0), vertices=16, category="transit_detail")
    for fin in range(4):
        fx = base.x - .58 + fin * .39
        h.box(f"Cloud bus dorsal fin {fin}", (fx, base.y + .04, base.z + .44), (.20, .055, .24),
              "titanium", bevel=.022, rotation=(0, -.12 + fin * .08, 0), category="transit_detail")
    h.beam("Cloud bus sensor boom", base + Vector((.62, 0, .34)), base + Vector((1.18, 0, .68)), .024,
           "titanium", vertices=12, category="transit_sensor")
    h.ball("Cloud bus sensor eye", base + Vector((1.18, 0, .68)), (.075, .075, .075), "cyan",
           segments=18, rings=12, category="transit_sensor")


def build(h: ForgeAuthor) -> None:
    build_bones(h)
    build_core(h)
    build_core_detail_pass(h)
    build_pylons(h)
    build_islands(h)
    build_bus(h)


def keyframe_bones(arm, frame: int) -> None:
    for bone in arm.pose.bones:
        for channel in ("location", "rotation_euler", "scale"):
            bone.keyframe_insert(channel, frame=frame, group=bone.name)


def animate(arm) -> list[dict]:
    rows = []
    scene = bpy.context.scene
    scene.render.fps = FPS
    for clip_name, seconds, loop in CLIPS:
        action = bpy.data.actions.new(clip_name)
        arm.animation_data_create()
        arm.animation_data.action = action
        action.use_fake_user = True
        end = round(seconds * FPS)
        frames = list(range(0, end + 1, 5))
        if frames[-1] != end:
            frames.append(end)
        for frame in frames:
            reset_pose(arm)
            t = frame / end
            phase = math.tau * t
            bones = arm.pose.bones
            if clip_name == "Forge_Idle":
                bones["Ring_A"].rotation_euler.y = math.tau * 2 * t
                bones["Ring_B"].rotation_euler.y = -math.tau * 2 * t
                pulse = 1 + .035 * math.sin(phase * 2)
                bones["Core"].scale = (pulse, pulse, pulse)
                bones["Energy"].scale = (1, 1, 1 + .025 * math.sin(phase * 3))
                for index in range(8):
                    bones[f"Pylon.{index + 1:02d}"].location.y = .08 * math.sin(phase + index * math.tau / 8)
                for index in range(6):
                    bones[f"Island.{index + 1:02d}"].location.y = .11 * math.sin(phase + index * .73)
                    bones[f"Island.{index + 1:02d}"].rotation_euler.y = .018 * math.sin(phase + index)
                bones["Bus"].location = (.16 * math.sin(phase), .08 * math.sin(phase * 2), .09 * math.sin(phase + .7))
                bones["Bus"].rotation_euler.y = .045 * math.sin(phase)
                bones["BusRotor.L"].rotation_euler.y = math.tau * 10 * t
                bones["BusRotor.R"].rotation_euler.y = -math.tau * 10 * t
                bones["BusDoor"].location.y = .02 * math.sin(phase)
            elif clip_name == "Forge_Build_Pulse":
                bones["Ring_A"].rotation_euler.y = math.tau * 3 * t
                bones["Ring_B"].rotation_euler.y = -math.tau * 2 * t
                core_pulse = 1 + .18 * math.sin(math.pi * t) ** 4
                bones["Core"].scale = (core_pulse,) * 3
                bones["Energy"].scale = (1, 1, 1 + .15 * math.sin(math.pi * t) ** 2)
                for index in range(8):
                    local = (t - index / 12) % 1
                    amount = math.sin(math.pi * min(1, local * 2)) ** 2 if local < .5 else 0
                    scale = 1 + .16 * amount
                    bones[f"Pylon.{index + 1:02d}"].scale = (scale, scale, scale)
                    bones[f"Pylon.{index + 1:02d}"].location.y = .13 * amount
                bones["BusRotor.L"].rotation_euler.y = math.tau * 8 * t
                bones["BusRotor.R"].rotation_euler.y = -math.tau * 8 * t
            else:
                ease = t * t * (3 - 2 * t)
                bones["Ring_A"].rotation_euler.y = math.tau * .75 * ease
                bones["Ring_B"].rotation_euler.y = -math.tau * .55 * ease
                core_scale = .52 + .48 * ease
                bones["Core"].scale = (core_scale,) * 3
                bones["Energy"].scale = (.20 + .80 * ease,) * 3
                for index in range(8):
                    delay = index * .045
                    rise = max(0, min(1, (t - delay) / max(.001, 1 - delay)))
                    rise = rise * rise * (3 - 2 * rise)
                    bones[f"Pylon.{index + 1:02d}"].location.y = -.40 * (1 - rise)
                    bones[f"Pylon.{index + 1:02d}"].scale = (.72 + .28 * rise,) * 3
                bones["BusRotor.L"].rotation_euler.y = math.tau * 4 * ease
                bones["BusRotor.R"].rotation_euler.y = -math.tau * 4 * ease
                bones["BusDoor"].location.x = .26 * ease
            keyframe_bones(arm, frame)
        for curve in action.fcurves:
            for key in curve.keyframe_points:
                key.interpolation = "BEZIER" if clip_name == "Dormant_To_Awake" else "LINEAR"
        rows.append({"name": clip_name, "seconds": seconds, "frames": end + 1, "fps": FPS, "loop": loop})
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


def build_collision(h: ForgeAuthor, output: Path) -> dict:
    objects = []
    collision = h.mat["collision"]
    objects.append(geo.cylinder("UCX_FORGE_ANCHOR", (0, 0, -.50), 2.20, 2.50, collision, vertices=12, bevel=0))
    objects.append(geo.sphere("UCX_FORGE_CORE", (0, 0, 2.80), (2.20, 2.20, 2.20), collision, segments=16, rings=10))
    for index in range(8):
        angle = -math.pi / 2 + index * math.tau / 8
        objects.append(geo.cylinder(f"UCX_PYLON_{index + 1:02d}", polar(4.15, angle, .56), .48, .70, collision, vertices=12, bevel=0))
    layouts = [(-5.55, 2.85, .25, .90), (5.75, 2.60, .65, .78), (-5.10, -3.65, -.10, .70),
               (5.45, -3.50, .15, .82), (-1.75, 5.45, .90, .58), (2.10, -5.50, -.45, .66)]
    for index, (x, y, z, scale) in enumerate(layouts, 1):
        objects.append(geo.cylinder(f"UCX_ISLAND_{index:02d}", (x, y, z + .10 * scale), 1.03 * scale, 1.72 * scale, collision, vertices=10, bevel=0))
    objects.append(geo.box("UCX_CLOUD_BUS", (-5.65, -1.10, 3.35), (2.25, 1.05, .92), collision, bevel=0))
    geo.select_only(objects)
    path = output / "Future_UC_Creation_Machine_UCX.glb"
    bpy.ops.export_scene.gltf(filepath=str(path), export_format="GLB", use_selection=True, export_yup=True, export_materials="NONE")
    stats = {"path": path.name, "objects": len(objects), "bytes": path.stat().st_size, "sha256": sha256(path)}
    collection = bpy.data.collections.new("COLLISION_editable")
    bpy.context.scene.collection.children.link(collection)
    for obj in objects:
        for old in list(obj.users_collection):
            old.objects.unlink(obj)
        collection.objects.link(obj)
    collection.hide_render = True
    collection.hide_viewport = True
    return stats


def parts_index(h: ForgeAuthor) -> dict:
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
        "semantic_deduplication": "Color or texture-only variants remain material overrides and are not counted as new geometry atoms.",
        "parts": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.unit_settings.system = "METRIC"
    bpy.context.scene.unit_settings.scale_length = 1.0
    author = ForgeAuthor(output)
    build(author)
    index = parts_index(author)
    (output / "parts-index.json").write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")
    arm, mesh = rig(author)
    arm.name = "Future_UC_Creation_Machine_Rig"
    arm.data.name = "Future_UC_Creation_Machine_Skeleton"
    mesh.name = "Future_UC_Creation_Machine_Surface"
    mesh.data.name = "Future_UC_Creation_Machine_Mesh"
    arm["asset_id"] = ASSET_ID
    arm["binding"] = "Rigid mechanical, pylon, island and transit parts on an addressable authored skeleton."
    animations = animate(arm)

    exports = {}
    for filename, ratio in [
        ("Future_UC_Creation_Machine_LOD0.glb", 1.0),
        ("Future_UC_Creation_Machine_LOD1.glb", .52),
        ("Future_UC_Creation_Machine_LOD2.glb", .22),
    ]:
        target = mesh
        if ratio < 1:
            target = mesh.copy()
            target.data = mesh.data.copy()
            bpy.context.collection.objects.link(target)
            target.modifiers.clear()
            geo.select_only([target])
            bpy.context.view_layer.objects.active = target
            modifier = target.modifiers.new("UC realization LOD", "DECIMATE")
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
    arm.animation_data.action = bpy.data.actions["Forge_Idle"]
    bpy.context.scene.frame_set(0)
    blend = output / "Future_UC_Creation_Machine.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend), compress=True)

    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent.parent
    source_files = [
        Path(__file__).resolve(),
        script_dir / "axm_blender_forge.py",
        script_dir / "axm_hero_motion.py",
        script_dir / "render_future_uc_machine.py",
        script_dir / "verify_future_uc_machine.py",
        repo_root / "examples/requests/forge_future_uc_creation_machine.json",
    ]
    manifest = {
        "schema": SCHEMA,
        "asset_id": ASSET_ID,
        "status": "STRUCTURE_EXPORTED_VISUAL_REVIEW_REQUIRED",
        "meters_per_unit": 1.0,
        "forward_axis": "-Y in Blender; +Z in glTF",
        "source_reference": {
            "filename": "1000001717.png",
            "sha256": "8840c68b4f3614072a4ff2483b4bd2971a332ba0c06e8d4c62db788f084508f6",
            "relationship": "authored visual-direction reference; no pixel projection",
        },
        "exports": exports,
        "collision": collision,
        "editable_source": {"path": blend.name, "bytes": blend.stat().st_size, "sha256": sha256(blend)},
        "parts_index": "parts-index.json",
        "construction": {
            "builder": "tools/blender/axm_future_uc_machine.py",
            "request": "examples/requests/forge_future_uc_creation_machine.json",
            "source_hashes": {str(path.relative_to(repo_root)): sha256(path) for path in source_files},
            "canonical_families": ["orbital-forge", "process-pylon", "floating-island", "cloud-bus"],
            "detail_pass": "v2-close-range-mechanical-layering",
            "detail_families": [
                "core-containment", "orbital-bearings", "gantry-service-conduits", "reactor-heatshield",
                "pylon-focus-and-console", "inhabited-island-infrastructure", "transit-service-hardware",
            ],
            "material_families": [material.name for material in bpy.data.materials if not material.name.startswith("UC_Collision")],
            "deduplication_rule": "Appearance-only variants do not create new reusable atoms.",
        },
        "bones": [{"name": name, "parent": values[2]} for name, values in author.bones.items()],
        "animations": animations,
        "process_pylons": PYLON_NAMES,
        "visual_contract": "examples/requests/forge_future_uc_creation_machine.json",
        "truth_boundary": [
            "Deterministic authored interpretation; not automatic image-to-3D reconstruction.",
            "Structural and animation verification do not establish AAA visual acceptance.",
            "No human/Mir character reconstruction, target-engine gameplay or navigation claim.",
        ],
    }
    (output / "asset-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print("FUTURE_UC_MACHINE_FORGE_COMPLETE", json.dumps({"parts": len(index["parts"]), "exports": list(exports), "collision": collision["path"]}), flush=True)


if __name__ == "__main__":
    main()
