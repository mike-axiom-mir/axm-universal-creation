"""Source/fresh-import coordinated poses and exact component collision contracts."""
import argparse,hashlib,json,sys
from pathlib import Path
import bpy
sys.path.insert(0,str(Path(__file__).resolve().parent))
import axm_fortress_utilities as u

def box_record(label,meshes,pivot=None):
    inverse=pivot.matrix_world.inverted() if pivot else None
    points=[(inverse@o.matrix_world@v.co if inverse else o.matrix_world@v.co) for o in meshes for v in o.data.vertices]
    bb=u.gltf_bounds([[min(p[k] for p in points),max(p[k] for p in points)] for k in range(3)])
    return {'part':label,'bounds_gltf_xyz_m':bb,'game_box_local':{'x':sum(bb[0])/2,'z':sum(bb[2])/2,'w':bb[0][1]-bb[0][0],'d':bb[2][1]-bb[2][0],'bottom':max(0,bb[1][0]) if not pivot else bb[1][0],'h':bb[1][1]}}

def main():
    p=argparse.ArgumentParser();p.add_argument('--pack',required=True);p.add_argument('--only',choices=list(u.SPECS));args=p.parse_args(sys.argv[sys.argv.index('--')+1:]);pack=Path(args.pack).resolve()
    for name in u.SPECS:
        if args.only and name!=args.only:continue
        target=pack/name;manifest=json.loads((target/'manifest.json').read_text());report={'asset':name,'glb_sha256':hashlib.sha256((target/(name+'.glb')).read_bytes()).hexdigest(),'scope':'21 coordinated progress samples in source and fresh import; all moving roots progress together. Triangle crossings, not continuous collision certification.','stages':{}};contract=None
        for stage in ('source','fresh-import'):
            if stage=='source':bpy.ops.wm.open_mainfile(filepath=str(target/(name+'.blend')))
            else:bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(target/(name+'.glb')))
            root=bpy.data.objects[manifest['root']];meshes=[o for o in root.children_recursive if o.type=='MESH'];pivots={spec['part']:(bpy.data.objects[spec['part']],spec) for spec in manifest['motions']};rests={n:(o.location.copy(),o.rotation_euler.to_quaternion() if o.rotation_mode!='QUATERNION' else o.rotation_quaternion.copy()) for n,(o,spec) in pivots.items()}
            def owner(obj):
                while obj:
                    if obj.name in pivots:return obj.name
                    obj=obj.parent
                return None
            owners={o:owner(o) for o in meshes};rows=[];bpy.context.view_layer.update()
            if name=='borrowed-wall' and stage=='source':
                fixed=[];moving=[]
                for obj in root.children:
                    if obj.type=='EMPTY' and obj.name.startswith(('WallBay','EndSupport')):fixed.append(box_record(obj.name+'Fixed',[o for o in obj.children if o.type=='MESH']))
                for n,(obj,spec) in pivots.items():
                    record=box_record(n,[o for o in obj.children_recursive if o.type=='MESH']);record['node_local_bounds_gltf_xyz_m']=box_record(n,[o for o in obj.children_recursive if o.type=='MESH'],obj)['bounds_gltf_xyz_m'];record['rest_world_translation_gltf_m']=manifest['nodes'][n]['world_translation_gltf_m'];record['axis']='local Y';record['travel_m']=spec['travel_m'];moving.append(record)
                contract={'root':root.name,'units':'meters','up':'Y','forward':'+Z','glb_sha256':report['glb_sha256'],'deployed_bounds_gltf_xyz_m':manifest['bounds_gltf_xyz_m'],'fixed_boxes':fixed,'moving_tier_boxes':moving,'scope':'Conservative AABBs per fixed group and per moving tier. Add each node Y displacement to that moving box bottom and h; x/z/w/d stay fixed. Rotate these boxes with the deployed root or bound their rotated corners for axis-aligned world collision. Merged full-height boxes are available separately in the asset manifest.'}
            for i in range(21):
                fraction=i/20
                for n,(obj,spec) in pivots.items():u.b.animate(obj,spec,spec['samples'][-1]*fraction,*rests[n])
                bpy.context.view_layer.update();trees={o:u.a.tree(o) for o in meshes};hits=[]
                for j,left in enumerate(meshes):
                    for right in meshes[j+1:]:
                        if owners[left]==owners[right]:continue
                        overlap=trees[left].overlap(trees[right])
                        if overlap:hits.append({'left':left.name,'right':right.name,'pairs':len(overlap)})
                bb=u.gltf_bounds(u.mesh_bounds(meshes));rows.append({'progress':fraction,'bounds_gltf_xyz_m':bb,'intersections':hits})
                if contract and stage=='source' and i==20:
                    contract['folded_bounds_gltf_xyz_m']=bb
                    for record in contract['moving_tier_boxes']:
                        obj=pivots[record['part']][0];record['folded_game_box_local']=box_record(obj.name,[o for o in obj.children_recursive if o.type=='MESH'])['game_box_local']
                if hits:print(json.dumps({'asset':name,'stage':stage,'progress':fraction,'hits':hits[:3]}),flush=True)
            report['stages'][stage]=rows
        (target/'combined-state-checks.json').write_text(json.dumps(report,indent=2))
        if contract:(target/'collision-contract.json').write_text(json.dumps(contract,indent=2))
        assert all(not r['intersections'] for rows in report['stages'].values() for r in rows),(name,'combined motion crossing')
        print(json.dumps({'asset':name,'combined_pose_checks':'PASS','samples_per_stage':21}),flush=True)

if __name__=='__main__':main()
