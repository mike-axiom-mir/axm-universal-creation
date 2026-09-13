import copy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from axm_uc.game_material_bridge import load_material_bundle
from axm_uc.game_material_styles import (
    FAMILIES, FINISHES, WearLayer, apply_layered_wear, game_material_fields, game_material_request,
    generate_game_material, layered_game_material_fields, protected_regions_mask,
)
from axm_uc.visual_assets_cli import main


class LayeredGameMaterialTests(unittest.TestCase):
    def test_every_family_finish_accepts_optional_layer_contract(self):
        for family in FAMILIES:
            for finish in FINISHES:
                with self.subTest(family=family, finish=finish.name):
                    result = layered_game_material_fields(family, 16, 17, finish.name,
                                                          layer=WearLayer(amount=.7))
                    self.assertEqual(result['orm'][1][0::3], result['ao'][1])
                    self.assertEqual(result['orm'][1][1::3], result['roughness'][1])
                    self.assertEqual(result['orm'][1][2::3], result['metallic'][1])
                    self.assertEqual(result['coat_height'][1],
                                     bytes(255 - v for v in result['exposed_mask'][1]))

    def test_zero_wear_preserves_runtime_maps_and_source(self):
        source = game_material_fields('painted-metal', 16, 5, 'comic-salvage')
        before = copy.deepcopy(source)
        result = apply_layered_wear(source, 16, 5, WearLayer(amount=0))
        for name in ('base_color', 'roughness', 'metallic', 'normal', 'ao', 'orm', 'height'):
            expected = source[name] if name in source else (1, source['orm'][1][2::3])
            self.assertEqual(result[name], expected)
        self.assertEqual(result['exposed_mask'][1], bytes(256))
        self.assertEqual(source, before)

    def test_protection_veto_is_exact_and_exposure_changes_pbr(self):
        size = 16
        source = game_material_fields('ceramic', size, 8, 'painted-adventure')
        protection = protected_regions_mask(size, [(0.25, 0.25, 0.75, 0.75)])
        result = apply_layered_wear(source, size, 8, WearLayer(amount=1), protection, bytes([255]) * 256)
        changed_outside = 0
        for i, protected in enumerate(protection):
            if protected:
                self.assertEqual(result['exposed_mask'][1][i], 0)
                self.assertEqual(result['base_color'][1][i * 3:i * 3 + 3], source['base_color'][1][i * 3:i * 3 + 3])
                self.assertEqual(result['roughness'][1][i], source['roughness'][1][i])
                self.assertEqual(result['metallic'][1][i], source['metallic'][1][i])
                self.assertEqual(result['normal'][1][i * 3:i * 3 + 3], source['normal'][1][i * 3:i * 3 + 3])
            else:
                changed_outside += result['base_color'][1][i * 3:i * 3 + 3] != source['base_color'][1][i * 3:i * 3 + 3]
                self.assertEqual(result['metallic'][1][i], 255)
        self.assertGreater(changed_outside, 100)
        self.assertEqual(result['orm'][1][0::3], source['ao'][1])
        self.assertEqual(result['orm'][1][1::3], result['roughness'][1])
        self.assertEqual(result['orm'][1][2::3], result['metallic'][1])

    def test_supplied_wear_amount_scales_and_normal_orientation_is_preserved(self):
        size = 16
        source = game_material_fields('rubber', size, 2, 'graphic-toon')
        ramp = bytes(round(y / (size - 1) * 255) for y in range(size) for _ in range(size))
        low = apply_layered_wear(source, size, 2, WearLayer(amount=.25), wear_mask=ramp)
        high_plus = apply_layered_wear(source, size, 2, WearLayer(amount=1), wear_mask=ramp)
        high_minus = apply_layered_wear(source, size, 2, WearLayer(amount=1), wear_mask=ramp,
                                        normal_convention='tangent -Y')
        self.assertLess(sum(low['exposed_mask'][1]), sum(high_plus['exposed_mask'][1]))
        index = (8 * size + 8) * 3 + 1
        self.assertLess(high_plus['normal'][1][index], 128)
        self.assertGreater(high_minus['normal'][1][index], 127)

    def test_procedural_layer_is_deterministic_distinct_and_not_only_color(self):
        source = game_material_fields('painted-metal', 32, 10, 'comic-salvage')
        a = apply_layered_wear(source, 32, 99, WearLayer(amount=.75))
        b = apply_layered_wear(source, 32, 99, WearLayer(amount=.75))
        c = apply_layered_wear(source, 32, 100, WearLayer(amount=.75))
        self.assertEqual(a, b)
        self.assertNotEqual(a['wear_mask'], c['wear_mask'])
        self.assertNotEqual(a['roughness'], source['roughness'])
        self.assertNotEqual(a['metallic'], source['metallic'])
        self.assertNotEqual(a['normal'], source['normal'])
        self.assertGreater(max(a['exposed_mask'][1]), 30)

    def test_publication_retains_masks_and_declares_sources(self):
        size = 16
        protection = protected_regions_mask(size, [(.35, .35, .65, .65)])
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / 'layered'
            generate_game_material(folder, 'painted-metal', size, 31, 'comic-salvage',
                                   layer=WearLayer(amount=.8), protected_mask=protection,
                                   protected_mask_source='authored-test-logo')
            bundle = load_material_bundle(folder)
            manifest = bundle['manifest']
            self.assertEqual(manifest['layers'][0]['wear_mask_source'], 'procedural-uv')
            self.assertEqual(manifest['layers'][0]['protected_mask_source'], 'authored-test-logo')
            for name in ('wear_mask', 'protection_mask', 'exposed_mask', 'coat_height'):
                self.assertIn(name, manifest['maps'])
                self.assertIn(name, bundle['pngs'])

    def test_supplied_masks_require_attributed_sources(self):
        mask = bytes(256)
        with self.assertRaisesRegex(ValueError, 'protected_mask_source'):
            game_material_request('out', 'rubber', 16, layer=WearLayer(), protected_mask=mask)
        with self.assertRaisesRegex(ValueError, 'wear_mask_source'):
            game_material_request('out', 'rubber', 16, layer=WearLayer(), wear_mask=mask)
        with self.assertRaisesRegex(ValueError, 'require a WearLayer'):
            game_material_request('out', 'rubber', 16, protected_mask=mask)

    def test_cli_publishes_pro_layer_and_refuses_orphan_controls(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / 'cli'
            with redirect_stdout(io.StringIO()):
                self.assertEqual(main(['game-material', 'painted-metal', str(folder), '--size', '16',
                                       '--finish', 'graphic-toon', '--layered-wear', '.7',
                                       '--substrate-color', '80', '90', '100',
                                       '--protect', '.3', '.3', '.7', '.7']), 0)
            manifest = json.loads((folder / 'game-material.json').read_text())
            self.assertEqual(manifest['layers'][0]['parameters']['amount'], .7)
            self.assertEqual(manifest['layers'][0]['protected_mask_source'], 'authored-cli-rectangles')
            with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                main(['game-material', 'rubber', str(Path(tmp) / 'bad'), '--protect', '0', '0', '1', '1'])

    def test_invalid_layer_and_masks_are_rejected(self):
        source = game_material_fields('rubber', 16)
        bad_layers = [WearLayer(amount=-1), WearLayer(amount=float('nan')),
                      WearLayer(substrate_rgb=(1, 2, 999)), WearLayer(scratch_count=True),
                      WearLayer(chip_scale=1), WearLayer(edge_normal_strength=2)]
        for layer in bad_layers:
            with self.subTest(layer=layer), self.assertRaises(ValueError):
                apply_layered_wear(source, 16, layer=layer)
        for mask in (b'', bytes(255), bytearray(256)):
            with self.subTest(mask=type(mask).__name__, length=len(mask)), self.assertRaises(ValueError):
                apply_layered_wear(source, 16, protected_mask=mask)
        for rectangles in ([(-1, 0, 1, 1)], [(0, 0, 0, 1)], [(0, 0, 1)], 'bad'):
            with self.subTest(rectangles=rectangles), self.assertRaises(ValueError):
                protected_regions_mask(16, rectangles)


if __name__ == '__main__':
    unittest.main()
