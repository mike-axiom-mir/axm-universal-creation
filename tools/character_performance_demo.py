"""Regenerate two bodies from one performance template and observe exported poses.

PYTHONPATH=src python tools/character_performance_demo.py /tmp/uc-performance --plot
Matplotlib is optional and used only for a technical pose sheet, never compilation.
"""
from copy import deepcopy
import argparse
import json
from pathlib import Path

from axm_uc.character_motion import build_character_motion
from axm_uc.character_recipe import compile_character_recipe, publish_character_recipe
from axm_uc.game_pose_runtime import load_game_pose_glb

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('output', type=Path)
    parser.add_argument('--plot', action='store_true')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    source = json.loads((ROOT/'examples/character-motion/seedling-performance.json').read_text())['inputs']['recipe']
    tall = deepcopy(source)
    tall['name'] = 'Tall seedling, same performance construction'
    for part in tall['form']['parts']:
        part['scale'] = [1.25,1,1.3]
        part['translation'] = [v*s for v,s in zip(part.get('translation',[0,0,0]),[1.25,1,1.3])]
    outputs, receipt = [], {'shared_performance': source['performance'] == tall['performance'], 'bodies': []}
    for i, recipe in enumerate((source,tall)):
        target = args.output/f'body-{i+1}.glb'
        published = publish_character_recipe(target,recipe)
        compiled = compile_character_recipe(recipe)
        # Load published bytes again, not the compiler's intermediate geometry.
        asset = load_game_pose_glb(target)
        replay = build_character_motion(compiled['specification'],compiled['motion'])
        assert replay['body'] == target.read_bytes(), 'construction replay changed bytes'
        outputs.append((compiled,asset))
        receipt['bodies'].append({'file':target.name,'landmarks':compiled['performance']['landmarks'],
                                  'motion_validation':published['motion_validation'],
                                  'exact_replay':True})
    receipt['boundary'] = ('Decoded sample positions and rigid foot contacts. Plot is a technical vertex view; '
                           'no shaded-normal, continuous contact, physical balance or external-engine claim.')
    if args.plot:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        from mpl_toolkits.mplot3d.art3d import Poly3DCollection
        states = [('walk',0),('walk',.5),('walk',1),('walk',1.5),('reach',1)]
        fig = plt.figure(figsize=(16,9),facecolor='#101923')
        for row,(compiled,asset) in enumerate(outputs):
            for col,(clip,time) in enumerate(states):
                pose = asset.sample(clip,time,vertices=True)
                ax = fig.add_subplot(2,len(states),row*len(states)+col+1,projection='3d',facecolor='#101923')
                for part,mesh in zip(compiled['specification']['primitives'],pose['meshes']):
                    points,indices = mesh['positions'],part['indices']
                    faces = [[points[indices[k+j]] for j in range(3)] for k in range(0,len(indices),3)]
                    ax.add_collection3d(Poly3DCollection(faces,facecolor=part['material']['color'][:7],
                                                       edgecolor='#b7c4c0',linewidth=.12))
                ax.plot([-.55,.55],[0,0],[0,0],color='#6e8597',linewidth=.6)
                ax.plot([0,0],[-.3,.6],[0,0],color='#6e8597',linewidth=.6)
                ax.set(xlim=(-.65,.65),ylim=(-.3,.65),zlim=(0,2.4))
                ax.set_box_aspect((1.3,.95,2.4))
                ax.view_init(12,-40)
                ax.set_axis_off()
                ax.set_title(f'Body {row+1} / {clip} {time:g}s',color='#e2ebef',fontsize=10)
        fig.suptitle('UC body-fitted performance | one retained template, two proportions',color='white',fontsize=18,y=.96)
        fig.text(.5,.045,'Landmarks + segment weights + two-bone targets → exported GLB → decoded vertex poses',
                 ha='center',color='#b3c4d1',fontsize=11)
        fig.savefig(args.output/'performance-proof.png',dpi=120,facecolor=fig.get_facecolor())
        plt.close(fig)
    (args.output/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt,indent=2))


if __name__ == '__main__':
    main()
