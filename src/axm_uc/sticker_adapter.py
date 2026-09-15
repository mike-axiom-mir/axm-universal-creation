"""UC consumers of axm_stickers; the registry remains independently usable.

2D instances render isolated editable recipes, then place cached RGBA results.
3D attachments add wrapper nodes/tracks to a derivative GLB, retaining source.
"""
import copy
import hashlib
import json
import math
from pathlib import Path
import shutil
import struct
import tempfile

from axm_stickers import Registry, digest, resolve, validate
from axm_stickers.core import SCHEMA
from axm_stickers.placement import (identity, rigid, multiply, inverse_rigid,
                                    attachment_matrix, placement_2d)
from . import studio_compositor as studio
from .fabric_noise import png_bytes
from .game_pose_runtime import GamePoseAsset, _parse

STUDIO = 'axm.sticker.studio-layered/v1'
GLB = 'axm.sticker.glb-rigid/v1'
MAX_PLACEMENTS = 4096
MAX_WORK = 16*1024*1024


def _sha(body): return hashlib.sha256(body).hexdigest()


def definition(id, name, adapter, attachment, recipe, assets, *, ver=1, tags=None,
               parameters=None, author, license, source):
    return validate({'schema':SCHEMA,'id':id,'version':ver,'name':name,'adapter':adapter,
                     'attachment':attachment,'recipe':recipe,'assets':assets,
                     'tags':tags or [],'parameters':parameters or {},
                     'origin':{'author':author,'license':license,'source':source}})


def register_studio(registry, project, source_root, *, id, name, anchor=None, **metadata):
    composed = studio.compose_studio_project(project,source_root)
    bodies = {_sha(body):body for body in composed['sources'].values()}
    d = definition(id,name,STUDIO,{'space':'2d','socket':'surface','anchor':anchor or [0,0]},
                   {'project':copy.deepcopy(project)},
                   {key:_sha(body) for key,body in composed['sources'].items()},**metadata)
    registry.register(d,bodies)
    return d


def _studio_render(registry,d,recipe):
    if set(recipe) != {'project'}: raise ValueError('unsupported Studio sticker recipe')
    project = copy.deepcopy(recipe['project'])
    if not isinstance(project,dict) or set(project.get('sources',{})) != set(d['assets']):
        raise ValueError('sticker source IDs must match its captured assets')
    with tempfile.TemporaryDirectory(prefix='axm-sticker-') as root:
        for index,(key,ref) in enumerate(sorted(d['assets'].items())):
            name = f'{index}.png'
            (Path(root)/name).write_bytes(registry.asset(ref))
            project['sources'][key] = name
        result = studio.compose_studio_project(project,root)
    # Studio emits unfiltered RGBA PNG; decode using the existing general reader.
    header,compressed,palette,transparency = studio._parse_png(result['png'])
    rows,_ = studio._inflate_scanlines(header,compressed)
    rgba = bytes(c for row in rows for pixel in studio._row_rgba(
        row,header['color_type'],palette,transparency) for c in pixel)
    return result['receipt']['width'],result['receipt']['height'],rgba


def _over(destination,at,source,opacity):
    a = source[3]/255*opacity
    if a == 0: return
    b = destination[at+3]/255
    out = a+b*(1-a)
    for c in range(3):
        destination[at+c] = round((source[c]*a+destination[at+c]*b*(1-a))/out)
    destination[at+3] = round(out*255)


