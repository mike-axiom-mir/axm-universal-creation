"""Authored vehicle reconstruction from the AXM vehicle concept plate.

Source-visible features are encoded as geometry. Hidden surfaces are inferred.
No claim of exact image reconstruction or automatic visual acceptance.
"""
import argparse,json,math,hashlib,sys
from pathlib import Path
import bpy
from mathutils import Vector
from axm_blender_forge import box,cylinder,torus,beam,cable,sphere,cone,select_only,export_glb
from axm_salvage_construction import mesh,cloth,barrel,crate,physically_scaled_uv
from axm_rts_workshop import materials,convert_and_batch,clean_mesh,setup_render,point
from axm_salvage_surfaces import solid

IDS=['push-cart','utility-hauler','scrap-buggy','scout-trike','flatbed-convoy-truck','armored-bus','tow-crawler','crane-truck','drill-rig-vehicle','cargo-trailer','field-ambulance-van','mercenary-carrier']


def badge(c,r,m,side=False):
    # Enamel smile marker, oriented on a vehicle door or hanging flag.
    x,y,z=c;rot=(0,math.pi/2,0) if side else (math.pi/2,0,0)
    cylinder('yellow smile panel',c,r,.014,m['yellow'],rotation=rot,vertices=40,bevel=.005)
    def p(u,v):return (x+.012,y+u,z+v) if side else (x+u,y-.012,z+v)
    for u in [-.30*r,.30*r]:sphere('smile eye',p(u,.22*r),(.023,.018,.032),m['black'],segments=10,rings=6)
    cable('painted smile',[p(.56*r*math.cos(a),-.04*r-.48*r*math.sin(a)) for a in [i*math.pi/16 for i in range(17)]],.014,m['black'])


def wheel(c,m,r=.47,w=.28):
    x,y,z=c
    torus('rounded offroad tire',c,r*.74,r*.26,m['rubber'],rotation=(0,math.pi/2,0),major_segments=40,minor_segments=12)
    cylinder('recessed steel wheel',c,r*.54,w*.75,m['iron'],rotation=(0,math.pi/2,0),vertices=32,bevel=.017)
    for side in [-1,1]:
        xx=x+side*w*.43
        torus('wheel rim lip',(xx,y,z),r*.50,.018,m['steel'],rotation=(0,math.pi/2,0),major_segments=32,minor_segments=6)
        cylinder('axle hub',(xx,y,z),r*.17,.035,m['rust'],rotation=(0,math.pi/2,0),vertices=16,bevel=.009)
        for j in range(8):
            a=j*math.tau/8
            cylinder('wheel lug',(xx+side*.025,y+r*.28*math.sin(a),z+r*.28*math.cos(a)),.018,.025,m['steel'],rotation=(0,math.pi/2,0),vertices=6,bevel=.001)
    for j in range(28):
        a=j*math.tau/28
        for side in [-1,1]:
            box('chevron tire tread',(x+side*w*.23,y+r*.97*math.sin(a),z+r*.97*math.cos(a)),(w*.53,.11,.042),m['rubber'],rotation=(-a,side*.13,side*.23),bevel=.009,segments=2)


def lamp(c,m,r=.105):
    x,y,z=c
    cylinder('round headlight housing',c,r,.15,m['iron'],rotation=(math.pi/2,0,0),vertices=28,bevel=.012)
    torus('headlight brass bezel',(x,y-.081,z),r*.90,.015,m['brass'],rotation=(math.pi/2,0,0),major_segments=28,minor_segments=6)
    cylinder('headlight warm lens',(x,y-.087,z),r*.78,.015,m['emission'],rotation=(math.pi/2,0,0),vertices=28,bevel=.009)


def flag(c,m):
    x,y,z=c
    beam('leaning flag pole',(x,y,z),(x+.13,y,z+.88),.016,m['wood'],vertices=8)
    cloth('tarp smile flag',[(x+.12,y,z+.85),(x+.65,y,z+.79),(x+.10,y,z+.43),(x+.61,y,z+.39)],m['yellow'],sag=.015,flutter=.02,subdivisions=(16,12))
    badge((x+.36,y-.024,z+.62),.14,m)


