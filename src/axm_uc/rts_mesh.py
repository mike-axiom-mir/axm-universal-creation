"""Reusable, dependency-free salvage surfaces and named rigid articulation.

All coordinates are meters, Y up, Z forward. References are interpreted by an
explicit authored recipe; this module does not reconstruct unseen image geometry.
"""
import math
from contextlib import contextmanager
from .surface_geometry import SurfaceBuilder, add, sub, mul, cross, norm
from .survivor_workshop import lin

PALETTE = {
 'iron':('#424b4c',.75,.58), 'rust':('#985034',.35,.86),
 'tin':('#aeb6ad',.65,.48), 'paint':('#337e82',.45,.66),
 'canvas':('#386c7c',0,.96), 'wood':('#8e6b44',0,.94),
 'rubber':('#242c30',0,.92), 'concrete':('#929083',0,.94),
 'glass':('#77b7b6',.25,.16), 'signal':('#edb63e',.25,.53),
 'ivory':('#e0d5b7',.12,.78), 'red':('#b64437',.28,.7),
 'skin':('#bd8d69',0,.85), 'cloth':('#606f59',0,.95),
 'darkcloth':('#434c41',0,.94), 'leaf':('#647c36',0,.9),
 'leaflight':('#96ad4b',0,.91), 'soil':('#504135',0,1),
 'glow':('#ffd080',0,.25), 'cyan':('#37d9dc',.15,.23),
}

