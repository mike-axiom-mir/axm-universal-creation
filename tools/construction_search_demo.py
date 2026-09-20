"""Run measured headless construction searches and render actual decoded output.

PYTHONPATH=src python tools/construction_search_demo.py /tmp/uc-search-proof --plot
Matplotlib is an optional diagnostic dependency; UC search itself is stdlib-only.
"""
from copy import deepcopy
import argparse
import json
from pathlib import Path
import platform
import time

from axm_uc.character_controller import CharacterController
from axm_uc.construction_search import publish_search, search_construction
from axm_uc.form_pattern import compile_form_pattern
from axm_uc.game_pose_runtime import load_game_pose_glb, GamePoseAsset
from axm_uc.procedural_3d import build_glb

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('output',type=Path)
    parser.add_argument('--plot',action='store_true')
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=False)
    receipt={'python_version':platform.python_version(),'runs':[],'boundary':
             'Measured on this host, not a hardware-independent speed claim. Plots show decoded vertices, not material/normal or external-engine verification.'}
    runs={}
    for name in ('vessel','broader-walker','deformation-repair'):
        request=json.loads((ROOT/f'examples/construction-search/{name}.json').read_text())
        contract=request['inputs']['search']
        begin=time.perf_counter()
        publish_search(args.output/name,contract)
        elapsed=time.perf_counter()-begin
        report=json.loads((args.output/name/'search.json').read_text())
        if report['status']!='CRITERIA_MET':
            raise RuntimeError(f'{name} did not meet its declared checks: {report["status"]}')
        warm=deepcopy(contract)
        warm['warm_starts']=[report['growth_candidate']['warm_start']]
        begin=time.perf_counter()
        reuse=search_construction(warm)
        warm_elapsed=time.perf_counter()-begin
        (args.output/name/'reuse.json').write_text(json.dumps(reuse,indent=2)+'\n')
        runs[name]=(contract,report)
        receipt['runs'].append({'name':name,'status':report['status'],'counts':report['counts'],
                                'elapsed_seconds':elapsed,'reuse_counts':reuse['counts'],
                                'reuse_elapsed_seconds':warm_elapsed,'selected':report['selected']['settings'],
                                'metrics':report['selected']['metrics']})
    # Inspect the published selected GLB once more through its own decoder.
    for name,(_,report) in runs.items():
        assert load_game_pose_glb(args.output/name/'winner.glb').source_sha256==report['publication']['sha256']
    if args.plot:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        from mpl_toolkits.mplot3d.art3d import Poly3DCollection

        fig=plt.figure(figsize=(14,10),facecolor='#101923')
        def draw(index,spec,pose,title,*,height=1.9,limits=None):
            ax=fig.add_subplot(2,3,index,projection='3d',facecolor='#101923')
            for part,mesh in zip(spec['primitives'],pose['meshes']):
                p,ids=mesh['positions'],part['indices']
                faces=[[p[v] for v in ids[k:k+3]] for k in range(0,len(ids),3)]
                ax.add_collection3d(Poly3DCollection(faces,facecolor=part['material']['color'][:7],
                                                     edgecolor='#b9cac9',linewidth=.15))
            ax.set(xlim=(-.55,.55),ylim=(-.35,.85),zlim=(0,height))
            if limits:ax.set(**limits)
            ax.set_box_aspect((1.1,1.2,height));ax.view_init(13,-48)
            ax.set_axis_off();ax.set_title(title,color='#e6eef2',fontsize=11,pad=2)
            return ax
        contract,report=runs['vessel']
        for index,recipe,title in ((1,contract['recipe'],'Vessel / initial construction'),
                                    (2,report['selected']['recipe'],'Vessel / measured selection')):
            spec=compile_form_pattern(recipe)['specification']
            asset=GamePoseAsset(build_glb(spec)['body'])
            draw(index,spec,asset.sample(vertices=True),title,height=1.2,
                 limits={'ylim':(-.55,.55)})
        ax=fig.add_subplot(2,3,3,facecolor='#101923')
        ax.set_axis_off()
        lines=['HEADLESS SEARCH / OBSERVED']
        for row in receipt['runs']:
            lines += ['',row['name'].replace('-',' ').upper(),
                      f"{row['counts']['visited']} trials · {row['counts']['deep_validations']} deep checks",
                      f"{row['elapsed_seconds']:.3f}s here · reuse: {row['reuse_counts']['visited']} trial"]
        ax.text(.02,.9,'\n'.join(lines),transform=ax.transAxes,color='#d6e4ec',fontsize=12,va='top',linespacing=1.7)
        contract,report=runs['broader-walker']
        for index,recipe,title in ((4,contract['recipe'],'Walk / initial body and lift'),
                                    (5,report['selected']['recipe'],'Walk / selected body and lift')):
            c=CharacterController(recipe)
            draw(index,c.compiled['specification'],c.sample('walk',1.6,vertices=True),title)
        _,report=runs['deformation-repair']
        c=CharacterController(report['selected']['recipe'])
        draw(6,c.compiled['specification'],c.sample('walk',1.6,vertices=True),'Skin / measured field correction')
        fig.suptitle('UC intent-directed construction | search → verify → retain → reuse',color='white',fontsize=18,y=.97)
        fig.text(.5,.035,'Actual decoded GLB vertices and query-time IK · technical geometry evidence · no aesthetic score',
                 ha='center',color='#aebfce',fontsize=11)
        fig.subplots_adjust(left=.035,right=.97,top=.88,bottom=.09,wspace=.08,hspace=.2)
        fig.savefig(args.output/'UC_Headless_Search_Proof.png',dpi=130,facecolor=fig.get_facecolor())
        plt.close(fig)
    (args.output/'benchmark.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt,indent=2))


if __name__=='__main__':main()