def cargo(c,m,large=False):
    x,y,z=c
    crate('bound luggage crate',(x,y,z),m,w=.66,d=.44,h=.38)
    for dx in [-.21,.21]:cable('cargo straps',[(x+dx,y-.25,z+.02),(x+dx,y-.25,z+.42),(x+dx,y+.25,z+.42),(x+dx,y+.25,z+.02)],.017,m['iron'])
    if large:barrel('supply drum',(x+.56,y,z),m,'red',r=.18,h=.52)


def chassis(m,length,width,axles):
    for x in [-width*.33,width*.33]:box('long chassis rail',(x,.15,.61),(.09,length,.13),m['iron'],bevel=.015)
    for y in axles:
        beam('drive axle',(-width*.60,y,.47),(width*.60,y,.47),.065,m['iron'],vertices=16)
        for x in [-width*.59,width*.59]:wheel((x,y,.47),m)
    box('floor pan',(0,.15,.78),(width*.94,length,.085),m['iron'],bevel=.025)


def tracks(m):
    """Crawler running gear: continuous links around six rollers per side."""
    for s in [-1,1]:
        x=s*.89
        for y in [-1.12,-.68,-.23,.23,.68,1.12]:
            cylinder('crawler road roller',(x,y,.43),.24,.25,m['iron'],rotation=(0,math.pi/2,0),vertices=24,bevel=.014)
            torus('roller rim',(x+s*.14,y,.43),.17,.018,m['steel'],rotation=(0,math.pi/2,0),major_segments=20,minor_segments=6)
        path=[]
        for j in range(16):path.append((-1.12+j*2.24/16,.74,0))
        for j in range(12):
            a=j*math.pi/12;path.append((1.12+.31*math.sin(a),.43+.31*math.cos(a),-a))
        for j in range(16):path.append((1.12-j*2.24/16,.12,math.pi))
        for j in range(12):
            a=math.pi+j*math.pi/12;path.append((-1.12+.31*math.sin(a),.43+.31*math.cos(a),-a))
        for y,z,a in path:box('individual crawler track link',(x,y,z),(.40,.145,.075),m['iron'],rotation=(a,0,0),bevel=.012,segments=2)
    box('tracked chassis deck',(0,0,.86),(1.65,3.15,.18),m['iron'],bevel=.035)


def cabin(m,front=-1.5,width=1.65,cream=True):
    # Distinct compact cab-over silhouette: raked windscreen, rounded roof,
    # cream door, exposed bumper and tall front radiator.
    y=front;paint=m['ivory' if cream else 'teal']
    box('cab lower body',(0,y+.48,1.02),(width,1.20,.53),m['teal'],bevel=.10)
    box('cab rear wall',(0,y+1.03,1.60),(width,.08,1.24),m['teal'],bevel=.03)
    box('cab roof',(0,y+.47,2.30),(width+.04,1.18,.12),paint,bevel=.055)
    box('windscreen lower cowl',(0,y+.035,1.65),(width,.15,.19),paint,bevel=.055)
    box('short sloped bonnet',(0,y-.025,1.48),(width*.83,.40,.16),m['teal'],rotation=(.10,0,0),bevel=.05)
    for x in [-width*.48,0,width*.48]:beam('windshield vertical frame',(x,y-.025,1.74),(x,y+.045,2.25),.023,m['steel'],vertices=10)
    for z in [1.74,2.25]:beam('windshield horizontal frame',(-width*.48,y-.018,z),(width*.48,y-.018,z),.025,m['steel'],vertices=10)
    for s in [-1,1]:
        xx=s*width*.5
        box('cream door',(xx,y+.52,1.34),(.065,.98,.67),paint,bevel=.06)
        box('door handle',(xx+s*.047,y+.84,1.56),(.025,.16,.035),m['iron'],bevel=.01)
        for yy in [y+.04,y+1.02]:beam('cab window pillar',(xx,yy,1.65),(xx,yy+.08 if yy<y+.2 else yy,2.26),.034,m['iron'],vertices=10)
        # Actual dark glass panels; no untextured bright squares.
        box('side window glass',(xx,y+.51,1.99),(.018,.83,.49),m['window'],bevel=.035)
        beam('side window sill',(xx,y+.04,1.71),(xx,y+1.02,1.71),.022,m['steel'],vertices=8)
        beam('wing mirror arm',(xx,y+.06,1.86),(xx+s*.23,y-.04,1.94),.019,m['iron'],vertices=8)
        box('wing mirror',(xx+s*.24,y-.04,1.99),(.07,.10,.22),m['iron'],bevel=.04)
        box('cab step',(xx,y+.52,.71),(.24,.62,.08),m['steel'],bevel=.017)
        if s==1:badge((xx+.043,y+.49,1.34),.25,m,True)
    for x in [-width*.25,width*.25]:
        box('raked windshield',(x,y+.006,1.99),(width*.44,.022,.49),m['window'],rotation=(math.radians(-8),0,0),bevel=.035)
        beam('windshield wiper',(x,y-.035,1.77),(x+.16,y-.06,2.07),.010,m['iron'],vertices=6)
    box('front grille panel',(0,y-.13,1.21),(width*.48,.13,.67),m['iron'],bevel=.05)
    for x in [i*width*.045 for i in range(-4,5)]:box('radiator grille slat',(x,y-.205,1.21),(.018,.021,.55),m['steel'],bevel=.002)
    for x in [-width*.38,width*.38]:lamp((x,y-.16,1.16),m,.12)
    box('heavy front bumper',(0,y-.27,.82),(width+.18,.15,.16),m['iron'],bevel=.035)
    for x in [-width*.39,width*.39]:box('bumper upright',(x,y-.30,1.02),(.08,.11,.47),m['brass'],bevel=.016)
    for x in [-.37,0,.37]:lamp((x,y+.10,2.42),m,.06)
    # Stout exhaust and beacon are explicit reference cues.
    cylinder('rear exhaust',(width*.57,y+.99,1.71),.063,1.35,m['iron'],vertices=20,bevel=.008)
    cylinder('amber beacon base',(width*.35,y+.7,2.45),.09,.08,m['iron'],vertices=20,bevel=.01)
    cylinder('amber beacon',(width*.35,y+.7,2.56),.07,.15,m['emission'],vertices=20,bevel=.025)


