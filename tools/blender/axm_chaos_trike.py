"""Detailed reference-directed AXM comedy trike with portable articulated rig."""
import argparse,hashlib,json,math
from pathlib import Path
import bpy
from mathutils import Vector,Matrix
from axm_chaos_hero import Hero
from axm_hero_motion import rig,clean_triangles,translate
from axm_oops_character import reset_pose
from axm_salvage_surfaces import solid
import axm_blender_forge as geo
TAU=math.tau
CLIPS=[('Engine_Idle',2,True),('Drive_Cycle',2,True),('Steer_Left',1,False),('Steer_Right',1,False),('Suspension_Bounce',2,True),('Duck_Honk',1,True)]
WHEELS={'Front':((0,-1.08,.64),.64,.50),'Rear.L':((-.73,.85,.49),.49,.40),'Rear.R':((.73,.85,.49),.49,.40)}
def turn_parts(h,start,c,angle):
    bpy.context.view_layer.update()
    mat=Matrix.Translation(c)@Matrix.Rotation(angle,4,'Z')@Matrix.Translation(-Vector(c))
    for o in h.parts[start:]:o.matrix_world=mat@o.matrix_world
def sideplate(h,n,c,d,m,label,size=.055,side=1):
    start=len(h.parts);h.plate(n,c,d,m,label,size)
    x,y,z=c
    if label:
        for dx in [-d[0]*.36,d[0]*.36]:
            h.box(n+' latch',(x+dx,y-d[1]/2-.027,z+d[2]*.31),(.055,.025,.075),'steel',.008)
        h.line(n+' carry handle',[(x-.10,y,z+d[2]/2),(x-.10,y,z+d[2]/2+.07),(x+.10,y,z+d[2]/2+.07),(x+.10,y,z+d[2]/2)],.012,'leather')
    for i in range(55):
        px=x+h.rng.uniform(-.45,.45)*d[0];pz=z+h.rng.uniform(-.44,.44)*d[2]
        q=h.rng.uniform(.003,.013)
        h.mesh(n+' paint wear',[(px-q,y-d[1]/2-.016,pz),(px+q,y-d[1]/2-.016,pz+q*.3),(px+q*.4,y-d[1]/2-.016,pz+q)],[(0,1,2)],'iron',smooth=False)
    turn_parts(h,start,c,side*math.pi/2)
def spring(h,n,a,b,r=.07,wire=.012,coils=10,m='red'):
    a,b=Vector(a),Vector(b);v=(b-a).normalized();u=v.cross(Vector((1,0,0))).normalized();w=v.cross(u)
    pts=[tuple(a+(b-a)*t+ r*(u*math.cos(TAU*coils*t)+w*math.sin(TAU*coils*t))) for t in [i/160 for i in range(161)]]
    h.line(n,pts,wire,m);h.beam(n+' piston',a,b,.023,'steel')