def stamp_layer(registry, instances, *, width, height, target=None):
    """Place up to 4096 instances under an explicit clipped-pixel work ceiling.

    Nearest-neighbour sampling preserves hard pixels; antialiasing is not claimed.
    Anchor and transforms use pixel edges; sampling uses pixel centres.
    """
    studio._dimension(width); studio._dimension(height)
    if not isinstance(instances,list) or not 1 <= len(instances) <= MAX_PLACEMENTS:
        raise ValueError('supply 1..4096 instances')
    target = {'space':'2d','socket':'surface'} if target is None else target
    canvas = bytearray(width*height*4)
    cache,definitions,seen = {},{},set()
    work,cached_pixels = 0,0
    for placed in instances:
        if not isinstance(placed,dict) or not isinstance(placed.get('sticker'),dict):
            raise ValueError('invalid sticker instance')
        reference = placed['sticker']
        key = (reference.get('id'),reference.get('version'))
        if key not in definitions: definitions[key] = registry.get(*key)
        d = definitions[key]
        recipe = resolve(d,placed)
        if placed['id'] in seen: raise ValueError('duplicate instance ID')
        seen.add(placed['id'])
        if d['adapter'] != STUDIO: raise ValueError('sticker requires another rendering adapter')
        a,b,c,e,tx,ty = placement_2d(d,placed,target)
        render_key = digest({'recipe':recipe,'assets':d['assets']})
        if render_key not in cache:
            if len(cache) >= 32: raise ValueError('at most 32 unique renders per placement call')
            w,h,pixels = _studio_render(registry,d,recipe)
            cached_pixels += w*h
            if cached_pixels > 4*1024*1024: raise ValueError('unique sticker raster budget exceeded')
            cache[render_key] = (w,h,pixels)
        w,h,pixels = cache[render_key]
        corners = [(a*x+c*y+tx,b*x+e*y+ty) for x,y in ((0,0),(w,0),(0,h),(w,h))]
        x0=max(0,math.floor(min(p[0] for p in corners))); x1=min(width,math.ceil(max(p[0] for p in corners)))
        y0=max(0,math.floor(min(p[1] for p in corners))); y1=min(height,math.ceil(max(p[1] for p in corners)))
        work += max(0,x1-x0)*max(0,y1-y0)
        if work > MAX_WORK: raise ValueError('sticker placement work budget exceeded')
        det = a*e-b*c
        opacity = placed['placement'].get('opacity',1)
        for y in range(y0,y1):
            for x in range(x0,x1):
                dx,dy = x+.5-tx,y+.5-ty
                sx,sy = math.floor((e*dx-c*dy)/det),math.floor((-b*dx+a*dy)/det)
                if 0 <= sx < w and 0 <= sy < h:
                    pos = (sy*w+sx)*4
                    _over(canvas,(y*width+x)*4,pixels[pos:pos+4],opacity)
    return {'png':png_bytes(width,height,4,bytes(canvas)),
            'receipt':{'instances':len(instances),'unique_renders':len(cache),
                       'clipped_pixel_visits':work,'sampling':'nearest-neighbour',
                       'visual_approval':False,'canonical_definitions_modified':False}}


def publish_sticker_scene(path, registry, host, source_root, instances):
    """Editable host + instance recipe + selected registry + replayable preview."""
    target = Path(path)
    if target.exists(): raise FileExistsError(target)
    base = studio.compose_studio_project(host,source_root)
    stamp = stamp_layer(registry,instances,width=base['receipt']['width'],height=base['receipt']['height'])
    if 'axm-stickers' in host['sources'] or any(x['id']=='axm-stickers' for x in host['recipe']['layers']):
        raise ValueError('reserved placement layer/source ID already exists')
    target.parent.mkdir(parents=True,exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='sticker-scene-',dir=target.parent))
    try:
        with tempfile.TemporaryDirectory(prefix='sticker-input-') as temp:
            derived = copy.deepcopy(host)
            for index,(key,body) in enumerate(sorted(base['sources'].items())):
                name=f'{index}.png'; (Path(temp)/name).write_bytes(body); derived['sources'][key]=name
            (Path(temp)/'stamps.png').write_bytes(stamp['png'])
            derived['sources']['axm-stickers']='stamps.png'
            derived['recipe']['layers'].append({'id':'axm-stickers','source_artifact_id':'axm-stickers'})
            studio.publish_studio_project(stage/'preview',derived,temp)
        published = json.loads((stage/'preview/project.json').read_text())
        canonical = copy.deepcopy(host)
        canonical['sources']={key:'preview/'+published['sources'][key] for key in host['sources']}
        scene={'schema':'axm.sticker-scene-2d/v1','host':canonical,'instances':copy.deepcopy(instances)}
        (stage/'scene.json').write_text(json.dumps(scene,indent=2)+'\n',encoding='utf-8')
        with Registry(stage/'stickers.sqlite') as selected:
            for p in instances:
                d=registry.get(p['sticker']['id'],p['sticker']['version'])
                selected.register(d,{ref:registry.asset(ref) for ref in set(d['assets'].values())})
        (stage/'receipt.json').write_text(json.dumps(stamp['receipt'],indent=2)+'\n',encoding='utf-8')
        if target.exists(): raise FileExistsError(target)
        stage.rename(target)
        return stamp['receipt']
    finally:
        if stage.exists(): shutil.rmtree(stage)


