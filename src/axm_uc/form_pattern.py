from __future__ import annotations

import hashlib
import json
import math
from copy import deepcopy
from pathlib import Path
from typing import Any

from .creator_retention import SOURCE_SCHEMA, publish_retained_glb


SCHEMA = "axm.form-pattern/v0.1"
MAX_PARTS = 128
MAX_PROFILE_POINTS = 128
MAX_PATH_POINTS = 128
MAX_SEGMENTS = 64
_PATTERNS = {"profile-extrude", "loft", "revolve", "tube"}
_DEFAULT_MATERIAL = {"color": "#8A8A8AFF", "metallic": 0.0, "roughness": 0.6}


class FormPatternError(RuntimeError):
    def __init__(self, status: str, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.status = status
        self.details = {"status": status, **(details or {})}


def _hold(status: str, message: str, **details: Any) -> None:
    raise FormPatternError(status, message, details)


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()
    except (TypeError, ValueError) as exc:
        raise FormPatternError("HOLD_FORM_PATTERN_INVALID", "form pattern must be finite JSON data") from exc


def _number(value: Any, label: str, low: float, high: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        _hold("HOLD_FORM_PATTERN_INVALID", f"{label} must be a finite number")
    result = float(value)
    if not math.isfinite(result) or not low <= result <= high:
        _hold("HOLD_FORM_PATTERN_INVALID", f"{label} must be from {low} through {high}")
    return result


def _vec(value: Any, label: str, width: int = 3, low: float = -100000.0, high: float = 100000.0) -> list[float]:
    if not isinstance(value, list) or len(value) != width:
        _hold("HOLD_FORM_PATTERN_INVALID", f"{label} must contain exactly {width} numbers")
    return [_number(v, f"{label}[{i}]", low, high) for i, v in enumerate(value)]


def _name(value: Any, label: str, maximum: int = 120) -> str:
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > maximum:
        _hold("HOLD_FORM_PATTERN_INVALID", f"{label} must be non-empty text up to {maximum} characters")
    return value.strip()


def _material(raw: Any, label: str) -> dict[str, Any]:
    if raw is None:
        raw = _DEFAULT_MATERIAL
    if not isinstance(raw, dict):
        _hold("HOLD_FORM_PATTERN_INVALID", f"{label} must be an object")
    extra = set(raw) - {"color", "metallic", "roughness", "emissive", "unlit"}
    if extra or not {"color", "metallic", "roughness"} <= set(raw):
        _hold("HOLD_FORM_PATTERN_INVALID", f"{label} fields do not match material grammar", unexpected=sorted(extra))
    color = raw["color"]
    if not isinstance(color, str) or len(color) not in {7, 9} or not color.startswith("#"):
        _hold("HOLD_FORM_PATTERN_INVALID", f"{label}.color must be #RRGGBB or #RRGGBBAA")
    try:
        int(color[1:], 16)
    except ValueError:
        _hold("HOLD_FORM_PATTERN_INVALID", f"{label}.color must be hexadecimal")
    result = {
        "color": color.upper(),
        "metallic": _number(raw["metallic"], f"{label}.metallic", 0, 1),
        "roughness": _number(raw["roughness"], f"{label}.roughness", 0, 1),
    }
    if "emissive" in raw:
        emissive = raw["emissive"]
        if not isinstance(emissive, str) or len(emissive) not in {7, 9} or not emissive.startswith("#"):
            _hold("HOLD_FORM_PATTERN_INVALID", f"{label}.emissive must be #RRGGBB or #RRGGBBAA")
        try:
            int(emissive[1:], 16)
        except ValueError:
            _hold("HOLD_FORM_PATTERN_INVALID", f"{label}.emissive must be hexadecimal")
        result["emissive"] = emissive.upper()
    if "unlit" in raw:
        if type(raw["unlit"]) is not bool:
            _hold("HOLD_FORM_PATTERN_INVALID", f"{label}.unlit must be boolean")
        if raw["unlit"]:
            result["unlit"] = True
    return result


def _segments(value: Any, label: str, default: int = 16) -> int:
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, int) or not 3 <= value <= MAX_SEGMENTS:
        _hold("HOLD_FORM_PATTERN_INVALID", f"{label} must be an integer from 3 through {MAX_SEGMENTS}")
    return value


def _faces_normals(positions: list[tuple[float, float, float]], faces: list[tuple[int, ...]]) -> tuple[list[list[float]], list[int]]:
    accum = [[0.0, 0.0, 0.0] for _ in positions]
    indices: list[int] = []
    for face in faces:
        if len(face) < 3:
            continue
        a = positions[face[0]]
        for j in range(1, len(face) - 1):
            b, c = positions[face[j]], positions[face[j + 1]]
            ab = (b[0]-a[0], b[1]-a[1], b[2]-a[2])
            ac = (c[0]-a[0], c[1]-a[1], c[2]-a[2])
            n = (
                ab[1]*ac[2]-ab[2]*ac[1],
                ab[2]*ac[0]-ab[0]*ac[2],
                ab[0]*ac[1]-ab[1]*ac[0],
            )
            length = math.sqrt(sum(v*v for v in n))
            if length <= 1e-12:
                continue
            n = tuple(v/length for v in n)
            tri = (face[0], face[j], face[j+1])
            indices.extend(tri)
            for idx in tri:
                for axis in range(3):
                    accum[idx][axis] += n[axis]
    if not indices:
        _hold("HOLD_FORM_PATTERN_DEGENERATE", "generated form contains no nondegenerate triangles")
    normals = []
    for row in accum:
        length = math.sqrt(sum(v*v for v in row))
        normals.append([0.0, 0.0, 1.0] if length <= 1e-12 else [v/length for v in row])
    return normals, indices


def _rotate_xyz(p: tuple[float,float,float], r: list[float]) -> tuple[float,float,float]:
    x,y,z = p
    cx,sx = math.cos(r[0]), math.sin(r[0])
    cy,sy = math.cos(r[1]), math.sin(r[1])
    cz,sz = math.cos(r[2]), math.sin(r[2])
    y,z = y*cx-z*sx, y*sx+z*cx
    x,z = x*cy+z*sy, -x*sy+z*cy
    x,y = x*cz-y*sz, x*sz+y*cz
    return (x,y,z)


def _transform(positions: list[tuple[float,float,float]], raw: dict[str,Any]) -> list[tuple[float,float,float]]:
    scale = raw.get("scale", [1,1,1])
    if isinstance(scale, (int,float)) and not isinstance(scale,bool):
        s = _number(scale, "part.scale", 0.001, 10000)
        scale = [s,s,s]
    else:
        scale = _vec(scale, "part.scale", 3, 0.001, 10000)
    rotation = _vec(raw.get("rotation", [0,0,0]), "part.rotation", 3, -100000, 100000)
    translation = _vec(raw.get("translation", [0,0,0]), "part.translation")
    result=[]
    for p in positions:
        q=(p[0]*scale[0], p[1]*scale[1], p[2]*scale[2])
        q=_rotate_xyz(q, rotation)
        result.append((q[0]+translation[0],q[1]+translation[1],q[2]+translation[2]))
    return result


def _profile_extrude(part: dict[str,Any]) -> tuple[list[tuple[float,float,float]], list[tuple[int,...]]]:
    outline = part.get("outline")
    if not isinstance(outline, list) or not 3 <= len(outline) <= MAX_PROFILE_POINTS:
        _hold("HOLD_FORM_PATTERN_INVALID", f"profile-extrude outline requires 3..{MAX_PROFILE_POINTS} points")
    pts=[_vec(p, "outline point", 2, -10000, 10000) for p in outline]
    depth=_number(part.get("depth"), "profile-extrude.depth", 0.001, 10000)
    positions=[(x,-depth/2,z) for x,z in pts]+[(x,depth/2,z) for x,z in pts]
    n=len(pts)
    faces=[tuple(reversed(range(n))), tuple(range(n,2*n))]
    for i in range(n):
        j=(i+1)%n
        faces.append((i,j,j+n,i+n))
    return positions,faces


def _loft(part: dict[str,Any]) -> tuple[list[tuple[float,float,float]], list[tuple[int,...]]]:
    sections=part.get("sections")
    if not isinstance(sections,list) or not 2 <= len(sections) <= MAX_PROFILE_POINTS:
        _hold("HOLD_FORM_PATTERN_INVALID", "loft requires 2..128 sections")
    seg=_segments(part.get("segments"),"loft.segments",20)
    positions=[]
    for i,s in enumerate(sections):
        if not isinstance(s,dict) or set(s)-{"at","radius","offset","twist"} or not {"at","radius"}<=set(s):
            _hold("HOLD_FORM_PATTERN_INVALID", f"loft.sections[{i}] fields are invalid")
        at=_number(s["at"],f"sections[{i}].at",-10000,10000)
        radius=_vec(s["radius"],f"sections[{i}].radius",2,0.001,10000)
        offset=_vec(s.get("offset",[0,0]),f"sections[{i}].offset",2,-10000,10000)
        twist=_number(s.get("twist",0),f"sections[{i}].twist",-100000,100000)
        for k in range(seg):
            a=2*math.pi*k/seg+twist
            positions.append((offset[0]+radius[0]*math.cos(a), offset[1]+radius[1]*math.sin(a), at))
    faces=[]
    for s in range(len(sections)-1):
        a=s*seg;b=(s+1)*seg
        for k in range(seg):
            j=(k+1)%seg
            faces.append((a+k,a+j,b+j,b+k))
    faces.append(tuple(reversed(range(seg))))
    last=(len(sections)-1)*seg
    faces.append(tuple(last+i for i in range(seg)))
    return positions,faces


def _revolve(part: dict[str,Any]) -> tuple[list[tuple[float,float,float]], list[tuple[int,...]]]:
    profile=part.get("profile")
    if not isinstance(profile,list) or not 2 <= len(profile) <= MAX_PROFILE_POINTS:
        _hold("HOLD_FORM_PATTERN_INVALID", "revolve profile requires 2..128 [radius,z] points")
    pts=[_vec(p,"revolve.profile point",2,-10000,10000) for p in profile]
    if any(p[0] < 0 for p in pts):
        _hold("HOLD_FORM_PATTERN_INVALID","revolve radii must be nonnegative")
    seg=_segments(part.get("segments"),"revolve.segments",24)
    positions=[]
    for radius,z in pts:
        for k in range(seg):
            a=2*math.pi*k/seg
            positions.append((radius*math.cos(a),radius*math.sin(a),z))
    faces=[]
    for s in range(len(pts)-1):
        a=s*seg;b=(s+1)*seg
        for k in range(seg):
            j=(k+1)%seg
            faces.append((a+k,a+j,b+j,b+k))
    if pts[0][0] > 1e-9: faces.append(tuple(reversed(range(seg))))
    last=(len(pts)-1)*seg
    if pts[-1][0] > 1e-9: faces.append(tuple(last+i for i in range(seg)))
    return positions,faces


def _unit(v: tuple[float,float,float]) -> tuple[float,float,float]:
    length=math.sqrt(sum(x*x for x in v))
    if length <= 1e-12:
        _hold("HOLD_FORM_PATTERN_DEGENERATE","tube path contains coincident-only tangent")
    return tuple(x/length for x in v)


def _cross(a,b): return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])