def wheel(h,key,c,r,width):
    h.current='Wheel.'+key;x,y,z=c
    # Radial tire profile: true tread crown, shoulders and sidewalls.
    profile=[(-width*.50,r*.60),(-width*.56,r*.76),(-width*.50,r*.93),(-width*.35,r),(width*.35,r),(width*.50,r*.93),(width*.56,r*.76),(width*.50,r*.60)]
    vs=[];fs=[];n=80
    for px,rr in profile:
        for i in range(n):t=i*TAU/n;vs.append((x+px,y+rr*math.sin(t),z+rr*math.cos(t)))
    for j in range(len(profile)-1):
        for i in range(n):a=j*n+i;b=j*n+(i+1)%n;fs.append((a,b,b+n,a+n))
    h.mesh(key+' tire carcass',vs,fs,'rubber')
    for i in range(40):
        t=i*TAU/40
        for row in [-1,0,1]:
            tt=t+row*.025;p=(x+row*width*.28,y+(r+.009)*math.sin(tt),z+(r+.009)*math.cos(tt))
            h.box('Chevron tread',p,(width*.30,.075,.028),'rubber',.008,rot=(-tt,0,row*.17))
    for s in [-1,1]:
        h.cyl('Wheel inner rim',(x+s*width*.45,y,z),r*.68,.06,'iron',(1,0,0),64)
        h.ring('Machined rim lip',(x+s*width*.56,y,z),r*(.88 if key=='Front' else .70),.022,'steel',(1,0,0))
        material='yellow' if key=='Front' else 'ivory'
        h.cyl('Armored hub plate',(x+s*width*.60,y,z),r*(.86 if key=='Front' else .68),.035,material,(1,0,0),64)
        h.cyl('Axle hub',(x+s*(width*.65+.03),y,z),r*.19,.10,'iron',(1,0,0),40)
        h.ring('Bearing collar',(x+s*(width*.65+.08),y,z),r*.15,.02,'brass',(1,0,0))
        for j in range(12):
            t=j*TAU/12
            h.bolt('Wheel lug',(x+s*width*.64,y+r*(.80 if key=='Front' else .61)*math.sin(t),z+r*(.80 if key=='Front' else .61)*math.cos(t)),.014,(s,0,0))
        # Markings rotate with wheel; front comic smile above hub.
        p=(x+s*width*.66,y-.17,z+.23);start=len(h.parts)
        if key=='Front':
            h.smile(p,.09);h.text('Squeak label','SQUEAK!',(p[0],p[1],p[2]-.18),.055)
        else:h.logo('Hub AXM',p,.18,'ink')
        turn_parts(h,start,p,s*math.pi/2)
