from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_uc.asset_atoms import (
    ASSET_ATOM_SCHEMA,
    ASSET_INSTANCE_SCHEMA,
    ATOM_KINDS,
    AssetAtomError,
    AssetPackageLibrary,
    asset_atom_schema_summary,
    compile_asset_package,
    materialize_asset_package,
    validate_asset_package,
)
from axm_uc.machine import UniversalCreationMachine


REF = "axm.example.modular-tank@1.0.0"


class AssetAtomTests(unittest.TestCase):
    def setUp(self):
        self.library = AssetPackageLibrary(ROOT)
        self.package = self.library.resolve(REF)

    @staticmethod
    def atom(package, atom_id):
        return next(atom for atom in package["atoms"] if atom["id"] == atom_id)

    def test_schema_and_installed_package_cover_all_requested_layers(self):
        schema = asset_atom_schema_summary()
        self.assertEqual(schema["package_schema"], ASSET_ATOM_SCHEMA)
        self.assertEqual(schema["instance_schema"], ASSET_INSTANCE_SCHEMA)
        self.assertEqual(schema["atom_kind_count"], 16)
        self.assertEqual(set(schema["atom_kinds"]), ATOM_KINDS)

        summary = self.library.summary()
        self.assertEqual(summary["package_count"], 1)
        self.assertEqual(summary["atom_count"], 26)
        self.assertEqual(summary["refs"], [REF])
        self.assertFalse(summary["runtime_execution_proven"])
        self.assertEqual(set(summary["atom_kind_counts"]), ATOM_KINDS)
        self.assertTrue(all(summary["atom_kind_counts"][kind] >= 1 for kind in ATOM_KINDS))

        installed = self.library.inspect(REF)
        self.assertEqual(installed["validation"]["atom_count"], 26)
        self.assertEqual(set(installed["validation"]["atom_kinds"]), ATOM_KINDS)
        self.assertTrue(installed["validation"]["all_references_resolved"])
        self.assertTrue(installed["validation"]["acyclic"])
        self.assertEqual(len(installed["validation"]["dependency_order"]), 26)

    def test_compile_selects_exact_lod_state_animation_and_palette_deterministically(self):
        selections = {}
        for distance, expected in ((5, "hull-high-part"), (50, "hull-medium-part"), (150, "hull-low-part")):
            compiled = compile_asset_package(
                self.package,
                observation_distance=distance,
                state="damaged-state",
                animation="turret-idle",
                palette_overrides={"faction-palette": {"primary": "#ff0000"}},
            )
            instance = compiled["instance"]
            self.assertEqual(compiled["truth_status"], "DETERMINISTIC_ASSET_INSTANCE_COMPILED")
            self.assertEqual(instance["selected_lods"]["tank-lod"]["atom"], expected)
            self.assertEqual(instance["selected_state"]["id"], "damaged-state")
            self.assertEqual(instance["selected_animation"]["id"], "turret-idle")
            self.assertEqual(instance["resolved_palettes"]["faction-palette"]["primary"], "#FF0000")
            self.assertEqual(instance["resource_evidence"]["truth_status"], "DECLARED_RESOURCE_REFERENCES_NOT_FETCHED")
            self.assertTrue(all(not row["bytes_fetched_or_verified"] for row in instance["resource_evidence"]["resources"]))
            selections[distance] = compiled

        repeated = compile_asset_package(
            self.package,
            observation_distance=50,
            state="damaged-state",
            animation="turret-idle",
            palette_overrides={"faction-palette": {"primary": "#ff0000"}},
        )
        self.assertEqual(repeated["package_digest"], selections[50]["package_digest"])
        self.assertEqual(repeated["instance"]["instance_digest"], selections[50]["instance"]["instance_digest"])

        other_palette = compile_asset_package(
            self.package,
            observation_distance=50,
            palette_overrides={"faction-palette": {"primary": "#00FF00"}},
        )
        self.assertEqual(other_palette["package_digest"], selections[50]["package_digest"])
        self.assertNotEqual(other_palette["instance"]["instance_digest"], selections[50]["instance"]["instance_digest"])

    def test_materialization_publishes_only_exact_validated_descriptor_files(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "tank-instance"
            result = materialize_asset_package(
                target,
                self.package,
                observation_distance=30,
                state="damaged-state",
                animation="turret-idle",
            )
            self.assertEqual(result["truth_status"], "VALIDATED_ASSET_DESCRIPTOR_PROJECT")
            self.assertTrue(result["validation"]["passed"])
            self.assertEqual({path.name for path in target.iterdir()}, {"asset.package.json", "asset.instance.json"})
            written_package = json.loads((target / "asset.package.json").read_text(encoding="utf-8"))
            written_instance = json.loads((target / "asset.instance.json").read_text(encoding="utf-8"))
            self.assertEqual(written_package["schema"], ASSET_ATOM_SCHEMA)
            self.assertEqual(written_instance["schema"], ASSET_INSTANCE_SCHEMA)
            self.assertEqual(written_instance["selected_lods"]["tank-lod"]["atom"], "hull-medium-part")

    def test_schema_fails_closed_on_reference_kind_cycle_lod_and_field_errors(self):
        cases = []

        unknown = copy.deepcopy(self.package)
        lod = self.atom(unknown, "tank-lod")
        lod["payload"]["representations"][0]["atom"] = "missing-part"
        lod["uses"] = ["missing-part", "hull-medium-part", "hull-low-part"]
        cases.append(("unknown reference", unknown))

        missing_use = copy.deepcopy(self.package)
        self.atom(missing_use, "armor-material")["uses"].remove("armor-shader")
        cases.append(("missing exact uses edge", missing_use))

        wrong_kind = copy.deepcopy(self.package)
        mask = self.atom(wrong_kind, "faction-color-mask")
        mask["payload"]["source"] = "hull-shape-high"
        mask["uses"] = ["hull-shape-high"]
        cases.append(("wrong reference kind", wrong_kind))

        cycle = copy.deepcopy(self.package)
        turret = self.atom(cycle, "turret-part")
        turret["payload"]["children"] = ["hull-high-part"]
        turret["uses"].append("hull-high-part")
        cases.append(("dependency cycle", cycle))

        lod_gap = copy.deepcopy(self.package)
        self.atom(lod_gap, "tank-lod")["payload"]["representations"][1]["min_distance"] = 30
        cases.append(("lod gap", lod_gap))

        unsupported = copy.deepcopy(self.package)
        unsupported["magic"] = True
        cases.append(("unsupported package field", unsupported))

        for label, package in cases:
            with self.subTest(label=label):
                with self.assertRaises(AssetAtomError):
                    validate_asset_package(package)

    def test_compile_rejects_non_exact_selections_and_palette_overrides(self):
        invalid_calls = [
            {"state": "missing-state"},
            {"animation": "damaged-state"},
            {"observation_distance": -1},
            {"palette_overrides": {"missing-palette": {"primary": "#FFFFFF"}}},
            {"palette_overrides": {"faction-palette": {"missing-role": "#FFFFFF"}}},
            {"palette_overrides": {"faction-palette": {"primary": "red"}}},
        ]
        for kwargs in invalid_calls:
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(AssetAtomError):
                    compile_asset_package(self.package, **kwargs)

    def test_live_capability_routes_inspection_compile_and_materialization(self):
        machine = UniversalCreationMachine(ROOT)
        inspection = machine.create({
            "kind": "inspect-asset-atom-schema",
            "inputs": {"operation": "inspect-schema"},
        })
        self.assertEqual(inspection["type"], "CREATION_RESULT")
        self.assertEqual(inspection["capability"], "AXM-CAP-COMPOSE-ASSET-ATOMS")
        self.assertEqual(inspection["result"]["schema"]["atom_kind_count"], 16)

        compiled = machine.create({
            "kind": "compile-asset-package",
            "inputs": {"operation": "compile", "ref": REF, "observation_distance": 101},
        })
        self.assertEqual(compiled["type"], "CREATION_RESULT")
        self.assertEqual(compiled["result"]["instance"]["selected_lods"]["tank-lod"]["id"], "far")

        with tempfile.TemporaryDirectory() as td:
            materialized = machine.create({
                "kind": "materialize-asset-package",
                "inputs": {"operation": "materialize", "ref": REF, "path": str(Path(td) / "asset")},
            })
            self.assertEqual(materialized["type"], "CREATION_RESULT")
            self.assertTrue(materialized["result"]["validation"]["passed"])

        blocked = machine.create({
            "kind": "materialize-asset-package",
            "inputs": {"operation": "materialize", "ref": REF, "path": "src/should-not-write"},
        })
        self.assertEqual(blocked["type"], "CREATION_ERROR")
        self.assertFalse((ROOT / "src/should-not-write").exists())


if __name__ == "__main__":
    unittest.main()
