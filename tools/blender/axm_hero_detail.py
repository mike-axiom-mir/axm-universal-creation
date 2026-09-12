"""Authored close-up passes: shaped armour, hardware, local wear and fur detail."""
import math
import random
import bpy
from mathutils import Vector
import axm_blender_forge as geo


def replace_armour(h):
    definitions={
        'Curved yellow breastplate':(.61,.47,.48,'yellow',0),
        'Thigh patch shell':(.238,.235,.275,None,0),
        'Shin armour':(.255,.217,.30,None,0),
        'Bulky forearm ivory armour':(.285,.268,.34,'ivory',.31),
        'Forearm yellow side panel':(.13,.22,.27,'yellow',.31),
        'Shoulder armour':(.32,.29,.285,None,.28),
    }
    replacements=[]
    for old in list(h.parts):
        key=next((n for n in definitions if old.name.startswith(n)),None)
        if not key:continue
        w,d,z,color,tilt=definitions[key];bone=old['axm_bone'];center=old.location.copy()
        material=h.mat[color] if color else old.data.materials[0]
        sign=-1 if center.x<0 else 1
        ob=geo.armored_cowl(old.name+' shaped forged shell',tuple(center),(w,d,z),material,bevel=.016,rotation=(0,-sign*tilt,0))
        h.bind(ob,bone);h.parts.remove(old);bpy.data.objects.remove(old,do_unlink=True);replacements.append(ob)
    return replacements


def rim_panel(h,n,c,rx,ry,height,m,bone,phase=0):
    """A real open curved armour plate with flanged edges and fasteners."""
    x,y,z=c;vs=[];fs=[];ncol,nrow=28,8
    def point(u,v):
        angle=math.pi*.98+u*math.pi*1.04+phase
        taper=.87+.13*math.sin(math.pi*v)
        return (x+rx*taper*math.cos(angle),y+ry*taper*math.sin(angle),z+(v-.5)*height)
    for j in range(nrow+1):
        for i in range(ncol+1):vs.append(point(i/ncol,j/nrow))
    for j in range(nrow):
        for i in range(ncol):q=j*(ncol+1)+i;fs.append((q,q+1,q+ncol+2,q+ncol+1))
    ob=h.mesh(n,vs,fs,m,bone)
    so=ob.modifiers.new('Plate gauge','SOLIDIFY');so.thickness=.010
    for v in [0,1]:h.line(n+' rolled edge',[point(i/20,v) for i in range(21)],.006,'steel',bone)
    for u in [.12,.88]:
        for v in [.17,.83]:
            a=point(u,v);h.bolt(n+' fixing',(a[0],a[1]-.006,a[2]),.008,bone=bone)
    return ob


