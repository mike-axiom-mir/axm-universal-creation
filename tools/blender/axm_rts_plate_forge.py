"""Execute bounded authored plate recipes with retained source and GLB evidence."""
import argparse,hashlib,json,sys
from pathlib import Path
import bpy
from mathutils import Vector
from axm_blender_forge import select_only,export_glb
from axm_rts_workshop import materials,convert_and_batch,clean_mesh,setup_render,point
from axm_salvage_construction import physically_scaled_uv
from axm_salvage_surfaces import solid
import axm_rts_plate_architecture as architecture
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from axm_uc.rts_foundry import catalog
from verify_rts_batch import verify
SOURCE_HASHES={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),Path(architecture.__file__),*[Path(__file__).with_name(n) for n in ['axm_rts_vehicle_forge.py','axm_blender_forge.py','axm_rts_workshop.py','axm_salvage_construction.py','axm_salvage_surfaces.py']]]}


def build(a,out,resolution):
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    bpy.data.orphans_purge(do_recursive=True)
    key=a['id'];m=materials(out,Path('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'))
    m['window']=solid('smoked glass','#344f54',metal=.15,rough=.22)
    m['skin']=solid('warm skin','#b38c70',rough=.73)
    m['cloth']=solid('olive clothing','#616650',rough=.95)
    m['cyan']=solid('anomaly turquoise','#39d8dd',rough=.25,emission=3)
    family=a['family'];fn={'buildings':'building','industry':'industry','defenses':'defense','world':'world','crew':'crew','equipment':'equipment','utilities':'utility'}[family]
    getattr(architecture,fn)(key,m)
    physically_scaled_uv([o for o in bpy.context.scene.objects if o.type=='MESH'])
    bpy.ops.wm.save_as_mainfile(filepath=str(out/(key+'.blend')))
    batches=convert_and_batch();export_glb(out/(key+'.glb'),batches)
    for ob in batches:
        if len(ob.data.polygons)>20:
            mod=ob.modifiers.new('Lower detail','DECIMATE');mod.ratio=.33;select_only([ob]);bpy.ops.object.modifier_apply(modifier=mod.name);clean_mesh(ob)
    export_glb(out/(key+'-lod1.glb'),batches)
    for o in list(bpy.data.objects):bpy.data.objects.remove(o,do_unlink=True)
    bpy.ops.import_scene.gltf(filepath=str(out/(key+'.glb')))
    meshes=[o for o in bpy.context.scene.objects if o.type=='MESH'];pts=[o.matrix_world@Vector(c) for o in meshes for c in o.bound_box]
    lo=Vector([min(p[j] for p in pts) for j in range(3)]);hi=Vector([max(p[j] for p in pts) for j in range(3)]);center=(lo+hi)/2
    cam=setup_render(resolution,24);cam.location=center+Vector((7,-11,6));point(cam,center);cam.data.ortho_scale=max(hi-lo)*1.48
    bpy.context.scene.render.filepath=str(out/(key+'.png'));bpy.ops.render.render(write_still=True)
    evidence={suffix:verify(out/(key+suffix+'.glb')) for suffix in ['', '-lod1']};assert evidence['-lod1']['triangles']<evidence['']['triangles']
    (out/'verification.json').write_text(json.dumps({'asset':key,'family':family,'source_sha256':SOURCE_HASHES,'geometry':evidence,'scope':'Authored reconstruction from named plate cell. Fresh-import still. Static geometry; hidden surfaces inferred. No exact visual equivalence, animation, collision or target RTS certification.'},indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--families',nargs='+',required=True);p.add_argument('--only',nargs='+');p.add_argument('--resolution',type=int,default=900);args=p.parse_args()
    if args.output.exists():raise SystemExit('Use a new destination')
    assets=[a for a in catalog()['assets'] if a['family'] in args.families and a['id']!='improvised-workshop' and (not args.only or a['id'] in args.only)]
    if not assets:raise SystemExit('No matching assets')
    for i,a in enumerate(assets):
        out=args.output/a['id'];out.mkdir(parents=True);print('BUILD',i+1,len(assets),a['id'],flush=True);build(a,out,args.resolution)
