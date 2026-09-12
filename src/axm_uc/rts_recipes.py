"""Authored 83-design reference collection built from reusable salvage operations."""
import math
from .rts_mesh import SalvageMesh, add

def platform(f,w=5,d=4):
 for x in [-w*.25,w*.25]:
  for z in [-d*.25,d*.25]:f.roundbox('foundation',(x,.10,z),(w*.49,.20,d*.49),'concrete',.12)
 if not f.far:
  for j in range(12):
   a=j*2.4;x=math.cos(a)*w*.49;z=math.sin(a)*d*.49
   f.ellipsoid('rubble',(x,.13,z),(.26+.13*math.sin(j)**2,.24,.29),'concrete',7,4)
  for x,z in [(-w*.43,d*.43),(w*.4,-d*.4),(w*.36,d*.38)]:f.plant((x,.15,z),.55)

def canopy(f,c=(0,2.8,1),w=4,d=2,mat='canvas'):
 x,y,z=c;corners=[(x-w/2,y+.30,z-d/2),(x+w/2,y+.40,z-d/2),(x-w/2-.2,y-.20,z+d/2),(x+w/2+.15,y-.08,z+d/2)]
 f.cloth('sagged-canopy',corners,.16,mat)
 for p in corners:
  f.pipe('canopy-pole',[(p[0],.2,p[2]),p],.045,'iron',6)
  f.pipe('tie-rope',[p,(p[0]*1.1,.15,p[2]*1.13)],.013,'wood',4)
 f.lantern((x,y-.55,z),.8)

def tank(f,c,r=.65,h=2,mat='paint'):
 x,y,z=c;f.lathe('pressure-tank',c,[(0,0),(r*.7,0),(r,.18),(r,h-.18),(r*.7,h),(0,h)],mat)
 for yy in [.24,h*.5,h-.24]:f.ring('tank-band',(x,y+yy,z),r+.01,.035,'iron')
 f.pipe('tank-feed',[(x,y+h,z),(x,y+h+.22,z),(x+r*.6,y+h+.22,z)],.07,'tin',8)
 f.pipe('tank-tap',[(x,y+.3,z+r),(x,y+.3,z+r+.2)],.065,'iron',8)
 f.smile((x,y+h*.58,z+r+.01),r*.32)

def shed(f,w=4,d=3,h=2.7,style='flat',open_front=True):
 for x in [-w/2,w/2]:
  for z in [-d/2,d/2]:f.beam('structure-post',(x,.2,z),(x,h,z),.12,.12,'iron')
 for x in [-w/2,w/2]:f.panel('patched-side',(x,h*.48,0),d,h*.87,'paint',axis='x')
 f.panel('rear-wall',(0,h*.48,-d/2),w,h*.87,'rust')
 if not open_front:f.panel('front-wall',(0,h*.48,d/2),w,h*.87,'paint')
 if style=='arch':
  for j in range(5 if f.far else 8):
   z=-d/2+j*d/(4 if f.far else 7)
   arc=[(w*.5*math.cos(a),h-1+1.4*math.sin(a),z) for a in [math.pi*i/12 for i in range(13)]]
   f.pipe('roof-rib',arc,.06,'iron',6)
  for j in range(8):
   a=j*math.pi/8;b=(j+1)*math.pi/8
   f.double('tin' if j%3 else 'paint',[(w*.5*math.cos(a),h-1+1.4*math.sin(a),-d/2),(w*.5*math.cos(b),h-1+1.4*math.sin(b),-d/2),(w*.5*math.cos(b),h-1+1.4*math.sin(b),d/2),(w*.5*math.cos(a),h-1+1.4*math.sin(a),d/2)],'arched-roof-skin')
 else:
  for j in range(5):
   x=-w*.5+(j+.5)*w/5;f.roundbox('roof-sheet',(x,h+.03*math.sin(j),0),(w/5+.04,.09,d+.28),'tin' if j%2 else 'paint',.02)
 for x in [-w/2,w/2]:f.beam('roof-rail',(x,h,-d/2),(x,h,d/2),.14,.14,'iron')
 f.lantern((-.75,h-.5,d/2+.08),.8)
 f.roundbox('entry-threshold',(0,.23,d/2+.12),(1.3,.13,.5),'wood')

def bench(f,c=(0,.95,0),width=1.6):
 x,y,z=c;f.roundbox('workbench',c,(width,.15,.75),'wood',.04)
 for dx in [-width*.42,width*.42]:f.beam('bench-leg',(x+dx,.20,z),(x+dx,y,z),.10,.57,'iron')
 f.roundbox('vise',(x+.35,y+.20,z),(.30,.28,.27),'iron',.03)
 f.pipe('vise-handle',[(x+.15,y+.2,z+.20),(x+.55,y+.2,z+.20)],.023,'tin',6)

def crane(f,c=(0,0,0),h=4,length=3):
 x,y,z=c
 for dx in [-.32,.32]:f.beam('crane-mast',(x+dx,y+.2,z),(x+dx,y+h,z),.17,.17,'signal')
 start=(x,y+h,z);end=(x+length,y+h+length*.4,z)
 for dz in [-.18,.18]:
  f.beam('crane-boom',add(start,(0,0,dz)),add(end,(0,0,dz)),.17,.17,'signal')
 for j in range(6):
  t=j/6;u=(j+1)/6
  f.beam('boom-crossbrace',add(start,(length*t,length*.4*t,-.18)),add(start,(length*u,length*.4*u,.18)),.06,.06,'iron')
 f.pipe('load-cable',[end,(end[0],y+1.5,z)],.027,'iron',6)
 f.pipe('crane-hook',[(end[0],y+1.5,z),(end[0]-.1,y+1.3,z),(end[0]+.1,y+1.2,z),(end[0]+.18,y+1.36,z)],.07,'iron',7)
 f.pipe('hydraulic',[(x,y+h*.5,z),(x+length*.5,y+h+length*.2,z)],.095,'tin',8)

def tower(f,h=4,spot=False):
 for x,z in [(-.65,-.6),(.65,-.6),(-.65,.6),(.65,.6)]:f.beam('tower-leg',(x*1.25,.2,z*1.25),(x,h,z),.15,.15,'signal')
 for y in [1,2,3]:
  if y>=h:continue
  for z in [-.6,.6]:
   f.beam('crossbrace',(-.65,y-.6,z),(.65,y+.35,z),.085,.085,'iron')
   f.beam('crossbrace',(.65,y-.6,z),(-.65,y+.35,z),.085,.085,'iron')
 f.roundbox('tower-platform',(0,h,0),(2,.18,1.8),'iron')
 if not spot:
  for z in [-.8,.8]:
   for x in [-.9,.9]:f.beam('railpost',(x,h,z),(x,h+.8,z),.06,.06,'iron')
   f.beam('guardrail',(-.9,h+.8,z),(.9,h+.8,z),.06,.06,'iron')
  canopy(f,(0,h+1.1,0),1.8,1.5)
 else:
  for x in [-.65,0,.65]:
   f.lathe('spotlight',(x,h+.45,.1),[(0,0),(.25,0),(.32,.27),(.27,.29),(0,.29)],'iron',axis='z')
   f.pipe('light-lens',[(x,h+.45,.401),(x,h+.45,.405)],.245,'glow',14)
 f.ladder(.35,.9,h)

