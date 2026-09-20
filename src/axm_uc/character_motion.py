"""Explicit reusable translation-rest skeletons, skins and clips over form geometry."""
from __future__ import annotations
import hashlib
import json
import math
from pathlib import Path
import struct
from .atomic import atomic_write_bytes
from .game_pose_runtime import GamePoseAsset, _parse
from .procedural_3d import build_glb, MAX_REPLACED_FILE_BYTES

SCHEMA = 'axm.character-rig/v0.1'

class CharacterMotionError(ValueError):
    pass

def require(ok, message):
    if not ok:
        raise CharacterMotionError(message)

def fields(value, required, optional=()):
    require(isinstance(value, dict) and set(required) <= set(value)
            and not set(value)-set(required)-set(optional), 'unsupported or missing motion fields')

def name(value):
    require(isinstance(value, str) and 0 < len(value) <= 120 and value.strip() == value, 'invalid motion name')
    return value

def number(value):
    require(type(value) in (int, float) and abs(value) <= 100000 and math.isfinite(value), 'invalid motion number')
    return float(value)

def vector(value, width):
    require(isinstance(value, list) and len(value) == width, 'invalid motion vector')
    return [number(v) for v in value]

def compile_motion(specification, rig, animation=None):
    fields(rig, {'schema', 'joints', 'bindings'})
    require(rig['schema'] == SCHEMA, 'unsupported character rig schema')
    joints = rig['joints']
    require(isinstance(joints, list) and 1 <= len(joints) <= 128, 'rig requires 1..128 joints')
    normalized, ids = [], {}
    for row in joints:
        fields(row, {'id', 'parent', 'translation'})
        jid = name(row['id'])
        require(jid not in ids, 'duplicate joint')
        parent = row['parent']
        require(parent is None or isinstance(parent, str) and parent in ids,
                'joints must be parent-first; missing parents and cycles are refused')
        translation = vector(row['translation'], 3)
        world = [v + (normalized[ids[parent]]['world'][i] if parent else 0) for i, v in enumerate(translation)]
        ids[jid] = len(normalized)
        normalized.append({'id': jid, 'parent': parent, 'translation': translation, 'world': world})
    require(sum(j['parent'] is None for j in normalized) == 1, 'exactly one skeleton root required')
    parts, bindings = specification['primitives'], rig['bindings']
    require(isinstance(bindings, dict) and set(bindings) == {p['id'] for p in parts}, 'bind every form part exactly once')
    skin = {}
    for part in parts:
        binding = bindings[part['id']]
        require(isinstance(binding, dict), 'part binding must be an object')
        if set(binding) == {'joint'}:
            require(isinstance(binding['joint'], str) and binding['joint'] in ids, 'unknown rigid joint')
            rows = [{binding['joint']: 1.0}] * len(part['positions'])
        elif set(binding) == {'axis_blend'}:
            blend = binding['axis_blend']
            fields(blend, {'from', 'to', 'axis', 'range'})
            require(isinstance(blend['from'], str) and isinstance(blend['to'], str)
                    and blend['from'] in ids and blend['to'] in ids and blend['from'] != blend['to'], 'invalid blend joints')
            axis = blend['axis']
            require(type(axis) is int and axis in (0, 1, 2), 'blend axis must be 0, 1 or 2')
            low, high = vector(blend['range'], 2)
            require(low < high, 'blend range must increase')
            rows = []
            for point in part['positions']:
                weight = min(1., max(0., (point[axis]-low)/(high-low)))
                rows.append({blend['from']: 1-weight, blend['to']: weight})
        else:
            fields(binding, {'weights'})
            rows = binding['weights']
            require(isinstance(rows, list) and len(rows) == len(part['positions']), 'weight rows must match compiled vertices')
        result = []
        for row in rows:
            require(isinstance(row, dict) and 1 <= len(row) <= 4 and set(row) <= set(ids), 'weights require 1..4 known joints')
            ordered = sorted((ids[j], number(w)) for j, w in row.items())
            require(all(w >= 0 for _, w in ordered) and abs(sum(w for _, w in ordered)-1) <= 1e-6,
                    'weights must be nonnegative and sum to one; no silent repair')
            result.append({'joints': [j for j, _ in ordered]+[0]*(4-len(ordered)),
                           'weights': [w for _, w in ordered]+[0.]*(4-len(ordered))})
        skin[part['id']] = result
    clips = [] if animation in (None, False, 'none') else animation
    require(isinstance(clips, list) and len(clips) <= 32, 'animation requires at most 32 clips')
    seen, output, total = set(), [], 0
    for clip in clips:
        fields(clip, {'name', 'tracks'})
        cname = name(clip['name'])
        require(cname not in seen, 'duplicate clip name')
        seen.add(cname)
        tracks = clip['tracks']
        require(isinstance(tracks, list) and 1 <= len(tracks) <= 256, 'clip requires 1..256 tracks')
        targets, out = set(), []
        for track in tracks:
            fields(track, {'joint', 'path', 'times', 'values'}, {'interpolation'})
            joint, path = track['joint'], track['path']
            require(isinstance(joint, str) and joint in ids and path in ('translation', 'rotation'), 'invalid track target')
            require((joint, path) not in targets, 'duplicate track target')
            targets.add((joint, path))
            times = track['times']
            require(isinstance(times, list) and 2 <= len(times) <= 4096, 'track requires 2..4096 times')
            times = [number(t) for t in times]
            total += len(times)
            require(total <= 65536 and times[0] == 0 and all(a < b for a, b in zip(times, times[1:])), 'invalid key times/budget')
            values = track['values']
            require(isinstance(values, list) and len(values) == len(times), 'track times/values differ')
            values = [vector(v, 4 if path == 'rotation' else 3) for v in values]
            if path == 'rotation':
                require(all(abs(sum(x*x for x in v)-1) <= 1e-6 for v in values), 'rotation requires unit xyzw quaternion')
            mode = track.get('interpolation', 'LINEAR')
            require(mode in ('LINEAR', 'STEP'), 'unsupported interpolation')
            out.append({'joint': joint, 'path': path, 'times': times, 'values': values, 'interpolation': mode})
        output.append({'name': cname, 'tracks': out})
    return {'schema': SCHEMA, 'joints': normalized, 'skin': skin, 'clips': output,
            'boundary': 'Explicit translation-rest skeleton, rigid or supplied four-influence skin, LINEAR/STEP clips; no anatomy inference, auto-weighting, IK, cloth or aesthetic acceptance.'}

