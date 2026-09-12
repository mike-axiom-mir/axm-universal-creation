"""Independent delivered-GLB checks including original animation byte equality."""
import argparse,hashlib,io,json
from pathlib import Path
import numpy as np
from PIL import Image
from axm_glb_reader import GLB


def verify(path,source=None):
    g=GLB(path);d=g.doc;tris=0
    for image in d.get('images',[]):
        assert not image.get('uri'),'External image dependency'
        v=d['bufferViews'][image['bufferView']];o=v.get('byteOffset',0)
        with Image.open(io.BytesIO(g.binary[o:o+v['byteLength']])) as im:im.load();assert min(im.size)>=256
    assert d.get('images'),'Missing surface textures'
    for mesh in d['meshes']:
        for p in mesh['primitives']:
            a=p['attributes'];v=g.accessor(a['POSITION']);n=g.accessor(a['NORMAL']);uv=g.accessor(a['TEXCOORD_0']);idx=g.accessor(p['indices']).astype(int).ravel()
            assert len(v)==len(n)==len(uv) and all(np.isfinite(x).all() for x in [v,n,uv])
            assert len(idx)%3==0 and idx.min()>=0 and idx.max()<len(v)
            assert np.max(abs(np.linalg.norm(n,axis=1)-1))<.03
            tris+=len(idx)//3
    if source:
        old=GLB(source)
        assert d['nodes']==old.doc['nodes'],'Node structure changed'
        assert d.get('animations')==old.doc.get('animations'),'Animation structure changed'
        for anim in d.get('animations',[]):
            for sampler in anim['samplers']:
                for role in ['input','output']:
                    assert np.array_equal(g.accessor(sampler[role]),old.accessor(sampler[role])),'Animation samples changed'
        assert d['extras']['axmAssembly']==old.doc['extras']['axmAssembly'],'Sockets/pivots changed'
    return {'triangles':tris,'images':len(d.get('images',[])),'clips':[a['name'] for a in d.get('animations',[])],
            'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'source_animation_and_assembly_preserved':bool(source)}


def main():
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('source',type=Path);args=p.parse_args()
    manifest=json.loads((args.root/'batch-manifest.json').read_text());results={}
    assert manifest['complete'] and manifest['asset_count']==83
    for key,a in manifest['assets'].items():
        files={}
        for suffix in ['', '-lod1']:
            name=key+suffix+'.glb';old=None if key=='improvised-workshop' else args.source/'assets'/key/name
            files[name]=verify(args.root/'assets'/key/name,old)
        assert files[key+'-lod1.glb']['triangles']<files[key+'.glb']['triangles'],key
        col=args.source/'assets'/key/(key+'-collision.glb')
        if key!='improvised-workshop' and col.exists():assert col.read_bytes()==(args.root/'assets'/key/col.name).read_bytes()
        results[key]=files
    (args.root/'verification.json').write_text(json.dumps({'verified_assets':len(results),'results':results,'scope':'Decoded GLB data and exact retained animation samples/assembly. No visual equivalence or target RTS execution claim.'},indent=2)+'\n')
    print('VERIFIED',len(results),'assets /',len(results)*2,'textured GLBs')

if __name__=='__main__':main()