def solar(f,c=(0,1,0),w=1.8,h=1.1):
 x,y,z=c
 f.roundbox('solar-frame',c,(w,h,.10),'iron',.025)
 for i in range(5):
  for j in range(3):f.box('photovoltaic-cell',(x-w*.4+i*w*.2,y-h*.33+j*h*.33,z+.06),(w*.18,h*.28,.025),'glass')
 f.beam('solar-support',(x,.2,z-.4),(x,y+h*.4,z),.1,.1,'iron')

def meteor(f,c=(0,1,0),s=1):
 x,y,z=c
 f.ellipsoid('faceted-meteor',c,(1.45*s,2*s,1.35*s),'iron',7,5)
 for j in range(7):
  a=j*math.tau/7
  path=[]
  for k in range(5):
   yy=-.65+k*.32;rr=math.sqrt(max(.1,1-yy*yy));aa=a+.14*math.sin(k*4+j)
   path.append((x+.735*s*rr*math.cos(aa),y+yy*s,z+.685*s*rr*math.sin(aa)))
  f.pipe('luminous-fracture',path,.025*s,'cyan',5)
 for dx in [-.75,.75]:
  f.beam('meteor-clamp',(x+dx*s,y-.7*s,z),(x+dx*.72*s,y+.2*s,z),.20*s,.25*s,'tin')
  f.pipe('coolant-hose',[(x+dx*s,y-.6*s,z),(x+dx*1.35*s,y-.1*s,z+.1*s),(x+dx*s,y+.35*s,z)],.08*s,'rubber',8)

def track(f,c=(0,.48,0),length=2):
 x,y,z=c
 f.roundbox('track-belt',c,(.40,.7,length),'rubber',.19)
 for j in range(5):
  zz=z-length*.38+j*length*.19;f.pipe('track-roller',[(x-.23,y,zz),(x+.23,y,zz)],.27,'iron',10)
  f.pipe('roller-hub',[(x-.25,y,zz),(x+.25,y,zz)],.09,'tin',8)
 for zz in range(9 if f.far else 15):
  p=-length*.47+length*.94*zz/(8 if f.far else 14)
  for yy in [-.37,.37]:f.box('track-shoe',(x,y+yy,z+p),(.49,.09,length*.065),'iron')

def gun(f,c=(0,0,0),kind='rifle',s=1):
 x,y,z=c
 def p(a,b,d):return(x+a*s,y+b*s,z+d*s)
 f.roundbox('receiver',p(0,0,0),(.19*s,.25*s,.64*s),'iron',.035*s)
 if kind=='smg':
  f.pipe('folding-stock',[p(-.10,0,-.2),p(-.10,0,-.57),p(-.10,-.20,-.57)],.025*s,'iron',7)
  f.roundbox('magazine-well',p(0,-.18,.06),(.17*s,.30*s,.15*s),'paint',.025*s)
 else:f.roundbox('stock',p(0,-.035,-.52),(.17*s,.23*s,.47*s),'wood',.04*s)
 f.beam('pistol-grip',p(0,-.05,-.14),p(0,-.32,-.25),.13*s,.12*s,'wood')
 f.roundbox('magazine',p(0,-.24,.18),(.115*s,.38*s,.20*s),'iron',.018*s)
 r=.06 if kind!='launcher' else .18
 if kind=='rotary':
  for i in range(6):
   a=i*math.tau/6;xx=.13*math.cos(a);yy=.13*math.sin(a)
   f.pipe('rotary-barrel',[p(xx,yy,.25),p(xx,yy,1.15)],.042*s,'iron',8)
  for zz in [.35,.85]:f.ring('barrel-collar',p(0,0,zz),.15*s,.045*s,'tin',axis='z')
 else:
  for xx in ([-.055,.055] if kind=='shotgun' else [0]):
   f.pipe('barrel',[p(xx,.04,.28),p(xx,.04,.64 if kind=='smg' else .99)],r*s,'iron',10)
   f.pipe('dark-bore',[p(xx,.04,.641 if kind=='smg' else .991),p(xx,.04,.651 if kind=='smg' else 1.001)],r*.70*s,'rubber',10)
  f.ring('muzzle-band',p(0,.04,.60 if kind=='smg' else .91),r*1.08*s,.018*s,'tin',axis='z')
 if kind=='launcher':f.ellipsoid('rocket-nose',p(0,.04,1.02),(.32*s,.32*s,.46*s),'red')
 if kind in ['rifle','smg']:
  f.pipe('optic',[p(0,.22,-.05),p(0,.22,.3)],.056*s,'iron',8)
  f.pipe('optic-lens',[p(0,.22,.301),p(0,.22,.31)],.047*s,'glass',8)
 for zz in [-.15,.1,.25]:
  for xx in [-.105,.105]:f.pipe('receiver-rivet',[p(xx,0,zz),p(xx*1.08,0,zz)],.020*s,'tin',6)
 for zz in [.38,.5,.62]:
  if kind not in ['launcher','rotary']:f.ring('foregrip-wrap',p(0,.04,zz),.079*s,.015*s,'wood',axis='z')
 f.pipe('trigger-guard',[p(0,-.14,-.05),p(0,-.27,-.05),p(0,-.27,.10),p(0,-.14,.10)],.020*s,'iron',6)
 f.sockets['muzzle']={'position':list(p(0,.04,.67 if kind=='smg' else 1.03)),'forward':[0,0,1],'component':f.active,'space':'bind-world'}


