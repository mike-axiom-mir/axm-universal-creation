"""Pixel fixtures and recovery checks against the actual pinned JavaScript."""
import copy
from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from axm_uc import studio_compositor as studio
from axm_uc.fabric_noise import png_bytes
from axm_uc.visual_assets_cli import main


def project(layers=None, width=1, height=1, sources=None):
    return {'schema':studio.SCHEMA, 'sources':sources or {},
            'recipe':{'schema':'axm.raster-composition/v1',
                      'canvas':{'width':width,'height':height},
                      'layers':layers or [{'id':'base','fill':'#204080'}]}}


def pixels(body):
    # Independent decoder for UC's unfiltered output PNG, not its intake decoder.
    at, compressed, size = 8, b'', None
    while at < len(body):
        n = struct.unpack_from('>I', body, at)[0]
        kind, data = body[at+4:at+8], body[at+8:at+8+n]
        if kind == b'IHDR': size = struct.unpack('>IIBBBBB', data)[:2]
        if kind == b'IDAT': compressed += data
        at += n + 12
    w, h = size
    raw = zlib.decompress(compressed)
    assert len(raw) == h * (4*w+1)
    result = []
    for y in range(h):
        row = raw[y*(4*w+1):(y+1)*(4*w+1)]
        assert row[0] == 0
        result.extend(tuple(row[i:i+4]) for i in range(1, len(row), 4))
    return result


class StudioRecoveryTests(unittest.TestCase):
    def test_layer_edits_preserve_project_and_source_links(self):
        p = project(sources={'paint':'paint.png'})
        original = copy.deepcopy(p)
        edited = studio.edit_studio_layers(p,[{'op':'add','layer':{'id':'ink','fill':'#00FF00'}},
                 {'op':'change','id':'ink','patch':{'opacity':0.5}},
                 {'op':'move','id':'ink','before':'base'}])
        self.assertEqual([x['id'] for x in edited['recipe']['layers']], ['ink','base'])
        self.assertEqual(edited['recipe']['layers'][0]['opacity'], 0.5)
        self.assertEqual(edited['sources'],original['sources'])
        self.assertEqual(studio.edit_studio_layers(edited,[{'op':'remove','id':'ink'}]),p)
        self.assertEqual(p,original)

    def test_invalid_edit_is_transactional(self):
        p=project(); original=copy.deepcopy(p)
        for operation in [{'op':'remove','id':'missing'},{'op':'remove','id':'base'},
                          {'op':'change','id':'base','patch':{'id':'renamed'}},
                          {'op':'add','layer':{'id':'base','fill':'#FFFFFF'}},
                          {'op':'move','id':'base','before':'missing'},{'op':'unknown'}]:
            with self.subTest(operation=operation), self.assertRaises(ValueError):
                studio.edit_studio_layers(p,[operation])
        self.assertEqual(p,original)

    def test_original_files_match_pinned_git_blobs(self):
        manifest = json.loads((ROOT / 'donors/collaboration-studio/manifest.json').read_text())
        self.assertEqual(manifest['commit'], studio.DONOR_COMMIT)
        studio_paths = []
        for item in manifest['files']:
            body = (ROOT / item['local']).read_bytes()
            digest = hashlib.sha1(b'blob ' + str(len(body)).encode() + b'\0' + body).hexdigest()
            self.assertEqual(digest, item['git_blob_sha'], item['local'])
            self.assertEqual(item['modifications'], 'none')
            if item['source'].startswith('tools/studio/'): studio_paths.append(item['source'])
        self.assertEqual(len(studio_paths), 19)

    def test_catalog_and_missing_runtime_are_truthful(self):
        self.assertIn('Node.js', studio.studio_compositor_catalog()['runtime'])
        with patch.object(studio.shutil, 'which', return_value=None):
            with self.assertRaisesRegex(RuntimeError, 'requires a local Node'):
                studio.compose_studio_project(project(), '.')


