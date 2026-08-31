from __future__ import annotations

import math
import random

from .visual_base import DECALS, FIXTURES, OBJ_FIXTURES, _hash2


def _svg_header(size: int = 512) -> str:
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" width="{size}" height="{size}">'


def _gear_points(cx: float, cy: float, outer: float, inner: float, teeth: int) -> str:
    pts = []
    for i in range(teeth * 2):
        a = math.tau * i / (teeth * 2) - math.pi / 2
        r = outer if i % 2 == 0 else inner
        pts.append(f"{cx + math.cos(a) * r:.1f},{cy + math.sin(a) * r:.1f}")
    return " ".join(pts)


def _fixture_svg(kind: str, seed: int = 0) -> str:
    kind = str(kind).strip().casefold()
    if kind not in FIXTURES:
        raise KeyError(f"unknown fixture kind: {kind}")
    rng = random.Random(seed)
    dark, mid, light, accent = "#151A20", "#46515D", "#D7E0E8", "#58E0FF"
    p = [_svg_header(), '<rect width="512" height="512" fill="none"/>']
    if kind == "button":
        p += [f'<circle cx="256" cy="256" r="150" fill="{dark}" stroke="{mid}" stroke-width="30"/>', f'<circle cx="256" cy="240" r="112" fill="{accent}"/>']
    elif kind == "knob":
        p += [f'<circle cx="256" cy="256" r="170" fill="{dark}" stroke="{mid}" stroke-width="24"/>', f'<circle cx="256" cy="256" r="125" fill="{mid}"/>', f'<path d="M256 256 L256 135" stroke="{light}" stroke-width="22" stroke-linecap="round"/>']
    elif kind == "slider":
        cx = 160 + rng.randrange(0, 190)
        p += [f'<rect x="80" y="228" width="352" height="56" rx="28" fill="{dark}"/>', f'<circle cx="{cx}" cy="256" r="72" fill="{light}" stroke="{mid}" stroke-width="18"/>']
    elif kind == "toggle":
        p += [f'<rect x="100" y="180" width="312" height="152" rx="76" fill="{dark}" stroke="{mid}" stroke-width="14"/>', f'<circle cx="330" cy="256" r="58" fill="{accent}"/>']
    elif kind in {"panel", "screen", "window"}:
        fill = "#071018" if kind == "screen" else "#75D9FF" if kind == "window" else dark
        p += [f'<rect x="72" y="88" width="368" height="336" rx="28" fill="{fill}" stroke="{mid}" stroke-width="22"/>']
        for x, y in ((96,112),(416,112),(96,400),(416,400)):
            p.append(f'<circle cx="{x}" cy="{y}" r="12" fill="{light}"/>')
    elif kind in {"vent", "grille"}:
        p += [f'<rect x="76" y="104" width="360" height="304" rx="24" fill="{dark}" stroke="{mid}" stroke-width="18"/>']
        if kind == "vent":
            for y in range(148, 386, 38):
                p.append(f'<rect x="118" y="{y}" width="276" height="14" rx="7" fill="{light}"/>')
        else:
            for x in range(116, 410, 42): p.append(f'<rect x="{x}" y="138" width="12" height="236" fill="{light}"/>')
            for y in range(148, 380, 42): p.append(f'<rect x="108" y="{y}" width="296" height="12" fill="{light}"/>')
    elif kind == "handle":
        p += [f'<path d="M132 326 V212 Q132 150 194 150 H318 Q380 150 380 212 V326" fill="none" stroke="{mid}" stroke-width="52" stroke-linecap="round"/>']
    elif kind == "hinge":
        p += [f'<rect x="84" y="136" width="344" height="240" rx="18" fill="{dark}" stroke="{mid}" stroke-width="20"/>', f'<rect x="236" y="114" width="40" height="284" rx="20" fill="{light}"/>']
    elif kind == "bracket":
        p += [f'<path d="M120 114 H210 V302 H392 V398 H120 Z" fill="{mid}" stroke="{dark}" stroke-width="20"/>']
    elif kind in {"bolt", "rivet", "screw", "washer"}:
        if kind == "washer":
            p += [f'<circle cx="256" cy="256" r="160" fill="{mid}"/>', '<circle cx="256" cy="256" r="82" fill="white"/>']
        else:
            points = _gear_points(256, 256, 145, 145, 3 if kind == "bolt" else 16)
            p += [f'<polygon points="{points}" fill="{mid}" stroke="{dark}" stroke-width="18"/>']
            if kind == "screw": p += [f'<path d="M172 256 H340" stroke="{dark}" stroke-width="24"/>']
            if kind == "rivet": p += ['<ellipse cx="215" cy="205" rx="68" ry="34" fill="#FFFFFF" opacity=".24"/>']
    elif kind == "gear":
        p += [f'<polygon points="{_gear_points(256,256,178,142,16)}" fill="{mid}" stroke="{dark}" stroke-width="14"/>', '<circle cx="256" cy="256" r="72" fill="white"/>']
    elif kind == "pipe":
        p += [f'<rect x="100" y="205" width="312" height="102" rx="51" fill="{mid}" stroke="{dark}" stroke-width="18"/>']
    elif kind == "elbow":
        p += [f'<path d="M140 380 V254 Q140 136 258 136 H382" fill="none" stroke="{mid}" stroke-width="92" stroke-linecap="round"/>']
    elif kind == "light":
        p += [f'<circle cx="256" cy="256" r="172" fill="{dark}" stroke="{mid}" stroke-width="20"/>', f'<circle cx="256" cy="256" r="126" fill="{accent}"/>', '<circle cx="256" cy="256" r="72" fill="#FFFFFF" opacity=".5"/>']
    elif kind == "gauge":
        p += [f'<circle cx="256" cy="256" r="176" fill="{dark}" stroke="{mid}" stroke-width="22"/>']
        for i in range(11):
            a = math.radians(210 + i * 24)
            p.append(f'<line x1="{256+math.cos(a)*118:.1f}" y1="{256+math.sin(a)*118:.1f}" x2="{256+math.cos(a)*150:.1f}" y2="{256+math.sin(a)*150:.1f}" stroke="{light}" stroke-width="8"/>')
        p += [f'<line x1="256" y1="256" x2="350" y2="180" stroke="{accent}" stroke-width="14"/>']
    elif kind == "badge":
        p += [f'<polygon points="256,60 388,126 430,268 350,404 162,404 82,268 124,126" fill="{mid}" stroke="{dark}" stroke-width="20"/>', f'<circle cx="256" cy="248" r="90" fill="{accent}"/>']
    elif kind == "port":
        p += [f'<rect x="96" y="138" width="320" height="236" rx="42" fill="{dark}" stroke="{mid}" stroke-width="20"/>']
        for x in (166,226,286,346): p.append(f'<circle cx="{x}" cy="256" r="20" fill="{light}"/>')
    p.append("</svg>")
    return "".join(p)