def crew(f,id):
 # Deliberately exaggerated but anatomical rigid figure: articulated coat/boots,
 # helmet shell, wrapped collar, pouches, lenses and role-specific carried gear.
 mat='paint' if id=='mechanic-repair-crew' else ('ivory' if id=='field-medic' else 'cloth')
 f.ellipsoid('coat-body',(0,1.14,0),(.67,.77,.41),mat)
 f.roundbox('belt',(0,.91,0),(.68,.13,.44),'wood',.03)
 f.roundbox('belt-buckle',(0,.92,.24),(.15,.13,.035),'tin',.02)
 for side in [-1,1]:
  with f.part('leg-'+str(side).replace('-','m'),(side*.18,.92,0),{'clip':'walk','axis':[1,0,0],'angles':[0,side*.40,0,-side*.40,0],'duration':.9}):
   f.ellipsoid('trouser-leg',(side*.18,.59,0),(.28,.63,.28),mat)
   f.roundbox('knee-pad',(side*.18,.48,.16),(.23,.21,.075),'iron',.045)
   f.roundbox('boot',(side*.18,.17,.09),(.30,.30,.48),'rubber',.065)
   for yy in [.20,.28]:f.box('boot-strap',(side*.18,yy,.305),(.22,.035,.025),'wood')
  with f.part('arm-'+str(side).replace('-','m'),(side*.37,1.38,0),{'clip':'walk','axis':[1,0,0],'angles':[0,-side*.2,0,side*.2,0],'duration':.9}):
   f.ellipsoid('sleeve',(side*.39,1.22,.02),(.26,.41,.28),mat)
   f.beam('forearm',(side*.44,1.10,.08),(side*.35,.98,.30),.20,.20,mat)
   f.ellipsoid('glove',(side*.35,.99,.32),(.22,.22,.23),'rubber')
   f.roundbox('wrist-guard',(side*.40,1.05,.22),(.22,.11,.18),'wood',.025)
  f.roundbox('belt-pouch',(side*.28,.94,.24),(.18,.22,.13),'wood',.025)
 f.roundbox('backpack',(0,1.27,-.32),(.56,.63,.25),'wood',.07)
 for x in [-.19,.19]:f.beam('backpack-strap',(x,.99,.235),(x,1.53,.16),.065,.045,'wood')
 f.pipe('bedroll',[(-.31,1.65,-.34),(.31,1.65,-.34)],.13,'darkcloth',10)
 for x in [-.21,.21]:f.ring('bedroll-strap',(x,1.65,-.34),.13,.023,'wood',axis='x')
 with f.part('head',(0,1.55,0)):
  f.ellipsoid('head',(0,1.70,0),(.53,.57,.48),'skin')
  f.ellipsoid('scarf',(0,1.52,.11),(.58,.23,.48),'red' if id not in ['crew-worker','field-medic'] else 'canvas')
  f.ellipsoid('helmet',(0,1.93,-.02),(.64,.37,.57),'ivory' if id=='field-medic' else ('red' if id=='shotgun-raider' else 'cloth'))
  f.roundbox('helmet-brim',(0,1.88,.085),(.68,.055,.64),'iron',.09)
  for x in [-.145,.145]:
   f.pipe('goggle-housing',[(x,1.76,.23),(x,1.76,.29)],.125,'rubber',12)
   f.pipe('goggle-lens',[(x,1.76,.291),(x,1.76,.305)],.095,'glass',12)
   f.pipe('lens-glint',[(x-.024,1.796,.307),(x-.024,1.796,.308)],.025,'ivory',6)
  f.beam('goggle-bridge',(-.035,1.77,.31),(.035,1.77,.31),.04,.04,'tin')
  f.smile((0,1.96,.278),.105)
 if id in ['scavenger','mercenary-free-agent']:
  f.cloth('ragged-hood-cape',[(-.4,1.88,-.12),(.4,1.88,-.12),(-.55,.72,-.40),(.55,.77,-.40)],.12,'darkcloth')
 if id=='citizen-harvester':
  f.ring('straw-hat-brim',(0,1.89,0),.37,.065,'wood')
  f.crate((0,1.00,.49),.65)
  for x in [-.20,0,.2]:f.plant((x,1.23,.5),.45)
 elif id=='crew-worker':f.crate((0,1.02,.51),.65);f.smile((0,1.03,.73),.13)
 elif id in ['rifle-guard','shotgun-raider','mercenary-ex-mil','mercenary-free-agent']:
  gun(f,(.08,1.02,.46),'shotgun' if id=='shotgun-raider' else 'rifle',.7)
 elif id=='mechanic-repair-crew':
  f.crate((.38,.67,.37),.40,'red');f.beam('wrench',(-.34,1.20,-.37),(-.45,2.18,-.37),.10,.10,'tin');f.ring('wrench-jaw',(-.45,2.18,-.37),.16,.055,'tin',axis='z')
 elif id=='field-medic':
  f.roundbox('medical-bag',(.4,.75,.40),(.34,.32,.22),'ivory',.035)
  for w,h in [(.22,.065),(.065,.22)]:f.box('medical-cross',(.4,.75,.52),(w,h,.015),'red')
 elif id=='scout':f.lantern((.38,.69,.40),.63);f.pipe('radio-aerial',[(-.24,1.5,-.4),(-.24,2.4,-.4)],.012,'iron',5)
 elif id=='heavy-vehicle-operator':f.roundbox('welding-visor',(0,1.74,.31),(.4,.36,.11),'iron',.06)
 elif id=='licensed-driver':f.ring('key-ring',(.37,.85,.4),.07,.012,'tin',axis='z')
 elif id=='scavenger':f.pipe('salvage-probe',[(.36,.99,.38),(.58,.22,.85)],.025,'iron',6);f.ring('detector-head',(.58,.16,.85),.18,.027,'iron')
 f.sockets['hand-right']={'position':[.35,.99,.32],'forward':[0,0,1]}
 f.sockets['backpack']={'position':[0,1.3,-.47],'forward':[0,0,-1]}

