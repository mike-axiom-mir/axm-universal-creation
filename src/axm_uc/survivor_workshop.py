"""Authored survivor workshop recipe, independent of any rendering runtime."""
import math
from .surface_geometry import SurfaceBuilder

PALETTE={'iron':('#554A3E',.75,.67),'rust':('#884529',.18,.93),'tin':('#777B70',.65,.57),'paint':('#465851',.45,.78),'canvas':('#827459',0,.96),'wood':('#584432',0,.96),'rubber':('#252823',0,.97),'concrete':('#655F52',0,.95),'glass':('#365256',.15,.28),'signal':('#BFA270',0,.7)}
def lin(x):return x/12.92 if x<=.04045 else ((x+.055)/1.055)**2.4

def workshop(f):
 # Broken concrete pads: stepped irregular perimeter, no perfect foundation box.
 for i,(x,z,w,d) in enumerate([(-1.4,-.2,3.1,5.1),(1.5,-.45,2.9,4.6),(0,2.35,2.1,1.05)]):f.box('old-concrete-pad',(x,.1,z),(w,.2,d),'concrete')
 # Five load-bearing hoops, visible through missing roof panels and open entrance.
 ribs=4 if f.far else 6
 for i in range(ribs):
  z=-2.4+i*4.8/(ribs-1);arc=[(3*math.cos(t),2.45+1.7*math.sin(t),z) for t in [j*math.pi/14 for j in range(15)]]
  f.pipe('arched-rebar-frame',[(3,.2,z),(3,2.45,z)]+arc[1:]+[(-3,.2,z)],.065,'iron',6)
 for x in [-2.95,2.95]:
  for y in [.4,1.8,2.5]:f.beam('salvaged-horizontal-frame',(x,y,-2.4),(x,y,2.4),.10,.08)
 # Metal skins: corrugated in geometry, dented along edges, torn through omissions.
 count_z=4 if f.far else 6;count_a=5
 for az in range(count_a):
  for iz in range(count_z):
   if az in [3,4] and iz==count_z-1:continue
   if az==0 and iz==2:continue
   a0=az*math.pi/count_a+.012;a1=(az+1)*math.pi/count_a-.018;z0=-2.43+iz*4.9/count_z;z1=z0+4.9/count_z+.015
   nu=4 if f.far else 12;nv=2 if f.far else 5;mat=['tin','rust','paint','iron','tin'][(az*3+iz)%5]
   def vertex(u,v):
    t=a0+(a1-a0)*u;z=z0+(z1-z0)*v;corr=.028*math.sin(u*math.pi*12);dent=.1*math.sin(u*4+iz)*math.sin(v*3+az);edge=.08*math.sin(u*13+iz)*v**7
    r=3+corr+dent;return (r*math.cos(t),2.45+(1.7+corr+dent)*math.sin(t)+edge,z)
   for i in range(nu):
    for j in range(nv):
     if not f.far and iz==count_z-1 and (i,j) in [(0,nv-1),(1,nv-1),(nu-1,nv-1)]:continue
     f.double(mat,[vertex(i/nu,j/nv),vertex((i+1)/nu,j/nv),vertex((i+1)/nu,(j+1)/nv),vertex(i/nu,(j+1)/nv)],'bent-corrugated-roof')
 # Salvaged planks and corrugated side infill, mismatched heights and real gaps.
 for side in [-1,1]:
  for i in range(9):
   z=-2.2+i*.53;h=1.4+.48*math.sin(i*1.7+side);x=side*3.02
   f.beam('patched-side-planks',(x,.22,z),(x+side*.025,h,z+.07),.47,.065,'wood' if i%3==0 else 'rust')
  f.beam('diagonal-wall-brace',(side*3.1,.45,-2.3),(side*3.1,2.2,.2),.12,.07,'tin')
 # Rear patch wall assembled from vertical salvage, partly open at roof.
 for i in range(10):
  x=-2.8+i*.59;f.box('rear-cladding',(x,1.35,-2.47),(.54,2.3,.08),'paint' if i%3 else 'rust')
 # Entrance is genuinely open with split sliding doors drawn to either side.
 for side in [-1,1]:
  f.box('door-rail',(side*1.7,2.72,2.61),(2.8,.09,.1),'iron')
  for j in range(4):
   x=side*(1.35+j*.44);f.box('welded-door-panel',(x,1.32,2.64),(.42,2.4,.065),'rust' if j%2 else 'tin')
  f.beam('door-cross-brace',(side*1.35,.3,2.7),(side*2.6,2.4,2.7),.11,.05,'iron')
 # Cantilevered cloth canopy. One pole leans; catenary-like sag and frayed edge.
 corners=[(-2.6,2.85,2.5),(1.05,3.2,2.5),(-3.5,2.08,4.45),(1.35,2.45,4.65)]
 f.cloth('sagging-patch-tarp',corners,.48)
 f.cloth('stitched-tarp-repair',[(-1.6,2.59,3.04),(-.75,2.68,3.04),(-1.6,2.24,3.6),(-.72,2.27,3.6)],.05,'paint')
 for i,c in enumerate(corners[2:]):
  foot=(c[0]+(-.15 if i==0 else .1),.05,c[2]+.1);f.pipe('crooked-canopy-pole',[foot,c],.055,'wood',6)
  anchor=(c[0]+(-.7 if i==0 else .65),.05,c[2]+.65);f.pipe('tension-rope',[c,anchor],.012,'canvas',4)
 # Work area visibly contains fabrication equipment rather than generic crates.
 f.box('workbench-top',(-1.8,.96,3.4),(1.8,.13,.85),'wood')
 for x in [-2.52,-1.07]:f.beam('bench-legs',(x,.18,3.4),(x,.92,3.4),.13,.65)
 f.box('bench-vise',(-1.35,1.14,3.5),(.28,.25,.28),'iron')
 f.pipe('vise-handle',[(-1.52,1.14,3.75),(-1.13,1.14,3.75)],.017,'tin',6)
 f.box('engine-block',(.7,.68,.45),(1.15,.72,.75),'iron')
 for i in range(4):f.pipe('engine-cylinder',[(.31+i*.25,.99,.45),(.31+i*.25,1.23,.45)],.085,'tin',7)
 f.box('engine-skid',(.7,.26,.45),(1.5,.13,1.1),'wood')
 f.pipe('hoist-post',[(2.35,.2,1.6),(2.2,3.55,1.6),(.7,3.4,1.5)],.085,'iron',7)
 f.beam('hoist-brace',(2.3,2.6,1.6),(1.25,3.43,1.5),.075,.075)
 f.pipe('hoist-chain',[(.75,3.4,1.5),(.75,1.75,1.5)],.023,'tin',5)
 f.pipe('hoist-hook',[(.75,1.75,1.5),(.69,1.6,1.5),(.8,1.55,1.5),(.88,1.66,1.5)],.025,'iron',6)
 # Chimney dogleg, salvaged tank, tire stack, external storage and ladder.
 f.pipe('dogleg-exhaust',[(2.5,.3,-1.3),(2.55,3,-1.3),(2.15,3.6,-1.3),(2.15,4.9,-1.3)],.16,'rust',10)
 f.pipe('chimney-cap',[(2.15,4.91,-1.3),(2.15,4.97,-1.3)],.28,'iron',10)
 for i in range(3):f.tire('stacked-tire',(3.7,.16+i*.23,1.5),.42,.23)
 f.pipe('salvage-barrel',[(3.5,.14,-.2),(3.5,1.02,-.2)],.32,'rust',14)
 for y in [.25,.87]:f.pipe('barrel-band',[(3.5,y,-.2),(3.5,y+.045,-.2)],.335,'iron',14)
 f.box('jerrycan',(3.57,.43,-1.05),(.35,.58,.3),'paint');f.box('jerrycan-handle',(3.57,.75,-1.05),(.2,.08,.15),'iron')
 for side in [-1,1]:f.beam('leaning-ladder-rail',(-2.15+side*.23,.12,-2.85),(-2.15+side*.23,3.55,-2.46),.055,.06,'wood')
 for i in range(8):
  y=.32+i*.4;z=-2.85+(y/3.55)*.39;f.beam('ladder-rung',(-2.4,y,z),(-1.9,y,z),.045,.065,'wood')
 # Salvaged sign is cut metal, mounted askew. Abstract wrench geometry, no IP logo.
 f.beam('sign-board',(-.8,3.15,2.71),(.6,3.29,2.71),.5,.045,'paint')
 f.beam('wrench-sign',(-.43,3.14,2.75),(.22,3.3,2.75),.08,.04,'signal')
 f.pipe('wrench-jaw',[(.19,3.35,2.75),(.31,3.36,2.75),(.38,3.27,2.75),(.28,3.22,2.75)],.042,'signal',5)
 # Steel strapping and patch nails at readable spacing.
 if not f.far:
  for z in [-2.35,-.8,.8,2.38]:
   arc=[(3.055*math.cos(t),2.45+1.76*math.sin(t),z) for t in [j*math.pi/18 for j in range(19)]];f.pipe('roof-retaining-strap',arc,.018,'iron',4)
  for side in [-1,1]:
   for z in [-1.9,-.6,.7,2.0]:f.box('repair-bolt',(side*3.11,1.25,z),(.05,.065,.065),'tin')
 return f


def workshop_spec(lod="near"):
    if lod not in ("near", "far"):
        raise ValueError("lod must be near or far")
    forge = workshop(SurfaceBuilder(far=lod == "far"))
    primitives = []
    for name, group in forge.groups.items():
        color, metallic, roughness = PALETTE[name]
        rgb = [lin(int(color[i:i+2], 16)/255) for i in (1, 3, 5)]
        linear_color = "#" + "".join(f"{round(value*255):02x}" for value in rgb) + "ff"
        primitives.append({"id": name, "positions": group["p"], "normals": group["n"],
                           "indices": group["i"], "colors": group["c"],
                           "material": {"color": linear_color, "metallic": metallic, "roughness": roughness}})
    return {"schema": "axm.surface-3d/v0.1", "name": "building-workshop-a-" + lod, "primitives": primitives}
