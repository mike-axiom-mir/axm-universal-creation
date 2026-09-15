"""One JSON authoring interface for people, scripts and AI orchestration.

UC includes the registry and realizers; no fabric checkout/service is required.
Paths are relative to the request file. Existing output files are never replaced.
"""
import argparse
import json
from pathlib import Path
from axm_stickers import Registry, instance
from axm_stickers.assembly import save_assembly, library_bundle, import_library
from .sticker_adapter import register_glb, register_studio
from .sticker_assembly import export_assembly
from .procedural_3d import build_glb


def execute(registry,request,root):
    request=dict(request); operation=request.pop('operation',None); root=Path(root)
    if operation=='create_3d':
        spec=request.pop('spec')
        body=build_glb(spec)['body']
        return register_glb(registry,body,editable_source=json.dumps(spec,indent=2,allow_nan=False).encode(),**request)
    if operation=='save_glb':
        file=root/request.pop('file')
        with file.open('rb') as f: body=f.read(32*1024*1024+1)
        if len(body)>32*1024*1024: raise ValueError('source GLB exceeds 32 MiB')
        source=request.pop('editable_source_file',None); editable=None
        if source is not None:
            with (root/source).open('rb') as f: editable=f.read(32*1024*1024+1)
            if len(editable)>32*1024*1024: raise ValueError('editable source exceeds 32 MiB')
        return register_glb(registry,body,editable_source=editable,**request)
    if operation=='save_2d':
        project=request.pop('project')
        return register_studio(registry,project,root,**request)
    if operation=='save_assembly': return save_assembly(registry,**request)
    if operation=='instance':
        d=registry.get(request.pop('sticker_id'),request.pop('version'))
        return instance(d,**request)
    if operation in ('export_assembly','export_library'):
        output=root/request.pop('output')
        if output.exists(): raise FileExistsError(output)
        result=export_assembly(registry,**request) if operation=='export_assembly' else library_bundle(registry,**request)
        body=result['body'] if operation=='export_assembly' else json.dumps(result,indent=2,allow_nan=False).encode()
        with output.open('xb') as f: f.write(body)
        return result['receipt'] if operation=='export_assembly' else {'output':str(output),'definitions':len(result['definitions'])}
    if operation=='import_library': return import_library(registry,**request)
    if operation=='search': return registry.search(**request)
    raise ValueError('unknown creation operation')


def main(argv=None):
    parser=argparse.ArgumentParser(description='UC sticker creation: the same saved requests for humans and machines')
    parser.add_argument('database',type=Path); parser.add_argument('request',type=Path)
    args=parser.parse_args(argv)
    with args.request.open('rb') as f: body=f.read(48*1024*1024+1)
    if len(body)>48*1024*1024: parser.error('request exceeds 48 MiB')
    with Registry(args.database) as registry: result=execute(registry,json.loads(body),args.request.parent)
    print(json.dumps(result,indent=2,allow_nan=False))


if __name__=='__main__': main()