def build_character_motion(specification, motion):
    built = build_glb(specification)
    doc, payload = _parse(built['body'])
    binary = bytearray(payload)
    def accessor(rows, shape, code='f', target=None):
        binary.extend(b'\0' * (-len(binary) % 4))
        start = len(binary)
        for row in rows:
            binary.extend(struct.pack('<'+code*len(row), *row))
        view = {'buffer': 0, 'byteOffset': start, 'byteLength': len(binary)-start}
        if target is not None:
            view['target'] = target
        doc['bufferViews'].append(view)
        a = {'bufferView': len(doc['bufferViews'])-1, 'componentType': 5126 if code == 'f' else 5123, 'count': len(rows), 'type': shape}
        if shape == 'SCALAR':
            a.update(min=[min(r[0] for r in rows)], max=[max(r[0] for r in rows)])
        doc['accessors'].append(a)
        return len(doc['accessors'])-1
    offset = len(doc['nodes'])
    joints = motion['joints']
    ids = {j['id']: offset+i for i, j in enumerate(joints)}
    inverses = []
    for j in joints:
        doc['nodes'].append({'name': j['id'], 'translation': j['translation']})
        x,y,z = j['world']
        inverses.append([1,0,0,0, 0,1,0,0, 0,0,1,0, -x,-y,-z,1])
    for j in joints:
        if j['parent'] is None:
            doc['scenes'][0]['nodes'].append(ids[j['id']])
        else:
            doc['nodes'][ids[j['parent']]].setdefault('children', []).append(ids[j['id']])
    doc['skins'] = [{'joints': list(ids.values()), 'skeleton': offset, 'inverseBindMatrices': accessor(inverses, 'MAT4')}]
    for node in doc['nodes'][:offset]:
        rows = motion['skin'][node['name']]
        attrs = doc['meshes'][node['mesh']]['primitives'][0]['attributes']
        attrs['JOINTS_0'] = accessor([r['joints'] for r in rows], 'VEC4', 'H', 34962)
        attrs['WEIGHTS_0'] = accessor([r['weights'] for r in rows], 'VEC4', target=34962)
        node['skin'] = 0
    if motion['clips']:
        doc['animations'] = []
    for clip in motion['clips']:
        samplers, channels = [], []
        for track in clip['tracks']:
            samplers.append({'input': accessor([[t] for t in track['times']], 'SCALAR'),
                             'output': accessor(track['values'], 'VEC4' if track['path'] == 'rotation' else 'VEC3'),
                             'interpolation': track['interpolation']})
            channels.append({'sampler': len(samplers)-1, 'target': {'node': ids[track['joint']], 'path': track['path']}})
        doc['animations'].append({'name': clip['name'], 'samplers': samplers, 'channels': channels})
    doc['buffers'][0]['byteLength'] = len(binary)
    raw = json.dumps(doc, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    raw += b' ' * (-len(raw) % 4)
    binary.extend(b'\0' * (-len(binary) % 4))
    body = (struct.pack('<4sII', b'glTF', 2, 28+len(raw)+len(binary)) + struct.pack('<I4s', len(raw), b'JSON') + raw
            + struct.pack('<I4s', len(binary), b'BIN\0') + binary)
    asset = GamePoseAsset(body)
    asset.sample(vertices=True)
    for clip in motion['clips']:
        for t in sorted({t for track in clip['tracks'] for t in track['times']}):
            asset.sample(clip['name'], t)
    validation = asset.describe()
    if motion.get('performance_observations'):
        errors, contacts = [], 0
        for observation in motion['performance_observations']:
            poses = {}
            for row in observation['samples']:
                if row['time'] not in poses:
                    poses[row['time']] = asset.sample(observation['clip'], row['time'])
                pose = poses[row['time']]
                actual = asset.point(pose, ids[row['joint']])
                error = math.dist(actual, row['target'])
                require(error <= 1e-4, 'exported performance misses a declared sample target')
                errors.append(error)
                contacts += int(row['contact'])
        validation['performance'] = {'max_sample_target_error_m': max(errors),
                                     'verified_targets': len(errors), 'verified_contact_samples': contacts,
                                     'boundary': 'Authored sample joint positions; no between-key contact or physical-balance claim.'}
    return {**built, 'body': body, 'document': doc, 'motion_validation': validation}

def publish_motion_glb(target, specification, motion, *, replace=False):
    target = Path(target).resolve()
    require(target.suffix.lower() == '.glb', 'motion output requires .glb')
    require(not target.exists() or target.is_file() and replace, 'motion destination exists or is not a file')
    previous = target.read_bytes() if target.exists() else None
    require(previous is None or len(previous) <= MAX_REPLACED_FILE_BYTES, 'replacement exceeds rollback budget')
    built = build_character_motion(specification, motion)
    try:
        atomic_write_bytes(target, built['body'])
        body = target.read_bytes()
        require(body == built['body'], 'published motion bytes changed')
        observed = GamePoseAsset(body).describe()
    except Exception:
        if previous is None:
            target.unlink(missing_ok=True)
        else:
            atomic_write_bytes(target, previous)
        raise
    return {'operation': 'glb', 'truth_status': 'VALIDATED_EXPLICIT_SKINNED_CHARACTER', 'path': str(target),
            'bytes': len(body), 'sha256': hashlib.sha256(body).hexdigest(), 'specification_sha256': built['specification_sha256'],
            'published': True, 'replaced': previous is not None, 'motion_validation': built['motion_validation'],
            'post_publish_pose_validation': observed,
            'rendered_appearance_observed': False, 'host_import_compatibility_observed': False}
