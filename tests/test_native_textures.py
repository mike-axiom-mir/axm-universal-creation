import base64
import copy
import math
import struct
import unittest
import zlib

from axm_uc.fabric_noise import png_bytes
from axm_uc.native_textures import Texture, decode_png, material_textures, normalize_texture_set, texture_set_from_bundle
from axm_uc.procedural_3d import Procedural3DError, build_glb, verify_glb
from axm_uc.software_glb_preview import render_glb_preview
from axm_uc.game_pose_runtime import _parse
from axm_uc.game_material_styles import game_material_fields, game_material_request


def maps(color=(190, 95, 25), normal=(128, 128, 255), orm=(255, 150, 0)):
    return {**{name: base64.b64encode(png_bytes(16, 16, 3, bytes(rgb)*256)).decode()
               for name, rgb in zip(("base_color", "normal", "orm"), (color, normal, orm))},
            "normal_convention": "tangent +Y", "wrap": "clamp"}


def panel(textured=False):
    group = {"id": "paint", "positions": [[-.5, -.5, 0], [.5, -.5, 0], [.5, .5, 0], [-.5, .5, 0]],
             "normals": [[0, 0, 1]]*4, "indices": [0, 1, 2, 0, 2, 3],
             "texcoords": [[0, 1], [1, 1], [1, 0], [0, 0]],
             "material": {"color": "#ffffff", "metallic": 1, "roughness": 1}}
    if textured:
        group["textures"] = maps()
    return {"schema": "axm.surface-3d/v0.1", "name": "UV test panel", "primitives": [group]}


