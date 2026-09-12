"""Original deterministic surface construction helpers: beams, pipes, cloth and tires.

Adapted from the authored survivor workshop v03 recipe. No process-global patches.
"""
import math

def cross(a,b):return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def sub(a,b):return tuple(a[i]-b[i] for i in range(3))
def add(a,b):return tuple(a[i]+b[i] for i in range(3))
def mul(a,s):return tuple(x*s for x in a)
def norm(a):
 l=math.sqrt(sum(v*v for v in a));return tuple(v/l for v in a)
class SurfaceBuilder:
 def __init__(self,far=False):self.far=far;self.groups={};self.parts=[]
 def face(self,mat,verts,tag,weather=True):
  g=self.groups.setdefault(mat,{'p':[],'n':[],'i':[],'c':[]})
  for j in range(1,len(verts)-1):
   v=[verts[0],verts[j],verts[j+1]];n=cross(sub(v[1],v[0]),sub(v[2],v[0]));le=math.sqrt(sum(x*x for x in n))
   if le<1e-10:continue
   n=mul(n,1/le);off=len(g['p']);g['p'].extend(v);g['n'].extend([n]*3);g['i'].extend([off,off+1,off+2])
   for x,y,z in v:
    # Position-based age: streaks follow gravity, grime collects near ground.
    grain=.5+.5*math.sin(x*16.3+math.sin(z*11)*1.5+y*7.1)
    streak=.5+.5*math.sin(x*31+z*19+math.sin(y*1.2)*.6)
    grime=.68+.32*min(1,max(0,y/.8));value=(.80+.20*grain)*grime
    c=[value]*3
    if mat in ['tin','paint','iron'] and weather:
     rust=(.5+.5*math.sin(x*4.3+math.sin(z*5.1)+y*.9))*streak
     if rust>.57:c=[value*.96,value*.57,value*.31]
    if mat=='canvas':c=[value*(.78+.22*streak)]*3
    g['c'].append((*c,1))
  self.parts.append(tag)
 def double(self,mat,verts,tag):self.face(mat,verts,tag);self.face(mat,list(reversed(verts)),tag)
 def beam(self,tag,start,end,width,depth,mat='iron'):
  direction=norm(sub(end,start));side=norm(cross(direction,(0,1,0) if abs(direction[1])<.95 else (0,0,1)));up=norm(cross(side,direction))
  corners=[]
  for center in [start,end]:
   corners.extend([add(center,add(mul(side,s*width/2),mul(up,t*depth/2))) for s,t in [(-1,-1),(1,-1),(1,1),(-1,1)]])
  for f in [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]:self.face(mat,[corners[i] for i in reversed(f)],tag)
 def box(self,tag,c,size,mat):self.beam(tag,(c[0],c[1]-size[1]/2,c[2]),(c[0],c[1]+size[1]/2,c[2]),size[2],size[0],mat)
 def pipe(self,tag,path,r,mat='iron',sides=7):
  rings=[]
  for i,c in enumerate(path):
   d=norm(sub(path[min(i+1,len(path)-1)],path[max(0,i-1)]));u=norm(cross(d,(0,1,0) if abs(d[1])<.9 else (0,0,1)));v=norm(cross(d,u));rings.append([add(c,add(mul(u,r*math.cos(j*2*math.pi/sides)),mul(v,r*math.sin(j*2*math.pi/sides)))) for j in range(sides)])
  for i in range(len(rings)-1):
   for j in range(sides):k=(j+1)%sides;self.face(mat,[rings[i][j],rings[i][k],rings[i+1][k],rings[i+1][j]],tag)
  self.face(mat,list(reversed(rings[0])),tag);self.face(mat,rings[-1],tag)
 def tire(self,tag,c,r=.42,width=.24):
  seg=12 if self.far else 20;minor=4 if self.far else 6
  def v(i,j):
   theta=i*2*math.pi/seg;phi=j*2*math.pi/minor;rad=r*.72+r*.28*math.cos(phi)
   return(c[0]+rad*math.cos(theta),c[1]+width/2*math.sin(phi),c[2]+rad*math.sin(theta))
  for i in range(seg):
   for j in range(minor):self.face('rubber',[v(i,j+1),v(i+1,j+1),v(i+1,j),v(i,j)],tag)
 def cloth(self,tag,corners,sag,mat='canvas'):
  n=4 if self.far else 12;m=3 if self.far else 9
  def at(u,v):
   x=[(1-v)*((1-u)*corners[0][k]+u*corners[1][k])+v*((1-u)*corners[2][k]+u*corners[3][k]) for k in range(3)]
   x[1]-=sag*math.sin(math.pi*u)*math.sin(math.pi*v)
   x[1]+=.055*math.sin(u*34+v*7)*math.sin(v*math.pi)
   return x
  for i in range(n):
   for j in range(m):
    if not self.far and (i,j) in [(0,m-1),(1,m-1),(n-1,m-1)]:continue
    self.double(mat,[at(i/n,j/m),at((i+1)/n,j/m),at((i+1)/n,(j+1)/m),at(i/n,(j+1)/m)],tag)