def crane(m,rear=1.0,tow=False):
    # Angled articulated boom and hanging hook; no rectangular upright gantry.
    cylinder('crane turntable',(0,rear,1.0),.35,.22,m['iron'],vertices=24,bevel=.025)
    a=(0,rear,1.1);b=(0,rear+.42,2.55);c=(0,rear+1.52,3.14)
    for s in [-1,1]:
        x=s*.12
        beam('lower crane boom',(x,a[1],a[2]),(x,b[1],b[2]),.095,m['yellow'],vertices=4)
        beam('upper crane boom',(x,b[1],b[2]),(x,c[1],c[2]),.074,m['yellow'],vertices=4)
    beam('chrome hydraulic ram',(0,rear+.12,1.25),(0,rear+.64,2.54),.039,m['steel'],vertices=16)
    for pt in [b,c]:cylinder('boom pivot',pt,.11,.37,m['iron'],rotation=(0,math.pi/2,0),vertices=20,bevel=.014)
    cable('crane lifting cable',[c,(0,c[1],2.23)],.014,m['iron'])
    cable('crane hook',[(0,c[1],2.25),(.12,c[1],2.08),(.09,c[1],1.98),(-.07,c[1],1.99),(-.12,c[1],2.10)],.033,m['steel'])


def vehicle_fittings(m,key,front,length,width,axles):
    # Reference-specific construction density: guards, winch, tanks, fasteners,
    # mirrors, suspension, loading straps and roof rack; all actual geometry.
    for side in [-1,1]:
        x=side*(width/2+.07)
        for yy in axles:
            cable('arched wheel fender',[(x,yy-.58,.65),(x,yy-.50,.98),(x,yy-.24,1.12),(x,yy+.27,1.12),(x,yy+.52,.93)],.07,m['teal'])
            for j in range(5):box('leaf suspension spring',(x*.72,yy,.40+j*.022),(.055,.76-j*.08,.023),m['iron'],bevel=.008)
        for yy in [front+.20,front+.98]:
            for zz in [1.13,1.53]:cylinder('cab door hinge bolt',(x,yy,zz),.024,.022,m['brass'],rotation=(0,math.pi/2,0),vertices=6,bevel=.002)
        cylinder('underbody fuel tank',(x*.84,.25,.65),.17,.72,m['steel'],rotation=(math.pi/2,0,0),vertices=24,bevel=.04)
        for yy in [.0,.5]:torus('tank retaining band',(x*.84,yy,.65),.174,.018,m['iron'],rotation=(math.pi/2,0,0),major_segments=24,minor_segments=8)
        box('cab lower mudflap',(x,front+.98,.47),(.24,.05,.37),m['rubber'],bevel=.014)
        beam('roof luggage rail',(side*.72,front+.20,2.48),(side*.72,front+.99,2.48),.023,m['iron'])
    for yy in [front+.22,front+.94]:beam('roof luggage rack',(-.73,yy,2.48),(.73,yy,2.48),.025,m['iron'])
    cylinder('front recovery winch',(0,front-.33,.92),.12,.51,m['iron'],rotation=(0,math.pi/2,0),vertices=24,bevel=.018)
    for j in range(12):torus('winch cable winding',(-.22+j*.04,front-.33,.92),.124,.009,m['steel'],rotation=(0,math.pi/2,0),major_segments=20,minor_segments=6)
    for x in [-.61,.61]:torus('front tow shackle',(x,front-.38,.79),.068,.018,m['yellow'],rotation=(math.pi/2,0,0),major_segments=20,minor_segments=8)
    # Guard rails wrap around the lights without replacing their round outline.
    cable('tubular brush guard',[(-.81,front-.36,.80),(-.81,front-.36,1.35),(-.40,front-.36,1.38),(-.40,front-.36,.84)],.025,m['brass'])
    cable('other brush guard',[(.81,front-.36,.80),(.81,front-.36,1.35),(.40,front-.36,1.38),(.40,front-.36,.84)],.025,m['brass'])
    cylinder('air cleaner behind cab',(-.94,front+1.05,1.45),.12,.64,m['steel'],vertices=24,bevel=.03)
    for j in range(7):torus('air cleaner ribs',(-.94,front+1.05,1.23+j*.055),.124,.012,m['iron'],major_segments=20,minor_segments=6)
    cable('air intake pipe',[(-.94,front+1.05,1.1),(-.95,front+.6,.95),(-.68,front+.6,.91)],.045,m['rubber'])
    if key in ['utility-hauler','flatbed-convoy-truck','tow-crawler','crane-truck','drill-rig-vehicle']:
        rear=length/2
        barrel('red strapped fuel barrel',(-.53,rear-.32,.91),m,'red',r=.19,h=.61)
        crate('stacked expedition supplies',(.37,rear-.43,.91),m,w=.59,d=.50,h=.43)
        crate('smaller upper tool box',(.38,rear-.43,1.34),m,w=.42,d=.39,h=.30)
        cylinder('rolled cargo blanket',(-.1,rear-.54,1.74),.14,.73,m['tarp'],rotation=(0,math.pi/2,0),vertices=24,bevel=.03)
        for x in [-.33,.16]:torus('blanket leather band',(x,rear-.54,1.74),.143,.018,m['wood'],rotation=(0,math.pi/2,0),major_segments=24,minor_segments=6)
        for x in [-.58,.56]:cable('cargo rope tie',[(x,rear-.85,.94),(x,rear-.72,1.57),(x,rear-.26,1.65),(x,rear-.08,.97)],.013,m['wood'])


