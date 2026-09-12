"""Lossless GLB -> portable glTF package with shared, content-addressed images.

Geometry views are copied byte-for-byte. No optimizer, remesher or image encoder
runs here. Export metadata retains source hashes and verifies every relocated view.
"""
import argparse,copy,hashlib,json,struct
from pathlib import Path


def sha(b):return hashlib.sha256(b).hexdigest()


def read_glb(path):
    raw=path.read_bytes();assert len(raw)>=12
    magic,version,size=struct.unpack_from('<III',raw);assert (magic,version,size)==(0x46546c67,2,len(raw))
    pos=12;doc=None;binary=None
    while pos<len(raw):
        n,t=struct.unpack_from('<II',raw,pos);part=raw[pos+8:pos+8+n];assert len(part)==n;pos+=8+n
        if t==0x4e4f534a:doc=json.loads(part)
        elif t==0x004e4942:binary=part
    assert doc is not None and binary is not None
    assert len(doc['buffers'])==1 and 'uri' not in doc['buffers'][0]
    return raw,doc,binary


def convert(path,dest,texture_root):
    raw,original,binary=read_glb(path);doc=copy.deepcopy(original)
    # Opaque extension-owned buffer references require a dedicated adapter.
    assert not any('compression' in k.lower() or 'meshopt' in k.lower() for k in doc.get('extensionsUsed',[]))
    image_views=set();image_receipts=[]
    for im in doc.get('images',[]):
        assert 'bufferView' in im and 'uri' not in im
        i=im.pop('bufferView');v=doc['bufferViews'][i];assert v['buffer']==0
        blob=binary[v.get('byteOffset',0):v.get('byteOffset',0)+v['byteLength']];assert len(blob)==v['byteLength']
        extension={'image/png':'.png','image/jpeg':'.jpg'}[im['mimeType']]
        filename=sha(blob)+extension;target=texture_root/filename
        if target.exists():assert target.read_bytes()==blob
        else:target.write_bytes(blob)
        im['uri']='../../textures/'+filename;image_views.add(i);image_receipts.append({'sha256':sha(blob),'bytes':len(blob)})
    used=set()
    for a in doc.get('accessors',[]):
        if 'bufferView' in a:used.add(a['bufferView'])
        for s in a.get('sparse',{}).values():
            if isinstance(s,dict) and 'bufferView' in s:used.add(s['bufferView'])
    keep=[i for i in range(len(doc['bufferViews'])) if i not in image_views or i in used]
    remap={old:new for new,old in enumerate(keep)};packed=bytearray();views=[];receipts=[]
    for i in keep:
        v=copy.deepcopy(doc['bufferViews'][i]);assert v['buffer']==0
        start=v.get('byteOffset',0);blob=binary[start:start+v['byteLength']];assert len(blob)==v['byteLength']
        packed.extend(b'\0'*(-len(packed)%4));v['byteOffset']=len(packed);packed.extend(blob);views.append(v)
        receipts.append({'old_view':i,'new_view':remap[i],'sha256':sha(blob),'bytes':len(blob)})
    for a in doc.get('accessors',[]):
        if 'bufferView' in a:a['bufferView']=remap[a['bufferView']]
        for s in a.get('sparse',{}).values():
            if isinstance(s,dict) and 'bufferView' in s:s['bufferView']=remap[s['bufferView']]
    doc['bufferViews']=views;doc['buffers']=[{'uri':dest.stem+'.bin','byteLength':len(packed)}]
    dest.parent.mkdir(parents=True,exist_ok=True);dest.with_suffix('.bin').write_bytes(packed);dest.write_text(json.dumps(doc,separators=(',',':'))+'\n')
    # Verify from the written files, not from only the in-memory construction.
    written=json.loads(dest.read_text());out=dest.with_suffix('.bin').read_bytes()
    for r in receipts:
        v=written['bufferViews'][r['new_view']];chunk=out[v['byteOffset']:v['byteOffset']+v['byteLength']];assert sha(chunk)==r['sha256']
    for im,r in zip(written.get('images',[]),image_receipts):assert sha((dest.parent/im['uri']).read_bytes())==r['sha256']
    for k in ['nodes','meshes','materials','textures','samplers','animations','skins','scenes','scene']:
        assert written.get(k)==original.get(k),k
    return {'source_glb_sha256':sha(raw),'gltf_sha256':sha(dest.read_bytes()),'bin_sha256':sha(out),'geometry_views':len(receipts),'image_occurrences':len(image_receipts),'lossless_views_verified':True,'source_bytes':len(raw),'geometry_bytes':len(out)}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--sources',type=Path,nargs='+',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise SystemExit('Use a new destination')
    textures=a.output/'textures';textures.mkdir(parents=True)
    reports={}
    for root in a.sources:
        for path in sorted(root.glob('*/*.glb')):
            asset=path.parent.name;name=asset+'/'+path.stem
            assert name not in reports,'Duplicate asset source'
            reports[name]=convert(path,a.output/'assets'/asset/(path.stem+'.gltf'),textures)
    assert reports,'No GLB assets found'
    (a.output/'packing-verification.json').write_text(json.dumps({'assets_lods':reports,'shared_images':len(list(textures.iterdir()))},indent=2)+'\n')
    print(json.dumps({'asset_lods':len(reports),'shared_images':len(list(textures.iterdir()))}))
