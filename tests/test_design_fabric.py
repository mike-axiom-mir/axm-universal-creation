from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_uc.design_fabric import (
    DESIGN_GENOME_SCHEMA,
    DESIGN_JUDGMENT_SCHEMA,
    DESIGN_OBSERVATION_SCHEMA,
    DESIGN_PLAN_SCHEMA,
    DesignFabricError,
    compose_design_plan,
    derive_design_genome,
    judge_design_plan,
    observe_project_style,
    validate_design_genome,
)
from axm_uc.machine import UniversalCreationMachine


REFERENCE_CSS = """
:root {
  --surface: #101010;
  --text: #F8F8F8;
  --space: 16px;
}
body {
  margin: 0;
  font-family: Inter, sans-serif;
  background: #101010;
  color: #F8F8F8;
}
.card {
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 8px 30px #000000;
}
.btn {
  color: #101010;
  background: #F8F8F8;
  transition: transform 180ms ease;
}
.btn:hover { transform: translateY(-1px); }
.btn:focus-visible { outline: 2px solid #F8F8F8; }
@media (min-width: 768px) {
  .card { padding: 24px; }
}
"""

REFERENCE_HTML = """<!doctype html>
<html lang="en">
<body>
  <main>
    <section class="card">
      <button class="btn" aria-label="Continue">Continue</button>
    </section>
  </main>
</body>
</html>
"""


