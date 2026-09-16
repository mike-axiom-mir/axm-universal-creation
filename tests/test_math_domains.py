import math
import unittest

from axm_stickers import convert, domain_catalog, domain_family, resolve_family, unit_info, validate_family


class MathDomainTests(unittest.TestCase):
    def test_builtin_unit_conversion_and_dimension_rejection(self):
        self.assertEqual(convert(100, "cm", "m"), 1.0)
        self.assertAlmostEqual(convert(36, "km/h", "m/s"), 10.0)
        self.assertEqual(unit_info("m3")["dimension"], {"length": 3})
        with self.assertRaisesRegex(ValueError, "incompatible"):
            convert(1, "kg", "m")

    def test_every_local_domain_family_validates_and_resolves(self):
        catalog = domain_catalog()
        self.assertGreaterEqual(len(catalog), 8)
        for entry in catalog:
            family = domain_family(entry["id"])
            self.assertEqual(validate_family(family)["id"], entry["id"])
            self.assertEqual(resolve_family(family)["family"], entry["id"])

    def test_circle_box_wave_and_gear_relations(self):
        circle = resolve_family(domain_family("geometry.circle"), overrides={"radius": 0.5})
        self.assertAlmostEqual(circle["derived"]["area"]["value"], math.pi * 0.25)

        box = resolve_family(domain_family("geometry.box"), overrides={"length": 2, "width": 3, "height": 4})
        self.assertEqual(box["derived"]["volume"]["value"], 24.0)

        wave = resolve_family(domain_family("waves.periodic"), overrides={"frequency": 2, "wavelength": 3})
        self.assertEqual(wave["derived"]["period"]["value"], 0.5)
        self.assertEqual(wave["derived"]["phase_speed"]["value"], 6.0)

        gear = resolve_family(domain_family("mechanism.gear_pair"))
        self.assertEqual(gear["derived"]["ratio"]["value"], 2.0)
        self.assertEqual(gear["derived"]["output_speed"]["value"], 60.0)

    def test_measured_inputs_are_not_upgraded_by_exact_equations(self):
        family = domain_family("geometry.circle")
        family["parameters"]["radius"]["truth"] = "measured"
        family["parameters"]["radius"]["uncertainty"] = 0.001
        result = resolve_family(family)
        self.assertEqual(result["derived"]["circumference"]["relation_truth"], "exact")
        self.assertEqual(result["derived"]["circumference"]["truth"], "measured")
        self.assertIn("derived uncertainty is not yet propagated", result["truth_boundary"])


if __name__ == "__main__":
    unittest.main()
