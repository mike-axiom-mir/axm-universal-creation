"""Single-reference AXM salvage hero: authored geometry, skin and clip export.

The reference is an art-direction input, not a projected billboard. Hidden
surfaces are authored interpretations. This is a bounded character recipe.
Run with the provisioned bpy Python runtime, --output NEW_DIRECTORY.
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
import axm_blender_forge as geo
from axm_salvage_construction import mesh as make_mesh
from axm_salvage_surfaces import pbr_material, solid
from axm_hero_surfaces import surface

TAU = math.tau
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'


class Hero:
    def __init__(self, output):
        self.output = output
        self.parts = []
        self.bones = {}
        self.current = 'Chest'
        self.rng = random.Random(471)
        self.mat = {}
        for name, color, kind in [
            ('yellow','#e5ad32','metal'),('ivory','#e1d6ba','metal'),
            ('teal','#397d87','metal'),('steel','#89928d','steel'),
            ('iron','#30373d','steel'),('brass','#b68c45','metal'),
            ('red','#b83c35','cloth'),('leather','#644233','leather'),
            ('rubber','#252b30','rubber'),('fur','#efe5d0','fur')]:
            self.mat[name] = surface(output/'textures', 'Hero_'+name,color,kind,1024)
        for name,color,metal,rough,emit in [
            ('white','#ffeed9',0,.28,0),('mouth','#241219',0,.9,0),
            ('skin','#e7a792',0,.56,0),('tongue','#cf6468',0,.44,0),
            ('hair','#362b26',0,.8,0),('iris','#aa6327',.1,.22,0),
            ('pupil','#120e0b',0,.1,0),('lens','#062a36',.45,.15,0),
            ('cyan','#49e5ff',.1,.22,3),('heart','#ff5c83',0,.35,2.2),
            ('ink','#252d32',0,.8,0),('duck','#ffc12f',0,.3,0),
            ('orange','#e5792c',0,.48,0)]:
            self.mat[name]=solid('Hero_'+name,color,metal,rough,emit)

    def bind(self, ob, bone=None):
        ob['axm_bone'] = bone or self.current
        self.parts.append(ob)
        return ob

    def ball(self,n,c,r,m='ivory',bone=None,segments=24,rings=16):
        return self.bind(geo.sphere(n,c,r,self.mat[m],segments=segments,rings=rings),bone)

    def box(self,n,c,d,m='ivory',bevel=.012,rot=(0,0,0),bone=None):
        return self.bind(geo.box(n,c,d,self.mat[m],bevel=bevel,segments=3,rotation=rot),bone)

    def cyl(self,n,c,r,d,m='iron',axis=(0,0,1),v=24,bone=None):
        ob=geo.cylinder(n,c,r,d,self.mat[m],vertices=v,bevel=min(.004,r*.12))
        ob.rotation_mode='QUATERNION';ob.rotation_quaternion=Vector(axis).to_track_quat('Z','Y')
        return self.bind(ob,bone)

    def ring(self,n,c,r,t,m='steel',axis=(0,-1,0),bone=None):
        ob=geo.torus(n,c,r,t,self.mat[m],major_segments=32,minor_segments=8)
        ob.rotation_mode='QUATERNION';ob.rotation_quaternion=Vector(axis).to_track_quat('Z','Y')
        return self.bind(ob,bone)

    def beam(self,n,a,b,r,m='steel',bone=None):
        a,b=Vector(a),Vector(b)
        return self.cyl(n,(a+b)/2,r,(b-a).length,m,b-a,bone=bone)

    def line(self,n,pts,r,m='iron',bone=None):
        ob=geo.cable(n,pts,r,self.mat[m]);ob.data.resolution_u=5
        ob.data.bevel_resolution=2
        return self.bind(ob,bone)

    def mesh(self,n,vs,fs,m,bone=None,uv=None,smooth=True):
        return self.bind(make_mesh(n,vs,fs,self.mat[m],uv,smooth),bone)

    def text(self,n,t,c,size,m='ink',bone=None,rot=(math.pi/2,0,0)):
        cu=bpy.data.curves.new(n,'FONT');cu.body=t;cu.size=size;cu.align_x='CENTER'
        cu.align_y='CENTER';cu.space_line=1.05;cu.extrude=.0004;cu.resolution_u=3
        cu.font=bpy.data.fonts.load(FONT,check_existing=True)
        ob=bpy.data.objects.new(n,cu);bpy.context.collection.objects.link(ob)
        ob.location=c;ob.rotation_euler=rot;cu.materials.append(self.mat[m])
        return self.bind(ob,bone)

    def bolt(self,n,c,r=.009,axis=(0,-1,0),bone=None):
        self.cyl(n,c,r,.009,'steel',axis,6,bone)
        # A real recessed slot reads under side lighting.
        if tuple(axis)==(0,-1,0):
            self.box(n+' slot',(c[0],c[1]-.005,c[2]),(r*1.2,.0015,r*.16),'iron',.0005,bone=bone)

    def logo(self,n,c,size,m='ivory',bone=None):
        x,y,z=c
        # Angular AXM mark from the reference, with the stepped central notch.
        pts=[(-.48,-.40),(-.12,.48),(.08,.10),(.35,.43),(.49,-.34),(.25,-.34),(.16,.02),(-.06,-.18),(-.16,.09),(-.25,-.40)]
        vs=[(x+a*size,y,z+b*size) for a,b in pts]
        ob=self.mesh(n,vs,[tuple(range(len(vs)))],m,bone,smooth=False)
        so=ob.modifiers.new('Emblem thickness','SOLIDIFY');so.thickness=size*.08
        be=ob.modifiers.new('Emblem rim','BEVEL');be.width=.002;be.segments=2
        return ob

    def plate(self,n,c,d,m='ivory',label=None,size=.024,bone=None):
        self.box(n,c,d,'iron',min(d)*.15,bone=bone)
        self.box(n+' enamel',(c[0],c[1]-.010,c[2]),(d[0]*.93,d[1],d[2]*.94),m,min(d)*.12,bone=bone)
        for sx in [-1,1]:
            for sz in [-1,1]:
                self.bolt(n+' rivet',(c[0]+sx*d[0]*.39,c[1]-d[1]/2-.014,c[2]+sz*d[2]*.40),.007,bone=bone)
        if label:self.text(n+' words',label,(c[0],c[1]-d[1]/2-.017,c[2]),size,bone=bone)

    def bone(self,n,h,t,p=None):self.bones[n]=(h,t,p)

    def skeleton(self):
        self.bone('Root',(0,0,0),(0,0,.15))
        self.bone('Pelvis',(0,0,.89),(0,0,1.02),'Root')
        self.bone('Chest',(0,0,1.02),(0,0,1.42),'Pelvis')
        self.bone('Head',(0,0,1.43),(0,0,1.90),'Chest')
        self.bone('Jaw',(0,-.03,1.51),(0,-.03,1.38),'Head')
        for name,x in [('Eye',-.155),('Brow.L',.19),('Brow.R',-.155)]:
            z=1.78 if name=='Eye' else 1.885
            self.bone(name,(x,-.30,z),(x,-.30,z+.045),'Head')
        for name in ['LidUpper','LidLower']:
            self.bone(name,(-.155,-.294,1.78),(-.155,-.294,1.83),'Head')
        self.bone('Tongue',(0,-.30,1.395),(0,-.36,1.395),'Jaw')
        self.bone('Antenna',(.07,.02,2.01),(.09,.02,2.20),'Head')
        self.bone('Cape.01',(0,.19,1.41),(0,.25,1.11),'Chest')
        self.bone('Cape.02',(0,.25,1.11),(0,.34,.81),'Cape.01')
        self.bone('Cape.03',(0,.34,.81),(0,.39,.52),'Cape.02')
        self.bone('Charm',(-.10,-.28,1.00),(-.10,-.28,.87),'Pelvis')
        self.bone('ScarfTail',(.22,.03,1.39),(.31,.15,1.17),'Chest')
        for s,side in [(-1,'R'),(1,'L')]:
            self.bone('Thigh.'+side,(s*.23,0,.91),(s*.27,-.07,.57),'Pelvis')
            self.bone('Shin.'+side,(s*.27,-.07,.57),(s*.28,0,.20),'Thigh.'+side)
            self.bone('Foot.'+side,(s*.28,0,.20),(s*.28,-.25,.14),'Shin.'+side)
            self.bone('UpperArm.'+side,(s*.40,0,1.36),(s*.57,0,1.15),'Chest')
            self.bone('Forearm.'+side,(s*.57,0,1.15),(s*.65,-.03,.96),'UpperArm.'+side)
            self.bone('Hand.'+side,(s*.65,-.03,.96),(s*.66,-.07,.84),'Forearm.'+side)
            self.bone('Socket_Grip.'+side,(s*.65,-.08,.94),(s*.65,-.08,1.05),'Hand.'+side)
            for i,dx in enumerate([-.068,-.023,.023,.068]):
                x=s*.65+dx
                self.bone(f'Finger{i}.01.{side}',(x,-.10,.945),(x,-.11,.879),'Hand.'+side)
                self.bone(f'Finger{i}.02.{side}',(x,-.11,.879),(x,-.055,.86),f'Finger{i}.01.{side}')
            self.bone('Thumb.'+side,(s*.55,-.07,.94),(s*.54,-.12,1.035),'Hand.'+side)
        self.bone('Tool',(-.65,-.08,.96),(-.65,-.08,1.37),'Socket_Grip.R')

    def body(self):
        self.current='Pelvis'
        self.ball('Padded pelvis',(0,0,.94),(.26,.21,.18),'leather')
        self.ring('Utility belt',(0,0,1.00),.275,.037,'leather',axis=(0,0,1))
        for x in [-.20,0,.20]:
            self.plate('Belt buckle',(x,-.229,1.02),(.06,.035,.066),'brass')
        self.current='Chest'
        self.ball('Barrel torso padded underlayer',(0,0,1.21),(.315,.235,.275),'leather',segments=40,rings=24)
        self.ball('Curved yellow breastplate',(0,-.055,1.21),(.302,.228,.233),'yellow',segments=40,rings=24)
        for s in [-1,1]:
            self.line('Harness leather',[(s*.21,-.11,1.42),(s*.20,-.225,1.33),(s*.23,-.265,1.15),(s*.26,-.18,1.02)],.026,'leather')
            self.plate('Harness silver buckle',(s*.205,-.242,1.30),(.078,.025,.078),'steel')
            self.line('Harness stitch',[(s*.226,-.255,1.27),(s*.239,-.277,1.15)],.002,'ivory')
        self.plate('Bad ideas better results',(.065,-.294,1.095),(.185,.024,.225),'ivory','BAD\nIDEAS\nBETTER\nRESULTS',.027)
        self.logo('Chest AXM raised emblem',(.04,-.291,1.327),.155,'steel')
        self.plate('Grin pouch',(-.177,-.285,1.16),(.11,.06,.102),'red')
        self.smile((- .177,-.326,1.166),.031)
        for x in [-.115,-.24]:
            self.beam('Belt spanner handle',(x,-.304,1.14),(x+.015,-.315,1.28),.010,'brass')
            self.ring('Belt spanner jaw',(x+.015,-.315,1.29),.023,.006,'steel')
        for s in [-1,1]:
            self.plate('Side utility pouch',(s*.293,-.08,1.10),(.12,.14,.17),'leather')
            self.line('Shoulder power hose',[(s*.27,.09,1.42),(s*.37,.13,1.28),(s*.30,.20,1.08)],.018,'iron')
        # Back view is a complete authored design, with retained cape above it.
        self.box('Backpack frame',(0,.215,1.24),(.38,.17,.35),'iron',.04)
        self.plate('Back panel',(0,.316,1.28),(.31,.025,.22),'yellow',bone='Chest')
        for x in [-.11,.11]:
            self.cyl('Back fuel tank',(x,.28,1.21),.062,.32,'teal')
            for z in [1.09,1.30]:self.ring('Tank retaining band',(x,.28,z),.063,.01,'steel',axis=(0,0,1))
        self.current='Pelvis'
        self.cyl('Duck fuel bottle',(-.37,-.04,.90),.065,.29,'ivory')
        self.cyl('Fuel bottle cap',(-.37,-.04,1.065),.041,.04,'iron')
        self.text('Bottle joke','DUCK\nFUELS\nBRAVER\nIDEAS',(-.37,-.107,.905),.021)
        self.line('Bottle clip',[(-.34,-.01,1.07),(-.30,-.10,1.12)],.014,'steel')
        self.ring('Spare tape',(.36,-.04,.94),.075,.024,'red')
        self.ring('Tape cardboard',(.36,-.042,.94),.046,.01,'ivory')
        self.current='Charm'
        self.line('Duck charm chain',[(-.10,-.29,1.015),(-.10,-.32,.96),(-.10,-.32,.93)],.004,'brass')
        self.duck((-.10,-.335,.885),.95)

    def smile(self,c,r,bone=None):
        x,y,z=c
        self.cyl('Hand painted smile disk',c,r,.002,'ivory',(0,-1,0),32,bone)
        for dx in [-.32,.32]:self.ball('Smile eye',(x+dx*r,y-.003,z+.17*r),(.06*r,.003,.13*r),'ink',bone,12,8)
        self.line('Smile curve',[(x+math.cos(a)*r*.55,y-.004,z+math.sin(a)*r*.55) for a in [math.pi+i*math.pi/12 for i in range(13)]],r*.07,'ink',bone)

    def duck(self,c,scale=1,bone=None):
        x,y,z=c;s=scale
        self.ball('Rubber duck body',(x,y,z),(.045*s,.035*s,.030*s),'duck',bone)
        self.ball('Rubber duck head',(x,y-.008*s,z+.034*s),(.026*s,.023*s,.026*s),'duck',bone)
        self.ball('Rubber duck bill',(x,y-.033*s,z+.029*s),(.024*s,.023*s,.009*s),'orange',bone)
        for dx in [-.012,.012]:self.ball('Duck eye',(x+dx*s,y-.029*s,z+.044*s),(.004*s,.003*s,.005*s),'pupil',bone,12,8)

    def legs(self):
        for s,side in [(-1,'R'),(1,'L')]:
            self.current='Thigh.'+side
            self.beam('Hip mechanical linkage',(s*.23,0,.91),(s*.27,-.07,.57),.084,'iron')
            self.ball('Upper leg leather',(s*.245,-.025,.79),(.121,.123,.149),'leather')
            self.ball('Thigh patch shell',(s*.25,-.104,.80),(.105,.081,.115),'yellow' if s<0 else 'ivory')
            self.current='Shin.'+side
            self.ball('Knee ball',(s*.27,-.07,.57),(.119,.11,.11),'iron')
            self.ball('Asymmetric kneecap',(s*.27,-.146,.594),(.122,.069,.114),'yellow' if s<0 else 'ivory')
            if s<0:
                self.smile((s*.27,-.216,.62),.038)
                self.text('Squeak knee','SQUEAK!',(s*.27,-.218,.558),.025)
            else:self.logo('Knee AXM',(s*.27,-.215,.597),.11,'iron')
            for dx in [-.078,.078]:self.bolt('Knee fastener',(s*.27+dx,-.196,.66),.008)
            self.beam('Shin piston',(s*.27,-.055,.53),(s*.28,0,.235),.065,'steel')
            for z in [.275,.32,.36]:self.ring('Shin bellows',(s*.28,-.007,z),.069,.010,'iron',axis=(0,0,1))
            self.ball('Shin armour',(s*.28,-.077,.365),(.117,.075,.15),'yellow' if s<0 else 'ivory')
            self.plate('Ankle square lock',(s*.28,-.153,.272),(.09,.025,.065),'steel')
            for xx in [s*.28-.09,s*.28+.09]:self.cyl('Ankle bearing',(xx,0,.20),.060,.023,'brass',(1,0,0))
            self.current='Foot.'+side
            self.boot(side,s)

    def boot(self,side,s):
        x=s*.28
        # Cross-section loft: deep chunky toe, narrow heel and an arched instep.
        sections=[(.17,.26,.105,.17),(.12,.35,.137,.235),(-.04,.405,.181,.325),(-.25,.43,.145,.26),(-.38,.36,.108,.18),(-.41,.26,.091,.135)]
        vs=[];n=32
        for y,w,z,h in sections:
            for i in range(n):
                a=TAU*i/n;c,q=math.cos(a),math.sin(a)
                vs.append((x+w*.5*math.copysign(abs(c)**.62,c),y,z+h*.5*math.copysign(abs(q)**.70,q)))
        fs=[tuple(reversed(range(n))),tuple((len(sections)-1)*n+i for i in range(n))]
        for row in range(len(sections)-1):
            for i in range(n):j=(i+1)%n;fs.append((row*n+i,row*n+j,(row+1)*n+j,(row+1)*n+i))
        self.mesh('Sculpted boot '+side,vs,fs,'yellow' if s<0 else 'teal')
        self.box('Rubber sole',(x,-.115,.037),(.424,.57,.066),'rubber',.04)
        self.box('Heavy toe cap',(x,-.345,.129),(.40,.139,.18),'iron',.04)
        for j,y in enumerate([-.28,-.18,-.08,.025,.11]):
            for dx in [-.115,.115]:
                self.box('Ground tread',(x+dx,y,.018),(.134,.055,.030),'rubber',.007,rot=(0,0,.18*(-1 if dx<0 else 1)))
        for y,z in [(-.14,.30),(.015,.343)]:
            self.box('Instep leather strap',(x,y,z),(.34,.050,.028),'leather',.009)
            self.plate('Steel strap clasp',(x+.065,y-.015,z+.016),(.07,.035,.050),'steel')
        for dx in [-.145,.145]:self.bolt('Toe cap anchor',(x+dx,-.415,.17),.011)
        self.logo('Boot insignia',(x-.058,-.420,.149),.047,'ivory')

    def arms(self):
        for s,side in [(-1,'R'),(1,'L')]:
            self.current='UpperArm.'+side
            self.ball('Shoulder articulation',(s*.40,0,1.36),(.13,.14,.13),'iron')
            self.ball('Shoulder armour',(s*.438,-.026,1.355),(.153,.145,.143),'yellow' if s<0 else 'ivory')
            self.cyl('Shoulder hub',(s*.542,0,1.36),.074,.025,'brass',(s,0,0))
            self.ring('Shoulder seal',(s*.555,0,1.36),.051,.011,'iron',axis=(s,0,0))
            self.beam('Upper arm cylinder',(s*.44,0,1.30),(s*.57,0,1.15),.077,'leather')
            self.ball('Elbow exposed joint',(s*.57,0,1.15),(.093,.09,.084),'iron')
            self.current='Forearm.'+side
            self.beam('Forearm inner piston',(s*.57,0,1.15),(s*.65,-.03,.96),.078,'steel')
            self.ball('Bulky forearm ivory armour',(s*.61,-.035,1.065),(.144,.133,.169),'ivory')
            self.ball('Forearm yellow side panel',(s*.69,-.019,1.09),(.074,.126,.13),'yellow')
            self.ring('Wrist retaining seal',(s*.65,-.03,.957),.095,.018,'iron',axis=(s*.35,-.1,-1))
            for dz in [-.04,.04]:
                for dx in [-.068,.068]:self.bolt('Forearm panel fastener',(s*.61+dx,-.151,1.09+dz),.010)
            self.line('Forearm hydraulic cable',[(s*.53,.077,1.19),(s*.56,.119,1.06),(s*.64,.082,.95)],.013,'iron')
            self.current='Hand.'+side
            self.ball('Glove palm',(s*.65,-.035,.91),(.118,.082,.10),'rubber')
            self.ball('Glove backplate',(s*.65,.024,.932),(.10,.05,.082),'yellow')
            for i,dx in enumerate([-.068,-.023,.023,.068]):
                self.current=f'Finger{i}.01.{side}';x=s*.65+dx
                self.beam('Finger padded segment',(x,-.10,.945),(x,-.11,.879),.025,'rubber')
                self.ball('Finger ivory knuckle',(x,-.126,.931),(.020,.025,.026),'ivory',segments=16,rings=10)
                self.current=f'Finger{i}.02.{side}'
                self.beam('Curled finger tip',(x,-.11,.879),(x,-.055,.86),.023,'rubber')
                self.ball('Finger end cap',(x,-.076,.853),(.02,.028,.02),'ivory',segments=16,rings=10)
            self.current='Thumb.'+side
            self.beam('Thumb glove',(s*.55,-.07,.94),(s*.54,-.12,1.015),.034,'rubber')
            self.ball('Exposed thumb tip',(s*.54,-.132,1.04),(.032,.032,.037),'skin',segments=24,rings=16)

    def head(self):
        self.current='Head'
        head=self.ball('Cream face',(0,-.005,1.699),(.362,.263,.331),'fur',segments=64,rings=40)
        # True mouth cavity; it is not a smile painted on a solid sphere.
        cut=geo.sphere('Mouth cutting volume',(0,-.238,1.477),(.245,.216,.111),self.mat['mouth'],segments=64,rings=32)
        geo.select_only([head]);bpy.context.view_layer.objects.active=head
        boolean=head.modifiers.new('Open mouth sculpt','BOOLEAN');boolean.operation='DIFFERENCE';boolean.object=cut
        bpy.ops.object.modifier_apply(modifier=boolean.name);bpy.data.objects.remove(cut,do_unlink=True)
        self.ball('Dark mouth interior',(0,-.163,1.477),(.236,.144,.108),'mouth',segments=48,rings=32)
        self.current='Jaw'
        self.ball('Soft smiling chin',(0,-.200,1.375),(.219,.106,.073),'fur',segments=48,rings=24)
        self.line('Lower smile lip',[(-.214,-.258,1.49),(-.17,-.307,1.404),(0,-.330,1.38),(.17,-.307,1.404),(.214,-.258,1.49)],.009,'skin')
        self.ball('Tongue',(0,-.307,1.406),(.088,.078,.032),'tongue','Tongue')
        self.line('Tongue crease',[(0,-.386,1.409),(0,-.339,1.425),(0,-.31,1.428)],.002,'skin','Tongue')
        for x in [-.135,-.082,.082,.135]:self.box('Lower tooth',(x,-.293,1.409),(.042,.042,.028),'white',.010)
        self.current='Head'
        self.line('Upper smiling muzzle',[(-.225,-.232,1.584),(-.18,-.292,1.586),(0,-.329,1.572),(.18,-.292,1.586),(.225,-.232,1.584)],.012,'fur')
        for i,x in enumerate([-.18,-.13,-.078,-.026,.027,.079,.13,.18]):
            y=-.322+.09*(abs(x)/.20)**2
            self.box('Big upper grin tooth',(x,y,1.548+abs(x)*.065),(.048,.044,.049-(abs(x)*.05)),'white',.012,rot=(0,x*.3,-x*.45))
        self.ball('Peach nose',(0,-.302,1.658),(.056,.052,.035),'skin',segments=32,rings=16)
        for x in [-.026,.026]:self.ball('Nostril',(x,-.344,1.652),(.009,.007,.005),'mouth',segments=12,rings=8)
        for s in [-1,1]:
            self.ball('Cheek',(s*.247,-.159,1.612),(.083,.077,.095),'fur')
            self.ball('Warm cheek',(s*.257,-.214,1.618),(.04,.019,.032),'skin')
        # One huge clear expressive eye, the other replaced by the cyan optic.
        self.ball('Right eye socket',(-.155,-.216,1.78),(.142,.115,.157),'hair',segments=40,rings=24)
        self.ball('Right eye white',(-.155,-.277,1.78),(.119,.083,.136),'white',segments=40,rings=24)
        self.ball('Brown iris',(-.145,-.356,1.775),(.061,.015,.065),'iris','Eye',40,20)
        for i in range(42):
            a=TAU*i/42;r=.047
            self.line('Iris radial fleck',[(-.145+math.cos(a)*r*.64,-.371,1.775+math.sin(a)*r*.69),(-.145+math.cos(a)*r,-.367,1.775+math.sin(a)*r)],.0012,'brass','Eye')
        self.ball('Eye pupil',(-.145,-.373,1.775),(.033,.010,.038),'pupil','Eye',32,16)
        self.ball('Eye glint',(-.163,-.382,1.798),(.012,.005,.013),'white','Eye',16,10)
        for upper in [True,False]:
            vs=[];fs=[];n=28;rows=9
            for j in range(rows+1):
                a=(j/rows)*(math.pi/2)
                for i in range(n+1):
                    t=TAU*i/n
                    vs.append((-.155+.122*math.sin(a)*math.cos(t),-.277+.088*math.sin(a)*math.sin(t),1.78+(1 if upper else -1)*.138*math.cos(a)))
            for j in range(rows):
                for i in range(n):q=j*(n+1)+i;fs.append((q,q+1,q+n+2,q+n+1))
            self.mesh('Articulated eyelid',vs,fs,'fur','LidUpper' if upper else 'LidLower')
        self.cyl('Monocle backing',(.18,-.228,1.77),.146,.079,'iron',(0,-1,0),48)
        self.ring('Monocle outer metal rim',(.18,-.279,1.77),.131,.017,'steel')
        self.ring('Monocle brass trim',(.18,-.291,1.77),.115,.006,'brass')
        self.cyl('Glassy blue monocle',(.18,-.294,1.77),.111,.021,'lens',(0,-1,0),48)
        self.ring('Cyan optic ring',(.18,-.307,1.77),.102,.004,'cyan')
        self.logo('Cyan AXM optic',(.18,-.311,1.773),.126,'cyan')
        for i in range(8):
            a=TAU*i/8;self.bolt('Optic rim screw',(.18+.129*math.cos(a),-.297,1.77+.129*math.sin(a)),.006)
        for s,side in [(-1,'R'),(1,'L')]:
            self.cyl('Headphone leather cushion',(s*.346,.005,1.74),.15,.067,'leather',(s,0,0),40)
            self.cyl('Headphone brass casing',(s*.384,.005,1.74),.128,.04,'brass',(s,0,0),40)
            self.cyl('Headphone yellow insert',(s*.412,.005,1.74),.099,.019,'yellow',(s,0,0),32)
            self.ring('Headphone seal',(s*.42,.005,1.74),.066,.012,'iron',axis=(s,0,0))
            for i in range(6):
                a=TAU*i/6;self.bolt('Headphone screw',(s*.428,.105*math.cos(a),1.74+.105*math.sin(a)),.007,axis=(s,0,0))
        self.line('Leather aviator headband',[(-.36,.05,1.78),(-.30,.025,1.93),(0,.033,2.031),(.30,.025,1.93),(.36,.05,1.78)],.042,'leather')
        for x in [-.145,.16]:
            self.cyl('Raised goggle leather',(x,-.071,2.004),.108,.048,'leather',(0,-.38,1),40)
            self.ring('Raised goggle brass',(x,-.084,2.033),.098,.015,'brass',axis=(0,-.38,1))
            self.cyl('Raised goggle glass',(x,-.084,2.033),.084,.009,'lens',(0,-.38,1),40)
        self.line('Goggle bridge',[(-.043,-.075,2.026),(.0,-.082,2.029),(.055,-.073,2.026)],.014,'steel')
        # Asymmetric eyebrows and swept locks are tapered actual volumes.
        self.tapered('Arched left-view brow',[(-.29,-.219,1.89),(-.24,-.298,1.96),(-.13,-.324,1.985),(-.053,-.31,1.915)], [.005,.03,.042,.005],'hair','Brow.R')
        self.tapered('Determined optic brow',[(.072,-.276,1.88),(.14,-.282,1.916),(.23,-.255,1.957),(.302,-.20,1.929)],[.007,.029,.036,.003],'hair','Brow.L')
        for j in range(5):
            self.tapered('Swept quiff',[(-.08+j*.035,-.07,2.009),(-.15+j*.03,-.10,2.08),(-.20+j*.027,-.11,2.093)], [.036,.027,.001],'hair','Head')
        self.plate('Cheek bandage',(-.27,-.244,1.635),(.076,.008,.025),'ivory',bone='Head')
        self.box('Crossed bandage',(-.27,-.249,1.635),(.025,.008,.073),'skin',.006,rot=(0,.33,0))
        self.fuzz()
        self.current='Antenna'
        self.beam('Heart antenna spring',(.07,.02,2.006),(.09,.02,2.145),.009,'steel')
        for z in [2.04,2.063,2.086]:self.ring('Antenna coil',(.075,.02,z),.017,.004,'brass',axis=(0,0,1))
        rows=['01100110','11111111','11111111','01111110','00111100','00011000']
        for j,row in enumerate(rows):
            for i,c in enumerate(row):
                if c=='1':self.box('Pixel heart',(.09+(i-3.5)*.016,.012,2.25-j*.016),(.014,.011,.014),'heart',.001)

    def tapered(self,n,points,radii,m,bone=None):
        control=[Vector(p) for p in points];dense=[];widths=[]
        for j in range(len(control)-1):
            a,b,c,d=control[max(j-1,0)],control[j],control[j+1],control[min(j+2,len(control)-1)]
            for k in range(7):
                t=k/7
                dense.append(.5*((2*b)+(-a+c)*t+(2*a-5*b+4*c-d)*t*t+(-a+3*b-3*c+d)*t*t*t))
                widths.append(radii[j]*(1-t)+radii[j+1]*t)
        dense.append(control[-1]);widths.append(radii[-1])
        vs=[];fs=[];points=dense;radii=widths;count=10
        for j,(p,r) in enumerate(zip(points,radii)):
            tangent=(points[min(j+1,len(points)-1)]-points[max(j-1,0)]).normalized()
            x=tangent.cross(Vector((0,1,0))).normalized();y=tangent.cross(x).normalized()
            for i in range(count):vs.append(tuple(p+r*(math.cos(TAU*i/count)*x+math.sin(TAU*i/count)*y)))
        for j in range(len(points)-1):
            for i in range(count):k=(i+1)%count;fs.append((j*count+i,j*count+k,(j+1)*count+k,(j+1)*count+i))
        fs+=[tuple(reversed(range(count))),tuple((len(points)-1)*count+i for i in range(count))]
        return self.mesh(n,vs,fs,m,bone)

    def fuzz(self):
        # Short, opaque mesh tufts avoid an engine-specific hair system.
        vs=[];fs=[];rng=random.Random(1000471)
        for i in range(2200):
            a=rng.uniform(0,TAU);z=rng.uniform(-1,1);q=math.sqrt(1-z*z)
            v=Vector((q*math.cos(a),q*math.sin(a),z))
            p=Vector((v.x*.363,v.y*.264-.005,1.699+v.z*.332))
            # Protect the face's expression and the mouth opening.
            if p.y<-.10 and ((abs(p.x)<.28 and p.z<1.65) or (abs(p.x)<.32 and 1.65<p.z<1.95)):continue
            if p.z>1.98:continue
            tangent=v.cross(Vector((0,0,1))).normalized()
            if tangent.length<.1:continue
            r=rng.uniform(.0018,.0033);l=rng.uniform(.004,.011)
            base=len(vs);tip=p+v*l+Vector((0,0,-.002))
            vs.extend([tuple(p-tangent*r),tuple(p+tangent*r),tuple(tip),tuple(p-v.cross(tangent)*r)])
            fs.extend([(base,base+1,base+2),(base+1,base+3,base+2),(base+3,base,base+2)])
        self.mesh('Short sculpted cream fur',vs,fs,'fur','Head')

    def cloth(self):
        self.current='Chest'
        for j in range(3):
            self.line('Folded red scarf',[(-.28,0,1.44-j*.016),(-.22,-.19,1.425-j*.018),(0,-.245,1.40-j*.022),(.22,-.19,1.435-j*.016),(.29,.04,1.45-j*.016)],.036,'red')
        self.ball('Scarf knot',(.257,-.13,1.421),(.06,.05,.045),'red')
        self.tapered('Scarf short tail',[(.26,-.11,1.40),(.32,-.09,1.29),(.31,-.04,1.20)],[.04,.037,.008],'red','ScarfTail')
        n,m=28,28;vs=[];uv=[];fs=[]
        for j in range(m+1):
            v=j/m;w=.28+.23*v
            for i in range(n+1):
                u=i/n;x=(u-.5)*2*w
                z=1.405-v*.83+.018*math.sin(u*21+v*4)*v
                if j==m:z+=.02*math.sin(i*2.7)+.015*(i%3)
                y=.215+.21*v+.034*math.cos(u*math.pi*8)*v
                vs.append((x,y,z));uv.append((u,1-v))
        for j in range(m):
            for i in range(n):
                # Small tears at the bottom of an otherwise continuous cape.
                if j>m-3 and i in [3,4,19,25]:continue
                q=j*(n+1)+i;fs.append((q,q+n+1,q+n+2,q+1))
        ob=self.mesh('Weighted red survivor cape',vs,fs,'red','Cape.01',uv)
        ob['axm_cape']=True
        so=ob.modifiers.new('Cape cloth thickness','SOLIDIFY');so.thickness=.003
        # Rear emblem is attached to the same smoothly weighted cloth.
        ob=self.logo('Cape AXM applique',(0,.445,.96),.43,'ivory','Cape.02');ob['axm_cape']=True
        for s in [-1,1]:self.bolt('Cape collar clasp',(s*.21,-.167,1.423),.017,bone='Chest')

    def wrench(self):
        self.current='Tool';x,y=-.65,-.08
        self.box('Oversized wrench shaft',(x,y,1.15),(.053,.045,.51),'steel',.013)
        for z in [.88,.91,.94,.97,1.00]:self.ring('Wrench rubber grip',(x,y,z),.037,.008,'rubber',axis=(0,0,1))
        self.ring('Wrench hanging eye',(x,y,.85),.035,.015,'steel')
        self.plate('Wrench yellow badge',(x,y-.007,1.405),(.15,.048,.148),'yellow')
        self.logo('Wrench maker mark',(x,y-.037,1.41),.082,'ink')
        # Open jaw profile: silhouette matters more than adding noise.
        outline=[(-.12,1.405),(-.18,1.56),(-.13,1.65),(-.067,1.68),(-.06,1.555),(.052,1.555),(.095,1.655),(.14,1.607),(.155,1.48),(.078,1.404)]
        vs=[(x+a,y+d,z) for d in [-.03,.03] for a,z in outline];n=len(outline)
        fs=[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
        ob=self.mesh('Open crescent wrench jaw',vs,fs,'steel',smooth=False)
        b=ob.modifiers.new('Forged jaw bevel','BEVEL');b.width=.009;b.segments=3
        for z in [1.235,1.29]:self.bolt('Wrench adjuster',(x,y-.032,z),.022)

    def build(self):
        self.skeleton();self.body();self.legs();self.arms();self.head();self.cloth();self.wrench()
        from axm_hero_detail import upgrade
        upgrade(self)
        return self


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True)
    p.add_argument('--resolution',type=int,default=1000)
    args=p.parse_args();out=args.output.resolve()
    if out.exists():raise SystemExit('Choose a new output directory; approved assets are not overwritten.')
    out.mkdir(parents=True);bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.unit_settings.system='METRIC';bpy.context.scene.render.fps=30
    hero=Hero(out).build()
    from axm_hero_motion import rig, animate, export, preview
    arm,mesh=rig(hero)
    clips=animate(arm,mesh)
    export(hero,arm,mesh,clips,out)
    preview(out,args.resolution,clip='Idle_Relaxed',frame=1)
    print('HERO_COMPLETE',out,flush=True)


if __name__=='__main__':main()