class SalvageMesh(SurfaceBuilder):
 def __init__(self, far=False):
  super().__init__(far); self.active='body'; self.pivots={'body':(0,0,0)}; self.motion={}; self.sockets={}
 def face(self,mat,verts,tag,weather=True):
  # SurfaceBuilder generates deterministic vertex weathering; keep that palette
  # lookup separate from the component/group key.
  stash=self.groups; self.groups={}
  super().face(mat,verts,tag,weather)
  emitted=self.groups; self.groups=stash
  key=self.active+'__'+mat
  for g in emitted.values():
   target=self.groups.setdefault(key,{'p':[],'n':[],'i':[],'c':[]})
   offset=len(target['p']);target['p'].extend(g['p']);target['n'].extend(g['n']);target['c'].extend(g['c']);target['i'].extend(i+offset for i in g['i'])
 @contextmanager
 def part(self,name,pivot,motion=None):
  old=self.active;self.active=name
  if name in self.pivots and tuple(pivot)!=tuple(self.pivots[name]):raise ValueError('conflicting component pivot')
  self.pivots[name]=tuple(pivot)
  if motion:self.motion[name]=motion
  try:yield self
  finally:self.active=old
 def ellipsoid(self,tag,c,size,mat='iron',segments=None,rings=None):
  n=segments or (8 if self.far else 14);m=rings or (5 if self.far else 8)
  def p(i,j):
   t=math.pi*j/m;a=math.tau*i/n
   return(c[0]+size[0]*.5*math.sin(t)*math.cos(a),c[1]+size[1]*.5*math.cos(t),c[2]+size[2]*.5*math.sin(t)*math.sin(a))
  for j in range(m):
   for i in range(n):self.face(mat,[p(i,j),p(i+1,j),p(i+1,j+1),p(i,j+1)],tag)
 def lathe(self,tag,c,profile,mat='iron',n=None,axis='y'):
  n=n or (10 if self.far else 18)
  def p(i,j):
   r,y=profile[j];a=math.tau*i/n;v=(r*math.cos(a),y,r*math.sin(a))
   if axis=='z':v=(v[0],-v[2],v[1])
   if axis=='x':v=(v[1],v[2],v[0])
   return add(c,v)
  for j in range(len(profile)-1):
   for i in range(n):self.face(mat,[p(i+1,j),p(i,j),p(i,j+1),p(i+1,j+1)],tag)
 def roundbox(self,tag,c,size,mat='iron',bevel=.10):
  # Convex box with a beveled eight-point perimeter and inset top/bottom.
  if self.far:
   self.box(tag,c,size,mat);return
  w,h,d=size; b=min(bevel,w*.24,h*.24,d*.24)
  shape=[(-w/2+b,-d/2),(w/2-b,-d/2),(w/2,-d/2+b),(w/2,d/2-b),(w/2-b,d/2),(-w/2+b,d/2),(-w/2,d/2-b),(-w/2,-d/2+b)]
  rings=[]
  for y,inset in [(-h/2,b),(-h/2+b,0),(h/2-b,0),(h/2,b)]:
   rings.append([(c[0]+x*(1-2*inset/w),c[1]+y,c[2]+z*(1-2*inset/d)) for x,z in shape])
  self.face(mat,rings[0],tag);self.face(mat,list(reversed(rings[-1])),tag)
  for j in range(3):
   for i in range(8):k=(i+1)%8;self.face(mat,[rings[j][k],rings[j][i],rings[j+1][i],rings[j+1][k]],tag)
 def ring(self,tag,c,r,tube,mat='iron',axis='y',ratio=1):
  n=10 if self.far else 20;m=4 if self.far else 6
  def p(i,j):
   a=i*math.tau/n;b=j*math.tau/m;rr=r+tube*math.cos(b);v=(rr*math.cos(a),tube*math.sin(b),rr*math.sin(a)*ratio)
   if axis=='x':v=(v[1],v[2],v[0])
   if axis=='z':v=(v[0],-v[2],v[1])
   return add(c,v)
  for i in range(n):
   for j in range(m):self.face(mat,[p(i,j+1),p(i+1,j+1),p(i+1,j),p(i,j)],tag)
 def wheel(self,name,c,r=.48,width=.30,animated=True):
  motion={'clip':'drive','axis':[1,0,0],'angles':[0,math.pi/2,math.pi,math.pi*1.5,math.tau],'duration':1} if animated else None
  with self.part(name,c,motion):
   self.ring('rubber-tire',c,r*.76,r*.24,'rubber',axis='x')
   self.pipe('wheel-hub',[(c[0]-width/2,c[1],c[2]),(c[0]+width/2,c[1],c[2])],r*.52,'iron',10)
   for s in [-1,1]:
    x=c[0]+s*width*.53;self.pipe('hubcap',[(x,c[1],c[2]),(x+s*.025,c[1],c[2])],r*.28,'signal',10)
    if not self.far:
     for j in range(6):
      a=j*math.tau/6;self.ellipsoid('lug',(x+s*.034,c[1]+r*.38*math.cos(a),c[2]+r*.38*math.sin(a)),(.045,.045,.045),'tin',6,3)
   for j in range(10 if self.far else 18):
    a=j*math.tau/(10 if self.far else 18);d=.13
    self.beam('tread',(c[0]-width*.44,c[1]+r*.94*math.cos(a-d),c[2]+r*.94*math.sin(a-d)),(c[0]+width*.44,c[1]+r*.94*math.cos(a+d),c[2]+r*.94*math.sin(a+d)),r*.15,r*.10,'rubber')
 def panel(self,tag,c,w,h,mat='paint',axis='z'):
  n=max(3,int(w*(3 if self.far else 7)))
  for i in range(n):
   x0=-w/2+w*i/n;x1=-w/2+w*(i+1)/n
   def p(x,y):
    z=.035*math.cos((x+w/2)*math.pi*n/w);v=(x,y,z)
    if axis=='x':v=(z,y,-x)
    return add(c,v)
   self.double(mat,[p(x0,-h/2),p(x1,-h/2),p(x1,h/2),p(x0,h/2)],tag)
  if not self.far:
   for x in [-w*.43,w*.43]:
    for y in [-h*.42,h*.42]:
     v=(x,y,.048) if axis=='z' else (.048,y,-x)
     self.ellipsoid('panel-rivet',add(c,v),(.05,.05,.05),'tin',6,3)
 def smile(self,c,r=.25):
  self.pipe('smile-badge',[add(c,(0,0,-.012)),add(c,(0,0,.012))],r,'signal',16)
  for s in [-1,1]:self.ellipsoid('smile-eye',add(c,(s*r*.32,r*.25,.018)),(r*.17,r*.24,.022),'rubber',6,4)
  self.pipe('smile-mouth',[add(c,(r*.60*math.cos(t),r*.58*math.sin(t),.034)) for t in [math.pi+j*math.pi/9 for j in range(10)]],r*.053,'rubber',5)
 def lantern(self,c,s=1):
  self.pipe('lantern-core',[add(c,(0,-.22*s,0)),add(c,(0,.22*s,0))],.12*s,'glow',8)
  for y,r in [(-.26,.22),(.26,.22),(.32,.15)]:self.pipe('lantern-cap',[add(c,(0,y*s,0)),add(c,(0,(y+.045)*s,0))],r*s,'iron',10)
  for j in range(4):
   a=math.tau*j/4;self.pipe('lantern-cage',[add(c,(.18*s*math.cos(a),-.27*s,.18*s*math.sin(a))),add(c,(.18*s*math.cos(a),.29*s,.18*s*math.sin(a)))],.017*s,'tin',5)
  self.ring('lantern-handle',add(c,(0,.41*s,0)),.08*s,.018*s,'iron',axis='z')
 def crate(self,c,s=1,mat='wood'):
  self.roundbox('supply-box',c,(s,.7*s,.65*s),mat,.04*s)
  for x in [-.41,.41]:self.box('crate-strap',add(c,(x*s,0,0)),(.08*s,.74*s,.69*s),'iron')
  self.box('crate-latch',add(c,(0,.11*s,.35*s)),(.15*s,.15*s,.04*s),'tin')
 def barrel(self,c,r=.32,h=.85,mat='paint'):
  self.lathe('barrel',c,[(0,0),(r*.92,0),(r,h*.08),(r,h*.92),(r*.92,h),(0,h)],mat)
  for y in [.1,.32,.74,.94]:self.ring('barrel-hoop',add(c,(0,y*h,0)),r,.023,'iron')
 def flag(self,c,s=1):
  self.pipe('flag-pole',[c,add(c,(0,2*s,0))],.03*s,'iron',6)
  x,y,z=add(c,(0,1.9*s,0));self.cloth('flag',[(x,y,z),(x+s,y-.09*s,z+.1*s),(x,y-.62*s,z),(x+s,y-.7*s,z+.1*s)],.05*s,'signal')
  self.smile((x+.48*s,y-.31*s,z+.085*s),.19*s)
 def plant(self,c,s=1):
  self.pipe('stem',[c,add(c,(0,.72*s,0))],.025*s,'leaf',5)
  for j in range(4 if self.far else 7):
   a=j*2.4;y=.13+j*.08;v=(math.cos(a),.5,math.sin(a));center=add(c,(0,y*s,0));tip=add(center,mul(v,.45*s));side=(-v[2]*.11*s,.02*s,v[0]*.11*s)
   self.double('leaflight' if j%2 else 'leaf',[center,add(mul(add(center,tip),.5),side),tip,sub(mul(add(center,tip),.5),side)],'leaf')
 def ladder(self,x,z,height,y=0):
  for s in [-1,1]:self.beam('ladder-rail',(x+s*.23,y,z+.35),(x+s*.23,y+height,z),.06,.06,'wood')
  for j in range(max(2,int(height/.32))):
   yy=.2+j*.32;zz=z+.35*(1-yy/height);self.beam('ladder-rung',(x-.23,y+yy,zz),(x+.23,y+yy,zz),.055,.075,'tin')
 def dish(self,c,r=1):
  # Parabolic bowl faces +Y; supporting feed and rim distinguish it from a disk.
  self.lathe('dish-bowl',c,[(0,0),(r*.3,r*.035),(r*.65,r*.16),(r,r*.40),(r,r*.43),(r*.65,r*.19),(r*.3,r*.065),(0,r*.03)],'ivory')
  self.ring('dish-rim',add(c,(0,r*.415,0)),r,.026,'iron')
  for j in range(3):
   a=j*math.tau/3;self.beam('dish-feed-support',add(c,(r*.9*math.cos(a),r*.35,r*.9*math.sin(a))),add(c,(0,r*1.05,0)),.025,.025,'iron')
  self.ellipsoid('dish-feed',add(c,(0,r*1.05,0)),(.17*r,.22*r,.17*r),'tin')
 def surface_spec(self,name):
  groups=[]
  for key,g in self.groups.items():
   component,mat=key.split('__');color,metal,rough=PALETTE[mat]
   rgb=[lin(int(color[i:i+2],16)/255) for i in (1,3,5)]
   # Exact welding preserves sharp edges and all authored vertex attributes.
   unique={};positions=[];normals=[];colors=[];indices=[]
   for i in g['i']:
    item=tuple(g['p'][i])+tuple(g['n'][i])+tuple(g['c'][i])
    if item not in unique:
     unique[item]=len(positions);positions.append(g['p'][i]);normals.append(g['n'][i]);colors.append(g['c'][i])
    indices.append(unique[item])
   groups.append({'id':key,'positions':positions,'normals':normals,'indices':indices,'colors':colors,'material':{'color':'#'+''.join(f'{round(v*255):02x}' for v in rgb)+'ff','metallic':metal,'roughness':rough}})
  return {'schema':'axm.surface-3d/v0.1','name':name,'primitives':groups}