def hardware(h):
    for s,side in [(-1,'R'),(1,'L')]:
        bone='UpperArm.'+side
        # Layered pauldrons and the exposed ring assembly beneath them.
        rim_panel(h,'Layered shoulder pauldron',(s*.43,-.024,1.38),.165,.153,.19,'yellow' if s<0 else 'ivory',bone)
        for z in [1.26,1.284]:h.ring('Shoulder split ring',(s*.45,0,z),.107,.009,'iron',axis=(0,0,1),bone=bone)
        h.plate('Shoulder repair patch',(s*.455,-.184,1.41),(.065,.009,.085),'steel',bone=bone)
        h.text('Pauldron stencil','07' if s<0 else 'AXM',(s*.397,-.176,1.344),.030,bone=bone)
        bone='Forearm.'+side
        rim_panel(h,'Forearm overlapping faceplate',(s*.615,-.033,1.078),.146,.14,.22,'ivory',bone)
        h.plate('Forearm service hatch',(s*.615,-.18,1.083),(.113,.018,.079),'ivory',bone=bone)
        for j in range(4):h.box('Forearm vent',(s*.615-.032+j*.021,-.194,1.083),(.010,.005,.046),'iron',.002,bone=bone)
        for y in [-.037,.04]:
            a=(s*.73,y,1.18);b=(s*.79,y,1.00)
            h.beam('Exposed forearm hydraulic strut',a,b,.014,'steel',bone)
            h.beam('Hydraulic strut casing',a,(s*.765,y,1.10),.021,'iron',bone)
            for c in [a,b]:h.ball('Strut rod end',c,(.025,.020,.024),'brass',bone,16,10)
        h.ring('Forearm rotating wrist collar',(s*.66,-.03,.978),.103,.013,'brass',axis=(s*.35,-.1,-1),bone=bone)
        bone='Thigh.'+side
        h.beam('Exposed thigh cylinder',(s*.32,.025,.89),(s*.36,-.01,.68),.026,'steel',bone)
        for z in [.85,.82,.79]:h.ring('Hip concertina',(s*.23,0,z),.093,.006,'iron',axis=(0,0,1),bone=bone)
        bone='Shin.'+side
        rim_panel(h,'Curved shin front guard',(s*.28,-.015,.405),.126,.145,.20,'yellow' if s<0 else 'ivory',bone)
        for x in [s*.28-.099,s*.28+.099]:
            h.beam('Side shin piston',(x,.025,.52),(x,.06,.265),.016,'steel',bone)
            h.beam('Shin piston housing',(x,.025,.52),(x,.041,.40),.026,'iron',bone)
        for x in [s*.27-.126,s*.27+.126]:
            h.cyl('Knee pivot washer',(x,-.07,.57),.058,.018,'steel',(1,0,0),32,bone)
            h.cyl('Knee pivot recess',(x+(.010 if x>s*.27 else -.010),-.07,.57),.032,.012,'iron',(1,0,0),24,bone)
            h.cyl('Knee pivot axle',(x+(.018 if x>s*.27 else -.018),-.07,.57),.018,.011,'brass',(1,0,0),6,bone)
        bone='Foot.'+side
        for x in [s*.28-.174,s*.28+.174]:
            h.box('Toe lateral scuff rail',(x,-.16,.11),(.025,.28,.052),'steel',.010,bone=bone)
            for y in [-.25,-.13,.01]:h.cyl('Boot side rivet',(x+(.014 if x>s*.28 else -.014),y,.12),.007,.009,'steel',(1,0,0),6,bone)
        h.plate('Boot instep nameplate',(s*.28,-.191,.281),(.135,.01,.052),'ivory','SQUEAK' if s<0 else 'AXM',.020,bone)
        for i in range(8):
            y=-.35+i*.065
            for x in [s*.28-.18,s*.28+.18]:h.box('Deep side tread',(x,y,.04),(.06,.035,.04),'rubber',.007,rot=(0,0,s*.25),bone=bone)
        bone='Hand.'+side
        h.ring('Wrist brass ring',(s*.65,-.028,.945),.092,.012,'brass',axis=(0,0,1),bone=bone)
        for i,dx in enumerate([-.068,-.023,.023,.068]):
            b=f'Finger{i}.01.{side}';x=s*.65+dx
            for z in [.90,.917]:h.box('Knuckle protective ridge',(x,-.145,z),(.034,.012,.011),'steel',.003,bone=b)
            h.bolt('Finger cap screw',(x,-.15,.94),.004,bone=b)
    # Chest seam hardware and the little tools tell the character's trade.
    h.current='Chest'
    for z,w in [(1.055,.45),(1.32,.43)]:
        h.line('Chest edge piping',[(-w/2,-.17,z),(-w*.35,-.24,z),(0,-.29,z),(w*.35,-.24,z),(w/2,-.17,z)],.006,'steel')
    for s in [-1,1]:
        for i in range(7):h.bolt('Chest fixing row',(s*.278,-.17,1.095+i*.038),.006)
        for j in range(10):
            z=1.13+j*.025;x=s*(.237-.018*(z-1.13)/.25)
            h.line('Harness hand stitching',[(x-.006,-.287,z),(x+.006,-.287,z+.008)],.0014,'ivory')
    h.line('Coiled power lead',[(.30,.02,1.34),(.34,-.10,1.24),(.35,-.12,1.09),(.31,-.04,1.01)],.010,'teal')
    for j in range(7):h.ring('Cable plug knurl',(.31,-.04,1.018+j*.008),.019,.003,'brass',axis=(0,0,1))
    # Overlapping scrap repair tabs; nonuniform placement avoids a tiled prop feel.
    h.plate('Small chest patch',(-.10,-.286,1.329),(.05,.011,.071),'teal')
    h.plate('Chest serial plate',(.15,-.254,1.235),(.073,.010,.027),'steel','AXM-01',.010)
    h.current='Pelvis'
    for s in [-1,1]:
        h.line('Pocket flap stitch',[(s*.27,-.15,1.15),(s*.31,-.151,1.16),(s*.34,-.15,1.15)],.002,'ivory')
    h.cyl('Hip flashlight',(-.41,.053,.97),.027,.20,'teal')
    h.ring('Flashlight head',(-.41,.053,1.074),.032,.009,'steel',axis=(0,0,1))
    h.cyl('Flashlight lens',(-.41,.053,1.08),.024,.006,'lens')
    for i in range(5):h.ring('Flashlight grip ridge',(-.41,.053,.90+i*.016),.027,.004,'iron',axis=(0,0,1))


