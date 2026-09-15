from __future__ import annotations

import copy
import io
import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from contextlib import redirect_stdout
from pathlib import Path

from axm_uc.procedural_effects import (
    GRAPH_SCHEMA,
    build_electric_arc,
    main,
    operate_procedural_effect,
    procedural_effect_catalog,
    publish_procedural_effect,
)


def request():
    return {
        "name": "Serious arc",
        "kind": "electric-arc",
        "seed": 42,
        "canvas": {"width": 800, "height": 600},
        "topology": {
            "source": [0.12, 0.18],
            "target": [0.83, 0.86],
            "grid": 48,
            "walkers": 32,
            "spread": 0.1,
            "octaves": 5,
            "roughness": 0.75,
        },
        "guides": {
            "points": [[0.4, 0.25], [0.62, 0.65]],
            "strength": 0.7,
            "radius": 0.14,
        },
        "realization": {
            "color": "#bfe7ff",
            "background": "#05070c",
            "core_width": 1.2,
            "glow_width": 11.0,
            "glow_strength": 0.8,
        },
    }


class ProceduralEffectsTests(unittest.TestCase):
    def test_catalog_is_truthfully_bounded(self):
        catalog = procedural_effect_catalog()
        self.assertTrue(catalog["offline"])
        self.assertFalse(catalog["ai_required"])
        self.assertEqual(list(catalog["effects"]), ["electric-arc"])
        self.assertEqual(catalog["effects"]["electric-arc"]["canonical_output"], GRAPH_SCHEMA)

    def test_same_recipe_is_deterministic_and_source_is_not_mutated(self):
        source = request()
        before = copy.deepcopy(source)
        first = build_electric_arc(source)
        second = build_electric_arc(source)
        self.assertEqual(source, before)
        self.assertEqual(first["graph_sha256"], second["graph_sha256"])
        self.assertEqual(first["graph"], second["graph"])
        self.assertGreater(first["graph"]["metrics"]["unique_edges"], 0)
        self.assertEqual(first["graph"]["paths"][0]["points"][0], source["topology"]["source"])
        self.assertEqual(first["graph"]["paths"][0]["points"][-1], source["topology"]["target"])

    def test_realization_changes_do_not_rewrite_canonical_topology(self):
        first_request = request()
        second_request = request()
        second_request["realization"].update(
            {"color": "#ff5500", "core_width": 3.0, "glow_width": 24.0}
        )
        first = build_electric_arc(first_request)
        second = build_electric_arc(second_request)
        self.assertEqual(first["graph_sha256"], second["graph_sha256"])
        self.assertNotEqual(first["recipe_sha256"], second["recipe_sha256"])

    def test_seed_and_guides_are_creation_controls(self):
        baseline = build_electric_arc(request())
        changed_seed = request()
        changed_seed["seed"] = 43
        changed_guides = request()
        changed_guides["guides"]["points"] = [[0.2, 0.75], [0.7, 0.25]]
        self.assertNotEqual(baseline["graph_sha256"], build_electric_arc(changed_seed)["graph_sha256"])
        self.assertNotEqual(baseline["graph_sha256"], build_electric_arc(changed_guides)["graph_sha256"])

    def test_publish_emits_editable_source_graph_and_replaceable_web_realization(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "arc"
            result = publish_procedural_effect(target, request())
            self.assertEqual(json.loads((target / "effect-graph.json").read_text())["schema"], GRAPH_SCHEMA)
            self.assertTrue((target / "recipe.json").is_file())
            self.assertTrue((target / "preview.html").is_file())
            ET.parse(target / "effect.svg")
            self.assertIn("replaceable realizations", result["receipt"]["canonical_authority"])
            with self.assertRaises(FileExistsError):
                publish_procedural_effect(target, request())

    def test_machine_adapter_confines_outputs_to_root(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            result = operate_procedural_effect(root, {"request": request(), "path": "out/arc"})
            self.assertEqual(result["result"]["graph"]["schema"], GRAPH_SCHEMA)
            with self.assertRaises(ValueError):
                operate_procedural_effect(root, {"request": request(), "path": "../escape"})

    def test_cli_executes_same_publication_surface(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            request_path = root / "request.json"
            request_path.write_text(json.dumps(request()), encoding="utf-8")
            with redirect_stdout(io.StringIO()):
                self.assertEqual(main(["electric-arc", str(request_path), str(root / "out")]), 0)
            self.assertEqual(json.loads((root / "out" / "effect-graph.json").read_text())["schema"], GRAPH_SCHEMA)
            with redirect_stdout(io.StringIO()) as output:
                self.assertEqual(main(["catalog"]), 0)
            self.assertIn("electric-arc", output.getvalue())

    def test_invalid_and_unbounded_requests_hold(self):
        bad = request()
        bad["topology"]["grid"] = 4096
        with self.assertRaises(ValueError):
            build_electric_arc(bad)
        bad = request()
        bad["realization"]["color"] = "electric-blue"
        with self.assertRaises(ValueError):
            build_electric_arc(bad)
        bad = request()
        bad["topology"]["target"] = bad["topology"]["source"]
        with self.assertRaises(ValueError):
            build_electric_arc(bad)


if __name__ == "__main__":
    unittest.main()