@unittest.skipUnless(shutil.which('node'), 'local Node runtime absent; dedicated CI supplies Node 22')
class StudioCompositorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def run_project(self, request):
        return studio.compose_studio_project(request, self.root)

    def source(self, name, values, width=None):
        body = png_bytes(width or len(values), 1, 4, bytes(c for p in values for c in p))
        (self.root / name).write_bytes(body)
        return body

    def test_catalog_matches_executed_donor(self):
        actual = studio._run({'catalog':True})
        for key in ('blends','filters'):
            self.assertEqual(actual[key], studio.studio_compositor_catalog()[key])

    def test_fractional_alpha_and_order(self):
        layers = [{'id':'blue','fill':'#0000FF80'},{'id':'red','fill':'#FF000080'}]
        self.assertEqual(pixels(self.run_project(project(layers))['png']), [(170,0,85,192)])
        self.assertEqual(pixels(self.run_project(project(layers[::-1]))['png']), [(85,0,170,192)])

    def test_blend_mode_analytical_fixtures(self):
        for mode, expected in [('multiply',(32,32,16,255)),('screen',(160,160,144,255)),
                               ('difference',(64,64,96,255)),('add',(192,192,160,255))]:
            with self.subTest(mode=mode):
                p = project([{'id':'base','fill':'#408080'},
                             {'id':'ink','fill':'#804020','blend_mode':mode}])
                self.assertEqual(pixels(self.run_project(p)['png']), [expected])

    def test_masks_offsets_and_hidden_layer(self):
        self.source('mask.png', [(255,255,255,255),(0,0,0,0)])
        p = project([{'id':'base','fill':'#0000FF'},
                     {'id':'ink','fill':'#FF0000','opacity':0.5,
                      'mask':{'source_artifact_id':'mask','channel':'alpha'}},
                     {'id':'hidden','fill':'#00FF00','visible':False}], width=2, sources={'mask':'mask.png'})
        self.assertEqual(pixels(self.run_project(p)['png']), [(128,0,128,255),(0,0,255,255)])
        p['recipe']['layers'][1]['mask'].update(channel='luminance',invert=True)
        self.assertEqual(pixels(self.run_project(p)['png']), [(0,0,255,255),(128,0,128,255)])
        p['recipe']['layers'][1]['offset'] = {'x':-1,'y':0}
        self.assertEqual(pixels(self.run_project(p)['png']), [(128,0,128,255),(0,0,255,255)])

    def test_point_filters_known_results(self):
        cases = [({'type':'brightness','value':1},(255,255,255,255)),
                 ({'type':'contrast','value':-1},(128,128,128,255)),
                 ({'type':'saturation','value':0},(43,43,43,255)),
                 ({'type':'grayscale','amount':1},(43,43,43,255)),
                 ({'type':'hue','value':120},(0,200,0,255)),
                 ({'type':'invert','amount':1},(55,255,255,255)),
                 ({'type':'gamma','value':1},(200,0,0,255)),
                 ({'type':'threshold','value':0.5},(0,0,0,255)),
                 ({'type':'posterize','levels':2},(255,0,0,255)),
                 ({'type':'tint','colour':'#102030','amount':1},(16,32,48,255))]
        for effect, expected in cases:
            with self.subTest(effect=effect):
                p = project([{'id':'base','fill':'#C80000','filters':[effect]}])
                self.assertEqual(pixels(self.run_project(p)['png']), [expected])

    def test_spatial_filters_and_global_filter(self):
        self.source('line.png', [(0,0,0,255),(255,255,255,255),(0,0,0,255)])
        p = project([{'id':'line','source_artifact_id':'line','filters':[{'type':'blur','radius':1}]}],
                    width=3, sources={'line':'line.png'})
        self.assertEqual(pixels(self.run_project(p)['png']), [(128,128,128,255),(85,85,85,255),(128,128,128,255)])
        p['recipe']['layers'][0]['filters'] = [{'type':'sharpen','amount':1}]
        self.assertEqual(pixels(self.run_project(p)['png']), [(0,0,0,255),(255,255,255,255),(0,0,0,255)])
        p['recipe']['layers'][0]['filters'] = [{'type':'pixelate','size':2}]
        p['recipe']['global_filters'] = [{'type':'invert','amount':1}]
        self.assertEqual(pixels(self.run_project(p)['png']), [(127,127,127,255),(127,127,127,255),(255,255,255,255)])

    def test_publish_replays_and_preserves_exact_sources_and_request(self):
        original = self.source('ink.png', [(20,100,230,180),(250,20,80,255)])
        p = project([{'id':'ink','source_artifact_id':'ink','filters':[{'type':'invert','amount':0.5}]}],
                    width=2, sources={'ink':'ink.png'})
        p['recipe']['artist_extension'] = {'intent':'preserve this even when donor normalization omits it'}
        before = copy.deepcopy(p)
        target = self.root / 'published'
        receipt = studio.publish_studio_project(target, p, self.root)
        replay = json.loads((target / 'project.json').read_text())
        replay_result = studio.compose_studio_project(replay, target)
        self.assertEqual(replay_result['png'], (target / 'composition.png').read_bytes())
        self.assertEqual((target / replay['sources']['ink']).read_bytes(), original)
        self.assertEqual((self.root / 'ink.png').read_bytes(), original)
        self.assertEqual(p, before)
        self.assertEqual(json.loads((target / 'request.json').read_text()), before)
        self.assertNotIn('artist_extension', json.loads((target / 'normalized-recipe.json').read_text()))
        self.assertEqual(receipt['sources']['ink']['png_sha256'], hashlib.sha256(original).hexdigest())
        self.assertFalse(receipt['visual_approval'])
        with self.assertRaises(FileExistsError): studio.publish_studio_project(target, p, self.root)

    def test_invalid_paths_and_reserved_source_ids(self):
        for name in ('../escape.png','/outside.png','..\\escape.png'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.run_project(project(sources={'ink':name}))
        with self.assertRaisesRegex(ValueError,'invalid source ID'):
            self.run_project(project(sources={'constructor':'ink.png'}))
        outside = self.root.parent / (self.root.name + '-outside.png')
        outside.write_bytes(png_bytes(1,1,4,bytes([1,2,3,255])))
        self.addCleanup(outside.unlink)
        try: (self.root / 'link.png').symlink_to(outside)
        except OSError: return  # Windows may prohibit symlinks; traversal checks still ran.
        with self.assertRaisesRegex(ValueError,'escapes'):
            self.run_project(project(sources={'ink':'link.png'}))

    def test_fail_closed_unsupported_and_budgets(self):
        for update in ({'alpha':False},{'width':1025},{'width':True}):
            p = project(); p['recipe']['canvas'].update(update)
            with self.subTest(update=update), self.assertRaises(ValueError): self.run_project(p)
        p = project(); p['recipe']['layers'][0]['filters'] = [{'type':'unknown'}]
        with self.assertRaisesRegex(ValueError,'unsupported filter'): self.run_project(p)
        p = project(width=1024,height=1024)
        p['recipe']['layers'][0]['filters'] = [{'type':'blur','radius':12}]
        with self.assertRaisesRegex(ValueError,'work budget'): self.run_project(p)
        self.source('small.png',[(1,1,1,255)])
        p = project([{'id':'offcanvas','fill':'#FFFFFF','offset':{'x':-10},
                      'mask':{'source_artifact_id':'mask'}}],width=2,sources={'mask':'small.png'})
        with self.assertRaisesRegex(ValueError,'mask dimensions'): self.run_project(p)

    def test_profile_and_corrupt_png_rejected(self):
        original = png_bytes(1,1,4,bytes([20,30,40,255]))
        for kind, data in [(b'iCCP',b'profile'),(b'gAMA',struct.pack('>I',100000)),(b'acTL',struct.pack('>II',2,0))]:
            chunk = struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
            (self.root / 'source.png').write_bytes(original[:33]+chunk+original[33:])
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                self.run_project(project(sources={'ink':'source.png'}))
        (self.root / 'source.png').write_bytes(original[:-1]+bytes([original[-1]^1]))
        with self.assertRaises(ValueError): self.run_project(project(sources={'ink':'source.png'}))

    def test_timeout_and_failed_publish_leave_no_output(self):
        target = self.root / 'out'
        with patch.object(studio.subprocess,'run',side_effect=subprocess.TimeoutExpired('node',30)):
            with self.assertRaisesRegex(RuntimeError,'30-second'):
                studio.publish_studio_project(target,project(),self.root)
        with patch.object(studio,'atomic_write_json',side_effect=OSError('disk failure')):
            with self.assertRaises(OSError): studio.publish_studio_project(target,project(),self.root)
        self.assertFalse(target.exists())
        self.assertEqual(list(self.root.iterdir()),[])

    def test_cli_publication(self):
        source = self.root / 'project.json'; source.write_text(json.dumps(project()))
        with redirect_stdout(io.StringIO()): main(['studio-compose',str(source),str(self.root / 'cli')])
        self.assertEqual(pixels((self.root / 'cli/composition.png').read_bytes()),[(32,64,128,255)])
        edits = self.root / 'edits.json'
        edits.write_text(json.dumps([{'op':'add','layer':{'id':'ink','fill':'#AABBCC'}}]))
        with redirect_stdout(io.StringIO()):
            main(['studio-edit',str(self.root / 'cli/project.json'),str(edits),str(self.root / 'revision')])
        self.assertEqual(pixels((self.root / 'revision/composition.png').read_bytes()),[(170,187,204,255)])
        self.assertEqual(pixels((self.root / 'cli/composition.png').read_bytes()),[(32,64,128,255)])


if __name__ == '__main__': unittest.main()