class NativeTextureTests(unittest.TestCase):
    def test_surface_controls_preserve_defaults_and_change_real_channels(self):
        original = game_material_fields("painted-metal", 16, 3)
        self.assertEqual(original, game_material_fields("painted-metal", 16, 3, surface_parameters={}))
        calm = game_material_fields("painted-metal", 16, 3, surface_parameters={"normal_strength": 0})
        self.assertNotEqual(original["normal"], calm["normal"])
        self.assertEqual(original["base_color"], calm["base_color"])
        request = game_material_request("unused", "painted-metal", 16, 3, surface_parameters={"normal_strength": .6})
        import json
        manifest = json.loads(request["inputs"]["text_files"]["game-material.json"])
        self.assertEqual(manifest["surface_parameters"], {"normal_strength": .6})

    def test_surface_controls_are_bounded_and_domain_specific(self):
        for family, controls in (("rubber", {"wear": .1}), ("painted-metal", {"scratches": 100000}),
                                 ("painted-metal", {"normal_strength": float("nan")}), ("painted-metal", {"unknown": 1})):
            with self.assertRaises(ValueError):
                game_material_fields(family, 16, surface_parameters=controls)

    def test_png_roundtrip_and_crc_truncation_bounds(self):
        pixels = bytes(range(48))
        encoded = png_bytes(4, 4, 3, pixels)
        self.assertEqual(decode_png(encoded), (4, 4, pixels))
        for malformed in (encoded[:-1], encoded+b"junk", encoded[:40]+b"x"+encoded[41:]):
            with self.assertRaises(ValueError):
                decode_png(malformed)

    def test_all_png_filters_against_known_constant_pixels(self):
        def chunk(kind, body):
            return struct.pack(">I", len(body))+kind+body+struct.pack(">I", zlib.crc32(kind+body)&0xffffffff)
        # Two identical pixels on two identical rows. Known encoded residuals.
        rows = {
            0: [bytes([20]*6), bytes([20]*6)],
            1: [bytes([20]*3+[0]*3)]*2,
            2: [bytes([20]*6), bytes([0]*6)],
            3: [bytes([20]*3+[10]*3), bytes([10]*3+[0]*3)],
            4: [bytes([20]*3+[0]*3), bytes([0]*6)],
        }
        for filtering, data in rows.items():
            encoded = b"\x89PNG\r\n\x1a\n"+chunk(b"IHDR", struct.pack(">IIBBBBB", 2, 2, 8, 2, 0, 0, 0))
            encoded += chunk(b"IDAT", zlib.compress(b"".join(bytes([filtering])+r for r in data)))+chunk(b"IEND", b"")
            self.assertEqual(decode_png(encoded)[2], bytes([20]*12))

    def test_srgb_filtering_occurs_in_linear_light(self):
        tex = Texture((2, 2, bytes([0,0,0, 255,255,255]*2)), srgb=True)
        self.assertAlmostEqual(tex.sample(.5, .5, 0, 33071, 33071)[0], .5)
        # Linear mean .5 encodes close to sRGB 188, never gamma-space 128.
        self.assertEqual(tex.levels[-1][2], bytes([188]*3))

    def test_wrapping_and_mipmap_sampling(self):
        tex = Texture((2, 1, bytes([0,0,0, 255,255,255])))
        self.assertEqual(tex.sample(1.25, .5, 0, 10497, 10497), [0,0,0])
        self.assertEqual(tex.sample(1.25, .5, 0, 33071, 33071), [1,1,1])
        self.assertAlmostEqual(tex.sample(.25, .5, 99, 33071, 33071)[0], 128/255)

    def test_odd_texture_dimensions_retain_edge_pixels(self):
        tex = Texture((3, 1, bytes([0,0,0, 0,0,0, 255,255,255])))
        self.assertEqual(tex.levels[-1], (1, 1, bytes([85,85,85])))

    def test_native_export_embeds_images_uvs_and_shared_orm(self):
        spec = panel(True)
        original = copy.deepcopy(spec)
        built = build_glb(spec)
        self.assertEqual(spec, original)
        self.assertEqual(built["body"], build_glb(spec)["body"])
        doc = built["document"]
        material = doc["materials"][0]
        self.assertEqual(material["occlusionTexture"], material["pbrMetallicRoughness"]["metallicRoughnessTexture"])
        self.assertEqual(len(doc["images"]), 3)
        self.assertTrue(all("uri" not in r for r in doc["images"]))
        self.assertEqual(verify_glb(built["body"])["textured_primitives"], 1)

    def test_uv_and_normal_contracts_fail_closed(self):
        for edit in (lambda g: g.pop("texcoords"), lambda g: g.update(texcoords=[[0,0]]*4),
                     lambda g: g["textures"].update(normal_convention="tangent -Y"),
                     lambda g: g["textures"].update(base_color="https://example.com/image.png")):
            spec = panel(True)
            edit(spec["primitives"][0])
            with self.assertRaises(Procedural3DError):
                build_glb(spec)

    def test_normal_conversion_preserves_source(self):
        values = maps(normal=(128, 30, 255))
        bundle = {"normal_convention": "tangent -Y", "pngs": {k: base64.b64decode(values[k]) for k in ("base_color", "normal", "orm")}}
        original = copy.deepcopy(bundle)
        result = texture_set_from_bundle(bundle)
        self.assertEqual(decode_png(base64.b64decode(result["normal"]))[2][:3], bytes([128,225,255]))
        self.assertEqual(bundle, original)

    def test_each_material_channel_changes_real_render(self):
        options = {"width": 96, "height": 96, "supersample": 1, "yaw": 0, "elevation": 0}
        spec = panel(True)
        reference = render_glb_preview(build_glb(spec)["body"], **options)
        self.assertGreater(reference["receipt"]["texture_shaded_pixels"], 0)
        for changed in (maps(color=(30,120,190)), maps(normal=(210,128,223)), maps(orm=(255,30,255)), maps(orm=(0,150,0))):
            spec["primitives"][0]["textures"] = changed
            actual = render_glb_preview(build_glb(spec)["body"], **options)
            self.assertNotEqual(actual["body"], reference["body"])

    def test_corrupt_embedded_texture_cannot_pass_geometry_verification(self):
        built = build_glb(panel(True))
        body = bytearray(built["body"])
        offset = body.index(b"\x89PNG")
        body[offset+29] ^= 1
        with self.assertRaises(Procedural3DError):
            verify_glb(bytes(body))

    def test_texture_transforms_are_not_silently_ignored(self):
        built = build_glb(panel(True))
        material = built["document"]["materials"][0]
        material["normalTexture"]["extensions"] = {"KHR_texture_transform": {"scale": [2,2]}}
        with self.assertRaisesRegex(ValueError, "transforms"):
            material_textures(built["document"], _parse(built["body"])[1], material)


if __name__ == "__main__":
    unittest.main()
