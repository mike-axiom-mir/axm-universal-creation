from __future__ import annotations

import json
import sys
import unittest
from copy import deepcopy
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_uc import neutral_compute as NC
from axm_uc.material_response import material_response_catalog
from axm_uc.shape_recipe import compile_shape_recipe


VECTORS = json.loads((ROOT / "tests" / "fixtures" / "neutral_compute_v0_1.json").read_text(encoding="utf-8"))


def _decode(body: dict[str, Any]) -> Any:
    if body["kind"] == "json":
        return deepcopy(body["value"])
    if body["kind"] == "bytes-base64":
        import base64
        return base64.b64decode(body["value"])
    raise AssertionError(f"unknown body kind: {body['kind']}")


def _ref(body: dict[str, Any]) -> dict[str, Any]:
    value = _decode(body)
    if body["kind"] == "bytes-base64":
        return NC.artifact_ref(value, hash_kind="bytes", representation="bytes")
    return NC.artifact_ref(value, hash_kind="canonical-json", representation="canonical-json")


def _actions(plan: dict[str, Any]) -> dict[str, str]:
    return {key: value["action"] for key, value in sorted(plan.get("contracts", {}).items())}


def _decisions(head_like: dict[str, Any]) -> dict[str, str]:
    return {key: value["decision"] for key, value in sorted(head_like.get("contracts", {}).items())}


def _partial(actual: Any, expected: Any, path: str = "$") -> tuple[bool, str | None]:
    if isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            return False, path
        for index, item in enumerate(expected):
            ok, where = _partial(actual[index], item, f"{path}[{index}]")
            if not ok:
                return ok, where
        return True, None
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            return False, path
        for key, item in expected.items():
            if key not in actual:
                return False, f"{path}.{key}"
            ok, where = _partial(actual[key], item, f"{path}.{key}")
            if not ok:
                return ok, where
        return True, None
    return (actual == expected, None if actual == expected else path)


class VectorContext:
    def __init__(self, setup: dict[str, Any]):
        artifacts = {key: _ref(value) for key, value in setup["artifacts"].items()}
        self.runtime = NC.create_runtime(
            label="uc-neutral-conformance",
            contracts=deepcopy(setup["contracts"]),
            artifacts=artifacts,
        )
        self.vars: dict[str, Any] = {}

    def sequence(self) -> int:
        head = NC.current_head(self.runtime)
        assert head is not None
        return head["sequence"]

    def hot(self) -> list[str]:
        return sorted(self.runtime.get("hot", {}))


