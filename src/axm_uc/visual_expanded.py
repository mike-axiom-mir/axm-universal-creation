from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Sequence

from .visual_base import SCHEMA, MAX_SIZE, DEFAULT_SIZE, png_bytes
from .visual_surface import SURFACES, surface_rows
from .visual_pigment import PIGMENTS, SMART_MASKS, pigment_maps
from .visual_sprite import SPRITES, sprite_sheet_bytes
from .visual_parts import MESH_PARTS, VECTOR_PARTS, mesh_obj, vector_svg

EXPANSION_SCHEMA = "axm.procedural-visual-assets.expansion/v0.2"


def _ensure(path: Path, replace: bool, directory: bool = False) -> None:
    if path.exists() and not replace:
        if directory and path.is_dir() and not any(path.iterdir()):
            return
        raise FileExistsError(f"target already exists: {path}; pass replace=True to overwrite")
    if directory:
        path.mkdir(parents=True, exist_ok=True)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def expansion_catalog() -> dict[str, Any]:
    return {
        "schema": EXPANSION_SCHEMA,
        "truth_status": "EXECUTABLE_GENERATOR_CATALOG",
        "deterministic": True,
        "outputs": {
            "surface": {"formats": ["png"], "kinds": list(SURFACES)},
            "pigment": {"formats": ["png", "json"], "kinds": list(PIGMENTS), "smart_masks": list(SMART_MASKS)},
            "sprite": {"formats": ["png", "json"], "kinds": list(SPRITES)},
            "mesh": {"formats": ["obj"], "kinds": list(MESH_PARTS)},
            "vector-part": {"formats": ["svg"], "kinds": list(VECTOR_PARTS)},
            "expansion-kit": {"formats": ["directory", "json-manifest"], "profiles": ["starter", "full"]},
        },
    }


def generate_surface(path: Path | str, kind: str, *, seed: int = 0, size: int = DEFAULT_SIZE, scale: float = 1.0, colors: Sequence[str] | None = None, replace: bool = False) -> dict[str, Any]:
    target=Path(path); kind=kind.strip().casefold(); size=int(size)
    if kind not in SURFACES: raise KeyError(f"unknown surface kind: {kind}")
    if not 1 <= size <= MAX_SIZE: raise ValueError(f"size must be 1..{MAX_SIZE}")
    _ensure(target,replace)
    target.write_bytes(png_bytes(size,size,surface_rows(kind,size,size,seed=seed,scale=scale,colors=colors),"RGB"))
    return {"schema":EXPANSION_SCHEMA,"truth_status":"OBSERVED_GENERATED_ASSET","category":"surface","kind":kind,"seed":int(seed),"size":size,"scale":float(scale),"path":str(target),"sha256":_sha(target),"bytes":target.stat().st_size}


def generate_pigment(path: Path | str, kind: str, *, seed: int=0, size: int=DEFAULT_SIZE, scale: float=1.0, age: float=.5, damage: float=.35, moisture: float=.25, replace: bool=False) -> dict[str, Any]:
    target=Path(path); kind=kind.strip().casefold(); size=int(size)
    if kind not in PIGMENTS: raise KeyError(f"unknown pigment kind: {kind}")
    if not 1 <= size <= MAX_SIZE: raise ValueError(f"size must be 1..{MAX_SIZE}")
    if target.exists() and any(target.iterdir()) and not replace: raise FileExistsError(f"target pigment directory is not empty: {target}")
    target.mkdir(parents=True,exist_ok=True)
    maps,meta=pigment_maps(kind,size,seed,scale,age=age,damage=damage,moisture=moisture)
    files=[]
    for channel,(mode,rows) in maps.items():
        out=target/f"{channel}.png"; out.write_bytes(png_bytes(size,size,rows,mode)); files.append({"channel":channel,"path":out.name,"sha256":_sha(out),"bytes":out.stat().st_size})
    manifest={"schema":EXPANSION_SCHEMA,"category":"pigment","kind":kind,"seed":int(seed),"size":size,"scale":float(scale),**meta,"channels":{r["channel"]:r["path"] for r in files}}
    mp=target/"pigment.json"; mp.write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    files.append({"channel":"manifest","path":mp.name,"sha256":_sha(mp),"bytes":mp.stat().st_size})
    return {"schema":EXPANSION_SCHEMA,"truth_status":"OBSERVED_GENERATED_SMART_PIGMENT_PACK","category":"pigment","kind":kind,"seed":int(seed),"path":str(target),"smart_masks":list(SMART_MASKS),"files":files}


def generate_sprite(path: Path | str, kind: str, *, seed: int=0, frame_size: int=32, frames: int=4, columns: int|None=None, replace: bool=False) -> dict[str, Any]:
    target=Path(path); kind=kind.strip().casefold(); _ensure(target,replace)
    data,meta=sprite_sheet_bytes(kind,seed=seed,frame_size=frame_size,frames=frames,columns=columns); target.write_bytes(data)
    metadata=target.with_suffix(target.suffix+".json")
    metadata.write_text(json.dumps({"schema":EXPANSION_SCHEMA,"category":"sprite","seed":int(seed),**meta},indent=2,sort_keys=True)+"\n",encoding="utf-8")
    return {"schema":EXPANSION_SCHEMA,"truth_status":"OBSERVED_GENERATED_SPRITE_SHEET","category":"sprite","kind":kind,"seed":int(seed),"path":str(target),"sha256":_sha(target),"metadata":str(metadata),"metadata_sha256":_sha(metadata),**meta}


