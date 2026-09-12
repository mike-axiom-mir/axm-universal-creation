"""Authored small-scale salvage details and geometric sign lettering."""
import math
from .surface_geometry import add

# Original hand-entered 3x5 stencil alphabet; each run becomes two real triangles.
FONT=dict(zip('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789',[
'010101111101101','110101110101110','011100100100011','110101101101110','111100110100111','111100110100100','011100101101011','101101111101101','111010010010111','001001001101010','101101110101101','100100100100111','101111111101101','101111111111101','010101101101010','110101110100100','010101101111011','110101110101101','011100010001110','111010010010010','101101101101111','101101101101010','101101111111101','101101010101101','101101010010010','111001010100111',
'111101101101111','010110010010111','110001010100111','110001010001110','101101111001001','111100110001110','011100111101111','111001010010010','111101111101111','111101111001110']))

def lettering(f,lines,c,w=1,h=1):
 x,y,z=c;maxchars=max(map(len,lines));cell=min(w/(maxchars*4),h/(len(lines)*6));total=len(lines)*6*cell
 for row,text in enumerate(lines):
  left=x-len(text)*4*cell/2;top=y+total/2-row*6*cell
  for k,ch in enumerate(text):
   bits=FONT.get(ch,'0'*15)
   for r in range(5):
    for col in range(3):
     if bits[r*3+col]=='1':
      xx=left+(k*4+col)*cell;yy=top-r*cell
      f.face('rubber',[(xx,yy-cell,z),(xx+cell*.90,yy-cell,z),(xx+cell*.90,yy,z),(xx,yy,z)],'stencil-letter',False)

def sign(f,c,lines,w=1.15,h=1.5,mat='ivory'):
 x,y,z=c;f.roundbox('salvaged-sign',c,(w,h,.065),mat,.025)
 if f.far:f.smile((x,y,z+.04),min(w,h)*.25)
 else:
  lettering(f,lines,(x,y+h*.13,z+.037),w*.83,h*.58);f.smile((x,y-h*.30,z+.04),w*.14)
  for dx in [-w*.43,w*.43]:
   for dy in [-h*.44,h*.44]:f.pipe('sign-bolt',[(x+dx,y+dy,z+.035),(x+dx,y+dy,z+.057)],.028,'iron',6)

def patches(f,c,w,h,axis='z'):
 x,y,z=c
 for j in range(3 if f.far else 8):
  dx=math.sin(j*2.4)*w*.35;dy=math.cos(j*1.7)*h*.37;ww=w*(.14+.06*(j%2));hh=h*(.13+.08*(j%3))
  pos=(x+dx,y+dy,z+.052) if axis=='z' else (x+.052,y+dy,z+dx)
  size=(ww,hh,.035) if axis=='z' else (.035,hh,ww)
  f.roundbox('welded-repair-plate',pos,size,['rust','tin','ivory','paint'][j%4],.008)
  if not f.far:
   for a in [-1,1]:
    q=(pos[0]+a*ww*.38,pos[1]+hh*.35,pos[2]+.022) if axis=='z' else (pos[0]+.022,pos[1]+hh*.35,pos[2]+a*ww*.38)
    f.ellipsoid('patch-fastener',q,(.037,.037,.037),'tin',6,3)

def cargo(f,c=(0,1,0),s=1):
 f.crate(c,s)
 for y in [-.20,0,.20]:f.box('crate-plank-seam',add(c,(0,y*s,.33*s)),(.98*s,.023*s,.02*s),'soil')
 for x in [-.32,.32]:f.pipe('cargo-rope',[add(c,(x*s,-.37*s,.38*s)),add(c,(x*s,.42*s,.36*s)),add(c,(x*s,.42*s,-.36*s)),add(c,(x*s,-.37*s,-.38*s))],.019*s,'canvas',5)

