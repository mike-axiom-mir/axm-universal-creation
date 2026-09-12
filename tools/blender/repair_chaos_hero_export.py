"""Re-export a retained character rig without re-running its modelling passes.

This only repairs triangulation/export. It does not pretend that editing a
modelling recipe changes already-built geometry. Parent provenance is retained.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
from types import SimpleNamespace

import bpy
from axm_hero_motion import clean_triangles, export
from axm_oops_character import reset_pose


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();source=args.source.resolve();out=args.output.resolve()
    if out.exists():raise SystemExit('Choose a new output directory')
    checkpoint=source/'rig-checkpoint.blend'
    upstream=json.loads((source/'character-manifest.json').read_text())
    parent_hash=hashlib.sha256(checkpoint.read_bytes()).hexdigest()
    bpy.ops.wm.open_mainfile(filepath=str(checkpoint))
    arm=bpy.data.objects.get('AXM_Hero_Rig');mesh=bpy.data.objects.get('AXM_Chaos_Hero')
    if arm is None or mesh is None:raise ValueError('Expected retained hero rig and skin')
    if set(arm.data.bones.keys())!={b['name'] for b in upstream['bones']}:
        raise ValueError('Checkpoint skeleton does not match parent manifest')
    arm.animation_data.action=None;reset_pose(arm);bpy.context.view_layer.update()
    clean_triangles(mesh)
    out.mkdir(parents=True)
    shutil.copytree(source/'textures',out/'textures')
    hero=SimpleNamespace(bones={b['name']:(None,None,b['parent']) for b in upstream['bones']})
    export(hero,arm,mesh,upstream['animations'],out)
    report=json.loads((out/'character-manifest.json').read_text())
    report['export_repair']={
        'checkpoint_sha256':parent_hash,
        'parent_geometry_source_hashes':upstream['source_hashes'],
        'repair_script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'operation':'Cross-product triangle cleanup and fresh full/LOD1 exports; modelling and animation retained.'}
    (out/'character-manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    print('REEXPORT_COMPLETE',out,flush=True)


if __name__=='__main__':main()
