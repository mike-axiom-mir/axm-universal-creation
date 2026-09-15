"""Use the pinned Studio raster donor directly, preserving editable source.

Python handles bounded PNG intake/publication; Node executes original donor JS.
No platform host, browser, npm dependency, account, or AI service is started.
"""
from __future__ import annotations
import base64
import copy
import hashlib
import json
from pathlib import Path
import re
import shutil
import struct
import subprocess
import tempfile

from .atomic import atomic_write_bytes, atomic_write_json
from .design_visual import DesignVisualError, _parse_png, _inflate_scanlines, _row_rgba
from .fabric_noise import png_bytes

SCHEMA = 'axm.studio-composition-project/v1'
DONOR_COMMIT = '27757ace6133b243a200b0463e427c8b04d5a8e3'
DATA = Path(__file__).parent / 'data' / 'studio'
MAX_SOURCE_BYTES = 8 * 1024 * 1024
MAX_SOURCE_PIXELS = 4 * 1024 * 1024


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False).encode('utf-8')


def _run(request):
    node = shutil.which('node')
    if not node:
        raise RuntimeError('Studio compositor requires a local Node.js runtime; nothing was installed')
    payload = _encode(request)
    if len(payload) > 32 * 1024 * 1024:
        raise ValueError('Studio request exceeds byte bound')
    try:
        result = subprocess.run([node, '--max-old-space-size=384', str(DATA / 'compose-runner.cjs')],
                                input=payload, capture_output=True, timeout=30, check=False)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError('Studio composition exceeded its 30-second bound') from exc
    if result.returncode:
        raise ValueError('Studio donor rejected composition: ' + result.stderr.decode('utf-8', 'replace')[:1000])
    return json.loads(result.stdout)


def studio_compositor_catalog():
    return {'schema':'axm.studio-compositor-catalog/v1', 'runtime':'Node.js (optional local runtime)',
            'project_schema':SCHEMA, 'donor_commit':DONOR_COMMIT,
            'blends':['normal','multiply','screen','overlay','darken','lighten','color-dodge','color-burn',
                      'hard-light','soft-light','difference','exclusion','add','subtract'],
            'filters':['brightness','contrast','saturation','hue','grayscale','invert','gamma','threshold',
                       'posterize','tint','blur','sharpen','pixelate'],
            'limits':{'dimension':1024,'sources':32,'decoded_source_pixels':MAX_SOURCE_PIXELS,'timeout_seconds':30},
            'truth':'Original raster-compositor.js executes layers, masks and filters. Studio UI, brushes, '
                    'animation and 3D projection are donor source only, not integrated by this adapter. '
                    'Compositing is in encoded sRGB RGBA8; no ICC conversion or premultiplied-alpha blur repair.'}


def _dimension(value):
    if type(value) is not int or not 1 <= value <= 1024:
        raise ValueError('Studio dimensions must be integers in 1..1024')
    return value


def _read_png(path):
    with path.open('rb') as handle:
        body = handle.read(MAX_SOURCE_BYTES + 1)
    if len(body) > MAX_SOURCE_BYTES:
        raise ValueError('source PNG exceeds byte bound')
    try:
        header, compressed, palette, transparency = _parse_png(body)
    except DesignVisualError as exc:
        raise ValueError(f'invalid source PNG: {exc}') from exc
    _dimension(header['width']); _dimension(header['height'])
    offset = 8
    while offset < len(body):
        length = struct.unpack_from('>I', body, offset)[0]
        kind, data = body[offset+4:offset+8], body[offset+8:offset+8+length]
        if kind in (b'iCCP', b'cHRM', b'acTL'):
            raise ValueError('ICC/chromaticity conversion and animated PNG intake are unsupported')
        if kind == b'gAMA' and (len(data) != 4 or struct.unpack('>I', data)[0] != 45455):
            raise ValueError('source gamma must be sRGB-compatible; explicit conversion is required')
        if kind == b'sRGB' and (len(data) != 1 or data[0] > 3):
            raise ValueError('invalid sRGB chunk')
        offset += 12 + length
    return body, header, compressed, palette, transparency