def _decal_svg(kind: str, seed: int = 0) -> str:
    kind = str(kind).strip().casefold()
    if kind not in DECALS:
        raise KeyError(f"unknown decal kind: {kind}")
    rng = random.Random(seed)
    p = [_svg_header(), '<g fill="none" stroke="#FFFFFF" stroke-width="28" stroke-linecap="round" stroke-linejoin="round">']
    if kind == "arrow": p += ['<path d="M92 256 H390 M286 152 L402 256 L286 360"/>']
    elif kind == "chevron": p += ['<path d="M120 140 L250 256 L120 372 M262 140 L392 256 L262 372"/>']
    elif kind == "warning": p += ['<path d="M256 76 L446 414 H66 Z"/>', '<path d="M256 176 V298"/>', '<circle cx="256" cy="354" r="10" fill="#FFFFFF" stroke="none"/>']
    elif kind == "hazard-stripes":
        p = [_svg_header(), '<defs><clipPath id="c"><rect x="48" y="128" width="416" height="256" rx="12"/></clipPath></defs>', '<rect x="48" y="128" width="416" height="256" fill="#FFD21F"/>', '<g clip-path="url(#c)" stroke="#151515" stroke-width="72">']
        for x in range(-100, 700, 110): p.append(f'<line x1="{x}" y1="420" x2="{x+220}" y2="92"/>')
        p += ['</g>', '</svg>']; return "".join(p)
    elif kind in {"target", "crosshair"}:
        p += ['<circle cx="256" cy="256" r="150"/>', '<circle cx="256" cy="256" r="82"/>']
        p += ['<circle cx="256" cy="256" r="24" fill="#FFFFFF" stroke="none"/>' if kind == "target" else '<path d="M256 48 V160 M256 352 V464 M48 256 H160 M352 256 H464"/>']
    elif kind == "panel-lines": p += ['<path d="M76 104 H286 L338 156 H438 V408 H224 L176 360 H76 Z"/>']
    elif kind == "serial-label":
        p = [_svg_header(), '<rect x="58" y="152" width="396" height="208" rx="14" fill="none" stroke="#FFFFFF" stroke-width="14"/>', '<g fill="#FFFFFF">']
        for i in range(18):
            h = 48 + int(_hash2(seed, i, 0) * 78); p.append(f'<rect x="{86+i*19}" y="{314-h}" width="{6+i%3*3}" height="{h}"/>')
        p += ['</g>', '</svg>']; return "".join(p)
    elif kind == "circuit-trace": p += ['<path d="M74 120 H172 V210 H252 V302 H346 V392 H438"/>', '<path d="M112 392 H188 V330 H286 V206 H394 V120"/>']
    elif kind == "scratch":
        for i in range(8):
            y = 112 + i * 38 + rng.randrange(-12,13); p.append(f'<path d="M{92+rng.randrange(0,70)} {y} C220 {y-30} 300 {y+24} {420-rng.randrange(0,70)} {y-8}" stroke-width="{8+rng.randrange(0,12)}"/>')
    elif kind == "crack": p += ['<path d="M262 78 L238 172 L282 230 L236 292 L268 354 L230 438"/>', '<path d="M282 230 L362 194 M236 292 L154 330 M268 354 L350 402" stroke-width="16"/>']
    elif kind == "drip":
        p = [_svg_header(), '<path d="M80 126 H432 V252 C388 232 372 292 338 266 C298 234 282 354 246 296 C210 240 188 328 154 272 C130 234 110 252 80 246 Z" fill="#FFFFFF"/>', '</svg>']; return "".join(p)
    p += ['</g>', '</svg>']
    return "".join(p)