def vehicle(f,id):
 length=4.8 if id in ['flatbed-convoy-truck','armored-bus','cargo-trailer','mercenary-carrier','crane-truck','drill-rig-vehicle'] else 3.1
 width=1.85 if length>4 else 1.5
 if id=='push-cart':
  f.roundbox('cart-bed',(0,.75,0),(1.25,.18,1.45),'paint')
  for x in [-.64,.64]:f.panel('cart-side',(x,1.04,0),1.45,.45,'paint',axis='x');f.wheel('wheel-'+str(x).replace('-','m').replace('.','d'),(x,.38,0),.37,.23)
  for x in [-.5,.5]:f.pipe('cart-handle',[(x,.8,-.6),(x,1.05,-1.3)],.04,'iron',7)
  f.crate((0,1.10,0),.82);f.barrel((.34,.88,-.36),.20,.65,'red');f.flag((-.52,.88,-.5),.55);return
 if id=='scout-trike':
  f.beam('motorcycle-spine',(0,.55,-1),(0,.67,1),.14,.15,'iron')
  for j,(x,z) in enumerate([(0,.95),(-.58,-.72),(.58,-.72)]):f.wheel('wheel-'+str(j),(x,.43,z),.43,.25)
  for x in [-.15,.15]:f.pipe('front-fork',[(x,.43,.95),(x,1.15,.64)],.035,'tin',8)
  f.pipe('handlebar',[(-.46,1.20,.63),(-.25,1.17,.75),(.25,1.17,.75),(.46,1.20,.63)],.033,'iron',8)
  f.ellipsoid('fuel-tank',(0,.92,.20),(.48,.38,.57),'ivory');f.smile((0,.95,.49),.14)
  f.roundbox('motorcycle-seat',(0,.88,-.35),(.45,.16,.65),'rubber',.065)
  f.roundbox('engine',(0,.58,.03),(.35,.35,.40),'iron')
  for y in [.46,.52,.58,.64]:f.box('engine-fin',(0,y,.03),(.43,.025,.42),'tin')
  f.roundbox('rear-cargo',(0,.79,-.9),(1.0,.17,.66),'paint');f.crate((0,1.05,-.87),.60);f.dish((.37,1.45,-1),.25)
  f.pipe('headlamp',[(0,1.13,.73),(0,1.13,.89)],.14,'iron',10);f.pipe('headlamp-glass',[(0,1.13,.90),(0,1.13,.91)],.11,'glow',10)
  return
 f.roundbox('chassis',(0,.62,0),(width,.22,length),'iron',.10)
 f.pipe('exhaust',[(width*.43,.60,-length*.35),(width*.5,1.1,-length*.36),(width*.5,1.95,-length*.35)],.065,'rust',9)
 zfront=length*.31;zback=-length*.32;r=.53 if length>4 else .46
 if id=='tow-crawler':
  for s in [-1,1]:track(f,(s*.83,.46,0),2.85)
 else:
  wheels=[(-1,zfront),(1,zfront),(-1,zback),(1,zback)]
  if id=='scout-trike':wheels=[(0,zfront),(-1,zback),(1,zback)]
  if id=='cargo-trailer':wheels=[(-1,zback),(1,zback),(-1,zback+.7),(1,zback+.7)]
  if length>4 and id not in ['armored-bus','mercenary-carrier']:wheels += [(-1,zback+.72),(1,zback+.72)]
  for j,(s,z) in enumerate(wheels):
   x=s*(width*.53);f.wheel('wheel-'+str(j),(x,r,z),r,.34)
   if s:f.roundbox('mudguard',(x,r*1.94,z),(.48,.11,.85),'paint',.045)
  for zz in [zfront,zback]:f.pipe('axle',[(-width*.56,r,zz),(width*.56,r,zz)],.075,'iron',8)
 openframe=id in ['scrap-buggy','scout-trike']
 trailer=id=='cargo-trailer'
 if trailer:
  canopy(f,(0,2.0,0),width,length,'canvas')
  f.beam('trailer-drawbar',(0,.6,length*.5),(0,.6,length*.5+.8),.16,.13,'iron')
 elif openframe:
  for x in [-width*.43,width*.43]:
   f.pipe('roll-cage',[(x,.8,-.65),(x,1.78,-.60),(x,1.91,.48),(x,.88,1.02)],.06,'iron',8)
  for z in [-.6,.48]:f.pipe('roof-crossbar',[(-width*.43,1.85,z),(width*.43,1.85,z)],.06,'iron',8)
  f.roundbox('hood',(0,.94,zfront),(.95,.27,.72),'paint',.10)
  for x in [-.27,.27]:f.roundbox('seat',(x,1.1,-.1),(.40,.52,.44),'rubber',.10)
  f.ring('steering-wheel',(-.28,1.40,.40),.17,.027,'iron',axis='z')
 else:
  cabz=length*.26
  cablen=length*.86 if id in ['armored-bus','field-ambulance-van','mercenary-carrier'] else 1.3
  cabz=0 if cablen>2 else cabz
  f.roundbox('cab',(0,1.37,cabz),(width*.91,1.36,cablen),'ivory' if id=='field-ambulance-van' else 'paint',.15)
  front=cabz+cablen*.5
  # Solid colored glass panels are stylized windows, not a transparency claim.
  for x in [-width*.22,width*.22]:f.roundbox('windshield',(x,1.65,front+.007),(width*.39,.51,.025),'glass',.025)
  f.roundbox('front-grille',(0,.98,front+.045),(width*.58,.35,.06),'rubber',.025)
  for j in range(7):f.box('grille-slot',(-width*.24+j*width*.08,.98,front+.08),(.035,.29,.025),'tin')
  for s in [-1,1]:
   for j in range(max(1,int(cablen/.7))):
    z=cabz-cablen*.37+j*.7;f.roundbox('side-window',(s*width*.458,1.69,z),(.025,.43,.54),'glass',.008)
   f.box('door-handle',(s*width*.48,1.25,cabz+.05),(.04,.065,.20),'tin')
   f.pipe('mirror-arm',[(s*width*.44,1.59,front-.1),(s*width*.66,1.59,front-.1)],.024,'iron',6)
   f.roundbox('mirror',(s*width*.66,1.63,front-.1),(.12,.22,.06),'tin',.02)
  if cablen>2:
   for j in range(5):
    zz=-cablen*.4+j*cablen*.2;f.pipe('roof-rack',[(-width*.47,2.13,zz),(width*.47,2.13,zz)],.035,'iron',6)
   f.crate((0,2.25,-cablen*.24),.8)
  else:
   f.roundbox('load-bed',(0,.95,-length*.22),(width,.19,length*.46),'wood',.04)
   for s in [-1,1]:f.panel('load-rail',(s*width*.5,1.2,-length*.22),length*.48,.46,'paint',axis='x')
 f.roundbox('bumper',(0,.72,length*.5+.08),(width+.16,.20,.17),'iron',.04)
 for x in [-width*.35,width*.35]:
  f.pipe('headlamp',[(x,1.02,length*.50),(x,1.02,length*.5+.12)],.15,'iron',10)
  f.pipe('headlamp-lens',[(x,1.02,length*.5+.121),(x,1.02,length*.5+.13)],.12,'glow',10)
 f.smile((0,1.12,length*.50+.14),.19)
 if id in ['crane-truck','tow-crawler']:crane(f,(0,.83,-.65),2.5,2)
 elif id=='drill-rig-vehicle':
  for x in [-.30,.30]:f.beam('drill-mast',(x,.9,-1.2),(x,3.7,-1.2),.14,.14,'signal')
  for y in [1.2,1.8,2.4,3.0,3.6]:f.beam('mast-brace',(-.3,y,-1.2),(.3,y,-1.2),.07,.07,'iron')
  f.lathe('auger',(0,.9,-1.2),[(.0,0),(.20,.3),(.22,1.7),(.14,2.7)],'iron')
  for y in [1.3,1.6,1.9,2.2]:f.ring('drill-flight',(0,y,-1.2),.25,.045,'tin')
 elif id=='field-ambulance-van':
  for w,h in [(.7,.17),(.17,.7)]:f.box('medical-cross',(0,1.15,length*.46+.02),(w,h,.025),'red')
  f.roundbox('emergency-beacon',(0,2.14,.35),(.7,.15,.27),'red',.04)
 elif id=='mercenary-carrier':
  with f.part('turret',(0,2.20,-.3),{'clip':'aim','axis':[0,1,0],'angles':[-.5,.5,-.5],'duration':4}):gun(f,(0,2.40,-.3),'rotary',.85)
 elif not openframe and not trailer:
  f.crate((0,1.37,-length*.32),.8);f.barrel((width*.29,1.0,-length*.29),.22,.7,'red')
 if id not in ['field-ambulance-van','tow-crawler']:f.flag((-width*.43,1.04,-length*.39),.60)
 f.sockets['hitch']={'position':[0,.60,-length*.5-.12],'forward':[0,0,-1]}

def greenhouse(f):
 w,d=4,3;h=2.3
 for x in [-2,2]:
  for z in [-1.5,-.5,.5,1.5]:f.beam('bus-window-frame',(x,.3,z),(x,h,z),.09,.09,'iron')
  for y in [.35,1.25,h]:f.beam('window-horizontal',(x,y,-1.5),(x,y,1.5),.085,.085,'iron')
  for z in [-1,0,1]:
   f.roundbox('window-glass',(x,1.75,z),(.025,.87,.89),'glass',.01)
   f.roundbox('window-glass',(x,.78,z),(.025,.77,.89),'glass',.01)
 for z in [-1.5,-.5,.5,1.5]:
  f.beam('gable',(-2,h,z),(0,3.3,z),.095,.095,'iron');f.beam('gable',(0,3.3,z),(2,h,z),.095,.095,'iron')
 for s in [-1,1]:
  for z in [-1,0,1]:
   f.double('glass',[(s*.06,3.27,z-.43),(s*1.94,2.33,z-.43),(s*1.94,2.33,z+.43),(s*.06,3.27,z+.43)],'greenhouse-roof-glass')
 f.beam('ridge',(0,3.3,-1.5),(0,3.3,1.5),.12,.12,'iron')
 for x in [-1.55,1.55]:
  f.roundbox('raised-planter',(x,.43,0),(.55,.43,2.6),'wood')
  for z in [-1,-.5,0,.5,1]:f.plant((x,.64,z),1)
 for x in [-1.45,1.45]:
  f.roundbox('front-window',(x,1.3,1.51),(.92,1.7,.035),'glass',.015)
 for x in [-.72,.72]:f.beam('door-frame',(x,.2,1.54),(x,2.4,1.54),.12,.12,'tin')
 f.barrel((2.42,.2,-.8),.38,1.15,'ivory');f.pipe('irrigation',[(2.42,1.3,-.8),(2.42,2.3,-.8),(1.8,2.3,-.8)],.055,'iron',8)
 f.lantern((0,2.4,1.48),.8);f.smile((1.45,.48,1.56),.20)