def sculptural_face(h):
    h.current='Head';rng=random.Random(4771)
    # Tapered muzzle volumes join the smile corners to the cheeks.
    for s in [-1,1]:
        h.tapered('Smile corner cheek',[(s*.205,-.248,1.579),(s*.259,-.217,1.577),(s*.28,-.177,1.64)], [.018,.047,.018],'fur')
        h.line('Nose cheek fold',[(s*.048,-.304,1.652),(s*.078,-.30,1.621),(s*.112,-.29,1.608)],.003,'skin')
        for j in range(14):
            a=1.1+j*.105;p=Vector((s*(.26+.033*math.sin(a)), -.12-.025*math.cos(a),1.46+j*.016))
            h.tapered('Cream cheek tuft',[p,p+Vector((s*.013,-.025,-.013)),p+Vector((s*.025,-.020,-.025))],[.008,.006,.0008],'fur')
    # Individual eyebrows/hair scratches follow the already shaped hair locks.
    for side,s in [('R',-1),('L',1)]:
        bone='Brow.'+side
        for j in range(24):
            u=j/23
            x=(-.29+.24*u) if s<0 else (.08+.21*u)
            z=(1.895+.076*math.sin(math.pi*u)) if s<0 else (1.895+.041*math.sin(math.pi*u))
            y=-.25-.053*math.sin(math.pi*u)
            h.line('Brow fine strand',[(x,y-.009,z),(x+.008*s,y-.012,z+.018),(x+.014*s,y-.006,z+.027)],.0012,'hair',bone)
    for j in range(26):
        x=-.14+j*.008
        h.line('Quiff strand',[(x,-.104,2.025),(x-.04,-.111,2.07),(x-.062,-.103,2.083)],.0016,'hair')
    # Tiny cheek pores and whisker roots are bounded geometry, not black dirt patches.
    for s in [-1,1]:
        for j in range(12):
            x=s*(.24+rng.uniform(-.018,.012));z=1.603+rng.uniform(-.025,.035)
            h.ball('Cheek fur root',(x,-.237,z),(.0014,.0011,.0015),'hair',segments=8,rings=6)
    h.current='Jaw'
    for j in range(40):
        x=(j/39-.5)*.35;z=1.337+.03*(abs(x)/.18)**1.4
        h.tapered('Soft chin tuft',[(x,-.23,z+.02),(x,-.245,z),(x+.002,-.24,z-.008)],[.004,.003,.0006],'fur')


def surface_wear(h):
    """Project tiny metal chips onto evaluated painted shells; no floating decals."""
    rng=random.Random(7100471);bpy.context.view_layer.update();batches={}
    candidates=[o for o in h.parts if o.type=='MESH' and o.data.materials and o.data.materials[0] in [h.mat[k] for k in ['yellow','ivory','teal','steel']]]
    for ob in candidates:
        if len(ob.data.polygons)<30 or max(ob.dimensions)<.10:continue
        ev=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());inv=ob.matrix_world.inverted()
        corners=[ob.matrix_world@Vector(c) for c in ob.bound_box];lo=Vector([min(v[i] for v in corners) for i in range(3)]);hi=Vector([max(v[i] for v in corners) for i in range(3)])
        vs,fs=batches.setdefault(ob['axm_bone'],([],[]))
        for i in range(38):
            origin=Vector((rng.uniform(lo.x,hi.x),lo.y-.1,rng.uniform(lo.z,hi.z)))
            hit,p,n,_=ev.ray_cast(inv@origin,inv.to_3x3()@Vector((0,1,0)))
            if not hit:continue
            n=(ob.matrix_world.to_3x3()@n).normalized();p=ob.matrix_world@p
            if abs(n.y)>.93 and rng.random()>.16:continue
            tangent=n.cross(Vector((0,0,1)))
            if tangent.length<.1:continue
            tangent.normalize();other=n.cross(tangent).normalized()
            length=rng.uniform(.002,.009);width=rng.uniform(.0008,.0023);p+=n*.0007
            base=len(vs);vs.extend([tuple(p-tangent*length-other*width),tuple(p+tangent*length-other*width*.3),tuple(p+tangent*length*.6+other*width),tuple(p-tangent*length*.5+other*width*.7)])
            fs.append((base,base+1,base+2,base+3))
    for bone,(vs,fs) in batches.items():
        if vs:h.mesh('Projected local paint chips '+bone,vs,fs,'steel',bone,smooth=False)


def upgrade(h):
    replace_armour(h);hardware(h);sculptural_face(h);surface_wear(h)
    from axm_hero_closeup import finish
    finish(h)