def register_glb(registry,body,*,id,name,socket,anchor=None,editable_source=None,**metadata):
    GamePoseAsset(body)
    document,_ = _parse(body)
    if document.get('skins') or any('uri' in image for image in document.get('images',[])):
        raise ValueError('first GLB adapter requires rigid meshes and embedded images')
    bodies={_sha(body):body}; assets={'model':_sha(body)}
    if editable_source is not None:
        if not isinstance(editable_source,bytes): raise ValueError('editable source must be exact bytes')
        bodies[_sha(editable_source)]=editable_source; assets['editable-source']=_sha(editable_source)
    d=definition(id,name,GLB,{'space':'3d','socket':socket,'anchor':anchor or identity()},
                 {'model':'model'},assets,**metadata)
    registry.register(d,bodies)
    return d


def _trs(frame):
    m=rigid(frame)
    # Stable quaternion recovery for all proper rigid rotations, including pi.
    trace=m[0]+m[5]+m[10]
    if trace > 0:
        s=math.sqrt(trace+1)*2
        q=[(m[9]-m[6])/s,(m[2]-m[8])/s,(m[4]-m[1])/s,s/4]
    elif m[0] > m[5] and m[0] > m[10]:
        s=math.sqrt(1+m[0]-m[5]-m[10])*2
        q=[s/4,(m[1]+m[4])/s,(m[2]+m[8])/s,(m[9]-m[6])/s]
    elif m[5] > m[10]:
        s=math.sqrt(1+m[5]-m[0]-m[10])*2
        q=[(m[1]+m[4])/s,s/4,(m[6]+m[9])/s,(m[2]-m[8])/s]
    else:
        s=math.sqrt(1+m[10]-m[0]-m[5])*2
        q=[(m[2]+m[8])/s,(m[6]+m[9])/s,s/4,(m[4]-m[1])/s]
    return [m[3],m[7],m[11]],q


