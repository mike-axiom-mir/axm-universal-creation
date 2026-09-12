"""Independent exported-file checks: GLB structure, skin weights and playback.

Does not call the generating recipe or its pose functions. Samples freshly
imported clips, including every exported foot-contact frame for locomotion.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct

import bpy
import numpy as np


def document(path):
    raw=path.read_bytes()
    if len(raw)<20 or struct.unpack_from('<III',raw)!=(0x46546c67,2,len(raw)):
        raise ValueError('Malformed GLB header')
    size,kind=struct.unpack_from('<II',raw,12)
    if kind!=0x4e4f534a:raise ValueError('Missing JSON chunk')
    return json.loads(raw[20:20+size])


def reset(arm):
    arm.animation_data_create();arm.animation_data.action=None
    for track in arm.animation_data.nla_tracks:track.mute=True
    for b in arm.pose.bones:
        b.location=(0,0,0);b.rotation_quaternion=(1,0,0,0);b.rotation_euler=(0,0,0);b.scale=(1,1,1)
    bpy.context.view_layer.update()


def action_set(arm,action):
    reset(arm);arm.animation_data.action=action
    if hasattr(action,'slots') and action.slots:arm.animation_data.action_slot=action.slots[0]


def find_action(name):
    matches=[a for a in bpy.data.actions if a.name==name or a.name.startswith(name+'_')]
    if len(matches)!=1:raise ValueError(f'Expected one imported action for {name}: {[a.name for a in matches]}')
    return matches[0]


def positions(mesh):
    ob=mesh.evaluated_get(bpy.context.evaluated_depsgraph_get());data=ob.to_mesh()
    out=np.empty(len(data.vertices)*3,dtype=np.float32);data.vertices.foreach_get('co',out)
    out=out.reshape(-1,3);m=np.array(ob.matrix_world)
    out=out@m[:3,:3].T+m[:3,3];ob.to_mesh_clear()
    if not len(out) or not np.isfinite(out).all():raise ValueError('Empty or non-finite posed geometry')
    return out


def inspect(path,manifest):
    doc=document(path);bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps=30;bpy.ops.import_scene.gltf(filepath=str(path))
    arms=[o for o in bpy.context.scene.objects if o.type=='ARMATURE']
    if len(arms)!=1:raise ValueError('Expected exactly one exported skeleton')
    arm=arms[0];meshes=[o for o in bpy.context.scene.objects if o.type=='MESH' and any(m.type=='ARMATURE' for m in o.modifiers)]
    if len(meshes)!=1:raise ValueError('Expected one character skin mesh')
    mesh=meshes[0];reset(arm);rest=positions(mesh)
    mesh.data.calc_loop_triangles()
    triangles=np.array([t.vertices[:] for t in mesh.data.loop_triangles],dtype=np.int64)
    area2=np.linalg.norm(np.cross(rest[triangles[:,1]]-rest[triangles[:,0]],rest[triangles[:,2]]-rest[triangles[:,0]]),axis=1)
    degenerate=int((area2<1e-12).sum())
    uv=np.array([loop.uv[:] for loop in mesh.data.uv_layers.active.data])
    bones={r['name'] for r in manifest['bones']}
    bad=sum(not v.groups or abs(sum(g.weight for g in v.groups)-1)>1e-4 for v in mesh.data.vertices)
    gates={'one_skin':len(doc.get('skins',[]))==1,'skeleton_matches':set(arm.data.bones.keys())==bones,
           'no_degenerate_triangles':degenerate==0,'finite_uvs':bool(np.isfinite(uv).all()),
           'normalized_weights':bad==0,'finite_rest_vertices':bool(np.isfinite(rest).all()),
           'all_textures_embedded':all('bufferView' in i for i in doc.get('images',[])),
           'all_primitives_skinned':all('JOINTS_0' in p['attributes'] and 'WEIGHTS_0' in p['attributes'] for m in doc['meshes'] for p in m['primitives'])}
    for image in bpy.data.images:
        if image.source=='FILE' and image.packed_file:
            if not len(image.pixels):raise ValueError('Embedded image could not be decoded')
    soles={}
    for side in ['L','R']:
        g=mesh.vertex_groups['Foot.'+side]
        indices=[v.index for v in mesh.data.vertices if rest[v.index,2]<.026 and any(w.group==g.index and w.weight>.95 for w in v.groups)]
        if not indices:raise ValueError('Foot sole geometry is missing')
        soles[side]=np.array(indices)
    rows=[]
    for clip in manifest['animations']:
        action=find_action(clip['name'])
        action_set(arm,action);first,last=map(float,action.frame_range);samples=[]
        for u in [0,.2,.4,.6,.8,1]:
            f=first+(last-first)*u;bpy.context.scene.frame_set(int(f),subframe=f-int(f));samples.append(positions(mesh))
        motion=max(float(np.linalg.norm(v-samples[0],axis=1).max()) for v in samples[1:])
        endpoint=float(np.linalg.norm(samples[-1]-samples[0],axis=1).max())
        row={'name':clip['name'],'duration_s':(last-first)/30,'sampled_motion_m':motion,'endpoint_delta_m':endpoint,
             'minimum_sampled_z_m':min(float(v[:,2].min()) for v in samples),'moves_skin':motion>.001,
             'loop_closed':endpoint<.001 if clip['loop'] else None}
        if 'matching_controller_speed_m_s' in clip:
            maximum_height_error=0;frame_rows=[]
            for f in range(round(first),round(last)+1):
                bpy.context.scene.frame_set(f);v=positions(mesh);t=(f-first)/(last-first)
                feet={}
                for side,indices in soles.items():
                    z=float(v[indices,2].min());phase=(t+(0 if side=='L' else .5))%1
                    if phase<.5:maximum_height_error=max(maximum_height_error,abs(z-float(rest[indices,2].min())))
                    feet[side]={'sole_z':z,'stance':phase<.5}
                frame_rows.append({'frame':f,'feet':feet})
            row['maximum_stance_height_error_m']=maximum_height_error
            row['contact_frames']=frame_rows
        rows.append(row);print('ROUNDTRIP_CLIP',path.name,clip['name'],round(motion,4),round(endpoint,5),flush=True)
    gates.update({'all_clips_move_skin':all(r['moves_skin'] for r in rows),
                  'all_loop_endpoints_match':all(r['loop_closed'] is not False for r in rows),
                  'all_clip_durations_match':all(abs(r['duration_s']-c['seconds'])<.04 for r,c in zip(rows,manifest['animations'])),
                  'locomotion_ground_contact':all(r.get('maximum_stance_height_error_m',0)<.008 for r in rows),
                  'sampled_geometry_above_ground':all(r['minimum_sampled_z_m']>-.008 for r in rows)})
    return {'path':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'gates':gates,
            'pass':all(gates.values()),'bones':len(arm.data.bones),'vertices':len(rest),'degenerate_triangles':degenerate,
            'bounds_m':{'min':rest.min(axis=0).tolist(),'max':rest.max(axis=0).tolist()},'clips':rows,
            'limits':'Fresh Blender re-import and numerical playback. Visual collision and target-engine performance are separate judgments.'}


def main():
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);args=p.parse_args()
    out=args.directory;manifest=json.loads((out/'character-manifest.json').read_text())
    rows=[inspect(out/r['path'],manifest) for r in manifest['exports'].values()]
    result={'schema':'axm.hero-roundtrip/v1','pass':all(r['pass'] for r in rows),'artifacts':rows}
    (out/'roundtrip-verification.json').write_text(json.dumps(result,indent=2)+'\n')
    if not result['pass']:raise SystemExit('Export verification requires repair; inspect report.')
    print('ROUNDTRIP_PASS',flush=True)


if __name__=='__main__':main()