def _tube(part: dict[str,Any]) -> tuple[list[tuple[float,float,float]], list[tuple[int,...]]]:
    path=part.get("path")
    if not isinstance(path,list) or not 2 <= len(path) <= MAX_PATH_POINTS:
        _hold("HOLD_FORM_PATTERN_INVALID","tube path requires 2..128 points")
    points=[tuple(_vec(p,"tube.path point")) for p in path]
    seg=_segments(part.get("segments"),"tube.segments",12)
    raw_radius=part.get("radius",0.1)
    if isinstance(raw_radius,list):
        if len(raw_radius)!=len(points): _hold("HOLD_FORM_PATTERN_INVALID","tube radius list must match path points")
        radii=[_number(v,"tube.radius",0.001,10000) for v in raw_radius]
    else:
        radius=_number(raw_radius,"tube.radius",0.001,10000);radii=[radius]*len(points)
    rings=[]
    for i,p in enumerate(points):
        a=points[max(0,i-1)];b=points[min(len(points)-1,i+1)]
        tangent=_unit((b[0]-a[0],b[1]-a[1],b[2]-a[2]))
        helper=(0.0,0.0,1.0) if abs(tangent[2])<0.9 else (0.0,1.0,0.0)
        side=_unit(_cross(tangent,helper));up=_unit(_cross(side,tangent))
        ring=[]
        for k in range(seg):
            ang=2*math.pi*k/seg
            ring.append((p[0]+radii[i]*(side[0]*math.cos(ang)+up[0]*math.sin(ang)),
                         p[1]+radii[i]*(side[1]*math.cos(ang)+up[1]*math.sin(ang)),
                         p[2]+radii[i]*(side[2]*math.cos(ang)+up[2]*math.sin(ang))))
        rings.append(ring)
    positions=[v for ring in rings for v in ring]
    faces=[]
    for i in range(len(rings)-1):
        a=i*seg;b=(i+1)*seg
        for k in range(seg):
            j=(k+1)%seg
            faces.append((a+k,a+j,b+j,b+k))
    faces.append(tuple(reversed(range(seg))))
    last=(len(rings)-1)*seg
    faces.append(tuple(last+i for i in range(seg)))
    return positions,faces