def truck(key,m):
    long=key in ['flatbed-convoy-truck','crane-truck','drill-rig-vehicle','cargo-trailer','armored-bus','mercenary-carrier']
    length=4.7 if long else 3.6;width=1.66;front=-length*.5
    axles=[front+.58,length*.5-.50]
    if long:axles.insert(1,length*.5-1.48)
    if key=='tow-crawler':tracks(m)
    else:chassis(m,length,width,axles)
    if key=='cargo-trailer':
        for x in [-.8,.8]:box('trailer sideboard',(x,.15,1.12),(.08,length,.62),m['teal'],bevel=.03)
        for y in [-1.7,-.6,.6,1.8]:
            cable('trailer bowed canopy rib',[(-.84,y,1.38),(-.87,y,2.25),(0,y,2.55),(.87,y,2.25),(.84,y,1.38)],.035,m['iron'])
        cloth('tarp trailer crown',[(-.95,-2,2.38),(.95,-2,2.38),(-.95,2.25,2.38),(.95,2.25,2.38)],m['tarp'],sag=-.2,flutter=.04)
        for x in [-.92,.92]:
            cloth('tarp trailer side',[(x,-2,2.37),(x,2.25,2.37),(x,-2,1.05),(x,2.25,1.05)],m['tarp'],sag=.06,flutter=.045)
        badge((.95,0,1.75),.42,m,True);cargo((0,0,.87),m,True);return
    cabin(m,front,width)
    vehicle_fittings(m,key,front,length,width,axles)
    deck_front=front+1.3;rear=length*.5
    if key in ['armored-bus','mercenary-carrier','field-ambulance-van']:
        ambulance=key=='field-ambulance-van';zroof=2.40
        box('rear passenger body',(0,(deck_front+rear)/2,1.33),(width,rear-deck_front,.90),m['ivory' if ambulance else 'teal'],bevel=.075)
        box('rounded passenger roof',(0,(deck_front+rear)/2,zroof),(width+.10,rear-deck_front+.05,.20),m['ivory'],bevel=.10)
        n=2 if ambulance else 5
        for s in [-1,1]:
            xx=s*.845
            if ambulance:
                box('ambulance upper box',(xx,(deck_front+rear)/2,1.99),(.08,rear-deck_front,.78),m['ivory'],bevel=.04)
                box('medical red cross upright',(xx+s*.05,(deck_front+rear)/2,1.98),(.022,.19,.58),m['red'],bevel=.012)
                box('medical red cross crossbar',(xx+s*.05,(deck_front+rear)/2,1.98),(.023,.55,.19),m['red'],bevel=.012)
            else:
                for j in range(n):
                    yy=deck_front+(j+.5)*(rear-deck_front)/n
                    box('passenger window',(xx,yy,2.00),(.025,(rear-deck_front)/n-.07,.43),m['window'],bevel=.045)
                    for dy in [-.5,.5]:beam('passenger window trim',(xx,yy+dy*((rear-deck_front)/n-.05),1.74),(xx,yy+dy*((rear-deck_front)/n-.05),2.28),.024,m['brass'],vertices=8)
            for j in range(4):box('mismatched lower door patch',(xx+s*.02,deck_front+(j+.5)*(rear-deck_front)/4,1.25),(.04,.40,.45),m[['teal','ivory','red','blue'][j]],bevel=.018)
        for yy in [deck_front+.3,rear-.4]:cargo((-.3,yy,2.53),m)
        for xx in [-.9,.9]:beam('roof rack side',(xx,deck_front,2.61),(xx,rear,2.61),.027,m['iron'],vertices=10)
        if key=='mercenary-carrier':
            cylinder('turret mount',(0,.65,2.65),.33,.15,m['iron'],vertices=24,bevel=.02)
            box('roof turret',(0,.65,2.87),(.57,.57,.33),m['teal'],bevel=.075)
            beam('turret barrel',(0,.43,2.9),(0,-.65,2.9),.055,m['iron'],vertices=20)
            for xx in [-.75,-.4,0,.4,.75]:beam('front cage bar',(xx,front-.36,.85),(xx,front-.26,2.46),.028,m['iron'],vertices=8)
        return
    for x in [-.84,.84]:
        box('patched flatbed side',(x,(deck_front+rear)/2,1.10),(.07,rear-deck_front,.46),m['teal'],bevel=.028)
        beam('flatbed upper rail',(x,deck_front,1.37),(x,rear,1.37),.035,m['brass'],vertices=10)
        for j in range(4):box('bed upright',(x,deck_front+j*(rear-deck_front)/3,1.15),(.045,.05,.65),m['iron'],bevel=.01)
    if key in ['crane-truck','tow-crawler']:crane(m,deck_front+.60,key=='tow-crawler')
    elif key=='drill-rig-vehicle':
        for x in [-.27,.27]:beam('drill mast',(x,.65,1),(x,.65,3.6),.055,m['yellow'],vertices=8)
        for z in [1.2,1.7,2.2,2.7,3.2]:beam('drill mast rung',(-.27,.65,z),(.27,.65,z),.023,m['iron'],vertices=8)
        cylinder('drill shaft',(0,.65,1.82),.13,2.8,m['steel'],vertices=24,bevel=.01)
        for j in range(9):torus('drill cutting flights',(0,.65,.31+j*.13),.23,.038,m['iron'],major_segments=24,minor_segments=6)
    else:
        cargo((-.30,deck_front+.45,.86),m,True)
        cargo((.18,rear-.48,.86),m)
        if key=='flatbed-convoy-truck':
            cloth('tarp over bound cargo',[(-.72,-.45,1.86),(.70,-.45,1.90),(-.72,.8,1.45),(.70,.8,1.40)],m['tarp'],sag=.14,flutter=.035)
            for x in [-.6,.6]:cable('load lashings',[(x,-.5,.95),(x,-.5,1.97),(x,.86,1.49),(x,.86,.92)],.018,m['wood'])
    flag((.65,rear-.1,1.30),m)


