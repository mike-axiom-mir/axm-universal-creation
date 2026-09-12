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
    if not script.is_file():raise FileNotFoundError('This execution hand requires a complete Universal Creation source checkout')
    target.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='axm-rts-polish-',dir=target.parent) as temp:
        stage=Path(temp)/'asset';log=Path(temp)/'build.log'
        command=[runtime,str(script),'--output',str(stage),'--font',str(font),'--resolution',str(resolution),'--samples',str(samples)]
        with log.open('w') as stream:
            result=subprocess.run(command,stdout=stream,stderr=subprocess.STDOUT,timeout=1800,check=False)
        if result.returncode:
            raise RuntimeError('Blender workshop failed; destination was not published. '+log.read_text(errors='replace')[-1800:])
        report_path=stage/'verification.json'
        if not report_path.is_file():raise RuntimeError('Blender returned without a verification report')
        report=json.loads(report_path.read_text())
        for name in ['improvised-workshop.glb','improvised-workshop-lod1.glb','workshop-editable.blend','workshop-hero.png','workshop-rear.png','workshop-detail.png']:
            path=stage/name;entry=report['artifacts'][name]
            if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=entry['sha256']:
                raise RuntimeError(f'Artifact evidence does not match: {name}')
        shutil.copyfile(log,stage/'build.log')
        if target.exists():raise FileExistsError(target)
        stage.rename(target)
    return {'type':'RTS_WORKSHOP_POLISH_RESULT','path':str(target),'verification':report,
            'scope':'Reference-led authored asset; fresh-import Blender renders, not target RTS execution or user visual acceptance.'}
