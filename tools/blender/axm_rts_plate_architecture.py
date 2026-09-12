"""Visible construction motifs authored from the AXM architecture plates.

Distinct compositions use a common kit of real corrugated shells, bowed roofs,
windows, rails, lamps, tanks, signs and clutter. Hidden geometry is inferred.
"""
import math,random
import bpy
from mathutils import Vector
from axm_blender_forge import box,cylinder,torus,beam,cable,sphere,cone
from axm_salvage_construction import mesh,corrugated,cloth,barrel,crate,lantern,plant,flange
from axm_rts_vehicle_forge import badge,flag,crane,wheel


def base(m,w=4.5,d=3.4):
    rng=random.Random(17)
    box('soil under foundation',(0,0,.045),(w,d,.09),m['soil'],bevel=.09)
    nx=round(w/.5);ny=round(d/.5)
    for i in range(nx):
        for j in range(ny):box('individual concrete paving',(-w/2+(i+.5)*w/nx,-d/2+(j+.5)*d/ny,.13),(w/nx-.017,d/ny-.017,.16),m['stone'],rotation=(0,0,rng.uniform(-.025,.025)),bevel=.027)
    for j in range(18):
        a=j*2.4;x=math.cos(a)*w*.46;y=math.sin(a)*d*.47
        sphere('scattered rubble',(x,y,.21),(.10,.065,.06),m['stone'],segments=7,rings=4)
        if j%3==0:plant('edge weeds',(x,y,.23),m,j,.7)


def sign(c,lines,m,w=1,h=1.35):
    x,y,z=c
    cloth('banner slogan',[(x-w/2,y,z+h/2),(x+w/2,y+.018,z+h/2-.018),(x-w/2,y-.018,z-h/2),(x+w/2,y-.024,z-h/2)],m['ivory'],sag=.012,flutter=.006,subdivisions=(12,16))
    fs=min(w/(max(map(len,lines))*.72),h/(len(lines)+2))
    for i,line in enumerate(lines):
        data=bpy.data.curves.new('authored slogan','FONT');data.body=line;data.align_x='CENTER';data.size=fs;data.extrude=.0005;data.materials.append(m['black'])
        ob=bpy.data.objects.new('slogan '+line,data);bpy.context.collection.objects.link(ob);ob.location=(x,y-.030,z+h*.32-i*fs*1.23);ob.rotation_euler=(math.pi/2,0,0)
        bpy.context.view_layer.objects.active=ob;ob.select_set(True);bpy.ops.object.convert(target='MESH');ob.select_set(False)
    badge((x,y-.034,z-h*.31),min(w*.15,h*.12),m)
    for dx in [-w*.44,w*.44]:torus('banner grommet',(x+dx,y-.028,z+h*.44),.02,.006,m['brass'],rotation=(math.pi/2,0,0),major_segments=12,minor_segments=6)


def ladder(x,y,h,m,z=.24):
    for dx in [-.17,.17]:beam('ladder rail',(x+dx,y-.25,z),(x+dx,y,z+h),.022,m['wood'],vertices=8)
    for j in range(max(3,int(h/.27))):
        t=(j+.5)/max(3,int(h/.27));beam('ladder rung',(x-.17,y-.25+.25*t,z+h*t),(x+.17,y-.25+.25*t,z+h*t),.019,m['wood'],vertices=8)


def window(c,m,w=.55,h=.62):
    x,y,z=c
    box('warm window',(x,y,z),(w,.027,h),m['emission'],bevel=.015)
    for dx in [-w/2,w/2]:box('window upright',(x+dx,y-.025,z),(.035,.04,h+.05),m['iron'],bevel=.007)
    for dz in [-h/2,0,h/2]:box('window cross rail',(x,y-.025,z+dz),(w+.04,.04,.029),m['iron'],bevel=.004)


def shell(m,c=(0,0,1.30),w=2.8,d=2,h=2.1,openfront=False,paint='teal'):
    x,y,z=c
    for s in [-1,1]:
        corrugated('container side',(x+s*w/2,y,z),d,h,m[paint],math.pi/2,3+s)
        for yy in [y-d/2,y+d/2]:
            box('container corner',(x+s*w/2,yy,z),(.085,.085,h+.07),m['iron'],bevel=.014)
            for zz in [z-h*.4,z+h*.4]:box('container corner casting',(x+s*w/2,yy,zz),(.12,.12,.14),m['rust'],bevel=.019)
    corrugated('container rear',(x,y+d/2,z),w,h,m[paint],seed=5)
    if not openfront:corrugated('container front',(x,y-d/2,z),w,h,m[paint],seed=8)
    for zz in [z-h/2,z+h/2]:box('front header',(x,y-d/2,zz),(w+.10,.075,.09),m['iron'],bevel=.012)
    box('container floor',(x,y,z-h/2),(w,d,.09),m['wood'],bevel=.02)
    box('container roof',(x,y,z+h/2),(w+.1,d+.1,.075),m[paint],bevel=.025)


def canopy(m,c=(.3,-.2,2.7),w=3.2,d=2.2,paint='tarp'):
    x,y,z=c
    corners=[(x-w/2,y+d/2,z+.17),(x+w/2,y+d/2,z),(x-w/2,y-d/2,z-.23),(x+w/2,y-d/2,z-.06)]
    _,pt=cloth('tarp patched canopy',corners,m[paint],sag=.18,flutter=.033,edge_sag=.14,corner_folds=.07)
    for u in [0,.33,.67,1]:cable('canvas seam',[pt(u,j/20) for j in range(21)],.009,m['tarp_light'])
    for p in corners:beam('canopy pole',(p[0],p[1],.22),p,.023,m['iron'],vertices=8)
    for x1 in [x-w*.36,x+w*.36]:lantern('canopy lantern',(x1,y-d/2+.12,z-.52),m,.78)


