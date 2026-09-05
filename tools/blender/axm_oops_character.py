"""AXM's original OOPS character: modeled geometry, rigid skin, and motion clips.

Run with the machine-managed Blender runtime. The concept PNG is intentionally
not projected onto the mesh: all visible features are actual authored geometry.
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

sys.path.insert(0, str(Path(__file__).resolve().parent))
import axm_blender_forge as geo

PALETTE = [
    ("Ceramic", (226, 218, 196), 165, 20),
    ("PetrolTeal", (39, 105, 109), 128, 95),
    ("SafetyCoral", (237, 95, 47), 151, 35),
    ("Graphite", (34, 43, 48), 133, 155),
    ("Brass", (172, 128, 66), 98, 230),
    ("MintOptic", (98, 224, 204), 58, 100),
    ("Lens", (8, 24, 29), 42, 40),
    ("Lettering", (250, 244, 218), 165, 0),
]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8", newline="\n")


def atlas_material(output):
    folder = output / "textures"
    folder.mkdir(exist_ok=True)
    width, height = 1024, 512
    albedo, orm = bytearray(), bytearray()
    rng = random.Random(42819)
    for y in range(height):
        for x in range(width):
            _, color, roughness, metal = PALETTE[(1 - y // 256) * 4 + x // 256]
            noise = rng.choice((-2, -1, 0, 0, 0, 1, 2))
            albedo.extend([max(0, min(255, channel + noise)) for channel in color] + [255])
            orm.extend((255, max(0, min(255, roughness + noise * 2)), metal, 255))
    geo.write_rgba_png(folder / "OOPS_BaseColor.png", width, height, albedo)
    geo.write_rgba_png(folder / "OOPS_ORM.png", width, height, orm)
    geo.write_rgba_png(folder / "OOPS_Normal.png", width, height, bytes((128, 128, 255, 255)) * (width * height))
    mat = bpy.data.materials.new("OOPS_Atlas_PBR")
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    shader = nodes.get("Principled BSDF")
    images = {}
    for role, filename in (("albedo", "OOPS_BaseColor.png"), ("orm", "OOPS_ORM.png"), ("normal", "OOPS_Normal.png")):
        node = nodes.new("ShaderNodeTexImage")
        node.image = bpy.data.images.load(str(folder / filename))
        if role != "albedo":
            node.image.colorspace_settings.name = "Non-Color"
        node.image.pack()
        node.label = role
        images[role] = node
    links.new(images["albedo"].outputs["Color"], shader.inputs["Base Color"])
    split = nodes.new("ShaderNodeSeparateColor")
    links.new(images["orm"].outputs["Color"], split.inputs["Color"])
    links.new(split.outputs["Green"], shader.inputs["Roughness"])
    links.new(split.outputs["Blue"], shader.inputs["Metallic"])
    normal = nodes.new("ShaderNodeNormalMap")
    links.new(images["normal"].outputs["Color"], normal.inputs["Color"])
    links.new(normal.outputs["Normal"], shader.inputs["Normal"])
    return mat


class Character:
    def __init__(self, mat, detail):
        self.mat, self.detail = mat, detail
        self.palette_materials = [mat.copy() for _ in PALETTE] if detail >= 3 else []
        self.parts = []
        self.bones = {}

    def bind(self, obj, palette=0, bone="Body"):
        obj["axm_palette"] = palette
        obj["axm_bone"] = bone
        self.parts.append(obj)
        return obj

    def box(self, name, loc, dims, palette=0, bone="Body", bevel=.025, rotation=(0, 0, 0)):
        obj = geo.box(name, loc, dims, self.mat, bevel=bevel, segments=5, rotation=rotation)
        for polygon in obj.data.polygons:
            polygon.use_smooth = True
        normals = obj.modifiers.new("ManufacturedSurfaceNormals", "WEIGHTED_NORMAL")
        normals.keep_sharp = True
        return self.bind(obj, palette, bone)

    def ball(self, name, loc, scale, palette=0, bone="Body", segments=32, rings=16):
        return self.bind(geo.sphere(name, loc, scale, self.mat, segments=segments, rings=rings), palette, bone)

    def cyl(self, name, loc, radius, depth, palette=3, bone="Body", rotation=(0, 0, 0), vertices=24, bevel=.003):
        return self.bind(geo.cylinder(name, loc, radius, depth, self.mat, rotation=rotation, vertices=vertices, bevel=bevel), palette, bone)

    def torus(self, name, loc, radius, tube, palette=3, bone="Body", rotation=(math.pi/2, 0, 0)):
        return self.bind(geo.torus(name, loc, radius, tube, self.mat, rotation=rotation, major_segments=40, minor_segments=8), palette, bone)

    def beam(self, name, start, end, radius, palette=0, bone="Body"):
        a, b = Vector(start), Vector(end)
        obj = self.cyl(name, (a+b)/2, radius, (b-a).length, palette, bone)
        obj.rotation_mode = "QUATERNION"
        obj.rotation_quaternion = (b-a).to_track_quat("Z", "Y")
        return obj

    def line(self, name, points, radius, palette=3, bone="Body"):
        return self.bind(geo.cable(name, points, radius, self.mat), palette, bone)

    def text(self, name, text, loc, size, palette=7, bone="Body"):
        curve = bpy.data.curves.new(name, "FONT")
        curve.body, curve.size, curve.align_x = text, size, "CENTER"
        curve.extrude = .00035
        curve.resolution_u = 4
        obj = bpy.data.objects.new(name, curve)
        bpy.context.collection.objects.link(obj)
        obj.location = loc
        obj.rotation_euler.x = math.pi / 2
        curve.materials.append(self.mat)
        return self.bind(obj, palette, bone)

    def bone(self, name, head, tail, parent=None, deform=True):
        self.bones[name] = (head, tail, parent, deform)

    def shell(self):
        rings = [(.438,.090,.095), (.455,.172,.132), (.49,.233,.173), (.56,.279,.199),
                 (.65,.295,.214), (.76,.279,.206), (.87,.247,.184), (.95,.213,.160),
                 (.987,.177,.134), (1.004,.125,.109)]
        count = 64
        vertices = [(rx*math.cos(2*math.pi*i/count), ry*math.sin(2*math.pi*i/count), z)
                    for z, rx, ry in rings for i in range(count)]
        faces = []
        for level in range(len(rings)-1):
            for i in range(count):
                j = (i+1) % count
                faces.append((level*count+i, level*count+j, (level+1)*count+j, (level+1)*count+i))
        faces.extend([tuple(reversed(range(count))), tuple((len(rings)-1)*count+i for i in range(count))])
        mesh = bpy.data.meshes.new("PearCeramicShell")
        mesh.from_pydata(vertices, [], faces)
        mesh.update()
        obj = bpy.data.objects.new("OOPS_PearShell", mesh)
        bpy.context.collection.objects.link(obj)
        mesh.materials.append(self.mat)
        for face in mesh.polygons:
            face.use_smooth = True
        subdivision = obj.modifiers.new("CrownedCeramic", "SUBSURF")
        subdivision.levels = 1
        self.bind(obj)
        self.body_shell = obj

    def project_shell(self, point, offset=.0005):
        """Project detailing onto the evaluated curved shell, including subdivision."""
        bpy.context.view_layer.update()
        shell = self.body_shell.evaluated_get(bpy.context.evaluated_depsgraph_get())
        direction = Vector((point[0],point[1],0)).normalized()
        origin = direction*2
        origin.z = point[2]
        found, position, normal, _ = shell.ray_cast(origin,-direction)
        if not found:
            raise ValueError(f"shell projection missed: {point}")
        return position+normal*offset

    def shell_seam(self, name, points):
        # Project densely sampled segment points; a sparse Bezier can bow
        # through or away from the surface between its projected controls.
        samples=[]
        for a,b in zip(points,points[1:]):
            for i in range(8):
                samples.append(self.project_shell(Vector(a).lerp(Vector(b),i/8),.0003))
        samples.append(self.project_shell(points[-1],.0003))
        curve=bpy.data.curves.new(name,"CURVE")
        curve.dimensions="3D"
        curve.bevel_depth=.0009
        curve.bevel_resolution=1
        spline=curve.splines.new("POLY")
        spline.points.add(len(samples)-1)
        for p,co in zip(spline.points,samples): p.co=(*co,1)
        obj=bpy.data.objects.new(name,curve)
        bpy.context.collection.objects.link(obj)
        curve.materials.append(self.mat)
        self.bind(obj,3,"Body")

    def mount_front_assembly(self, start, reference):
        """Seat a control and its labels on the shell instead of a guessed Y plane."""
        bpy.context.view_layer.update()
        shell=self.body_shell.evaluated_get(bpy.context.evaluated_depsgraph_get())
        found,point,_,_=shell.ray_cast(Vector((reference[0],-2,reference[2])),Vector((0,1,0)))
        if not found: raise ValueError("front service assembly missed shell")
        delta=point.y-.003-reference[1]
        for obj in self.parts[start:]: obj.location.y+=delta

    def loft_y(self, name, sections, palette=0, bone="Body", x=0, power=.62):
        """Manufactured rounded-rectangle sections, not a scaled box primitive."""
        count = 40
        vertices = []
        for y, width, z, height in sections:
            for i in range(count):
                angle = math.tau * i / count
                c, s = math.cos(angle), math.sin(angle)
                vertices.append((x + width * .5 * math.copysign(abs(c)**power, c), y,
                                 z + height * .5 * math.copysign(abs(s)**power, s)))
        faces = []
        for row in range(len(sections)-1):
            for i in range(count):
                j = (i+1) % count
                faces.append((row*count+i, (row+1)*count+i, (row+1)*count+j, row*count+j))
        faces += [tuple(range(count)), tuple((len(sections)-1)*count+i for i in reversed(range(count)))]
        if sections[-1][0] < sections[0][0]:
            faces = [tuple(reversed(face)) for face in faces]
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(vertices, [], faces)
        mesh.update()
        obj = bpy.data.objects.new(name, mesh)
        bpy.context.collection.objects.link(obj)
        mesh.materials.append(self.mat)
        for face in mesh.polygons:
            face.use_smooth = True
        mod = obj.modifiers.new("CrownedPanel", "SUBSURF")
        mod.levels = 1
        return self.bind(obj, palette, bone)

    def fastener(self, name, loc, radius=.0045, bone="Body", rotation=(math.pi/2,0,0)):
        self.cyl(name+"Socket", loc, radius*1.28, .0025, 3, bone, rotation=rotation, vertices=16, bevel=.0006)
        self.cyl(name+"Head", (loc[0],loc[1]-.0015,loc[2]), radius, .003, 4, bone,
                 rotation=rotation, vertices=12, bevel=.0006)
        self.box(name+"Slot", (loc[0],loc[1]-.0036,loc[2]), (radius*1.3,.0008,.0012),
                 3,bone,bevel=.0002)

    def premium_details(self):
        # Functional seams and panel relief; deliberately restrained, not a
        # blanket grid of decorative greebles. Wear is baked separately.
        for s in (-1,1):
            self.shell_seam("SideServiceSplit", [(s*.205,-.083,.951),(s*.235,-.086,.906),
                      (s*.262,-.09,.827),(s*.279,-.09,.732),(s*.282,-.08,.644),
                      (s*.264,-.072,.543),(s*.207,-.063,.481)])
            self.box("FlankRubberLatch",(s*.27,-.061,.622),(.024,.075,.034),3,bevel=.008)
            self.box("FlankTealLatch",(s*.28,-.061,.624),(.019,.057,.025),1,bevel=.006)
        for x,z in ((-.064,.562),(.129,.562),(-.064,.751),(.129,.751)):
            self.fastener("HatchCaptiveBolt",(x,-.256,z),.0035,"Hatch")
        self.box("HatchHandleRecess",(.118,-.252,.655),(.023,.006,.065),3,"Hatch",bevel=.006)
        self.box("HatchHandle",(.121,-.260,.655),(.010,.010,.041),4,"Hatch",bevel=.003)
        self.text("ChestMotto","FIX FIRST",(-.109,-.181,.819),.012,3)
        self.text("ChestMotto2","PANIC LATER",(-.109,-.184,.804),.009,3)
        # A compact progress indicator and service diagnostic connector.
        start=len(self.parts)
        self.box("DiagnosticFrame",(.145,-.157,.895),(.046,.018,.016),3,bevel=.004)
        for i in range(3):
            self.box("DiagnosticLamp",(.131+i*.012,-.168,.895),(.007,.004,.006),5 if i<2 else 2,bevel=.002)
        self.mount_front_assembly(start,(.145,-.157,.895))
        # Rear hub carries the cable load; rim clips have real fastening heads.
        for angle in (0,math.pi/2,math.pi,math.pi*1.5):
            start=(.026*math.sin(angle),.270,.768+.026*math.cos(angle))
            end=(.095*math.sin(angle),.270,.768+.095*math.cos(angle))
            self.beam("SpoolLoadSpoke",start,end,.005,4,"Spool")
        self.line("LooseCableTail",[(.067,.25,.677),(.116,.245,.645),(.137,.225,.603),
                  (.115,.217,.585)],.006,4,"Spool")
        self.box("CablePlug",(.11,.218,.581),(.041,.027,.024),3,"Spool",bevel=.006)
        for x in (-.054,.054):
            self.box("RearLowerAccess",(x,.200,.586),(.092,.018,.056),0,bevel=.012)
        for z in (.565,.580,.595):
            self.box("RearCoolingLouvre",(0,.219,z),(.048,.005,.005),3,bevel=.002)
        # Deliberately asymmetrical optic scales, not painted highlights alone.
        for x,r,z in ((-.084,.053,1.195),(.092,.038,1.180)):
            for i in range(12):
                a=math.tau*i/12
                self.box("LensCalibrationTick",(x+math.sin(a)*(r+.009),-.164,z+math.cos(a)*(r+.009)),
                         (.0018,.002,.0045),3,"Head",bevel=.0003,rotation=(0,a,0))
        self.text("OpticsSerial","O / 01",(.07,-.145,1.106),.009,3,"Head")
        self.box("HeadSideVentPanel",(.190,.018,1.211),(.008,.104,.061),3,"Head",bevel=.009)
        for y in (-.018,0,.018,.036):
            self.box("HeadSideCoolingFin",(.197,y,1.211),(.008,.010,.047),0,"Head",bevel=.003)
        self.box("RearHeadTealPanel",(0,.117,1.195),(.219,.020,.103),1,"Head",bevel=.027)
        label=self.text("RearHeadSerial","PROPERTY OF AXM",(0,.130,1.18),.012,7,"Head")
        label.rotation_euler.z=math.pi
        for z in (1.152,1.165):
            self.box("HeadRearVent",(0,.128,z),(.132,.008,.004),3,"Head",bevel=.002)
        for z in (1.119,1.286):
            self.fastener("RadioFastener",(.313,.034,z),.004,"Antenna")
        self.text("RadioSerial","07",(.313,.033,1.243),.017,7,"Antenna")
        hub=(.367,.068,1.415)
        for tip in ((.354,.068,1.429),(.384,.068,1.414),(.356,.068,1.402)):
            self.beam("FlagRepairGlyph",hub,tip,.0012,7,"Antenna")
            self.ball("FlagGlyphTerminal",tip,(.003,.001,.003),7,"Antenna",12,6)

    def premium_boot(self, s, foot):
        x=s*.183
        self.loft_y("SculptedBootSole",[(-.256,.12,.030,.035),(-.249,.184,.030,.043),
                    (-.21,.216,.030,.047),(.067,.198,.030,.047),(.10,.17,.030,.041),
                    (.105,.12,.030,.029)],3,foot,x,power=.43)
        boot=self.loft_y("CastMagneticBoot",[(y,w,.044+h/2,h) for y,w,h in
                    [(-.244,.108,.055),(-.233,.176,.074),(-.199,.199,.105),(-.127,.199,.132),
                     (-.074,.18,.172),(.018,.159,.181),(.076,.158,.146),(.089,.13,.115),
                     (.091,.103,.095)]],1,foot,x)
        toe_cap=self.loft_y("BootToeCap",[(-.247,.096,.078,.050),(-.239,.158,.086,.066),
                    (-.207,.185,.101,.093),(-.182,.195,.106,.100),(-.177,.193,.106,.099)],1,foot,x)
        # Raised diagonal service strap follows the slope of the instep.
        self.line("BootInstepStrap",[(x-.079,-.047,.126),(x-.069,-.061,.18),
                  (x-.041,-.074,.211),(x+.041,-.074,.211),(x+.070,-.061,.18),
                  (x+.079,-.047,.126)],.009,3,foot)
        self.line("BootInstepStrapTeal",[(x-.069,-.063,.177),(x-.039,-.077,.212),
                  (x+.039,-.077,.212),(x+.069,-.063,.177)],.0065,1,foot)
        self.cyl("StrapPivot",(x+s*.087,-.045,.146),.025,.014,4,foot,rotation=(0,math.pi/2,0))
        self.cyl("StrapPivotInner",(x+s*.096,-.045,.146),.012,.006,3,foot,rotation=(0,math.pi/2,0))
        self.torus("BootAnkleSeal",(x,.009,.220),.039,.006,3,foot,rotation=(0,0,0))
        for y in (-.207,-.143,-.076,.012,.068):
            for side in (-1,1):
                self.box("RubberSoleLug",(x+side*.095,y,.027),(.022,.031,.037),3,foot,bevel=.006)
        for dx in (-.061,.061):
            for y in (-.182,.043):
                self.cyl("MagneticContact",(x+dx,y,.008),.021,.009,4,foot,vertices=20,bevel=.002)
        self.box("BootToeBumper",(x,-.242,.058),(.146,.013,.025),3,foot,bevel=.009)
        # A small painted service marking is actual geometry sharing the atlas.
        mark=self.text("BootLockMark","U",(x,-.224,.113),.018,7,foot)
        mark.rotation_euler.x=math.pi/2+.55
        mark.data.extrude=0
        mark["axm_project_target"]=toe_cap.name
        mark=self.text("BootLockType","MAG LOCK",(x,-.231,.096),.007,7,foot)
        mark.rotation_euler.x=math.pi/2+.4
        mark.data.extrude=0
        mark["axm_project_target"]=toe_cap.name
        self.box("BootHeelPull",(x,.097,.143),(.048,.020,.025),3,foot,bevel=.005)

    def build(self):
        self.bone("Root", (0,0,0), (0,0,.12))
        if self.detail>=3:
            # A stable ground attachment is useful to controllers/VFX. Keeping
            # a second spatially distinct Root child also prevents FBX importers
            # from auto-connecting the translating pelvis to Root's inferred tail.
            self.bone("Socket_Ground",(0,0,0),(.08,0,0),"Root",False)
        self.bone("Pelvis", (0,0,.41), (0,0,.56), "Root")
        self.bone("Body", (0,0,.55), (0,0,1.0), "Pelvis")
        self.bone("Neck", (0,0,1.0), (0,0,1.075), "Body")
        self.bone("Head", (0,0,1.075), (0,0,1.29), "Neck")
        self.bone("Antenna", (.215,.075,.985), (.33,.075,1.37), "Body")
        self.bone("Spool", (0,.208,.77), (0,.29,.77), "Body")
        self.bone("Hatch", (.165,-.202,.64), (.165,-.202,.82), "Body")
        self.shell()
        # Deliberately asymmetric front service panel and articulated latch.
        if self.detail >= 3:
            self.loft_y("HatchGasket",[(-.138,.23,.653,.252),(-.182,.274,.653,.300),
                        (-.210,.286,.653,.312),(-.219,.286,.653,.312),
                        (-.224,.271,.653,.297)],3,x=.040,power=.48)
            self.loft_y("CoralServiceHatch",[(-.219,.267,.654,.292),(-.225,.272,.654,.294),
                        (-.246,.261,.654,.282),(-.250,.244,.654,.264)],2,"Hatch",x=.040,power=.47)
        else:
            self.box("HatchGasket", (.040,-.202,.653), (.276,.031,.307), 3, bevel=.057)
            self.box("CoralServiceHatch", (.040,-.223,.654), (.256,.035,.284), 2, "Hatch", bevel=.050)
            self.box("HatchInset", (.040,-.244,.658), (.209,.010,.235), 2, "Hatch", bevel=.035)
        for z in (.555,.756):
            self.box("BrassHinge", (.177,-.239,z), (.040,.018,.048), 4, bevel=.012)
            self.cyl("HingePin", (.178,-.252,z), .011, .010, 3, rotation=(math.pi/2,0,0))
        self.box("HatchLatch", (-.093,-.250,.729), (.026,.021,.050), 4, "Hatch", bevel=.008)
        self.box("ServiceTongue", (.028,-.272,.505), (.081,.014,.079), 2, "Hatch", rotation=(.19,0,.09), bevel=.010)
        self.text("ChestBrand", "AXM", (.037,-.252,.692), .040, bone="Hatch")
        self.text("ChestName", "OOPS", (.037,-.252,.646), .035, bone="Hatch")
        self.text("Serial", "REPAIR / 01", (.037,-.252,.610), .011, bone="Hatch")
        self.text("TongueBang", "!", (.027,-.286,.488), .039, bone="Hatch")
        # A quiet service seam follows the shell, not repeated ornamental tiles.
        waist_points=[(.284*math.cos(angle),.203*math.sin(angle),.59)
                      for angle in [i*math.pi/24 for i in range(-2,27)]]
        shoulder_points=[(-.211,-.075,.956),(-.145,-.125,.978),(0,-.138,.984),(.15,-.11,.971)]
        if self.detail>=3:
            self.shell_seam("WaistSeam",waist_points)
            self.shell_seam("ShoulderSeam",shoulder_points)
        else:
            self.line("WaistSeam",waist_points,.0013)
            self.line("ShoulderSeam",shoulder_points,.0017)
        start=len(self.parts)
        self.box("TealChestBadge", (-.112,-.178,.866), (.072,.014,.067), 1, bevel=.011, rotation=(0,0,-.08))
        self.text("BadgeGlyph", "+", (-.112,-.190,.849), .046, 7)
        if self.detail>=3: self.mount_front_assembly(start,(-.112,-.178,.866))
        start=len(self.parts)
        self.box("MailSlotFrame", (.047,-.165,.927), (.103,.014,.026), 4, bevel=.009)
        self.box("MailSlot", (.047,-.175,.927), (.074,.012,.009), 3, bevel=.003)
        if self.detail>=3: self.mount_front_assembly(start,(.047,-.165,.927))
        for i in range(4):
            start=len(self.parts)
            self.box("BreatherSlot", (.175,-.162,.858-i*.015), (.030,.015,.006), 3, bevel=.002)
            if self.detail>=3: self.mount_front_assembly(start,(.175,-.162,.858-i*.015))
        if self.detail >= 2:
            for x,z in ((-.174,.79),(-.198,.66),(.19,.82),(.22,.64),(-.14,.951)):
                if self.detail>=3:
                    point=self.project_shell((x,-.170,z),.001)
                    obj=self.cyl("FlushShellScrew",point,.0045,.003,4,vertices=12,bevel=.0006)
                    direction=Vector((point.x,point.y,0)).normalized()
                    obj.rotation_mode="QUATERNION"
                    obj.rotation_quaternion=direction.to_track_quat("Z","Y")
                else:
                    self.cyl("FlushShellScrew", (x,-.170,z), .006,.010,4,rotation=(math.pi/2,0,0),vertices=12,bevel=.001)
        self.cyl("NeckSocket", (0,0,1.007), .085,.025,4,"Neck")
        self.cyl("NeckCore", (0,0,1.045), .049,.089,3,"Neck")
        for z in (1.015,1.034,1.053,1.072):
            self.torus("NeckBellows", (0,0,z), .054,.009,3,"Neck",rotation=(0,0,0))
        if self.detail >= 3:
            self.loft_y("SculptedHeadCowl",[(.115,.219,1.187,.169),(.110,.310,1.186,.209),
                        (.069,.375,1.19,.242),(-.060,.38,1.187,.242),(-.105,.368,1.183,.230),
                        (-.118,.353,1.181,.216)],0,"Head",power=.43)
            self.loft_y("FaceSeal",[(-.117,.348,1.181,.213),(-.127,.35,1.181,.211)],3,"Head",power=.43)
            self.loft_y("FacePlate",[(-.126,.344,1.181,.207),(-.132,.341,1.181,.205),
                        (-.140,.319,1.181,.191)],0,"Head",power=.45)
        else:
            self.box("HeadGasket", (0,-.007,1.181), (.358,.229,.216),3,"Head",bevel=.080)
            self.box("RoundedHeadShell", (0,.0,1.186), (.375,.229,.245),0,"Head",bevel=.080)
            self.box("FacePlate", (0,-.119,1.185), (.349,.032,.214),0,"Head",bevel=.054)
        for x, radius, z, side in ((-.084,.053,1.195,"L"),(.092,.038,1.180,"R")):
            eye, brow = f"Eye.{side}", f"Brow.{side}"
            self.bone(eye, (x,-.145,z), (x,-.195,z), "Head")
            self.bone(brow, (x,-.139,z+.072), (x,-.139,z+.102), "Head")
            self.cyl("EyeSocket", (x,-.141,z), radius+.013,.018,3,"Head",rotation=(math.pi/2,0,0))
            self.torus("MachinedEyeRim", (x,-.155,z), radius+.008,.005,4,"Head")
            self.ball("EyeWhite", (x,-.159,z), (radius,.016,radius),7,eye)
            self.ball("MintIris", (x+.006,-.175,z), (radius*.68,.010,radius*.68),5,eye)
            self.ball("Pupil", (x+.006,-.184,z), (radius*.36,.009,radius*.39),6,eye,24,12)
            self.ball("Catchlight", (x-.004,-.193,z+.010), (.008,.002,.008),7,eye,16,8)
            self.box("ExpressiveBrow", (x,-.148,z+radius+.023), (radius*1.65,.035,.026),3,brow,bevel=.008,
                     rotation=(0, -.09 if side=="L" else .22, 0))
        for s in (-1,1):
            self.cyl("EarAxle", (s*.19,.008,1.178), .038,.022,4,"Head",rotation=(0,math.pi/2,0))
            self.cyl("EarCap", (s*.202,.008,1.178), .030,.014,0,"Head",rotation=(0,math.pi/2,0))
        if self.detail >= 2:
            self.line("HeadPanelSeam", [(-.161,.095,1.253),(0,.112,1.263),(.157,.094,1.252)], .0015,3,"Head")
            for x in (-.144,.144):
                self.cyl("FaceScrew", (x,-.141,1.109), .004,.006,4,"Head",rotation=(math.pi/2,0,0),vertices=12,bevel=.0007)
        # The flag fin and rear cable lifebelt are OOPS's identity anchors.
        self.box("AntennaMount", (.224,.071,1.004), (.075,.076,.091),4,"Antenna",bevel=.023)
        self.beam("AntennaElbow", (.23,.071,1.02), (.310,.071,1.10), .028,0,"Antenna")
        self.box("SweptRadioFin", (.309,.071,1.217), (.059,.050,.278),0,"Antenna",bevel=.018,rotation=(0,.13,0))
        self.box("RadioTealInsert", (.314,.042,1.217), (.036,.008,.19),1,"Antenna",bevel=.008,rotation=(0,.13,0))
        self.beam("PennantMast", (.326,.071,1.345), (.338,.071,1.455), .0045,4,"Antenna")
        self.ball("MastTip", (.338,.071,1.458), (.008,.008,.008),4,"Antenna",16,8)
        mesh = bpy.data.meshes.new("PennantMesh")
        mesh.from_pydata([(.340,.071,1.444),(.452,.071,1.390),(.340,.071,1.391)], [], [(0,1,2)])
        mesh.materials.append(self.mat)
        flag = bpy.data.objects.new("LittleStatusFlag", mesh)
        bpy.context.collection.objects.link(flag)
        solid = flag.modifiers.new("ClothThickness", "SOLIDIFY")
        solid.thickness = .003
        self.bind(flag,2,"Antenna")
        self.box("RearSpoolMount", (0,.204,.758), (.239,.036,.248),3,bevel=.032)
        self.torus("LifebeltSpool", (0,.254,.768), .114,.019,0,"Spool")
        for radius in (.045,.055,.065,.075,.085,.095):
            self.torus("CopperCableCoil", (0,.247,.768), radius,.004,4,"Spool")
        self.cyl("SpoolHub", (0,.272,.768), .028,.036,4,"Spool",rotation=(math.pi/2,0,0))
        for angle in (0, math.pi/2, math.pi, 3*math.pi/2):
            x,z = math.sin(angle)*.112, .768+math.cos(angle)*.112
            self.box("SpoolClamp", (x,.276,z), (.039,.022,.049),1,"Spool",bevel=.008,rotation=(0,angle,0))
        self.box("RearServicePanel", (0,.190,.535), (.168,.018,.066),0,bevel=.022)
        rear_label = self.text("ReturnLabel", "RETURN IF LOST", (0,.202,.526), .014, 3)
        rear_label.rotation_euler.z = math.pi
        for s, side in ((-1,"L"),(1,"R")):
            upper, fore, hand = f"UpperArm.{side}",f"Forearm.{side}",f"Hand.{side}"
            shoulder = (s*.25,0,.91)
            elbow = (s*.365,-.018,.735)
            wrist = (s*.41,-.052,.568)
            palm = (s*.419,-.066,.514)
            self.bone(upper, shoulder, elbow, "Body")
            self.bone(fore, elbow, wrist, upper)
            self.bone(hand, wrist, (s*.429,-.068,.47), fore)
            self.bone(f"Socket_Grip.{side}", (s*.429,-.080,.49), (s*.429,-.13,.49),hand,False)
            self.cyl("ShoulderGasket", shoulder,.052,.037,3,upper,rotation=(0,math.pi/2,0))
            self.cyl("ShoulderRing", (s*.277,0,.91),.046,.015,1,upper,rotation=(0,math.pi/2,0))
            self.beam("UpperArmPiston", shoulder,elbow,.018,4,upper)
            self.beam("UpperArmCeramic", (s*.282,-.005,.864),(s*.343,-.015,.771),.026,0,upper)
            self.cyl("ElbowMechanism", elbow,.034,.052,3,fore,rotation=(0,math.pi/2,0))
            self.cyl("ElbowBrassPin", (s*.395,-.018,.735),.014,.008,4,fore,rotation=(0,math.pi/2,0),vertices=16)
            self.beam("ForearmPiston", elbow,wrist,.017,4,fore)
            self.beam("ForearmCuff", (s*.374,-.025,.699),(s*.405,-.048,.594),.028,0,fore)
            self.cyl("WristJoint", wrist,.026,.043,3,hand,rotation=(0,math.pi/2,0))
            self.box("PalmCeramic", palm,(.063,.063,.091),0,hand,bevel=.020)
            if self.detail >= 3:
                self.box("PalmRubberGrip",(palm[0],-.103,.516),(.055,.013,.060),3,hand,bevel=.014)
                for z in (.498,.515,.532):
                    self.box("PalmGripRib",(palm[0],-.111,z),(.041,.005,.004),3,hand,bevel=.002)
                self.cyl("WristLockCollar",wrist,.029,.016,4,hand,rotation=(0,math.pi/2,0))
                for start,end,r in ((shoulder,elbow,.027),(elbow,wrist,.028)):
                    a,b=Vector(start),Vector(end)
                    direction=(b-a).normalized()
                    for f in (.23,.78):
                        center=a.lerp(b,f)
                        obj=self.torus("SleeveSeal",center,r,.0025,3,upper if start==shoulder else fore,
                                       rotation=(0,0,0))
                        obj.rotation_mode="QUATERNION"
                        obj.rotation_quaternion=direction.to_track_quat("Z","Y")
            for finger, offset in enumerate((-.020,.019)):
                bone = f"Finger{finger+1}.{side}"
                p0=(s*.419+offset,-.071,.478)
                p1=(s*.419+offset,-.090,.423)
                self.bone(bone,p0,p1,hand)
                if self.detail >= 3:
                    mid=(p0[0],-.080,.450)
                    tip=f"Finger{finger+1}Tip.{side}"
                    self.bone(tip,mid,p1,bone)
                    self.beam("FingerProximalLink",p0,mid,.010,4,bone)
                    self.box("FingerArmour",(p0[0],-.073,.462),(.019,.019,.026),0,bone,bevel=.006)
                    self.cyl("FingerKnuckle",mid,.012,.022,3,tip,rotation=(0,math.pi/2,0),vertices=16,bevel=.002)
                    self.beam("FingerDistalLink",mid,p1,.009,4,tip)
                    self.box("TealFingertip",p1,(.020,.028,.028),1,tip,bevel=.007)
                else:
                    self.beam("FingerMechanism",p0,p1,.011,3,bone)
                    self.box("TealFingertip",(p1[0],p1[1],p1[2]),(.019,.026,.031),1,bone,bevel=.007)
            thumb=f"Thumb.{side}"
            self.bone(thumb,(s*.396,-.086,.52),(s*.378,-.12,.482),hand)
            self.beam("Thumb",(s*.396,-.086,.52),(s*.378,-.12,.482),.012,3,thumb)
            self.ball("ThumbTip",(s*.378,-.12,.482),(.014,.015,.018),1,thumb,20,10)
            thigh, shin, foot = f"Thigh.{side}",f"Shin.{side}",f"Foot.{side}"
            hip,knee,ankle=(s*.14,0,.46),(s*.17,-.018,.309),(s*.183,0,.165)
            self.bone(thigh,hip,knee,"Pelvis")
            self.bone(shin,knee,ankle,thigh)
            self.bone(foot,ankle,(s*.183,-.21,.09),shin)
            self.cyl("HipAxle",hip,.042,.061,3,thigh,rotation=(0,math.pi/2,0))
            self.beam("ThighPiston",hip,knee,.028,3,thigh)
            self.box("ThighCap",(s*.154,-.025,.401),(.055,.064,.094),0,thigh,bevel=.015)
            self.cyl("KneeJoint",knee,.041,.075,3,shin,rotation=(0,math.pi/2,0))
            self.cyl("KneeRivet",(s*.207,-.018,.309),.023,.013,4,shin,rotation=(0,math.pi/2,0))
            self.beam("ShinPiston",knee,ankle,.023,4,shin)
            self.box("ShinCover",(s*.177,-.029,.227),(.061,.046,.079),1,shin,bevel=.016)
            if self.detail >= 3:
                self.premium_boot(s,foot)
                continue
            self.box("BootSole",(s*.183,-.068,.027),(.214,.363,.043),3,foot,bevel=.030)
            self.box("MagneticBoot",(s*.183,-.055,.099),(.203,.330,.141),1,foot,bevel=.065)
            self.ball("BootVamp",(s*.183,-.071,.122),(.086,.126,.051),1,foot)
            self.box("BootToeBumper",(s*.183,-.235,.067),(.185,.020,.054),3,foot,bevel=.014)
            self.torus("AnkleSeal",(s*.183,0,.174),.042,.009,3,foot,rotation=(0,0,0))
            self.cyl("BootSideHinge",(s*.284,.020,.125),.023,.012,4,foot,rotation=(0,math.pi/2,0))
            for xoffset in (-.063,.063):
                for y in (-.182,.043):
                    self.cyl("MagneticContact",(s*.183+xoffset,y,.008),.021,.009,4,foot,vertices=16,bevel=.002)
            if self.detail >= 2:
                for y in (-.18,-.12,-.06,.0,.06):
                    self.box("SoleGroove",(s*.285,y,.025),(.012,.006,.028),4,foot,bevel=.001)
                self.box("BootStripe",(s*.183,-.225,.125),(.067,.009,.014),7,foot,bevel=.003)
        if self.detail >= 3:
            self.premium_details()
        return self

    def rig(self):
        arm_data = bpy.data.armatures.new("OOPS_Skeleton")
        arm = bpy.data.objects.new("OOPS_Rig", arm_data)
        bpy.context.collection.objects.link(arm)
        geo.select_only([arm])
        bpy.context.view_layer.objects.active = arm
        bpy.ops.object.mode_set(mode="EDIT")
        for name,(head,tail,parent,deform) in self.bones.items():
            bone = arm_data.edit_bones.new(name)
            bone.head, bone.tail = head, tail
            if parent:
                bone.parent = arm_data.edit_bones[parent]
            bone.use_deform = deform
        bpy.ops.object.mode_set(mode="OBJECT")
        arm.show_in_front = True
        arm_data.display_type = "STICK"
        for obj in self.parts:
            geo.select_only([obj])
            bpy.context.view_layer.objects.active = obj
            if obj.type != "MESH":
                bpy.ops.object.convert(target="MESH")
            for modifier in list(obj.modifiers):
                bpy.ops.object.modifier_apply(modifier=modifier.name)
            bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
            if obj.get("axm_project_target"):
                target=bpy.data.objects[obj["axm_project_target"]].evaluated_get(bpy.context.evaluated_depsgraph_get())
                for vertex in obj.data.vertices:
                    origin=vertex.co.copy()
                    origin.y=-2
                    found,position,normal,_=target.ray_cast(origin,Vector((0,1,0)))
                    if not found:
                        raise ValueError(f"decal projection missed {obj.name}")
                    vertex.co=position+normal*.0008
            if not obj.data.uv_layers:
                bpy.ops.object.mode_set(mode="EDIT")
                bpy.ops.mesh.select_all(action="SELECT")
                bpy.ops.uv.smart_project(island_margin=.02)
                bpy.ops.object.mode_set(mode="OBJECT")
            tile = int(obj["axm_palette"])
            for face in obj.data.polygons:
                face.material_index = 0
            # Separate placeholder slots survive joining; the unique bake uses
            # these palette IDs, not a shared-color UV lookup.
            if self.detail >= 3:
                obj.data.materials.clear()
                for palette_material in self.palette_materials:
                    obj.data.materials.append(palette_material)
                for face in obj.data.polygons:
                    face.material_index = tile
            for uv in obj.data.uv_layers.active.data:
                uv.uv.x = (tile % 4 + .08 + (uv.uv.x % 1.00001)*.84) / 4
                uv.uv.y = (tile // 4 + .08 + (uv.uv.y % 1.00001)*.84) / 2
            group = obj.vertex_groups.new(name=obj["axm_bone"])
            group.add(list(range(len(obj.data.vertices))), 1.0, "REPLACE")
        geo.select_only(self.parts)
        bpy.context.view_layer.objects.active = self.parts[0]
        bpy.ops.object.join()
        mesh = bpy.context.object
        mesh.name = "OOPS_Body_LOD0"
        # All palette regions share one PBR material and one draw-call primitive.
        if self.detail < 3:
            for polygon in mesh.data.polygons:
                polygon.material_index = 0
            mesh.data.materials.clear()
            mesh.data.materials.append(self.mat)
        mesh.parent = arm
        if self.detail>=3:
            triangulate_game_mesh(mesh)
        mod = mesh.modifiers.new("OOPS_RigidSkin", "ARMATURE")
        mod.object = arm
        arm["asset_id"] = "axm-oops"
        arm["forward_axis"] = "-Y in Blender; +Z in exported glTF"
        arm["binding"] = "Rigid mechanical skin; one bone influence per vertex"
        mesh["design"] = "Original AXM OOPS repair courier"
        return arm, mesh


def reset_pose(arm):
    for bone in arm.pose.bones:
        bone.rotation_mode = "XYZ"
        bone.rotation_euler = (0,0,0)
        bone.location = (0,0,0)
        bone.scale = (1,1,1)


def triangulate_game_mesh(mesh):
    """Freeze the tangent basis before baking/export, and reject invalid output."""
    geo.select_only([mesh])
    bpy.context.view_layer.objects.active=mesh
    mesh.data.validate(verbose=True,clean_customdata=False)
    tri=mesh.modifiers.new("PortableTriangleBasis","TRIANGULATE")
    if hasattr(tri,"keep_custom_normals"):
        tri.keep_custom_normals=True
    bpy.ops.object.modifier_apply(modifier=tri.name)
    repaired=mesh.data.validate(verbose=True,clean_customdata=False)
    mesh.data.update()
    if mesh.data.validate(clean_customdata=False):
        raise ValueError(f"invalid generated game mesh: {mesh.name}")
    print("OOPS_TRIANGLE_VALIDATION",mesh.name,"repaired",repaired,flush=True)


def aim_limb(arm, name, direction, influence):
    """Aim a rigid segment in world space without assuming its local bend axis."""
    bone = arm.pose.bones[name]
    rest_direction = (bone.bone.tail_local-bone.bone.head_local).normalized()
    target = rest_direction.lerp(Vector(direction).normalized(), influence).normalized()
    desired = rest_direction.rotation_difference(target) @ bone.bone.matrix_local.to_quaternion()
    bpy.context.view_layer.update()
    if bone.parent:
        rest_relative = bone.parent.bone.matrix_local.inverted() @ bone.bone.matrix_local
        basis = rest_relative.to_quaternion().inverted() @ bone.parent.matrix.to_quaternion().inverted() @ desired
    else:
        basis = bone.bone.matrix_local.to_quaternion().inverted() @ desired
    bone.rotation_euler = basis.to_euler("XYZ")
    bpy.context.view_layer.update()


def orient_world(arm, name, desired):
    """Set a world-space mechanical orientation with any parent bone basis."""
    bone=arm.pose.bones[name]
    bpy.context.view_layer.update()
    rest_relative=bone.parent.bone.matrix_local.inverted() @ bone.bone.matrix_local
    basis=rest_relative.to_quaternion().inverted() @ bone.parent.matrix.to_quaternion().inverted() @ desired
    bone.rotation_euler=basis.to_euler("XYZ")
    bpy.context.view_layer.update()


def solve_leg(arm, side, target):
    """Two rigid links, forward knee pole, and a level magnetic sole."""
    thigh,shin=arm.pose.bones[f"Thigh.{side}"],arm.pose.bones[f"Shin.{side}"]
    bpy.context.view_layer.update()
    hip=thigh.head.copy()
    delta=Vector(target)-hip
    distance=delta.length
    a,b=thigh.bone.length,shin.bone.length
    if not abs(a-b)+1e-5 < distance < a+b-1e-5:
        raise ValueError(f"unreachable {side} walk target: {distance} for {a}+{b}")
    axis=delta.normalized()
    along=(a*a-b*b+distance*distance)/(2*distance)
    height=math.sqrt(max(0,a*a-along*along))
    pole=Vector((0,-1,0))
    pole=(pole-axis*pole.dot(axis)).normalized()
    knee=hip+axis*along+pole*height
    aim_limb(arm,f"Thigh.{side}",knee-hip,1)
    aim_limb(arm,f"Shin.{side}",Vector(target)-knee,1)
    orient_world(arm,f"Foot.{side}",arm.data.bones[f"Foot.{side}"].matrix_local.to_quaternion())
def animate(arm, mesh):
    arm.animation_data_create()
    clips = []
    for name, end in (("Idle",61),("Walk_InPlace",33),("Wave",81),("Oops_Recover",81)):
        action = bpy.data.actions.new(name)
        action.use_fake_user = True
        arm.animation_data.action = action
        crafted="Finger1Tip.L" in arm.pose.bones
        for frame in sorted(set(list(range(1,end+1,1 if crafted else 4))+[end])):
            reset_pose(arm)
            t = (frame-1)/(end-1)
            phase = t * math.tau
            bones = arm.pose.bones
            if name == "Idle":
                bones["Body"].rotation_euler.y = .018*math.sin(phase)
                bones["Head"].rotation_euler.z = .05*math.sin(phase)
                bones["Brow.R"].rotation_euler.y = .09*math.sin(phase)
                bones["Antenna"].rotation_euler.x = .035*math.sin(phase+.2)
            elif name == "Walk_InPlace":
                bones["Pelvis"].location.y = -.050+.008*(1-math.cos(phase*2)) if crafted else .016*(1-math.cos(phase*2))
                if crafted:
                    bones["Pelvis"].location.x=-.010*math.sin(phase)
                bones["Body"].rotation_euler.z = .065*math.sin(phase)
                bones["Head"].rotation_euler.z = -.055*math.sin(phase)
                for s,side in ((1,"L"),(-1,"R")):
                    swing = s*math.sin(phase)
                    if crafted:
                        cycle=(t+(0 if side=="L" else .5))%1
                        if cycle<.5:
                            y=-.075+.30*cycle
                            lift=0
                        else:
                            u=(cycle-.5)*2
                            ease=u*u*(3-2*u)
                            y=.075-.15*ease
                            lift=.045*math.sin(math.pi*u)**2
                        solve_leg(arm,side,((-.183 if side=="L" else .183),y,.165+lift))
                    else:
                        bones[f"Thigh.{side}"].rotation_euler.x = .42*swing
                        bones[f"Shin.{side}"].rotation_euler.x = -.28*max(0,swing)
                        bones[f"Foot.{side}"].rotation_euler.x = -.15*swing
                    bones[f"UpperArm.{side}"].rotation_euler.x = -.27*swing
                bones["Antenna"].rotation_euler.x = .06*math.sin(phase)
            elif name == "Wave":
                envelope = math.sin(math.pi*t)**2
                aim_limb(arm,"UpperArm.R",(1,-.12,.6),envelope)
                aim_limb(arm,"Forearm.R",(.1,-.08,1),envelope)
                bones["Hand.R"].rotation_euler.z = .5*math.sin(phase*3)*envelope
                bones["Head"].rotation_euler.y = -.12*envelope
                bones["Brow.L"].location.y = .012*envelope
                if crafted:
                    for finger in (1,2):
                        bones[f"Finger{finger}Tip.R"].rotation_euler.x=.30*math.sin(phase*3+(finger-1)*.4)*envelope
                    bones["Eye.L"].rotation_euler.y=-.10*envelope
                    bones["Eye.R"].rotation_euler.y=-.10*envelope
            else:
                envelope = math.sin(math.pi*t)**2
                wobble = math.sin(phase*2)*envelope
                bones["Body"].rotation_euler.x = .17*envelope
                bones["Body"].rotation_euler.y = .15*wobble
                bones["Head"].rotation_euler.x = -.20*envelope
                bones["Head"].rotation_euler.y = -.22*wobble
                for s,side in ((-1,"L"),(1,"R")):
                    aim_limb(arm,f"UpperArm.{side}",(s*.7,-.8,.12),envelope)
                    aim_limb(arm,f"Forearm.{side}",(s*.35,-1,.2),envelope)
                    bones[f"Hand.{side}"].rotation_euler.z = s*.25*wobble
                bones["Antenna"].rotation_euler.y = .19*math.sin(phase*3)*envelope
                bones["Brow.L"].location.y = .016*envelope
                bones["Brow.R"].location.y = .013*envelope
            if name == "Walk_InPlace" and not crafted:
                # Solve vertical ground contact from the actual deformed soles.
                # Short mechanical legs otherwise lift both oversized boots at
                # mid-stride even when the numerical skin/export checks pass.
                bpy.context.view_layer.update()
                evaluated = mesh.evaluated_get(bpy.context.evaluated_depsgraph_get())
                posed_mesh = evaluated.to_mesh()
                lowest = min((evaluated.matrix_world @ vertex.co).z for vertex in posed_mesh.vertices)
                evaluated.to_mesh_clear()
                bones["Pelvis"].location.y += .0035-lowest
            for bone in bones:
                bone.keyframe_insert("rotation_euler",frame=frame,group=bone.name)
                bone.keyframe_insert("location",frame=frame,group=bone.name)
        clip={"name":name,"start_frame":1,"end_frame":end,"fps":30,"loop":name in {"Idle","Walk_InPlace"}}
        if name=="Walk_InPlace" and crafted:
            clip.update({"gait":"analytic two-link legs; level soles; 50 percent stance",
                         "stance_travel_m":.15,"matching_forward_speed_m_s":.28125})
        clips.append(clip)
    arm.animation_data.action = None
    reset_pose(arm)
    bpy.context.scene.frame_set(1)
    return clips


def export_glb(output, arm, mesh, name, animations=True):
    geo.select_only([arm,mesh])
    bpy.context.view_layer.objects.active = arm
    bpy.ops.export_scene.gltf(filepath=str(output/name), export_format="GLB", use_selection=True,
        export_apply=False, export_skins=True, export_def_bones=False, export_animations=animations,
        export_animation_mode="ACTIONS", export_merge_animation="ACTION", export_anim_slide_to_zero=True,
        export_force_sampling=True, export_yup=True, export_extras=True,
        export_tangents=True,
        export_cameras=False, export_lights=False, export_materials="EXPORT")


def studio(resolution):
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 24
    scene.cycles.use_denoising = True
    scene.render.resolution_x = resolution
    scene.render.resolution_y = resolution
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    if scene.world is None:
        scene.world = bpy.data.worlds.new("OOPS_StudioWorld")
    scene.world.use_nodes = True
    bg = scene.world.node_tree.nodes.get("Background")
    bg.inputs["Color"].default_value = (.17,.22,.27,1)
    bg.inputs["Strength"].default_value = .32
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.exposure = -.20
    ground_mat = bpy.data.materials.new("StudioGround")
    ground_mat.use_nodes = True
    ground_mat.node_tree.nodes.get("Principled BSDF").inputs["Base Color"].default_value = (.023,.039,.049,1)
    ground_mat.node_tree.nodes.get("Principled BSDF").inputs["Roughness"].default_value = .72
    geo.box("STUDIO_Ground",(0,0,-.045),(200,200,.08),ground_mat,bevel=0)
    for name, loc, power, size, color in (
        ("Key",(-2.5,-3.4,4.5),440,3.0,(1,.86,.71)),
        ("Fill",(2.3,-1.8,2.3),250,2.3,(.71,.85,1)),
        ("Rim",(.8,2.6,3.0),550,2.0,(.58,.92,1)),
    ):
        data = bpy.data.lights.new(name,"AREA")
        data.energy, data.shape, data.size, data.color = power,"DISK",size,color
        obj = bpy.data.objects.new(name,data)
        bpy.context.collection.objects.link(obj)
        obj.location = loc
        obj.rotation_euler = (Vector((0,0,.7))-obj.location).to_track_quat("-Z","Y").to_euler()
    bpy.ops.object.camera_add()
    camera = bpy.context.object
    camera.name = "STUDIO_Camera"
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 1.88
    scene.camera = camera
    return camera


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output",required=True)
    parser.add_argument("--resolution",type=int,default=960)
    parser.add_argument("--detail",type=int,default=2)
    parser.add_argument("--texture-resolution",type=int,default=2048)
    parser.add_argument("--no-render",action="store_true")
    args = parser.parse_args(sys.argv[sys.argv.index("--")+1:])
    output = Path(args.output).resolve()
    output.mkdir(parents=True,exist_ok=True)
    geo.clear_scene()
    bpy.context.scene.unit_settings.system = "METRIC"
    bpy.context.scene.unit_settings.scale_length = 1.0
    bpy.context.scene.render.fps = 30
    mat = atlas_material(output)
    character = Character(mat,args.detail).build()
    arm,mesh = character.rig()
    if args.detail >= 3:
        from axm_character_surfaces import bake_character
        mat = bake_character(mesh,output,PALETTE,args.texture_resolution)
    clips = animate(arm,mesh)
    exports = {}
    ratios=(("LOD0",1.0),("LOD1",.45),("LOD2",.15)) if args.detail>=3 else (("LOD0",1.0),("LOD1",.55),("LOD2",.26))
    for lod,ratio in ratios:
        target = mesh
        if ratio < 1:
            target = mesh.copy()
            target.data = mesh.data.copy()
            bpy.context.collection.objects.link(target)
            target.name = f"OOPS_Body_{lod}"
            # Collapse in bind pose before the armature modifier, retaining weights.
            target.modifiers.clear()
            geo.select_only([target])
            bpy.context.view_layer.objects.active = target
            decimate = target.modifiers.new("GameLOD","DECIMATE")
            decimate.ratio = ratio
            decimate.use_collapse_triangulate=True
            bpy.ops.object.modifier_apply(modifier=decimate.name)
            if args.detail>=3:
                triangulate_game_mesh(target)
            skin = target.modifiers.new("OOPS_RigidSkin","ARMATURE")
            skin.object = arm
        name = f"AXM_OOPS_{lod}.glb"
        if args.detail>=3:
            # A failed tangent calculation is an error, not an exporter warning
            # that silently drops a promised runtime attribute.
            target.data.calc_tangents(uvmap=target.data.uv_layers.active.name)
        export_glb(output,arm,target,name)
        target.data.calc_loop_triangles()
        exports[lod.lower()] = {"path":name,"sha256":digest(output/name),"triangles":len(target.data.loop_triangles)}
        if target != mesh:
            bpy.data.objects.remove(target,do_unlink=True)
    geo.select_only([arm,mesh])
    bpy.ops.export_scene.fbx(filepath=str(output/"AXM_OOPS.fbx"), use_selection=True,
        object_types={"ARMATURE","MESH"}, add_leaf_bones=False, use_armature_deform_only=False,
        bake_anim=True, bake_anim_use_all_actions=True, bake_anim_use_nla_strips=False,
        bake_anim_simplify_factor=0, path_mode="COPY", embed_textures=True,
        use_triangles=True, axis_forward="-Z", axis_up="Y")
    exports["fbx"] = {"path":"AXM_OOPS.fbx","sha256":digest(output/"AXM_OOPS.fbx")}
    # Some engine import paths consume one animation per FBX. Include reusable
    # skeleton-only takes as well as the convenient all-clips character FBX.
    animation_dir = output / "animations"
    animation_dir.mkdir(exist_ok=True)
    for clip in clips:
        action = bpy.data.actions[clip["name"]]
        arm.animation_data.action = action
        arm.animation_data.action_slot = action.slots[0]
        bpy.context.scene.frame_start = clip["start_frame"]
        bpy.context.scene.frame_end = clip["end_frame"]
        geo.select_only([arm])
        path = animation_dir / f"AXM_OOPS_{clip['name']}.fbx"
        bpy.ops.export_scene.fbx(filepath=str(path), use_selection=True, object_types={"ARMATURE"},
            add_leaf_bones=False, use_armature_deform_only=False, bake_anim=True,
            bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False,
            bake_anim_simplify_factor=0, axis_forward="-Z", axis_up="Y")
        clip["fbx"] = {"path":f"animations/{path.name}","sha256":digest(path)}
    arm.animation_data.action = None
    reset_pose(arm)
    bpy.context.scene.frame_set(1)
    # Gameplay collision is intentionally separate from the render/skin mesh.
    collision = geo.box("UCX_OOPS_BODY_00",(0,0,.72),(.61,.44,.59),mat,bevel=0)
    geo.select_only([collision])
    bpy.ops.export_scene.gltf(filepath=str(output/"AXM_OOPS_COLLISION.glb"),export_format="GLB",
        use_selection=True,export_animations=False,export_materials="NONE")
    bpy.data.objects.remove(collision,do_unlink=True)
    exports["collision"] = {"path":"AXM_OOPS_COLLISION.glb","sha256":digest(output/"AXM_OOPS_COLLISION.glb")}
    camera = studio(args.resolution)
    previews = []
    for angle in (() if args.no_render else (28,118,208,298)):
        radians = math.radians(angle)
        camera.location = (math.sin(radians)*3.8,-math.cos(radians)*3.8,1.93)
        camera.rotation_euler = (Vector((0,0,.73))-camera.location).to_track_quat("-Z","Y").to_euler()
        name=f"OOPS_view_{angle:03d}.png"
        bpy.context.scene.render.filepath=str(output/name)
        bpy.ops.render.render(write_still=True)
        previews.append({"angle_degrees":angle,"path":name,"sha256":digest(output/name)})
    reset_pose(arm)
    geo.select_only([arm])
    bpy.context.view_layer.objects.active=arm
    bpy.ops.wm.save_as_mainfile(filepath=str(output/"AXM_OOPS.blend"))
    save_json(output/"character-manifest.json",{
        "schema":"axm.rigged-character/v0.1","asset_id":"axm-oops","name":"OOPS",
        "original_design":True,"uniqueness_clearance":"NOT_AN_EXHAUSTIVE_SIMILARITY_OR_TRADEMARK_CHECK",
        "source":{"path":"AXM_OOPS.blend","sha256":digest(output/"AXM_OOPS.blend")},
        "exports":exports,"render_proofs":previews,"animations":clips,
        "bones":[{"name":name,"parent":spec[2],"deform":spec[3]} for name,spec in character.bones.items()],
        "materials":1,"atlas_size":[args.texture_resolution,args.texture_resolution] if args.detail>=3 else [1024,512],"meters_per_unit":1,
        "surface_workflow":"unique baked PBR" if args.detail>=3 else "shared palette atlas",
        "binding":"rigid-skinned mechanical character; no soft-tissue deformation",
        "collision":"separate box proxy; configure the gameplay capsule/controller per engine",
        "engine_compatibility":"portable exports; target-engine controller/retarget/import tuning still required",
        "detail_pass":args.detail,"renderer":"Cycles CPU, 24 samples with denoising",
    })
    print("OOPS_BUILD_COMPLETE",str(output),flush=True)


if __name__ == "__main__":
    main()
