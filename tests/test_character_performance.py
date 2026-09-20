"""Check fitted performance against decoded world positions and contact geometry."""
from copy import deepcopy
import json
import math
from pathlib import Path
import tempfile
import unittest

from axm_uc.character_motion import build_character_motion, CharacterMotionError
from axm_uc.character_performance import solve_chain
from axm_uc.character_recipe import compile_character_recipe, publish_character_recipe, CharacterRecipeError
from axm_uc.game_pose_runtime import GamePoseAsset
from axm_uc.machine import UniversalCreationMachine

ROOT = Path(__file__).resolve().parents[1]


def recipe():
    return json.loads((ROOT/'examples/character-motion/seedling-performance.json').read_text())['inputs']['recipe']


def taller(source):
    result = deepcopy(source)
    for part in result['form']['parts']:
        part['scale'] = [1.25, 1, 1.3]
        part['translation'] = [v*s for v, s in zip(part.get('translation', [0,0,0]), [1.25,1,1.3])]
    return result


def build(source):
    compiled = compile_character_recipe(source)
    built = build_character_motion(compiled['specification'], compiled['motion'])
    asset = GamePoseAsset(built['body'])
    nodes = {node['name']: i for i, node in enumerate(built['document']['nodes'])}
    return compiled, built, asset, nodes


