import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from axm_uc.game_material_bridge import LEGACY_NORMAL, load_material_bundle
from axm_uc.game_material_styles import FAMILIES, FINISHES, generate_game_material
from axm_uc.fabric_noise import _png_chunk, png_bytes
import zlib


class MaterialBundleTests(unittest.TestCase):
    def test_all_finishes_and_legacy_normal_resolution(self):
        with tempfile.TemporaryDirectory() as tmp:
            for family in FAMILIES:
                for finish in FINISHES:
                    folder = Path(tmp) / (family + finish.name)
                    generate_game_material(folder, family, 16, 47, finish.name)
                    bundle = load_material_bundle(folder)
                    expected = 'tangent -Y' if family in ('painted-metal', 'woven-fabric') else 'tangent +Y'
                    self.assertEqual(bundle['normal_convention'], expected)
                    self.assertEqual(bundle['dimensions'], [16, 16])
                    path = folder / 'game-material.json'
                    manifest = json.loads(path.read_text())
                    manifest['normal_convention'] = LEGACY_NORMAL
                    path.write_text(json.dumps(manifest))
                    self.assertEqual(load_material_bundle(folder)['normal_convention'], expected)

    def test_rectangular_dimensions_are_explicit_and_verified(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / 'paint'
            generate_game_material(folder, 'painted-metal', 16)
            manifest_path = folder / 'game-material.json'
            manifest = json.loads(manifest_path.read_text())
            manifest.pop('size')
            manifest['dimensions'] = [16, 24]
            for name, record in manifest['maps'].items():
                channels = int(record['channels'])
                value = bytes([128, 128, 255]) if name == 'normal' else bytes([127]) * channels
                payload = png_bytes(16, 24, channels, value * (16 * 24))
                path = folder / record['file']
                path.write_bytes(payload)
                record['sha256'] = hashlib.sha256(payload).hexdigest()
            manifest_path.write_text(json.dumps(manifest))
            bundle = load_material_bundle(folder)
            self.assertEqual(bundle['dimensions'], [16, 24])
            self.assertNotIn('size', bundle['manifest'])

            bad = json.loads(manifest_path.read_text())
            bad['size'] = 16
            manifest_path.write_text(json.dumps(bad))
            with self.assertRaisesRegex(ValueError, 'exactly one'):
                load_material_bundle(folder)

            for dimensions in ([16, True], [15, 24], [16, 513], [16], '16x24'):
                bad = json.loads(json.dumps(manifest))
                bad['dimensions'] = dimensions
                manifest_path.write_text(json.dumps(bad))
                with self.assertRaisesRegex(ValueError, 'dimensions'):
                    load_material_bundle(folder)

    def test_bundle_validation_does_not_need_blender_or_modify_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / 'paint'
            generate_game_material(folder, 'painted-metal', 16)
            before = {p.name: p.read_bytes() for p in folder.iterdir() if p.is_file()}
            bundle = load_material_bundle(folder)
            self.assertEqual(bundle['pngs']['normal'], before['normal.png'])
            self.assertEqual(before, {p.name: p.read_bytes() for p in folder.iterdir() if p.is_file()})

    def test_invalid_manifest_contracts_rejected(self):
        changes = [
            lambda m: m.update(schema='unknown'), lambda m: m.update(family='unknown'),
            lambda m: m.update(size=True), lambda m: m.update(size=4096),
            lambda m: m.update(normal_convention='guess'),
            lambda m: m.update(orm_channels=['metallic', 'roughness', 'occlusion']),
            lambda m: m['maps'].pop('normal'),
            lambda m: m['maps']['normal'].update(color_space='sRGB'),
            lambda m: m['maps']['normal'].update(channels=4),
            lambda m: m['maps']['normal'].update(file='../normal.png'),
            lambda m: m['maps']['normal'].update(file='/normal.png'),
            lambda m: m['maps']['normal'].update(file='C:\\normal.png'),
            lambda m: m['maps']['normal'].update(sha256='0' * 64),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / 'paint'
            generate_game_material(folder, 'painted-metal', 16)
            path = folder / 'game-material.json'
            original = path.read_text()
            for change in changes:
                manifest = json.loads(original)
                change(manifest)
                path.write_text(json.dumps(manifest))
                with self.assertRaises(ValueError):
                    load_material_bundle(folder)

    def test_declared_digest_does_not_excuse_wrong_png_dimensions(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / 'wood'
            generate_game_material(folder, 'carved-wood', 16)
            path = folder / 'normal.png'
            data = bytearray(path.read_bytes())
            data[19] = 64
            path.write_bytes(data)
            manifest_path = folder / 'game-material.json'
            manifest = json.loads(manifest_path.read_text())
            manifest['maps']['normal']['sha256'] = hashlib.sha256(data).hexdigest()
            manifest_path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, 'PNG dimensions'):
                load_material_bundle(folder)

    def test_symlink_is_not_followed(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / 'wood'
            generate_game_material(folder, 'carved-wood', 16)
            path = folder / 'normal.png'
            target = folder / 'linked.png'
            path.rename(target)
            try:
                path.symlink_to(target)
            except OSError:
                self.skipTest('symlinks unavailable')
            with self.assertRaisesRegex(ValueError, 'linked'):
                load_material_bundle(folder)

    def test_rehashed_truncated_corrupt_and_oversized_pngs_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / 'wood'
            generate_game_material(folder, 'carved-wood', 16)
            path = folder / 'normal.png'
            original = path.read_bytes()
            bad_crc = bytearray(original)
            bad_crc[29] ^= 1
            huge = (original[:33] + _png_chunk(b'IDAT', zlib.compress(bytes(1000000)))
                    + _png_chunk(b'IEND', b''))
            for data in (original[:-12], bytes(bad_crc), huge, original + b'trailing'):
                path.write_bytes(data)
                manifest_path = folder / 'game-material.json'
                manifest = json.loads(manifest_path.read_text())
                manifest['maps']['normal']['sha256'] = hashlib.sha256(data).hexdigest()
                manifest_path.write_text(json.dumps(manifest))
                with self.assertRaises(ValueError):
                    load_material_bundle(folder)


if __name__ == '__main__':
    unittest.main()
