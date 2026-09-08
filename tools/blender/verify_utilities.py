"""Decode utility GLBs; exact rigid sweep bounds and triangle/box coverage."""
import hashlib,json,math,sys
from pathlib import Path
import numpy as np
from axm_glb_reader import GLB
ROOTS={'velcro-sun':'VelcroSunRoot','upsie-daisy':'UpsieDaisyRoot','panic-biscuit':'PanicBiscuitRoot','borrowed-wall-device':'BorrowedWallDeviceRoot','borrowed-wall':'BorrowedWallRoot'}
GRIPS={'velcro-sun':[0,.030,-.039],'upsie-daisy':[0,.026,-.030],'panic-biscuit':[0,.035,-.043],'borrowed-wall-device':[0,.036,-.038]}

def world(g,i):return (world(g,g.parents[i]) if i in g.parents else np.eye(4))@g.local(i)
def points(g,name,local=False):
    pts=np.concatenate([p for _,p in g.points(name,skip_first=True)])
    return pts if local else (world(g,g.names[name])@np.column_stack((pts,np.ones(len(pts)))).T).T[:,:3]
def sinusoid_extrema(aa,bb,cc,lo,hi):
    ends=np.stack((cc+aa*np.cos(lo)+bb*np.sin(lo),cc+aa*np.cos(hi)+bb*np.sin(hi)))
    minima=ends.min(axis=0);maxima=ends.max(axis=0);phi=np.arctan2(bb,aa)
    for k in range(-3,4):
        theta=phi+k*np.pi;valid=(theta>=lo-1e-12)&(theta<=hi+1e-12);value=cc+aa*np.cos(theta)+bb*np.sin(theta);minima=np.minimum(minima,np.where(valid,value,np.inf));maxima=np.maximum(maxima,np.where(valid,value,-np.inf))
    return minima,maxima
def triangles_world(g):
    chunks=[]
    for i,n in enumerate(g.doc['nodes']):
        if 'mesh' not in n:continue
        matrix=world(g,i)
        for p in g.doc['meshes'][n['mesh']]['primitives']:
            pts=g.accessor(p['attributes']['POSITION']);pts=(matrix@np.column_stack((pts,np.ones(len(pts)))).T).T[:,:3];chunks.append(pts[g.accessor(p['indices']).ravel().reshape(-1,3)])
    return np.concatenate(chunks)