class CharacterPerformanceTests(unittest.TestCase):
    def test_same_template_refits_different_proportions_and_replays(self):
        first = recipe()
        other = taller(first)
        a, ab, aa, _ = build(first)
        b, bb, ba, _ = build(other)
        self.assertEqual(first['performance'], other['performance'])
        self.assertNotEqual(a['performance']['landmarks'], b['performance']['landmarks'])
        self.assertNotEqual(a['motion']['skin'], b['motion']['skin'])
        self.assertNotEqual(ab['body'], bb['body'])
        self.assertEqual(bb['body'], build(other)[1]['body'])
        for c, built, asset in ((a,ab,aa),(b,bb,ba)):
            for p, mesh in zip(c['specification']['primitives'], asset.sample(vertices=True)['meshes']):
                for expected, actual in zip(p['positions'], mesh['positions']):
                    self.assertLess(math.dist(expected, actual), 1e-6)
            for rows in c['motion']['skin'].values():
                for row in rows:
                    self.assertAlmostEqual(sum(row['weights']), 1)
                    self.assertTrue(all(w >= 0 for w in row['weights']))
            proof = built['motion_validation']['performance']
            self.assertEqual(proof['verified_targets'], 123)
            self.assertGreater(proof['verified_contact_samples'], 0)
            self.assertLess(proof['max_sample_target_error_m'], 1e-5)

    def test_walk_support_vertices_stay_planted_and_swing_clears_ground(self):
        c, _, asset, nodes = build(recipe())
        observations = c['performance']['observations'][0]['samples']
        rest = asset.sample(vertices=True)
        foot_mesh = {side: next(m for m in rest['meshes'] if m['node'] == nodes[side+'-foot'])
                     for side in ('left','right')}
        prior, lifted = {}, 0
        for row in observations:
            side = row['joint'].split('-')[0]
            pose = asset.sample('walk', row['time'], vertices=True)
            mesh = next(m for m in pose['meshes'] if m['node'] == nodes[side+'-foot'])
            actual = asset.point(pose, nodes[row['joint']])
            self.assertLess(math.dist(actual, row['target']), 1e-6)
            for p, q in zip(foot_mesh[side]['positions'], mesh['positions']):
                # End counter-rotation keeps the entire rigid foot level, not just its joint.
                expected = [v + t-r for v, t, r in zip(p, row['target'], c['performance']['landmarks'][row['joint']])]
                self.assertLess(math.dist(q, expected), 1e-6)
            height = min(p[2] for p in mesh['positions'])
            if row['contact']:
                self.assertAlmostEqual(height, 0, places=6)
                if side in prior and prior[side]['contact'] and row['time'] < 2:
                    self.assertLess(math.dist(row['target'], prior[side]['target']), 1e-9)
            elif height > .02:
                lifted += 1
            prior[side] = row
        self.assertGreater(lifted, 5)
        start, end = asset.sample('walk',0), asset.sample('walk',2)
        delta = [b-a for a,b in zip(asset.point(start,nodes['root']),asset.point(end,nodes['root']))]
        self.assertLess(math.dist(delta,[0,.22,0]),1e-6)
        for side in ('left','right'):
            # A cycle repeats relative pose while advancing the root by one stride.
            p, q = asset.point(start,nodes[side+'-ankle']),asset.point(end,nodes[side+'-ankle'])
            self.assertLess(math.dist([b-a for a,b in zip(p,q)],delta),1e-6)

    def test_reach_target_stays_in_world_space_when_root_moves(self):
        r = recipe()
        r['performance']['clips'][1]['root_translation'] = [0,.03,0]
        c, _, asset, nodes = build(r)
        for row in c['performance']['observations'][1]['samples']:
            pose = asset.sample('reach',row['time'])
            self.assertLess(math.dist(asset.point(pose,nodes['left-ankle']),row['target']),1e-6)
        # The peak was defined in foot bounds: depth .33, height .12, offset .55/1.
        peak = asset.point(asset.sample('reach',1),nodes['left-ankle'])
        self.assertLess(math.dist(peak,[-.18,.1835,.24]),1e-6)

    def test_nonplanar_solver_preserves_lengths_and_reconstructs_endpoint(self):
        start, middle, end, target = [1,2,3],[1.2,2.9,3.2],[1.7,3.4,3.8],[1.8,2.4,3.7]
        q1, q2, _, elbow = solve_chain(start,middle,end,target,[0,1,0])
        self.assertAlmostEqual(math.dist(start,elbow),math.dist(start,middle))
        self.assertAlmostEqual(math.dist(elbow,target),math.dist(middle,end))
        def rotate(q,v):
            x,y,z,w=q
            matrix=[[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],
                    [2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],
                    [2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]]
            return [sum(a*b for a,b in zip(row,v)) for row in matrix]
        upper=rotate(q1,[b-a for a,b in zip(start,middle)])
        lower=rotate(q1,rotate(q2,[b-a for a,b in zip(middle,end)]))
        self.assertLess(math.dist([a+b+c for a,b,c in zip(start,upper,lower)],target),1e-8)

    def test_live_route_retains_fitting_causes_and_exact_replay(self):
        with tempfile.TemporaryDirectory() as t:
            target=Path(t)/'body.glb'
            r=recipe()
            result=UniversalCreationMachine(ROOT).create({'kind':'character-performance-asset','inputs':{'path':str(target),'recipe':r}})
            self.assertEqual(result['type'],'CREATION_RESULT',result)
            source=json.loads(target.with_suffix('.glb.source.json').read_text())
            self.assertEqual(source['recipe']['performance'],r['performance'])
            self.assertEqual(len(source['performance']['landmarks']),7)
            self.assertEqual(source['artifact']['motion_validation']['performance']['verified_targets'],123)
            self.assertLess(source['artifact']['motion_validation']['performance']['max_sample_target_error_m'],1e-5)
            self.assertTrue(source['source_authority'])
            self.assertFalse(source['automatic_canon_admission'])
            replay=Path(t)/'replay.glb'
            publish_character_recipe(replay,source['recipe'])
            self.assertEqual(target.read_bytes(),replay.read_bytes())

    def test_invalid_or_unsupported_performance_is_refused(self):
        mutations=[
            lambda r:r['performance'].update(body_family='different'),
            lambda r:r['performance']['joints'][1]['anchor'].update(part='missing'),
            lambda r:r['performance']['joints'][1]['anchor'].update(fraction=[2,0,0]),
            lambda r:r['performance']['joints'][1].update(parent='left-ankle'),
            lambda r:r['performance']['bindings'].pop('body'),
            lambda r:r['performance']['bindings']['left-upper']['segment_weights'].update(max_influences=5),
            lambda r:r['performance']['bindings']['left-upper']['segment_weights'].update(segments=[['left-hip','left-hip']]),
            lambda r:r['performance']['clips'][0].update(stride=10),
            lambda r:r['performance']['clips'][0].update(up_axis=1),
            lambda r:r['performance']['clips'][0].update(samples=True),
            lambda r:r['performance']['clips'][0]['chains'][0].update(max_bend_degrees=1),
            lambda r:r['performance']['clips'][0]['chains'][0].update(pole=[0,0,0]),
            lambda r:r['performance']['clips'][1]['chains'][0]['targets'][1].update(at=0),
            lambda r:r['performance']['clips'][1]['chains'][0]['targets'][1].update(point=[99,99,99]),
            lambda r:r.update(rig={'schema':'axm.character-rig/v0.1'}),
        ]
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                r=recipe();mutate(r)
                with self.assertRaises(CharacterRecipeError):
                    compile_character_recipe(r)
        for args in (([0,0,0],[0,0,0],[1,0,0],[.5,0,0],[0,1,0]),
                     ([0,0,0],[1,1,0],[2,0,0],[1,0,0],[1,0,0])):
            with self.assertRaises(CharacterMotionError):
                solve_chain(*args)


if __name__ == '__main__':
    unittest.main()
