"""Rebuild five contact-sensitive assets; runtime pose/contact admission is separate."""
import argparse,json,sys
from pathlib import Path
import bpy
sys.path.insert(0,str(Path(__file__).resolve().parent))
import axm_fortress_pack as f
import axm_fortress_detail as d
import axm_fortress_weapons as w
import axm_fortress_enemies as e
import axm_fortress_defender as s

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True)
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:]);out=Path(args.output).resolve();out.mkdir(parents=True,exist_ok=False);rows=[]
    for name,builder in [('rebounder',d.rebounder),('relay-rifle',w.relay),('pinball-cannon',w.pinball),('breacher',e.breacher)]:
        bpy.ops.wm.read_factory_settings(use_empty=True);d.materials()
        if name in ('relay-rifle','pinball-cannon'):f.M['violet']=f.material('violet',(.31,.045,.8),.1,1.8)
        if name=='breacher':f.M['red']=f.material('red',(.85,.018,.009),.1,2)
        built=builder();contract=built[1];bpy.context.view_layer.update();f.batch_static_meshes();before=d.bounds()
        target=out/name;target.mkdir();glb=target/(name+'.glb')
        bpy.ops.export_scene.gltf(filepath=str(glb),export_format='GLB',export_yup=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(target/(name+'.blend')))
        bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(glb));after=d.bounds()
        assert max(abs(before[i][j]-after[i][j]) for i in range(3) for j in range(2))<.00002
        assert all(bpy.data.objects.get(n) for n in contract)
        meshes=[o for o in bpy.context.scene.objects if o.type=='MESH'];triangles=0
        for o in meshes:o.data.calc_loop_triangles();triangles+=len(o.data.loop_triangles)
        rows.append({'asset':name,'triangles':triangles,'primitives':len(meshes),'bounds_blender_xyz':after,'nodes':contract})
        w.render_views(target)
    original_args=sys.argv.copy();sys.argv=['blender','--','--output',str(out/'defender')]
    try:s.main()
    finally:sys.argv=original_args
    rows.append({'asset':'defender',**json.loads((out/'defender/manifest.json').read_text())})
    (out/'manifest.json').write_text(json.dumps({'assets':rows,'scope':'Fresh imports and source rig checks. Requires separate full integrated pose/contact regression before admission.'},indent=2))
if __name__=='__main__':main()
