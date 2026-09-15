"""Saved rigid assemblies: reusable parts, explicit motion, portable closure.

All commands accept the same data regardless of human/machine authorship.
A saved group is a normal immutable sticker whose children have exact pins.
"""
import base64
import copy
import math
from .core import (SCHEMA, MAX_ASSETS, Registry, digest, encode, identifier,
                   instance, resolve, validate)
from .placement import identity, rigid, attachment_matrix

ASSEMBLY = 'axm.sticker.assembly-3d/v1'
LIBRARY = 'axm.sticker-library/v1'
MAX_PARTS = 4096
MAX_DEPTH = 16


def motion_samples(motion, target):
    if motion is None: return
    if not isinstance(motion,list) or not 2 <= len(motion) <= 240:
        raise ValueError('motion requires 2..240 samples')
    previous = -1
    for sample in motion:
        if not isinstance(sample,dict) or set(sample) != {'time','frame'}:
            raise ValueError('motion requires time and rigid frame')
        t = sample['time']
        if type(t) not in (int,float) or not math.isfinite(t) or not previous < t <= 3600:
            raise ValueError('motion times must strictly increase in 0..3600')
        rigid(sample['frame']); previous = t
    if motion[0]['time'] != 0 or motion[0]['frame'] != target['frame']:
        raise ValueError('motion starts at zero with declared target')


def expand(registry, definition):
    """Parent-before-child records; hierarchy and exact source remain explicit."""
    records=[]
    cache={}
    def visit(d, placed, target, parent, path, motion, clip, ancestors):
        if len(records) >= MAX_PARTS or len(ancestors) >= MAX_DEPTH:
            raise ValueError('assembly expansion budget exceeded')
        key=digest(d)
        if key in ancestors: raise ValueError('cyclic assembly')
        recipe=resolve(d,placed)
        attachment_matrix(d,placed,target); motion_samples(motion,target)
        if clip is not None and (not isinstance(clip,str) or not clip or len(clip)>120):
            raise ValueError('invalid source clip name')
        index=len(records)
        records.append({'definition':d,'instance':placed,'target':target,'parent':parent,
                        'path':path,'motion':motion,'clip':clip})
        if d['adapter'] != ASSEMBLY: return
        if clip is not None or set(recipe) != {'children'}:
            raise ValueError('assembly uses child motions, not an implicit source clip')
        children=recipe['children']
        if not isinstance(children,list) or not 1 <= len(children) <= MAX_PARTS:
            raise ValueError('assembly requires 1..4096 children')
        seen=set()
        for child in children:
            if not isinstance(child,dict) or set(child) != {'instance','target','motion','clip'}:
                raise ValueError('child requires instance, target, motion and clip')
            p=child['instance']
            if not isinstance(p,dict) or not isinstance(p.get('sticker'),dict):
                raise ValueError('invalid child instance')
            identifier(p.get('id'))
            if p['id'] in seen: raise ValueError('duplicate child instance')
            seen.add(p['id']); pin=p['sticker']; lookup=(pin.get('id'),pin.get('version'))
            if lookup not in cache: cache[lookup]=registry.get(*lookup)
            visit(cache[lookup],p,child['target'],index,path+'/'+p['id'],child['motion'],
                  child['clip'],ancestors+(key,))
    visit(validate(definition),instance(definition,'root'),
          {'space':'3d','socket':definition['attachment']['socket'],'frame':identity()},
          None,'root',None,None,())
    return records


def save_assembly(registry, *, id, name, children, origin, ver=1, socket='mount',
                  anchor=None, tags=None, parameters=None):
    d=validate({'schema':SCHEMA,'id':id,'version':ver,'name':name,'origin':origin,
                'tags':tags or [],'adapter':ASSEMBLY,
                'attachment':{'space':'3d','socket':socket,'anchor':anchor or identity()},
                'recipe':{'children':copy.deepcopy(children)},'assets':{},'parameters':parameters or {}})
    expand(registry,d)  # No incomplete or incompatible group is committed.
    registry.register(d)
    return d


def library_bundle(registry,id,ver):
    """Closure includes every source once, not per placement."""
    root=registry.get(id,ver)
    records=expand(registry,root) if root['adapter']==ASSEMBLY else [{'definition':root}]
    definitions={digest(r['definition']):r['definition'] for r in records}
    refs={s for d in definitions.values() for s in d['assets'].values()}
    assets={}; total=0
    for key in sorted(refs):
        body=registry.asset(key); total+=len(body)
        if total>MAX_ASSETS: raise ValueError('library assets exceed 32 MiB')
        assets[key]=base64.b64encode(body).decode('ascii')
    return {'schema':LIBRARY,'root':{'id':root['id'],'version':root['version'],'digest':digest(root)},
            'definitions':list(definitions.values()),'assets':assets}


def import_library(registry,bundle):
    if not isinstance(bundle,dict) or set(bundle) != {'schema','root','definitions','assets'} or bundle['schema'] != LIBRARY:
        raise ValueError('invalid sticker library')
    definitions=bundle['definitions']; assets=bundle['assets']
    if not isinstance(definitions,list) or not 1 <= len(definitions) <= MAX_PARTS:
        raise ValueError('invalid library definitions')
    selected={}
    for d in definitions:
        validate(d); key=(d['id'],d['version'])
        if key in selected: raise ValueError('duplicate library definition')
        selected[key]=d
    class Lookup:
        def get(self,id,ver):
            try: return selected[(id,ver)]
            except (KeyError,TypeError): raise ValueError('missing library dependency') from None
    pin=bundle['root']
    if not isinstance(pin,dict): raise ValueError('invalid library root')
    d=Lookup().get(pin.get('id'),pin.get('version'))
    p=instance(d,'check'); p['sticker']=pin; resolve(d,p)
    records=expand(Lookup(),d) if d['adapter']==ASSEMBLY else [{'definition':d}]
    if {digest(r['definition']) for r in records} != {digest(x) for x in definitions}:
        raise ValueError('library includes unrelated definitions')
    refs={s for d in definitions for s in d['assets'].values()}
    if not isinstance(assets,dict) or set(assets)!=refs or any(not isinstance(v,str) for v in assets.values()):
        raise ValueError('library must contain exactly referenced assets')
    if sum(map(len,assets.values()))>45*1024*1024: raise ValueError('library asset budget exceeded')
    registry.register_many(definitions,{s:base64.b64decode(v,validate=True) for s,v in assets.items()})
    return pin