out=Path(sys.argv[1]);reports={}
for name,root in ROOTS.items():
    folder=out/name;g=GLB(folder/(name+'.glb'));doc=g.doc;m=json.loads((folder/'manifest.json').read_text());sha=hashlib.sha256(g.raw).hexdigest();assert sha==m['sha256'];assert doc['scenes'][doc.get('scene',0)]['nodes']==[g.names[root]];assert np.allclose(g.local(g.names[root]),np.eye(4),atol=1e-7)
    assert not any(doc.get(k) for k in ('textures','images','skins','animations','cameras'));assert all('uri' not in b for b in doc['buffers']);assert len(doc['materials'])<=6 and all(mat.get('alphaMode','OPAQUE')=='OPAQUE' for mat in doc['materials'])
    for key,record in m['nodes'].items():
        node=doc['nodes'][g.names[key]];assert 'mesh' not in node;parent=doc['nodes'][g.parents[g.names[key]]]['name'] if g.names[key] in g.parents else None;assert parent==record['parent'];assert np.allclose(node.get('translation',[0,0,0]),record['translation_gltf_m'],atol=1e-7);assert np.allclose(world(g,g.names[key])[:3,3],record['world_translation_gltf_m'],atol=1e-6);assert np.allclose(node.get('rotation',[0,0,0,1]),[0,0,0,1],atol=1e-7);assert np.allclose(node.get('scale',[1,1,1]),[1,1,1],atol=1e-7)
    assert np.allclose(world(g,g.names['Contact'])[:3,3],[0,0,0],atol=1e-7)
    if name in GRIPS:assert np.allclose(world(g,g.names['Grip'])[:3,3],GRIPS[name],atol=1e-7)
    if name in ('panic-biscuit','borrowed-wall-device'):
        assert doc['nodes'][g.parents[g.names['EffectOrigin']]]['name']==('BeaconLift' if name=='panic-biscuit' else 'ProjectorLift')
    count=primitives=0
    for mesh in doc['meshes']:
        for p in mesh['primitives']:
            assert p.get('mode',4)==4;pos=g.accessor(p['attributes']['POSITION']);norm=g.accessor(p['attributes']['NORMAL']);ix=g.accessor(p['indices']).ravel();assert np.isfinite(pos).all() and np.isfinite(norm).all();assert len(pos)==len(norm) and np.allclose(np.linalg.norm(norm,axis=1),1,atol=.001);assert len(ix)%3==0 and ix.max()<len(pos)
            tri=pos[ix.reshape(-1,3)];area=np.linalg.norm(np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]),axis=1);assert np.all(area>1e-12),(name,mesh.get('name'),int((area<=1e-12).sum()));count+=len(ix)//3;primitives+=1
    assert (count,primitives)==(m['triangles'],m['primitives']) and count<=m['triangle_budget'] and primitives<=m['primitive_budget']
    pts=points(g,root);bounds=np.column_stack((pts.min(0),pts.max(0)));assert np.allclose(bounds,m['bounds_gltf_xyz_m'],atol=1e-5);assert bounds[1,0]>=-1e-6
    states=json.loads((folder/'combined-state-checks.json').read_text());assert states['glb_sha256']==sha
    for stage in ('source','fresh-import'):assert len(states['stages'][stage])==21 and all(not row['intersections'] for row in states['stages'][stage])
    assert all(not row['intersections'] for check in m['motion_checks'] for row in check['samples'])
    swept=bounds.copy();radius=float(np.linalg.norm(pts,axis=1).max());parts=[]
    for spec in m['motions']:
        pp=points(g,spec['part']);pivot=world(g,g.names[spec['part']])[:3,3];axis=np.eye(3)[{'local X':0,'local Y':1,'local Z':2}[spec['axis']]];lo,hi=sorted((0,spec['samples'][-1]))
        if spec['motion']=='translation':
            union=np.concatenate((pp+axis*lo,pp+axis*hi));bb=np.column_stack((union.min(0),union.max(0)));rr=float(np.linalg.norm(union,axis=1).max())
        else:
            relative=pp-pivot;parallel=np.outer(relative@axis,axis);aa=relative-parallel;bbv=np.cross(np.broadcast_to(axis,relative.shape),relative);cc=pivot+parallel;bb=[]
            for k in range(3):mn,mx=sinusoid_extrema(aa[:,k],bbv[:,k],cc[:,k],lo,hi);bb.append([float(mn.min()),float(mx.max())])
            bb=np.array(bb);_,rad=sinusoid_extrema(2*np.sum(cc*aa,axis=1),2*np.sum(cc*bbv,axis=1),np.sum(cc*cc,axis=1)+np.sum(aa*aa,axis=1),lo,hi);rr=float(np.sqrt(max(0,rad.max())))
        swept[:,0]=np.minimum(swept[:,0],bb[:,0]);swept[:,1]=np.maximum(swept[:,1],bb[:,1]);radius=max(radius,rr);parts.append({'part':spec['part'],'continuous_bounds_gltf_xyz_m':bb.tolist(),'continuous_max_origin_radius_m':rr})
    assert swept[1,0]>=-1e-6
    collision=None
    if name=='borrowed-wall':
        contract=json.loads((folder/'collision-contract.json').read_text());assert contract['glb_sha256']==sha and len(contract['fixed_boxes'])==9 and len(contract['moving_tier_boxes'])==14;assert np.allclose(contract['deployed_bounds_gltf_xyz_m'],bounds,atol=1e-5);assert np.allclose(swept[[0,2]],bounds[[0,2]],atol=1e-5)
        coverage=[];originals={s['part']:json.loads(json.dumps(doc['nodes'][g.names[s['part']]])) for s in m['motions']}
        for i in range(21):
            fraction=i/20;boxes=[np.array(r['bounds_gltf_xyz_m']) for r in contract['fixed_boxes']]
            for record in contract['moving_tier_boxes']:
                node=doc['nodes'][g.names[record['part']]];delta=record['travel_m'][-1]*fraction;node['translation']=originals[record['part']]['translation'].copy();node['translation'][1]+=delta;bb=np.array(record['bounds_gltf_xyz_m']);bb[1]+=delta;boxes.append(bb)
            tri=triangles_world(g);covered=np.zeros(len(tri),dtype=bool)
            for bb in boxes:covered|=((tri>=bb[:,0]-1e-5)&(tri<=bb[:,1]+1e-5)).all(axis=(1,2))
            assert covered.all(),(name,'uncovered collision triangles',i,int((~covered).sum()));p=tri.reshape(-1,3);bb=np.column_stack((p.min(0),p.max(0)));assert np.allclose(bb[[0,2]],bounds[[0,2]],atol=1e-5)
            coverage.append({'progress':fraction,'triangles_enclosed':int(covered.sum()),'bounds_gltf_xyz_m':bb.tolist()})
            if i==20:assert np.allclose(bb,contract['folded_bounds_gltf_xyz_m'],atol=1e-5)
        for n,record in originals.items():doc['nodes'][g.names[n]].clear();doc['nodes'][g.names[n]].update(record)
        collision={'component_boxes':23,'coordinated_samples':21,'coverage':coverage,'folded_bounds_gltf_xyz_m':contract['folded_bounds_gltf_xyz_m']}
    reports[name]={'status':'PASS','sha256':sha,'triangles':count,'primitives':primitives,'opaque_materials':len(doc['materials']),'bounds_gltf_xyz_m':bounds.tolist(),'continuous_motion_bounds_gltf_xyz_m':swept.tolist(),'continuous_max_origin_radius_m':radius,'conservative_origin_sphere_radius_m':math.ceil((radius+1e-6)*1000)/1000,'motion_part_envelopes':parts,'collision_verification':collision,'notes':'Swept extrema are analytic per transformed mesh vertex over each allowed rotation/translation interval. Moving roots are independent and do not nest; the union covers simultaneous allowed poses. Collision-contact tests remain bounded samples.'}
(out/'verification.json').write_text(json.dumps(reports,indent=2)+'\n');print(json.dumps({n:{k:r[k] for k in ('status','triangles','primitives','conservative_origin_sphere_radius_m')} for n,r in reports.items()},indent=2))
