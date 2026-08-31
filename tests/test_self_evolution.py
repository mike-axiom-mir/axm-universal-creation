from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_uc.evolution import adopt_organ, inspect_evolution, restore_machine_snapshot, snapshot_machine
from axm_uc.machine import UniversalCreationMachine
from axm_uc.organ_library import ExecutableOrganError, ExecutableOrganLibrary
from axm_uc.spawn import SPAWN_PROPOSAL_SCHEMA, spawn_unit


ZERO_AUTHORITY = {
    "execute": False,
    "install": False,
    "register": False,
    "promote": False,
    "merge": False,
    "canon": False,
    "permissions": False,
}


def roots(prefix: str) -> dict:
    return {
        "truth": {"fit": True, "basis": f"{prefix}: exact source, evidence, and state transitions remain inspectable."},
        "agency": {"fit": True, "basis": f"{prefix}: the continuing machine chooses the transition without a permanent outside gate."},
        "continuity": {"fit": True, "basis": f"{prefix}: the daily whole-machine snapshot provides the recovery floor."},
        "wisdom-before-speed": {"fit": True, "basis": f"{prefix}: testing, root fit, and recovery readiness happen before live mutation."},
    }


class SelfEvolutionTests(unittest.TestCase):
    DAY = date(2026, 8, 31)

    def _proposal(self, unit_id: str = "axm.test.evolution.organ") -> dict:
        version = "1.0.0"
        entry = json.loads((ROOT / "executable-organs/axm.web.theme-1.0.0.json").read_text(encoding="utf-8"))
        entry.update({"id": unit_id, "version": version})
        entrypoint = "organ.json"
        return {
            "schema": SPAWN_PROPOSAL_SCHEMA,
            "id": unit_id,
            "version": version,
            "kind": "organ",
            "purpose": "Provide one exact executable-organ fixture for self-evolution adoption tests.",
            "files": {entrypoint: json.dumps(entry, indent=2, sort_keys=True) + "\n"},
            "implementation": {
                "kind": "DETERMINISTIC_SOURCE",
                "entrypoint": entrypoint,
                "source_files": [entrypoint],
            },
            "contracts": {
                "inputs": {"kind": "test-input"},
                "outputs": {"kind": "test-output"},
                "provides": ["test-evolution-organ"],
                "requires": [],
            },
            "dependencies": [],
            "relationships": [],
            "verification": {"checks": [{"type": "nonempty", "path": entrypoint}]},
            "provenance": {
                "kind": "test-fixture",
                "refs": ["tests/test_self_evolution.py"],
                "basis": "A deterministic local organ candidate used to prove adoption and daily recovery behavior.",
            },
            "limitations": ["This fixture proves only the exact tested organ package and evolution transitions."],
            "authority": copy.deepcopy(ZERO_AUTHORITY),
            "root_fit": roots("candidate"),
        }

    def _machine_root(self, parent: Path) -> Path:
        root = parent / "machine"
        (root / "executable-organs").mkdir(parents=True)
        (root / "state").mkdir()
        (root / "state" / "baseline.txt").write_text("known-good\n", encoding="utf-8")
        return root

    def _spawn_candidate(self, parent: Path, unit_id: str = "axm.test.evolution.organ") -> Path:
        parent.mkdir(parents=True, exist_ok=True)
        candidate = parent / f"candidate-{unit_id.rsplit('.', 1)[-1]}"
        result = spawn_unit(candidate, self._proposal(unit_id))
        self.assertTrue(result["validation"]["passed"], result)
        return candidate

    def test_live_machine_exposes_explicit_evolution_routes(self):
        machine = UniversalCreationMachine(ROOT)
        for handle in ("adopt-organ", "inspect-evolution", "snapshot-machine", "restore-machine-snapshot"):
            manifest = machine.capabilities.route(handle)
            self.assertIsNotNone(manifest, handle)
            self.assertEqual(manifest["id"], "AXM-CAP-EVOLVE-MACHINE")

    def test_adoption_creates_daily_recovery_then_installs_registers_and_promotes(self):
        with tempfile.TemporaryDirectory() as td:
            parent = Path(td)
            root = self._machine_root(parent)
            candidate = self._spawn_candidate(parent / "candidates")

            adopted = adopt_organ(
                root,
                candidate,
                reason="A real creation gap needs this exact reusable organ.",
                root_fit=roots("adoption"),
                today=self.DAY,
            )
            self.assertTrue(adopted["adopted"], adopted)
            self.assertTrue(adopted["live_machine_body_modified"])
            self.assertTrue(adopted["transition"]["installed"])
            self.assertTrue(adopted["transition"]["registered"])
            self.assertTrue(adopted["transition"]["promoted_for_composition"])
            self.assertFalse(adopted["transition"]["merged"])
            self.assertFalse(adopted["transition"]["canon_changed"])
            self.assertFalse(adopted["transition"]["permissions_changed"])

            recovery = adopted["recovery_snapshot"]
            self.assertTrue(recovery["created_now"])
            self.assertTrue(Path(recovery["path"]).is_file())
            package = ExecutableOrganLibrary(root).inspect("axm.test.evolution.organ@1.0.0")
            self.assertEqual(package["id"], "axm.test.evolution.organ")

            observed = inspect_evolution(root, today=self.DAY)
            self.assertTrue(observed["daily_recovery"]["exists"])
            self.assertEqual(observed["executable_organs"]["packages"], 1)

    def test_same_day_adoptions_reuse_one_snapshot_and_whole_body_restore_removes_both(self):
        with tempfile.TemporaryDirectory() as td:
            parent = Path(td)
            root = self._machine_root(parent)
            first = self._spawn_candidate(parent / "candidates-1", "axm.test.evolution.first")
            second = self._spawn_candidate(parent / "candidates-2", "axm.test.evolution.second")

            adopted_first = adopt_organ(
                root,
                first,
                reason="First same-day organ.",
                root_fit=roots("adoption"),
                today=self.DAY,
            )
            adopted_second = adopt_organ(
                root,
                second,
                reason="Second same-day organ.",
                root_fit=roots("adoption"),
                today=self.DAY,
            )
            self.assertTrue(adopted_first["recovery_snapshot"]["created_now"])
            self.assertFalse(adopted_second["recovery_snapshot"]["created_now"])
            self.assertTrue(adopted_second["recovery_snapshot"]["already_existed"])
            self.assertEqual(
                adopted_first["recovery_snapshot"]["path"],
                adopted_second["recovery_snapshot"]["path"],
            )
            self.assertEqual(ExecutableOrganLibrary(root).summary()["packages"], 2)

            restored = restore_machine_snapshot(
                root,
                Path(adopted_first["recovery_snapshot"]["path"]),
                confirm=True,
                reason="The later same-day machine state proved unwanted.",
            )
            self.assertTrue(restored["restored"])
            self.assertTrue(restored["live_machine_body_modified"])
            self.assertEqual(ExecutableOrganLibrary(root).summary()["packages"], 0)
            self.assertEqual((root / "state/baseline.txt").read_text(encoding="utf-8"), "known-good\n")

            quarantine = Path(restored["quarantine"])
            self.assertTrue((quarantine / "executable-organs/axm.test.evolution.first-1.0.0.json").is_file())
            self.assertTrue((quarantine / "executable-organs/axm.test.evolution.second-1.0.0.json").is_file())

    def test_collision_and_candidate_mutation_hold_before_live_mutation(self):
        with tempfile.TemporaryDirectory() as td:
            parent = Path(td)
            root = self._machine_root(parent)
            candidate = self._spawn_candidate(parent / "candidates-1", "axm.test.evolution.collision")
            adopted = adopt_organ(
                root,
                candidate,
                reason="Install the first exact ref.",
                root_fit=roots("adoption"),
                today=self.DAY,
            )
            self.assertTrue(adopted["adopted"])

            duplicate = self._spawn_candidate(parent / "candidates-2", "axm.test.evolution.collision")
            held = adopt_organ(
                root,
                duplicate,
                reason="Attempt the same exact ref again.",
                root_fit=roots("adoption"),
                today=self.DAY,
            )
            self.assertFalse(held["adopted"])
            self.assertEqual(held["truth_status"], "HOLD_EXECUTABLE_ORGAN_REF_COLLISION")
            self.assertFalse(held["live_machine_body_modified"])

            mutated = self._spawn_candidate(parent / "candidates-3", "axm.test.evolution.mutated")
            organ_path = mutated / "organ.json"
            organ_path.write_text(organ_path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
            rejected = adopt_organ(
                root,
                mutated,
                reason="A mutated candidate must be re-established rather than silently trusted.",
                root_fit=roots("adoption"),
                today=self.DAY,
            )
            self.assertFalse(rejected["adopted"])
            self.assertEqual(rejected["truth_status"], "HOLD_CANDIDATE_TESTS_FAILED")
            self.assertFalse((root / "executable-organs/axm.test.evolution.mutated-1.0.0.json").exists())

    def test_snapshot_operation_is_one_per_day_without_replace(self):
        with tempfile.TemporaryDirectory() as td:
            parent = Path(td)
            root = self._machine_root(parent)
            out = parent / "manual-snapshots"
            first = snapshot_machine(root, output_dir=out, today=self.DAY)
            second = snapshot_machine(root, output_dir=out, today=self.DAY)
            self.assertTrue(first["created"])
            self.assertFalse(second["created"])
            self.assertEqual(first["path"], second["path"])
            self.assertTrue(Path(first["path"]).is_file())


if __name__ == "__main__":
    unittest.main()
