"""UC-owned realization of reusable rigid sticker assemblies into actual GLB.

Resources are copied once per exact source asset; each placement receives its
own node hierarchy. Explicit source clips and socket traces join AssemblyMotion.
"""
import copy
import json
import struct
from axm_stickers import resolve
from axm_stickers.assembly import ASSEMBLY, expand
from axm_stickers.placement import identity, attachment_matrix
from .sticker_adapter import GLB, _trs
from .game_pose_runtime import GamePoseAsset, _parse


def export_assembly(registry,id,ver):
    d=registry.get(id,ver)
    if d['adapter'] != ASSEMBLY: raise ValueError('expected saved assembly')
    records=expand(registry,d)
    doc={'asset':{'version':'2.0','generator':'AXM UC sticker assembly'},'scene':0,
         'scenes':[{'nodes':[]}],'nodes':[],'buffers':[{'byteLength':0}],
         'bufferViews':[],'accessors':[],'meshes':[],'materials':[],
         'images':[],'textures':[],'samplers':[],'animations':[]}
    binary=bytearray(); cache={}; holders={}; mappings={}
    combined={'name':'AssemblyMotion','samplers':[],'channels':[]}

    def index(value,seq,label):
        if type(value) is not int or not 0 <= value < len(seq): raise ValueError('invalid '+label+' reference')
        return value

    def supported(value):
        if isinstance(value,dict):
            if 'extensions' in value and set(value['extensions'])-{'KHR_materials_unlit'}:
                raise ValueError('assembly cannot remap this glTF extension')
            for v in value.values(): supported(v)
        elif isinstance(value,list):
            for v in value: supported(v)

    def load_source(reference):
        if reference in cache: return cache[reference]
        source=registry.asset(reference); GamePoseAsset(source); src,raw=_parse(source)
        supported(src)
        if src.get('skins') or src.get('cameras') or len(src.get('scenes',[]))!=1 or src.get('scene',0)!=0:
            raise ValueError('assembly supports one rigid scene without cameras/skins')
        if set(src.get('extensionsRequired',[]))-{'KHR_materials_unlit'}:
            raise ValueError('unsupported required extension')
        for mesh in src.get('meshes',[]):
            for prim in mesh['primitives']:
                if prim.get('targets'): raise ValueError('morph targets unsupported')
        while len(binary)%4: binary.append(0)
        start=len(binary); binary.extend(raw)
        if len(binary)>32*1024*1024: raise ValueError('assembly source budget exceeded')
        offsets={k:len(doc[k]) for k in ('bufferViews','accessors','meshes','materials','images','textures','samplers')}
        def remap(value,kind): return offsets[kind]+index(value,src.get(kind,[]),kind)
        for view in src.get('bufferViews',[]):
            if view.get('buffer',0)!=0: raise ValueError('external buffer')
            v=copy.deepcopy(view); v['byteOffset']=v.get('byteOffset',0)+start; doc['bufferViews'].append(v)
        for accessor in src.get('accessors',[]):
            if 'sparse' in accessor: raise ValueError('sparse accessor unsupported')
            a=copy.deepcopy(accessor); a['bufferView']=remap(a['bufferView'],'bufferViews'); doc['accessors'].append(a)
        for image in src.get('images',[]):
            if 'uri' in image: raise ValueError('external image unsupported')
            im=copy.deepcopy(image); im['bufferView']=remap(im['bufferView'],'bufferViews'); doc['images'].append(im)
        doc['samplers'].extend(copy.deepcopy(src.get('samplers',[])))
        for texture in src.get('textures',[]):
            t=copy.deepcopy(texture)
            if 'source' not in t: raise ValueError('texture source required')
            t['source']=remap(t['source'],'images')
            if 'sampler' in t: t['sampler']=remap(t['sampler'],'samplers')
            doc['textures'].append(t)
        for material in src.get('materials',[]):
            m=copy.deepcopy(material)
            for container,keys in ((m,('normalTexture','occlusionTexture','emissiveTexture')),
                    (m.get('pbrMetallicRoughness',{}),('baseColorTexture','metallicRoughnessTexture'))):
                for key in keys:
                    if key in container: container[key]['index']=remap(container[key]['index'],'textures')
            doc['materials'].append(m)
        for mesh in src.get('meshes',[]):
            m=copy.deepcopy(mesh)
            for p in m['primitives']:
                p['attributes']={k:remap(v,'accessors') for k,v in p['attributes'].items()}
                if 'indices' in p: p['indices']=remap(p['indices'],'accessors')
                if 'material' in p: p['material']=remap(p['material'],'materials')
            doc['meshes'].append(m)
        used=set(doc.get('extensionsUsed',[]))|set(src.get('extensionsUsed',[]))
        if used: doc['extensionsUsed']=sorted(used)
        required=set(doc.get('extensionsRequired',[]))|set(src.get('extensionsRequired',[]))
        if required: doc['extensionsRequired']=sorted(required)
        cache[reference]=(src,offsets)
        return src,offsets

    def add_track(rows,shape):
        while len(binary)%4: binary.append(0)
        start=len(binary); values=[x for row in rows for x in row]
        binary.extend(struct.pack('<'+'f'*len(values),*values))
        view=len(doc['bufferViews']); doc['bufferViews'].append({'buffer':0,'byteOffset':start,'byteLength':len(binary)-start})
        at=len(doc['accessors']); doc['accessors'].append({'bufferView':view,'componentType':5126,'count':len(rows),'type':shape,
            'min':[min(r[i] for r in rows) for i in range(len(rows[0]))],'max':[max(r[i] for r in rows) for i in range(len(rows[0]))]})
        return at

    def join(animation):
        offset=len(combined['samplers']); combined['samplers'].extend(copy.deepcopy(animation['samplers']))
        for channel in animation['channels']:
            c=copy.deepcopy(channel); c['sampler']+=offset; combined['channels'].append(c)

    for i,record in enumerate(records):
        definition=record['definition']; p=record['instance']; path=record['path']; target=record['target']
        local=attachment_matrix(definition,p,dict(target,frame=identity()))
        socket=len(doc['nodes']); tr,rot=_trs(target['frame']); holder=socket+1
        doc['nodes'].extend([{'name':path+'.socket','translation':tr,'rotation':rot,'children':[holder]},
                            {'name':path+'.mount','matrix':[local[r*4+c] for c in range(4) for r in range(4)],'children':[]}])
        parent=record['parent']
        if parent is None: doc['scenes'][0]['nodes'].append(socket)
        else: doc['nodes'][holders[parent]]['children'].append(socket)
        holders[i]=holder; mappings[path]={'socket':socket,'mount':holder,'source_nodes':[]}
        if record['motion']:
            motion=record['motion']; positions=[]; rotations=[]
            for sample in motion:
                tr,qr=_trs(sample['frame'])
                if rotations and sum(a*b for a,b in zip(rotations[-1],qr))<0: qr=[-x for x in qr]
                positions.append(tr); rotations.append(qr)
            clock=add_track([[s['time']] for s in motion],'SCALAR')
            pos=add_track(positions,'VEC3'); rot=add_track(rotations,'VEC4')
            join({'samplers':[{'input':clock,'output':pos,'interpolation':'LINEAR'},
                              {'input':clock,'output':rot,'interpolation':'LINEAR'}],
                  'channels':[{'sampler':0,'target':{'node':socket,'path':'translation'}},
                              {'sampler':1,'target':{'node':socket,'path':'rotation'}}]})
        if definition['adapter']==ASSEMBLY: continue
        if definition['adapter']!=GLB or resolve(definition,p)!={'model':'model'}:
            raise ValueError('assembly leaf requires rigid GLB sticker')
        src,offsets=load_source(definition['assets']['model']); node_start=len(doc['nodes'])
        def node_ref(v): return node_start+index(v,src['nodes'],'node')
        for j,node in enumerate(src['nodes']):
            n=copy.deepcopy(node); n['name']=path+'/'+str(n.get('name',j))
            if 'mesh' in n: n['mesh']=offsets['meshes']+index(n['mesh'],src.get('meshes',[]),'mesh')
            if 'children' in n: n['children']=[node_ref(v) for v in n['children']]
            if 'skin' in n or 'camera' in n: raise ValueError('unsupported node binding')
            doc['nodes'].append(n)
        doc['nodes'][holder]['children']=[node_ref(v) for v in src['scenes'][0]['nodes']]
        mappings[path]['source_nodes']=list(range(node_start,len(doc['nodes'])))
        found=False; names=set()
        for j,animation in enumerate(src.get('animations',[])):
            a=copy.deepcopy(animation); name=a.get('name',str(j))
            if name in names: raise ValueError('ambiguous source clip name')
            names.add(name); a['name']=path+'::'+name
            for sampler in a['samplers']:
                for key in ('input','output'): sampler[key]=offsets['accessors']+index(sampler[key],src['accessors'],'accessor')
            for channel in a['channels']: channel['target']['node']=node_ref(channel['target']['node'])
            doc['animations'].append(a)
            if record['clip']==name: join(a); found=True
        if record['clip'] is not None and not found: raise ValueError('unknown source clip')
        if len(doc['nodes'])>2048: raise ValueError('assembly GLB node budget exceeded')
    if combined['channels']: doc['animations'].append(combined)
    doc['extras']={'axm_assembly':{'id':id,'version':ver,'source_preserved':True,
                                 'parts':[{'path':r['path'],'pin':r['instance']['sticker'],'origin':r['definition']['origin']} for r in records]}}
    doc['buffers'][0]['byteLength']=len(binary)
    encoded=json.dumps(doc,separators=(',',':'),allow_nan=False).encode(); encoded+=b' '*(-len(encoded)%4)
    binary.extend(b'\0'*(-len(binary)%4))
    body=struct.pack('<4sII',b'glTF',2,28+len(encoded)+len(binary))
    body+=struct.pack('<II',len(encoded),0x4E4F534A)+encoded+struct.pack('<II',len(binary),0x004E4942)+binary
    GamePoseAsset(body)
    return {'body':body,'receipt':{'expanded_parts':len(records),'unique_source_glbs':len(cache),
            'mesh_resources':len(doc['meshes']),'nodes':len(doc['nodes']),'bytes':len(body),
            'clip':'AssemblyMotion' if combined['channels'] else None,'mappings':mappings,
            'source_preserved':True,'continuous_playback_verified':False}}
