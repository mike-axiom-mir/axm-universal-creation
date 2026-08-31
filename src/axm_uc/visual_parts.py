from __future__ import annotations

import math
import random

MESH_PARTS=(
 "wall","floor","roof","stair","column","arch","door","window-frame","pipe","vent","crate","barrel","rock","crystal","tree-trunk","branch","bolt","plate","armor-panel","wheel","gear","turret-base","antenna","rail","fence","road-block","greeble","console","beam","bracket","socket","thruster",
)
VECTOR_PARTS=(
 "border","corner-border","ornament","rune","tech-rune","panel-trim","pipe-trim","cable-trim","road-marking","hazard-trim","fantasy-carving","celtic-knot","geometric-tile","circuit-strip","greeble-strip","riveted-strip","window-frame","door-frame","badge-frame","shield-emblem","wing-emblem","leaf-vine","crystal-cluster","mountain-icon","planet-icon","bot-face","energy-glyph","arrow-set","target-ring","grid-overlay",
)

def _box(v,f,x,y,z,w,h,d):
    n=len(v)+1; v += [(x,y,z),(x+w,y,z),(x+w,y+h,z),(x,y+h,z),(x,y,z+d),(x+w,y,z+d),(x+w,y+h,z+d),(x,y+h,z+d)]
    f += [(n,n+1,n+2,n+3),(n+4,n+7,n+6,n+5),(n,n+4,n+5,n+1),(n+1,n+5,n+6,n+2),(n+2,n+6,n+7,n+3),(n+4,n,n+3,n+7)]

def _cyl(v,f,cx,cy,z,r,h,seg=12):
    n=len(v)+1
    for zz in (z,z+h):
        for i in range(seg):
            a=2*math.pi*i/seg; v.append((cx+math.cos(a)*r,cy+math.sin(a)*r,zz))
    for i in range(seg):
        j=(i+1)%seg; f.append((n+i,n+j,n+seg+j,n+seg+i))
    f.append(tuple(n+i for i in range(seg))); f.append(tuple(n+seg+i for i in reversed(range(seg))))