def industry(f,id):
 platform(f,5,4)
 if id=='bus-window-greenhouse':greenhouse(f)
 elif id=='open-crop-terrace':
  for row in range(3):
   z=-1.1+row*1.05;y=.45+(2-row)*.50
   f.roundbox('terrace-bed',(0,y,z),(3.8,.45,.88),'wood',.07)
   f.box('earth',(0,y+.24,z),(3.6,.08,.7),'soil')
   for x in [-1.5,-.9,-.3,.3,.9,1.5]:f.plant((x,y+.27,z),.75)
  f.flag((1.9,.25,-1.45),1)
 elif id=='fungal-shed':
  shed(f,3.8,2.8,2.8);canopy(f,(0,3.0,.7),3.9,2.9)
  for y in [.55,1.25,1.95]:
   f.box('mushroom-shelf',(0,y,-.65),(3.3,.10,.65),'wood')
   for j in range(5):
    x=-1.35+j*.67;s=.17+.03*(j%3)
    f.pipe('mushroom-stalk',[(x,y,-.62),(x,y+.27,-.62)],s*.3,'ivory',7)
    f.ellipsoid('mushroom-cap',(x,y+.28,-.62),(s*2.5,s*.9,s*2.5),'signal',10,5)
  bench(f,(.7,.75,.65));f.barrel((-2,.2,1),.3,.8)
 elif id=='livestock-pen':
  for z in [-1.5,1.5]:
   for x in [-2,-1,0,1,2]:f.beam('fence-post',(x,.2,z),(x,1.25,z),.13,.13,'wood')
   for y in [.52,.96]:f.beam('fence-rail',(-2,y,z),(2,y,z),.11,.11,'wood')
  for x in [-2,2]:
   for y in [.52,.96]:f.beam('fence-rail',(x,y,-1.5),(x,y,1.5),.11,.11,'wood')
  for x,scale,mat in [(-.7,1,'ivory'),(.85,.65,'skin')]:
   f.ellipsoid('livestock-body',(x,1.06,0),(1.25*scale,.85*scale,.65*scale),mat)
   for dx in [-.4,.4]:
    for z in [-.2,.2]:f.beam('livestock-leg',(x+dx*scale,.27,z),(x+dx*scale,.99,z),.12*scale,.12*scale,mat)
   f.ellipsoid('animal-head',(x+.55*scale,1.25,.1),(.43*scale,.56*scale,.40*scale),mat)
   for z in [-.17,.17]:f.ellipsoid('ear',(x+.50*scale,1.50,z),(.22*scale,.10*scale,.14*scale),'rubber')
  canopy(f,(0,2.7,-.5),4,2,'red')
 elif id=='water-catcher':
  for x in [-1.8,.2]:f.beam('water-tower-post',(x,.2,-.7),(x,3.6,-.7),.15,.15,'wood')
  f.cloth('catchment-tarp',[(-1.9,3.6,-1.1),(.3,3.6,-1.1),(-1.9,3.35,.9),(.3,3.35,.9)],.80,'canvas')
  f.pipe('collector-spout',[(-.8,2.7,.7),(-.8,2.5,1),(1.3,2.5,1),(1.3,2.25,.7)],.08,'tin',8)
  tank(f,(1.2,.2,.5),.83,2.2,'tin');f.ladder(-1.55,.1,3.1)
 elif id=='scrap-sorting-yard':
  for x,mat in [(-1.5,'paint'),(0,'ivory'),(1.5,'red')]:
   f.roundbox('sorting-bin',(x,.6,.9),(1.3,.8,1.2),mat)
   for j in range(6):
    f.roundbox('scrap',(x+.3*math.sin(j),1.0+.13*(j%3),.9+.3*math.cos(j)),(.5,.18,.4),'rust' if j%2 else 'iron',.025)
  crane(f,(-1.7,.2,-1.2),2.7,2.8)
 elif id in ['shallow-mine-entrance','deep-mine-head']:
  if id=='shallow-mine-entrance':
   for j in range(10):
    a=j*math.pi/9;f.ellipsoid('rock-arch',(2*math.cos(a),.7+2.3*math.sin(a),-.6),(.95,1.0,1.5),'concrete',7,4)
   for x in [-1.25,1.25]:f.beam('mine-timber',(x,.2,-.2),(x,2.05,-.2),.22,.24,'wood')
   f.beam('mine-lintel',(-1.4,2,-.2),(1.4,2,-.2),.3,.25,'wood')
  else:
   tower(f,4.5);f.ring('mine-sheave',(0,4.8,0),.5,.10,'iron',axis='z')
   f.pipe('hoist-cable',[(0,4.8,0),(0,.25,0)],.033,'iron',6)
  for x in [-.4,.4]:f.beam('mine-rail',(x,.23,-1.2),(x,.23,1.8),.065,.085,'iron')
  f.roundbox('mine-cart',(0,.68,.9),(1,.6,.8),'iron');f.lantern((-1.2,1.65,.35))
 elif id=='asteroid-extraction-rig':
  f.ellipsoid('asteroid',(-.6,1.6,0),(2.7,2.5,2.4),'concrete',9,6)
  for j in range(8):
   a=j*2.4;f.ring('asteroid-crater',(-.6+math.sin(a)*.8,1.6+math.cos(a)*.8,1),.14+.05*(j%3),.035,'iron',axis='z')
  crane(f,(1.45,.2,-.5),3.0,-2.4);f.crate((1.6,.7,.9),1,'ivory');meteor(f,(-.6,1.7,0),.65)
 elif id=='battery-fuel-station':
  tank(f,(-1.2,.2,0),.75,2.0,'ivory');canopy(f,(1,2.7,.3),2.2,2.3)
  for x,mat in [(.4,'red'),(1.4,'signal')]:
   f.roundbox('fuel-pump',(x,1.0,.7),(.62,1.6,.55),mat,.10)
   f.roundbox('pump-meter',(x,1.4,1),(.43,.3,.03),'rubber',.02)
   f.pipe('fuel-hose',[(x+.36,1.5,.7),(x+.54,.4,.7),(x+.64,.55,1),(x+.40,1.2,1)],.044,'rubber',8)
 elif id=='clustered-storage-bins':
  for x,z,r,h,mat in [(-1.3,-.65,.6,2.4,'signal'),(0,-.7,.62,2.0,'red'),(1.35,-.65,.62,2.8,'paint'),(-.8,.8,.65,1.6,'paint'),(.85,.8,.73,1.55,'ivory')]:tank(f,(x,.2,z),r,h,mat)