def _append_box(vertices: list[tuple[float,float,float]], faces: list[tuple[int,...]], cx: float, cy: float, cz: float, sx: float, sy: float, sz: float) -> None:
    start = len(vertices) + 1
    for dx,dy,dz in ((-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)):
        vertices.append((cx+dx*sx/2, cy+dy*sy/2, cz+dz*sz/2))
    faces += [tuple(start+i for i in f) for f in ((0,1,2,3),(4,7,6,5),(0,4,5,1),(1,5,6,2),(2,6,7,3),(4,0,3,7))]


def _append_cylinder(vertices: list[tuple[float,float,float]], faces: list[tuple[int,...]], radius: float, height: float, segments: int = 16, z: float = 0.0) -> None:
    start = len(vertices) + 1
    for zz in (z-height/2, z+height/2):
        for i in range(segments):
            a = math.tau*i/segments; vertices.append((math.cos(a)*radius, math.sin(a)*radius, zz))
    for i in range(segments):
        j=(i+1)%segments; faces.append((start+i,start+j,start+segments+j,start+segments+i))
    faces.append(tuple(start+i for i in range(segments)))
    faces.append(tuple(start+segments+i for i in reversed(range(segments))))


def _fixture_obj(kind: str, seed: int = 0) -> str:
    kind = str(kind).strip().casefold()
    if kind not in OBJ_FIXTURES:
        raise KeyError(f"fixture {kind!r} has no OBJ generator")
    v: list[tuple[float,float,float]]=[]; f: list[tuple[int,...]]=[]
    if kind in {"button","knob","bolt","rivet","screw","washer","light","port"}:
        _append_cylinder(v,f,1.0,0.45 if kind not in {"knob","port"} else .8,6 if kind=="bolt" else 20)
        if kind=="washer": _append_cylinder(v,f,.46,.52,20)
    elif kind in {"pipe","elbow"}:
        _append_cylinder(v,f,.42,2.4,16)
        if kind=="elbow": _append_box(v,f,.75,0,.75,1.5,.72,.72)
    elif kind=="gear":
        _append_cylinder(v,f,.8,.32,20)
        for i in range(12):
            a=math.tau*i/12; _append_box(v,f,math.cos(a)*.92,math.sin(a)*.92,0,.34,.34,.32)
    elif kind=="handle":
        _append_box(v,f,0,0,.65,1.8,.35,.35); _append_box(v,f,-.75,0,0,.3,.35,1.3); _append_box(v,f,.75,0,0,.3,.35,1.3)
    elif kind=="hinge":
        _append_box(v,f,-.62,0,0,1.0,1.8,.18); _append_box(v,f,.62,0,0,1.0,1.8,.18); _append_cylinder(v,f,.16,2.0,12)
    elif kind=="bracket":
        _append_box(v,f,-.55,0,0,.35,1.8,.35); _append_box(v,f,.2,0,-.72,1.85,.35,.35)
    else:
        _append_box(v,f,0,0,0,2.0,1.5,.28)
    lines=[f"# AXM procedural fixture: {kind} seed={int(seed)}", f"o axm_{kind.replace('-','_')}"]
    lines += [f"v {x:.6f} {y:.6f} {z:.6f}" for x,y,z in v]
    lines += ["f "+" ".join(map(str,face)) for face in f]
    return "\n".join(lines)+"\n"
