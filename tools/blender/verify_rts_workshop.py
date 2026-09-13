"""Independent checks of the exported workshop, including UV/material images."""
import io
import json
import hashlib
import sys
from pathlib import Path
import numpy as np
from PIL import Image
from axm_glb_reader import GLB


VARIANTS = (
    'improvised-workshop.glb',
    'improvised-workshop-lod1.glb',
    'improvised-workshop-tactical.glb',
    'improvised-workshop-rts.glb',
    'improvised-workshop-far.glb',
)

TARGET_BANDS = {
    'improvised-workshop-tactical.glb': (20_000, 40_000),
    'improvised-workshop-rts.glb': (4_000, 12_000),
    'improvised-workshop-far.glb': (500, 2_000),
}


def verify(path):
    g=GLB(path);doc=g.doc;triangles=0;vertices=0;degenerate=0;all_points=[]
    assert not doc.get('cameras') and not doc.get('animations')
    assert not any(i.get('uri') for i in doc.get('images',[])), 'all texture images must be embedded'
    images=[];compressed_image_bytes=0;estimated_rgba8_bytes=0
    for image in doc.get('images',[]):
        view=doc['bufferViews'][image['bufferView']];off=view.get('byteOffset',0);blob=g.binary[off:off+view['byteLength']]
        compressed_image_bytes+=len(blob)
        with Image.open(io.BytesIO(blob)) as im:
            im.load();assert im.width>=256 and im.height>=256
            estimated_rgba8_bytes+=im.width*im.height*4
            images.append({'size':[im.width,im.height],'bytes':len(blob),'sha256':hashlib.sha256(blob).hexdigest()})
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
    materials=doc.get('materials',[])
    return {'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'triangles':triangles,'vertices':vertices,
            'degenerate_triangles_under_1e-10':degenerate,'material_batches':len(doc['meshes']),
            'materials':len(materials),'double_sided_materials':sum(bool(m.get('doubleSided')) for m in materials),
            'embedded_images':len(images),'embedded_compressed_bytes':compressed_image_bytes,
            'estimated_rgba8_bytes_before_mips':estimated_rgba8_bytes,
            'bounds_y_up':{'min':lo.tolist(),'max':hi.tolist()},'images':images,
            'scope':'Decoded geometry, UV, normals, material flags, embedded images and world bounds. Not collision, engine import, FPS, LOD perceptual equivalence or visual-quality proof.'}


def validate_lod_ladder(report):
    counts=[report[name]['triangles'] for name in VARIANTS]
    assert all(a>b for a,b in zip(counts,counts[1:])), f'LOD ladder must strictly reduce triangles: {counts}'
    target_results={}
    for name,(minimum,maximum) in TARGET_BANDS.items():
        triangles=report[name]['triangles']
        assert minimum<=triangles<=maximum, f'{name} triangles {triangles} outside target {minimum}..{maximum}'
        target_results[name]={'triangles':triangles,'target_min':minimum,'target_max':maximum,'inside_target_band':True}
    return target_results


def game_readiness_gates(report):
    near=report['improvised-workshop.glb'];lod=report['improvised-workshop-lod1.glb']
    tactical=report['improvised-workshop-tactical.glb'];rts=report['improvised-workshop-rts.glb'];far=report['improvised-workshop-far.glb']
    ratio=lod['triangles']/near['triangles']
    target_results=validate_lod_ladder(report)
    return {
        'schema':'axm.workshop-game-readiness-gates/v0.2-lod-ladder',
        'source':'glb-inspection.json',
        'measured':{
            'detailed_triangles':near['triangles'],
            'lod1_triangles':lod['triangles'],
            'lod1_triangle_ratio':ratio,
            'tactical_triangles':tactical['triangles'],
            'rts_triangles':rts['triangles'],
            'far_triangles':far['triangles'],
            'runtime_lod_target_bands':target_results,
            'detailed_materials':near['materials'],
            'lod1_materials':lod['materials'],
            'tactical_materials':tactical['materials'],
            'rts_materials':rts['materials'],
            'far_materials':far['materials'],
            'detailed_double_sided_materials':near['double_sided_materials'],
            'lod1_double_sided_materials':lod['double_sided_materials'],
            'detailed_embedded_images':near['embedded_images'],
            'detailed_embedded_compressed_bytes':near['embedded_compressed_bytes'],
            'detailed_estimated_rgba8_bytes_before_mips':near['estimated_rgba8_bytes_before_mips'],
        },
        'gates':{
            'geometry_structure':'TESTED',
            'embedded_texture_integrity':'TESTED',
            'lod_triangle_reduction':'TESTED',
            'runtime_lod_target_bands':'TESTED',
            'lod_perceptual_equivalence':'NOT_TESTED',
            'collision':'NOT_TESTED',
            'navigation':'NOT_TESTED',
            'target_engine_import':'NOT_TESTED',
            'target_rts_integration':'NOT_TESTED',
            'target_device_fps':'NOT_TESTED',
            'material_texture_budget_acceptance':'NOT_TESTED',
            'visual_quality':'NOT_TESTED',
        },
        'nonclaims':[
            'A valid GLB is not a game-ready asset by itself.',
            'Triangle reduction and target-band membership are not LOD visual equivalence.',
            'Material/image counts are measured cost surfaces, not accepted budgets.',
            'The far geometry tier is not an impostor and is not automatically the final far-distance solution.',
            'No collision, navigation, target-engine, target-RTS or target-device performance claim is created by this report.',
        ],
    }


if __name__=='__main__':
    root=Path(sys.argv[1]);report={}
    for name in VARIANTS:report[name]=verify(root/name)
    validate_lod_ladder(report)
    (root/'glb-inspection.json').write_text(json.dumps(report,indent=2)+'\n')
    gates=game_readiness_gates(report)
    (root/'game-readiness-gates.json').write_text(json.dumps(gates,indent=2)+'\n')
    print(json.dumps({k:{a:b for a,b in v.items() if a!='images'} for k,v in report.items()},indent=2))
    print(json.dumps(gates,indent=2))
