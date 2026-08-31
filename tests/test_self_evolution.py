from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_uc.evolution import adopt_organ, inspect_evolution, rollback_adoption
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
        "continuity": {"fit": True, "basis": f"{prefix}: the change preserves an exact bounded rollback path."},
        "wisdom-before-speed": {"fit": True, "basis": f"{prefix}: testing and root fit happen before the live-body mutation."},
    }


class SelfEvolutionTests(unittest.TestCase):
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
            "files": {
                entrypoint: json.dumps(entry, indent=2, sort_keys=True) + "\n",
            },
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
                "basis": "A deterministic local organ candidate used to prove adoption and rollback behavior.",
            },
            "limitations": ["This fixture proves only the exact tested organ package and evolution transitions."],
            "authority": copy.deepcopy(ZERO_AUTHORITY),
            "root_fit": roots("candidate"),
        }

    def _machine_root(self, parent: Path) -> Path:
        root = parent / "machine"
        (root / "executable-organs").mkdir(parents=True)
        return root

    def _spawn_candidate(self, parent: Path, unit_id: str = "axm.test.evolution.organ") -> Path:
        candidate = parent / f"candidate-{unit_id.rsplit('.', 1)[-1]}"
        result = spawn_unit(candidate, self._proposal(unit_id))
        self.assertTrue(result["validation"]["passed"], result)
        return candidate

    def test_live_machine_exposes_explicit_evolution_route(self):
        machine = UniversalCreationMachine(ROOT)
        manifest = machine.capabilities.route("adopt-organ")
        self.assertIsNotNone(manifest)
        self.assertEqual(manifest["id"], "AXM-CAP-EVOLVE-MACHINE")
        self.assertEqual(machine.capabilities.route("rollback-adoption")["id"], "AXM-CAP-EVOLVE-MACHINE")

    def test_tested_organ_can_be_adopted_and_rolled_back_within_one_day(self):
        fixed = datetime(2026, 8, 31, 2, 45, tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as td:
            parent = Path(td)
            root = self._machine_root(parent)
            candidate = self._spawn_candidate(parent)

            adopted = adopt_organ(
                root,
                candidate,
                reason="The observed creation gap needs this exact reusable organ.",
                root_fit=roots("adoption"),
                now=fixed,
            )
            self.assertTrue(adopted["adopted"], adopted)
            self.assertTrue(adopted["live_machine_body_modified"])
            self.assertTrue(adopted["transition"]["installed"])
            self.assertTrue(adopted["transition"]["registered"])
            self.assertTrue(adopted["transition"]["promoted_for_composition"])
            self.assertFalse(adopted["transition"]["merged"])
            self.assertEqual(
                adopted["rollback_until"],
                (fixed + timedelta(days=1)).isoformat().replace("+00:00", "Z"),
            )

            package = ExecutableOrganLibrary(root).inspect("axm.test.evolution.organ@1.0.0")
            self.assertEqual(package["id"], "axm.test.evolution.organ")
            self.assertTrue(Path(adopted["adoption_receipt"]).is_file())

            observed = inspect_evolution(root, adopted["adoption_id"], now=fixed + timedelta(hours=23))
            self.assertEqual(observed["state"], "ACTIVE_ROLLBACK_WINDOW")
            self.assertTrue(observed["rollback_available_now"])
            self.assertTrue(observed["live_exact"])

            rolled = rollback_adoption(
                root,
                adopted["adoption_id"],
                reason="The post-adoption observation exposed a regression.",
                now=fixed + timedelta(hours=23),
            )
            self.assertTrue(rolled["rolled_back"], rolled)
            self.assertTrue(rolled["live_machine_body_modified"])
            self.assertFalse(rolled["transition"]["installed"])
            self.assertTrue(Path(rolled["rollback_receipt"]).is_file())
            with self.assertRaises(ExecutableOrganError):
                ExecutableOrganLibrary(root).inspect("axm.test.evolution.organ@1.0.0")

            after = inspect_evolution(root, adopted["adoption_id"], now=fixed + timedelta(hours=23))
            self.assertEqual(after["state"], "ROLLED_BACK")
            self.assertFalse(after["rollback_available_now"])

    def test_rollback_window_expires_without_reversing_the_live_adoption(self):
        fixed = datetime(2026, 8, 31, 3, 0, tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as td:
            parent = Path(td)
            root = self._machine_root(parent)
            candidate = self._spawn_candidate(parent, "axm.test.evolution.expiry")
            adopted = adopt_organ(
                root,
                candidate,
                reason="Exercise the one-day continuity boundary.",
                root_fit=roots("adoption"),
                now=fixed,
            )
            observed = inspect_evolution(root, adopted["adoption_id"], now=fixed + timedelta(hours=25))
            self.assertEqual(observed["state"], "ACTIVE_ROLLBACK_WINDOW_EXPIRED")
            self.assertFalse(observed["rollback_available_now"])

            rolled = rollback_adoption(
                root,
                adopted["adoption_id"],
                reason="This request is deliberately outside the bounded rollback window.",
                now=fixed + timedelta(hours=25),
            )
            self.assertFalse(rolled["rolled_back"])
            self.assertEqual(rolled["truth_status"], "HOLD_ROLLBACK_WINDOW_EXPIRED")
            self.assertIsNotNone(ExecutableOrganLibrary(root).inspect("axm.test.evolution.expiry@1.0.0"))

    def test_live_drift_holds_rollback_instead_of_erasing_later_change(self):
        fixed = datetime(2026, 8, 31, 3, 15, tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as td:
            parent = Path(td)
            root = self._machine_root(parent)
            candidate = self._spawn_candidate(parent, "axm.test.evolution.drift")
            adopted = adopt_organ(
                root,
                candidate,
                reason="Exercise exact rollback drift protection.",
                root_fit=roots("adoption"),
                now=fixed,
            )
            destination = Path(adopted["destination"])
            destination.write_text(destination.read_text(encoding="utf-8") + "\n", encoding="utf-8")

            rolled = rollback_adoption(
                root,
                adopted["adoption_id"],
                reason="A later observation asks for rollback after the organ bytes have changed.",
                now=fixed + timedelta(hours=1),
            )
            self.assertFalse(rolled["rolled_back"])
            self.assertEqual(rolled["truth_status"], "HOLD_ROLLBACK_REQUIRES_EXACT_ADOPTED_BODY")
            self.assertTrue(destination.is_file())

    def test_collision_and_candidate_mutation_hold_before_live_mutation(self):
        fixed = datetime(2026, 8, 31, 3, 30, tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as td:
            parent = Path(td)
            root = self._machine_root(parent)
            candidate = self._spawn_candidate(parent, "axm.test.evolution.collision")
            adopted = adopt_organ(
                root,
                candidate,
                reason="Install the first exact ref.",
                root_fit=roots("adoption"),
                now=fixed,
            )
            self.assertTrue(adopted["adopted"])

            duplicate = self._spawn_candidate(parent / "other", "axm.test.evolution.collision")
            held = adopt_organ(
                root,
                duplicate,
                reason="Attempt the same exact ref again.",
                root_fit=roots("adoption"),
                now=fixed + timedelta(minutes=1),
            )
            self.assertFalse(held["adopted"])
            self.assertEqual(held["truth_status"], "HOLD_EXECUTABLE_ORGAN_REF_COLLISION")
            self.assertFalse(held["live_machine_body_modified"])

            mutated = self._spawn_candidate(parent, "axm.test.evolution.mutated")
            organ_path = mutated / "organ.json"
            organ_path.write_text(organ_path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
            rejected = adopt_organ(
                root,
                mutated,
                reason="A mutated candidate must be re-established rather than silently trusted.",
                root_fit=roots("adoption"),
                now=fixed + timedelta(minutes=2),
            )
            self.assertFalse(rejected["adopted"])
            self.assertEqual(rejected["truth_status"], "HOLD_CANDIDATE_TESTS_FAILED")
            self.assertFalse((root / "executable-organs/axm.test.evolution.mutated-1.0.0.json").exists())


if __name__ == "__main__":
    unittest.main()
