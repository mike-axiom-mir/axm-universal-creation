from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_uc.machine import UniversalCreationMachine
from axm_uc.self_workspace import (
    SelfWorkspaceError,
    clone_self_workspace,
    inspect_self_workspace,
    request_merge_check,
    test_self_workspace as run_self_workspace_build,
)


class SelfWorkspaceTests(unittest.TestCase):
    def _mini_body(self, root: Path) -> Path:
        (root / "src/axm_uc").mkdir(parents=True)
        (root / "tests").mkdir()
        (root / "tools").mkdir()
        (root / "creations/old-output").mkdir(parents=True)
        (root / ".axm-build").mkdir()
        (root / ".git").mkdir()
        (root / "machine.contract.json").write_text("{}\n", encoding="utf-8")
        (root / "src/axm_uc/body.py").write_text("VALUE = 'live'\n", encoding="utf-8")
        (root / "tests/test_seed.py").write_text("# seed\n", encoding="utf-8")
        (root / "tools/build.py").write_text("print('BUILD_OK')\n", encoding="utf-8")
        (root / "creations/old-output/result.txt").write_text("runtime\n", encoding="utf-8")
        (root / ".axm-build/debris.txt").write_text("debris\n", encoding="utf-8")
        (root / ".git/config").write_text("history\n", encoding="utf-8")
        return root

    def test_clone_is_complete_editable_source_body_without_runtime_surfaces(self):
        with tempfile.TemporaryDirectory() as td:
            parent = Path(td)
            live = self._mini_body(parent / "live")
            candidate = parent / "candidate"
            result = clone_self_workspace(live, candidate)
            self.assertTrue(result["exact_copy_verified"])
            self.assertTrue(result["editable"])
            self.assertFalse(result["live_body_modified"])
            self.assertEqual((candidate / "src/axm_uc/body.py").read_text(encoding="utf-8"), "VALUE = 'live'\n")
            self.assertFalse((candidate / ".git").exists())
            self.assertFalse((candidate / ".axm-build").exists())
            self.assertFalse((candidate / "creations").exists())

            (candidate / "src/axm_uc/body.py").write_text("VALUE = 'candidate'\n", encoding="utf-8")
            (candidate / "src/axm_uc/new_organ.py").write_text("NEW = True\n", encoding="utf-8")
            (candidate / "tests/test_seed.py").unlink()
            comparison = inspect_self_workspace(live, candidate)["comparison"]
            self.assertEqual(comparison["modified"], ["src/axm_uc/body.py"])
            self.assertEqual(comparison["added"], ["src/axm_uc/new_organ.py"])
            self.assertEqual(comparison["removed"], ["tests/test_seed.py"])

    def test_candidate_body_runs_its_own_build_and_returns_log(self):
        with tempfile.TemporaryDirectory() as td:
            parent = Path(td)
            live = self._mini_body(parent / "live")
            candidate = parent / "candidate"
            clone_self_workspace(live, candidate)
            result = run_self_workspace_build(live, candidate, timeout_seconds=30)
            self.assertTrue(result["passed"], result)
            self.assertIn("BUILD_OK", result["stdout"])
            self.assertEqual(result["command"], ["python", "tools/build.py"])
            self.assertFalse(result["os_security_sandbox"])

    def test_live_machine_routes_full_source_clone_without_adopting_it(self):
        with tempfile.TemporaryDirectory() as td:
            candidate = Path(td) / "full-body"
            result = UniversalCreationMachine(ROOT).create({
                "kind": "self-clone-body",
                "direction": "create a complete editable experimental body",
                "inputs": {"operation": "clone", "path": str(candidate)},
            })
            self.assertEqual(result["type"], "CREATION_RESULT", result)
            self.assertEqual(result["capability"], "AXM-CAP-SELF-WORKSPACE")
            self.assertTrue((candidate / "src/axm_uc/machine.py").is_file())
            self.assertTrue((candidate / "capabilities/live/AXM-CAP-SELF-WORKSPACE.json").is_file())
            self.assertFalse((candidate / ".git").exists())
            self.assertFalse(result["result"]["live_body_modified"])

            requested = UniversalCreationMachine(ROOT).create({
                "kind": "self-workspace",
                "direction": "exercise candidate-selected analysis and creation observations",
                "inputs": {
                    "operation": "request-merge-check",
                    "path": str(candidate),
                    "requested_by": "integration-candidate",
                    "readiness_statement": "I choose to exercise the current observation surfaces.",
                    "requested_checks": [
                        "source-diff",
                        "machine-inspect",
                        "executable-anatomy",
                        "plan-probes",
                        "creation-trials",
                    ],
                    "probe_requests": ["examples/requests/create_real_site.json"],
                    "timeout_seconds": 60,
                },
            })
            self.assertEqual(requested["type"], "CREATION_RESULT", requested)
            observations = requested["result"]["observations"]
            self.assertFalse(observations["source-diff"]["changed"])
            self.assertTrue(observations["machine-inspect"]["passed"])
            self.assertTrue(observations["executable-anatomy"]["passed"])
            self.assertTrue(observations["plan-probes"][0]["observation"]["passed"])
            self.assertTrue(observations["creation-trials"][0]["observation"]["passed"])
            self.assertFalse(requested["result"]["live_body_modified"])

    def test_candidate_voluntarily_requests_selected_merge_observations(self):
        with tempfile.TemporaryDirectory() as td:
            parent = Path(td)
            live = self._mini_body(parent / "live")
            candidate = parent / "candidate"
            clone_self_workspace(live, candidate)
            (candidate / "src/axm_uc/body.py").write_text("VALUE = 'ready experiment'\n", encoding="utf-8")
            result = request_merge_check(
                live,
                candidate,
                readiness_statement="The candidate organ is implemented and I choose to request observation now.",
                requested_checks=["source-diff", "build"],
                requested_by="candidate-body",
                timeout_seconds=30,
            )
            self.assertEqual(result["request_state"], "MERGE_CHECK_REQUESTED_NOT_APPROVED")
            self.assertFalse(result["merge_performed"])
            self.assertFalse(result["merge_approved"])
            self.assertFalse(result["readiness_decided_by_workspace_manager"])
            self.assertEqual(result["observations"]["source-diff"]["modified"], ["src/axm_uc/body.py"])
            self.assertTrue(result["observations"]["build"]["passed"])
            self.assertTrue(Path(result["request_artifact"]).is_file())

    def test_workspace_manager_does_not_invent_candidate_readiness(self):
        with tempfile.TemporaryDirectory() as td:
            parent = Path(td)
            live = self._mini_body(parent / "live")
            candidate = parent / "candidate"
            clone_self_workspace(live, candidate)
            with self.assertRaisesRegex(SelfWorkspaceError, "readiness_statement"):
                request_merge_check(live, candidate, readiness_statement="")
            with self.assertRaisesRegex(SelfWorkspaceError, "timeout_seconds"):
                run_self_workspace_build(live, candidate, timeout_seconds="whenever")

    def test_clone_cannot_replace_or_contain_the_live_body(self):
        with tempfile.TemporaryDirectory() as td:
            live = self._mini_body(Path(td) / "live")
            with self.assertRaises(SelfWorkspaceError):
                clone_self_workspace(live, live)
            with self.assertRaises(SelfWorkspaceError):
                clone_self_workspace(live, Path(td))


if __name__ == "__main__":
    unittest.main()
