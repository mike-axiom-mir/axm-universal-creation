"""Create two bodies from one retained rig/clip and inspect actual GLB deformation.
Run: PYTHONPATH=src python tools/character_motion_demo.py /tmp/uc-motion-demo
Optional --plot adds a technical pose sheet (matplotlib required only for plotting).
"""
from copy import deepcopy
import argparse
import json
from pathlib import Path
from axm_uc.character_recipe import publish_character_recipe, compile_character_recipe
from axm_uc.game_pose_runtime import load_game_pose_glb

ROOT = Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser();parser.add_argument('output',type=Path);parser.add_argument('--plot',action='store_true');args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    request=json.loads((ROOT/'examples/character-motion/bonsai-wave.json').read_text())
    recipes=[request['inputs']['recipe'],deepcopy(request['inputs']['recipe'])]
    recipes[1]['name']='Broad bonsai, shared motion'
    recipes[1]['form']['parts'][0]['sections'][1]['radius']=[.48,.30]
    recipes[1]['form']['parts'][1]['radius']=[.12,.09,.04]
    outputs=[]
    for i,r in enumerate(recipes):
        path=args.output/f'body-{i+1}.glb';publish_character_recipe(path,r)
        asset=load_game_pose_glb(path)
        outputs.append({'path':str(path),'decoded':asset.describe(),'poses':[asset.sample('wave',t,vertices=True) for t in (0,.5,1)]})
    receipt={'shared_rig':recipes[0]['rig']==recipes[1]['rig'],'shared_clips':recipes[0]['animation']==recipes[1]['animation'],
             'outputs':[{'path':r['path'],'decoded':r['decoded']} for r in outputs],
             'boundary':'Offline decoded vertex deformation. Plot is a technical pose view, not a material or target-engine render.'}
    (args.output/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    if args.plot:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        from mpl_toolkits.mplot3d.art3d import Poly3DCollection
        fig=plt.figure(figsize=(12,8),facecolor='#101923')
        for row,(r,out) in enumerate(zip(recipes,outputs)):
            spec=compile_character_recipe(r)['specification']
            for col,pose in enumerate(out['poses']):
                ax=fig.add_subplot(2,3,row*3+col+1,projection='3d',facecolor='#101923')
                for part,mesh in zip(spec['primitives'],pose['meshes']):
                    p=mesh['positions'];ix=part['indices'];faces=[[p[ix[k+j]] for j in range(3)] for k in range(0,len(ix),3)]
                    ax.add_collection3d(Poly3DCollection(faces,facecolor=part['material']['color'][:7],edgecolor='#b1c0bf',linewidth=.12))
                ax.set(xlim=(-.9,.9),ylim=(-.6,.6),zlim=(0,1.8));ax.set_box_aspect((1.8,1.2,1.8));ax.view_init(18,-65)
                ax.set_axis_off();ax.set_title(f'Body {row+1} / {pose["time_s"]:g} seconds',color='white')
        fig.suptitle('UC retained character motion | same rig + clip, two freeform bodies',color='white',fontsize=16)
        fig.text(.5,.035,'Actual exported GLB vertices sampled by UC pose runtime | technical deformation view',ha='center',color='#a8b9c9')
        fig.savefig(args.output/'pose-proof.png',dpi=120,facecolor=fig.get_facecolor())
    print(json.dumps(receipt,indent=2))

if __name__=='__main__':main()
