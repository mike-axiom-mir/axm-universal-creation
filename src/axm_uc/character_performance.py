"""Body-relative rig fitting and sampled two-bone performances.

Landmarks are declared, never inferred. Reuses UC's two-bone locus solver and
emits the existing explicit character-motion contract. Z-up is not assumed.
"""
from __future__ import annotations

from copy import deepcopy
import math

from .character_motion import fields, name, number, require, vector
from .limb_geometry import two_bone_entry_range

SCHEMA = 'axm.character-performance/v0.1'


def add(a, b):
    return [x + y for x, y in zip(a, b)]


def sub(a, b):
    return [x - y for x, y in zip(a, b)]


def mul(a, scale):
    return [x * scale for x in a]


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def cross(a, b):
    return [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]]


def unit(a):
    length = math.hypot(*a)
    require(length > 1e-9, 'direction or segment has zero length')
    return mul(a, 1 / length)


def conjugate(q):
    return [-q[0], -q[1], -q[2], q[3]]


def product(a, b):
    v = add(add(mul(b[:3], a[3]), mul(a[:3], b[3])), cross(a[:3], b[:3]))
    return v + [a[3]*b[3] - dot(a[:3], b[:3])]


def rotation_between(a, b, pole):
    a, b = unit(a), unit(b)
    cosine = max(-1., min(1., dot(a, b)))
    if cosine < -1 + 1e-10:
        # The declared pole selects the otherwise ambiguous half-turn axis.
        return unit(sub(pole, mul(a, dot(pole, a)))) + [0.]
    q = cross(a, b) + [1 + cosine]
    return mul(q, 1 / math.hypot(*q))


def solve_chain(start, middle_rest, end_rest, target, pole):
    upper, lower = sub(middle_rest, start), sub(end_rest, middle_rest)
    require(min(math.hypot(*upper), math.hypot(*lower)) > 1e-9,
            'chain segment has zero length')
    pole = unit(pole)
    locus = two_bone_entry_range(start, target, math.hypot(*upper), math.hypot(*lower), pole)
    require(locus.status == 'reachable' and locus.locus != 'sphere',
            'target is unreachable or has an ambiguous coincident endpoint')
    if locus.radius_m > 1e-9:
        bend = unit(sub(pole, mul(locus.circle_axis, dot(pole, locus.circle_axis))))
        middle = add(locus.center, mul(bend, locus.radius_m))
    else:
        middle = list(locus.center)
    upper_q = rotation_between(upper, sub(middle, start), pole)
    lower_world_q = rotation_between(lower, sub(target, middle), pole)
    lower_q = product(conjugate(upper_q), lower_world_q)
    return upper_q, lower_q, conjugate(lower_world_q), middle


def _bounds(specification):
    return {p['id']: ([min(v[i] for v in p['positions']) for i in range(3)],
                      [max(v[i] for v in p['positions']) for i in range(3)])
            for p in specification['primitives']}


def anchor_point(raw, bounds):
    if isinstance(raw, list):
        return vector(raw, 3)
    fields(raw, {'part', 'fraction'}, {'offset', 'offset_fraction'})
    require(isinstance(raw['part'], str) and raw['part'] in bounds, 'landmark references unknown form part')
    fraction = vector(raw['fraction'], 3)
    require(all(0 <= v <= 1 for v in fraction), 'landmark fractions must be in 0..1')
    low, high = bounds[raw['part']]
    offset = vector(raw.get('offset', [0, 0, 0]), 3)
    relative = vector(raw.get('offset_fraction', [0, 0, 0]), 3)
    return [a + (b-a)*(f+r) + o for a, b, f, r, o in zip(low, high, fraction, relative, offset)]