def building(f,id):
 w=6 if id=='settlement-hub' else 5
 platform(f,w,4.8)
 if id in ['civic-shelter','storage-hall']:
  shed(f,4.4,3.3,3.1,'arch');canopy(f,(.8,2.8,1.5),2.5,1.8)
  for x in [-1.8,1.8]:tank(f,(x,.2,1.65),.37,1.1,'ivory')
  if id=='storage-hall':
   for x in [-1.35,0,1.35]:
    for y in [.6,1.3]:f.crate((x,y,-.8),1)
 elif id=='settlement-hub':
  shed(f,5,3.5,2.6);canopy(f,(0,2.75,1.7),5.5,1.8)
  with f.part('upper-storey',(0,0,0)):
   # Explicit upper room preserves a single foundation and a usable entrance.
   f.roundbox('upper-container',(0,3.2,-.6),(3.1,1.35,2.1),'paint',.12)
   for x in [-.9,0,.9]:f.roundbox('upper-window',(x,3.4,.47),(.59,.55,.045),'glow',.025)
   f.roundbox('upper-roof',(0,3.94,-.6),(3.35,.12,2.35),'tin')
  f.ladder(2,1.5,3.8);f.flag((-1,3.95,-.6),.85);f.crate((-2,.65,1.8),.85,'red')
 elif id=='improvised-workshop':
  shed(f,4,3.1,2.6);canopy(f,(.1,2.9,1.65),4.6,2.1)
  bench(f,(-.6,1,1.4),2.2);f.crate((1.6,.55,1.8),.9,'red');tank(f,(-2.15,.2,1),.32,.85)
  f.pipe('chimney',[(1.55,.2,-.8),(1.55,3.9,-.8)],.17,'tin',12)
  for y in [2.8,3.2,3.7]:f.ring('chimney-band',(1.55,y,-.8),.19,.028,'iron')
  f.dish((-1.25,2.75,-.7),.55);crane(f,(.8,.2,-.6),2.8,-1.1)
 elif id=='command-signal-hall':
  shed(f,4.5,3.2,2.7);canopy(f,(-.7,2.95,.4),2.8,2)
  f.dish((1.3,3,-.35),.90);f.ladder(.65,1.8,2.9)
  f.pipe('radio-mast',[(-1.5,2.7,-1),(-1.5,5,-1)],.075,'iron',8)
  for y in [3.4,4.0,4.6]:f.beam('antenna',(-2,y,-1),(-1,y,-1),.035,.035,'tin')
  f.lantern((-1.5,5,-1),.6)
 elif id=='training-yard':
  for x in [-2,-1,0,1,2]:f.panel('yard-wall',(x,1.4,-1.8),.9,2.4,'wood')
  for x in [-1.4,0,1.4]:
   f.beam('target-post',(x,.2,0),(x,1.8,0),.09,.09,'wood');f.smile((x,1.55,.06),.37)
  for x in [-1.8,-1.1]:
   for y in [.35,.6,.85]:f.ring('tire-stack',(x,y,1.3),.38,.11,'rubber')
  f.flag((1.9,.2,-1.8),1.2)
 elif id=='repair-garage':
  canopy(f,(0,3.5,0),4.4,3.4);crane(f,(-1.8,.2,-.8),3.4,2)
  f.roundbox('repair-chassis',(0,.6,.1),(1.7,.2,2.5),'iron')
  for i,(x,z) in enumerate([(-.9,-.8),(.9,-.8),(-.9,1),(.9,1)]):f.wheel('service-wheel-'+str(i),(x,.48,z),.47,.3,False)
  f.roundbox('stripped-cab',(0,1.35,.45),(1.3,1.1,.9),'ivory');f.roundbox('garage-windscreen',(0,1.58,.91),(1.1,.5,.04),'glass')
  bench(f,(1.55,1,-.8),1.3)
 elif id=='refinery-shack':
  for x,h in [(-1.1,2.8),(.9,2.3)]:tank(f,(x,.2,0),.67,h,'tin')
  for y in [1,1.7,2.6]:f.pipe('refinery-pipe',[(-1.1,y,.7),(-1.1,y,.96),(.9,y,.96),(.9,y,.7)],.08,'iron',8)
  f.pipe('flare-stack',[(1.7,.2,-1),(1.7,4.1,-1)],.14,'rust',9);f.ellipsoid('flare',(1.7,4.35,-1),(.28,.65,.28),'glow')
 elif id=='power-core-building':
  shed(f,2.8,2.6,1.9);f.lantern((0,3.1,0),2.6);solar(f,(-1.6,1.5,1.45),1.6,1.0)
  f.pipe('power-conduit',[(.7,.2,1.2),(.7,2.2,1.2),(0,2.4,.4)],.095,'iron',9)
 elif id=='machine-shop':
  shed(f,3.7,3,2.5);canopy(f,(.2,2.8,1.3),3.9,2);crane(f,(-1.5,.2,-1),3.5,3)
  bench(f,(0,1,1.2),2.3);f.lathe('lathe-machine',(.2,1.3,1.2),[(.18,-.5),(.2,.5)],'tin',axis='x');f.crate((-1.7,.55,1.5),.8,'red')
 f.smile((0,2.0,1.65),.28)
 f.sockets['entrance']={'position':[0,.2,2.5],'forward':[0,0,1]}


def defense(f,id):
 platform(f,4.3,2.8)
 if id in ['comic-book-wall','car-door-wall','fridge-barricade','signplate-barricade']:
  for j,mat in enumerate(['red','ivory','paint']):
   x=(j-1)*1.23
   if id=='fridge-barricade':
    f.roundbox('salvaged-fridge',(x,1.25,0),(1.13,2.05+.20*(j%2),.83),mat,.13)
    f.roundbox('freezer-door',(x,1.86,.435),(1.03,.66,.07),mat,.035)
    f.box('fridge-handle',(x+.36,1.1,.5),(.055,.46,.05),'iron')
   elif id=='car-door-wall':
    f.roundbox('car-door',(x,1.12,0),(1.18,1.62,.11),mat,.1)
    f.roundbox('car-window',(x,1.67,.07),(.93,.57,.035),'glass',.03)
    f.box('door-handle',(x+.35,1.18,.10),(.20,.06,.035),'tin')
   else:
    f.panel('salvage-wall',(x,1.3,0),1.16,2.2,mat if id=='signplate-barricade' else 'paint')
    if id=='signplate-barricade':f.roundbox('traffic-sign',(x,1.8,.1),(.96,.9,.06),mat,.16)
  f.smile((0,1.3,.5 if id=='fridge-barricade' else .13),.5)
  for x in [-2,2]:f.beam('barrier-post',(x,.2,0),(x,2.65,0),.16,.18,'iron')
  f.pipe('top-cable',[(-2,2.65,0),(0,2.35,0),(2,2.65,0)],.025,'iron',6)
 elif id=='bathtub-turret':
  f.roundbox('turret-foot',(0,.38,0),(1.9,.5,1.65),'iron',.18)
  f.ring('traverse-bearing',(0,.78,0),.65,.13,'tin')
  with f.part('turret',(0,.8,0),{'clip':'aim','axis':[0,1,0],'angles':[-.7,.7,-.7],'duration':4}):
   # Elliptic open tub: continuous outer wall, rolled rim and inner bowl.
   profile=[(0,0),(.45,0),(.71,.2),(.93,.72),(1,.82),(.97,.90),(.87,.86),(.63,.25),(.35,.17),(0,.17)]
   n=12 if f.far else 24
   for j in range(len(profile)-1):
    def p(i,k):r,y=profile[k];a=i*math.tau/n;return(r*math.cos(a),.85+y,r*.66*math.sin(a))
    for i in range(n):f.face('ivory',[p(i+1,j),p(i,j),p(i,j+1),p(i+1,j+1)],'open-bathtub')
   f.smile((0,1.33,.65),.25);gun(f,(0,1.92,.15),'rotary',1.1)
   f.ellipsoid('rubber-duck',(-.65,1.91,.12),(.26,.21,.25),'signal');f.ellipsoid('duck-head',(-.65,2.06,.19),(.15,.16,.15),'signal');f.roundbox('duck-beak',(-.65,2.03,.29),(.12,.05,.10),'red',.012)
 elif id=='crane-section-watchtower':tower(f,3.8);f.flag((.7,4,0),.8)
 elif id=='spotlight-tower':tower(f,3.5,True);solar(f,(-1,1.2,.7),1.5,1)
 elif id=='scrap-bunker':
  shed(f,3.2,2,1.8);canopy(f,(0,2.1,0),3.4,2.2)
  for x in [-1.2,1.2]:f.panel('bunker-front',(x,.85,1.12),.85,1.45,'tin')
  gun(f,(0,1.33,.9),'rotary',1.1)
 elif id=='spike-gate':
  for x in [-1.7,1.7]:f.roundbox('gate-pillar',(x,1.1,0),(.48,2,.6),'concrete');f.lantern((x,2.25,0),.75)
  with f.part('gate',(-1.45,.25,0),{'clip':'open','axis':[0,1,0],'angles':[0,-math.pi/2],'duration':1.5}):
   for x in [-1.2,-.6,0,.6,1.2]:f.beam('gate-spike',(x,.3,.3),(x,1.9,-.05),.15,.15,'iron')
   for y in [.5,1.75]:f.beam('gate-crossbar',(-1.45,y,0),(1.45,y,0),.17,.17,'signal')
 elif id=='mine-marker':
  f.beam('mine-sign-post',(0,.2,0),(0,1.6,0),.12,.12,'red');f.roundbox('danger-sign',(0,1.4,.06),(1,.8,.07),'red');f.smile((0,1.4,.11),.26);f.lantern((0,2,0),.5)
 elif id=='sandbag-scrap-firing-nest':
  for j in range(12):
   a=j*math.pi/11
   for k in range(3):f.roundbox('sandbag',(1.25*math.cos(a),.35+k*.25,.6*math.sin(a)),(.56,.28,.4),'wood',.12)
  gun(f,(0,1.30,.25),'rotary',1.05)
 elif id=='improvised-anti-vehicle-barrier':
  for z in [-.4,.5]:
   for s in [-1,1]:f.beam('steel-hedgehog',(-s*1.1,.2,z),(s*1.1,1.8,z),.21,.24,'rust')
  f.ring('discarded-tire',(.85,.5,.5),.39,.13,'rubber',axis='z')