def build(h):
    h.bone('Root',(0,0,0),(0,0,.2))
    h.bone('Chassis',(0,0,.95),(0,0,1.15),'Root')
    for key,(c,r,w) in WHEELS.items():
        h.bone('Suspension.'+key,c,(c[0],c[1],c[2]+.2),'Root')
        parent='Suspension.'+key
        if key=='Front':h.bone('Steering',c,(c[0],c[1],c[2]+.2),parent);parent='Steering'
        h.bone('Wheel.'+key,c,(c[0]+.2,c[1],c[2]),parent)
    h.bone('SteeringWheel',(0,-.39,1.65),(0,-.49,1.79),'Chassis')
    h.bone('Duck',(0,-.18,2.55),(0,-.18,2.8),'Chassis')
    h.bone('Flag',(.46,.55,2.62),(.46,.55,2.9),'Chassis')
    h.bone('Cape',(0,.72,2.03),(0,1.05,1.94),'Chassis')
    h.bone('DriverSeat',(0,.28,1.39),(0,.28,1.6),'Chassis')
    h.bone('CompanionDock',(-.53,.67,2.15),(-.53,.67,2.3),'Chassis')
    h.current='Chassis'
    h.mat['lamp']=solid('Warm headlamp','#ffb944',0,.2,1.2)
    h.mat['cyan']=solid('Trike cyan lens','#087384',.35,.2,.7)
    h.mat['tail']=solid('Brake lamp','#fa3529',0,.25,2)
    # Lower frame and open tubular cage.
    h.box('Underslung chassis',(0,.08,.77),(1.12,1.62,.20),'iron',.055)
    for s in [-1,1]:
        h.line('Continuous roll cage',[(s*.50,-.65,.85),(s*.51,-.56,1.28),(s*.49,-.20,2.06),(s*.46,.62,2.16),(s*.50,.83,1.20),(s*.49,.71,.86)],.038,'steel')
        h.beam('Floor rail',(s*.53,-.60,.82),(s*.53,.94,.82),.045,'iron')
        for y in [-.53,.2,.75]:
            h.cyl('Frame clamp',(s*.50,y,1.04),.058,.075,'brass',v=32)
        h.box('Foot running board',(s*.53,-.19,.93),(.26,.85,.07),'steel',.015)
        for y in [-.48,-.35,-.22,-.09,.04,.17]:h.box('Foot grip',(s*.53,y,.973),(.23,.022,.011),'iron',.002)
    for y,z in [(-.2,2.06),(.62,2.16),(.82,1.2)]:
        h.beam('Cage cross member',(-.49,y,z),(.49,y,z),.04,'steel')
    # Red bucket seat, harness slots, steering and readable gauges.
    h.box('Driver cushion',(0,.28,1.35),(.62,.61,.14),'red',.07)
    h.box('Driver backrest',(0,.58,1.71),(.67,.15,.72),'red',.08,rot=(.12,0,0))
    h.plate('Seat emblem',(0,.475,1.82),(.32,.022,.26),'red')
    h.logo('Seat crown',(0,.452,1.83),.20)
    for x in [-.22,.22]:
        h.line('Harness webbing',[(x,.47,1.98),(x,.41,1.67),(x*.7,.13,1.45)],.026,'leather')
        h.box('Harness buckle',(x*.7,.11,1.47),(.09,.035,.075),'steel',.012)
    h.box('Dash box',(0,-.40,1.41),(.63,.20,.25),'iron',.035)
    # Dashboard faces the driver (towards +Y).
    for x in [-.19,0,.19]:
        h.cyl('Instrument',(x,-.29,1.44),.060,.028,'steel',(0,1,0),32)
        h.cyl('Gauge glass',(x,-.271,1.44),.050,.012,'lens',(0,1,0),32)
        h.beam('Gauge needle',(x,-.259,1.44),(x+.022,-.259,1.465),.003,'cyan')
    h.beam('Steering column',(0,-.39,1.48),(0,-.39,1.71),.025,'steel')
    h.current='SteeringWheel';h.ring('Red steering wheel',(0,-.39,1.73),.235,.025,'red',(0,-.58,.82))
    for t in [0,TAU/3,TAU*2/3]:
        h.beam('Steering spoke',(0,-.39,1.73),(.20*math.sin(t),-.39+.14*math.cos(t),1.73+.14*math.cos(t)),.013,'steel')
    h.current='Chassis'
    # Hood: slanted cream enamel flanked by mismatched lamps.
    h.box('Sloping hood',(0,-.67,1.25),(.89,.58,.14),'ivory',.06,rot=(.35,0,0))
    h.plate('Front AXM plate',(0,-.942,1.27),(.56,.05,.23),'ivory','AXM',.12)
    for s,mat in [(-1,'lamp'),(1,'cyan')]:
        c=(s*.49,-.75,1.39)
        h.cyl('Headlamp housing',c,.19,.23,'iron',(0,-1,0),64)
        h.ring('Headlamp brass bezel',(c[0],-.88,c[2]),.169,.018,'brass')
        h.cyl('Headlamp lens',(c[0],-.898,c[2]),.148,.02,mat,(0,-1,0),64)
        if s==1:h.logo('Cyan headlamp mark',(c[0],-.912,c[2]),.19,'white')
        else:h.text('Silly headlamp','X X\n ᴗ',(c[0],-.913,c[2]),.08,'ink')
        for j in range(8):
            t=j*TAU/8;h.bolt('Lamp cage bolt',(c[0]+.18*math.sin(t),-.891,c[2]+.18*math.cos(t)),.013)
    h.duck((0,-.69,1.48),2.3,'Chassis')
    # Visible engine, cooling fins, coils, carburettor and pipe work.
    h.box('Engine block',(0,.04,1.06),(.70,.82,.40),'iron',.045)
    for s in [-1,1]:
        for y in [-.22,.02,.26]:
            h.cyl('Cylinder bank',(s*.37,y,1.15),.12,.30,'steel',(s,0,.35),40)
            for k in range(6):h.ring('Engine cooling fin',(s*(.29+k*.027),y,1.12+k*.01),.125,.009,'iron',(s,0,.35))
        h.line('Sweeping exhaust header',[(s*.38,-.36,1.18),(s*.60,-.36,1.05),(s*.57,.03,.66),(s*.30,.55,.65),(s*.26,.89,1.13)],.032,'steel')
        h.line('Red hydraulic hose',[(s*.43,-.40,.94),(s*.57,-.04,1.12),(s*.51,.54,1.43)],.018,'red')
        sideplate(h,'Yellow side armor',(s*.57,-.05,1.21),(.47,.05,.32),'yellow',None,side=s)
        sideplate(h,'Joke tool case',(s*.67,.53,1.13),(.55,.15,.49),'teal' if s==1 else 'red','GOOD\nTOOLS\nWORSE\nCHOICES' if s==1 else 'MORE\nTOOLS\nMORE\nTROUBLE',.065,s)
        for y in [.32,.72]:
            h.cyl('Side bottle',(s*.80,y,1.10),.055,.32,'brass',v=24)
            h.ring('Bottle strap',(s*.80,y,1.08),.058,.008,'iron',(0,0,1))
    h.plate('Road joke',(0,-.91,.98),(.43,.055,.29),'ivory','BAD ROADS\nBETTER STORIES',.047)
    h.cyl('Rear differential',(0,.85,.52),.19,.55,'iron',(1,0,0),48)
    h.beam('Rear axle',(-.74,.85,.49),(.74,.85,.49),.058,'steel')
    # Suspension and steerable front fork.
    for key,(c,r,w) in WHEELS.items():
        wheel(h,key,c,r,w)
        h.current='Suspension.'+key
        if key=='Front':
            h.current='Steering'
            for s in [-1,1]:
                h.beam('Steerable fork',(s*.32,-1.08,.64),(s*.30,-.57,1.5),.044,'steel')
                spring(h,'Front red shock',(s*.34,-.96,.77),(s*.32,-.66,1.29),.054,.012,10)
        else:
            x,y,z=c;spring(h,'Rear coilover',(x*.70,y,.59),(x*.67,y,1.02),.065,.012,9)
    h.current='Chassis'
    # Rear rack, tail lights and hanging fuel cylinder.
    h.box('Rear cargo rack',(0,.95,1.08),(1.10,.16,.20),'iron',.035)
    for x in [-.36,.36]:
        h.cyl('Rear tail lamp',(x,1.055,1.29),.11,.07,'iron',(0,1,0),40)
        h.cyl('Red tail glass',(x,1.10,1.29),.083,.015,'tail',(0,1,0),40)
        for dx in [-.045,0,.045]:h.beam('Tail grille',(x+dx,1.117,1.22),(x+dx,1.117,1.36),.006,'iron')
    start=len(h.parts);h.plate('Rear plate',(0,1.09,1.04),(.40,.04,.18),'ivory','AXM',.10);turn_parts(h,start,(0,1.09,1.04),math.pi)
    h.cyl('Idea fuel bottle',(-.67,.83,1.55),.115,.54,'ivory',v=48)
    start=len(h.parts);h.text('Fuel label','AXM\nFUELED\nBY IDEAS',(-.79,.83,1.55),.055);turn_parts(h,start,(-.79,.83,1.55),-math.pi/2)
    # Tall real perforated heat shield: holes built as gaps in a panel grid.
    a=Vector((.37,.75,1.62));axis=Vector((.2,.17,1)).normalized();u=Vector((1,0,-.2)).normalized();v=axis.cross(u).normalized()
    h.beam('Exhaust stack core',a,a+axis*1.05,.073,'iron')
    n=32;rows=9;vs=[];fs=[]
    for j in range(rows+1):
        for i in range(n):t=i*TAU/n;vs.append(tuple(a+axis*(.18+j*.078)+.112*(u*math.cos(t)+v*math.sin(t))))
    for j in range(rows):
        for i in range(n):
            if j%2==1 and i%4 in [1,2]:continue
            fs.append((j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i))
    ob=h.mesh('Perforated exhaust shield',vs,fs,'steel');sol=ob.modifiers.new('Shield thickness','SOLIDIFY');sol.thickness=.006
    h.ring('Exhaust flared mouth',a+axis*.99,.11,.022,'iron',axis)
    # Lamps, mirrors and wrench mast.
    for x in [-.20,.20]:
        h.cyl('Roof light',(x,-.20,2.20),.10,.12,'iron',(0,-1,0),40)
        h.cyl('Roof warm lens',(x,-.27,2.20),.08,.02,'lamp',(0,-1,0),40)
        h.ring('Roof lamp guard',(x,-.29,2.20),.087,.008,'brass')
    for s in [-1,1]:
        h.beam('Mirror arm',(s*.48,-.17,1.96),(s*.74,-.15,2.12),.016,'steel')
        h.box('Square mirror',(s*.77,-.15,2.13),(.18,.07,.15),'iron',.02)
        h.box('Mirror silver',(s*.77,-.106,2.13),(.15,.01,.12),'steel',.012)
    h.beam('Wrench mast',(-.58,-.55,1.39),(-.58,-.55,2.22),.026,'steel')
    pts=[(-.13,0),(-.18,.20),(-.13,.30),(-.08,.27),(-.07,.14),(.07,.14),(.08,.27),(.13,.30),(.18,.20),(.13,0)]
    ob=h.mesh('Giant wrench head',[(-.58+x,-.55,2.14+z) for x,z in pts],[tuple(range(10))],'steel',smooth=False)
    sol=ob.modifiers.new('Forged wrench','SOLIDIFY');sol.thickness=.045
    h.cyl('Wrench yellow badge',(-.58,-.58,2.19),.095,.02,'yellow',(0,-1,0),6)
    h.logo('Wrench crest',(-.58,-.595,2.19),.12,'ink')
    # Duck on flexible spring and cloth pennant.
    spring(h,'Duck bobble spring',(0,-.18,2.20),(0,-.18,2.57),.035,.009,8,'brass')
    h.current='Duck';h.duck((0,-.18,2.61),2.1,'Duck')
    h.current='Chassis';h.beam('Flag mast',(.46,.55,1.86),(.46,.55,2.94),.017,'steel')
    h.current='Flag';h.plate('Small crew banner',(.72,.54,2.60),(.45,.015,.57),'ivory','SMALL\nCREW\nBIG\nCHAOS',.065)
    # Curved, torn cloth cape with authored folds, not a plane billboard.
    h.current='Cape';vs=[];fs=[];nx=24;ny=28
    for j in range(ny+1):
        t=j/ny
        for i in range(nx+1):
            q=i/nx;edge=.07*math.sin(i*2.31) if j==ny else 0
            vs.append(((q-.5)*(1.0+.20*t),.69+1.12*t+edge,2.04-.39*t+.05*math.sin(q*TAU*3+t*5)+.035*math.sin(t*9)))
    for j in range(ny):
        for i in range(nx):
            if j>ny-3 and (i%7==2 or i==0):continue
            a=j*(nx+1)+i;fs.append((a,a+1,a+nx+2,a+nx+1))
    ob=h.mesh('Flowing torn red cape',vs,fs,'red');sol=ob.modifiers.new('Cloth gauge','SOLIDIFY');sol.thickness=.005
    h.current='Chassis'
    # Dense but deliberate nuts, cable ties, case seams and small charms.
    for s in [-1,1]:
        for y in [-.5,-.25,0,.25,.5,.75]:
            h.bolt('Frame fastener',(s*.56,y,.85),.015,(s,0,0))
        h.duck((s*.77,.40,.91),1.0,'Chassis')
    print('AUTHORED_PARTS',len(h.parts),flush=True)
