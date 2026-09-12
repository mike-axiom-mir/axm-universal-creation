"""Render family contact sheets from final GLBs, never source-only geometry."""
import argparse,json,math,sys
from pathlib import Path
import bpy
from mathutils import Vector, Matrix
from axm_rts_workshop import setup_render,point
from axm_salvage_surfaces import solid


def render(root,resolution=1400):
    report=json.loads((root/'batch-manifest.json').read_text());families={}
    for key,a in report['assets'].items():families.setdefault(a['family'],[]).append(key)
    folder=root/'previews';folder.mkdir(exist_ok=True)
    for family,ids in families.items():
        bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
        cols=min(4,len(ids));rows=math.ceil(len(ids)/cols)
        labelmat=solid('preview-label','#d9d7c5',rough=1,emission=.4)
        for i,key in enumerate(ids):
            before=set(bpy.data.objects)
            bpy.ops.import_scene.gltf(filepath=str(root/'assets'/key/(key+'.glb')))
            objects=list(set(bpy.data.objects)-before)
            meshes=[o for o in objects if o.type=='MESH']
            bpy.context.scene.frame_set(0);bpy.context.view_layer.update()
            corners=[o.matrix_world@Vector(c) for o in meshes for c in o.bound_box]
            lo=Vector(tuple(min(p[j] for p in corners) for j in range(3)));hi=Vector(tuple(max(p[j] for p in corners) for j in range(3)))
            scale=2.3/max(hi-lo);center=Vector(((lo.x+hi.x)/2,(lo.y+hi.y)/2,lo.z))
            x=(i%cols-(cols-1)/2)*3.2;y=((rows-1)/2-i//cols)*5.2
            parent=bpy.data.objects.new('REVIEW '+key,None);bpy.context.collection.objects.link(parent)
            for o in objects:
                if o.parent is None:o.parent=parent
            parent.scale=(scale,)*3;parent.rotation_euler.z=math.radians(-25)
            parent.location=Vector((x,y,.02))-(Matrix.Rotation(math.radians(-25),3,'Z')@center)*scale
            curve=bpy.data.curves.new('label','FONT');curve.body=key.replace('-',' ');curve.align_x='CENTER';curve.size=.14;curve.extrude=0;curve.materials.append(labelmat)
            ob=bpy.data.objects.new('REVIEW label',curve);bpy.context.collection.objects.link(ob);ob.location=(x,y-1.70,.10);ob.rotation_euler.x=math.radians(56)
        cam=setup_render(resolution,24);cam.location=(0,-21,14);point(cam,(0,0,.3));cam.data.ortho_scale=max(cols*3.35,rows*4.4)+1
        for lamp in bpy.context.scene.objects:
            if lamp.type=='LIGHT' and lamp.data.type=='AREA':
                lamp.location*=2;lamp.data.energy*=4;lamp.data.size*=2;point(lamp,(0,0,.5))
        bpy.context.scene.render.filepath=str(folder/(family+'.png'));bpy.ops.render.render(write_still=True)
        print('RENDERED',family,flush=True)
    (folder/'render-receipt.json').write_text(json.dumps({'source':'Fresh imports of each delivered near GLB','families':families,'renderer':'Blender Cycles CPU','scope':'Static review; no runtime gameplay or animation playback claim.'},indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('--resolution',type=int,default=1400);args=p.parse_args();render(args.root,args.resolution)