_GENERATORS={
    "profile-extrude":_profile_extrude,
    "loft":_loft,
    "revolve":_revolve,
    "tube":_tube,
}


def form_pattern_summary() -> dict[str,Any]:
    return {
        "schema":SCHEMA,
        "truth_status":"LIVE_GENERIC_SURFACE_PATTERN_COMPILER",
        "patterns":sorted(_PATTERNS),
        "supports_rotation":True,
        "supports_nonuniform_scale":True,
        "retains_source_structure":True,
        "output_schema":"axm.surface-3d/v0.1",
        "truth_boundary":"Generic deterministic surface construction; not sculpting intelligence, retopology, rigging, animation, collision, or aesthetic acceptance.",
    }


def compile_form_pattern(raw: Any) -> dict[str,Any]:
    if not isinstance(raw,dict) or raw.get("schema")!=SCHEMA:
        _hold("HOLD_FORM_PATTERN_INVALID",f"form recipe must use schema {SCHEMA}")
    extra=set(raw)-{"schema","name","parts","metadata"}
    if extra:
        _hold("HOLD_FORM_PATTERN_INVALID","form recipe contains unsupported fields",unexpected=sorted(extra))
    name=_name(raw.get("name"),"recipe.name")
    parts=raw.get("parts")
    if not isinstance(parts,list) or not 1 <= len(parts) <= MAX_PARTS:
        _hold("HOLD_FORM_PATTERN_INVALID",f"recipe.parts must contain 1..{MAX_PARTS} parts")
    ids=set(); groups=[]; index=[]
    for i,part in enumerate(parts):
        if not isinstance(part,dict):
            _hold("HOLD_FORM_PATTERN_INVALID",f"parts[{i}] must be an object")
        allowed={"id","role","pattern","material","translation","rotation","scale","outline","depth","sections","segments","profile","path","radius","metadata"}
        unexpected=set(part)-allowed
        if unexpected:
            _hold("HOLD_FORM_PATTERN_INVALID",f"parts[{i}] contains unsupported fields",unexpected=sorted(unexpected))
        pid=_name(part.get("id"),f"parts[{i}].id",80)
        if pid in ids:_hold("HOLD_FORM_PATTERN_INVALID","part ids must be unique",duplicate=pid)
        ids.add(pid)
        role=_name(part.get("role",pid),f"parts[{i}].role",80)
        pattern=str(part.get("pattern","")).strip().casefold()
        if pattern not in _PATTERNS:
            _hold("HOLD_FORM_PATTERN_UNSUPPORTED_PATTERN","unknown form pattern",pattern=pattern,supported=sorted(_PATTERNS))
        positions,faces=_GENERATORS[pattern](part)
        positions=_transform(positions,part)
        normals,indices=_faces_normals(positions,faces)
        material=_material(part.get("material"),f"parts[{i}].material")
        groups.append({
            "id":pid,
            "positions":[list(v) for v in positions],
            "normals":normals,
            "indices":indices,
            "material":material,
        })
        index.append({
            "id":pid,"role":role,"pattern":pattern,
            "vertices":len(positions),"triangles":len(indices)//3,
            "recipe_fragment_sha256":hashlib.sha256(_canonical(part)).hexdigest(),
            "metadata":deepcopy(part.get("metadata",{})),
        })
    specification={"schema":"axm.surface-3d/v0.1","name":name,"primitives":groups}
    return {
        "schema":SCHEMA,
        "truth_status":"COMPILED_GENERIC_SURFACE_PATTERN",
        "recipe_sha256":hashlib.sha256(_canonical(raw)).hexdigest(),
        "parts_index":index,
        "part_count":len(index),
        "vertex_count":sum(p["vertices"] for p in index),
        "triangle_count":sum(p["triangles"] for p in index),
        "specification":specification,
        "metadata":deepcopy(raw.get("metadata",{})),
    }


def publish_form_pattern(target: str|Path, recipe: Any, *, replace: bool=False) -> dict[str,Any]:
    compiled=compile_form_pattern(recipe)
    source={
        "schema":SOURCE_SCHEMA,
        "kind":"form-pattern",
        "source_authority":True,
        "realization_is_secondary":True,
        "recipe":deepcopy(recipe),
        "recipe_sha256":compiled["recipe_sha256"],
        "parts_index":deepcopy(compiled["parts_index"]),
        "compiled_specification":deepcopy(compiled["specification"]),
        "capability":"generic surface patterns: profile-extrude, loft, revolve, tube",
        "automatic_canon_admission":False,
    }
    result=publish_retained_glb(target,compiled["specification"],source,replace=replace)
    result["form_pattern"]={k:v for k,v in compiled.items() if k!="specification"}
    return result
