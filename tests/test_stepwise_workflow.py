from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_uc.machine import UniversalCreationMachine
from axm_uc.stepwise_workflow import (
    STEPWISE_PLAN_SCHEMA,
    execute_current_step,
    prepare_checkpoint,
    prepare_stepwise_workflow,
    record_checkpoint_analysis,
    record_step_result,
    run_instant_staged,
    split_current_step,
    start_workflow,
)


class StepwisePerspectiveWorkflowTests(unittest.TestCase):
    @staticmethod
    def _step(step_id: str, purpose: str, *, action=None, depends_on=None):
        row = {
            "id": step_id,
            "purpose": purpose,
            "mode": "action" if action is not None else "analysis",
            "expected_evidence": [f"evidence for {step_id}"],
            "stop_condition": f"{step_id} has one inspectable result",
            "depends_on": depends_on or [],
            "perspective_focus": f"check whether {step_id} is small enough and correctly ordered",
        }
        if action is not None:
            row["action"] = action
        return row

    @classmethod
    def _plan(cls, goal: str, steps):
        return {
            "schema": STEPWISE_PLAN_SCHEMA,
            "goal": goal,
            "planning_truth": "explicit test plan selected from bounded planning work",
            "steps": steps,
        }

    @staticmethod
    def _analyses(checkpoint: dict, *, override_id: str | None = None, override_decision: str = "PROCEED"):
        result = {}
        for perspective in checkpoint["perspectives"]:
            specialist_id = perspective["id"]
            result[specialist_id] = {
                "analysis": f"{specialist_id} inspected this exact checkpoint",
                "decision": override_decision if specialist_id == override_id else "PROCEED",
                "evidence_refs": ["checkpoint fixture evidence"],
            }
        return result

    def test_live_machine_routes_stepwise_workflow(self):
        result = UniversalCreationMachine(ROOT).create({
            "kind": "stepwise-workflow",
            "inputs": {"operation": "inspect"},
        })
        self.assertEqual(result["type"], "CREATION_RESULT", result)
        self.assertTrue(result["result"]["instant_runs_preserve_logical_step_order"])
        self.assertEqual(
            result["result"]["chronology"],
            ["pre-analysis", "execution-or-result", "post-analysis", "advance"],
        )

    def test_prepare_uses_parallel_perspectives_without_claiming_a_plan_exists(self):
        prepared = prepare_stepwise_workflow(
            ROOT,
            "create a tiny verified local artifact",
            request={
                "kind": "text-file",
                "direction": "write one exact file",
                "inputs": {"path": "creations/stepwise.txt", "content": "hello"},
            },
            pool_size=12,
            team_size=3,
            max_teams=8,
        )
        self.assertEqual(prepared["status"], "AWAITING_PARALLEL_STEP_PLAN_PROPOSALS")
        self.assertIsNotNone(prepared["structural_context"])
        self.assertEqual(prepared["planning_tournament"]["status"], "READY_FOR_PARALLEL_SPECIALIST_CHALLENGE")
        self.assertIn("does not claim", prepared["truth_boundary"])
        self.assertEqual(prepared["required_plan_contract"]["maximum_initial_steps"], 64)

    def test_pre_execute_post_chronology_for_live_capability_step(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "microstep.txt"
            goal = "write one exact text file through staged reasoning"
            plan = self._plan(goal, [
                self._step(
                    "write",
                    "write the exact file",
                    action={"kind": "text-file", "inputs": {"path": str(target), "content": "micro\n"}},
                )
            ])
            workflow = start_workflow(goal, plan)
            pre = prepare_checkpoint(ROOT, workflow, pool_size=12, seed="pre")
            workflow = record_checkpoint_analysis(workflow, pre, self._analyses(pre))
            self.assertEqual(workflow["status"], "READY_TO_EXECUTE")
            workflow = execute_current_step(ROOT, workflow)
            self.assertEqual(workflow["status"], "AWAITING_POST_ANALYSIS")
            self.assertEqual(target.read_text(encoding="utf-8"), "micro\n")
            post = prepare_checkpoint(ROOT, workflow, pool_size=12, seed="post")
            workflow = record_checkpoint_analysis(workflow, post, self._analyses(post))
            self.assertEqual(workflow["status"], "COMPLETE")
            self.assertEqual(
                [row["type"] for row in workflow["timeline"]],
                ["PERSPECTIVE_CHECKPOINT", "STEP_RESULT", "PERSPECTIVE_CHECKPOINT"],
            )
            self.assertEqual([row.get("phase") for row in workflow["timeline"] if row["type"] == "PERSPECTIVE_CHECKPOINT"], ["pre", "post"])

    def test_any_perspective_can_force_broad_step_to_split(self):
        goal = "analyze two independent unknowns without hiding them in one step"
        plan = self._plan(goal, [
            self._step("broad", "inspect two independent unknowns"),
            self._step("after", "use the resolved unknowns", depends_on=["broad"]),
        ])
        workflow = start_workflow(goal, plan)
        checkpoint = prepare_checkpoint(ROOT, workflow, pool_size=12, seed="split")
        analyses = self._analyses(
            checkpoint,
            override_id=checkpoint["perspectives"][-1]["id"],
            override_decision="SPLIT",
        )
        workflow = record_checkpoint_analysis(workflow, checkpoint, analyses)
        self.assertEqual(workflow["status"], "SPLIT_REQUIRED")
        workflow = split_current_step(
            workflow,
            [
                self._step("unknown-a", "inspect only unknown A"),
                self._step("unknown-b", "inspect only unknown B"),
            ],
            reason="the checkpoint identified two independent questions",
        )
        self.assertEqual(workflow["status"], "AWAITING_PRE_ANALYSIS")
        ids = [row["id"] for row in workflow["plan"]["steps"]]
        self.assertEqual(ids, ["unknown-a", "unknown-b", "after"])
        self.assertEqual(workflow["plan"]["steps"][1]["depends_on"], ["unknown-a"])
        self.assertEqual(workflow["plan"]["steps"][2]["depends_on"], ["unknown-b"])
        self.assertEqual(workflow["plan"]["steps"][0]["split_depth"], 1)
        self.assertEqual(workflow["retired_steps"][0]["step"]["id"], "broad")

    def test_missing_live_action_route_holds_instead_of_inventing_execution(self):
        goal = "attempt one unavailable action truthfully"
        plan = self._plan(goal, [
            self._step(
                "missing",
                "invoke an action that is not installed",
                action={"kind": "not-a-live-step-kind", "inputs": {}},
            )
        ])
        workflow = start_workflow(goal, plan)
        checkpoint = prepare_checkpoint(ROOT, workflow, pool_size=8, seed="missing")
        workflow = record_checkpoint_analysis(workflow, checkpoint, self._analyses(checkpoint))
        workflow = execute_current_step(ROOT, workflow)
        self.assertEqual(workflow["status"], "HOLD_NO_LIVE_STEP_ROUTE")
        self.assertEqual(workflow["timeline"][-1]["type"], "STEP_EXECUTION_HOLD")

    def test_analysis_only_step_requires_explicit_external_result_then_post_review(self):
        goal = "inspect evidence without pretending the deterministic engine reasoned"
        plan = self._plan(goal, [self._step("inspect", "inspect one supplied hypothesis")])
        workflow = start_workflow(goal, plan)
        pre = prepare_checkpoint(ROOT, workflow, pool_size=8, seed="analysis-pre")
        workflow = record_checkpoint_analysis(workflow, pre, self._analyses(pre))
        workflow = record_step_result(
            workflow,
            {"finding": "executor supplied one bounded observation"},
            ["fixture observation"],
            executor="test-cognition-provider",
        )
        post = prepare_checkpoint(ROOT, workflow, pool_size=8, seed="analysis-post")
        workflow = record_checkpoint_analysis(workflow, post, self._analyses(post))
        self.assertEqual(workflow["status"], "COMPLETE")
        self.assertEqual(workflow["timeline"][1]["executor"], "test-cognition-provider")

    def test_instant_run_still_records_pre_result_post_for_every_step(self):
        goal = "complete two tiny analyses inside one call without collapsing chronology"
        plan = self._plan(goal, [
            self._step("one", "answer one bounded question"),
            self._step("two", "answer the next bounded question", depends_on=["one"]),
        ])

        # Build the exact deterministic perspective ids that the instant runner will ask for.
        shadow = start_workflow(goal, plan, selection_evidence="instant staged run selected plan")
        records = []
        for step_id in ("one", "two"):
            pre = prepare_checkpoint(ROOT, shadow, pool_size=12, seed=f"instant|{step_id}|pre")
            pre_analyses = self._analyses(pre)
            shadow = record_checkpoint_analysis(shadow, pre, pre_analyses)
            result = {"step": step_id, "finding": f"result-{step_id}"}
            shadow = record_step_result(shadow, result, [f"evidence-{step_id}"], executor="instant-test-executor")
            post = prepare_checkpoint(ROOT, shadow, pool_size=12, seed=f"instant|{step_id}|post")
            post_analyses = self._analyses(post)
            shadow = record_checkpoint_analysis(shadow, post, post_analyses)
            records.append({
                "step_id": step_id,
                "pre_analyses": pre_analyses,
                "result": result,
                "evidence": [f"evidence-{step_id}"],
                "executor": "instant-test-executor",
                "post_analyses": post_analyses,
            })

        workflow = run_instant_staged(
            ROOT,
            goal,
            plan,
            records,
            perspective_pool_size=12,
            seed="instant",
        )
        self.assertEqual(workflow["status"], "COMPLETE")
        self.assertEqual(workflow["completed_steps"], ["one", "two"])
        self.assertEqual(
            [(row["type"], row.get("phase"), row["step_id"]) for row in workflow["timeline"]],
            [
                ("PERSPECTIVE_CHECKPOINT", "pre", "one"),
                ("STEP_RESULT", None, "one"),
                ("PERSPECTIVE_CHECKPOINT", "post", "one"),
                ("PERSPECTIVE_CHECKPOINT", "pre", "two"),
                ("STEP_RESULT", None, "two"),
                ("PERSPECTIVE_CHECKPOINT", "post", "two"),
            ],
        )


if __name__ == "__main__":
    unittest.main()