def buggy(m,trike=False):
    if trike:
        chassis(m,2.6,1.10,[.90])
        wheel((0,-1.05,.47),m,.47,.26)
        for x in [-.14,.14]:beam('motorcycle front fork',(x,-1.04,.46),(x,-.67,1.38),.032,m['steel'],vertices=14)
        cable('handlebars',[(-.43,-.70,1.42),(-.35,-.82,1.46),(.35,-.82,1.46),(.43,-.70,1.42)],.025,m['iron'])
        box('motorcycle saddle',(0,.05,1.18),(.50,.78,.17),m['rubber'],bevel=.12)
        sphere('round fuel tank',(0,-.48,1.08),(.29,.40,.31),m['ivory'],segments=28,rings=16)
        lamp((0,-.94,1.3),m,.16);cargo((-.17,.70,.88),m,True);badge((.31,-.44,1.11),.17,m,True);return
    chassis(m,2.75,1.35,[-.96,1.00])
    # Distinct skeletal dune buggy: sloped nose, wide tires, no truck cab.
    for s in [-1,1]:
        x=s*.66
        cable('roll cage side',[(x,-.68,.80),(x,-.46,1.34),(x,-.02,1.92),(x,.83,1.94),(x,1.27,.87)],.035,m['iron'])
        box('salvaged buggy door',(x,.44,.99),(.045,.93,.43),m['ivory'],rotation=(0,0,s*.04),bevel=.025)
        for j in range(3):box('door rust repair',(x+s*.03,.12+j*.22,1.02),(.02,.12,.22),m['rust'],rotation=(.15*j,0,0),bevel=.01)
        for yy in [-.96,1.0]:
            beam('suspension wishbone',(s*.35,yy,.60),(s*.79,yy,.47),.033,m['steel'],vertices=10)
            beam('suspension spring core',(s*.61,yy,.51),(s*.57,yy,.94),.03,m['yellow'],vertices=12)
            for j in range(6):torus('coil spring',(s*.59,yy,.56+j*.056),.068,.013,m['iron'],major_segments=16,minor_segments=6)
    for y,z in [(-.02,1.92),(.83,1.94),(-.6,1.27)]:beam('roll cage crossbar',(-.66,y,z),(.66,y,z),.036,m['iron'],vertices=12)
    for x in [-.32,.32]:
        box('bucket seat cushion',(x,.34,.89),(.50,.54,.15),m['rubber'],bevel=.10)
        box('bucket seat back',(x,.66,1.22),(.49,.16,.64),m['rubber'],rotation=(math.radians(-10),0,0),bevel=.10)
        cable('seat harness',[(x-.13,.52,1.49),(x-.13,.22,.94),(x+.13,.22,.94),(x+.13,.52,1.49)],.026,m['wood'])
    box('sloping buggy nose',(0,-.97,.88),(.83,.70,.13),m['iron'],rotation=(math.radians(12),0,0),bevel=.055)
    for x in [-.56,.56]:lamp((x,-1.17,1.12),m,.135)
    for x in [-.32,.32]:lamp((x,-.08,2.08),m,.105)
    cable('yellow tubular bull bar',[(-.64,-1.52,.60),(-.64,-1.54,.90),(.64,-1.54,.90),(.64,-1.52,.60)],.045,m['yellow'])
    for x in [-.38,.38]:beam('bullbar brace',(x,-1.2,.70),(x,-1.53,.70),.035,m['iron'],vertices=10)
    torus('steering wheel',(-.30,-.34,1.27),.14,.018,m['iron'],rotation=(math.radians(55),0,0),major_segments=24,minor_segments=6)
    barrel('rear red fuel drum',(.56,.94,.86),m,'red',r=.18,h=.60)
    box('rear engine',(0,1.04,.89),(.58,.47,.33),m['iron'],bevel=.035)
    for x in [-.18,0,.18]:beam('exposed engine exhaust',(x,1.06,.90),(x,1.46,1.1),.032,m['steel'],vertices=10)
    cargo((-.28,.94,1.04),m);flag((.47,.83,1.19),m)