def mesh_obj(kind:str,seed:int=0)->str:
    kind=kind.strip().casefold()
    if kind not in MESH_PARTS: raise KeyError(f"unknown mesh part: {kind}")
    rng=random.Random(seed); v=[]; f=[]
    if kind in {"wall","floor","door","plate","armor-panel","road-block","beam","bracket","console","greeble","socket"}:
        dims={"wall":(2,.2,1.4),"floor":(2,2,.12),"door":(.9,.15,1.8),"plate":(1,.12,.7),"armor-panel":(1.2,.18,.8),"road-block":(1.5,.6,.6),"beam":(2,.2,.2),"bracket":(.7,.35,.7),"console":(1,.5,.8),"greeble":(.8,.5,.3),"socket":(.5,.5,.25)}[kind]
        _box(v,f,-dims[0]/2,-dims[1]/2,0,*dims)
        if kind in {"armor-panel","greeble","console"}: _box(v,f,-.28,-.18,dims[2],.56,.36,.12)
    elif kind=="roof":
        _box(v,f,-1,-.8,0,2,1.6,.12); _box(v,f,-.8,-.6,.12,1.6,1.2,.25)
    elif kind=="stair":
        for i in range(6): _box(v,f,-.7,-.6+i*.18,i*.16,1.4,.22,.16)
    elif kind in {"column","pipe","barrel","tree-trunk","bolt","wheel","gear","turret-base","antenna","thruster"}:
        r,h={"column":(.25,1.8),"pipe":(.15,1.6),"barrel":(.35,1),"tree-trunk":(.28,1.7),"bolt":(.18,.7),"wheel":(.45,.2),"gear":(.5,.18),"turret-base":(.55,.35),"antenna":(.06,1.6),"thruster":(.3,.7)}[kind]
        _cyl(v,f,0,0,0,r,h,16 if kind in {"wheel","gear","turret-base"} else 12)
    elif kind in {"arch","window-frame","vent","rail","fence"}:
        if kind=="arch":
            _box(v,f,-.8,-.12,0,.2,.24,1.5); _box(v,f,.6,-.12,0,.2,.24,1.5); _box(v,f,-.8,-.12,1.3,1.6,.24,.2)
        elif kind=="window-frame":
            for x,y,w,h in [(-.8,-.08,.15,1.2),(.65,-.08,.15,1.2),(-.8,-.08,1.6,.15),(-.8,-.08,1.6,.15)]: _box(v,f,x,y,0,w,.16,h)
        else:
            count=6 if kind!="vent" else 8
            for i in range(count): _box(v,f,-.8+i*.28,-.08,0,.08,.16,1 if kind!="vent" else .5)
    elif kind in {"rock","crystal"}:
        rings=8; n=len(v)+1; v.append((0,0,1.2 if kind=="crystal" else .7))
        for i in range(rings):
            a=2*math.pi*i/rings; rr=(.45 if kind=="crystal" else .6)*( .8+rng.random()*.3); v.append((math.cos(a)*rr,math.sin(a)*rr,0))
        for i in range(rings): f.append((n,n+1+i,n+1+((i+1)%rings)))
    elif kind=="branch":
        _cyl(v,f,0,0,0,.12,1.3,10); _cyl(v,f,.15,0,.8,.07,.8,8)
    else:
        _box(v,f,-.5,-.5,0,1,1,.2)
    lines=[f"# axm procedural mesh {kind}",f"o {kind}"]
    lines += [f"v {x:.6f} {y:.6f} {z:.6f}" for x,y,z in v]
    lines += ["f "+" ".join(map(str,face)) for face in f]
    return "\n".join(lines)+"\n"

def vector_svg(kind:str,seed:int=0)->str:
    kind=kind.strip().casefold()
    if kind not in VECTOR_PARTS: raise KeyError(f"unknown vector part: {kind}")
    rng=random.Random(seed); strokes=[]
    if "border" in kind or "frame" in kind:
        strokes=['<rect x="8" y="8" width="240" height="240" rx="16"/>','<rect x="22" y="22" width="212" height="212" rx="12"/>']
    elif "trim" in kind or "strip" in kind or kind in {"road-marking","hazard-trim","riveted-strip"}:
        for i in range(8): strokes.append(f'<path d="M {i*32} 20 L {i*32+18} 236"/>')
        if kind=="riveted-strip":
            for i in range(10): strokes.append(f'<circle cx="{16+i*24}" cy="128" r="5"/>')
    elif kind in {"planet-icon","target-ring","grid-overlay"}:
        strokes=['<circle cx="128" cy="128" r="90"/>','<circle cx="128" cy="128" r="55"/>','<circle cx="128" cy="128" r="18"/>']
        if kind=="planet-icon": strokes.append('<ellipse cx="128" cy="128" rx="118" ry="34" transform="rotate(-18 128 128)"/>')
    elif kind in {"leaf-vine","crystal-cluster","mountain-icon","wing-emblem","shield-emblem"}:
        strokes=['<path d="M 28 210 Q 90 80 128 128 Q 166 176 228 46"/>','<path d="M 60 172 L 96 96 L 128 150 L 164 72 L 204 172"/>']
    else:
        pts=[]
        for i in range(12):
            a=2*math.pi*i/12; r=92 if i%2==0 else 46+rng.randint(-8,8); pts.append(f"{128+math.cos(a)*r:.1f},{128+math.sin(a)*r:.1f}")
        strokes=[f'<polygon points="{" ".join(pts)}"/>','<circle cx="128" cy="128" r="24"/>']
    return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="none" stroke="currentColor" stroke-width="6" stroke-linejoin="round">'+''.join(strokes)+'</svg>\n'
