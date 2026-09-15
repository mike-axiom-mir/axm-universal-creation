"""Creation controls for a reusable charged surface, not a layer-editor UI.

A prompt interpreter or clickable control can call create_surface once. The
deterministic machine compiles its internal material/effect/composition graph.
"""
import argparse
import json
from pathlib import Path

from .game_material_styles import FAMILIES, FINISHES
from .parallel_create import SCHEMA, build, read

SURFACE = 'axm.surface-creation/v1'


def surface_catalog():
    return {'schema':SURFACE,'creations':['charged-surface'], 'families':list(FAMILIES),
            'finishes':[f.name for f in FINISHES], 'controls':['name','seed','size','family','finish','color','effect_color','wear','charge'],
            'invocation':'create_surface(request, output); no manual task graph required',
            'outputs':['PNG','editable Studio project','original material maps','effect graph/SVG','portable source library'],
            'ai_required':False, 'truth':'One deterministic creation composition; not free-form prompt interpretation or a new human editor.'}


def compile_surface(request):
    if not isinstance(request,dict) or request.get('schema') != SURFACE or set(request)-{'schema','origin',*surface_catalog()['controls']}:
        raise ValueError('invalid surface creation controls')
    name = request.get('name','Charged salvage surface')
    if not isinstance(name,str) or not name.strip() or len(name)>100: raise ValueError('name requires 1..100 characters')
    size = request.get('size',256); seed = request.get('seed',1)
    if type(size) is not int or not 64<=size<=512: raise ValueError('size must be 64..512')
    if type(seed) is not int or not 0<=seed<=2147483647: raise ValueError('seed must be 0..2147483647')
    family = request.get('family','painted-metal'); finish = request.get('finish','realistic')
    if family not in FAMILIES or finish not in [f.name for f in FINISHES]: raise ValueError('unknown surface family/finish')
    wear = request.get('wear',.35); charge = request.get('charge',.8)
    if any(type(v) not in (float,int) or not 0<=v<=1 for v in (wear,charge)):
        raise ValueError('wear and charge must be in 0..1')
    origin = request.get('origin', {'author':'AXM','license':'CC0-1.0','source':'Original charged-surface deterministic composition'})
    tasks = []
    def task(id, dependencies, operation, **values):
        tasks.append({'id':id,'dependencies':dependencies,'request':{
            'operation':operation,'id':id,'name':name+' / '+id,'origin':origin,**values}})
    settings = {'family':family,'finish':finish,'size':size,'seed':seed,
                'layer':{'amount':wear}, 'protected_regions':[[.02,.02,.98,.09],[.02,.91,.98,.98]]}
    if 'color' in request: settings['color'] = request['color']
    task('material', [], 'create_material', settings=settings)
    task('arc', [], 'create_effect', settings={
        'name':name,'kind':'electric-arc','seed':seed,'canvas':{'width':size,'height':size},
        'topology':{'source':[.08,.18],'target':[.9,.78],'grid':48,'walkers':28,'spread':.13,'octaves':5,'roughness':.78},
        'guides':{'points':[[.38,.27],[.58,.68]],'strength':.65,'radius':.14},
        'realization':{'color':request.get('effect_color','#9deaff'),'background':None,
                       'core_width':max(.7,size/170),'glow_width':size/22,'glow_strength':.8}})
    project = {'schema':'axm.studio-composition-project/v1',
        'sources':{'paint':{'$asset':{'task':'material','key':'base_color'}},'charge':{'$asset':{'task':'arc','key':'image'}}},
        'recipe':{'schema':'axm.raster-composition/v1','canvas':{'width':size,'height':size},
                  'layers':[{'id':'paint','source_artifact_id':'paint'},
                            {'id':'charge','source_artifact_id':'charge','blend_mode':'screen','opacity':charge}]}}
    task('composed', ['material','arc'], 'compose_layers', project=project)
    task('finished', ['composed'], 'edit_layers', source={'$task':'composed'},
         edits=[{'op':'change','id':'paint','patch':{'filters':[{'type':'contrast','value':.12}]}}])
    return {'schema':SCHEMA,'tasks':tasks,'result':'finished'}


def create_surface(request, output, *, workers=4, timeout=120):
    return build(compile_surface(request), output, workers=workers, timeout=timeout)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('request',help='saved creation controls, or catalog')
    parser.add_argument('output',nargs='?')
    parser.add_argument('--workers',type=int,default=4)
    args = parser.parse_args(argv)
    if args.request == 'catalog': result = surface_catalog()
    else:
        if args.output is None: parser.error('output directory required')
        result = create_surface(read(Path(args.request)),args.output,workers=args.workers)
    print(json.dumps(result,allow_nan=False))
    return 0


if __name__ == '__main__': raise SystemExit(main())