def roof_arch(m,c=(0,0,.3),w=3,d=2.2,h=2.8,glass=False):
    x,y,z=c;r=w/2;spring=h-r
    for j in range(9):
        yy=y-d/2+j*d/8
        pts=[(x+r*math.cos(a),yy,z+spring+r*math.sin(a)) for a in [i*math.pi/24 for i in range(25)]]
        cable('bowed roof rib',pts,.035,m['iron'])
    for j in range(8):
        yy=y-d/2+(j+.5)*d/8
        for k in range(10):
            a=k*math.pi/10;b=(k+1)*math.pi/10
            verts=[(x+r*math.cos(t),yy+v*d/8,z+spring+r*math.sin(t)) for v,t in [(-.48,a),(-.48,b),(.48,b),(.48,a)]]
            mesh('arched roof sheet',verts,[(0,1,2,3)],m['window' if glass else ['teal','ivory','blue'][((j+k)//3)%3]])
    for s in [-1,1]:corrugated('arched shed lower side',(x+s*r,y,z+spring/2),d,spring,m['teal'],math.pi/2)
    corrugated('arched shed back',(x,y+d/2,z+h*.46),w,h*.90,m['teal'])


def tank(c,m,r=.55,h=1.65,paint='teal'):
    x,y,z=c
    cylinder('tank vessel',(x,y,z+h/2),r,h,m[paint],vertices=32,bevel=.055)
    sphere('tank domed lid',(x,y,z+h), (r,r,.10),m[paint],segments=28,rings=12)
    for t in [.08,.30,.72,.95]:torus('tank rolled seam',(x,y,z+h*t),r+.008,.019,m['steel'],major_segments=28,minor_segments=6)
    cylinder('tank hatch',(x,y,z+h+.11),r*.32,.10,m['iron'],vertices=24,bevel=.012)
    cable('tank outlet',[(x,y-r,z+.20),(x,y-r-.22,z+.20),(x,y-r-.22,z+.52)],.045,m['brass'])
    ladder(x+r*.6,y-r*.82,h,m,z)


def clutter(m,positions=None):
    for j,(x,y) in enumerate(positions or [(-1.75,-1.0),(1.65,-.85),(1.5,.85)]):
        barrel('salvaged barrel',(x,y,.22),m,['teal','red','ivory'][j%3],r=.19,h=.62)
        crate('parts crate',(x+.35,y+.06,.22),m,w=.48,d=.39,h=.40)


def tower(m,c=(0,.2,.24),h=3.3,w=1.45,enclosed=False):
    x,y,z=c
    for sx in [-1,1]:
        for sy in [-1,1]:
            beam('tower angled leg',(x+sx*w*.60,y+sy*w*.60,z),(x+sx*w*.42,y+sy*w*.42,z+h),.055,m['yellow'],vertices=4)
        for j in range(3):
            a=z+j*h/3;b=z+(j+1)*h/3
            beam('tower cross brace',(x-w*.52,y+sx*w*.52,a),(x+w*.52,y+sx*w*.52,b),.027,m['iron'],vertices=8)
            beam('tower cross brace',(x+w*.52,y+sx*w*.52,a),(x-w*.52,y+sx*w*.52,b),.027,m['iron'],vertices=8)
    box('tower platform',(x,y,z+h),(w*1.18,w*1.18,.13),m['wood'],bevel=.022)
    for sy in [-1,1]:
        beam('tower handrail',(x-w*.60,y+sy*w*.6,z+h+.64),(x+w*.6,y+sy*w*.6,z+h+.64),.025,m['brass'],vertices=8)
        for sx in [-1,1]:beam('tower handrail upright',(x+sx*w*.6,y+sy*w*.6,z+h),(x+sx*w*.6,y+sy*w*.6,z+h+.65),.024,m['iron'],vertices=8)
    if enclosed:
        shell(m,(x,y,z+h+.54),w,w,1.08,paint='teal')
        for xx in [-.28,.28]:window((x+xx,y-w*.51,z+h+.58),m,.40,.50)
    else:cloth('tarp tower cover',[(x-w*.7,y+w*.6,z+h+1),(x+w*.7,y+w*.6,z+h+.90),(x-w*.7,y-w*.6,z+h+.83),(x+w*.7,y-w*.6,z+h+.87)],m['tarp'],sag=.10,flutter=.02)
    ladder(x+w*.5,y-w*.62,h,m,z)
    lantern('tower lamp',(x-w*.5,y-w*.5,z+h-.25),m,.75)


def dish(m,c=(0,0,2.5),r=.75):
    x,y,z=c;parent=bpy.data.objects.new('dish aiming mount',None);bpy.context.collection.objects.link(parent)
    verts=[];faces=[]
    for j in range(13):
        rad=.001+r*j/12
        for i in range(40):a=i*math.tau/40;verts.append((rad*math.cos(a),rad*math.sin(a),rad*rad*.65))
    for j in range(12):
        for i in range(40):a=j*40+i;b=j*40+(i+1)%40;faces.append((a,b,b+40,a+40))
    ob=mesh('parabolic dish bowl',verts,faces,m['ivory'],smooth=True);ob.parent=parent
    ob=torus('dish rim',(0,0,r*r*.65),r,.018,m['steel'],major_segments=40,minor_segments=6);ob.parent=parent
    for i in range(8):
        a=i*math.tau/8
        ob=cable('dish radial rib',[(r*j/12*math.cos(a),r*j/12*math.sin(a),(r*j/12)**2*.65+.006) for j in range(13)],.008,m['rust']);ob.parent=parent
    for i in range(3):
        a=i*math.tau/3;ob=beam('dish feed strut',(r*.8*math.cos(a),r*.8*math.sin(a),r*r*.4),(0,0,r),.012,m['iron'],vertices=8);ob.parent=parent
    parent.location=c;parent.rotation_euler=(math.radians(40),math.radians(-14),0)
    beam('dish mounting post',(x,y,z-.7),(x,y,z),.06,m['iron'],vertices=16)


def workshop_inside(m,c=(0,.5,.25),fungus=False):
    x,y,z=c
    for level in [.45,1.05,1.65]:
        box('workbench shelf',(x,y,z+level),(1.65,.50,.075),m['wood'],bevel=.018)
        for j in range(5):
            xx=x-.65+j*.32
            if fungus:
                cylinder('mushroom stalk',(xx,y,z+level+.12),.035,.22,m['ivory'],vertices=12,bevel=.009)
                sphere('mushroom cap',(xx,y,z+level+.25),(.13,.12,.075),m['yellow' if j%2 else 'wood'],segments=20,rings=10)
            else:cylinder('shelf can',(xx,y,z+level+.10),.085,.20,m[['teal','ivory','red'][j%3]],vertices=16,bevel=.01)
    for xx in [x-.80,x+.80]:box('shelf vertical',(xx,y,z+.94),(.06,.06,1.95),m['iron'],bevel=.01)
    lantern('workshop inside glow',(x,y-.15,z+2.0),m)


def building(key,m):
    base(m)
    if key=='settlement-hub':
        shell(m,(-.65,.35,1.30),2.6,2.1,2.12,True)
        shell(m,(-.62,.47,3.04),2.25,1.70,1.27)
        for xx in [-1.32,-.60,.12]:window((xx,-.405,3.0),m,.50,.65)
        canopy(m,(.1,-.55,2.45),3.65,1.65);workshop_inside(m,(-.60,.6,.24));ladder(1.05,-.7,3.4,m);flag((-.3,.6,3.75),m)
        sign((-.65,-1.56,2.12),['PEOPLE','KEEP','PEOPLE','GOING'],m,1.1,1.55)
    elif key in ['civic-shelter','storage-hall']:
        roof_arch(m,(-.35,.28,.24),3.1,2.2,2.8)
        workshop_inside(m,(-.6,.6,.24));canopy(m,(.2,-.75,2.33),3.0,1.35)
        sign((.64,-1.46,1.55),['SAME','MESS','DIFFERENT','TOMORROW'] if key=='civic-shelter' else ['SUPPLIES','TOMORROW'],m,1.18,1.8)
        for xx in [-1.64,1.63]:tank((xx,.4,.24),m,.32,.95,'ivory')
    elif key=='command-signal-hall':
        shell(m,(0,.28,1.45),3.3,2.25,2.4,True);workshop_inside(m,(-.7,.7,.24));canopy(m,(0,-.25,2.98),3.6,2.1)
        dish(m,(1.18,.80,3.13),.85);tower(m,(-1.30,.70,2.7),1.65,.55);ladder(.05,-.95,2.8,m)
        sign((.62,-1.30,1.72),['FARTHER','TOGETHER'],m,1.2,1.6)
    elif key=='training-yard':
        for j in range(15):box('uneven timber fence',(-1.85+j*.27,.90,1.0),(.23,.10,1.5+.17*math.sin(j)),m['wood'],bevel=.025)
        for j in range(3):
            x=-1.1+j*1.1;beam('target post',(x,.1,.24),(x,.1,1.66),.05,m['wood'],vertices=8);badge((x,.07,1.55),.32,m)
        sign((-.9,-1.02,1.0),['PRACTICE','SURVIVES'],m,1.15,1.25);flag((1.55,.85,1.45),m)
        for j in range(4):torus('training tire',(.60+j*.31,-.85,.32),.20,.065,m['rubber'],major_segments=24,minor_segments=8)
    elif key in ['repair-garage','machine-shop']:
        shell(m,(-.3,.36,1.38),3.2,2.1,2.27,True);canopy(m,(0,-.3,2.8),3.65,2.1);workshop_inside(m,(-.70,.7,.24))
        crane(m,.70)
        if key=='repair-garage':
            for xx in [-.48,.48]:wheel((xx,-.6,.55),m,.32,.19)
            box('vehicle under repair',(0,-.30,.93),(1.05,1.30,.47),m['teal'],bevel=.07)
        else:
            cylinder('lathe motor',(.65,-.45,1.23),.24,.75,m['iron'],rotation=(0,math.pi/2,0),vertices=28,bevel=.04)
        sign((1.05,-1.14,1.76),['FIX','IT','AGAIN'] if key=='repair-garage' else ['OLD','TOOLS','NEW','DAYS'],m,.92,1.6)
    elif key=='refinery-shack':
        for xx,h in [(-.90,2.35),(.25,2.1),(1.23,1.5)]:tank((xx,.35,.23),m,.48,h,'ivory' if xx<0 else 'teal')
        for zz in [.85,1.80,2.37]:cable('refinery plumbing',[(-1.4,.50,zz),(-1.65,.50,zz),(-1.65,-.7,zz),(-.70,-.7,zz)],.052,m['brass'])
        cylinder('refinery stack',(1.48,.6,2.5),.13,3.0,m['iron'],vertices=24,bevel=.014)
        sign((.2,-.95,1.40),['NOT','WASTE.','FUEL.'],m,.95,1.60)
    elif key=='power-core-building':
        shell(m,(0,.3,1.25),2.75,2.1,2.05,True);workshop_inside(m,(-.50,.70,.24))
        lantern('giant lantern core',(.15,.30,3.08),m,2.5)
        sign((.6,-1.1,1.45),['SMALL','POWER','BIG','PEOPLE'],m,1.05,1.55)
        box('solar array',(-1.50,-.55,1.55),(1.0,.08,1.2),m['blue'],rotation=(math.radians(-22),0,0),bevel=.02)
        for j in range(5):beam('solar cell division',(-1.94+j*.22,-.62,1.02),(-1.94+j*.22,-.17,2.10),.008,m['steel'],vertices=6)
    clutter(m)


def industry(key,m):
    base(m)
    if key=='open-crop-terrace':
        for j in range(3):
            z=.24+j*.50;y=-.9+j*.72
            for x in [-.85,.85]:
                crate('raised vegetable bed',(x,y,z),m,w=1.45,d=.68,h=.40)
                box('garden soil',(x,y,z+.39),(1.32,.57,.05),m['soil'],bevel=.01)
                for k in range(7):plant('crop leaves',(x-.55+k*.18,y,z+.43),m,k+j,1.1)
        sign((1.68,-.90,1.0),['DIRT','FOOD','HOPE'],m,.72,1.20);flag((1.3,.9,1.75),m)
    elif key=='bus-window-greenhouse':
        shell(m,(0,.25,.69),3.25,2.15,.85,True)
        for x in [-1.62,1.62]:
            for j in range(5):
                yy=-.65+j*.46;box('salvaged bus side glass',(x,yy,1.65),(.022,.40,1.15),m['window'],bevel=.015)
                beam('glasshouse upright',(x,yy-.22,1.04),(x,yy-.22,2.28),.027,m['brass'],vertices=8)
        for xx in [-1.15,-.55,.05,.65,1.25]:window((xx,-.85,1.72),m,.52,1.10)
        for s in [-1,1]:
            for j in range(5):
                yy=-.84+j*.49
                mesh('greenhouse roof pane',[(0,yy,2.87),(s*1.67,yy,2.25),(s*1.67,yy+.44,2.25),(0,yy+.44,2.87)],[(0,1,2,3)],m['window'])
                beam('greenhouse pitched roof rib',(0,yy,2.9),(s*1.68,yy,2.25),.031,m['iron'],vertices=8)
        for j in range(10):plant('greenhouse plants',(-1.3+j*.27,-1.05,.54),m,j,1.4)
        sign((.93,-1.09,1.20),['GREENER','DAYS','AHEAD'],m,.85,1.4);tank((1.65,.85,.24),m,.32,1.0,'ivory')
    elif key=='fungal-shed':
        shell(m,(-.1,.25,1.40),3.15,2.0,2.3,True,paint='ivory');canopy(m,(.1,-.3,2.9),3.6,2.2);workshop_inside(m,(.35,.6,.24),True)
        for x,y,s in [(.7,-.55,1.0),(1.2,-.2,.65),(.12,-.4,.52)]:
            cylinder('giant mushroom stem',(x,y,.65),.10*s,.84*s,m['ivory'],vertices=20,bevel=.03)
            sphere('giant mushroom hood',(x,y,.65+.43*s),(.47*s,.42*s,.20*s),m['yellow'],segments=28,rings=14)
        sign((-1.13,-.91,1.58),['SHROOMS','FEED','PEOPLE'],m,.85,1.5)
    elif key=='livestock-pen':
        for y in [-1.18,1.18]:
            for z in [.66,1.10]:beam('pen fence rail',(-1.7,y,z),(1.7,y,z),.043,m['wood'],vertices=8)
            for x in [-1.7,-.6,.6,1.7]:beam('pen upright',(x,y,.22),(x,y,1.33),.05,m['wood'],vertices=8)
        canopy(m,(0,.05,2.7),3.4,2.25,'red')
        for x,y,size,paint in [(-.65,.1,1.0,'ivory'),(.85,-.25,.58,'red')]:
            sphere('animal rounded torso',(x,y,.93*size+.20),(.48*size,.72*size,.42*size),m[paint],segments=28,rings=16)
            sphere('animal head',(x,y-.68*size,.95*size+.20),(.26*size,.32*size,.30*size),m[paint],segments=24,rings=14)
            for sx in [-1,1]:
                for sy in [-1,1]:beam('animal leg',(x+sx*.28*size,y+sy*.42*size,.26),(x+sx*.28*size,y+sy*.42*size,.94*size),.075*size,m[paint],vertices=12)
                sphere('animal eye',(x+sx*.21*size,y-.84*size,1.28*size),(.023*size,)*3,m['black'],segments=10,rings=6)
                sphere('animal ear',(x+sx*.30*size,y-.58*size,1.36*size),(.14*size,.06*size,.06*size),m[paint],segments=12,rings=8)
            if size==1:
                for yy in [-.28,.17,.38]:sphere('cow black patch',(x+.445,y+yy,1.20),(.02,.19,.21),m['black'],segments=14,rings=8)
        sign((1.0,-1.26,.97),['HAPPY','STOMACHS','BRIGHTER','DAYS'],m,1.0,1.24)
    elif key=='water-catcher':
        tank((.95,.20,.24),m,.75,1.8,'steel')
        for x in [-1.7,-.2]:
            for y in [-.55,1.02]:beam('water collector legs',(x,y,.22),(x,y,2.85),.038,m['wood'],vertices=10)
        cloth('tarp water collecting bowl',[(-1.78,1.06,2.85),(-.10,1.06,2.8),(-1.75,-.64,2.90),(-.07,-.60,2.84)],m['tarp'],sag=.62,flutter=.017)
        cable('collector outlet',[(-.92,.22,2.30),(-.92,.22,2.05),(.65,.22,2.05)],.065,m['iron'])
        for j in range(13):torus('tank corrugated ring',(.95,.20,.36+j*.12),.76,.015,m['steel'],major_segments=32,minor_segments=6)
        sign((.95,-.57,1.18),['EVERY','DROP','COUNTS'],m,.8,1.25)
    elif key=='scrap-sorting-yard':
        for j,paint in enumerate(['iron','teal','yellow']):
            x=-1.26+j*1.27
            crate('sorting bin',(x,-.48,.24),m,w=1.13,d=.94,h=.72)
            for k in range(15):
                a=k*2.4;box('loose scrap',(x+.35*math.cos(a),-.45+.31*math.sin(a),1.0+.06*(k%4)),(.33,.20,.10),m[['iron','rust','teal','steel'][k%4]],rotation=(k*.23,k*.17,k),bevel=.01)
            sign((x,-.98,.61),[['METAL'],['PLASTIC'],['OTHER']][j],m,.75,.55)
        crane(m,.85);sign((1.30,.42,2.38),['TRASH','INTO','TOMORROW'],m,1.12,1.25)
    elif key=='shallow-mine-entrance':
        for j in range(18):
            a=j*math.pi/17
            sphere('jagged mine arch',(1.45*math.cos(a),.45,.45+2.0*math.sin(a)),(.36,.45,.38),m['iron' if j%3 else 'stone'],segments=7,rings=4)
        for x in [-1.07,1.07]:beam('mine timber upright',(x,.03,.24),(x,.03,2.17),.12,m['wood'],vertices=4)
        beam('mine timber lintel',(-1.12,.03,2.12),(1.12,.03,2.12),.15,m['wood'],vertices=4)
        for x in [-.42,.42]:beam('mine rail',(x,-1.62,.26),(x,.90,.26),.035,m['iron'],vertices=4)
        crate('mine cart',(-.12,-.62,.34),m,w=.82,d=.83,h=.51)
        for x in [-.40,.24]:wheel((x,-.54,.34),m,.15,.08)
        sign((.25,-.09,2.25),['DIG','A LITTLE','LIVE A LOT'],m,1.15,.92);lantern('mine lamp',(-.85,-.09,1.68),m)
    elif key=='deep-mine-head':
        tower(m,(.25,.4,.24),3.65,1.6)
        cylinder('winding drum',(.25,.3,3.98),.35,1.06,m['rust'],rotation=(0,math.pi/2,0),vertices=32,bevel=.025)
        torus('winding wheel',(1.0,.3,3.98),.48,.052,m['iron'],rotation=(0,math.pi/2,0),major_segments=32,minor_segments=8)
        for x in [-1.6,1.6]:cable('mine head guy rope',[(x,-1.3,.25),(.25,.4,3.92)],.012,m['iron'])
        shell(m,(-1.07,.12,.81),1.30,1.55,1.12,True,paint='wood')
        sign((.93,-.52,1.0),['GO','DEEPER'],m,1.05,1.25)
    elif key=='asteroid-extraction-rig':
        sphere('asteroid rock',(-.65,.05,1.52),(1.00,.84,1.14),m['iron'],segments=10,rings=7)
        for j in range(9):
            a=j*2.4;p=(-.65+.84*math.cos(a),-.60,1.52+.80*math.sin(a))
            torus('asteroid drill collar',p,.18,.035,m['steel'],rotation=(math.pi/2,0,0),major_segments=20,minor_segments=6)
        crane(m,.4);shell(m,(1.15,.05,1.33),1.02,1.1,1.18,paint='ivory');badge((1.15,-.53,1.3),.3,m)
    elif key=='battery-fuel-station':
        tank((-1.10,.35,.24),m,.62,1.8,'ivory');canopy(m,(.62,.18,2.6),2.18,2.0,'tarp_light')
        for x in [.10,.94]:
            box('vintage fuel pump',(x,-.25,1.03),(.50,.50,1.47),m['red' if x<.5 else 'yellow'],bevel=.08)
            box('fuel pump meter',(x,-.511,1.41),(.34,.028,.28),m['ivory'],bevel=.02)
            cable('fuel pump hose',[(x+.22,-.25,1.52),(x+.44,-.3,1.15),(x+.46,-.3,.40),(x+.26,-.5,.36),(x+.23,-.5,1.07)],.027,m['rubber'])
        sign((1.65,-.65,1.27),['CHARGE','REFUEL','SURVIVE'],m,.74,1.5)
    elif key=='clustered-storage-bins':
        for x,y,r,h,p in [(-1.1,.5,.55,2.2,'yellow'),(.12,.56,.49,2.5,'red'),(1.25,.56,.54,2.18,'teal'),(-.60,-.60,.50,1.28,'blue'),(.73,-.66,.53,1.36,'ivory')]:tank((x,y,.24),m,r,h,p)
        sign((-.61,-1.12,.98),['METAL'],m,.68,.60);sign((.74,-1.22,1.02),['SUPPLIES'],m,.8,.58)
    clutter(m,[(-1.8,-1.20),(1.75,.9)])


def gun(m,c=(0,0,1),kind='rifle',scale=1):
    """Separate receiver, furniture, barrel bores, controls and sling; points +X."""
    old=set(bpy.data.objects)
    box('weapon receiver',(0,0,0),(.65,.20,.24),m['iron'],bevel=.035)
    box('shaped wooden buttstock',(-.59,.015,-.07),(.58,.16,.32),m['wood'],rotation=(0,.14,0),bevel=.075)
    box('stock butt pad',(-.89,.015,-.09),(.045,.18,.29),m['rubber'],bevel=.015)
    box('pistol grip',(-.12,0,-.23),(.15,.16,.29),m['wood'],rotation=(0,-.25,0),bevel=.035)
    if kind=='shotgun':
        for y in [-.085,.085]:
            beam('double shotgun barrel',(.18,y,.02),(1.05,y,.02),.069,m['iron'],vertices=20)
            cylinder('open shotgun muzzle',(1.056,y,.02),.046,.01,m['black'],rotation=(0,math.pi/2,0),vertices=20,bevel=0)
        box('shotgun foregrip',(.48,0,-.08),(.43,.20,.14),m['wood'],bevel=.05)
        for x in [-.21,-.08,.05]:cylinder('red spare cartridge',(x,-.13,.03),.032,.19,m['red'],vertices=12,bevel=.006)
    elif kind=='launcher':
        cylinder('launcher tube',(.32,0,.15),.16,1.35,m['teal'],rotation=(0,math.pi/2,0),vertices=32,bevel=.018)
        torus('launcher muzzle lip',(1.01,0,.15),.155,.024,m['steel'],rotation=(0,math.pi/2,0),major_segments=24)
        cone('rocket nose',(1.14,0,.15),.12,0,.36,m['red'],rotation=(0,math.pi/2,0),bevel=.008)
        box('launcher sight',(.2,0,.35),(.15,.08,.12),m['iron'],bevel=.012)
    else:
        length=.49 if kind=='smg' else .83
        beam('rifled barrel',(.25,0,.04),(.25+length,0,.04),.043,m['iron'],vertices=20)
        cylinder('muzzle bore',(.255+length,0,.04),.025,.011,m['black'],rotation=(0,math.pi/2,0),vertices=16,bevel=0)
        box('ventilated foregrip',(.40,0,.025),(.38,.16,.17),m['wood' if kind=='rifle' else 'iron'],bevel=.026)
        for x in [.27,.38,.49]:box('foregrip vent',(x,-.083,.05),(.035,.007,.05),m['black'],bevel=.008)
        for x in [-.15,.88 if kind=='rifle' else .65]:box('iron sight',(x,0,.19),(.045,.045,.10),m['iron'],bevel=.006)
        beam('slanted magazine',(.1,0,-.11),(.23,0,-.44),.092,m['iron'],vertices=4)
    cable('trigger guard',[(-.17,-.02,-.13),(-.10,-.02,-.26),(.02,-.02,-.27),(.08,-.02,-.12)],.014,m['iron'])
    cable('canvas sling',[(-.70,.08,-.15),(-.37,.14,-.45),(.37,.14,-.45),(.69,.08,-.03)],.017,m['tarp'])
    for ob in set(bpy.data.objects)-old:
        ob.location=Vector(c)+ob.location*scale;ob.scale*=scale


def rotary(m,c=(0,0,1),scale=1):
    old=set(bpy.data.objects)
    cylinder('rotary receiver',(-.3,0,0),.28,.58,m['teal'],rotation=(0,math.pi/2,0),vertices=24,bevel=.025)
    for i in range(6):
        a=i*math.tau/6;y=.145*math.cos(a);z=.145*math.sin(a)
        beam('six barrel cluster',(-.02,y,z),(1.05,y,z),.049,m['iron'],vertices=16)
        cylinder('barrel bore',(1.058,y,z),.029,.012,m['black'],rotation=(0,math.pi/2,0),vertices=12,bevel=0)
    for x in [.13,.83]:torus('barrel clamp',(x,0,0),.195,.035,m['steel'],rotation=(0,math.pi/2,0),major_segments=24)
    cylinder('ammo drum',(-.35,.33,0),.28,.32,m['rust'],rotation=(math.pi/2,0,0),vertices=24,bevel=.025)
    for x in [-.30,0,.3]:beam('gun mount brace',(0,0,-.20),(x,.2 if x==0 else -.30,-.8),.045,m['iron'])
    for i in range(12):
        t=i/11;cylinder('linked brass ammunition',(-.35,.56+t*.25,-.15-t*.65),.036,.19,m['brass'],rotation=(0,math.pi/2,0),vertices=12,bevel=.004)
    for ob in set(bpy.data.objects)-old:ob.location=Vector(c)+ob.location*scale;ob.scale*=scale


def engine(m,c=(0,0,.55)):
    x,y,z=c;box('cast engine block',c,(1.18,.87,.55),m['iron'],bevel=.07)
    for side in [-1,1]:
        for j in range(4):
            xx=x-.43+j*.29;beam('V cylinder',(xx,y,z+.15),(xx,y+side*.37,z+.58),.115,m['steel'])
            box('red valve cover',(xx,y+side*.30,z+.56),(.23,.23,.13),m['red'],bevel=.035)
            cable('exhaust header',[(xx,y+side*.34,z+.4),(xx,y+side*.58,z+.23),(x+.67,y+side*.58,z+.18)],.033,m['rust'])
    cylinder('radiator fan hub',(x-.66,y,z+.15),.14,.10,m['brass'],rotation=(0,math.pi/2,0))
    for j in range(7):
        a=j*math.tau/7;ob=box('fan blade',(x-.7,y+.24*math.sin(a),z+.15+.24*math.cos(a)),(.05,.14,.37),m['steel'],bevel=.025);ob.rotation_euler.x=-a
    for j in range(6):box('sump cooling rib',(x,y-.38+j*.15,z-.24),(1.17,.035,.07),m['steel'],bevel=.008)


def anomaly(m,c=(0,0,1.1),r=.8):
    x,y,z=c;sphere('fractured meteor',c,(r,r*.78,r*1.13),m['iron'],segments=11,rings=7)
    for i in range(7):
        a=i*math.tau/7
        cable('luminous mineral fracture',[(x+r*.82*math.cos(a),y-r*.5,z+r*.73*math.sin(a)),(x+r*.37*math.cos(a+.3),y-r*.78,z+r*.37*math.sin(a+.3)),(x+.08,y-r*.79,z-.12)],r*.023,m['cyan'])
    for i in range(4):
        a=i*math.pi/2;beam('meteor containment claw',(x+r*1.12*math.cos(a),y+r*math.sin(a),z-r),(x+r*.80*math.cos(a),y+r*.72*math.sin(a),z),r*.09,m['yellow'])


def equipment(key,m):
    base(m,3.0,2.35)
    if key in ['scrap-rifle','pipe-shotgun','compact-smg','improvised-launcher']:
        kind={'scrap-rifle':'rifle','pipe-shotgun':'shotgun','compact-smg':'smg','improvised-launcher':'launcher'}[key]
        gun(m,(-.12,0,1.05),kind,1.2)
        for x in [-.62,.65]:beam('display resting support',(x,.12,.24),(x,.12,.89),.045,m['wood'])
        sign((-.7,-.48,.56),{'rifle':['STAY','BACK'],'shotgun':['KNOCK','KNOCK'],'smg':['BAD IDEAS','FAST'],'launcher':['SEND IT']}[kind],m,.72,.58)
    elif key in ['rotary-gun','turret-module']:
        cylinder('rotating turret base',(0,0,.41),.58,.37,m['teal'],vertices=32,bevel=.04)
        if key=='rotary-gun':rotary(m,(0,0,1.25),.92);crate('ammunition box',(-.75,-.53,.23),m,w=.5,d=.43,h=.38)
        else:
            cylinder('turret shell',(0,0,.89),.61,.69,m['teal'],vertices=32,bevel=.10)
            for y in [-.20,.20]:beam('twin turret barrel',(.30,y,1.0),(1.27,y,1.0),.079,m['iron']);torus('turret muzzle',(1.27,y,1),.062,.018,m['steel'],rotation=(0,math.pi/2,0))
            canopy(m,(0,0,1.43),1.26,1.18);badge((0,-.62,.87),.23,m)
    elif key=='wheel-module':
        wheel((0,0,.88),m,.66,.48);box('wheel display chock',(0,-.50,.3),(.74,.23,.17),m['wood'],bevel=.035)
    elif key=='track-module':
        from axm_rts_vehicle_forge import tracks
        tracks(m)
    elif key=='engine-block':engine(m,(0,0,.62));barrel('coolant drum',(.97,.47,.23),m,r=.22,h=.65)
    elif key=='meteor-power-cell':
        anomaly(m,(0,0,1.15),.67);cylinder('cell plinth',(0,0,.39),.84,.3,m['teal'],vertices=24,bevel=.04)
        for s in [-1,1]:cable('power extraction conduit',[(s*.58,0,1.12),(s*.97,.1,.95),(s*1.03,-.45,.45),(s*.64,-.54,.3)],.055,m['brass'])
    elif key=='bridge-kit':
        for z in [.36,.61,.86]:
            for y in [-.45,.45]:
                for zz in [z,z+.19]:beam('bridge section chord',(-1.18,y,zz),(1.18,y,zz),.045,m['teal'],vertices=4)
                for j in range(6):beam('bridge diagonal',(-1.18+j*.39,y,z),(-.79+j*.39,y,z+.19),.023,m['steel'],vertices=4)
            for j in range(12):box('portable bridge plank',(-1.07+j*.195,0,z+.05),(.17,.90,.055),m['wood'],bevel=.008)
        crate('bridge repair tools',(-.88,-.8,.23),m,w=.55,d=.45,h=.37)
    elif key=='repair-welder':
        tank((-.48,.1,.24),m,.29,1.1,'red');box('welder power case',(.42,.05,.55),(.7,.55,.64),m['yellow'],bevel=.07)
        cable('welding leads',[(.5,-.22,.75),(.8,-.45,.3),(.65,-.85,.26),(-.15,-.75,.3),(-.27,-.40,.69)],.031,m['rubber'])
        beam('welding handpiece',(-.27,-.4,.69),(-.55,-.35,.93),.07,m['iron']);sphere('welding contact',(-.56,-.35,.94),(.045,.045,.045),m['cyan'])
    elif key=='lantern-scanner':
        for a in [0,2.1,4.2]:beam('scanner tripod',(.1,0,1.28),(.58*math.cos(a),.58*math.sin(a),.24),.045,m['iron'])
        lantern('scanning lantern',(.1,0,1.37),m);box('green scanner screen',(.45,-.24,1.02),(.45,.16,.36),m['teal'],bevel=.035)
        box('scanner readout',(.45,-.33,1.04),(.33,.014,.22),m['cyan'],bevel=.012)
        dish(m,(-.55,.2,1.07),.42)
    elif key=='mining-drill':
        for y in [-.48,.48]:
            for x in [-.70,-.35,0,.35,.70]:cylinder('drill track roller',(x,y,.48),.21,.17,m['rubber'],rotation=(math.pi/2,0,0),vertices=20,bevel=.015)
            for j in range(20):
                a=j*math.tau/20;box('drill tread link',(.78*math.cos(a),y,.48+.25*math.sin(a)),(.18,.22,.09),m['iron'],rotation=(0,-a,0),bevel=.015)
        box('drilling power body',(-.27,0,.89),(1.13,.84,.65),m['teal'],bevel=.09)
        cone('drill auger core',(.80,0,.91),.36,.035,.96,m['steel'],rotation=(0,math.pi/2,0),vertices=32,bevel=.02)
        pts=[]
        for j in range(120):
            t=j/119;pts.append((.32+t*.96,(.36*(1-t)+.025)*math.cos(t*math.tau*5),.91+(.36*(1-t)+.025)*math.sin(t*math.tau*5)))
        cable('continuous auger flight',pts,.035,m['brass']);badge((-.3,-.43,.92),.20,m)


def sandbags(m,c=(0,0,.3),rows=3,width=2.3):
    x,y,z=c
    for row in range(rows):
        for j in range(5):
            ob=sphere('stuffed sandbag',(x-width/2+(j+.5)*width/5+(row%2)*.08,y,z+row*.20),(.27,.19,.13),m['wood'],segments=16,rings=8)
            cable('sandbag stitched seam',[(ob.location.x-.20,y-.14,ob.location.z),(ob.location.x,y-.19,ob.location.z-.02),(ob.location.x+.20,y-.14,ob.location.z)],.006,m['tarp'])


def defense(key,m):
    base(m,3.8,2.8)
    if key in ['comic-book-wall','car-door-wall','signplate-barricade']:
        for x in [-1.36,1.36]:beam('barricade post',(x,.10,.24),(x,.10,2.2),.07,m['iron']);lantern('wall lantern',(x,-.05,1.85),m)
        if key=='comic-book-wall':
            corrugated('patched comic wall',(0,.05,1.22),2.7,1.7,m['teal'],seed=72);sign((0,-.035,1.32),['TAKE','THAT!'],m,1.40,1.35)
            for i in range(15):
                x=-1.4+i*.2;cable('barbed wire loop',[(x,.1,2.12),(x+.07,.07,2.36),(x+.18,.1,2.15)],.009,m['iron'])
        elif key=='car-door-wall':
            for j in range(3):
                x=(j-1)*.86;box('salvaged car door',(x,0,.8),(.86,.11,.98),m[['red','ivory','blue'][j]],rotation=(0,.035*(j-1),0),bevel=.12)
                box('car door window glass',(x,0,1.63),(.70,.035,.65),m['window'],bevel=.11)
                for xx in [x-.38,x+.38]:beam('car window frame',(xx,0,1.13),(xx,0,1.91),.026,m['steel'])
                beam('car window header',(x-.34,0,1.94),(x+.34,0,1.94),.03,m['steel']);box('car door handle',(x+.20,-.075,1.10),(.19,.05,.035),m['steel'],bevel=.013)
            sign((.1,-.14,.78),['STILL DRIVES','US HOME'],m,1.2,.6)
        else:
            for x,z,n in [(-.75,1.45,8),(.22,1.80,4),(.82,.8,4)]:cylinder('salvaged traffic sign',(x,-.02,z),.47,.055,m['red' if n==8 else 'yellow'],rotation=(math.pi/2,0,0),vertices=n,bevel=.02)
            sign((-.75,-.07,1.45),['STOP'],m,.55,.46);sign((.5,-.1,1.32),['BAD PEOPLE','GO AROUND'],m,1.3,.64)
    elif key=='fridge-barricade':
        for j,(x,z,w,h,p) in enumerate([(-1.05,.94,.77,1.4,'ivory'),(-.17,1.13,.83,1.8,'teal'),(.77,.89,.90,1.3,'ivory'),(.6,1.9,1.1,.67,'red')]):
            box('discarded refrigerator',(x,.18,z),(w,.62,h),m[p],bevel=.08)
            for zz,hh in [(z+h*.27,h*.34),(z-h*.19,h*.54)]:
                box('separate fridge door',(x,-.16,zz),(w*.93,.075,hh),m[p],bevel=.045);box('fridge handle',(x-w*.30,-.22,zz),(.035,.05,hh*.5),m['steel'],bevel=.012)
        sign((-.25,-.24,1.12),['COLD HARD','SAFER'],m,.69,.65)
    elif key in ['scrap-bunker','sandbag-scrap-firing-nest']:
        sandbags(m,(0,-.50,.33),3);sandbags(m,(-.9,.2,.33),3,.7);sandbags(m,(.9,.2,.33),3,.7)
        if key=='scrap-bunker':
            shell(m,(0,.45,1.05),2.45,1.6,1.6,True);canopy(m,(0,.2,1.98),2.65,1.9)
        gun(m,(.20,-.18,1.04),'rifle',1.05)
        corrugated('firing front patch',(0,-.72,.70),1.22,.62,m['teal'],seed=31);badge((0,-.76,.74),.2,m)
    elif key=='crane-section-watchtower':tower(m,(0,0,.24),3.3,1.6,True);flag((.75,.40,3.65),m)
    elif key in ['spotlight-tower','light-tower']:
        for a in [0,2.1,4.2]:beam('light mast tripod',(0,0,2.65),(.95*math.cos(a),.95*math.sin(a),.25),.065,m['iron'])
        beam('floodlight cross arm',(-.9,0,2.80),(.9,0,2.80),.065,m['teal'])
        for x in [-.65,0,.65]:
            cylinder('round floodlight housing',(x,0,2.93),.25,.25,m['yellow'],rotation=(math.pi/2,0,0),vertices=32,bevel=.04)
            cylinder('floodlight lens',(x,-.14,2.93),.211,.03,m['emission'],rotation=(math.pi/2,0,0),vertices=32,bevel=.01)
            torus('floodlight bezel',(x,-.17,2.93),.222,.027,m['steel'],rotation=(math.pi/2,0,0))
        box('solar panel',(.82,.28,1.1),(.95,.74,.07),m['blue'],rotation=(.45,0,0),bevel=.025)
        for x in [.5,.8,1.1]:beam('solar grid',(x,-.02,1.25),(x,.57,.95),.008,m['steel'])
        cable('power cable',[(0,0,2.8),(.15,.1,1.5),(.1,.2,.3),(.8,.3,.4)],.018,m['rubber'])
    elif key=='bathtub-turret':
        cylinder('bath turret swivel',(0,0,.44),.64,.43,m['teal'],vertices=32,bevel=.07)
        # Open, nested oval rings: an actual hollow tub, not an opaque box.
        verts=[];faces=[];N=48
        for z,rx,ry in [(.61,.83,.42),(1.15,1.03,.58),(1.18,.93,.48),(.70,.70,.32)]:
            verts.extend([(rx*math.cos(i*math.tau/N),ry*math.sin(i*math.tau/N),z) for i in range(N)])
        for k in range(3):
            for i in range(N):faces.append((k*N+i,k*N+(i+1)%N,(k+1)*N+(i+1)%N,(k+1)*N+i))
        faces.append(tuple(range(3*N,4*N)));mesh('hollow enamel bathtub',verts,faces,m['ivory'])
        rotary(m,(.40,0,1.32),.78)
        sphere('rubber duck body',(-.65,-.23,1.17),(.14,.10,.10),m['yellow']);sphere('rubber duck head',(-.60,-.25,1.28),(.075,.07,.075),m['yellow']);cone('duck beak',(-.52,-.25,1.27),.045,0,.08,m['red'],rotation=(0,math.pi/2,0))
        badge((0,-.54,.91),.17,m)
    elif key=='spike-gate':
        for x in [-1.3,1.3]:
            box('gate concrete pillar',(x,0,1.0),(.53,.6,1.55),m['stone'],bevel=.06);lantern('gate warning beacon',(x,0,1.94),m)
        beam('gate cross member',(-1.28,0,1.1),(1.28,0,1.1),.11,m['yellow'],vertices=4)
        for x in [-.95,-.55,-.15,.25,.65,1.05]:cone('gate angled spike',(x,-.20,1.01),.095,0,1.30,m['iron'],rotation=(.5,0,0),vertices=8)
        sign((0,-.31,.77),['NICE TRY'],m,1.12,.45)
    elif key=='mine-marker':
        beam('mine warning post',(0,0,.24),(0,0,1.55),.065,m['wood'],vertices=4);box('red warning cabinet',(0,0,1.35),(.70,.22,.65),m['red'],bevel=.05)
        sign((0,-.13,1.38),['SURPRISE','LATER'],m,.61,.58);lantern('mine warning lamp',(0,0,1.89),m)
        for x,y in [(-.55,-.32),(.53,.39)]:cylinder('buried mine casing',(x,y,.27),.22,.10,m['iron'],vertices=24,bevel=.018)
    elif key=='improvised-anti-vehicle-barrier':
        for x in [-.86,.86]:
            for a,b in [((x-.46,0,.24),(x+.46,0,1.42)),((x+.46,0,.24),(x-.46,0,1.42)),((x,-.66,.82),(x,.66,.82))]:
                beam('hedgehog steel web',a,b,.10,m['iron'],vertices=4)
            sphere('hedgehog central joint',(x,0,.83),(.16,.16,.16),m['rust'],segments=12,rings=8)
        wheel((1.20,.30,.48),m,.29,.18);sign((0,-.31,.86),['CARS NOT','WELCOME'],m,.80,.75)


def utility(key,m):defense(key,m)


def crew(key,m):
    """Plate-led large-headed, clothed survivor with explicit face and role gear."""
    from axm_salvage_surfaces import solid
    skin=m['skin'];fabric=solid('matte olive fabric','#626b48',rough=.95);denim=solid('matte blue workwear','#355e70',rough=.91)
    scarf=solid('red woven scarf','#ac4835',rough=.96);leather=solid('brown leather','#634b35',rough=.81)
    base(m,1.65,1.4)
    heavy=key=='heavy-vehicle-operator';blue=key in ['mechanic-repair-crew','crew-worker','citizen-harvester'];jacket=denim if blue else fabric
    # Rounded anatomy under clothing. Larger boots and head intentionally match the miniature plate language.
    for s in [-1,1]:
        x=s*.23
        sphere('rounded boot upper',(x,-.10,.41),(.22,.33,.20),leather,segments=24,rings=12)
        box('thick rubber boot sole',(x,-.11,.285),(.44,.65,.105),m['rubber'],bevel=.07)
        for j in range(4):beam('boot laces',(x-.10,-.18-j*.039,.55-j*.011),(x+.10,-.18-j*.039,.55-j*.011),.007,m['ivory'])
        sphere('trouser leg',(x,.035,.78),(.20,.20,.39),jacket,segments=24,rings=16)
        sphere('rounded knee patch',(x,-.16,.73),(.15,.045,.17),leather,segments=20,rings=10)
        box('cargo trouser pocket',(x+s*.17,.0,.90),(.08,.21,.22),jacket,bevel=.025)
    sphere('jacket torso',(0,.025,1.34),(.42,.255,.48),jacket,segments=32,rings=20)
    sphere('jacket hem',(0,.02,1.05),(.41,.25,.13),leather,segments=28,rings=12)
    box('belt buckle',(0,-.238,1.06),(.14,.035,.105),m['brass'],bevel=.015)
    for s in [-1,1]:
        box('breast pocket',(s*.19,-.22,1.43),(.19,.055,.20),jacket,bevel=.025)
        box('pocket flap',(s*.19,-.255,1.49),(.205,.025,.06),leather,bevel=.013)
        sphere('pocket button',(s*.19,-.275,1.48),(.014,.008,.014),m['brass'],segments=10,rings=6)
    beam('jacket zipper',(0,-.25,1.12),(0,-.25,1.63),.009,m['brass'])
    cylinder('neck',(0,0,1.79),.13,.23,skin,vertices=24,bevel=.035)
    sphere('large survivor head',(0,-.015,2.075),(.32,.275,.345),skin,segments=40,rings=24)
    for s in [-1,1]:
        sphere('ear',(s*.31,.0,2.06),(.07,.052,.105),skin,segments=20,rings=12)
        sphere('cheek',(s*.17,-.23,2.0),(.115,.07,.10),skin,segments=24,rings=12)
        sphere('eye white',(s*.115,-.265,2.115),(.061,.026,.045),m['ivory'],segments=20,rings=12)
        sphere('dark pupil',(s*.115,-.289,2.115),(.026,.012,.029),m['black'],segments=16,rings=10)
        cable('eyebrow',[(s*.115-.055,-.28,2.174),(s*.115,-.293,2.19),(s*.115+.055,-.28,2.177)],.015,leather)
    sphere('rounded nose',(0,-.302,2.06),(.078,.083,.066),skin,segments=24,rings=14)
    cable('wry smile',[(-.075,-.266,1.955),(0,-.290,1.944),(.075,-.266,1.96)],.009,m['black'])
    if key in ['mechanic-repair-crew','mercenary-ex-mil','licensed-driver']:
        for s in [-1,1]:sphere('comical moustache',(s*.061,-.286,1.996),(.075,.029,.035),leather,segments=20,rings=10)
    # Neck scarf and fluttering tail, separate from painted skin.
    sc=denim if key in ['citizen-harvester','licensed-driver'] else m['ivory'] if key=='scout' else scarf
    torus('wrapped fabric scarf',(0,0,1.79),.185,.067,sc,major_segments=32,minor_segments=12)
    cloth('scarf tail',[(.12,-.21,1.80),(.27,-.20,1.77),(.20,-.25,1.38),(.36,-.23,1.46)],sc,sag=.025,flutter=.02,subdivisions=(9,15))
    # Backpacks, straps, bedrolls and side pouches make role readable from behind too.
    box('rounded canvas backpack',(0,.34,1.42),(.59,.28,.66),leather,bevel=.11)
    for s in [-1,1]:
        cable('shoulder carrying strap',[(s*.23,.31,1.65),(s*.31,.01,1.70),(s*.26,-.25,1.47),(s*.25,-.25,1.08)],.026,leather)
        box('belt utility pouch',(s*.37,.0,1.13),(.17,.20,.25),leather,bevel=.045)
    cylinder('backpack rolled blanket',(0,.36,1.83),.13,.63,sc,rotation=(0,math.pi/2,0),vertices=24,bevel=.025)
    for x in [-.20,.20]:torus('bedroll strap',(x,.36,1.83),.134,.013,leather,rotation=(0,math.pi/2,0),major_segments=20,minor_segments=6)
    holding=key in ['crew-worker','citizen-harvester','rifle-guard','shotgun-raider','mercenary-ex-mil','mercenary-free-agent']
    for s in [-1,1]:
        shoulder=Vector((s*.37,.0,1.62));elbow=Vector((s*.52,-.03,1.30));hand=Vector((s*.30,-.40,1.22)) if holding else Vector((s*.51,-.07,1.03))
        def limb(name,a,b,r,mat):
            ob=sphere(name,(a+b)/2,(r,r,(b-a).length*.65),mat,segments=24,rings=16);ob.rotation_euler=(b-a).to_track_quat('Z','Y').to_euler()
        limb('jacket sleeve upper',shoulder,elbow,.17,jacket);limb('forearm sleeve',elbow,hand,.135,jacket)
        sphere('work glove',hand,(.13,.105,.13),leather,segments=24,rings=14)
        sphere('gloved thumb',hand+Vector((-s*.08,-.04,.04)),(.055,.065,.075),leather,segments=18,rings=10)
    if key in ['scavenger','mercenary-free-agent']:
        # A rounded cloth hood with a genuine face aperture and covered crown.
        import bmesh
        hood=sphere('rounded fabric hood',(0,.035,2.13),(.368,.326,.42),fabric if key=='scavenger' else leather,segments=40,rings=24)
        bm=bmesh.new();bm.from_mesh(hood.data)
        remove=[]
        for face in bm.faces:
            c=hood.matrix_world@face.calc_center_median()
            if c.y < -.09 and 1.90 < c.z < 2.34:remove.append(face)
        bmesh.ops.delete(bm,geom=remove,context='FACES');bm.to_mesh(hood.data);bm.free();hood.data.update()
        mod=hood.modifiers.new('hood fabric thickness','SOLIDIFY');mod.thickness=.012
        cable('hood face hem',[(-.27,-.16,1.91),(-.31,-.18,2.08),(-.25,-.22,2.30),(0,-.25,2.36),(.25,-.22,2.30),(.31,-.18,2.08),(.27,-.16,1.91)],.018,fabric if key=='scavenger' else leather)

    else:
        hat=m['yellow'] if key=='crew-worker' else m['ivory'] if key=='field-medic' else fabric
        if key=='citizen-harvester':
            cylinder('broad harvest hat brim',(0,0,2.31),.47,.04,m['wood'],vertices=40,bevel=.018)
            cone('straw hat crown',(0,0,2.38),.26,.18,.20,m['wood'],vertices=32,bevel=.04)
        elif heavy:
            box('raised welding visor',(0,-.19,2.17),(.65,.18,.59),m['yellow'],bevel=.09);box('welding visor glass',(0,-.291,2.24),(.42,.025,.17),m['window'],bevel=.025)
        else:
            sphere('helmet crown',(0,.015,2.31),(.35,.30,.17),hat,segments=32,rings=16)
            box('helmet short brim',(0,-.24,2.29),(.59,.24,.035),hat,bevel=.06)
            if key=='shotgun-raider':
                for x in [-.18,0,.18]:cone('raider helmet spike',(x,0,2.54),.06,0,.24,m['steel'],vertices=10)
            for s in [-1,1]:
                torus('raised goggles frame',(s*.13,-.265,2.32),.085,.018,m['brass'],rotation=(math.pi/2,0,0),major_segments=24,minor_segments=8)
                cylinder('goggle glass',(s*.13,-.267,2.32),.068,.018,m['window'],rotation=(math.pi/2,0,0),vertices=24,bevel=.008)
    if key in ['crew-worker','citizen-harvester']:
        crate('carried supplies',(0,-.62,.94),m,w=.69,d=.48,h=.45)
        if key=='citizen-harvester':
            for i in range(5):plant('harvest greens',(-.25+i*.12,-.63,1.43),m,i,.8)
    elif key in ['rifle-guard','shotgun-raider','mercenary-ex-mil','mercenary-free-agent']:
        gun(m,(-.04,-.50,1.24),'shotgun' if key=='shotgun-raider' else 'rifle',.62)
    elif key=='mechanic-repair-crew':
        beam('oversized spanner shaft',(-.54,-.08,.89),(-.67,-.08,1.70),.046,m['steel'],vertices=8)
        torus('spanner open jaw',(-.69,-.08,1.82),.14,.038,m['steel'],rotation=(math.pi/2,0,0),major_segments=20,minor_segments=8)
        box('red toolbox',(.58,-.04,.82),(.43,.29,.35),m['red'],bevel=.045)
    elif key=='field-medic':
        box('medical case',(.57,-.07,.82),(.42,.29,.37),m['ivory'],bevel=.04)
        for c,w,h in [((.57,-.22,.82),.23,.065),((.57,-.222,.82),.065,.23),((0,-.30,2.31),.16,.047),((0,-.301,2.31),.047,.16)]:box('red medical cross',c,(w,.009,h),m['red'],bevel=.005)
    elif key=='scavenger':
        beam('metal detector shaft',(.52,-.08,1.09),(.79,-.57,.34),.024,m['iron']);torus('detector search coil',(.79,-.61,.28),.19,.018,m['iron'],major_segments=24,minor_segments=8)
    elif key=='scout':lantern('scout carried lantern',(.54,-.06,.76),m)
    elif key=='heavy-vehicle-operator':
        for s in [-1,1]:sphere('large yellow shoulder armor',(s*.40,0,1.59),(.23,.23,.18),m['yellow'],segments=24,rings=14)
    else:
        sphere('driver thumbs up',(.55,-.13,1.16),(.055,.06,.16),skin,segments=20,rings=12)


def ruins(m,c=(0,0,.24),w=2.5,d=1.8,h=2.4):
    x,y,z=c
    # Window openings constructed from fragments, leaving actual gaps.
    for j in range(4):
        xx=x-w/2+j*w/3;hh=h*(.68+.25*math.sin(j*2.1)**2)
        box('broken masonry pier',(xx,y+d/2,z+hh/2),(.28,.28,hh),m['stone'],bevel=.035)
    for zz in [.30,1.15,2.05]:
        box('ruin window lintel',(x,y+d/2,z+zz),(w,.27,.20),m['stone'],bevel=.035)
    for j in range(3):box('broken side wall',(x-w/2,y-d*.3+j*d*.35,z+h*(.30+j*.10)),(.28,d*.38,h*(.60+j*.20)),m['stone'],bevel=.04)
    rng=random.Random(45)
    for j in range(24):
        p=(x+rng.uniform(-w/2,w/2),y+rng.uniform(-d/2,d/2),z+.09);ob=box('fallen masonry',p,(rng.uniform(.12,.35),.17,.16),m['stone'],rotation=(.1,.15,rng.random()*3),bevel=.02)
    for xx in [x-.8,x+.4]:beam('exposed reinforcing rod',(xx,y+d/2,z+2),(xx+.12,y+d/2,z+2.45),.014,m['rust'])


def world(key,m):
    base(m,5.8,4.5)
    if key=='ruined-town-block':
        ruins(m,(-.5,.5,.24),3.1,2.0,2.9)
        box('abandoned small red car',(1.35,-.75,.63),(1.15,.64,.40),m['red'],bevel=.15);box('car roof',(1.30,-.71,.94),(.62,.57,.33),m['window'],bevel=.11)
        for x in [1.0,1.70]:
            for y in [-1.08,-.42]:cylinder('abandoned car wheel',(x,y,.46),.19,.13,m['rubber'],rotation=(math.pi/2,0,0),vertices=20,bevel=.02)
    elif key in ['survivor-outpost-cluster','major-city-tower-district']:
        dense=key=='major-city-tower-district'
        for i,(x,y,z,w,h) in enumerate([(-1.45,.48,1.19,1.8,1.9),(.65,.69,1.38,2.2,2.25),(-.25,.65,3.06,1.8,1.12)]):
            shell(m,(x,y,z),w,1.65,h,paint=['teal','ivory','blue'][i]);window((x-.27,y-.84,z+.12),m);ladder(x+w*.38,y-.75,h,m,z-h/2)
        canopy(m,(-1.0,-.75,2.35),2.5,1.50)
        tower(m,(1.78,-.17,.24),3.2,1.1,True)
        if dense:
            shell(m,(-1.70,.8,3.98),1.45,1.5,1.35,paint='ivory')
            for z in [2.65,3.50]:
                box('district balcony',(-.80,-.48,z),(2.3,.76,.09),m['wood'],bevel=.015)
                for x in [-1.85,-1.3,-.7,-.1,.25]:beam('balcony rail post',(x,-.81,z),(x,-.81,z+.48),.024,m['iron'])
                beam('balcony handrail',(-1.9,-.81,z+.49),(.3,-.81,z+.49),.029,m['iron'])
            crane(m,.75)
        sign((-.3,-1.56,1.4),['STILL HERE','STILL TRYING'],m,1.2,1.1)
    elif key=='regional-scrap-market-gate':
        for x in [-1.8,1.8]:shell(m,(x,.3,1.35),1.28,2.3,2.2,paint='teal');ladder(x,.1,2.4,m)
        for z in [2.63,3.1]:beam('market overhead beam',(-2.50,.35,z),(2.50,.35,z),.10,m['yellow'],vertices=4)
        for j in range(8):beam('overhead truss diagonal',(-2.5+j*.625,.35,2.63),(-1.875+j*.625,.35,3.1),.036,m['iron'])
        sign((0,-.20,2.55),['TRADE FAIR','LEAVE HAPPY'],m,2.65,1.15);cable('hanging crane hook',[(.70,.3,2.9),(.70,.3,1.40),(.87,.3,1.27),(.98,.3,1.43)],.026,m['iron'])
    elif key=='rail-checkpoint':
        for x in [-.46,.46]:beam('rail track',(x,-2.15,.27),(x,2.15,.27),.047,m['steel'],vertices=4)
        for j in range(12):box('railway sleeper',(0,-2+j*.35,.23),(1.43,.16,.10),m['wood'],bevel=.016)
        shell(m,(-1.55,.25,1.18),1.25,1.4,1.8,paint='ivory');window((-1.55,-.47,1.42),m)
        tower(m,(1.45,.58,.24),2.5,1.0,True)
        beam('rail barrier pole',(-1.3,-.75,.24),(-1.3,-.75,1.20),.065,m['yellow'])
        box('rail crossing barrier',(0,-.75,1.14),(2.70,.11,.15),m['ivory'],bevel=.025)
        for x in [-1,-.5,0,.5,1]:box('barrier red stripes',(x,-.815,1.14),(.18,.015,.155),m['red'],rotation=(0,.15,0),bevel=.006)
        cylinder('red signal lamp',(1.45,.04,2.57),.16,.16,m['red'],rotation=(math.pi/2,0,0),vertices=24)
    elif key=='bridge-fragment':
        for s in [-1,1]:
            x=s*1.6;box('bridge concrete pier',(x,.0,.8),(.62,1.55,1.15),m['stone'],bevel=.06)
            box('broken bridge deck',(s*1.83,0,1.48),(1.85,1.85,.25),m['stone'],bevel=.045)
            for y in [-.85,.85]:
                for xx in [s*.95,s*1.55,s*2.30]:beam('bridge railing upright',(xx,y,1.6),(xx,y,2.15),.036,m['iron'])
                beam('broken bridge handrail',(s*.75,y,2.14),(s*2.6,y,2.14),.038,m['iron'])
            for j in range(6):beam('hanging broken rebar',(s*.90,-.65+j*.25,1.45),(s*.45,-.60+j*.24,1.18-j*.035),.013,m['rust'])
        for j in range(10):sphere('bridge fall rubble',(.5*math.sin(j),.6*math.cos(j),.27),(.22,.18,.12),m['stone'],segments=8,rings=5)
    elif key=='major-city-wall-section':
        for x in [-2.0,2.0]:tower(m,(x,.40,.24),3.40,1.25,True)
        for j in range(5):corrugated('city defensive panel',(-1.32+j*.66,.25,1.45),.68,2.4,m['teal' if j%2 else 'ivory'],seed=j)
        box('wall walkway',(0,.54,2.75),(3.8,1.0,.12),m['wood'],bevel=.018)
        for x in [-1.5,-.75,0,.75,1.5]:beam('city wall crenellation',(x,.20,2.75),(x,.20,3.12),.07,m['iron'],vertices=4)
        sign((0,.17,1.80),['BAD PEOPLE','STAY OUT'],m,1.25,1.2)
    elif key=='asteroid-impact-crater-rig':
        # Annular uneven crater rim with a depressed glowing core.
        verts=[];faces=[];N=48
        for r,z in [(1.95,.24),(1.53,.77),(.98,.33),(.75,.23)]:
            for j in range(N):
                a=j*math.tau/N;verts.append((r*math.cos(a),r*.77*math.sin(a),z+.08*math.sin(j*2.4)))
        for k in range(3):
            for j in range(N):faces.append((k*N+j,k*N+(j+1)%N,(k+1)*N+(j+1)%N,(k+1)*N+j))
        mesh('impact crater rim',verts,faces,m['stone']);anomaly(m,(0,0,.64),.55);crane(m,.6)
        shell(m,(1.78,.52,1.1),1.1,1.2,1.7,paint='yellow')
    elif key=='meteor-reactor':
        cylinder('reactor foundation',(0,0,.58),1.28,.64,m['teal'],vertices=32,bevel=.07)
        anomaly(m,(0,0,2.17),.93)
        for z,r in [(1.27,1.34),(2.66,1.45)]:torus('reactor containment ring',(0,0,z),r,.10,m['steel'],major_segments=48,minor_segments=12)
        for j in range(6):
            a=j*math.tau/6;beam('reactor containment upright',(1.32*math.cos(a),1.32*math.sin(a),.5),(1.45*math.cos(a),1.45*math.sin(a),2.64),.07,m['yellow'])
        for x in [-1.9,1.9]:shell(m,(x,.25,.82),.95,1.5,1.1,paint='ivory')
    elif key=='sky-tracker-dish':
        shell(m,(0,.15,1.08),2.65,2.3,1.65,paint='ivory');window((-.65,-1.01,1.22),m)
        dish(m,(0,.2,2.36),1.45);ladder(1.45,-.08,2.10,m);sign((.54,-1.04,1.12),['STILL','LISTENING'],m,.83,1.0)
    elif key=='strange-late-tech-salvage-structure':
        for r in [1.08,1.47,1.82]:
            torus('standing anomaly ring',(0,.45,2.20),r,.12,m['iron'],rotation=(math.pi/2,0,.07),major_segments=48,minor_segments=12)
            for j in range(8):
                a=j*math.tau/8;box('ring luminous insert',(r*math.cos(a),.30,2.2+r*math.sin(a)),(.17,.09,.10),m['cyan'],rotation=(0,-a,0),bevel=.02)
        anomaly(m,(0,.42,2.18),.43)
        for x in [-1.5,1.5]:beam('portal footing',(x,.5,.24),(x,.5,1.35),.17,m['yellow'],vertices=4)
        canopy(m,(-1.60,-.70,1.65),1.8,1.3);crate('anomaly instruments',(-1.45,-.75,.23),m,w=.7,d=.5,h=.5)
    clutter(m,[(-2.4,-1.55),(2.4,1.5)])