def equipment(f,id):
 if id in ['scrap-rifle','pipe-shotgun','compact-smg','improvised-launcher','rotary-gun']:
  gun(f,(0,.40,0),{'scrap-rifle':'rifle','pipe-shotgun':'shotgun','compact-smg':'smg','improvised-launcher':'launcher','rotary-gun':'rotary'}[id]);return
 if id=='wheel-module':f.wheel('wheel',(0,.63,0),.62,.4);return
 if id=='track-module':track(f,(0,.44,0),2.2);return
 if id=='engine-block':
  f.roundbox('engine-block',(0,.55,0),(1.1,.9,.85),'iron')
  for x in [-.4,-.14,.14,.4]:
   f.pipe('engine-cylinder',[(x,.88,0),(x,1.18,0)],.10,'tin',8)
   f.pipe('exhaust-header',[(x,.73,.43),(x,.83,.72),(.5,.4,.73)],.04,'rust',6)
  f.ring('flywheel',(0,.60,.53),.43,.065,'tin',axis='z')
  for j in range(6):
   a=j*math.tau/6;f.beam('fan-blade',(0,.6,.54),(.36*math.cos(a),.6+.36*math.sin(a),.54),.10,.035,'iron')
 elif id=='repair-welder':
  tank(f,(-.45,0,0),.3,1.15,'red');f.crate((.3,.38,0),.65,'signal')
  f.pipe('welder-hose',[(-.45,1.16,0),(-.7,1.4,.25),(0,1.25,.4),(.6,.95,.7)],.045,'rubber',8)
  f.pipe('welding-torch',[(.55,.95,.65),(.75,.95,1)],.065,'tin',8)
 elif id=='mining-drill':
  track(f,(-.4,.3,0),1.4);track(f,(.4,.3,0),1.4)
  f.roundbox('drill-body',(0,.83,0),(.9,.62,1.2),'signal')
  with f.part('auger',(0,.9,.55),{'clip':'operate','axis':[0,0,1],'angles':[0,math.pi/2,math.pi,math.pi*1.5,math.tau],'duration':1}):
   f.lathe('drill-cone',(0,.9,.55),[(.38,0),(.35,.3),(.26,.6),(.12,.95),(0,1.2)],'tin',axis='z')
   for j in range(6):f.ring('drill-flight',(0,.9,.65+j*.15),.37-j*.05,.04,'iron',axis='z')
 elif id=='lantern-scanner':
  for x,z in [(-.4,-.3),(.4,-.3),(0,.5)]:f.beam('scanner-tripod',(x,0,z),(0,1.2,0),.07,.07,'iron')
  f.lantern((0,1.65,0),1.2);f.roundbox('scanner-screen',(.45,1.5,0),(.55,.65,.16),'paint');f.roundbox('scan-display',(.45,1.5,.09),(.41,.45,.025),'cyan');f.dish((.45,1.9,0),.28)
 elif id=='bridge-kit':
  for x in [-.85,.85]:
   f.beam('bridge-girder',(x,.24,-2),(x,.24,2),.20,.32,'iron')
   for j in range(4):f.beam('bridge-web',(x,.12,-2+j),(x,.58,-1+j),.075,.075,'iron')
  for j in range(12):f.roundbox('deck-plank',(0,.64,-1.85+j*.335),(1.95,.13,.30),'wood',.035)
 elif id=='turret-module':
  f.roundbox('turret-foot',(0,.24,0),(1.2,.45,1.1),'iron');f.ring('bearing',(0,.55,0),.46,.09,'tin')
  with f.part('turret',(0,.55,0),{'clip':'aim','axis':[0,1,0],'angles':[-.6,.6,-.6],'duration':4}):
   f.roundbox('turret-armor',(0,.91,0),(.9,.67,.7),'ivory');gun(f,(0,1.02,.3),'rotary',.8);f.smile((0,.88,.37),.21)
 elif id=='meteor-power-cell':
  f.roundbox('power-cell-base',(0,.25,0),(1.65,.50,1.3),'paint');meteor(f,(0,1.23,0),.7)
 f.sockets.setdefault('mount',{'position':[0,0,0],'forward':[0,0,1]})

def ruins(f,c=(0,0,0),w=3,h=4):
 x,y,z=c
 for s in [-1,1]:
  f.panel('broken-building-side',(x+s*w/2,y+h*.4,z),2,h*.8,'concrete',axis='x')
  for k in range(3):
   xx=x+s*w/2;zz=z-.9+k*.65;f.roundbox('broken-parapet',(xx,y+h*.8+.16*(k%2),zz),(.20,.38,.46),'concrete',.04)
 for yy in [1.2,2.5,3.8]:
  if yy>h:continue
  f.roundbox('broken-floor',(x,y+yy,z),(w,.16,1.9),'concrete')
  for xx in [-w*.38,0,w*.38]:
   f.beam('exposed-rebar',(x+xx,y+yy,z+.93),(x+xx+.05,y+yy+.6,z+1.0),.021,.021,'iron')
 for yy in [1.8,3.1]:
  if yy>h:continue
  for xx in [-w*.4,w*.4]:f.roundbox('window-pier',(x+xx,y+yy,z+.95),(.24,1.25,.22),'concrete')
 f.roundbox('back-wall',(x,y+h*.4,z-.95),(w,h*.8,.15),'concrete')