def dress(f,a):
 id=a['id'];family=a['family']
 if family=='crew':
  # Smaller seams and hardware live in their existing moving component.
  for s in [-1,1]:
   name='leg-'+str(s).replace('-','m')
   with f.part(name,(s*.18,.92,0)):
    for yy in [.35,.68,.79]:f.beam('trouser-seam',(s*.18-.10,yy,.135),(s*.18+.10,yy-.016,.135),.02,.014,'wood')
    for yy in [.16,.22,.27]:f.beam('boot-lacing',(s*.18-.07,yy,.315),(s*.18+.07,yy+.045,.315),.014,.012,'tin')
   with f.part('arm-'+str(s).replace('-','m'),(s*.37,1.38,0)):
    f.ellipsoid('shoulder-armor',(s*.40,1.38,.09),(.27,.24,.24),'tin' if id=='heavy-vehicle-operator' else 'wood')
    f.smile((s*.42,1.36,.223),.065)
  for y in [1.08,1.20,1.32,1.44]:f.pipe('coat-button',[(.045,y,.216),(.045,y,.237)],.025,'tin',6)
  for x in [-.20,.20]:
   f.roundbox('chest-pocket',(x,1.23,.25),(.19,.22,.065),'darkcloth',.021)
   f.box('pocket-flap',(x,1.32,.295),(.20,.047,.019),'wood')
  f.pipe('canteen',[(-.42,.93,-.22),(-.42,1.22,-.22)],.10,'paint',8)
  f.pipe('radio',[(-.27,1.60,-.36),(-.27,2.16,-.36)],.013,'iron',5)
  with f.part('head',(0,1.55,0)):
   f.ellipsoid('nose',(0,1.66,.265),(.105,.14,.12),'skin')
   for x in [-.2,.2]:f.pipe('helmet-rivet',[(x,1.96,.23),(x,1.96,.25)],.025,'tin',6)
   if id=='shotgun-raider':
    for x in [-.20,0,.20]:f.lathe('helmet-spike',(x,2.04,0),[(.055,0),(0,.18)],'tin',n=7)
   if id in ['mercenary-ex-mil','licensed-driver']:
    f.ellipsoid('beard',(0,1.56,.25),(.33,.25,.18),'wood' if id=='licensed-driver' else 'tin')
  if id=='heavy-vehicle-operator':
   for x in [-.15,.15]:f.roundbox('chest-plate',(x,1.21,.28),(.27,.41,.055),'signal',.04)
  return
 if family=='vehicles':
  length=4.8 if id in ['flatbed-convoy-truck','armored-bus','cargo-trailer','mercenary-carrier','crane-truck','drill-rig-vehicle'] else 3.1
  width=1.85 if length>4 else 1.5
  if id in ['scout-trike','push-cart']:return
  if id in ['scrap-buggy']:
   for x in [-.51,.51]:
    f.pipe('front-suspension',[(x,.45,1),(x,.94,.7)],.055,'tin',7)
    for j in range(5):f.ring('spring-coil',(x,.51+j*.07,.97-j*.045),.09,.022,'iron')
   f.roundbox('exposed-engine',(0,1.0,-.95),(.7,.43,.45),'iron')
   for x in [-.25,-.08,.08,.25]:f.pipe('intake-pipe',[(x,1.1,-.95),(x,1.35,-.95)],.065,'tin',8)
  else:
   for s in [-1,1]:
    patches(f,(s*width*.48,1.05,0),length*.65,.62,axis='x')
    f.pipe('side-step',[(s*width*.57,.71,-.7),(s*width*.57,.71,.8)],.06,'tin',8)
   for x in [-.27,.27]:f.beam('windshield-wiper',(x,1.40,length*.47+.02),(x+.19,1.79,length*.47+.02),.023,.019,'rubber')
  f.pipe('bullbar',[(-width*.45,.85,length*.5+.22),(-width*.45,1.30,length*.5+.22),(width*.45,1.30,length*.5+.22),(width*.45,.85,length*.5+.22)],.05,'iron',8)
  if id in ['armored-bus','mercenary-carrier']:
   for s in [-1,1]:
    for j in range(6):
     zz=-1.7+j*.64;f.beam('window-cage',(s*width*.49,1.43,zz),(s*width*.49,2.05,zz+.15),.035,.035,'iron')
   cargo(f,(0,2.44,.7),.74)
  elif id not in ['cargo-trailer','tow-crawler','crane-truck','drill-rig-vehicle']:cargo(f,(0,1.75,-length*.3),.64)
  return
 if family in ['buildings','industry']:
  # Yard clutter, functional plumbing and repair details keep large surfaces from
  # reducing to pristine boxes. Every family keeps its distinct silhouette.
  f.barrel((-2.20,.20,1.60),.29,.79,'paint');cargo(f,(1.9,.51,1.8),.70)
  for j in range(2):f.ring('yard-tire',(2.05,.24+j*.20,-1.4),.34,.09,'rubber')
  if family=='buildings':
   if id not in ['refinery-shack','training-yard']:patches(f,(2.05,1.2,-.2),2.5,1.7,axis='x')
   messages={'settlement-hub':['PEOPLE','KEEP','PEOPLE','GOING'],'civic-shelter':['SAME','MESS','NEW','DAY'],'improvised-workshop':['GOOD','STUFF','LASTS'],'command-signal-hall':['FARTHER','TOGETHER'],'training-yard':['PRACTICE','SURVIVES'],'repair-garage':['FIX','IT','AGAIN'],'storage-hall':['SUPPLIES','TOMORROW'],'refinery-shack':['NOT','WASTE','FUEL'],'power-core-building':['SMALL','POWER','BIG','PEOPLE'],'machine-shop':['OLD','TOOLS','NEW','DAYS']}
   sign(f,(-1.05,1.58,1.86),messages[id],1.1,1.4)
  else:
   messages={'open-crop-terrace':['DIRT','FOOD','HOPE'],'bus-window-greenhouse':['GREENER','DAYS','AHEAD'],'fungal-shed':['SHROOMS','FEED','PEOPLE'],'livestock-pen':['HAPPY','STOMACHS'],'water-catcher':['EVERY','DROP','COUNTS'],'scrap-sorting-yard':['TRASH','INTO','TOMORROW'],'shallow-mine-entrance':['DIG','A LITTLE','LIVE','A LOT'],'deep-mine-head':['GO','DEEPER'],'asteroid-extraction-rig':['SPACE','PAYS'],'battery-fuel-station':['CHARGE','REFUEL'],'clustered-storage-bins':['FOOD','METAL','SUPPLIES']}
   sign(f,(1.4,1.25,1.93),messages[id],.95,1.35)
 elif family=='defenses':
  if id in ['comic-book-wall','car-door-wall','fridge-barricade','signplate-barricade']:
   patches(f,(-1.2,.85,.08 if id!='fridge-barricade' else .46),1.0,1.0)
   patches(f,(1.2,.9,.08 if id!='fridge-barricade' else .46),1.0,1.25)
   sign(f,(0,1.26,.56 if id=='fridge-barricade' else .15),{'comic-book-wall':['TAKE','THAT'],'car-door-wall':['STILL','DRIVES','US HOME'],'fridge-barricade':['COLD','HARD','SAFER'],'signplate-barricade':['GO','AROUND']}[id],.82,1.1)
   for j in range(8):f.ring('wire-loop',(-1.7+j*.48,2.57,0),.11,.013,'iron',axis='z')
   f.barrel((-1.65,.2,.73),.25,.65,'paint');f.lantern((1.95,2.85,0),.55)
  elif id=='bathtub-turret':
   with f.part('turret',(0,.8,0)):
    for x in [-.70,.70]:f.pipe('tub-plumbing',[(x,1.03,0),(x*1.25,1.05,0),(x*1.25,1.73,0)],.055,'rust',8)
    for j in range(8):
     a=j*math.tau/8;f.ellipsoid('tub-rivet',(.91*math.cos(a),1.57,.61*math.sin(a)),(.07,.07,.07),'iron',6,3)
   for s in [-1,1]:f.beam('turret-brace',(s*.73,.35,.6),(s*.32,.85,.3),.15,.18,'signal')
  else:
   sign(f,(1.45,1.03,1),['STILL','HERE'],.72,1.0);f.barrel((-1.5,.2,.7),.24,.65)
 elif family=='world':
  for x in [-2.6,2.6]:f.barrel((x,.2,1.9),.27,.85);cargo(f,(x,.55,1),.7)
  sign(f,(-1.9,1.3,2.0),['OLD','WORLD','NEW','IDEAS'],1.15,1.6)
