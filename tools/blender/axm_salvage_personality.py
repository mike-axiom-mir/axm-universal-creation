"""Bounded found-object construction for inhabited miniature workshops.

These are editable meshes, not a raster makeover. Reuse the prop constructors
independently; the composition function owns their deliberate placement.
"""
import math
import bpy
from axm_blender_forge import box, cylinder, torus, cable, beam, sphere


def kettle(name, c, m, scale=1):
    x,y,z=c;s=scale
    sphere(name+' enamel body',(x,y,z+.13*s),(.16*s,.13*s,.14*s),m['yellow'],segments=24,rings=12)
    cylinder(name+' lid',(x,y,z+.25*s),.10*s,.025*s,m['iron'],vertices=24,bevel=.009*s)
    sphere(name+' lid knob',(x,y,z+.28*s),(.035*s,)*3,m['wood'],segments=12,rings=8)
    cable(name+' spout',[(x+.12*s,y,z+.10*s),(x+.23*s,y,z+.17*s),(x+.25*s,y,z+.25*s)],.034*s,m['yellow'])
    cable(name+' carry handle',[(x-.10*s,y,z+.20*s),(x-.11*s,y,z+.37*s),(x+.10*s,y,z+.37*s),(x+.10*s,y,z+.20*s)],.020*s,m['iron'])


def mug(name,c,m):
    x,y,z=c
    cylinder(name+' enamel',(x,y,z+.065),.055,.13,m['ivory'],vertices=20,bevel=.009)
    cylinder(name+' tea',(x,y,z+.132),.044,.003,m['wood'],vertices=20,bevel=0)
    torus(name+' handle',(x+.061,y,z+.073),.034,.009,m['ivory'],rotation=(math.pi/2,0,0),major_segments=16,minor_segments=6)


def salvage_grin(c,m,scale=1.0):
    """Large front-facing found-object emblem readable from RTS distance."""
    x,y,z=c;s=scale
    torus('front salvage grin ring',(x,y,z),.29*s,.040*s,m['yellow'],rotation=(math.pi/2,0,0),major_segments=32,minor_segments=8)
    sphere('front salvage grin left eye',(x-.105*s,y-.018*s,z+.085*s),(.033*s,.020*s,.040*s),m['black'],segments=12,rings=8)
    sphere('front salvage grin right eye',(x+.105*s,y-.018*s,z+.085*s),(.033*s,.020*s,.040*s),m['black'],segments=12,rings=8)
    cable('front salvage grin mouth',[(x-.14*s,y-.024*s,z-.055*s),(x-.08*s,y-.032*s,z-.12*s),(x,y-.035*s,z-.145*s),(x+.08*s,y-.032*s,z-.12*s),(x+.14*s,y-.024*s,z-.055*s)],.018*s,m['red'])
    for dx in [-.22,.22]:
        beam('front salvage grin bracket',(x+dx*s,y+.015*s,z-.23*s),(x+dx*s,y+.10*s,z-.34*s),.020*s,m['iron'],vertices=8)


def roof_wheel_vane(c,m,scale=1.0):
    """Crooked roof crown built from a reused wheel and scrap arrow."""
    x,y,z=c;s=scale
    beam('roof vane crooked mast',(x,y,z-.52*s),(x+.045*s,y+.015*s,z+.02*s),.032*s,m['iron'],vertices=10)
    torus('roof vane salvage wheel',(x+.04*s,y,z+.02*s),.27*s,.034*s,m['red'],rotation=(math.pi/2,0,0),major_segments=28,minor_segments=8)
    for a in [0,math.pi/2,math.pi,3*math.pi/2]:
        beam('roof vane wheel spoke',(x+.04*s,y,z+.02*s),(x+.04*s+.25*s*math.cos(a),y,z+.02*s+.25*s*math.sin(a)),.012*s,m['yellow'],vertices=8)
    beam('roof vane arrow shaft',(x-.34*s,y-.015*s,z+.02*s),(x+.45*s,y-.015*s,z+.02*s),.018*s,m['brass'],vertices=8)
    beam('roof vane arrow barb',(x+.45*s,y-.015*s,z+.02*s),(x+.31*s,y-.015*s,z+.14*s),.016*s,m['brass'],vertices=8)
    beam('roof vane arrow barb',(x+.45*s,y-.015*s,z+.02*s),(x+.31*s,y-.015*s,z-.10*s),.016*s,m['brass'],vertices=8)
    box('roof vane counterweight',(x-.40*s,y-.015*s,z+.02*s),(.13*s,.055*s,.11*s),m['teal'],rotation=(0,.12,0),bevel=.018*s)


