from __future__ import annotations

import io
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))

from axm_uc.rigged_characters import character_catalog, forge_rigged_character, inspect_rigged_character
from axm_uc.visual_assets_bridge import operate_visual_expansion
from axm_uc.visual_assets_cli import main


def fixture_document():
    return {
        "asset":{"version":"2.0"},
        "nodes":[{"name":f"Joint{i}"} for i in range(32)]+[{"mesh":0,"skin":0}],
        "skins":[{"joints":list(range(32))}],
        "meshes":[{"primitives":[{"indices":0,"attributes":{
            "POSITION":1,"NORMAL":2,"TEXCOORD_0":3,"JOINTS_0":4,"WEIGHTS_0":5}}]}],
        "accessors":[{"count":300}],"materials":[{"name":"Atlas"}],"images":[{},{}],"textures":[{},{}],
        "animations":[{"name":name,"channels":[{"sampler":0}],"samplers":[{"input":0,"output":1}]}
                      for name in ("Idle","Wave","Walk_InPlace","Oops_Recover")],
    }


def write_glb(path,document):
    data=json.dumps(document).encode()
    data+=b" "*(-len(data)%4)
    path.write_bytes(struct.pack("<4sII",b"glTF",2,len(data)+20)+struct.pack("<I4s",len(data),b"JSON")+data)


class RiggedCharacterTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root=Path(self.temporary.name)
        self.path=self.root/"character.glb"

    def test_catalog_reports_portability_boundaries(self):
        result=character_catalog()
        self.assertEqual(set(result["characters"]),{"axm-oops"})
        self.assertIn("fbx",result["outputs"])
        self.assertTrue(result["truth"]["targetEngineSetupRequired"])
        self.assertFalse(result["truth"]["aaaCertification"])
        self.assertFalse(result["truth"]["exhaustiveOriginalityClearance"])

    def test_inspector_reports_skinned_structure_not_playback(self):
        write_glb(self.path,fixture_document())
        result=inspect_rigged_character(self.path)
        self.assertEqual(result["status"],"RIGGED_STRUCTURE_PASS")
        self.assertEqual(len(result["joint_names"]),32)
        self.assertEqual(len(result["animations"]),4)
        self.assertIn("not playback",result["truth"])

    def test_unskinned_or_missing_attributes_are_not_accepted(self):
        for field in ("JOINTS_0","WEIGHTS_0","TEXCOORD_0"):
            document=fixture_document()
            del document["meshes"][0]["primitives"][0]["attributes"][field]
            write_glb(self.path,document)
            self.assertEqual(inspect_rigged_character(self.path)["status"],"RIGGED_STRUCTURE_REVIEW_REQUIRED")
        document=fixture_document()
        del document["nodes"][-1]["skin"]
        write_glb(self.path,document)
        self.assertFalse(inspect_rigged_character(self.path)["gates"]["all-meshes-skinned"])

    def test_missing_clip_or_empty_animation_fails(self):
        document=fixture_document()
        document["animations"].pop()
        write_glb(self.path,document)
        self.assertFalse(inspect_rigged_character(self.path)["gates"]["four-required-clips"])
        document=fixture_document()
        document["animations"][0]["channels"]=[]
        write_glb(self.path,document)
        self.assertFalse(inspect_rigged_character(self.path)["gates"]["nonempty-animation-channels"])

    def test_input_validation_precedes_runtime_or_output_mutation(self):
        output=self.root/"output"
        for request in (None,{"asset_id":"copied-franchise"},{"render_resolution":0},{"detail_pass":99},
                        {"detail_pass":True},{"texture_resolution":True},{"texture_resolution":8192},
                        {"texture_resolution":"2048"},
                        {"verify_roundtrip":"false"},
                        {"auto_provision_runtime":"false"},{"no_render":"false"}):
            with self.assertRaises(ValueError):
                forge_rigged_character(self.root,request,output)
        self.assertFalse(output.exists())

    def test_hero_request_passes_resolution_to_machine_builder(self):
        output=self.root/"hero"
        def build(command, **kwargs):
            for lod in ("lod0","lod1","lod2"):
                write_glb(output/f"{lod}.glb",fixture_document())
            (output/"character-manifest.json").write_text(json.dumps({"exports":{
                lod:{"path":f"{lod}.glb"} for lod in ("lod0","lod1","lod2")}}))
            return type("Completed",(),{"returncode":0})()
        with patch("axm_uc.rigged_characters.resolve_blender",return_value=(Path("blender"),{})), \
             patch("axm_uc.rigged_characters.inspect_visual_learning",return_value={"contexts":{}}), \
             patch("axm_uc.rigged_characters.subprocess.run",side_effect=build) as run:
            result=forge_rigged_character(ROOT,{"detail_pass":3,"texture_resolution":4096},output)
        command=run.call_args.args[0]
        self.assertEqual(command[command.index("--detail")+1],"3")
        self.assertEqual(command[command.index("--texture-resolution")+1],"4096")
        self.assertIn("axm_character_surfaces.py",result["supporting_builder_sha256"])
        self.assertEqual(result["visual_acceptance"],"REQUIRED")
        self.assertEqual(result["status"],"SURFACE_STRUCTURE_FAILED")

    def test_crafted_surface_features_are_read_from_actual_glb(self):
        document=fixture_document()
        document["meshes"][0]["primitives"][0]["attributes"]["TANGENT"]=6
        document["materials"]=[{"pbrMetallicRoughness":{"baseColorTexture":{"index":0},
                                "metallicRoughnessTexture":{"index":1}},
                                "normalTexture":{"index":2},"occlusionTexture":{"index":1}}]
        write_glb(self.path,document)
        self.assertTrue(all(inspect_rigged_character(self.path)["surface_features"].values()))
        del document["meshes"][0]["primitives"][0]["attributes"]["TANGENT"]
        write_glb(self.path,document)
        self.assertFalse(inspect_rigged_character(self.path)["surface_features"]["tangents"])

    def test_requested_roundtrip_check_is_automatic_and_failure_is_not_accepted(self):
        for success in (True,False):
            output=self.root/str(success)
            def run(command,**kwargs):
                if "verify_rigged_character.py" in command[command.index("--python")+1]:
                    (output/"roundtrip-verification.json").write_text(json.dumps({"status":"PASS" if success else "REVIEW_REQUIRED"}))
                    return type("Completed",(),{"returncode":0 if success else 1})()
                for lod in ("lod0","lod1","lod2"):
                    write_glb(output/f"{lod}.glb",fixture_document())
                (output/"character-manifest.json").write_text(json.dumps({"exports":{
                    lod:{"path":f"{lod}.glb"} for lod in ("lod0","lod1","lod2")}}))
                return type("Completed",(),{"returncode":0})()
            with patch("axm_uc.rigged_characters.resolve_blender",return_value=(Path("blender"),{})), \
                 patch("axm_uc.rigged_characters.inspect_visual_learning",return_value={"contexts":{}}), \
                 patch("axm_uc.rigged_characters.subprocess.run",side_effect=run) as subprocess:
                result=forge_rigged_character(ROOT,{"verify_roundtrip":True},output)
            self.assertEqual(subprocess.call_count,2)
            self.assertEqual(result["status"],"STRUCTURE_AND_PLAYBACK_CHECKED_VISUAL_REVIEW_REQUIRED" if success else "ROUNDTRIP_FAILED")
            self.assertEqual(result["visual_acceptance"],"REQUIRED")
            self.assertIsNotNone(result["roundtrip"]["report_sha256"])

    def test_existing_output_is_rejected_before_runtime_provisioning(self):
        with patch("axm_uc.rigged_characters.resolve_blender") as runtime:
            with self.assertRaises(FileExistsError):
                forge_rigged_character(ROOT,{},self.root)
            runtime.assert_not_called()

    def test_bridge_requires_explicit_path(self):
        with self.assertRaises(ValueError):
            operate_visual_expansion(self.root,{"operation":"character-forge","request":{}})
        write_glb(self.path,fixture_document())
        result=operate_visual_expansion(self.root,{"operation":"character-inspect","path":"character.glb"})
        self.assertEqual(result["status"],"RIGGED_STRUCTURE_PASS")

    def test_cli_catalog_and_inspection(self):
        with patch("sys.stdout",new_callable=io.StringIO) as stdout:
            self.assertEqual(main(["character-catalog"]),0)
            self.assertIn("axm-oops",json.loads(stdout.getvalue())["characters"])
        write_glb(self.path,fixture_document())
        with patch("sys.stdout",new_callable=io.StringIO) as stdout:
            self.assertEqual(main(["character-inspect",str(self.path)]),0)
            self.assertEqual(json.loads(stdout.getvalue())["status"],"RIGGED_STRUCTURE_PASS")


if __name__=="__main__":
    unittest.main()
