import copy
import unittest

from axm_uc.atom_novelty import classify_creator_atoms


def part(task_id, color, size=(1, 1, 1)):
    return {
        "id": task_id,
        "dependencies": [],
        "request": {
            "operation": "create_3d",
            "id": task_id,
            "name": task_id,
            "socket": "mount",
            "author": "AXM",
            "license": "CC0-1.0",
            "source": "test",
            "spec": {
                "schema": "axm.procedural-3d/v0.1",
                "name": task_id,
                "primitives": [{
                    "id": "body",
                    "type": "box",
                    "size": list(size),
                    "translation": [0, 0, 0],
                    "material": {"color": color, "metallic": 0.1, "roughness": 0.6},
                }],
            },
        },
    }


class AtomNoveltyTests(unittest.TestCase):
    def test_color_only_variant_is_not_a_new_atom(self):
        plan = {"tasks": [part("red", "#ff0000"), part("blue", "#0000ff")]}
        result = classify_creator_atoms(plan)
        self.assertEqual(result["counts"], {
            "successful_parts": 2,
            "novel_atoms": 1,
            "deduplicated_variants": 1,
            "appearance_families": 1,
        })
        self.assertEqual(result["tasks"][1]["duplicate_of"], "red")
        self.assertTrue(result["tasks"][1]["variant_not_growth"])
        self.assertNotEqual(result["tasks"][0]["exact_variant_digest"], result["tasks"][1]["exact_variant_digest"])

    def test_geometry_change_is_a_new_atom(self):
        plan = {"tasks": [part("small", "#ff0000"), part("large", "#ff0000", size=(2, 1, 1))]}
        result = classify_creator_atoms(plan)
        self.assertEqual(result["counts"]["novel_atoms"], 2)
        self.assertTrue(all(task["novel_atom"] for task in result["tasks"]))

    def test_material_behavior_change_is_appearance_family_not_shape_spam(self):
        a = part("matte", "#ff0000")
        b = copy.deepcopy(part("metal", "#ff0000"))
        b["request"]["spec"]["primitives"][0]["material"]["metallic"] = 0.9
        result = classify_creator_atoms({"tasks": [a, b]})
        self.assertEqual(result["counts"]["novel_atoms"], 1)
        self.assertEqual(result["counts"]["appearance_families"], 2)


if __name__ == "__main__":
    unittest.main()