def cart(m):
    # Two wheels and hand tow shafts, no engine/cab/steering truck substitute.
    for x in [-.69,.69]:wheel((x,.15,.39),m,.39,.20)
    box('cart wooden floor',(0,.10,.66),(1.18,1.65,.11),m['wood'],bevel=.03)
    for x in [-.62,.62]:
        box('cart patched side',(x,.10,.96),(.06,1.65,.54),m['teal'],bevel=.025)
        beam('cart towing shaft',(x,-.68,.72),(x,-1.37,1.07),.03,m['iron'],vertices=12)
        beam('cart upper hand rail',(x,-.68,1.27),(x,.88,1.27),.024,m['brass'],vertices=8)
    for y in [-.72,.92]:box('cart end board',(0,y,.96),(1.22,.06,.54),m['wood'],bevel=.025)
    cargo((-.22,-.30,.74),m,True);cargo((.17,.43,.74),m)
    barrel('cart little can',(-.40,.5,1.14),m,'red',r=.10,h=.32)
    badge((.66,.08,1.00),.25,m,True);flag((.52,.7,1.16),m)


def build(key,out,font,resolution=1000):
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    bpy.data.orphans_purge(do_recursive=True)
    m=materials(out,font);m['window']=solid('dark blue smoked glass','#263d40',metal=.18,rough=.19)
    if key=='scrap-buggy':buggy(m)
    elif key=='scout-trike':buggy(m,True)
    elif key=='push-cart':cart(m)
    else:truck(key,m)
    physically_scaled_uv([o for o in bpy.context.scene.objects if o.type=='MESH'])
    bpy.ops.wm.save_as_mainfile(filepath=str(out/(key+'.blend')))
    batches=convert_and_batch();export_glb(out/(key+'.glb'),batches)
    for o in batches:
        if len(o.data.polygons)>20:
            mod=o.modifiers.new('Lower detail','DECIMATE');mod.ratio=.35;select_only([o]);bpy.ops.object.modifier_apply(modifier=mod.name);clean_mesh(o)
    export_glb(out/(key+'-lod1.glb'),batches)
    for o in list(bpy.data.objects):bpy.data.objects.remove(o,do_unlink=True)
    bpy.ops.import_scene.gltf(filepath=str(out/(key+'.glb')))
    meshes=[o for o in bpy.context.scene.objects if o.type=='MESH'];pts=[o.matrix_world@Vector(c) for o in meshes for c in o.bound_box]
    lo=Vector([min(p[j] for p in pts) for j in range(3)]);hi=Vector([max(p[j] for p in pts) for j in range(3)]);center=(lo+hi)/2
    cam=setup_render(resolution,32);cam.location=center+Vector((7,-11,5));point(cam,center);cam.data.ortho_scale=max(hi-lo)*1.55
    bpy.context.scene.render.filepath=str(out/(key+'.png'));bpy.ops.render.render(write_still=True)
    from verify_rts_batch import verify
    evidence={suffix:verify(out/(key+suffix+'.glb')) for suffix in ['', '-lod1']}
    assert evidence['-lod1']['triangles']<evidence['']['triangles']
    (out/'verification.json').write_text(json.dumps({'asset':key,'reference':'1000000417.png','reference_region':'Named vehicle cell','source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'geometry':evidence,'scope':'Authored reference-led geometry, fresh-import render. Static exports; no wheel animation or target-engine test. Hidden geometry inferred. Visual match is not exact reconstruction.'},indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--only',nargs='+',choices=IDS,default=IDS);p.add_argument('--resolution',type=int,default=1000);args=p.parse_args()
    if args.output.exists():raise SystemExit('Use a new output directory')
    for key in args.only:
        out=args.output/key;out.mkdir(parents=True);print('BUILD',key,flush=True);build(key,out,Path('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'),args.resolution)
