"""Intent-directed finite construction search; no model, renderer or hidden clock.

The supplied intent is made executable by explicit controls and measurements.
Acceptance means the declared checks passed, never a probability of correctness.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import heapq
import json
import math
from pathlib import Path
import platform
import shutil

from .atom_novelty import classify_creator_atoms
from .character_controller import CharacterController
from .character_motion import fields, name, number, require, CharacterMotionError
from .character_recipe import CharacterRecipeError, compile_character_recipe
from .form_pattern import FormPatternError, compile_form_pattern
from .game_pose_runtime import GamePoseAsset
from .mesh_quality import _area3
from .procedural_3d import Procedural3DError, build_glb

SCHEMA = 'axm.construction-search/v0.1'
GEOMETRY_METRICS = {'extent_x_m', 'extent_y_m', 'extent_z_m', 'surface_area_m2', 'vertices', 'triangles'}
MOTION_METRICS = {'maximum_target_error_m', 'maximum_bend_degrees', 'minimum_area_ratio',
                  'maximum_edge_ratio', 'maximum_contact_slip_m', 'foot_penetration_m', 'peak_foot_lift_m'}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def _geometry(specification):
    parts = specification['primitives']
    points = [p for part in parts for p in part['positions']]
    require(len(points) <= 10000 and sum(len(p['indices']) for p in parts) <= 60000,
            'search supports at most 10000 vertices and 20000 triangles per candidate')
    metrics = {f'extent_{axis}_m': max(p[i] for p in points)-min(p[i] for p in points)
               for i,axis in enumerate('xyz')}
    metrics.update(vertices=len(points), triangles=sum(len(p['indices'])//3 for p in parts),
                   surface_area_m2=sum(_area3(*(part['positions'][v] for v in part['indices'][k:k+3]))
                                       for part in parts for k in range(0,len(part['indices']),3)))
    return metrics


def _locate(recipe, path):
    require(isinstance(path, list) and 2 <= len(path) <= 24, 'control paths need 2..24 components')
    node = recipe
    for token in path[:-1]:
        require((isinstance(node, dict) and isinstance(token, str) and token in node)
                or (isinstance(node, list) and type(token) is int and 0 <= token < len(node)),
                'control references a missing construction field')
        node = node[token]
    key = path[-1]
    require((isinstance(node, dict) and isinstance(key, str) and key in node)
            or (isinstance(node, list) and type(key) is int and 0 <= key < len(node)),
            'control references a missing construction field')
    return node, key


def _validate(raw):
    fields(raw, {'schema','intent','recipe','controls','criteria','budget'}, {'motion_probe','warm_starts'})
    require(raw['schema'] == SCHEMA, 'unsupported construction-search schema')
    require(isinstance(raw['intent'], str) and 0 < len(raw['intent'].strip()) <= 2000, 'search needs explicit intent')
    require(isinstance(raw['recipe'], dict), 'search recipe must be an object')
    character = raw['recipe'].get('schema') == 'axm.character-recipe/v0.1'
    require(character or raw['recipe'].get('schema') == 'axm.form-pattern/v0.1', 'search supports form and character recipes')
    require(len(canonical(raw).encode()) <= 2_000_000, 'search contract exceeds 2 MB')
    controls = raw['controls']
    require(isinstance(controls, list) and 1 <= len(controls) <= 8, 'search needs 1..8 controls')
    ids, paths = set(), []
    for control in controls:
        fields(control, {'id','paths','values'})
        cid = name(control['id'])
        require(cid not in ids, 'duplicate search control')
        ids.add(cid)
        require(isinstance(control['values'], list) and 1 <= len(control['values']) <= 33, 'control needs 1..33 options')
        require(len(set(canonical(v) for v in control['values'])) == len(control['values']), 'duplicate control options')
        require(isinstance(control['paths'], list) and 1 <= len(control['paths']) <= 64, 'control needs 1..64 paths')
        for path in control['paths']:
            _locate(raw['recipe'], path)
            require(path[0] in ({'form','performance'} if character else {'parts'}), 'only construction fields can be searched')
            require(not any(path[:min(len(path),len(p))] == p[:min(len(path),len(p))] for p in paths),
                    'control paths overlap')
            paths.append(path)
    criteria = raw['criteria']
    require(isinstance(criteria, list) and 1 <= len(criteria) <= 16, 'search needs 1..16 measured criteria')
    metrics = set()
    for criterion in criteria:
        fields(criterion, {'metric'}, {'min','max','scale'})
        metric = criterion['metric']
        require(isinstance(metric, str) and metric in GEOMETRY_METRICS | MOTION_METRICS
                and metric not in metrics, 'unknown or duplicate metric; unsupported intent must not be silently scored')
        metrics.add(metric)
        require('min' in criterion or 'max' in criterion, 'criterion needs min and/or max')
        low = number(criterion['min']) if 'min' in criterion else -math.inf
        high = number(criterion['max']) if 'max' in criterion else math.inf
        require(low <= high and number(criterion.get('scale',1)) > 0, 'invalid criterion bounds/scale')
    fields(raw['budget'], {'candidates','validations','validation_samples'})
    for key,low,high in (('candidates',1,256),('validations',1,32),('validation_samples',17,257)):
        value = raw['budget'][key]
        require(type(value) is int and low <= value <= high, f'invalid {key} budget')
    probe = raw.get('motion_probe')
    if probe is not None:
        fields(probe, {'clip','cycles','feet','up_axis','ground_height_m'})
        name(probe['clip'])
        require(character and isinstance(raw['recipe'].get('performance'),dict), 'motion search requires character performance')
        require(type(probe['cycles']) is int and 1 <= probe['cycles'] <= 4, 'probe needs 1..4 cycles')
        require(type(probe['up_axis']) is int and probe['up_axis'] in (0,1,2), 'invalid probe up axis')
        number(probe['ground_height_m'])
        require(isinstance(probe['feet'],dict), 'feet must map end joints to form parts')
    require(not metrics.intersection(MOTION_METRICS) or probe is not None, 'motion metrics require a motion probe')
    if metrics.intersection({'maximum_contact_slip_m','foot_penetration_m','peak_foot_lift_m'}):
        require(bool(probe['feet']), 'foot metrics require explicit foot parts')
    warm = raw.get('warm_starts',[])
    require(isinstance(warm,list) and len(warm) <= 16, 'at most 16 warm starts')
    for settings in warm:
        require(isinstance(settings,dict) and set(settings) == ids, 'warm starts must name every control')
        for c in controls:
            require(canonical(settings[c['id']]) in [canonical(v) for v in c['values']], 'warm start outside declared options')
    return character


def _checks(criteria, metrics):
    result, loss = [], 0.
    for c in criteria:
        value = metrics.get(c['metric'])
        observed = value is not None and math.isfinite(value)
        deficit = (max(0.,c.get('min',-math.inf)-value,value-c.get('max',math.inf)) if observed else None)
        passed = observed and deficit == 0
        # Very small declared scales must not turn retained JSON into Infinity.
        loss = min(1e30, loss + (deficit/c.get('scale',1) if observed else 1e6))
        result.append({'metric':c['metric'],'observed':value,'min':c.get('min'),'max':c.get('max'),'passed':passed})
    return result, loss


def _form(recipe, character):
    return compile_form_pattern(recipe['form'] if character else recipe)['specification']


def _evaluate(recipe, character, probe, samples, *, geometry_only=False):
    spec = _form(recipe,character)
    metrics, evidence = _geometry(spec), None
    if geometry_only:
        return metrics, evidence
    if probe is not None:
        controller = CharacterController(recipe)
        require(probe['clip'] in controller.plans, 'motion probe names a missing clip')
        plan = controller.plans[probe['clip']]
        require(plan['kind'] == 'walk' or probe['cycles'] == 1, 'reach probes cannot loop')
        duration = plan['duration']*probe['cycles']
        evidence = controller.measure(probe['clip'],[duration*i/(samples-1) for i in range(samples)],
                    feet=probe['feet'],up_axis=probe['up_axis'],ground_height_m=probe['ground_height_m'])
        metrics.update(evidence['metrics'])
        asset = controller.asset
    else:
        if character:
            compiled = compile_character_recipe(recipe)
            if compiled['motion']:
                from .character_motion import build_character_motion
                body = build_character_motion(compiled['specification'],compiled['motion'])['body']
            else:
                body = build_glb(compiled['specification'])['body']
        else:
            body = build_glb(spec)['body']
        asset = GamePoseAsset(body)
        evidence = {'source_sha256':asset.source_sha256, 'boundary':'Decoded rest geometry; no motion or artistic-quality evidence.'}
    # Acceptance uses decoded output, including float32 geometry precision.
    observed = deepcopy(spec)
    for part,mesh in zip(observed['primitives'],asset.sample(vertices=True)['meshes']):
        part['positions'] = mesh['positions']
    metrics.update(_geometry(observed))
    return metrics, evidence


def search_construction(raw):
    """Best-first traversal of neighboring declared options, then deeper verification."""
    character = _validate(raw)
    controls, criteria, budget = raw['controls'], raw['criteria'], raw['budget']
    probe = raw.get('motion_probe')
    geometry_criteria = [c for c in criteria if c['metric'] in GEOMETRY_METRICS]
    start = []
    for c in controls:
        node,key = _locate(raw['recipe'],c['paths'][0])
        values = [canonical(v) for v in c['values']]
        start.append(values.index(canonical(node[key])) if canonical(node[key]) in values else 0)
    seeds = [tuple([next(i for i,v in enumerate(c['values']) if canonical(v)==canonical(s[c['id']])) for c in controls])
             for s in raw.get('warm_starts',[])] + [tuple(start)]
    queue, queued, history, cache = [], set(), [], {}
    for index, point in enumerate(seeds):
        if point not in queued:
            heapq.heappush(queue,(-1.,index,point)); queued.add(point)
    serial, validations, evaluations, duplicates, selected = len(queue), 0, 0, 0, None
    caught = (CharacterMotionError, CharacterRecipeError, FormPatternError, Procedural3DError, ValueError)

    def validate(row):
        nonlocal validations
        validations += 1
        row['validation_attempted'] = True
        try:
            metrics,evidence = _evaluate(row['recipe'],character,probe,budget['validation_samples'])
            checks,loss = _checks(criteria,metrics)
            row.update(metrics=metrics,checks=checks,loss=loss,evidence=evidence,
                       status='ACCEPTED' if all(c['passed'] for c in checks) else 'VALIDATION_FAILED')
        except caught as exc:
            row.update(status='VALIDATION_FAILED',reason=str(exc),loss=1e30)
        return row if row['status']=='ACCEPTED' else None

    while queue and len(history) < budget['candidates']:
        _,_,point = heapq.heappop(queue)
        recipe,settings = deepcopy(raw['recipe']),{}
        for c,i in zip(controls,point):
            settings[c['id']] = deepcopy(c['values'][i])
            for path in c['paths']:
                node,key = _locate(recipe,path); node[key] = deepcopy(c['values'][i])
        novelty = classify_creator_atoms({'tasks':[{'id':'candidate','dependencies':[],
                    'request':{'operation':'construct_recipe','recipe':recipe}}]})['tasks'][0]
        signature = novelty['atom_signature']
        row = {'trial':len(history)+1,'settings':settings,'recipe':recipe,'signature':signature,
               'status':'REJECTED','loss':1e30,'validation_attempted':False}
        if signature in cache:
            duplicates += 1
            prior = cache[signature]
            row.update(status='DUPLICATE_STRUCTURE',duplicate_of=prior['trial'],loss=prior['loss'])
        else:
            evaluations += 1
            try:
                metrics,_ = _evaluate(recipe,character,probe,9,geometry_only=True)
                cheap_checks,cheap_loss = _checks(geometry_criteria,metrics)
                if all(c['passed'] for c in cheap_checks):
                    metrics,_ = _evaluate(recipe,character,probe,9)
                    checks,loss = _checks(criteria,metrics)
                    row.update(status='COARSE_CANDIDATE',metrics=metrics,checks=checks,loss=loss)
                    if all(c['passed'] for c in checks) and validations < budget['validations']:
                        selected = validate(row)
                else:
                    row.update(status='GEOMETRY_REJECTED',metrics=metrics,checks=cheap_checks,loss=cheap_loss)
            except caught as exc:
                row['reason'] = str(exc)
            if row['status'] != 'REJECTED':
                cache[signature] = row
        history.append(row)
        if selected is not None:
            break
        for axis,c in enumerate(controls):
            for step in (-1,1):
                neighbor = list(point); neighbor[axis] += step; neighbor = tuple(neighbor)
                if 0 <= neighbor[axis] < len(c['values']) and neighbor not in queued:
                    queued.add(neighbor); serial += 1
                    heapq.heappush(queue,(row['loss'],serial,neighbor))
    # Coarse sampling can miss a useful swing peak. Recheck the best unresolved
    # candidates densely instead of treating a cheap observation as a proof.
    if selected is None:
        pending = sorted((r for r in history if r['status']=='COARSE_CANDIDATE' and not r['validation_attempted']),
                         key=lambda r:(r['loss'],r['trial']))
        for row in pending:
            if validations >= budget['validations']:
                break
            selected = validate(row)
            if selected is not None:
                break
    status = ('CRITERIA_MET' if selected else 'BUDGET_EXHAUSTED' if queue or any(
        r['status']=='COARSE_CANDIDATE' and not r['validation_attempted'] for r in history) else 'SPACE_EXHAUSTED')
    best = min(history,key=lambda r:(r['loss'],r['trial']))
    public_history = [{k:v for k,v in row.items() if k not in ('recipe','evidence')} for row in history]
    return {'schema':SCHEMA,'implementation_version':'0.1.0','python_version':platform.python_version(),
            'status':status,'intent':raw['intent'],'search_contract':deepcopy(raw),
            'contract_sha256':digest(raw),'selected':deepcopy(selected),'best_trial':best['trial'],
            'history':public_history,'counts':{'visited':len(history),'evaluated':evaluations,
            'deduplicated':duplicates,'deep_validations':validations,'declared_combinations':math.prod(len(c['values']) for c in controls)},
            'acceptance':{'basis':'DECLARED_MEASUREMENTS','probability':None,'global_optimality_claimed':False,
                          'validation_samples':budget['validation_samples'] if probe else 0},
            'growth_candidate':({'semantic_signature':selected['signature'],'recipe':deepcopy(selected['recipe']),
                'warm_start':deepcopy(selected['settings']),'evidence':deepcopy(selected['evidence']),
                'automatic_canon_admission':False} if selected else None),
            'boundary':'Finite supplied construction options and measured criteria. Deterministic within the same runtime. No invented aesthetic score, global search completeness, physical realism or automatic library admission.'}


def publish_search(directory, contract):
    """Retain all trials and, on acceptance, the actual GLB and creator source."""
    from .atomic import atomic_write_json
    from .character_recipe import publish_character_recipe
    from .form_pattern import publish_form_pattern
    target = Path(directory).resolve()
    require(not target.exists(), 'search output directory already exists')
    report = search_construction(contract)
    target.mkdir(parents=True, exist_ok=False)
    try:
        if report['selected']:
            recipe = report['selected']['recipe']
            publisher = publish_character_recipe if recipe['schema']=='axm.character-recipe/v0.1' else publish_form_pattern
            publication = publisher(target/'winner.glb',recipe)
            require(publication['sha256']==report['selected']['evidence']['source_sha256'],
                    'published winner differs from the verified construction')
            report['publication'] = {'asset':'winner.glb','creator_source':'winner.glb.source.json',
                                     'sha256':publication['sha256'],
                                     'runtime_contact_requires_controller':bool(contract.get('motion_probe'))}
        atomic_write_json(target/'search.json',report)
    except Exception:
        shutil.rmtree(target)
        raise
    return {'operation':'construction-search','status':report['status'],'path':str(target),
            'report_path':str(target/'search.json'),'counts':report['counts'],
            'publication':report.get('publication'),'acceptance':report['acceptance']}
