from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_uc.machine import UniversalCreationMachine
from axm_uc.spawn import FIRST_CLASS_KINDS, SPAWN_PROPOSAL_SCHEMA


ZERO_AUTHORITY = {
    "execute": False,
    "install": False,
    "register": False,
    "promote": False,
    "merge": False,
    "canon": False,
    "permissions": False,
}


def root_fit() -> dict:
    return {
        "truth": {"fit": True, "basis": "The proposal separates supplied source, structural checks, and unproven behavior."},
        "agency": {"fit": True, "basis": "The detached candidate grants itself no authority and preserves an external admission choice."},
        "continuity": {"fit": True, "basis": "The candidate is created outside the live machine body and can be discarded without replacing it."},
        "wisdom-before-speed": {"fit": True, "basis": "Exact lineage and bounded tests are retained before any later admission choice."},
    }


class CreationForgeTests(unittest.TestCase):
    def setUp(self):
        self.machine = UniversalCreationMachine(ROOT)

    def _capability_entry(self, unit_id: str, version: str, handle: str) -> dict:
        return {
            "id": unit_id,
            "version": version,
            "status": "candidate",
            "purpose": "Write exact Markdown through the existing text capability.",
            "handles": [handle],
            "input_contract": {"required": ["path", "content"], "properties": {}},
            "output_contract": {"kind": "file"},
            "dependencies": ["AXM-CAP-WRITE-TEXT"],
            "relationships": [{"type": "delegates-to", "target": "AXM-CAP-WRITE-TEXT"}],
            "implementation": {
                "kind": "DETERMINISTIC_ALIAS",
                "delegate": "AXM-CAP-WRITE-TEXT",
                "source": "this manifest",
            },
            "limitations": ["This proves only the declared exact-text fixture."],
            "persistent_state": None,
            "tests": [{
                "inputs": {"path": "${TEST_DIR}/proof.md", "content": "# Spawned\n"},
                "expect": {"file_text": "# Spawned\n"},
            }],
            "root_fit": root_fit(),
        }

    def _proposal(self, kind: str, unit_id: str | None = None) -> dict:
        unit_id = unit_id or f"axm.test.{kind}"
        version = "1.0.0"
        if kind in {"hand", "capability"}:
            entrypoint = f"{kind}.json"
            entry = self._capability_entry(unit_id, version, f"test-{kind}-{unit_id.rsplit('.', 1)[-1]}")
            implementation_kind = "DETERMINISTIC_ALIAS"
            files = {entrypoint: json.dumps(entry, indent=2, sort_keys=True) + "\n"}
        elif kind == "organ":
            entrypoint = "organ.json"
            entry = json.loads((ROOT / "executable-organs/axm.web.theme-1.0.0.json").read_text(encoding="utf-8"))
            entry.update({"id": unit_id, "version": version})
            implementation_kind = "DETERMINISTIC_SOURCE"
            files = {entrypoint: json.dumps(entry, indent=2, sort_keys=True) + "\n"}
        elif kind == "skill":
            entrypoint = "SKILL.md"
            implementation_kind = "INSTRUCTION_ONLY"
            files = {entrypoint: "# Bounded review\n\nInspect evidence, state limits, and return a candidate finding.\n"}
        else:
            entrypoint = f"{kind}.json"
            entry = {"schema": f"axm.test.{kind}/v1", "id": unit_id, "version": version, "status": "candidate"}
            files = {entrypoint: json.dumps(entry, indent=2, sort_keys=True) + "\n"}
            implementation_kind = {
                "protocol": "DETERMINISTIC_CONTRACT",
                "specialist": "METHOD_OVERLAY",
                "recipe": "DETERMINISTIC_RECIPE",
            }.get(kind, "HUMAN_SUPPLIED")

        return {
            "schema": SPAWN_PROPOSAL_SCHEMA,
            "id": unit_id,
            "version": version,
            "kind": kind,
            "purpose": f"Exercise deterministic detached {kind} candidate materialization.",
            "files": files,
            "implementation": {
                "kind": implementation_kind,
                "entrypoint": entrypoint,
                "source_files": [entrypoint],
            },
            "contracts": {
                "inputs": {"kind": "test-input"},
                "outputs": {"kind": "test-output"},
                "provides": [f"test-{kind}-output"],
                "requires": [],
            },
            "dependencies": [],
            "relationships": [],
            "verification": {"checks": [{"type": "nonempty", "path": entrypoint}]},
            "provenance": {
                "kind": "test-fixture",
                "refs": ["tests/test_creation_forge.py"],
                "basis": "A bounded local fixture for the detached forge.",
            },
            "limitations": ["The fixture does not prove behavior beyond its emitted checks."],
            "authority": copy.deepcopy(ZERO_AUTHORITY),
            "root_fit": root_fit(),
        }

    def _spawn(self, target: Path, proposal: dict) -> dict:
        return self.machine.create({
            "kind": "spawn-creation-unit",
            "direction": "materialize new reusable creation machinery",
            "inputs": {"operation": "spawn", "path": str(target), "proposal": proposal},
        })

    def _operate(self, target: Path, operation: str, **extra) -> dict:
        return self.machine.create({
            "kind": "test-spawned-unit" if operation == "test" else "inspect-spawned-unit",
            "inputs": {"operation": operation, "path": str(target), **extra},
        })

    def test_all_first_class_kinds_materialize_and_receive_honest_tests(self):
        with tempfile.TemporaryDirectory() as td:
            parent = Path(td)
            strengths = {}
            for kind in sorted(FIRST_CLASS_KINDS):
                target = parent / kind
                spawned = self._spawn(target, self._proposal(kind))
                self.assertEqual(spawned["type"], "CREATION_RESULT", spawned)
                self.assertEqual(spawned["result"]["unit"]["kind"], kind)
                self.assertEqual(spawned["result"]["unit"]["kind_contract"], "FIRST_CLASS")
                self.assertFalse(spawned["result"]["spawn_receipt"]["generated_code_executed"])
                self.assertTrue((target / "axm.proposal.json").is_file())
                self.assertTrue((target / "axm.unit.json").is_file())
                self.assertTrue((target / "axm.spawn-receipt.json").is_file())

                tested = self._operate(target, "test")
                self.assertEqual(tested["type"], "CREATION_RESULT", tested)
                self.assertTrue(tested["result"]["passed"], tested)
                strengths[kind] = tested["result"]["kind_test"]["evidence_strength"]
                self.assertFalse(tested["result"]["installed"])
                self.assertFalse(tested["result"]["registered"])

            self.assertEqual(strengths["capability"], "DECLARED_CANDIDATE_TESTS_EXECUTED")
            self.assertEqual(strengths["hand"], "DECLARED_CANDIDATE_TESTS_EXECUTED")
            self.assertEqual(strengths["organ"], "EXECUTABLE_ORGAN_PACKAGE_SCHEMA_VALIDATION")
            self.assertEqual(strengths["protocol"], "STRUCTURAL_ENTRYPOINT_AND_DECLARED_FILE_CHECKS")
            self.assertEqual(strengths["specialist"], "STRUCTURAL_ENTRYPOINT_AND_DECLARED_FILE_CHECKS")

    def test_extension_kind_is_open_but_reports_generic_evidence_only(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "new-kind"
            spawned = self._spawn(target, self._proposal("world-rule"))
            self.assertEqual(spawned["type"], "CREATION_RESULT", spawned)
            self.assertEqual(spawned["result"]["unit"]["kind_contract"], "OPEN_EXTENSION_GENERIC")
            tested = self._operate(target, "test")
            self.assertTrue(tested["result"]["passed"], tested)
            self.assertEqual(tested["result"]["kind_test"]["evidence_strength"], "DECLARED_FILE_CHECKS_ONLY")

    def test_same_proposal_rebuilds_to_same_path_independent_package_digest(self):
        with tempfile.TemporaryDirectory() as td:
            parent = Path(td)
            proposal = self._proposal("protocol")
            first = self._spawn(parent / "first", proposal)["result"]["spawn_receipt"]
            second = self._spawn(parent / "second", proposal)["result"]["spawn_receipt"]
            self.assertEqual(first["proposal_digest"], second["proposal_digest"])
            self.assertEqual(first["manifest_digest"], second["manifest_digest"])
            self.assertEqual(first["package_digest"], second["package_digest"])
            self.assertEqual(first["body_files"], second["body_files"])

    def test_mutation_is_detected_and_blocks_admission_readiness(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "mutated"
            self._spawn(target, self._proposal("protocol"))
            (target / "protocol.json").write_text('{"tampered":true}\n', encoding="utf-8")
            inspected = self._operate(target, "inspect")
            self.assertFalse(inspected["result"]["passed"])
            self.assertFalse(inspected["result"]["checks"]["payload_digests"])

            requested = self.machine.create({
                "kind": "request-unit-admission-check",
                "inputs": {
                    "operation": "request-admission-check",
                    "path": str(target),
                    "requested_by": "mutated-candidate",
                    "readiness_statement": "I choose to request review, even though the exact test should hold me.",
                },
            })
            self.assertEqual(requested["result"]["request_state"], "HELD_FAILED_TESTS")
            self.assertFalse(requested["result"]["admission_performed"])

    def test_self_granted_authority_and_hidden_fields_are_rejected_before_output(self):
        with tempfile.TemporaryDirectory() as td:
            parent = Path(td)
            authority = self._proposal("skill")
            authority["authority"]["execute"] = True
            result = self._spawn(parent / "authority", authority)
            self.assertEqual(result["type"], "CREATION_ERROR")
            self.assertIn("cannot grant itself authority", result["message"])
            self.assertFalse((parent / "authority").exists())

            hidden = self._proposal("skill")
            hidden["hidden_magic"] = True
            result = self._spawn(parent / "hidden", hidden)
            self.assertEqual(result["type"], "CREATION_ERROR")
            self.assertEqual(result["details"]["unexpected_fields"], ["hidden_magic"])
            self.assertFalse((parent / "hidden").exists())

    def test_capability_test_refuses_output_paths_outside_disposable_test_space(self):
        with tempfile.TemporaryDirectory() as td:
            parent = Path(td)
            proposal = self._proposal("capability", "axm.test.unconfined-capability")
            entry = json.loads(proposal["files"]["capability.json"])
            entry["tests"][0]["inputs"]["path"] = str(parent / "must-not-be-written.md")
            proposal["files"]["capability.json"] = json.dumps(entry, indent=2, sort_keys=True) + "\n"
            target = parent / "candidate"
            self._spawn(target, proposal)
            tested = self._operate(target, "test")
            self.assertFalse(tested["result"]["passed"])
            candidate_test = tested["result"]["kind_test"]["capability_test"]
            self.assertIn("candidate test input paths must stay under ${TEST_DIR}/", candidate_test["errors"])
            self.assertFalse((parent / "must-not-be-written.md").exists())

    def test_capability_test_refuses_json_result_comparison_outside_test_space(self):
        with tempfile.TemporaryDirectory() as td:
            parent = Path(td)
            proposal = self._proposal("capability", "axm.test.unconfined-json-comparison")
            entry = json.loads(proposal["files"]["capability.json"])
            entry["tests"][0]["expect"]["json_file_equals_result"] = {
                "path": str(parent / "outside.json"),
                "result_field": "kind",
            }
            proposal["files"]["capability.json"] = json.dumps(entry, indent=2, sort_keys=True) + "\n"
            target = parent / "candidate"
            self._spawn(target, proposal)
            tested = self._operate(target, "test")
            self.assertFalse(tested["result"]["passed"])
            errors = tested["result"]["kind_test"]["capability_test"]["errors"]
            self.assertIn(
                "json_file_equals_result requires a ${TEST_DIR}/ path and one non-empty result_field",
                errors,
            )
            self.assertFalse((parent / "outside.json").exists())

    def test_passing_capability_may_request_review_without_becoming_live(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "capability"
            proposal = self._proposal("capability", "axm.test.reviewable-capability")
            handle = json.loads(proposal["files"]["capability.json"])["handles"][0]
            self._spawn(target, proposal)
            self.assertIsNone(self.machine.capabilities.route(handle))

            requested = self.machine.create({
                "kind": "request-unit-admission-check",
                "inputs": {
                    "operation": "request-admission-check",
                    "path": str(target),
                    "requested_by": "reviewable-capability",
                    "readiness_statement": "My exact detached fixture passes and I choose to request an admission decision.",
                },
            })
            self.assertEqual(requested["type"], "CREATION_RESULT", requested)
            self.assertEqual(requested["result"]["request_state"], "READY_FOR_HUMAN_ADMISSION_REVIEW")
            self.assertFalse(requested["result"]["request"]["approval_granted"])
            self.assertFalse(requested["result"]["request"]["installed"])
            self.assertIsNone(self.machine.capabilities.route(handle))

            inspected = self._operate(target, "inspect")
            self.assertTrue(inspected["result"]["passed"], inspected)
            self.assertEqual(inspected["result"]["admission_request"]["state"], "READY_FOR_HUMAN_ADMISSION_REVIEW")

    def test_machine_inspection_exposes_potential_instead_of_inflated_live_count(self):
        inspection = self.machine.inspect()
        forge = inspection["creation_forge"]
        self.assertEqual(set(forge["first_class_kinds"]), set(FIRST_CLASS_KINDS))
        self.assertTrue(forge["extension_kinds_allowed"])
        self.assertFalse(forge["automatic_execution"])
        self.assertFalse(forge["automatic_install_or_registration"])
        self.assertEqual(len(inspection["live_capabilities"]), 19)


if __name__ == "__main__":
    unittest.main()