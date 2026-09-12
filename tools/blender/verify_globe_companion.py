"""Fresh-import geometry and animation checks for the flying companion."""
import argparse,hashlib,json
from pathlib import Path
import bpy
import numpy as np
from verify_chaos_hero import document,reset,positions,action_set,find_action

def inspect(path,manifest):
    d=document(path);bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.scene.render.fps=30
    bpy.ops.import_scene.gltf(filepath=str(path));arm=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
    mesh=next(o for o in bpy.context.scene.objects if o.type=='MESH');reset(arm);rest=positions(mesh)
    mesh.data.calc_loop_triangles();tri=np.array([t.vertices[:] for t in mesh.data.loop_triangles]);a=rest[tri]
    deg=int((np.linalg.norm(np.cross(a[:,1]-a[:,0],a[:,2]-a[:,0]),axis=1)<1e-12).sum())
    bad=sum(not v.groups or abs(sum(g.weight for g in v.groups)-1)>1e-4 for v in mesh.data.vertices)
    gates={'one_skin':len(d.get('skins',[]))==1,'bone_contract':set(arm.data.bones.keys())=={b['name'] for b in manifest['bones']},
           'valid_triangles':deg==0,'weights_normalized':bad==0,'finite_uvs':bool(np.isfinite([x.uv[:] for x in mesh.data.uv_layers.active.data]).all()),
           'embedded_textures':all('bufferView' in x for x in d.get('images',[]))}
    rows=[]
    for clip in manifest['animations']:
        action=find_action(clip['name']);action_set(arm,action);start,end=action.frame_range;frames=[]
        for u in [0,.125,.25,.375,.5,.625,.75,.875,1]:
            f=start+(end-start)*u;bpy.context.scene.frame_set(int(f),subframe=f-int(f));frames.append(positions(mesh))
        motion=max(float(np.linalg.norm(x-frames[0],axis=1).max()) for x in frames[1:]);delta=float(np.linalg.norm(frames[-1]-frames[0],axis=1).max())
        rows.append({'name':clip['name'],'moves':motion>.001,'loop_matches':delta<.001 if clip['loop'] else True,'duration_matches':abs((end-start)/30-clip['seconds'])<.001,'endpoint_delta_m':delta})
    gates['animations']=all(all(r[k] for k in ['moves','loop_matches','duration_matches']) for r in rows)
    return {'path':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'pass':all(gates.values()),'gates':gates,'degenerate_triangles':deg,'clips':rows}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);a=p.parse_args();m=json.loads((a.directory/'companion-manifest.json').read_text())
    rows=[inspect(a.directory/x['path'],m) for x in m['exports'].values()];r={'pass':all(x['pass'] for x in rows),'artifacts':rows,'limits':'Numerical re-import/playback; not a target-game integration or visual quality score.'}
    (a.directory/'verification.json').write_text(json.dumps(r,indent=2)+'\n');print('COMPANION_VERIFIED',r['pass'])
    if not r['pass']:raise SystemExit(1)