def animate(arm):
    rows=[];bpy.context.scene.render.fps=30
    for name,duration,loop in CLIPS:
        arm.animation_data_create();act=bpy.data.actions.new(name);arm.animation_data.action=act;act.use_fake_user=True
        for f in range(round(duration*30)+1):
            reset_pose(arm);t=f/(duration*30);p=TAU*t;b=arm.pose.bones
            b['Duck'].rotation_euler.x=.055*math.sin(p*2);b['Cape'].rotation_euler.x=.045*math.sin(p);b['Flag'].rotation_euler.x=.025*math.sin(p)
            if name=='Engine_Idle':translate(arm,'Chassis',(0,0,.006*math.sin(p*4)))
            if name=='Drive_Cycle':
                for key in WHEELS:b['Wheel.'+key].rotation_euler.y=TAU*t
                b['Cape'].rotation_euler.x=.10*math.sin(p);b['Duck'].rotation_euler.x=.10*math.sin(p*2)
            if name.startswith('Steer_'):
                sign=-1 if name=='Steer_Left' else 1
                b['Steering'].rotation_euler.y=sign*.48*t;b['SteeringWheel'].rotation_euler.y=sign*.72*t
            if name=='Suspension_Bounce':
                for key in WHEELS:translate(arm,'Suspension.'+key,(0,0,.065*(1-math.cos(p))))
            if name=='Duck_Honk':b['Duck'].rotation_euler.x=.30*math.sin(p)
            for bone in b:
                for ch in ['location','rotation_euler','scale']:bone.keyframe_insert(ch,frame=f,group=bone.name)
        for fc in act.fcurves:
            for k in fc.keyframe_points:k.interpolation='LINEAR'
        rows.append({'name':name,'seconds':duration,'loop':loop,'fps':30})
    arm.animation_data.action=None;reset_pose(arm);return rows