def _step(ctx: VectorContext, spec: dict[str, Any]) -> dict[str, Any]:
    op = spec["op"]

    if op == "remember_current":
        head = NC.current_head(ctx.runtime)
        assert head is not None
        if spec.get("save_generation"):
            ctx.vars[spec["save_generation"]] = head["generation_sha256"]
        return {"status": "REMEMBERED", "current_sequence": head["sequence"]}

    if op == "plan":
        result = NC.plan_mutation(
            ctx.runtime,
            selectors=spec.get("selectors", []),
            reason="neutral-conformance",
        )
        if spec.get("save_as") and result["status"] == "PLANNED":
            ctx.vars[spec["save_as"]] = result
        out = {"status": result["status"], "current_sequence": ctx.sequence()}
        if "contracts" in result:
            out["actions"] = _actions(result)
        if "unknown_selectors" in result:
            out["unknown_selectors"] = deepcopy(result["unknown_selectors"])
        return out

    if op in {"stage", "stage_from_current"}:
        plan = ctx.vars[spec["plan"]]
        updates: dict[str, Any] = {}
        if op == "stage_from_current":
            head = NC.current_head(ctx.runtime)
            assert head is not None
            for contract_id, route in spec.get("routes", {}).items():
                updates[contract_id] = {**deepcopy(head["contracts"][contract_id]), "route": route}
        else:
            for contract_id, update in spec.get("updates", {}).items():
                updates[contract_id] = {**_ref(update["body"]), "route": update.get("route")}
        result = NC.stage_generation(ctx.runtime, plan, updates)
        if spec.get("save_as") and result["status"] == "STAGED":
            ctx.vars[spec["save_as"]] = result
        out = {"status": result["status"], "current_sequence": ctx.sequence()}
        if "contract" in result:
            out["contract"] = result["contract"]
        if "generation" in result:
            out["staged_sequence"] = result["generation"]["sequence"]
            out["decisions"] = _decisions(result["generation"])
        return out

    if op == "commit":
        result = NC.commit_generation(ctx.runtime, ctx.vars[spec["stage"]], actor="neutral-conformance")
        head = NC.current_head(ctx.runtime)
        assert head is not None
        if spec.get("save_generation") and result["status"] == "COMMITTED":
            ctx.vars[spec["save_generation"]] = head["generation_sha256"]
        return {
            "status": result["status"],
            "current_sequence": head["sequence"],
            "decisions": _decisions(head),
        }

    if op == "rollback":
        result = NC.rollback(ctx.runtime, ctx.vars.get(spec["target"], spec["target"]), actor="neutral-conformance")
        return {"status": result["status"], "current_sequence": ctx.sequence()}

    if op == "reactivate":
        result = NC.reactivate(ctx.runtime, ctx.vars.get(spec["target"], spec["target"]), actor="neutral-conformance")
        return {"status": result["status"], "current_sequence": ctx.sequence()}

    if op == "wake":
        result = NC.wake_contract(ctx.runtime, spec["contract"], _decode(spec["body"]))
        return {"status": result["status"], "current_sequence": ctx.sequence(), "hot_contracts": ctx.hot()}

    if op == "sleep":
        result = NC.sleep_contract(ctx.runtime, spec["contract"])
        return {"status": result["status"], "current_sequence": ctx.sequence(), "hot_contracts": ctx.hot()}

    if op == "restart":
        ctx.runtime = NC.import_runtime(json.loads(json.dumps(NC.export_runtime(ctx.runtime))))
        return {"status": "RESTARTED", "current_sequence": ctx.sequence(), "hot_contracts": ctx.hot()}

    if op == "tamper_import":
        exported = json.loads(json.dumps(NC.export_runtime(ctx.runtime)))
        generation = exported["generations"][exported["current_generation_sha256"]]
        generation["contracts"][spec["contract"]][spec["field"]] = deepcopy(spec["value"])
        refused = False
        try:
            NC.import_runtime(exported)
        except NC.NeutralComputeError:
            refused = True
        return {
            "status": "REFUSED_TAMPERED_RUNTIME" if refused else "UNSAFE_ACCEPTED_TAMPERED_RUNTIME",
            "current_sequence": ctx.sequence(),
        }

    raise AssertionError(f"unknown conformance op: {op}")


def _small_recipe(count: int) -> dict[str, Any]:
    return {
        "schema": "axm.shape-recipe/v0.1",
        "name": "Neutral compute UC proof",
        "vars": {"count": count},
        "parts": [
            {
                "repeat": ["var", "count"],
                "as": "i",
                "body": [
                    {
                        "shape": "box",
                        "size": [0.2, 0.2, 0.2],
                        "pos": [["*", 0.5, ["var", "i"]], 0, 0],
                    }
                ],
            }
        ],
    }