def rear_trophy_rack(c,m,scale=1.0):
    """Asymmetric rear scrap trophy so the back has its own readable identity."""
    x,y,z=c;s=scale
    beam('rear trophy upper rail',(x-.42*s,y,z+.30*s),(x+.40*s,y,z+.22*s),.028*s,m['wood'],vertices=8)
    beam('rear trophy lower rail',(x-.36*s,y,z-.28*s),(x+.34*s,y,z-.21*s),.024*s,m['iron'],vertices=8)
    torus('rear trophy spare wheel',(x-.18*s,y-.02*s,z+.02*s),.25*s,.037*s,m['yellow'],rotation=(math.pi/2,0,0),major_segments=28,minor_segments=8)
    for a in [0,math.pi/2,math.pi,3*math.pi/2]:
        beam('rear trophy wheel spoke',(x-.18*s,y-.02*s,z+.02*s),(x-.18*s+.22*s*math.cos(a),y-.02*s,z+.02*s+.22*s*math.sin(a)),.011*s,m['rust'],vertices=8)
    box('rear trophy red plate',(x+.22*s,y-.03*s,z+.10*s),(.28*s,.045*s,.22*s),m['red'],rotation=(0,.16,0),bevel=.022*s)
    box('rear trophy blue plate',(x+.30*s,y-.035*s,z-.19*s),(.22*s,.040*s,.16*s),m['teal'],rotation=(0,-.20,0),bevel=.018*s)
    cable('rear trophy dangling strap',[(x+.34*s,y-.045*s,z+.34*s),(x+.40*s,y-.055*s,z+.02*s),(x+.36*s,y-.060*s,z-.31*s)],.014*s,m['rubber'])


def workshop_life(m):
    # A household kettle doubles as the workshop's essential machinery.
    kettle('tea engine',(1.20,-.08,1.22),m,1.0)
    mug('mechanic tea',(.61,-.54,1.215),m)
    # An old car door becomes a cupboard front underneath the workbench.
    box('reclaimed car door',(.99,-.42,.78),(.62,.07,.50),m['teal'],rotation=(0,.025,.03),bevel=.085)
    box('car door cream inset',(.99,-.465,.82),(.49,.025,.21),m['ivory'],bevel=.045)
    box('car door handle',(1.14,-.491,.92),(.12,.03,.025),m['steel'],bevel=.011)
    # Chunky temporary bracing gives an understandable hand-repaired silhouette.
    for x,sign in [(-2.1,1),(2.08,-1)]:
        beam('timber knee brace',(x,-.72,2.38),(x+.44*sign,-.72,2.92),.052,m['wood'],vertices=8)
    # An old wheel is the hoist's winch, attached to the existing roof bracket.
    torus('reused hoist wheel',(-.31,.86,3.88),.19,.031,m['red'],rotation=(math.pi/2,0,0),major_segments=28,minor_segments=8)
    for a in [0,math.tau/3,math.tau*2/3]:
        beam('winch spoke',(-.31,.86,3.88),(-.31+.18*math.cos(a),.86,3.88+.18*math.sin(a)),.013,m['iron'],vertices=8)
    cable('winch drop cable',[(-.31,.82,3.86),(-.22,.68,3.38),(-.12,.67,3.05)],.015,m['rubber'])
    # Repair history on the sign bay; broad straps remain readable when small.
    for x,z,angle in [(-1.92,1.0,.10),(-.76,2.85,-.15)]:
        box('mismatched repair strap',(x,-.865,z),(.25,.033,.075),m['yellow'],rotation=(0,angle,0),bevel=.014)
    # A stool on mismatched legs and a small round salvaged seat.
    x,y=1.83,-.65
    for dx,dy,h in [(-.11,-.09,.46),(.11,-.09,.46),(0,.12,.46)]:
        beam('stool reused leg',(x+dx*1.3,y+dy*1.3,.26),(x+dx,y+dy,.26+h),.025,m['wood'],vertices=8)
    cylinder('stool hubcap seat',(x,y,.73),.19,.07,m['red'],vertices=28,bevel=.023)

    # Profession Fabric Live Job 001: large personality anchors instead of
    # another blanket micro-detail pass. These are deliberately simple,
    # editable found-object constructions that must still be visually reviewed
    # from fresh GLB imports before any direction-success claim is made.
    salvage_grin((1.42,-.87,2.55),m,1.0)
    roof_wheel_vane((.10,.40,4.43),m,1.0)
    rear_trophy_rack((-1.22,1.69,2.08),m,1.0)

    # Local task illumination, separate from studio lighting, accompanies export
    # as named practical-light metadata. It is not baked into albedo textures.
    data=bpy.data.lights.new('workbench warm task spill','POINT')
    data.energy=95;data.color=(1,.52,.20);data.shadow_soft_size=.30
    light=bpy.data.objects.new('workbench warm task spill',data)
    bpy.context.collection.objects.link(light);light.location=(.70,.23,2.33)