def world(f,id):
 platform(f,7,5.7)
 if id=='ruined-town-block':
  ruins(f,(-.9,.2,-.7),2.8,4.1);ruins(f,(1.7,.2,-.9),1.7,2.5)
  f.roundbox('abandoned-car',(-1,.65,1.7),(1.6,.7,.85),'red');f.roundbox('car-roof',(-1,1.07,1.6),(.9,.39,.7),'rust')
 elif id=='survivor-outpost-cluster':
  shed(f,3,2.5,2.4);canopy(f,(0,2.7,1.5),4.8,1.8)
  # Watch post intentionally smaller than standalone watchtower.
  for x in [2,2.8]:
   for z in [-1.5,-.7]:f.beam('outpost-tower-leg',(x,.2,z),(x,3.6,z),.13,.13,'wood')
  f.roundbox('outpost-watchroom',(2.4,3.4,-1.1),(1.2,.8,1.2),'paint');f.roundbox('watch-window',(2.4,3.6,-.48),(.8,.35,.025),'glow');f.flag((2.7,3.9,-1.2),.8)
  for x in [-2.3,1.8]:f.barrel((x,.2,1.8));f.crate((x,.65,1),.9)
 elif id=='regional-scrap-market-gate':
  for x in [-2.1,2.1]:
   f.roundbox('market-container',(x,1.4,0),(1.35,2.4,2),'paint' if x<0 else 'red')
   f.panel('container-ribs',(x,1.4,1.02),1.25,2.3,'paint' if x<0 else 'red')
  f.beam('market-lintel',(-2.5,3.1,0),(2.5,3.1,0),.35,.4,'iron');canopy(f,(0,3.1,.4),2.7,2.2,'ivory')
  f.smile((0,2.92,1.55),.28)
 elif id=='rail-checkpoint':
  for x in [-.55,.55]:f.beam('rail',(x,.22,-2.5),(x,.22,2.5),.08,.13,'iron')
  for z in [-2,-1.5,-1,-.5,0,.5,1,1.5,2]:f.box('rail-sleeper',(0,.18,z),(1.7,.14,.19),'wood')
  for x in [1.3,2.3]:
   for z in [-1.2,-.2]:f.beam('signal-hut-leg',(x,.2,z),(x,2,z),.14,.14,'iron')
  f.roundbox('signal-hut',(1.8,2.4,-.7),(1.5,1.1,1.5),'paint');f.roundbox('hut-window',(1.8,2.6,.07),(1.15,.45,.03),'glow')
  with f.part('barrier',(1.2,1,.9),{'clip':'open','axis':[0,0,1],'angles':[0,-1.45],'duration':1.8}):
   f.beam('crossing-arm',(-1.3,1,.9),(1.2,1,.9),.16,.16,'ivory')
   for x in [-1,-.3,.4]:f.box('warning-stripe',(x,1,.99),(.3,.17,.025),'red')
 elif id=='bridge-fragment':
  for x in [-2,2]:f.roundbox('bridge-pier',(x,1.65,0),(.8,3,1.6),'concrete')
  for x in [-1.6,-.8,0,.8,1.6]:f.roundbox('bridge-deck',(x,3.2,0),(.77,.25,2.4),'concrete')
  for z in [-1.0,1.0]:f.beam('bridge-rail',(-2.6,3.9,z),(2.6,3.9,z),.08,.08,'iron')
  for x in [-2.3,-1,1,2.3]:
   for z in [-1,1]:f.beam('railpost',(x,3.2,z),(x,3.9,z),.06,.06,'iron')
 elif id=='major-city-wall-section':
  for x in [-2.4,0,2.4]:
   f.roundbox('city-buttress',(x,2.5,0),(.75,4.6,1.4),'concrete')
   if x:f.roundbox('guard-box',(x,5,0),(1.3,.95,1.8),'paint');f.roundbox('guard-window',(x,5.1,.92),(.9,.42,.03),'glow')
  for x in [-1.2,1.2]:f.panel('city-wall',(x,2.3,0),1.75,4.1,'concrete')
  f.smile((0,3.15,.74),.65)
 elif id=='major-city-tower-district':
  for x,z,h in [(-1.8,-.7,3.7),(0,-.9,5.6),(1.8,-.5,4.3)]:
   f.roundbox('stacked-habitat',(x,h/2+.2,z),(1.6,h,1.8),'paint')
   for yy in range(1,int(h)):
    for dx in [-.42,.42]:f.roundbox('district-window',(x+dx,yy+.4,z+.92),(.38,.42,.035),'glow' if yy%2 else 'glass')
   f.roundbox('roof-slab',(x,h+.25,z),(1.9,.17,2),'tin')
  crane(f,(1.5,4.5,-.5),1.8,-3.7)
 elif id=='asteroid-impact-crater-rig':
  for j in range(14):
   a=j*math.tau/14;f.ellipsoid('crater-rim',(2.55*math.cos(a),.75+math.sin(a)**2*.8,1.85*math.sin(a)),(.95,1.35,.95),'concrete',7,4)
  meteor(f,(0,1.35,0),.85);crane(f,(2.1,.2,.9),3.5,-2);f.ladder(-1.5,1.4,2.1)
 elif id=='meteor-reactor':
  f.roundbox('reactor-plinth',(0,.6,0),(3.4,.8,2.7),'paint');meteor(f,(0,2.6,0),1.5)
  for x in [-2.2,2.2]:tank(f,(x,.2,0),.45,2.2,'tin');f.lantern((x,3,0),1)
 elif id=='sky-tracker-dish':
  shed(f,3.7,3,2.1);f.pipe('dish-pedestal',[(0,2.1,0),(0,3.2,0)],.27,'iron',12)
  with f.part('dish',(0,3,0),{'clip':'scan','axis':[0,1,0],'angles':[-.4,.4,-.4],'duration':7}):f.dish((0,3,0),2.1)
 elif id=='strange-late-tech-salvage-structure':
  for r,z in [(2,-.5),(1.1,1.3)]:
   f.ring('alien-housing',(0,2.35,z),r,.32,'tin',axis='z');f.ring('alien-inner-conduit',(0,2.35,z+.10),r*.83,.10,'cyan',axis='z')
   for j in range(8):
    a=j*math.tau/8;f.roundbox('ancient-mechanism',(r*math.cos(a),2.35+r*math.sin(a),z),(.38,.43,.7),'iron')
  canopy(f,(1.6,2.5,1.1),2.3,2.4);f.crate((2.1,.7,1.5),.9)


def build_reference_mesh(asset,lod='near'):
 if lod not in ('near','far'):raise ValueError('lod must be near or far')
 f=SalvageMesh(lod=='far');family=asset['family'];id=asset['id']
 route={'crew':crew,'vehicles':vehicle,'industry':industry,'buildings':building,'defenses':defense,'equipment':equipment,'world':world}
 if family=='utilities':
  platform(f,3,3)
  for x,z in [(-.65,-.5),(.65,-.5),(0,.8)]:f.beam('light-tripod',(x,.2,z),(0,3.3,0),.10,.10,'iron')
  f.lantern((0,3.6,0),2);solar(f,(-.6,1.2,.7),1.2,.9)
 else:route[family](f,id)
 from .rts_detail import dress
 dress(f,asset)
 if family=='equipment':
  floor=min(p[1] for g in f.groups.values() for p in g['p'])
  for g in f.groups.values():g['p']=[(p[0],p[1]-floor,p[2]) for p in g['p']]
  f.pivots={k:(p[0],p[1]-floor,p[2]) for k,p in f.pivots.items()}
  for socket in f.sockets.values():socket['position'][1]-=floor
 if not f.groups:raise ValueError('reference recipe emitted no geometry')
 return f