class NeutralComputeConformanceTests(unittest.TestCase):
    def test_hash_primitives_match_neutral_vectors(self):
        self.assertEqual(
            NC.hash_canonical(VECTORS["hash_primitives"]["canonical_json"]["value"]),
            VECTORS["hash_primitives"]["canonical_json"]["sha256"],
        )
        import base64
        self.assertEqual(
            NC.hash_bytes(base64.b64decode(VECTORS["hash_primitives"]["bytes_base64"]["value"])),
            VECTORS["hash_primitives"]["bytes_base64"]["sha256"],
        )

    def test_uc_native_python_runtime_consumes_pinned_neutral_vectors(self):
        failures = []
        for case in VECTORS["cases"]:
            ctx = VectorContext(case.get("setup", VECTORS["default_setup"]))
            for index, step in enumerate(case["steps"]):
                actual = _step(ctx, step)
                ok, mismatch = _partial(actual, step.get("expect", {}))
                if not ok:
                    failures.append({
                        "case": case["id"],
                        "step": index,
                        "op": step["op"],
                        "mismatch": mismatch,
                        "actual": actual,
                        "expected": step.get("expect", {}),
                    })
                    break
        self.assertEqual(failures, [])

    def test_real_uc_shape_recipe_updates_only_dependent_contracts(self):
        recipe_v0 = _small_recipe(2)
        compiled_v0 = compile_shape_recipe(recipe_v0)
        material_catalog = material_response_catalog()

        runtime = NC.create_runtime(
            label="uc-shape-recipe-retained-state",
            contracts=[
                {
                    "id": "creator-source",
                    "depends_on": ["uc:shape-recipe/**"],
                    "allowed_routes": ["retain-source"],
                },
                {
                    "id": "compiled-realization",
                    "depends_on": ["uc:shape-recipe/**", "uc:material-response/**"],
                    "allowed_routes": ["compile-shape-recipe"],
                },
                {
                    "id": "material-response-catalog",
                    "depends_on": ["uc:material-response/**"],
                    "allowed_routes": ["resolve-material-response"],
                },
            ],
            artifacts={
                "creator-source": NC.artifact_ref(recipe_v0),
                "compiled-realization": NC.artifact_ref(compiled_v0["specification"]),
                "material-response-catalog": NC.artifact_ref(material_catalog),
            },
        )
        before = NC.current_head(runtime)
        assert before is not None

        recipe_v1 = _small_recipe(3)
        compiled_v1 = compile_shape_recipe(recipe_v1)
        self.assertNotEqual(compiled_v0["recipe_sha256"], compiled_v1["recipe_sha256"])

        plan = NC.plan_mutation(
            runtime,
            selectors=["uc:shape-recipe/proof"],
            reason="creator changed one retained recipe input",
        )
        self.assertEqual(plan["status"], "PLANNED")
        self.assertEqual(plan["contracts"]["creator-source"]["action"], "UPDATE_REQUIRED")
        self.assertEqual(plan["contracts"]["compiled-realization"]["action"], "UPDATE_REQUIRED")
        self.assertEqual(plan["contracts"]["material-response-catalog"]["action"], "REUSE_EXACT")

        stage = NC.stage_generation(
            runtime,
            plan,
            {
                "creator-source": {
                    **NC.artifact_ref(recipe_v1),
                    "route": "retain-source",
                },
                "compiled-realization": {
                    **NC.artifact_ref(compiled_v1["specification"]),
                    "route": "compile-shape-recipe",
                },
            },
        )
        self.assertEqual(stage["status"], "STAGED")
        self.assertEqual(NC.current_head(runtime)["generation_sha256"], before["generation_sha256"])

        committed = NC.commit_generation(runtime, stage, actor="uc-proof")
        self.assertEqual(committed["status"], "COMMITTED")
        after = NC.current_head(runtime)
        assert after is not None
        self.assertEqual(after["contracts"]["material-response-catalog"]["artifact_sha256"],
                         before["contracts"]["material-response-catalog"]["artifact_sha256"])
        self.assertEqual(after["contracts"]["material-response-catalog"]["decision"], "REUSED_EXACT")
        self.assertEqual(after["contracts"]["creator-source"]["decision"], "UPDATED")
        self.assertEqual(after["contracts"]["compiled-realization"]["decision"], "UPDATED")

    def test_unknown_uc_source_holds_instead_of_declaring_everything_reusable(self):
        recipe = _small_recipe(2)
        compiled = compile_shape_recipe(recipe)
        runtime = NC.create_runtime(
            contracts=[{
                "id": "shape",
                "depends_on": ["uc:shape-recipe/**"],
                "allowed_routes": ["compile-shape-recipe"],
            }],
            artifacts={"shape": NC.artifact_ref(compiled["specification"])},
        )
        result = NC.plan_mutation(runtime, selectors=["uc:unknown-future-source/value"])
        self.assertEqual(result["status"], "HOLD_UNKNOWN_SELECTOR")


if __name__ == "__main__":
    unittest.main()