def compose_studio_project(project, source_root):
    """Return result and original PNG bytes without writing caller state."""
    if not isinstance(project, dict) or set(project) != {'schema','recipe','sources'} or project['schema'] != SCHEMA:
        raise ValueError('project requires exactly schema, recipe and sources')
    if len(_encode(project)) > 1024 * 1024:
        raise ValueError('project JSON exceeds byte bound')
    recipe = project['recipe']
    if not isinstance(recipe, dict) or not isinstance(recipe.get('canvas'), dict):
        raise ValueError('recipe requires a canvas')
    for name in ('width','height'): _dimension(recipe['canvas'].get(name))
    declared = project['sources']
    if not isinstance(declared, dict) or len(declared) > 32:
        raise ValueError('sources must map at most 32 IDs to relative PNG paths')
    root = Path(source_root).resolve()
    originals, sources, digests = {}, {}, {}
    pixels, source_bytes = 0, 0
    for id, relative in sorted(declared.items()):
        if (not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,79}', id)
                or id in {'constructor','prototype','toString','valueOf','hasOwnProperty',
                          'isPrototypeOf','propertyIsEnumerable','toLocaleString'}):
            raise ValueError('invalid source ID')
        if not isinstance(relative, str) or '\\' in relative or Path(relative).is_absolute() or '..' in Path(relative).parts:
            raise ValueError('source path must be relative and stay within source root')
        path = (root / relative).resolve()
        if not path.is_relative_to(root):
            raise ValueError('source path escapes source root')
        body, header, compressed, palette, transparency = _read_png(path)
        pixels += header['width'] * header['height']; source_bytes += len(body)
        if pixels > MAX_SOURCE_PIXELS or source_bytes > 32 * 1024 * 1024:
            raise ValueError('total source budget exceeded')
        try:
            rows, _ = _inflate_scanlines(header, compressed)
            rgba = bytes(channel for row in rows for pixel in _row_rgba(row, header['color_type'], palette, transparency) for channel in pixel)
        except DesignVisualError as exc:
            raise ValueError(f'invalid source PNG pixels: {exc}') from exc
        originals[id] = body
        digests[id] = {'png_sha256':_sha(body),'rgba_sha256':_sha(rgba),'width':header['width'],'height':header['height']}
        sources[id] = {'width':header['width'],'height':header['height'],'rgba_base64':base64.b64encode(rgba).decode('ascii')}
    result = _run({'recipe':recipe,'sources':sources})
    rgba = base64.b64decode(result.pop('rgba_base64'), validate=True)
    if len(rgba) != result['width'] * result['height'] * 4:
        raise ValueError('donor output pixel size mismatch')
    body = png_bytes(result['width'], result['height'], 4, rgba)
    receipt = {'schema':'axm.studio-composition-receipt/v1','donor_commit':DONOR_COMMIT,
               'donor_sha256':result['donor_sha256'],'request_sha256':_sha(_encode(project)),
               'sources':digests,'output_png_sha256':_sha(body),'output_rgba_sha256':_sha(rgba),
               'width':result['width'],'height':result['height'], 'donor_receipt':result['donor_receipt'],
               'estimated_filter_work':result['estimated_filter_work'], 'source_preserved':True,
               'visual_approval':False,'truth':studio_compositor_catalog()['truth']}
    return {'png':body,'recipe':result['recipe'],'receipt':receipt,'sources':originals}


def edit_studio_layers(project, operations):
    """Apply ordered layer edits to a copy; rendering performs donor validation.

    Source paths and original project remain untouched. Use a fresh publication
    directory to retain both the previous project and this revision.
    """
    if not isinstance(project, dict) or project.get('schema') != SCHEMA:
        raise ValueError('invalid Studio project')
    if not isinstance(operations, list) or not 1 <= len(operations) <= 64:
        raise ValueError('supply 1..64 layer edits')
    if len(_encode(operations)) > 1024 * 1024:
        raise ValueError('layer edit byte bound exceeded')
    result = copy.deepcopy(project)
    layers = result.get('recipe', {}).get('layers')
    if not isinstance(layers, list): raise ValueError('project requires layers')

    def index(id):
        matches = [i for i, layer in enumerate(layers) if layer.get('id') == id]
        if len(matches) != 1: raise ValueError(f'unknown or ambiguous layer: {id}')
        return matches[0]

    for edit in operations:
        if not isinstance(edit, dict): raise ValueError('layer edit must be an object')
        op = edit.get('op')
        fields = {'add':{'op','layer','before'},'change':{'op','id','patch'},
                  'move':{'op','id','before'},'remove':{'op','id'}}
        if op not in fields or set(edit)-fields[op]: raise ValueError('unknown layer edit or fields')
        if op == 'add':
            layer = copy.deepcopy(edit.get('layer'))
            if not isinstance(layer, dict) or not isinstance(layer.get('id'),str) or not layer['id'].strip():
                raise ValueError('new layer requires an ID')
            if any(item.get('id') == layer['id'] for item in layers): raise ValueError('duplicate layer ID')
            layers.insert(index(edit['before']) if edit.get('before') is not None else len(layers),layer)
        elif op == 'change':
            changes = edit.get('patch')
            if not isinstance(changes,dict) or 'id' in changes: raise ValueError('patch must preserve layer ID')
            layers[index(edit.get('id'))].update(copy.deepcopy(changes))
        elif op == 'remove': layers.pop(index(edit.get('id')))
        else:
            old = index(edit.get('id'))
            if edit.get('before') == edit.get('id'): continue
            if edit.get('before') is not None: index(edit['before'])
            layer = layers.pop(old)
            layers.insert(index(edit['before']) if edit.get('before') is not None else len(layers),layer)
        if not 1 <= len(layers) <= 32: raise ValueError('layer count must remain in 1..32')
    return result


def publish_studio_project(path, project, source_root):
    target = Path(path)
    if target.exists(): raise FileExistsError(f'refusing to overwrite {target}')
    result = compose_studio_project(project, source_root)
    target.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='.axm-studio-', dir=target.parent))
    try:
        replay = copy.deepcopy(project)
        for index, (id, body) in enumerate(result['sources'].items()):
            relative = f'sources/{index:03d}.png'
            atomic_write_bytes(stage / relative, body)
            replay['sources'][id] = relative
        atomic_write_bytes(stage / 'composition.png', result['png'])
        atomic_write_json(stage / 'request.json', project)
        atomic_write_json(stage / 'project.json', replay)
        atomic_write_json(stage / 'normalized-recipe.json', result['recipe'])
        atomic_write_json(stage / 'receipt.json', result['receipt'])
        if target.exists(): raise FileExistsError(f'refusing to overwrite {target}')
        stage.rename(target)
    finally:
        if stage.exists(): shutil.rmtree(stage)
    return result['receipt']
