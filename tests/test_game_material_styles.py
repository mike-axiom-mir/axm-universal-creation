import copy
import hashlib
import io
import json
import math
from pathlib import Path
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from axm_uc.donor_metal import painted_metal_fields, PaintedMetalSpec
from axm_uc.fabric_material import fabric_fields, FabricSpec
from axm_uc.game_material_styles import (
    DEFAULT_COLORS, FAMILIES, FINISHES, apply_finish, game_material_fields,
    game_material_request, generate_game_material, _normal_from_height,
)
from axm_uc.project import ProjectError
from axm_uc.visual_assets_cli import main
from axm_uc.visual_learning import inspect_png


class GameMaterialStyleTests(unittest.TestCase):
    def test_realism_is_identity_and_donors_are_unchanged(self):
        for family, original in [
            ('painted-metal', painted_metal_fields(16, 7, PaintedMetalSpec(paint_rgb=DEFAULT_COLORS['painted-metal']))),
            ('woven-fabric', fabric_fields(16, 7, FabricSpec(base_rgb=DEFAULT_COLORS['woven-fabric']))),
        ]:
            before = copy.deepcopy(original)
            self.assertEqual(game_material_fields(family, 16, 7), original)
            self.assertEqual(apply_finish(original, 16), original)
            apply_finish(original, 16, 'graphic-toon')
            self.assertEqual(original, before)

    def test_all_family_finish_pairs_preserve_pbr_contract(self):
        for family in FAMILIES:
            raw = game_material_fields(family, 16, 9)
            for finish in FINISHES:
                with self.subTest(family=family, finish=finish.name):
                    fields = game_material_fields(family, 16, 9, finish.name)
                    for channels, pixels in fields.values():
                        self.assertEqual(len(pixels), 16 * 16 * channels)
                    orm = fields['orm'][1]
                    self.assertEqual(orm[0::3], raw['ao'][1])
                    self.assertEqual(orm[1::3], fields['roughness'][1])
                    self.assertEqual(orm[2::3], raw['orm'][1][2::3])
                    if family != 'painted-metal':
                        self.assertEqual(orm[2::3], bytes(256))
                    for i in range(0, len(fields['normal'][1]), 3):
                        n = [c / 127.5 - 1 for c in fields['normal'][1][i:i + 3]]
                        self.assertAlmostEqual(math.sqrt(sum(c * c for c in n)), 1, delta=.014)

    def test_styles_change_relief_and_response_not_just_color(self):
        raw = game_material_fields('painted-metal', 32, 17)
        comic = apply_finish(raw, 32, 'comic-salvage')
        graphic = apply_finish(raw, 32, 'graphic-toon')
        self.assertNotEqual(comic['normal'], raw['normal'])
        self.assertNotEqual(graphic['roughness'], raw['roughness'])
        self.assertEqual(graphic['normal'][1], bytes([128, 128, 255]) * 1024)
        self.assertEqual(graphic['height'], raw['height'])
        self.assertEqual(graphic['ao'], raw['ao'])

    def test_seed_repeat_variation_and_family_differences(self):
        fingerprints = set()
        for family in FAMILIES:
            fields = game_material_fields(family, 16, 81, 'painted-adventure')
            self.assertEqual(fields, game_material_fields(family, 16, 81, 'painted-adventure'))
            self.assertNotEqual(fields['base_color'], game_material_fields(family, 16, 82, 'painted-adventure')['base_color'])
            fingerprints.add(hashlib.sha256(fields['normal'][1]).digest())
        self.assertGreater(len(fingerprints), 3)

    def test_new_family_normal_orientation_and_flat_surface(self):
        self.assertEqual(_normal_from_height([.5] * 256, 16, 1), bytes([128, 128, 255]) * 256)
        slope = [y / 16 for y in range(16) for x in range(16)]
        normal = _normal_from_height(slope, 16, 1)
        self.assertGreater(normal[(8 * 16 + 8) * 3 + 1], 128)

    def test_invalid_input_and_inconsistent_orm_rejected(self):
        for kw in [{'size': True}, {'size': 513}, {'seed': -1}, {'seed': True},
                   {'finish': 'unknown'}, {'color': [1, 2, math.nan]}, {'color': []}]:
            with self.subTest(kw=kw), self.assertRaises(ValueError):
                game_material_fields('ceramic', **kw)
        with self.assertRaises(ValueError):
            game_material_fields('unknown')
        fields = game_material_fields('rubber', 16)
        fields['orm'] = (3, bytes(256 * 3))
        with self.assertRaisesRegex(ValueError, 'ORM'):
            apply_finish(fields, 16)

    def test_actual_cli_publication_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / 'material'
            with redirect_stdout(io.StringIO()):
                self.assertEqual(main(['game-material', 'carved-wood', str(target), '--size', '16',
                                      '--finish', 'painted-adventure', '--color', '150', '90', '40']), 0)
            manifest = json.loads((target / 'game-material.json').read_text())
            self.assertEqual(manifest['finish'], 'painted-adventure')
            self.assertEqual(manifest['color'], [150, 90, 40])
            for row in manifest['maps'].values():
                path = target / row['file']
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), row['sha256'])
                report = inspect_png(path)
                self.assertEqual(report['width'], 16)
                self.assertEqual(report['height'], 16)
            before = {p.name: p.read_bytes() for p in target.iterdir() if p.is_file()}
            with self.assertRaises(ProjectError):
                generate_game_material(target, 'ceramic', 16)
            self.assertEqual(before, {p.name: p.read_bytes() for p in target.iterdir() if p.is_file()})

    def test_request_uses_existing_machine_protocol(self):
        request = game_material_request('out', 'woven-fabric', 16)
        self.assertEqual(request['kind'], 'mixed-media-project')
        self.assertIn('thickness.png', request['inputs']['binary_files'])
        self.assertEqual(len(request['inputs']['checks']), len(request['inputs']['binary_files']))


if __name__ == '__main__':
    unittest.main()
