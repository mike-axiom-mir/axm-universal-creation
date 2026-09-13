import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOD_SOURCE = ROOT / 'tools' / 'blender' / 'axm_rts_workshop_lods.py'
VERIFY_SOURCE = ROOT / 'tools' / 'blender' / 'verify_rts_workshop.py'
POLISH_SOURCE = ROOT / 'src' / 'axm_uc' / 'rts_polish.py'


class WorkshopLodLadderSourceTests(unittest.TestCase):
    def test_sources_parse(self):
        for path in (LOD_SOURCE, VERIFY_SOURCE, POLISH_SOURCE):
            ast.parse(path.read_text(encoding='utf-8'))

    def test_runtime_ladder_artifacts_are_explicit(self):
        combined = '\n'.join(path.read_text(encoding='utf-8') for path in (LOD_SOURCE, VERIFY_SOURCE, POLISH_SOURCE))
        for name in (
            'improvised-workshop-lod1.glb',
            'improvised-workshop-tactical.glb',
            'improvised-workshop-rts.glb',
            'improvised-workshop-far.glb',
        ):
            self.assertIn(name, combined)

    def test_target_bands_match_current_rts_policy(self):
        text = VERIFY_SOURCE.read_text(encoding='utf-8')
        for literal in ('20_000, 40_000', '4_000, 12_000', '500, 2_000'):
            self.assertIn(literal, text)
        self.assertIn('validate_lod_ladder', text)
        self.assertIn("'runtime_lod_target_bands':'TESTED'", text)

    def test_visual_and_target_acceptance_stay_separate(self):
        text = VERIFY_SOURCE.read_text(encoding='utf-8')
        for gate in (
            'lod_perceptual_equivalence',
            'target_rts_integration',
            'target_device_fps',
            'material_texture_budget_acceptance',
            'visual_quality',
        ):
            self.assertIn(f"'{gate}':'NOT_TESTED'", text)

    def test_execution_hand_requires_and_publishes_lod_stage(self):
        text = POLISH_SOURCE.read_text(encoding='utf-8')
        self.assertIn('axm_rts_workshop_lods.py', text)
        self.assertIn('lod-ladder-build.json', text)
        self.assertIn('game-readiness-gates.json', text)


if __name__ == '__main__':
    unittest.main()