def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    bpy.ops.wm.read_factory_settings(use_empty=True);h=Hero(out);build(h);arm,mesh=rig(h);arm.name='AXM_Trike_Rig';mesh.name='AXM_Chaos_Trike';arm['binding']='Articulated vehicle: wheel spins, front steering, suspension, cockpit steering, duck and cloth.'
    clips=animate(arm);exports={}
    for name,ratio in [('AXM_Chaos_Trike',1),('AXM_Chaos_Trike_LOD1',.4)]:
        target=mesh
        if ratio<1:
            target=mesh.copy();target.data=mesh.data.copy();bpy.context.collection.objects.link(target);target.modifiers.clear()
            geo.select_only([target]);bpy.context.view_layer.objects.active=target
            mod=target.modifiers.new('LOD','DECIMATE');mod.ratio=ratio;bpy.ops.object.modifier_apply(modifier=mod.name);clean_triangles(target)
            mod=target.modifiers.new('Rig','ARMATURE');mod.object=arm
        geo.select_only([arm,target]);bpy.context.view_layer.objects.active=arm;path=out/(name+'.glb')
        bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,export_skins=True,export_animations=True,export_animation_mode='ACTIONS',export_force_sampling=True,export_yup=True,export_extras=True,export_tangents=True)
        target.data.calc_loop_triangles();exports[name]={'path':path.name,'triangles':len(target.data.loop_triangles),'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
        if ratio<1:bpy.data.objects.remove(target,do_unlink=True)
    arm.animation_data.action=bpy.data.actions['Engine_Idle'];bpy.context.scene.frame_set(0)
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'AXM_Chaos_Trike.blend'),compress=True)
    refs=[]
    for file in sorted(Path('upload').glob('*file_00000000*.png')):
        if any(k in file.name for k in ['210c81','05b081','717882']):refs.append({'name':file.name,'sha256':hashlib.sha256(file.read_bytes()).hexdigest()})
    m={'asset_id':'axm-chaos-trike','exports':exports,'bones':[{'name':k,'parent':v[2]} for k,v in h.bones.items()],'animations':clips,'coordinates':'metres, glTF Y-up,+Z forward; origin ground centre','wheelbase_m':1.93,'wheels':{k:{'centre_gltf_m':[c[0],c[2],-c[1]],'radius_m':r,'bone':'Wheel.'+k} for k,(c,r,w) in WHEELS.items()},'sockets':{'DriverSeat':[0,1.39,-.28],'CompanionDock':[-.53,2.15,-.67]},'collision_suggestion':{'type':'box','centre_gltf_m':[0,1.05,-.08],'half_extents_m':[.59,.35,.81],'status':'coarse starting shape; tune in target physics engine'},'references':refs,'limits':['Authored approximation; not exact reconstruction.','No engine-specific physics, crash simulation or automatic rider animation retargeting.','Drive_Cycle is display animation; controller drives wheels from distance.'],'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (out/'vehicle-manifest.json').write_text(json.dumps(m,indent=2)+'\n');print('TRIKE_COMPLETE',flush=True)
if __name__=='__main__':main()
