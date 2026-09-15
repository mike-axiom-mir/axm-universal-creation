"""Exercise the exact Creative Precision Fabric JavaScript foundations in CI."""
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
PROGRAM = ROOT / 'capabilities' / 'platform-hands' / 'shared' / 'asset-hands' / 'upgrade-program'


@unittest.skipUnless(shutil.which('node'), 'Node is required; dedicated CI supplies it')
class CreativePrecisionFabricTests(unittest.TestCase):
    def run_node(self, name):
        result = subprocess.run(
            ['node', str(PROGRAM / name)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('"status": "PASS"', result.stdout)

    def test_mask_brush_and_effect_foundations(self):
        self.run_node('creative-precision-selftest.js')

    def test_pixel_selection_and_transform_foundations(self):
        self.run_node('precision-raster-selftest.js')

    def test_creative_recipe_composition(self):
        self.run_node('creative-recipes-selftest.js')

    def test_executable_creative_hand_wave(self):
        self.run_node('creative-hands-selftest.js')

    def test_advanced_executable_creative_hand_wave(self):
        self.run_node('creative-hands-wave3-selftest.js')

    def test_compositing_geometry_procedural_audio_timeline_wave(self):
        self.run_node('creative-hands-wave4-selftest.js')

    def test_precision_mesh_hand_wave(self):
        self.run_node('creative-mesh-hands-selftest.js')

    def test_face_edge_vertex_mesh_edit_wave(self):
        self.run_node('creative-mesh-edit-hands-selftest.js')


if __name__ == '__main__':
    unittest.main()
