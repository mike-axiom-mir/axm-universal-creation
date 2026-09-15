"""One creation request -> reusable surface -> further ordinary Studio editing."""
import copy
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from axm_uc.surface_creation import create_surface, SURFACE
from axm_uc.studio_compositor import compose_studio_project, edit_studio_layers
from axm_uc.game_material_bridge import load_material_bundle
from axm_uc.creative_tasks import export_creative
from axm_stickers import Registry
from axm_stickers.assembly import import_library


def make(destination):
    root = Path(destination); root.mkdir(parents=True,exist_ok=False)
    controls = {'schema':SURFACE,'name':'Stormpost coil housing','size':256,'seed':41,
                'family':'painted-metal','finish':'comic-salvage','color':[40,78,88],
                'effect_color':'#b5eeff','wear':.32,'charge':.95}
    (root/'creation.json').write_text(json.dumps(controls,indent=2)+'\n')
    result = create_surface(controls,root/'created',workers=4)
    folder = root/'created'
    body = (folder/'asset.png').read_bytes()
    project = json.loads((folder/'studio-project.json').read_text())
    assert compose_studio_project(project,folder)['png'] == body
    original = copy.deepcopy(project)
    # Demonstrate a human tool's next edit using existing Studio, outside the graph.
    edited = edit_studio_layers(project,[{'op':'change','id':'charge','patch':{'opacity':.25}}])
    later = compose_studio_project(edited,folder)
    assert project == original and later['png'] != body
    (folder/'studio-edited-project.json').write_text(json.dumps(edited,indent=2)+'\n')
    (folder/'studio-edited.png').write_bytes(later['png'])
    entries = json.loads((folder/'source-index.json').read_text())
    material = next(e for e in entries if e['operation']=='create_material')
    validated = load_material_bundle(folder/material['folder'])
    arc = next(e for e in entries if e['operation']=='create_effect')
    graph = json.loads((folder/arc['folder']/'graph.json').read_text())
    with Registry(root/'restored.sqlite') as registry:
        bundle = json.loads((folder/'library.json').read_text()); import_library(registry,bundle)
        replay = root/'restored';replay.mkdir()
        export_creative(registry,registry.get('finished',1),replay)
        assert (replay/'asset.png').read_bytes()==body
    evidence = {'jobs':len(result['outputs']),'original_definitions':len(bundle['definitions']),
        'material_maps_verified':sorted(validated['pngs']), 'effect_edges':len(graph['edges']),
        'studio_replay_byte_exact':True,'portable_library_replay_byte_exact':True,
        'further_studio_edit_changes_pixels_and_preserves_source':True,
        'limits':'One generated surface, not new editor UI, free-form prompt interpretation, animated image or 3D projection.'}
    (root/'verification.json').write_text(json.dumps(evidence,indent=2)+'\n')
    (root/'README.md').write_text('''# Stormpost coil housing / reusable creation

The human-facing request is a creation choice and controls. The machine generates
and connects its internal tools. Run `axm-create-surface creation.json NEW_FOLDER`.
No manual task graph, AI account, online service or new editor is needed.

`created/asset.png`: finished surface for reuse in other creations.
`created/studio-project.json`: editable layered Studio project with captured PNGs.
`created/studio-edited-project.json`: an example further tool-based edit;
`created/studio-edited.png`: its separately saved result.
`created/sources/`: original material maps, effect topology/SVG and composition.
`created/source-index.json`: names and locations of those source assets.
`created/library.json`: complete portable immutable dependency closure.
`created/stickers.sqlite`: saved reusable outputs.

The original material maps retain their physical channel meanings. The composed
image adds an artistic arc overlay; it does not silently become a new physically
consistent PBR material. Apply/project it explicitly in a later 3D workflow.
PNG arc halos use bounded radial coverage; SVG retains its separate blur styling.
No live Studio UI interaction or third-party editor compatibility is claimed.
''')
    return evidence


def preview(destination):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    root=Path(destination); folder=root/'created'
    entries=json.loads((folder/'source-index.json').read_text())
    material=next(e for e in entries if e['operation']=='create_material')
    arc=next(e for e in entries if e['operation']=='create_effect')
    panels=[(folder/material['folder']/'base_color.png','Original painted surface'),
            (folder/arc['folder']/'image.png','Reusable electric path effect'),
            (folder/'asset.png','Machine-created composition'),
            (folder/'studio-edited.png','Further edit with Studio tools')]
    fig,axes=plt.subplots(1,4,figsize=(14,4.5),facecolor='#101b26')
    for ax,(path,title) in zip(axes,panels):
        ax.set_facecolor('#142633');ax.imshow(plt.imread(path));ax.axis('off');ax.set_title(title,color='#dce8ee',fontsize=11)
    fig.suptitle('STORMPOST / CREATE → REUSE → CONTINUE EDITING',color='white',fontsize=16)
    fig.text(.5,.06,'Actual generated pixels • editable layers • original PBR maps and path graph retained',ha='center',color='#b9cbd4')
    fig.tight_layout(rect=(0,.12,1,.9));fig.savefig(root/'creative-surface.png',dpi=140,facecolor=fig.get_facecolor());plt.close(fig)


if __name__=='__main__':
    if sys.argv[1]=='preview': preview(sys.argv[2])
    else: print(json.dumps(make(sys.argv[1]),indent=2))