def _fit_joints(rows, bounds):
    require(isinstance(rows, list) and 1 <= len(rows) <= 128, 'performance needs 1..128 landmark joints')
    positions, parents, joints = {}, {}, []
    for row in rows:
        fields(row, {'id', 'parent', 'anchor'})
        jid = name(row['id'])
        require(jid not in positions, 'duplicate fitted joint')
        parent = row['parent']
        require(parent is None or isinstance(parent, str) and parent in positions, 'fitted joints must be parent-first')
        position = anchor_point(row['anchor'], bounds)
        positions[jid], parents[jid] = position, parent
        joints.append({'id': jid, 'parent': parent,
                       'translation': sub(position, positions[parent]) if parent else position})
    require(sum(p is None for p in parents.values()) == 1, 'fitted skeleton must have one root')
    return joints, positions, parents


def _segment_distance(point, start, end):
    direction = sub(end, start)
    length2 = dot(direction, direction)
    require(length2 > 1e-18, 'weight segment has zero length')
    fraction = min(1., max(0., dot(sub(point, start), direction) / length2))
    return math.hypot(*sub(point, add(start, mul(direction, fraction))))


def _fit_bindings(raw, specification, positions):
    require(isinstance(raw, dict) and set(raw) == {p['id'] for p in specification['primitives']},
            'performance bindings must cover every part exactly')
    bindings = {}
    for part in specification['primitives']:
        binding = raw[part['id']]
        require(isinstance(binding, dict), 'invalid fitted binding')
        if set(binding) != {'segment_weights'}:
            # Rigid and caller-owned weights stay supported by the existing compiler.
            bindings[part['id']] = deepcopy(binding)
            continue
        field = binding['segment_weights']
        fields(field, {'segments'}, {'falloff', 'max_influences', 'softness_m'})
        segments = field['segments']
        require(isinstance(segments, list) and 1 <= len(segments) <= 32, 'weight field needs 1..32 segments')
        power = number(field.get('falloff', 2))
        softness = number(field.get('softness_m', .02))
        limit = field.get('max_influences', 4)
        require(1 <= power <= 8 and 1e-5 <= softness <= 1 and type(limit) is int and 1 <= limit <= 4,
                'invalid segment weight settings')
        starts = set()
        for segment in segments:
            require(isinstance(segment, list) and len(segment) == 2 and all(isinstance(j, str) and j in positions for j in segment),
                    'weight segment requires two known joints')
            require(segment[0] not in starts, 'duplicate weight influence joint')
            starts.add(segment[0])
            _segment_distance(positions[segment[0]], positions[segment[0]], positions[segment[1]])
        rows = []
        for point in part['positions']:
            influences = [(a, 1 / (softness + _segment_distance(point, positions[a], positions[b]))**power)
                          for a, b in segments]
            influences.sort(key=lambda row: (-row[1], row[0]))
            selected = influences[:limit]
            total = sum(w for _, w in selected)
            rows.append({j: w/total for j, w in selected})
        bindings[part['id']] = {'weights': rows}
    return bindings


def _target_at(targets, phase):
    for a, b in zip(targets, targets[1:]):
        if phase <= b[0]:
            blend = (phase-a[0])/(b[0]-a[0])
            return add(a[1], mul(sub(b[1], a[1]), blend))
    return list(targets[-1][1])