def attach_glb(registry,placed,target,*,motion=None,clip='StickerSocketMotion'):
    """Derivative GLB with preserved meshes/materials and animated host socket.

    motion is a bounded sampled host trace [{time, frame}, ...]. It creates one
    ordinary glTF LINEAR clip; internal clips are retained, not implicitly mixed.
    """
    d=registry.get(placed['sticker']['id'],placed['sticker']['version'])
    recipe=resolve(d,placed)
    if d['adapter'] != GLB or recipe != {'model':'model'} or placed['overrides']:
        raise ValueError('unsupported rigid GLB sticker recipe/parameters')
    local_target={'space':'3d','socket':target.get('socket'),'frame':identity()}
    attachment_matrix(d,placed,target)  # Validate target before deriving local frame.
    local=attachment_matrix(d,placed,local_target)
    source=registry.asset(d['assets']['model'])
    GamePoseAsset(source)
    doc,original_binary=_parse(source)
    if doc.get('skins') or any('uri' in image for image in doc.get('images',[])):
        raise ValueError('first GLB adapter requires rigid meshes and embedded images')
    if len(doc.get('scenes',[])) != 1 or doc.get('scene',0) != 0: raise ValueError('attachment requires one explicit scene')
    roots=list(doc['scenes'][0]['nodes']); nodes=doc['nodes']
    holder=len(nodes)
    nodes.append({'name':placed['id']+'.mount','matrix':[local[r*4+c] for c in range(4) for r in range(4)],'children':roots})
    socket=len(nodes)
    translation,rotation=_trs(target['frame'])
    nodes.append({'name':placed['id']+'.socket','translation':translation,'rotation':rotation,'children':[holder]})
    doc['scenes'][0]['nodes']=[socket]
    binary=bytearray(original_binary)
    if motion is not None:
        if not isinstance(motion,list) or not 2 <= len(motion) <= 240: raise ValueError('motion requires 2..240 samples')
        if not isinstance(clip,str) or not clip or len(clip)>120: raise ValueError('invalid clip name')
        animations=doc.setdefault('animations',[])
        if any(x.get('name')==clip for x in animations): raise ValueError('clip name already exists')
        times,translations,rotations=[],[],[]
        for sample in motion:
            if not isinstance(sample,dict) or set(sample) != {'time','frame'}: raise ValueError('invalid motion sample')
            t=sample['time']
            if type(t) not in (int,float) or not math.isfinite(t) or not 0 <= t <= 3600 or (times and t<=times[-1]):
                raise ValueError('motion times must strictly increase in 0..3600 seconds')
            tr,qr=_trs(sample['frame'])
            if rotations and sum(a*b for a,b in zip(rotations[-1],qr))<0: qr=[-v for v in qr]
            times.append(t); translations.append(tr); rotations.append(qr)
        if times[0] != 0 or motion[0]['frame'] != target['frame']:
            raise ValueError('motion must start at zero with the declared target frame')
        def accessor(rows,shape):
            while len(binary)%4: binary.append(0)
            start=len(binary)
            values=[x for row in rows for x in row]
            binary.extend(struct.pack('<'+'f'*len(values),*values))
            views=doc.setdefault('bufferViews',[]); index=len(views)
            views.append({'buffer':0,'byteOffset':start,'byteLength':len(binary)-start})
            accesses=doc.setdefault('accessors',[]); result=len(accesses)
            accesses.append({'bufferView':index,'componentType':5126,'count':len(rows),'type':shape,
                             'min':[min(row[i] for row in rows) for i in range(len(rows[0]))],
                             'max':[max(row[i] for row in rows) for i in range(len(rows[0]))]})
            return result
        clock=accessor([[t] for t in times],'SCALAR')
        pos=accessor(translations,'VEC3'); rot=accessor(rotations,'VEC4')
        animations.append({'name':clip,'samplers':[{'input':clock,'output':pos,'interpolation':'LINEAR'},
                                                  {'input':clock,'output':rot,'interpolation':'LINEAR'}],
                           'channels':[{'sampler':0,'target':{'node':socket,'path':'translation'}},
                                       {'sampler':1,'target':{'node':socket,'path':'rotation'}}]})
    doc['buffers'][0]['byteLength']=len(binary)
    doc.setdefault('extras',{})['axm_sticker']={'definition':placed['sticker'],'instance':placed,'origin':d['origin'],'source_sha256':_sha(source)}
    json_chunk=json.dumps(doc,separators=(',',':'),allow_nan=False).encode()
    json_chunk+=b' '*((-len(json_chunk))%4); binary.extend(b'\0'*((-len(binary))%4))
    body=struct.pack('<4sII',b'glTF',2,28+len(json_chunk)+len(binary))
    body+=struct.pack('<II',len(json_chunk),0x4E4F534A)+json_chunk
    body+=struct.pack('<II',len(binary),0x004E4942)+binary
    GamePoseAsset(body)  # Independent intake validates the derivative, including tracks.
    return {'body':body,'receipt':{'source_sha256':_sha(source),'output_sha256':_sha(body),
            'source_preserved':True,'socket_node':socket,'mount_node':holder,
            'clip':clip if motion is not None else None,'visual_approval':False}}
