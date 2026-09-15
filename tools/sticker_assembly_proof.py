"""Original Rivetwing dispatch beacon: nested reusable animated mechanical parts."""
import json
import math
from pathlib import Path
import struct
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from axm_stickers import Registry,instance
from axm_stickers.assembly import save_assembly,library_bundle,import_library
from axm_uc.sticker_create import execute
from axm_uc.sticker_assembly import export_assembly
from axm_uc.game_pose_runtime import GamePoseAsset,_parse

ORIGIN={'author':'AXM','license':'CC0-1.0','source':'Original Rivetwing dispatch beacon, tools/sticker_assembly_proof.py'}

def frame(x=0,y=0,z=0,a=0):
    c,s=math.cos(a),math.sin(a)
    return [c,-s,0,x,s,c,0,y,0,0,1,z,0,0,0,1]

def make(root):
    root=Path(root);root.mkdir(parents=True,exist_ok=False)
    requests=[]
    with Registry(root/'stickers.sqlite') as r:
        def part(id,size,color,metal=.6,kind='box'):
            spec={'schema':'axm.procedural-3d/v0.1','name':id,'primitives':[
                {'id':id,'type':kind,'size':size,'translation':[0,0,0],
                 'material':{'color':color,'metallic':metal,'roughness':.58}}]}
            req={'operation':'create_3d','id':id,'name':id,'socket':'mount','spec':spec,**ORIGIN}
            requests.append(req);return execute(r,req,root)
        rivet=part('steel-rivet',[.055,.055,.07],'#C2CED1',.85)
        tooth=part('brass-tooth',[.07,.13,.10],'#D9A24A')
        feather=part('wing-feather',[.13,.63,.08],'#406D7C')
        stripe=part('feather-tip',[.13,.08,.095],'#C6A25C')
        plate=part('body-shell',[1.38,1.5,.46],'#B8782C')
        inset=part('body-inset',[1.17,1.27,.12],'#233C50')
        visor=part('brow',[.57,.13,.10],'#D4A34B')
        hub=part('gear-hub',[.42,.42,.1],'#304453')
        eye=part('signal-eye',[.18,.25,.12],'#40D8CF',.1)
        beak=part('beak',[.27,.35,.29],'#C36A38',.4,kind='pyramid')
        leg=part('leg',[.14,.48,.17],'#526679')
        boot=part('boot',[.42,.16,.36],'#293843',.2)
        antenna=part('antenna',[.045,.50,.06],'#87979F')
        lamp=part('antenna-lamp',[.15,.15,.12],'#D25138',.1)
        label=part('mail-slot',[.65,.08,.09],'#172B38',.2)
        def c(d,id,x=0,y=0,z=0,a=0,motion=None):
            return {'instance':instance(d,id),'target':{'space':'3d','socket':'mount','frame':frame(x,y,z,a)},'motion':motion,'clip':None}
        def group(id,children):
            req={'operation':'save_assembly','id':id,'name':id,'children':children,'origin':ORIGIN}
            requests.append(req);return execute(r,req,root)
        gearparts=[c(hub,'hub'),c(eye,'signal',z=.09)]
        for i in range(24):
            a=i*math.tau/24
            gearparts += [c(tooth,'tooth'+str(i),.30*math.cos(a),.30*math.sin(a),a=a-math.pi/2),
                          c(rivet,'pin'+str(i),.22*math.cos(a),.22*math.sin(a),.1)]
        gear=group('signal-gear',gearparts)
        wings=[]
        for side in (-1,1):
            parts=[]
            for i in range(12):
                x=side*(.15+i*.07);y=-.1-i*.035;a=-side*.25
                parts.extend([c(feather,'fin'+str(i),x,y,0,a),c(stripe,'tip'+str(i),x-side*.066,y-.27,.015,a)])
                for j in range(3):parts.append(c(rivet,f'pin-{i}-{j}',x+side*(j-1)*.037,y+.17-j*.11,.065))
            wings.append(group('wing-left' if side<0 else 'wing-right',parts))
        children=[c(plate,'shell'),c(inset,'inset',z=.28),c(beak,'beak',y=.08,z=.42),c(label,'slot',y=-.35,z=.36)]
        for i in range(40):
            a=i*math.tau/40
            # Rectangular rim with evenly distributed sides.
            side=i//10;t=(i%10)/9
            x,y=[(-.64+1.28*t,.68),(.64,.68-1.36*t),(.64-1.28*t,-.68),(-.64,-.68+1.36*t)][side]
            children.append(c(rivet,'rim'+str(i),x,y,.28))
        for side in (-1,1):
            # Return to exact starting orientation; a readable half-turn and settle.
            trace=[{'time':i/8,'frame':frame(side*.36,.35,.38,side*.6*(0 if i in (0,16) else math.sin(i/8*math.pi)))} for i in range(17)]
            children.append(c(gear,'gear-left' if side<0 else 'gear-right',side*.36,.35,.38,motion=trace))
            children.append(c(visor,'brow'+str(side),side*.38,.71,.49,a=side*.18))
            trace=[{'time':i/8,'frame':frame(side*.71,.17,0,side*.28*(0 if i in (0,16) else math.sin(i/8*math.pi)))} for i in range(17)]
            children.append(c(wings[0 if side<0 else 1],'wing-left' if side<0 else 'wing-right',side*.71,.17,0,motion=trace))
            children.extend([c(leg,'leg'+str(side),side*.43,-.96),c(boot,'boot'+str(side),side*.43,-1.22,.08)])
        children.extend([c(antenna,'antenna',.38,1.04,0,a=-.15),c(lamp,'lamp',.42,1.29,0)])
        machine=group('rivetwing',children)
        start=time.perf_counter();result=export_assembly(r,'rivetwing',1);elapsed=time.perf_counter()-start
        (root/'rivetwing.glb').write_bytes(result['body'])
        bundle=library_bundle(r,'rivetwing',1)
        (root/'rivetwing-library.json').write_text(json.dumps(bundle,indent=2)+'\n')
        (root/'create-requests.json').write_text(json.dumps(requests,indent=2)+'\n')
        (root/'assembly.json').write_text(json.dumps(machine,indent=2)+'\n')
        with Registry(root/'reimport.sqlite') as other:
            import_library(other,bundle)
            replay=export_assembly(other,'rivetwing',1)
            assert replay['body']==result['body']
        asset=GamePoseAsset(result['body']);poses=[asset.sample('AssemblyMotion',t,vertices=True) for t in (0,.5,1.5,2)]
        assert poses[0]['world_matrices']==poses[-1]['world_matrices']
        assert poses[0]['world_matrices']!=poses[1]['world_matrices']
        receipt=result['receipt']|{'build_seconds':elapsed,'portable_rebuild_byte_exact':True,
            'loop_world_matrices_exact':True,'sampled_frames':[0,.5,1.5,2],
            'limits':'Original assembly proof; offline geometry inspection, no continuous engine playback or physics acceptance.'}
        (root/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
        (root/'README.md').write_text('''# Rivetwing dispatch beacon

Original reusable rigid 3D parts, saved subassemblies and named AssemblyMotion.
`rivetwing.glb` is the actual animated realization. `assembly.json`, the portable
library and `create-requests.json` retain exact editable source and every part.
Run each request through `axm_uc.sticker_create.execute(registry, request, root)`
or write a single request file and call `axm-sticker-create DB REQUEST.json`.
No fabric repository, service or AI is required by UC. Geometry is shared across
instances; this is not a skin, cloth simulation, collision or LOD proof.
''')
        return {k:v for k,v in receipt.items() if k!='mappings'}

def preview(root):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    root=Path(root);body=(root/'rivetwing.glb').read_bytes();asset=GamePoseAsset(body);doc,raw=_parse(body)
    fig=plt.figure(figsize=(14,6),facecolor='#101B29')
    for k,t in enumerate((0,.5,1.5),1):
        ax=fig.add_subplot(1,3,k,projection='3d');triangles=[];colors=[]
        for m in asset.sample('AssemblyMotion',t,vertices=True)['meshes']:
            p=doc['meshes'][doc['nodes'][m['node']]['mesh']]['primitives'][m['primitive']]
            a=doc['accessors'][p['indices']];v=doc['bufferViews'][a['bufferView']]
            ids=struct.unpack_from('<'+{5123:'H',5125:'I'}[a['componentType']]*a['count'],raw,v.get('byteOffset',0)+a.get('byteOffset',0))
            color=doc['materials'][p['material']]['pbrMetallicRoughness']['baseColorFactor']
            for j in range(0,len(ids),3):triangles.append([m['positions'][i] for i in ids[j:j+3]]);colors.append(color)
        ax.add_collection3d(Poly3DCollection(triangles,facecolors=colors,edgecolors='#172330',linewidths=.15))
        ax.set(xlim=(-1.9,1.9),ylim=(-1.55,1.65),zlim=(-.5,.8));ax.set_box_aspect((3.8,3.2,1.3))
        ax.view_init(elev=74,azim=-78);ax.set_axis_off();ax.set_facecolor('#101B29')
        ax.set_title(f'ASSEMBLY MOTION / {t:.1f}s',color='#C7DAE5')
    fig.suptitle('RIVETWING / SAVED PARTS → MOVING SUBASSEMBLIES → REUSABLE CREATURE',color='white',fontsize=14)
    fig.text(.5,.08,'Actual exported GLB geometry • shared meshes • exact portable rebuild • offline flat-colour inspection',ha='center',color='#AFBFCE')
    fig.tight_layout(rect=(0,.12,1,.92));fig.savefig(root/'rivetwing.png',dpi=140,facecolor=fig.get_facecolor());plt.close(fig)

if __name__=='__main__':
    if sys.argv[1]=='preview':preview(sys.argv[2])
    else:print(json.dumps(make(sys.argv[1]),indent=2))