def generate_mesh(path: Path | str, kind: str, *, seed: int=0, replace: bool=False) -> dict[str, Any]:
    target=Path(path); kind=kind.strip().casefold(); _ensure(target,replace); target.write_text(mesh_obj(kind,seed),encoding="utf-8")
    return {"schema":EXPANSION_SCHEMA,"truth_status":"OBSERVED_GENERATED_MESH","category":"mesh","kind":kind,"seed":int(seed),"format":"obj","path":str(target),"sha256":_sha(target),"bytes":target.stat().st_size}


def generate_vector_part(path: Path | str, kind: str, *, seed: int=0, replace: bool=False) -> dict[str, Any]:
    target=Path(path); kind=kind.strip().casefold(); _ensure(target,replace); target.write_text(vector_svg(kind,seed),encoding="utf-8")
    return {"schema":EXPANSION_SCHEMA,"truth_status":"OBSERVED_GENERATED_VECTOR_PART","category":"vector-part","kind":kind,"seed":int(seed),"format":"svg","path":str(target),"sha256":_sha(target),"bytes":target.stat().st_size}


def generate_expanded_asset(*, category: str, kind: str, path: Path|str, seed: int=0, size: int=DEFAULT_SIZE, scale: float=1.0, colors: Sequence[str]|None=None, age: float=.5, damage: float=.35, moisture: float=.25, frame_size: int=32, frames: int=4, columns: int|None=None, replace: bool=False) -> dict[str, Any]:
    category=category.strip().casefold()
    if category=="surface": return generate_surface(path,kind,seed=seed,size=size,scale=scale,colors=colors,replace=replace)
    if category=="pigment": return generate_pigment(path,kind,seed=seed,size=size,scale=scale,age=age,damage=damage,moisture=moisture,replace=replace)
    if category=="sprite": return generate_sprite(path,kind,seed=seed,frame_size=frame_size,frames=frames,columns=columns,replace=replace)
    if category=="mesh": return generate_mesh(path,kind,seed=seed,replace=replace)
    if category=="vector-part": return generate_vector_part(path,kind,seed=seed,replace=replace)
    raise KeyError(f"unknown expanded visual asset category: {category}")


def generate_expansion_kit(path: Path|str, *, profile: str="starter", seed: int=0, size: int=48, replace: bool=False) -> dict[str, Any]:
    target=Path(path); profile=profile.strip().casefold()
    if profile not in {"starter","full"}: raise ValueError("expansion kit profile must be starter or full")
    if target.exists() and any(target.iterdir()) and not replace: raise FileExistsError(f"target kit directory is not empty: {target}")
    target.mkdir(parents=True,exist_ok=True)
    chosen={
        "surface": SURFACES if profile=="full" else ("bark","moss","asphalt","rusted-steel","spaceship-hull","cyber-grid","alien-alloy","biotech-membrane"),
        "pigment": PIGMENTS if profile=="full" else ("painted-metal","military-paint","weathered-wall-paint","neon-coat","biotech-pigment"),
        "sprite": SPRITES if profile=="full" else ("bot","tank","drone","tree","rock","building","effect-burst"),
        "mesh": MESH_PARTS if profile=="full" else ("wall","stair","column","door","pipe","crate","rock","armor-panel","turret-base","greeble"),
        "vector-part": VECTOR_PARTS if profile=="full" else ("border","panel-trim","hazard-trim","fantasy-carving","circuit-strip","shield-emblem","energy-glyph"),
    }
    receipts=[]
    for i,k in enumerate(chosen["surface"]): receipts.append(generate_surface(target/"surfaces"/f"{k}.png",k,seed=seed+i*13,size=size,replace=True))
    for i,k in enumerate(chosen["pigment"]): receipts.append(generate_pigment(target/"pigments"/k,k,seed=seed+1000+i*17,size=size,replace=True))
    for i,k in enumerate(chosen["sprite"]): receipts.append(generate_sprite(target/"sprites"/f"{k}.png",k,seed=seed+2000+i,frame_size=min(48,size),frames=4,replace=True))
    for i,k in enumerate(chosen["mesh"]): receipts.append(generate_mesh(target/"meshes"/f"{k}.obj",k,seed=seed+3000+i,replace=True))
    for i,k in enumerate(chosen["vector-part"]): receipts.append(generate_vector_part(target/"vector-parts"/f"{k}.svg",k,seed=seed+4000+i,replace=True))
    files=[{"path":p.relative_to(target).as_posix(),"sha256":_sha(p),"bytes":p.stat().st_size} for p in sorted(x for x in target.rglob("*") if x.is_file())]
    manifest={"schema":EXPANSION_SCHEMA,"truth_status":"OBSERVED_GENERATED_VISUAL_EXPANSION_KIT","profile":profile,"seed":int(seed),"size":int(size),"catalog":expansion_catalog()["outputs"],"receipt_count":len(receipts),"files":files}
    mp=target/"visual-expansion.manifest.json"; mp.write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    return {"schema":EXPANSION_SCHEMA,"truth_status":manifest["truth_status"],"profile":profile,"seed":int(seed),"path":str(target),"receipt_count":len(receipts),"file_count":len(files)+1,"manifest":str(mp),"manifest_sha256":_sha(mp)}