def _chains(raw, positions, parents, kind, bounds):
    require(isinstance(raw, list) and 1 <= len(raw) <= 16, 'clip needs 1..16 chains')
    seen, result = set(), []
    for chain in raw:
        fields(chain, {'joints', 'pole', 'phase'} if kind == 'walk' else {'joints', 'pole', 'targets'},
               {'keep_end_orientation', 'max_bend_degrees'})
        ids = chain['joints']
        require(isinstance(ids, list) and len(ids) == 3 and all(isinstance(j, str) and j in positions for j in ids)
                and len(set(ids)) == 3, 'chain needs three distinct known joints')
        require(not seen.intersection(ids) and parents[ids[1]] == ids[0] and parents[ids[2]] == ids[1],
                'chains must be disjoint consecutive parent-child joints')
        seen.update(ids)
        pole = unit(vector(chain['pole'], 3))
        keep = chain.get('keep_end_orientation', False)
        require(type(keep) is bool, 'keep_end_orientation must be boolean')
        bend = number(chain.get('max_bend_degrees', 180))
        require(0 < bend <= 180, 'max bend must be in 0..180')
        normalized = {'joints': ids, 'pole': pole, 'keep': keep, 'bend': bend}
        if kind == 'walk':
            phase = number(chain['phase'])
            require(0 <= phase < 1, 'walk phase must be in [0,1)')
            normalized['phase'] = phase
        else:
            targets = chain['targets']
            require(isinstance(targets, list) and 2 <= len(targets) <= 128, 'reach requires 2..128 targets')
            points = []
            for target in targets:
                fields(target, {'at', 'point'})
                at = number(target['at'])
                require(0 <= at <= 1, 'target phase must be in 0..1')
                points.append([at, anchor_point(target['point'], bounds)])
            require(points[0][0] == 0 and points[-1][0] == 1 and all(a[0] < b[0] for a, b in zip(points, points[1:])),
                    'target phases must cover 0..1 and strictly increase')
            normalized['targets'] = points
        result.append(normalized)
    # Ancestor rotation would require solving in that ancestor's animated frame.
    for chain in result:
        parent = parents[chain['joints'][0]]
        while parent is not None:
            require(parent not in seen, 'animated chain ancestors are unsupported')
            parent = parents[parent]
    return result


def _prepare_clip(raw, positions, parents, bounds):
    require(isinstance(raw, dict), 'performance clip must be an object')
    kind = raw.get('kind')
    require(kind in ('reach', 'walk'), 'supported performance kinds are reach and walk')
    common = {'name', 'kind', 'duration', 'samples', 'chains'}
    fields(raw, common | ({'stride', 'lift', 'up_axis', 'forward_axis', 'stance_fraction'} if kind == 'walk' else set()),
           {'root_translation'} if kind == 'reach' else set())
    cname, duration, samples = name(raw['name']), number(raw['duration']), raw['samples']
    require(.01 <= duration <= 120 and type(samples) is int and 3 <= samples <= 257, 'invalid clip duration/sample count')
    chains = _chains(raw['chains'], positions, parents, kind, bounds)
    root = next(j for j, p in parents.items() if p is None)
    require(all(root not in c['joints'] for c in chains), 'chain joints must be below the motion root')
    travel = vector(raw.get('root_translation', [0, 0, 0]), 3)
    if kind == 'walk':
        forward, up = raw['forward_axis'], raw['up_axis']
        require(type(forward) is int and type(up) is int and forward in (0,1,2) and up in (0,1,2) and forward != up,
                'walk requires distinct forward and up axes')
        stride, lift, stance = number(raw['stride']), number(raw['lift']), number(raw['stance_fraction'])
        require(0 < stride <= 10 and 0 < lift <= 2 and .5 <= stance < .9, 'invalid stride/lift/stance')
        travel = [0., 0., 0.]
        travel[forward] = stride
    plan = {'name': cname, 'kind': kind, 'duration': duration, 'samples': samples,
            'chains': chains, 'root': root, 'travel': travel}
    if kind == 'walk':
        plan.update(forward=forward, up=up, stride=stride, lift=lift, stance=stance)
    return plan


