"""Internal creative tools: materials, effect topology and editable compositions.

Creation controls compile these steps for people; machines/AI may also compose
the same explicit graph. No new editor UI or natural-language model is required.
"""
import base64
import copy
import hashlib
import json
import math
from pathlib import Path

from axm_stickers import digest, instance
from axm_stickers.assembly import CREATIVE, library_definitions
from .sticker_adapter import definition
from .game_material_styles import game_material_request, WearLayer, protected_regions_mask
from .procedural_effects import build_electric_arc, _svg
from .fabric_noise import png_bytes
from . import studio_compositor as studio

OPERATIONS = ('create_material', 'create_effect', 'compose_layers', 'edit_layers')


def encoded(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode('utf-8')


def raster_arc(result):
    """Bounded antialiased segment coverage; independent from SVG Gaussian glow.

    Preserve the original graph/SVG. PNG uses max coverage across shared edges
    to avoid bright segment joints. Its soft radial halo is not a light simulation.
    """
    recipe = result['recipe']; real = recipe['realization']
    w, h = recipe['canvas']['width'], recipe['canvas']['height']
    if w > 512 or h > 512: raise ValueError('effect raster requires dimensions <=512')
    alpha = [0.0] * (w*h); work = 0
    for edge in result['graph']['edges']:
        ax, ay = edge['a'][0]*w, edge['a'][1]*h
        bx, by = edge['b'][0]*w, edge['b'][1]*h
        weight = edge['intensity']; core = real['core_width']*(.55+.9*weight)/2
        halo = real['glow_width']*(.35+.65*weight)/2 if real['glow_strength'] else 0
        radius = core + halo + 1
        x0, x1 = max(0, math.floor(min(ax,bx)-radius)), min(w, math.ceil(max(ax,bx)+radius))
        y0, y1 = max(0, math.floor(min(ay,by)-radius)), min(h, math.ceil(max(ay,by)+radius))
        work += (x1-x0)*(y1-y0)
        if work > 16*1024*1024: raise ValueError('effect raster work budget exceeded')
        dx, dy = bx-ax, by-ay; length = dx*dx+dy*dy
        for y in range(y0,y1):
            for x in range(x0,x1):
                t = max(0, min(1, ((x+.5-ax)*dx+(y+.5-ay)*dy)/length)) if length else 0
                distance = math.hypot(x+.5-ax-t*dx, y+.5-ay-t*dy)
                coverage = max(0, min(1, core+.5-distance))*(.35+.65*weight)
                if halo: coverage = max(coverage, max(0, 1-distance/(core+halo))**2*real['glow_strength']*.65)
                at = y*w+x; alpha[at] = max(alpha[at], coverage)
    color = bytes.fromhex(real['color'][1:]); background = real['background']
    pixels = bytearray()
    for a in alpha:
        if background:
            bg = bytes.fromhex(background[1:])
            pixels.extend(round(c*a+b*(1-a)) for c,b in zip(color,bg)); pixels.append(255)
        else:
            pixels.extend(color if a else bytes(3)); pixels.append(round(a*255))
    return png_bytes(w,h,4,bytes(pixels)), work


def _source(ref, dependencies, key=True):
    marker = '$asset' if key else '$task'
    if not isinstance(ref, dict) or set(ref) != {marker}: raise ValueError('expected typed dependency reference')
    value = ref[marker]
    if key:
        if not isinstance(value, dict) or set(value) != {'task','key'}: raise ValueError('asset reference requires task and key')
        task = value['task']
    else: task = value
    if not isinstance(task, str) or task not in dependencies: raise ValueError('unknown declared dependency')
    d = dependencies[task]
    if d['adapter'] != CREATIVE: raise ValueError('dependency requires creative-task output')
    if key:
        name = value['key']
        if not isinstance(name,str) or d['recipe']['outputs'].get(name) != 'image/png':
            raise ValueError('layer input must name a declared PNG output')
        return d, name
    return d


def execute_creative(registry, request, root, dependencies):
    request = copy.deepcopy(request); root = Path(root)
    operation = request.get('operation')
    fields = {'create_material': {'settings'}, 'create_effect': {'settings'},
              'compose_layers': {'project'}, 'edit_layers': {'source','edits'}}
    common = {'operation','id','name','origin','version','tags'}
    if operation not in fields or set(request)-common-fields[operation] or not {'id','name','origin'} <= set(request):
        raise ValueError('invalid creative task request')
    bodies = {}; outputs = {}; extra = {}; project = None
    def put(key, body, media):
        if not isinstance(body, bytes): raise ValueError('creative output must be bytes')
        bodies[key] = body; outputs[key] = media
    if operation == 'create_material':
        settings = dict(request['settings']); layer = settings.pop('layer', None)
        regions = settings.pop('protected_regions', None)
        allowed = {'family','size','seed','finish','color'}
        if set(settings)-allowed: raise ValueError('unknown material controls')
        if layer is not None: settings['layer'] = WearLayer(**layer)
        if regions is not None:
            settings['protected_mask'] = protected_regions_mask(settings.get('size',128),regions)
            settings['protected_mask_source'] = 'authored normalized rectangles'
        material = game_material_request('unused', **settings)['inputs']
        manifest = json.loads(material['text_files']['game-material.json'])
        put('material', encoded(manifest), 'application/json')
        for name, entry in manifest['maps'].items():
            put(name, base64.b64decode(material['binary_files'][entry['file']]['content'],validate=True), 'image/png')
        primary = 'base_color'
    elif operation == 'create_effect':
        result = build_electric_arc(request['settings'])
        body, work = raster_arc(result)
        put('image', body, 'image/png'); put('graph', encoded(result['graph']), 'application/json')
        put('svg', _svg(result).encode(), 'image/svg+xml'); put('effect_recipe', encoded(result['recipe']), 'application/json')
        extra['raster_pixel_visits'] = work; primary = 'image'
    else:
        if operation == 'compose_layers':
            project = copy.deepcopy(request['project'])
            if not isinstance(project,dict) or set(project) != {'schema','recipe','sources'} or not isinstance(project['sources'],dict):
                raise ValueError('invalid composition project')
            source_bytes = {}
            for name, ref in project['sources'].items():
                d, key = _source(ref, dependencies)
                source_bytes[name] = registry.asset(d['assets'][key])
        else:
            d = _source(request['source'], dependencies, False)
            if 'project' not in d['recipe']: raise ValueError('layer editing requires a saved composition')
            project = studio.edit_studio_layers(d['recipe']['project'], request['edits'])
            source_bytes = {name: registry.asset(d['assets']['input.'+name]) for name in project['sources']}
        # Only exact completed PNG outputs become local files; never arbitrary paths.
        for i, (name, body) in enumerate(source_bytes.items()):
            filename = f'input-{i}.png'; (root/filename).write_bytes(body)
            project['sources'][name] = filename
            put('input.'+name, body, 'image/png')
        rendered = studio.compose_studio_project(project, root)
        put('image', rendered['png'], 'image/png'); put('project', encoded(project), 'application/json')
        extra['composition'] = rendered['receipt']; primary = 'image'
    put('request', encoded(request), 'application/json')
    recipe = {'dependencies': [instance(d,'dependency')['sticker'] for d in dependencies.values()],
              'outputs': outputs, 'primary': primary, 'operation': operation, 'evidence': extra}
    if project is not None: recipe['project'] = project
    origin = request['origin']
    if not isinstance(origin,dict) or set(origin) != {'author','license','source'}: raise ValueError('origin requires author/license/source')
    d = definition(request['id'], request['name'], CREATIVE,
        {'space':'2d','socket':'surface','anchor':[0,0]}, recipe,
        {key:hashlib.sha256(body).hexdigest() for key,body in bodies.items()},
        ver=request.get('version',1), tags=request.get('tags',[]), **origin)
    library_definitions(registry,d)  # Validate all retained dependencies before save.
    registry.register(d,{hashlib.sha256(body).hexdigest():body for body in bodies.values()})
    return d


def export_creative(registry, d, destination):
    """Publish original named outputs; PNG is a derivative of retained source."""
    if d['adapter'] != CREATIVE: raise ValueError('unsupported creative output')
    extensions = {'image/png':'.png','image/svg+xml':'.svg','application/json':'.json'}
    outputs = d['recipe']['outputs']; primary = d['recipe']['primary']
    if not isinstance(outputs,dict) or set(outputs) != set(d['assets']) or primary not in outputs:
        raise ValueError('invalid creative output manifest')
    exported = {}
    for key, media in outputs.items():
        if media not in extensions: raise ValueError('unknown creative output media')
        name = key+extensions[media]; body = registry.asset(d['assets'][key])
        (Path(destination)/name).write_bytes(body); exported[key] = name
    # Stable top-level realization name for the selected task.
    body = registry.asset(d['assets'][primary]); name = 'asset'+extensions[outputs[primary]]
    (Path(destination)/name).write_bytes(body)
    if 'project' in d['recipe']:
        replay = copy.deepcopy(d['recipe']['project'])
        replay['sources'] = {key:exported['input.'+key] for key in replay['sources']}
        (Path(destination)/'studio-project.json').write_bytes(encoded(replay))
    if d['recipe']['operation'] == 'create_material':
        (Path(destination)/'game-material.json').write_bytes(registry.asset(d['assets']['material']))
    return {'primary':name,'sha256':hashlib.sha256(body).hexdigest(), 'outputs':exported,
            'source_preserved':True, 'visual_approval':False,
            'limits':'Authored maps, path effects and encoded-sRGB layer composition; no 3D projection or physical lighting claim.'}


def export_creative_sources(registry, root, destination):
    """Openable source folders alongside the portable immutable library."""
    entries = []
    for i, d in enumerate(library_definitions(registry,root)):
        if digest(d) == digest(root) or d['adapter'] != CREATIVE: continue
        folder = Path(destination) / 'sources' / f'{i:03d}'
        folder.mkdir(parents=True)
        info = export_creative(registry,d,folder)
        entries.append({'sticker':instance(d,'source')['sticker'], 'folder':folder.relative_to(destination).as_posix(),
                        'operation':d['recipe']['operation'], 'outputs':info['outputs']})
    (Path(destination)/'source-index.json').write_bytes(encoded(entries))
    return entries
