from copy import deepcopy
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from axm_uc.character_recipe import compile_character_recipe, publish_character_recipe, CharacterRecipeError
from axm_uc.character_motion import build_character_motion
from axm_uc.game_pose_runtime import GamePoseAsset
from axm_uc.machine import UniversalCreationMachine
from tests.test_form_character_recipe import character_recipe

ROOT = Path(__file__).resolve().parents[1]

def recipe():
    r = character_recipe()
    r['rig'] = {'schema': 'axm.character-rig/v0.1', 'joints': [
        {'id': 'root', 'parent': None, 'translation': [0,0,0]},
        {'id': 'branch', 'parent': 'root', 'translation': [0,0,.85]}],
        'bindings': {'trunk': {'joint': 'root'}, 'eye-shell': {'joint': 'root'}, 'branch-left': {'joint': 'branch'}}}
    r['animation'] = [{'name': 'wave', 'tracks': [{'joint': 'branch', 'path': 'rotation',
        'times': [0,1,2], 'values': [[0,0,0,1], [0,math.sin(math.pi/4),0,math.cos(math.pi/4)], [0,0,0,1]]}]}]
    return r

def build(r):
    c = compile_character_recipe(r)
    return build_character_motion(c['specification'], c['motion']), c

class MotionTests(unittest.TestCase):
    def test_rest_pose_and_rotation_against_analytic_positions(self):
        b, c = build(recipe()); a = GamePoseAsset(b['body'])
        rest, posed = a.sample(vertices=True), a.sample('wave', 1, vertices=True)
        for group, observed in zip(c['specification']['primitives'], rest['meshes']):
            for expected, actual in zip(group['positions'], observed['positions']):
                for x,y in zip(expected, actual): self.assertAlmostEqual(x,y,places=5)
        for p,q in zip(rest['meshes'][1]['positions'], posed['meshes'][1]['positions']):
            for expected, actual in zip([p[2]-.85,p[1],.85-p[0]], q): self.assertAlmostEqual(expected,actual,places=5)
        self.assertEqual(rest['meshes'][0], posed['meshes'][0])
        self.assertEqual(a.sample('wave', 0, vertices=True)['meshes'], a.sample('wave', 2, vertices=True)['meshes'])

    def test_axis_blend_deforms_fractionally(self):
        r=recipe();r['rig']['bindings']['trunk']={'axis_blend': {'from':'root','to':'branch','axis':2,'range':[0,2]}}
        r['animation'][0]['tracks']=[{'joint':'branch','path':'translation','times':[0,1], 'values':[[0,0,.85],[2,0,.85]]}]
        b,c=build(r);a=GamePoseAsset(b['body']);rest=a.sample(vertices=True);posed=a.sample('wave',1,vertices=True)
        for p,q in zip(rest['meshes'][0]['positions'],posed['meshes'][0]['positions']):
            self.assertAlmostEqual(q[0]-p[0],min(1,max(0,p[2]/2))*2,places=5)

    def test_reuse_across_shape_changes_is_deterministic(self):
        first=recipe();second=deepcopy(first);second['form']['parts'][1]['radius']=[.12,.09,.04]
        b,_=build(first);other,_=build(second)
        self.assertNotEqual(b['body'],other['body']);self.assertEqual(other['body'],build(second)[0]['body'])
        self.assertEqual(first['rig'],second['rig']);self.assertEqual(first['animation'],second['animation'])

    def test_static_route_unchanged(self):
        c=compile_character_recipe(character_recipe());self.assertIsNone(c['motion'])
        self.assertEqual(c['rig_status'],'NOT_PRESENT')

    def test_invalid_motion_is_refused(self):
        mutations=[lambda r:r['rig']['joints'][0].update(parent='branch'),
                   lambda r:r['rig']['bindings'].pop('trunk'),
                   lambda r:r['rig']['bindings']['trunk'].update(joint='missing'),
                   lambda r:r['rig']['joints'][1].update(rotation=[0,0,0,1]),
                   lambda r:r['animation'][0]['tracks'][0].update(times=[0,0,1]),
                   lambda r:r['animation'][0]['tracks'][0].update(values=[[0,0,0,0]]*3),
                   lambda r:r['animation'][0]['tracks'][0].update(interpolation='CUBICSPLINE'),
                   lambda r:r['rig']['bindings'].update(trunk={'weights':[]}),
                   lambda r:r['rig']['joints'][0].update(translation=[float('nan'),0,0])]
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                r=recipe();mutate(r)
                with self.assertRaises(CharacterRecipeError):compile_character_recipe(r)

    def test_explicit_mixed_weights(self):
        r=recipe();count=compile_character_recipe(character_recipe())['specification']['primitives'][0]['positions']
        r['rig']['bindings']['trunk']={'weights':[{'root':.25,'branch':.75} for _ in count]}
        b,c=build(r);self.assertEqual(c['motion']['skin']['trunk'][0]['weights'],[.25,.75,0,0])
        r['rig']['bindings']['trunk']['weights'][0]={'root':.5}
        with self.assertRaises(CharacterRecipeError):compile_character_recipe(r)

    def test_live_route_retains_and_replays_source(self):
        with tempfile.TemporaryDirectory() as t:
            path=Path(t)/'character.glb'
            result=UniversalCreationMachine(ROOT).create({'kind':'character-recipe-asset','inputs':{'path':str(path),'recipe':recipe()}})
            self.assertEqual(result['type'],'CREATION_RESULT',result)
            source=json.loads(path.with_suffix('.glb.source.json').read_text())
            replay=Path(t)/'replay.glb';publish_character_recipe(replay,source['recipe'])
            self.assertEqual(path.read_bytes(),replay.read_bytes())
            self.assertTrue(source['source_authority']);self.assertFalse(source['automatic_canon_admission'])
            self.assertEqual(source['rig_status'],'EXPLICIT_SKIN_COMPILED')

    def test_sidecar_failure_restores_both_prior_files(self):
        with tempfile.TemporaryDirectory() as t:
            path=Path(t)/'character.glb';publish_character_recipe(path,recipe())
            side=path.with_suffix('.glb.source.json');before=(path.read_bytes(),side.read_bytes())
            r=recipe();r['form']['parts'][1]['radius']=[.1,.08,.03]
            with patch('axm_uc.creator_retention.atomic_write_json',side_effect=OSError('disk')):
                with self.assertRaises(OSError):publish_character_recipe(path,r,replace=True)
            self.assertEqual(before,(path.read_bytes(),side.read_bytes()))

    def test_step_and_parent_translation(self):
        r=recipe();r['animation'][0]['tracks']=[{'joint':'root','path':'translation','times':[0,1], 'values':[[0,0,0],[2,0,0]],'interpolation':'STEP'}]
        b,_=build(r);a=GamePoseAsset(b['body']);rest=a.sample(vertices=True)
        self.assertEqual(rest['meshes'],a.sample('wave',.5,vertices=True)['meshes'])
        for p,q in zip(rest['meshes'][1]['positions'],a.sample('wave',1,vertices=True)['meshes'][1]['positions']):
            self.assertAlmostEqual(q[0]-p[0],2,places=5)