class DesignFabricTests(unittest.TestCase):
    @staticmethod
    def write_reference(target: Path) -> None:
        target.mkdir(parents=True, exist_ok=True)
        (target / "index.html").write_text(REFERENCE_HTML, encoding="utf-8")
        (target / "style.css").write_text(REFERENCE_CSS, encoding="utf-8")

    @staticmethod
    def enrich_for_complete_plan(genome: dict) -> dict:
        genome = copy.deepcopy(genome)
        button = next(component for component in genome["components"] if component["id"] == "btn")
        button["description"] = "Primary action button supplied with explicit semantics for the test."
        button["roles"] = ["primary-action"]
        button["tags"] = ["action", "control"]
        button["interactive"] = True
        button["states"] = ["default", "hover", "focus", "active", "disabled"]
        button["source_status"] = "explicit-test-semantics"
        genome["motion"]["reduced_motion_strategy"] = "disable-nonessential"
        return genome

    def test_reference_lens_observes_source_signals_without_claiming_visual_semantics(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "reference"
            self.write_reference(target)
            first = observe_project_style(target)
            second = observe_project_style(target)

        self.assertEqual(first["schema"], DESIGN_OBSERVATION_SCHEMA)
        self.assertEqual(first["truth_status"], "OBSERVED_LOCAL_SOURCE_STYLE_SIGNALS")
        self.assertEqual(first["observation_digest"], second["observation_digest"])
        self.assertEqual(first["source"]["file_count"], 2)
        colors = {row["value"] for row in first["signals"]["colors"]}
        self.assertTrue({"#101010", "#F8F8F8"}.issubset(colors))
        self.assertEqual(first["signals"]["breakpoints"][0]["value"], "768px")
        button = next(row for row in first["signals"]["component_selector_signals"] if row["selector"] == ".btn")
        self.assertEqual(button["states_observed"], ["focus", "hover"])
        self.assertEqual(button["truth_status"], "SELECTOR_SIGNAL_ONLY_NOT_SEMANTIC_COMPONENT_PROOF")
        self.assertGreaterEqual(first["signals"]["aria_attribute_count"], 1)
        self.assertIn("source observation is lexical and structural, not visual perception", first["limitations"])

    def test_derived_genome_is_deterministic_and_separates_reference_signal_from_axm_policy(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "reference"
            self.write_reference(target)
            observation = observe_project_style(target)
            first = derive_design_genome(observation, "axm.test.reference", "0.1.0", "test reference grammar")
            second = derive_design_genome(observation, "axm.test.reference", "0.1.0", "test reference grammar")

        genome = first["genome"]
        self.assertEqual(genome["schema"], DESIGN_GENOME_SCHEMA)
        self.assertEqual(genome["genome_digest"], second["genome"]["genome_digest"])
        self.assertGreaterEqual(first["coverage"]["colors"], 2)
        self.assertGreaterEqual(first["coverage"]["component_selector_signals"], 2)
        self.assertEqual(genome["quality_gates"]["policy_origin"], "AXM_DESIGN_FABRIC_DEFAULT_NOT_REFERENCE_DERIVED")
        self.assertFalse(genome["provenance"]["source_composition_copied"])
        self.assertFalse(genome["provenance"]["semantic_roles_inferred"])
        self.assertFalse(genome["provenance"]["visual_quality_observed"])
        self.assertEqual(genome["motion"]["reduced_motion_strategy"], "unknown")
        self.assertTrue(all(not component["roles"] for component in genome["components"]))

    def test_complete_explicit_genome_can_compose_and_pass_structural_design_gates(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "reference"
            self.write_reference(target)
            observation = observe_project_style(target)
            genome = derive_design_genome(observation, "axm.test.control", "0.1.0", "control surface")["genome"]

        genome = self.enrich_for_complete_plan(genome)
        by_color = {row["value"]: row["id"] for row in genome["tokens"]["colors"]}
        request = {
            "goal": "original responsive control surface",
            "required_roles": ["primary-action"],
            "components": [],
            "viewports": ["mobile", "desktop"],
            "contrast_pairs": [
                {
                    "foreground": by_color["#F8F8F8"],
                    "background": by_color["#101010"],
                }
            ],
        }
        plan = compose_design_plan(genome, request)
        judgment = judge_design_plan(plan)

        self.assertEqual(plan["schema"], DESIGN_PLAN_SCHEMA)
        self.assertEqual(plan["selected_components"][0]["id"], "btn")
        self.assertEqual(plan["missing_roles"], [])
        self.assertTrue(plan["contrast_pairs"][0]["passed"])
        self.assertEqual(judgment["schema"], DESIGN_JUDGMENT_SCHEMA)
        self.assertEqual(judgment["status"], "PASS")
        self.assertTrue(judgment["passed"])
        self.assertTrue(all(gate["status"] == "PASS" for gate in judgment["gates"]))
        self.assertIn("rendered visual hierarchy", judgment["unobserved"])

    def test_missing_visual_evidence_holds_instead_of_becoming_fake_quality(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "reference"
            self.write_reference(target)
            observation = observe_project_style(target)
            genome = derive_design_genome(observation, "axm.test.hold", "0.1.0", "reference-only genome")["genome"]

        plan = compose_design_plan(
            genome,
            {
                "goal": "reference-only draft",
                "required_roles": [],
                "components": ["btn"],
                "viewports": ["mobile", "desktop"],
                "contrast_pairs": [],
            },
        )
        judgment = judge_design_plan(plan)
        self.assertEqual(judgment["status"], "HOLD")
        self.assertFalse(judgment["passed"])
        by_gate = {row["gate"]: row for row in judgment["gates"]}
        self.assertEqual(by_gate["reduced-motion-strategy"]["status"], "HOLD")
        self.assertEqual(by_gate["explicit-text-contrast"]["status"], "HOLD")

    def test_genome_validation_fails_closed_on_unknown_fields_and_bad_references(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "reference"
            self.write_reference(target)
            genome = derive_design_genome(
                observe_project_style(target),
                "axm.test.invalid",
                "0.1.0",
                "invalidity test",
            )["genome"]

        unknown = copy.deepcopy(genome)
        unknown["magic"] = True
        with self.assertRaises(DesignFabricError):
            validate_design_genome(unknown)

        bad = self.enrich_for_complete_plan(genome)
        with self.assertRaises(DesignFabricError):
            compose_design_plan(
                bad,
                {
                    "goal": "bad contrast ref",
                    "required_roles": ["primary-action"],
                    "components": [],
                    "viewports": ["desktop"],
                    "contrast_pairs": [{"foreground": "missing-color", "background": bad["tokens"]["colors"][0]["id"]}],
                },
            )

    def test_live_machine_routes_design_fabric_and_materialization_respects_machine_boundary(self):
        machine = UniversalCreationMachine(ROOT)
        inspection = machine.create({
            "kind": "inspect-design-fabric",
            "inputs": {"operation": "inspect-schema"},
        })
        self.assertEqual(inspection["type"], "CREATION_RESULT")
        self.assertEqual(inspection["capability"], "AXM-CAP-DESIGN-FABRIC")
        self.assertEqual(inspection["result"]["genome_schema"], DESIGN_GENOME_SCHEMA)
        self.assertFalse(inspection["result"]["screenshot_comparison_available"])

        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "reference"
            self.write_reference(source)
            observed = machine.create({
                "kind": "observe-design-reference",
                "inputs": {"operation": "observe-project", "path": str(source)},
            })
            self.assertEqual(observed["type"], "CREATION_RESULT")
            genome = derive_design_genome(
                observed["result"],
                "axm.test.machine",
                "0.1.0",
                "machine route test",
            )["genome"]
            genome = self.enrich_for_complete_plan(genome)
            by_color = {row["value"]: row["id"] for row in genome["tokens"]["colors"]}
            request = {
                "goal": "machine routed design descriptor",
                "required_roles": ["primary-action"],
                "components": [],
                "viewports": ["mobile", "desktop"],
                "contrast_pairs": [{
                    "foreground": by_color["#F8F8F8"],
                    "background": by_color["#101010"],
                }],
            }
            materialized = machine.create({
                "kind": "materialize-design-plan",
                "inputs": {
                    "operation": "materialize",
                    "path": str(Path(td) / "design-output"),
                    "genome": genome,
                    "request": request,
                },
            })
            self.assertEqual(materialized["type"], "CREATION_RESULT")
            self.assertTrue(materialized["result"]["validation"]["passed"])
            self.assertEqual(materialized["result"]["design_judgment"]["status"], "PASS")

        blocked_target = ROOT / "src" / "should-not-write-design"
        blocked = machine.create({
            "kind": "materialize-design-plan",
            "inputs": {
                "operation": "materialize",
                "path": "src/should-not-write-design",
                "genome": genome,
                "request": request,
            },
        })
        self.assertEqual(blocked["type"], "CREATION_ERROR")
        self.assertFalse(blocked_target.exists())


if __name__ == "__main__":
    unittest.main()
