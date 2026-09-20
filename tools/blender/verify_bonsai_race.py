from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import bpy
from mathutils import Vector


def sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):
            h.update(chunk)
    return h.hexdigest()


def fail(msg: str):
    raise SystemExit(msg)


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--directory',required=True)
    args=ap.parse_args()
    root=Path(args.directory)
    glb=root/'bonsai-race-v0.1.glb'
    manifest_path=root/'manifest.json'
    receipt_path=root/'receipt.json'
    for p in (glb,manifest_path,receipt_path):
        if not p.is_file():
            fail(f'missing {p}')
    receipt=json.loads(receipt_path.read_text())
    if sha256(glb)!=receipt['glb_sha256']:
        fail('GLB digest mismatch')

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(glb))
    meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']
    mats={m.name for o in meshes for m in o.data.materials if m}
    if len(meshes)<35:
        fail(f'expected substantial modular character, got {len(meshes)} meshes')
    if len(mats)<8:
        fail(f'expected material variety, got {len(mats)}')

    world=[]
    tri=0
    degenerate=0
    for o in meshes:
        me=o.data
        tri += sum(max(0,len(poly.vertices)-2) for poly in me.polygons)
        for poly in me.polygons:
            if len(poly.vertices)>=3:
                a=o.matrix_world @ me.vertices[poly.vertices[0]].co
                b=o.matrix_world @ me.vertices[poly.vertices[1]].co
                c=o.matrix_world @ me.vertices[poly.vertices[2]].co
                if (b-a).cross(c-a).length < 1e-9:
                    degenerate += 1
        for corner in o.bound_box:
            world.append(o.matrix_world @ Vector(corner))
    if not world:
        fail('no mesh bounds')
    mins=[min(v[i] for v in world) for i in range(3)]
    maxs=[max(v[i] for v in world) for i in range(3)]
    dims=[maxs[i]-mins[i] for i in range(3)]
    height=max(dims)
    if not (1.4 <= height <= 2.6):
        fail(f'character out of expected meter scale: dims={dims}')
    if tri<2000:
        fail(f'too little actual mesh structure: {tri} triangles')
    if degenerate>0:
        fail(f'degenerate polygon faces found: {degenerate}')

    required_tokens=['head','eye','trunk','leaf','staff','lantern','backpack','scarf','belt']
    names=' '.join(o.name.lower() for o in meshes)
    missing=[t for t in required_tokens if t not in names]
    if missing:
        fail(f'missing semantic parts after fresh GLB import: {missing}')

    result={
        'schema':'axm.uc.bonsai-race-verification/v0.1',
        'status':'STRUCTURE_VERIFIED_VISUAL_REVIEW_REQUIRED',
        'fresh_import':True,
        'glb_sha256':sha256(glb),
        'mesh_objects':len(meshes),
        'materials':sorted(mats),
        'triangles_estimate':tri,
        'degenerate_polygon_faces':degenerate,
        'bounds':{'min':mins,'max':maxs,'dimensions':dims},
        'semantic_parts_required':required_tokens,
        'semantic_parts_missing':missing,
        'gates':{
            'glb_parse_and_fresh_import':'TESTED_PASS',
            'meter_scale_bounds':'TESTED_PASS',
            'semantic_part_presence':'TESTED_PASS',
            'nondegenerate_polygon_faces':'TESTED_PASS',
            'visual_similarity':'NOT_TESTED_HUMAN_REVIEW_REQUIRED',
            'rig_and_animation':'NOT_PRESENT_V0_1',
            'clothing_compatibility':'NOT_TESTED',
            'target_engine_integration':'NOT_TESTED',
        }
    }
    (root/'verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    main()
