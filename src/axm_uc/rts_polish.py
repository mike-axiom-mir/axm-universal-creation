"""Explicit offline Blender execution hand for the reference-led workshop.

The caller supplies a Python environment containing bpy 4.3, numpy <2 and
Pillow. No downloads, credentials, service or mandatory core dependency.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


WORKSHOP_ARTIFACTS = (
    'improvised-workshop.glb',
    'improvised-workshop-lod1.glb',
    'improvised-workshop-tactical.glb',
    'improvised-workshop-rts.glb',
    'improvised-workshop-far.glb',
    'workshop-editable.blend',
    'workshop-hero.png',
    'workshop-rear.png',
    'workshop-detail.png',
    'lod-ladder-build.json',
    'glb-inspection.json',
    'game-readiness-gates.json',
)


def polish_workshop(root, destination, python, font, resolution=1100, samples=64):
    root=Path(root).resolve();target=Path(destination).resolve()
    if target.exists():raise FileExistsError(f'Refusing to overwrite {target}')
    if type(resolution) is not int or not 256<=resolution<=2048:raise ValueError('resolution must be 256..2048')
    if type(samples) is not int or not 8<=samples<=256:raise ValueError('samples must be 8..256')
    runtime=shutil.which(str(python))
    if runtime is None or not os.access(runtime,os.X_OK):raise ValueError('Supply an executable Python environment with bpy installed')
    font=Path(font).resolve()
    if not font.is_file():raise FileNotFoundError(font)
    script=root/'tools/blender/axm_rts_workshop.py'
    lod_script=root/'tools/blender/axm_rts_workshop_lods.py'
    verifier=root/'tools/blender/verify_rts_workshop.py'
    for required in (script,lod_script,verifier):
        if not required.is_file():raise FileNotFoundError('This execution hand requires a complete Universal Creation source checkout')
    target.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='axm-rts-polish-',dir=target.parent) as temp:
        stage=Path(temp)/'asset';log=Path(temp)/'build.log'
        commands=[
            [runtime,str(script),'--output',str(stage),'--font',str(font),'--resolution',str(resolution),'--samples',str(samples)],
            [runtime,str(lod_script),'--root',str(stage)],
            [runtime,str(verifier),str(stage)],
        ]
        with log.open('w') as stream:
            for command in commands:
                stream.write('$ '+' '.join(command)+'\n');stream.flush()
                result=subprocess.run(command,stdout=stream,stderr=subprocess.STDOUT,timeout=1800,check=False)
                if result.returncode:
                    raise RuntimeError('Blender workshop stage failed; destination was not published. '+log.read_text(errors='replace')[-1800:])
        report_path=stage/'verification.json'
        if not report_path.is_file():raise RuntimeError('Blender returned without a verification report')
        report=json.loads(report_path.read_text())
        digest=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
        report['source_sha256'][lod_script.name]=digest(lod_script)
        report['source_sha256'][verifier.name]=digest(verifier)
        report['lod_ladder']=json.loads((stage/'lod-ladder-build.json').read_text())
        report['game_readiness_gates']=json.loads((stage/'game-readiness-gates.json').read_text())
        for name in WORKSHOP_ARTIFACTS:
            path=stage/name
            if not path.is_file():raise RuntimeError(f'Missing workshop artifact: {name}')
            report['artifacts'][name]={'bytes':path.stat().st_size,'sha256':digest(path)}
        report['scope']='Reference-led authored asset with fresh-import Blender hero renders and a structurally verified runtime LOD ladder. LOD visual equivalence, target RTS acceptance and target-device performance remain separate evidence.'
        report_path.write_text(json.dumps(report,indent=2)+'\n')
        for name in WORKSHOP_ARTIFACTS:
            path=stage/name;entry=report['artifacts'][name]
            if digest(path)!=entry['sha256']:
                raise RuntimeError(f'Artifact evidence does not match: {name}')
        shutil.copyfile(log,stage/'build.log')
        if target.exists():raise FileExistsError(target)
        stage.rename(target)
    return {'type':'RTS_WORKSHOP_POLISH_RESULT','path':str(target),'verification':report,
            'scope':'Reference-led authored asset; fresh-import Blender hero renders plus independently verified runtime LOD structure, not target RTS execution or user visual acceptance.'}