def sample_performance(plan, positions, phase):
    """Solve at an explicit phase; walk phases above one accumulate root travel.

    Plans come from _prepare_clip. No hidden clock, prior frame or baked-key
    interpolation determines this pose. Reach phases must remain within 0..1.
    """
    phase = number(phase)
    require(phase >= 0 and (plan['kind'] == 'walk' or phase <= 1), 'invalid performance phase')
    root_offset = mul(plan['travel'], phase)
    values = {(plan['root'], 'translation'): add(positions[plan['root']], root_offset)}
    observations = []
    for chain in plan['chains']:
        first, middle, end = chain['joints']
        start, mid_rest, end_rest = [add(positions[j], root_offset) for j in chain['joints']]
        contact, plant = False, None
        if plan['kind'] == 'walk':
            cycle = phase + chain['phase']
            step = math.floor(cycle)
            local = cycle - step
            target = list(positions[end])
            distance = plan['stride']*(step-chain['phase'])
            if local <= plan['stance']:
                contact, plant = True, step
            else:
                u = (local-plan['stance'])/(1-plan['stance'])
                distance += plan['stride']*u*u*(3-2*u)
                target[plan['up']] += plan['lift']*math.sin(math.pi*u)**2
            target[plan['forward']] += distance
        else:
            target = _target_at(chain['targets'], phase)
        q1, q2, q3, elbow = solve_chain(start, mid_rest, end_rest, target, chain['pole'])
        bend = math.degrees(math.acos(max(-1., min(1., dot(unit(sub(elbow,start)), unit(sub(target,elbow)))))))
        require(bend <= chain['bend'] + 1e-7, f"{plan['name']}: chain bend exceeds declared limit")
        values[first, 'rotation'], values[middle, 'rotation'] = q1, q2
        if chain['keep']:
            values[end, 'rotation'] = q3
        observations.append({'time': phase*plan['duration'], 'joint': end, 'target': target,
                             'contact': contact, 'plant': plant, 'bend_degrees': bend})
    return values, observations


def _compile_clip(plan, positions):
    cname, duration, samples = plan['name'], plan['duration'], plan['samples']
    root, chains = plan['root'], plan['chains']
    values = {(root, 'translation'): []}
    for chain in chains:
        for j in chain['joints'][:3 if chain['keep'] else 2]:
            values[j, 'rotation'] = []
    observations = []
    times = [duration*i/(samples-1) for i in range(samples)]
    for i, time in enumerate(times):
        solved, rows = sample_performance(plan, positions, i/(samples-1))
        for key in values:
            values[key].append(solved[key])
        observations.extend({**row, 'time': time} for row in rows)
    tracks = []
    for (joint, path), keys in values.items():
        if path == 'rotation':
            for i in range(1, len(keys)):
                if dot(keys[i-1], keys[i]) < 0:
                    keys[i] = mul(keys[i], -1)
        tracks.append({'joint': joint, 'path': path, 'times': times, 'values': keys, 'interpolation': 'LINEAR'})
    return {'name': cname, 'tracks': tracks}, {'clip': cname, 'kind': plan['kind'], 'samples': observations,
            'root_travel': plan['travel'], 'boundary': 'Baked targets/contact verified at authored samples only; use the runtime controller to solve between keys. No physical balance or collision guarantee.'}


def fit_character_performance(raw, specification, *, body_family):
    fields(raw, {'schema', 'body_family', 'joints', 'bindings', 'clips'})
    require(raw['schema'] == SCHEMA, 'unsupported performance schema')
    require(raw['body_family'] == body_family, 'performance body family does not match character')
    bounds = _bounds(specification)
    joints, positions, parents = _fit_joints(raw['joints'], bounds)
    bindings = _fit_bindings(raw['bindings'], specification, positions)
    require(isinstance(raw['clips'], list) and 1 <= len(raw['clips']) <= 8, 'performance needs 1..8 clips')
    clips, observations, controllers = [], [], []
    for raw_clip in raw['clips']:
        plan = _prepare_clip(raw_clip, positions, parents, bounds)
        clip, observation = _compile_clip(plan, positions)
        clips.append(clip)
        observations.append(observation)
        controllers.append(plan)
    return {'rig': {'schema': 'axm.character-rig/v0.1', 'joints': joints, 'bindings': bindings},
            'animation': clips, 'landmarks': positions, 'observations': observations, 'controllers': controllers,
            'boundary': 'Declared body-relative fitting, segment-distance skin fields and sampled two-bone reach/walk. No inferred anatomy or automatic growth-library admission.'}
