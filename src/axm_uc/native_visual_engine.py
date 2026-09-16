from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any


SCENE_SCHEMA = "axm.native-visual-scene/v0.1"
RECEIPT_SCHEMA = "axm.native-visual-receipt/v0.1"
ENGINE_ID = "axm-native-webgl2"
MAX_OBJECTS = 1024
MAX_LIGHTS = 8
SUPPORTED_PRIMITIVES = {"box", "sphere", "cylinder", "plane"}
SUPPORTED_ANIMATIONS = {"none", "spin", "bob", "orbit"}


def _finite(value: Any, field: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be numeric") from exc
    if not math.isfinite(number):
        raise ValueError(f"{field} must be finite")
    return number


def _bounded(value: Any, field: str, low: float, high: float) -> float:
    number = _finite(value, field)
    if not low <= number <= high:
        raise ValueError(f"{field} must be between {low} and {high}")
    return number


def _vec(value: Any, field: str, length: int, default: tuple[float, ...]) -> list[float]:
    raw = default if value is None else value
    if not isinstance(raw, (list, tuple)) or len(raw) != length:
        raise ValueError(f"{field} must contain exactly {length} numbers")
    return [_finite(item, f"{field}[{index}]") for index, item in enumerate(raw)]


def _color(value: Any, field: str, default: tuple[float, float, float, float]) -> list[float]:
    rgba = _vec(value, field, 4, default)
    for index, channel in enumerate(rgba):
        if not 0.0 <= channel <= 1.0:
            raise ValueError(f"{field}[{index}] must be between 0 and 1")
    return rgba


def _rgb(value: Any, field: str, default: tuple[float, float, float]) -> list[float]:
    raw = default if value is None else value
    if not isinstance(raw, (list, tuple)) or len(raw) not in {3, 4}:
        raise ValueError(f"{field} must contain 3 RGB or 4 RGBA numbers")
    rgb = [_finite(item, f"{field}[{index}]") for index, item in enumerate(raw[:3])]
    for index, channel in enumerate(rgb):
        if not 0.0 <= channel <= 1.0:
            raise ValueError(f"{field}[{index}] must be between 0 and 1")
    return rgb


def _identifier(value: Any, field: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{field} must be non-empty")
    if len(text) > 96:
        raise ValueError(f"{field} exceeds 96 characters")
    return text


def _material(raw: Any, field: str) -> dict[str, Any]:
    data = raw if isinstance(raw, dict) else {}
    return {
        "base_color": _color(data.get("base_color"), f"{field}.base_color", (0.48, 0.55, 0.62, 1.0)),
        "metallic": _bounded(data.get("metallic", 0.05), f"{field}.metallic", 0.0, 1.0),
        "roughness": _bounded(data.get("roughness", 0.48), f"{field}.roughness", 0.04, 1.0),
        "emissive": _rgb(data.get("emissive"), f"{field}.emissive", (0.0, 0.0, 0.0)),
        "emissive_strength": _bounded(data.get("emissive_strength", 0.0), f"{field}.emissive_strength", 0.0, 32.0),
    }


def _animation(raw: Any, field: str) -> dict[str, Any]:
    data = raw if isinstance(raw, dict) else {}
    kind = str(data.get("kind", "none")).strip().casefold()
    if kind not in SUPPORTED_ANIMATIONS:
        raise ValueError(f"{field}.kind must be one of {sorted(SUPPORTED_ANIMATIONS)}")
    return {
        "kind": kind,
        "speed": _finite(data.get("speed", 18.0 if kind == "spin" else 1.0), f"{field}.speed"),
        "amplitude": _bounded(data.get("amplitude", 0.2), f"{field}.amplitude", 0.0, 1000.0),
        "radius": _bounded(data.get("radius", 1.0), f"{field}.radius", 0.0, 10000.0),
    }


def compile_scene(raw: Any) -> dict[str, Any]:
    """Normalize and validate one deterministic native visual scene.

    This is deliberately a small, inspectable scene contract rather than a hidden
    editor state. The same values are suitable for adaptation into Blender or a
    game runtime later, while this module can render them immediately in WebGL2.
    """
    if not isinstance(raw, dict):
        raise TypeError("native visual scene must be an object")

    title = str(raw.get("title", "AXM Native Visual Scene")).strip() or "AXM Native Visual Scene"
    if len(title) > 160:
        raise ValueError("title exceeds 160 characters")

    camera_raw = raw.get("camera") if isinstance(raw.get("camera"), dict) else {}
    camera = {
        "position": _vec(camera_raw.get("position"), "camera.position", 3, (7.2, 5.0, 8.6)),
        "target": _vec(camera_raw.get("target"), "camera.target", 3, (0.0, 1.0, 0.0)),
        "fov_degrees": _bounded(camera_raw.get("fov_degrees", 44.0), "camera.fov_degrees", 15.0, 100.0),
        "near": _bounded(camera_raw.get("near", 0.05), "camera.near", 0.001, 100.0),
        "far": _bounded(camera_raw.get("far", 500.0), "camera.far", 1.0, 100000.0),
        "orbit_enabled": bool(camera_raw.get("orbit_enabled", True)),
    }
    if camera["near"] >= camera["far"]:
        raise ValueError("camera.near must be smaller than camera.far")

    lights_raw = raw.get("lights")
    if lights_raw is None:
        lights_raw = [
            {"id": "key", "kind": "directional", "direction": [-0.45, -0.8, -0.35], "color": [1.0, 0.88, 0.74, 1.0], "intensity": 2.4},
            {"id": "fill", "kind": "directional", "direction": [0.7, -0.35, 0.5], "color": [0.42, 0.65, 1.0, 1.0], "intensity": 1.25},
            {"id": "rim", "kind": "directional", "direction": [0.15, -0.15, -1.0], "color": [0.35, 0.95, 1.0, 1.0], "intensity": 1.45},
        ]
    if not isinstance(lights_raw, list) or len(lights_raw) > MAX_LIGHTS:
        raise ValueError(f"lights must be a list with at most {MAX_LIGHTS} entries")
    lights: list[dict[str, Any]] = []
    light_ids: set[str] = set()
    for index, entry in enumerate(lights_raw):
        if not isinstance(entry, dict):
            raise ValueError(f"lights[{index}] must be an object")
        light_id = _identifier(entry.get("id", f"light-{index}"), f"lights[{index}].id")
        if light_id in light_ids:
            raise ValueError(f"duplicate light id: {light_id}")
        light_ids.add(light_id)
        kind = str(entry.get("kind", "directional")).strip().casefold()
        if kind not in {"directional", "point"}:
            raise ValueError(f"lights[{index}].kind must be directional or point")
        lights.append({
            "id": light_id,
            "kind": kind,
            "direction": _vec(entry.get("direction"), f"lights[{index}].direction", 3, (-0.4, -0.7, -0.3)),
            "position": _vec(entry.get("position"), f"lights[{index}].position", 3, (4.0, 6.0, 4.0)),
            "color": _rgb(entry.get("color"), f"lights[{index}].color", (1.0, 1.0, 1.0)),
            "intensity": _bounded(entry.get("intensity", 1.0), f"lights[{index}].intensity", 0.0, 1000.0),
            "range": _bounded(entry.get("range", 25.0), f"lights[{index}].range", 0.01, 100000.0),
        })

    objects_raw = raw.get("objects", [])
    if not isinstance(objects_raw, list) or len(objects_raw) > MAX_OBJECTS:
        raise ValueError(f"objects must be a list with at most {MAX_OBJECTS} entries")
    objects: list[dict[str, Any]] = []
    object_ids: set[str] = set()
    for index, entry in enumerate(objects_raw):
        if not isinstance(entry, dict):
            raise ValueError(f"objects[{index}] must be an object")
        object_id = _identifier(entry.get("id"), f"objects[{index}].id")
        if object_id in object_ids:
            raise ValueError(f"duplicate object id: {object_id}")
        object_ids.add(object_id)
        primitive = str(entry.get("primitive", "box")).strip().casefold()
        if primitive not in SUPPORTED_PRIMITIVES:
            raise ValueError(f"objects[{index}].primitive must be one of {sorted(SUPPORTED_PRIMITIVES)}")
        scale = _vec(entry.get("scale"), f"objects[{index}].scale", 3, (1.0, 1.0, 1.0))
        if any(abs(value) < 1e-6 for value in scale):
            raise ValueError(f"objects[{index}].scale components must be non-zero")
        objects.append({
            "id": object_id,
            "primitive": primitive,
            "position": _vec(entry.get("position"), f"objects[{index}].position", 3, (0.0, 0.0, 0.0)),
            "rotation_degrees": _vec(entry.get("rotation_degrees"), f"objects[{index}].rotation_degrees", 3, (0.0, 0.0, 0.0)),
            "scale": scale,
            "material": _material(entry.get("material"), f"objects[{index}].material"),
            "animation": _animation(entry.get("animation"), f"objects[{index}].animation"),
            "visible": bool(entry.get("visible", True)),
        })

    scene = {
        "schema": SCENE_SCHEMA,
        "engine": ENGINE_ID,
        "title": title,
        "background": _color(raw.get("background"), "background", (0.015, 0.022, 0.035, 1.0)),
        "ambient": {
            "color": _rgb((raw.get("ambient") or {}).get("color") if isinstance(raw.get("ambient"), dict) else None, "ambient.color", (0.18, 0.22, 0.3)),
            "intensity": _bounded((raw.get("ambient") or {}).get("intensity", 0.42) if isinstance(raw.get("ambient"), dict) else 0.42, "ambient.intensity", 0.0, 10.0),
        },
        "camera": camera,
        "lights": lights,
        "objects": objects,
        "render": {
            "exposure": _bounded((raw.get("render") or {}).get("exposure", 1.0) if isinstance(raw.get("render"), dict) else 1.0, "render.exposure", 0.05, 16.0),
            "fog_density": _bounded((raw.get("render") or {}).get("fog_density", 0.012) if isinstance(raw.get("render"), dict) else 0.012, "render.fog_density", 0.0, 1.0),
            "grid": bool((raw.get("render") or {}).get("grid", True) if isinstance(raw.get("render"), dict) else True),
        },
        "truth": {
            "runtime": "browser-webgl2",
            "offline_after_bundle_creation": True,
            "external_javascript_dependencies": False,
            "final_asset_authoring_replacement": False,
            "purpose": "fast deterministic scene preview, coded visuals, camera/light/material iteration",
        },
    }
    scene["scene_sha256"] = scene_sha256(scene)
    return scene


def catalog_native_visual() -> dict[str, Any]:
    return {
        "schema": "axm.native-visual-catalog/v0.1",
        "truth_status": "EXECUTABLE_CODED_VISUAL_RUNTIME",
        "engine": ENGINE_ID,
        "scene_schema": SCENE_SCHEMA,
        "primitives": sorted(SUPPORTED_PRIMITIVES),
        "animations": sorted(SUPPORTED_ANIMATIONS),
        "lighting": ["ambient", "directional", "point"],
        "materials": ["base_color", "metallic", "roughness", "emissive"],
        "outputs": ["scene.json", "index.html", "receipt.json"],
        "bridge": {
            "target": "Blender bpy",
            "helper": "tools/blender/axm_blender_pro.py::apply_native_scene",
            "shared_state": ["camera", "transforms", "basic-materials", "lights", "world"],
            "pixel_parity_claimed": False,
        },
        "truth": {
            "bundle_is_self_contained": True,
            "external_javascript_dependencies": False,
            "live_pixels_require_webgl2_host_evidence": True,
            "replaces_blender_final_authoring": False,
        },
    }


def scene_sha256(scene: dict[str, Any]) -> str:
    payload = dict(scene)
    payload.pop("scene_sha256", None)
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def demo_scene() -> dict[str, Any]:
    return compile_scene({
        "title": "AXM Native Visual Engine — Forge Bay",
        "camera": {"position": [8.6, 5.2, 10.8], "target": [0.0, 1.4, 0.0], "fov_degrees": 42},
        "objects": [
            {"id": "floor", "primitive": "plane", "position": [0, 0, 0], "scale": [12, 1, 12], "material": {"base_color": [0.055, 0.065, 0.08, 1], "metallic": 0.65, "roughness": 0.58}},
            {"id": "core", "primitive": "cylinder", "position": [0, 1.5, 0], "scale": [1.7, 2.8, 1.7], "material": {"base_color": [0.12, 0.16, 0.2, 1], "metallic": 0.82, "roughness": 0.24}, "animation": {"kind": "spin", "speed": 9}},
            {"id": "energy", "primitive": "sphere", "position": [0, 2.1, 0], "scale": [0.72, 0.72, 0.72], "material": {"base_color": [0.08, 0.42, 0.66, 1], "metallic": 0.2, "roughness": 0.16, "emissive": [0.02, 0.7, 1.0, 1], "emissive_strength": 2.7}, "animation": {"kind": "bob", "speed": 1.4, "amplitude": 0.18}},
            {"id": "left-pylon", "primitive": "box", "position": [-3.0, 1.0, -0.4], "rotation_degrees": [0, -18, 0], "scale": [0.75, 2.0, 0.9], "material": {"base_color": [0.18, 0.2, 0.23, 1], "metallic": 0.72, "roughness": 0.32, "emissive": [0.0, 0.32, 0.9, 1], "emissive_strength": 0.55}},
            {"id": "right-pylon", "primitive": "box", "position": [3.0, 1.0, -0.4], "rotation_degrees": [0, 18, 0], "scale": [0.75, 2.0, 0.9], "material": {"base_color": [0.18, 0.2, 0.23, 1], "metallic": 0.72, "roughness": 0.32, "emissive": [0.95, 0.24, 0.05, 1], "emissive_strength": 0.42}},
        ],
    })


_HTML_TEMPLATE = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/><title>__TITLE__</title><style>
html,body{margin:0;width:100%;height:100%;overflow:hidden;background:#05070a;color:#e8eef7;font-family:system-ui,sans-serif}canvas{display:block;width:100%;height:100%;touch-action:none}#hud{position:fixed;left:14px;top:14px;padding:10px 12px;border:1px solid #ffffff24;border-radius:10px;background:#07101ac9;backdrop-filter:blur(10px);font-size:12px;line-height:1.45;max-width:360px;pointer-events:none}#hud b{font-size:13px}#truth{opacity:.68;margin-top:4px}.ok{color:#8df4c7}</style></head><body>
<canvas id="view"></canvas><div id="hud"><b>__TITLE__</b><div id="stats"></div><div id="truth" class="ok">AXM native WebGL2 preview · local bundle · no external JS</div></div><script id="axm-scene" type="application/json">__SCENE_JSON__</script><script>
'use strict';const scene=JSON.parse(document.getElementById('axm-scene').textContent);const canvas=document.getElementById('view');const gl=canvas.getContext('webgl2',{antialias:true,alpha:scene.background[3]<1});if(!gl){document.getElementById('truth').textContent='WebGL2 unavailable on this device/browser';throw new Error('WebGL2 unavailable');}
const VERT=`#version 300 es
precision highp float;layout(location=0) in vec3 aPos;layout(location=1) in vec3 aNormal;uniform mat4 uModel,uView,uProj;out vec3 vWorld;out vec3 vNormal;void main(){vec4 w=uModel*vec4(aPos,1.0);vWorld=w.xyz;vNormal=normalize(transpose(inverse(mat3(uModel)))*aNormal);gl_Position=uProj*uView*w;}`;
const FRAG=`#version 300 es
precision highp float;in vec3 vWorld;in vec3 vNormal;out vec4 outColor;uniform vec3 uCamera,uAmbientColor,uEmissive;uniform float uAmbientIntensity,uMetallic,uRoughness,uEmissiveStrength,uExposure,uFogDensity;uniform vec4 uBase;uniform int uLightCount;uniform vec4 uLightPosType[8];uniform vec4 uLightColorIntensity[8];uniform float uLightRange[8];void main(){vec3 n=normalize(vNormal),v=normalize(uCamera-vWorld);vec3 base=uBase.rgb;vec3 c=base*uAmbientColor*uAmbientIntensity;float shininess=mix(96.0,5.0,uRoughness);vec3 f0=mix(vec3(.04),base,uMetallic);for(int i=0;i<8;i++){if(i>=uLightCount)break;vec3 l;float attenuation=1.0;if(uLightPosType[i].w>.5){vec3 d=uLightPosType[i].xyz-vWorld;float dist=length(d);l=d/max(dist,.0001);float r=max(uLightRange[i],.001);attenuation=1.0/(1.0+(dist*dist)/(r*r));}else{l=normalize(-uLightPosType[i].xyz);}float ndl=max(dot(n,l),0.0);vec3 h=normalize(l+v);float spec=pow(max(dot(n,h),0.0),shininess)*(1.0-uRoughness*.6);vec3 lc=uLightColorIntensity[i].rgb*uLightColorIntensity[i].a*attenuation;c+=(base*(1.0-uMetallic)*ndl+f0*spec)*lc;}c+=uEmissive*uEmissiveStrength;float dist=length(uCamera-vWorld);float fog=1.0-exp(-uFogDensity*dist);vec3 fogColor=vec3(.018,.026,.042);c=mix(c,fogColor,clamp(fog,0.0,.72));c*=uExposure;c=c/(vec3(1.0)+c);c=pow(max(c,vec3(0.0)),vec3(1.0/2.2));outColor=vec4(c,uBase.a);}`;
function shader(type,src){const s=gl.createShader(type);gl.shaderSource(s,src);gl.compileShader(s);if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))throw new Error(gl.getShaderInfoLog(s));return s}const program=gl.createProgram();gl.attachShader(program,shader(gl.VERTEX_SHADER,VERT));gl.attachShader(program,shader(gl.FRAGMENT_SHADER,FRAG));gl.linkProgram(program);if(!gl.getProgramParameter(program,gl.LINK_STATUS))throw new Error(gl.getProgramInfoLog(program));gl.useProgram(program);const U={};['uModel','uView','uProj','uCamera','uAmbientColor','uAmbientIntensity','uEmissive','uMetallic','uRoughness','uEmissiveStrength','uExposure','uFogDensity','uBase','uLightCount','uLightPosType[0]','uLightColorIntensity[0]','uLightRange[0]'].forEach(n=>U[n]=gl.getUniformLocation(program,n));
const M={I:()=>new Float32Array([1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1]),mul:(a,b)=>{const o=new Float32Array(16);for(let c=0;c<4;c++)for(let r=0;r<4;r++)o[c*4+r]=a[0*4+r]*b[c*4+0]+a[1*4+r]*b[c*4+1]+a[2*4+r]*b[c*4+2]+a[3*4+r]*b[c*4+3];return o},T:(x,y,z)=>{const m=M.I();m[12]=x;m[13]=y;m[14]=z;return m},S:(x,y,z)=>new Float32Array([x,0,0,0,0,y,0,0,0,0,z,0,0,0,0,1]),Rx:a=>{let c=Math.cos(a),s=Math.sin(a);return new Float32Array([1,0,0,0,0,c,s,0,0,-s,c,0,0,0,0,1])},Ry:a=>{let c=Math.cos(a),s=Math.sin(a);return new Float32Array([c,0,-s,0,0,1,0,0,s,0,c,0,0,0,0,1])},Rz:a=>{let c=Math.cos(a),s=Math.sin(a);return new Float32Array([c,s,0,0,-s,c,0,0,0,0,1,0,0,0,0,1])},persp:(fov,aspect,n,f)=>{let t=1/Math.tan(fov/2),nf=1/(n-f);return new Float32Array([t/aspect,0,0,0,0,t,0,0,0,0,(f+n)*nf,-1,0,0,2*f*n*nf,0])},look:(eye,target,up=[0,1,0])=>{let z=norm(sub(eye,target)),x=norm(cross(up,z)),y=cross(z,x);return new Float32Array([x[0],y[0],z[0],0,x[1],y[1],z[1],0,x[2],y[2],z[2],0,-dot(x,eye),-dot(y,eye),-dot(z,eye),1])}};const sub=(a,b)=>[a[0]-b[0],a[1]-b[1],a[2]-b[2]],dot=(a,b)=>a[0]*b[0]+a[1]*b[1]+a[2]*b[2],cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]],norm=a=>{let l=Math.hypot(...a)||1;return a.map(v=>v/l)};
function mesh(vertices,indices){const vao=gl.createVertexArray();gl.bindVertexArray(vao);const vbo=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,vbo);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(vertices),gl.STATIC_DRAW);gl.enableVertexAttribArray(0);gl.vertexAttribPointer(0,3,gl.FLOAT,false,24,0);gl.enableVertexAttribArray(1);gl.vertexAttribPointer(1,3,gl.FLOAT,false,24,12);const ibo=gl.createBuffer();gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,ibo);gl.bufferData(gl.ELEMENT_ARRAY_BUFFER,new Uint32Array(indices),gl.STATIC_DRAW);return{vao,count:indices.length}}
function box(){const f=[[1,0,0],[-1,0,0],[0,-1,0],[0,1,0],[0,0,1],[0,0,-1]];let v=[],i=[];const faces=[[[1,-1,-1],[1,-1,1],[1,1,1],[1,1,-1]],[[-1,-1,1],[-1,-1,-1],[-1,1,-1],[-1,1,1]],[[-1,-1,1],[1,-1,1],[1,-1,-1],[-1,-1,-1]],[[-1,1,-1],[1,1,-1],[1,1,1],[-1,1,1]],[[1,-1,1],[-1,-1,1],[-1,1,1],[1,1,1]],[[-1,-1,-1],[1,-1,-1],[1,1,-1],[-1,1,-1]]];faces.forEach((q,k)=>{let n=f[k];let b=v.length/6;q.forEach(p=>v.push(...p.map(x=>x*.5),...n));i.push(b,b+1,b+2,b,b+2,b+3)});return mesh(v,i)}function plane(){return mesh([-.5,0,-.5,0,1,0,.5,0,-.5,0,1,0,.5,0,.5,0,1,0,-.5,0,.5,0,1,0],[0,1,2,0,2,3])}function sphere(seg=28,rings=18){let v=[],i=[];for(let y=0;y<=rings;y++){let a=y*Math.PI/rings,sy=Math.cos(a),sr=Math.sin(a);for(let x=0;x<=seg;x++){let b=x*2*Math.PI/seg,n=[sr*Math.cos(b),sy,sr*Math.sin(b)];v.push(n[0]*.5,n[1]*.5,n[2]*.5,...n)}}for(let y=0;y<rings;y++)for(let x=0;x<seg;x++){let a=y*(seg+1)+x,b=a+seg+1;i.push(a,b,a+1,b,b+1,a+1)}return mesh(v,i)}function cylinder(seg=32){let v=[],i=[];for(let y=0;y<2;y++)for(let x=0;x<=seg;x++){let a=x*2*Math.PI/seg,n=[Math.cos(a),0,Math.sin(a)];v.push(n[0]*.5,(y-.5),n[2]*.5,...n)}for(let x=0;x<seg;x++){let a=x,b=x+seg+1;i.push(a,b,a+1,b,b+1,a+1)};for(let side of [-1,1]){let center=v.length/6;v.push(0,side*.5,0,0,side,0);let start=v.length/6;for(let x=0;x<=seg;x++){let a=x*2*Math.PI/seg;v.push(Math.cos(a)*.5,side*.5,Math.sin(a)*.5,0,side,0)}for(let x=0;x<seg;x++)side>0?i.push(center,start+x+1,start+x):i.push(center,start+x,start+x+1)}return mesh(v,i)}const meshes={box:box(),plane:plane(),sphere:sphere(),cylinder:cylinder()};
let cam={pos:[...scene.camera.position],target:[...scene.camera.target]};let d=sub(cam.pos,cam.target),radius=Math.hypot(...d),yaw=Math.atan2(d[0],d[2]),pitch=Math.asin(d[1]/radius),drag=false,last=[0,0];function updateCam(){cam.pos=[cam.target[0]+radius*Math.cos(pitch)*Math.sin(yaw),cam.target[1]+radius*Math.sin(pitch),cam.target[2]+radius*Math.cos(pitch)*Math.cos(yaw)]}if(scene.camera.orbit_enabled){canvas.addEventListener('pointerdown',e=>{drag=true;last=[e.clientX,e.clientY];canvas.setPointerCapture(e.pointerId)});canvas.addEventListener('pointerup',()=>drag=false);canvas.addEventListener('pointermove',e=>{if(!drag)return;yaw-=(e.clientX-last[0])*.006;pitch=Math.max(-1.45,Math.min(1.45,pitch-(e.clientY-last[1])*.006));last=[e.clientX,e.clientY];updateCam()});canvas.addEventListener('wheel',e=>{e.preventDefault();radius=Math.max(.5,Math.min(250,radius*Math.exp(e.deltaY*.001)));updateCam()},{passive:false})}
function resize(){let dpr=Math.min(devicePixelRatio||1,2),w=Math.max(1,Math.floor(innerWidth*dpr)),h=Math.max(1,Math.floor(innerHeight*dpr));if(canvas.width!==w||canvas.height!==h){canvas.width=w;canvas.height=h;gl.viewport(0,0,w,h)}}function modelFor(o,t){let p=[...o.position],rot=o.rotation_degrees.map(x=>x*Math.PI/180),a=o.animation;if(a.kind==='spin')rot[1]+=t*a.speed*Math.PI/180;if(a.kind==='bob')p[1]+=Math.sin(t*a.speed*Math.PI*2)*a.amplitude;if(a.kind==='orbit'){p[0]+=Math.sin(t*a.speed)*a.radius;p[2]+=Math.cos(t*a.speed)*a.radius}return M.mul(M.T(...p),M.mul(M.Rz(rot[2]),M.mul(M.Ry(rot[1]),M.mul(M.Rx(rot[0]),M.S(...o.scale)))))}function frame(ms){resize();let t=ms*.001;gl.enable(gl.DEPTH_TEST);gl.enable(gl.CULL_FACE);gl.clearColor(...scene.background);gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);gl.useProgram(program);let proj=M.persp(scene.camera.fov_degrees*Math.PI/180,canvas.width/canvas.height,scene.camera.near,scene.camera.far),view=M.look(cam.pos,cam.target);gl.uniformMatrix4fv(U.uView,false,view);gl.uniformMatrix4fv(U.uProj,false,proj);gl.uniform3fv(U.uCamera,cam.pos);gl.uniform3fv(U.uAmbientColor,scene.ambient.color);gl.uniform1f(U.uAmbientIntensity,scene.ambient.intensity);gl.uniform1f(U.uExposure,scene.render.exposure);gl.uniform1f(U.uFogDensity,scene.render.fog_density);let lp=new Float32Array(32),lc=new Float32Array(32),lr=new Float32Array(8);scene.lights.forEach((l,k)=>{let q=k*4,v=l.kind==='point'?l.position:l.direction;lp.set([v[0],v[1],v[2],l.kind==='point'?1:0],q);lc.set([l.color[0],l.color[1],l.color[2],l.intensity],q);lr[k]=l.range});gl.uniform1i(U.uLightCount,scene.lights.length);gl.uniform4fv(U['uLightPosType[0]'],lp);gl.uniform4fv(U['uLightColorIntensity[0]'],lc);gl.uniform1fv(U['uLightRange[0]'],lr);for(const o of scene.objects){if(!o.visible)continue;let m=meshes[o.primitive],mat=o.material;gl.uniformMatrix4fv(U.uModel,false,modelFor(o,t));gl.uniform4fv(U.uBase,mat.base_color);gl.uniform1f(U.uMetallic,mat.metallic);gl.uniform1f(U.uRoughness,mat.roughness);gl.uniform3fv(U.uEmissive,mat.emissive);gl.uniform1f(U.uEmissiveStrength,mat.emissive_strength);gl.bindVertexArray(m.vao);gl.drawElements(gl.TRIANGLES,m.count,gl.UNSIGNED_INT,0)}requestAnimationFrame(frame)}document.getElementById('stats').textContent=`${scene.objects.length} objects · ${scene.lights.length} lights · drag orbit · wheel zoom`;requestAnimationFrame(frame);
</script></body></html>'''


def render_html(scene: dict[str, Any]) -> str:
    normalized = compile_scene(scene)
    encoded = json.dumps(normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=False).replace("</", "<\\/")
    title = normalized["title"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return _HTML_TEMPLATE.replace("__TITLE__", title).replace("__SCENE_JSON__", encoded)


def write_visual_bundle(output_dir: str | Path, raw_scene: Any, *, replace: bool = False) -> dict[str, Any]:
    output = Path(output_dir).expanduser().resolve()
    if output.exists() and any(output.iterdir()) and not replace:
        raise FileExistsError(f"native visual output is not empty: {output}")
    output.mkdir(parents=True, exist_ok=True)
    scene = compile_scene(raw_scene)
    scene_path, html_path, receipt_path = output / "scene.json", output / "index.html", output / "receipt.json"
    scene_bytes = (json.dumps(scene, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
    html_bytes = render_html(scene).encode("utf-8")
    scene_path.write_bytes(scene_bytes)
    html_path.write_bytes(html_bytes)
    receipt = {
        "schema": RECEIPT_SCHEMA,
        "status": "NATIVE_VISUAL_BUNDLE_COMPILED",
        "engine": ENGINE_ID,
        "scene_sha256": scene["scene_sha256"],
        "files": {"scene.json": hashlib.sha256(scene_bytes).hexdigest(), "index.html": hashlib.sha256(html_bytes).hexdigest()},
        "counts": {"objects": len(scene["objects"]), "lights": len(scene["lights"])},
        "truth": {"webgl_execution_tested_here": False, "bundle_is_self_contained": True, "requires_webgl2_browser": True, "replaces_blender_final_authoring": False},
    }
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compile a self-contained AXM native WebGL2 visual scene")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--scene", type=Path, help="JSON scene input")
    source.add_argument("--demo", action="store_true", help="Compile the built-in forge-bay demo")
    parser.add_argument("--output", type=Path, required=True, help="Output bundle directory")
    parser.add_argument("--replace", action="store_true", help="Replace AXM native visual bundle files in a non-empty output directory")
    args = parser.parse_args(argv)
    scene = demo_scene() if args.demo else json.loads(args.scene.read_text(encoding="utf-8"))
    receipt = write_visual_bundle(args.output, scene, replace=args.replace)
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
