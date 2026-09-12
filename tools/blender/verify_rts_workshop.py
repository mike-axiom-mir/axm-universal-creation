"""Independent checks of the exported workshop, including UV/material images."""
import io
import json
import hashlib
import sys
from pathlib import Path
import numpy as np
from PIL import Image
from axm_glb_reader import GLB


def verify(path):
    g=GLB(path);doc=g.doc;triangles=0;vertices=0;degenerate=0;all_points=[]
    assert not doc.get('cameras') and not doc.get('animations')
    assert not any(i.get('uri') for i in doc.get('images',[])), 'all texture images must be embedded'
    images=[]
    for image in doc.get('images',[]):
        view=doc['bufferViews'][image['bufferView']];off=view.get('byteOffset',0);blob=g.binary[off:off+view['byteLength']]
        with Image.open(io.BytesIO(blob)) as im:
            im.load();assert im.width>=256 and im.height>=256
            images.append({'size':[im.width,im.height],'sha256':hashlib.sha256(blob).hexdigest()})
    assert len(images)>=12, 'PBR imagery was lost'
    for mesh in doc['meshes']:
        for p in mesh['primitives']:
            a=p['attributes'];assert all(k in a for k in ['POSITION','NORMAL','TEXCOORD_0'])
            v=g.accessor(a['POSITION']);n=g.accessor(a['NORMAL']);uv=g.accessor(a['TEXCOORD_0']);idx=g.accessor(p['indices']).astype(int).ravel()
            assert all(np.isfinite(t).all() for t in [v,n,uv]);assert len(v)==len(n)==len(uv)
            assert len(idx)%3==0 and idx.min()>=0 and idx.max()<len(v)
            assert np.max(np.abs(np.linalg.norm(n,axis=1)-1))<.03
            cross=np.cross(v[idx.reshape(-1,3)[:,1]]-v[idx.reshape(-1,3)[:,0]],v[idx.reshape(-1,3)[:,2]]-v[idx.reshape(-1,3)[:,0]])
            degenerate+=int(np.sum(np.linalg.norm(cross,axis=1)<1e-10))
            triangles+=len(idx)//3;vertices+=len(v)
    for scene in doc['scenes']:
        for ref in scene.get('nodes',[]):
            for _,points in g.points(doc['nodes'][ref]['name']):all_points.append(points)
    points=np.concatenate(all_points);lo=points.min(0);hi=points.max(0)
    assert np.isfinite(points).all() and hi[1]-lo[1]>4 and hi[1]-lo[1]<6
    assert max(hi-lo)<8, 'review floor or a misplaced component leaked into the asset'
    assert triangles>0 and degenerate/max(1,triangles)<.001
    return {'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'triangles':triangles,'vertices':vertices,
            'degenerate_triangles_under_1e-10':degenerate,'material_batches':len(doc['meshes']),
            'embedded_images':len(images),'bounds_y_up':{'min':lo.tolist(),'max':hi.tolist()},'images':images,
            'scope':'Decoded geometry, UV, normals, embedded images and world bounds. Not an FPS or visual-quality score.'}

if __name__=='__main__':
    root=Path(sys.argv[1]);report={}
    for name in ['improvised-workshop.glb','improvised-workshop-lod1.glb']:report[name]=verify(root/name)
    assert report['improvised-workshop-lod1.glb']['triangles']<report['improvised-workshop.glb']['triangles']
    (root/'glb-inspection.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:{a:b for a,b in v.items() if a!='images'} for k,v in report.items()},indent=2))
