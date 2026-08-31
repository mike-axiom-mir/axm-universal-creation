from __future__ import annotations

import json
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_uc.local_provider import LocalProviderError, normalize_loopback_endpoint, operate_local_provider
from axm_uc.machine import UniversalCreationMachine
from axm_uc.stepwise_workflow import prepare_checkpoint, start_workflow


class LocalProviderTests(unittest.TestCase):
    def _server(self, proposal: dict) -> tuple[ThreadingHTTPServer, list[dict]]:
        received: list[dict] = []

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:  # noqa: N802 - stdlib handler contract
                length = int(self.headers.get("Content-Length", "0"))
                received.append(json.loads(self.rfile.read(length).decode("utf-8")))
                body = json.dumps(
                    {"choices": [{"message": {"role": "assistant", "content": json.dumps(proposal)}}]}
                ).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, _format: str, *_args: object) -> None:
                return

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        return server, received

    def test_inspect_and_prepare_do_not_call_a_provider(self):
        inspected = operate_local_provider(ROOT, {"operation": "inspect"})
        self.assertFalse(inspected["automatic_call_without_explicit_allow"])
        prepared = operate_local_provider(
            ROOT,
            {
                "operation": "prepare",
                "goal": "create a tiny local game",
                "project_type": "static-web",
            },
        )
        self.assertEqual(prepared["truth_status"], "LOCAL_PROVIDER_REQUEST_PREPARED_NO_CALL_MADE")
        self.assertFalse(prepared["provider"]["allow_call"])

    def test_provider_endpoint_rejects_non_loopback_hosts(self):
        with self.assertRaisesRegex(LocalProviderError, "explicit loopback host"):
            normalize_loopback_endpoint("https://api.example.com/v1")

    def test_loopback_provider_redirect_cannot_escape_to_a_cloud_endpoint(self):
        class RedirectHandler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:  # noqa: N802 - stdlib handler contract
                self.send_response(302)
                self.send_header("Location", "https://api.example.com/v1/chat/completions")
                self.end_headers()

            def log_message(self, _format: str, *_args: object) -> None:
                return

        server = ThreadingHTTPServer(("127.0.0.1", 0), RedirectHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        with tempfile.TemporaryDirectory() as td:
            result = UniversalCreationMachine(ROOT).create(
                {
                    "kind": "software-project",
                    "direction": "prove redirects stay local",
                    "inputs": {"path": str(Path(td) / "redirect")},
                    "provider": {
                        "endpoint": f"http://127.0.0.1:{server.server_port}/v1",
                        "allow_call": True,
                    },
                }
            )
            self.assertEqual(result["type"], "CREATION_ERROR")
            self.assertEqual(result["details"]["status"], 302)

    def test_operation_specific_requirements_prevent_false_ready_coverage(self):
        machine = UniversalCreationMachine(ROOT)
        request = {"kind": "provider-backed-project", "inputs": {"operation": "create"}}
        plan = machine.plan(request)
        exact = next(hit for hit in plan["live_capability_coverage"] if hit["exact_handle_match"])
        self.assertEqual(exact["missing_required_inputs"], ["goal", "path", "provider"])
        self.assertEqual(plan["gap"]["status"], "input-gap")
        created = machine.create(request)
        self.assertEqual(created["type"], "CAPABILITY_INPUT_GAP")
        self.assertEqual(created["missing_required_inputs"], ["goal", "path", "provider"])

    def test_explicit_provider_fills_missing_files_then_revalidates_project(self):
        proposal = {
            "schema": "axm.local-creation-provider-response/v0.1",
            "project_type": "static-web",
            "files": {
                "index.html": "<!doctype html><html><head><link rel=\"stylesheet\" href=\"style.css\"></head><body><button id=\"start\">Start</button><script src=\"game.js\"></script></body></html>\n",
                "style.css": "body { background: #05080d; color: #6ff; }\n",
                "game.js": "document.querySelector('#start').addEventListener('click', () => { document.body.dataset.started = 'true'; });\n",
            },
            "summary": "A bounded local static-web game shell.",
            "limitations": ["Runtime, interaction, and appearance still require host evidence."],
        }
        server, received = self._server(proposal)
        endpoint = f"http://127.0.0.1:{server.server_port}/v1"
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "game"
            result = UniversalCreationMachine(ROOT).create(
                {
                    "kind": "static-web-project",
                    "direction": "create a tiny local RTS shell",
                    "inputs": {"path": str(target)},
                    "provider": {"endpoint": endpoint, "model": "waldo", "allow_call": True},
                }
            )
            self.assertEqual(result["type"], "CREATION_RESULT", result)
            self.assertEqual(result["capability"], "AXM-CAP-LOCAL-CREATION-PROVIDER")
            self.assertEqual(result["filled_missing_inputs"], ["files"])
            self.assertTrue(result["result"]["passed"], result)
            self.assertTrue(result["result"]["verification"]["passed"])
            self.assertEqual(result["result"]["host_evidence_status"], "NOT_OBSERVED")
            self.assertTrue((target / "index.html").is_file())
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0]["model"], "waldo")

    def test_trial_independently_reverifies_provider_generated_files(self):
        proposal = {
            "schema": "axm.local-creation-provider-response/v0.1",
            "project_type": "static-web",
            "files": {"index.html": "<!doctype html><title>Local trial</title>\n"},
            "summary": "A minimal local provider trial fixture.",
            "limitations": ["No browser observation is claimed."],
        }
        server, _received = self._server(proposal)
        with tempfile.TemporaryDirectory() as td:
            result = UniversalCreationMachine(ROOT).trial(
                {
                    "kind": "static-web-project",
                    "direction": "create and independently reverify a local page",
                    "inputs": {"path": str(Path(td) / "site")},
                    "provider": {
                        "endpoint": f"http://127.0.0.1:{server.server_port}/v1",
                        "allow_call": True,
                    },
                }
            )
            self.assertTrue(result["passed"], result)
            self.assertEqual(result["verification"]["type"], "CREATION_RESULT")
            self.assertTrue(result["verification"]["result"]["passed"])

    def test_explicit_consent_is_required_and_unsafe_provider_paths_do_not_materialize(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "no-call"
            result = UniversalCreationMachine(ROOT).create(
                {
                    "kind": "static-web-project",
                    "direction": "create a tiny game",
                    "inputs": {"path": str(target)},
                    "provider": {"allow_call": False},
                }
            )
            self.assertEqual(result["type"], "CREATION_ERROR")
            self.assertIn("allow_call=true", result["message"])
            self.assertFalse(target.exists())

        proposal = {
            "schema": "axm.local-creation-provider-response/v0.1",
            "project_type": "generic",
            "files": {"../escape.txt": "no\n"},
            "summary": "Unsafe proposal fixture.",
            "limitations": ["Rejected by the host."],
        }
        server, _received = self._server(proposal)
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "unsafe"
            result = UniversalCreationMachine(ROOT).create(
                {
                    "kind": "software-project",
                    "direction": "test unsafe provider output",
                    "inputs": {"path": str(target)},
                    "provider": {
                        "endpoint": f"http://127.0.0.1:{server.server_port}/v1",
                        "allow_call": True,
                    },
                }
            )
            self.assertEqual(result["type"], "CREATION_ERROR")
            self.assertIn("safely relative", result["message"])
            self.assertFalse(target.exists())

    def test_local_provider_executes_prepared_perspective_methods_without_fake_identities(self):
        workflow = start_workflow(
            "Inspect one bounded change.",
            {
                "goal": "Inspect one bounded change.",
                "steps": [
                    {
                        "id": "inspect-change",
                        "purpose": "Inspect the exact proposed change.",
                        "mode": "analysis",
                        "expected_evidence": ["one explicit finding"],
                        "stop_condition": "A bounded finding is recorded.",
                    }
                ],
                "planning_truth": "Explicit test plan.",
            },
        )
        checkpoint = prepare_checkpoint(ROOT, workflow, pool_size=8, seed="local-provider-test")
        analyses = {
            row["id"]: {
                "analysis": f"{row['name']} applies its declared method to the exact checkpoint.",
                "decision": "PROCEED",
                "evidence_refs": ["provider:test-fixture"],
            }
            for row in checkpoint["perspectives"]
        }
        response = {
            "schema": "axm.local-specialist-checkpoint-response/v0.1",
            "analyses": analyses,
            "limitations": ["One local model applied all method overlays."],
        }
        server, received = self._server(response)
        result = UniversalCreationMachine(ROOT).create(
            {
                "kind": "local-specialist-checkpoint",
                "inputs": {
                    "operation": "analyze-checkpoint",
                    "workflow": workflow,
                    "checkpoint": checkpoint,
                    "provider": {
                        "endpoint": f"http://127.0.0.1:{server.server_port}/v1",
                        "model": "waldo",
                        "allow_call": True,
                    },
                },
            }
        )
        self.assertEqual(result["type"], "CREATION_RESULT", result)
        provider_result = result["result"]
        self.assertEqual(provider_result["workflow"]["status"], "READY_TO_EXECUTE")
        self.assertFalse(provider_result["authority"]["independent_specialist_identities_claimed"])
        self.assertFalse(provider_result["authority"]["provider_analysis_is_external_evidence"])
        self.assertEqual(len(received), 1)


if __name__ == "__main__":
    unittest.main()
