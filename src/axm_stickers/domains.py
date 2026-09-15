"""Small built-in library of source-honest mathematical creation families.

These families encode relationships, not claims that one preset represents a
real-world population or engineering standard. Empirical/standardized size
libraries should be added separately with explicit provenance.
"""
from __future__ import annotations

import copy
from typing import Any

from .math import SCHEMA, validate_family

RELATION_SOURCE = "AXM mathematical relation; no empirical size claim"


def _parameter(unit: str, minimum: float, maximum: float, default: float) -> dict[str, Any]:
    return {
        "unit": unit,
        "min": minimum,
        "max": maximum,
        "default": default,
        "truth": "exact",
        "source": "AXM reference input domain; caller-selected quantity",
    }


FAMILIES: dict[str, dict[str, Any]] = {
    "geometry.circle": {
        "schema": SCHEMA,
        "id": "geometry.circle",
        "parameters": {"radius": _parameter("m", 0.000001, 1000000.0, 1.0)},
        "variants": {"unit_meter": {"radius": 1.0}, "compact_350mm": {"radius": 0.35}},
        "derived": {
            "diameter": {
                "unit": "m", "truth": "exact", "source": RELATION_SOURCE,
                "expr": {"op": {"name": "mul", "args": [{"param": "radius"}, 2]}},
            },
            "circumference": {
                "unit": "m", "truth": "exact", "source": RELATION_SOURCE,
                "expr": {"op": {"name": "mul", "args": [{"const": "tau"}, {"param": "radius"}]}},
            },
            "area": {
                "unit": "m2", "truth": "exact", "source": RELATION_SOURCE,
                "expr": {"op": {"name": "mul", "args": [
                    {"const": "pi"},
                    {"op": {"name": "pow", "args": [{"param": "radius"}, 2]}}
                ]}},
            },
        },
        "constraints": [{"label": "positive_radius", "left": {"param": "radius"}, "op": "gt", "right": {"quantity": {"value": 0, "unit": "m"}}}],
    },
    "geometry.box": {
        "schema": SCHEMA,
        "id": "geometry.box",
        "parameters": {
            "length": _parameter("m", 0.000001, 1000000.0, 1.0),
            "width": _parameter("m", 0.000001, 1000000.0, 1.0),
            "height": _parameter("m", 0.000001, 1000000.0, 1.0),
        },
        "variants": {"unit_cube": {"length": 1.0, "width": 1.0, "height": 1.0}},
        "derived": {
            "volume": {
                "unit": "m3", "truth": "exact", "source": RELATION_SOURCE,
                "expr": {"op": {"name": "mul", "args": [{"param": "length"}, {"param": "width"}, {"param": "height"}]}},
            },
            "surface_area": {
                "unit": "m2", "truth": "exact", "source": RELATION_SOURCE,
                "expr": {"op": {"name": "mul", "args": [2, {"op": {"name": "add", "args": [
                    {"op": {"name": "mul", "args": [{"param": "length"}, {"param": "width"}]}},
                    {"op": {"name": "mul", "args": [{"param": "length"}, {"param": "height"}]}},
                    {"op": {"name": "mul", "args": [{"param": "width"}, {"param": "height"}]}}
                ]}}]}},
            },
            "diagonal": {
                "unit": "m", "truth": "exact", "source": RELATION_SOURCE,
                "expr": {"op": {"name": "sqrt", "args": [{"op": {"name": "add", "args": [
                    {"op": {"name": "pow", "args": [{"param": "length"}, 2]}},
                    {"op": {"name": "pow", "args": [{"param": "width"}, 2]}},
                    {"op": {"name": "pow", "args": [{"param": "height"}, 2]}}
                ]}}]}},
            },
        },
        "constraints": [],
    },
    "motion.linear": {
        "schema": SCHEMA,
        "id": "motion.linear",
        "parameters": {
            "distance": _parameter("m", 0.0, 1000000000.0, 100.0),
            "duration": _parameter("s", 0.000001, 1000000000.0, 10.0),
        },
        "variants": {},
        "derived": {
            "speed_mps": {
                "unit": "m/s", "truth": "exact", "source": RELATION_SOURCE,
                "expr": {"op": {"name": "div", "args": [{"param": "distance"}, {"param": "duration"}]}},
            },
            "speed_kmh": {
                "unit": "km/h", "truth": "exact", "source": RELATION_SOURCE,
                "expr": {"op": {"name": "div", "args": [{"param": "distance"}, {"param": "duration"}]}},
            },
        },
        "constraints": [{"label": "positive_duration", "left": {"param": "duration"}, "op": "gt", "right": {"quantity": {"value": 0, "unit": "s"}}}],
    },
    "motion.constant_acceleration": {
        "schema": SCHEMA,
        "id": "motion.constant_acceleration",
        "parameters": {
            "initial_velocity": _parameter("m/s", -1000000.0, 1000000.0, 0.0),
            "acceleration": _parameter("m/s2", -1000000.0, 1000000.0, 1.0),
            "duration": _parameter("s", 0.0, 1000000.0, 1.0),
        },
        "variants": {},
        "derived": {
            "final_velocity": {
                "unit": "m/s", "truth": "exact",
                "source": "AXM constant-acceleration idealized relation",
                "expr": {"op": {"name": "add", "args": [
                    {"param": "initial_velocity"},
                    {"op": {"name": "mul", "args": [{"param": "acceleration"}, {"param": "duration"}]}}
                ]}},
            },
            "displacement": {
                "unit": "m", "truth": "exact",
                "source": "AXM constant-acceleration idealized relation",
                "expr": {"op": {"name": "add", "args": [
                    {"op": {"name": "mul", "args": [{"param": "initial_velocity"}, {"param": "duration"}]}},
                    {"op": {"name": "mul", "args": [
                        0.5, {"param": "acceleration"},
                        {"op": {"name": "pow", "args": [{"param": "duration"}, 2]}}
                    ]}}
                ]}},
            },
        },
        "constraints": [],
    },
    "waves.periodic": {
        "schema": SCHEMA,
        "id": "waves.periodic",
        "parameters": {
            "frequency": _parameter("Hz", 0.000001, 1000000000000.0, 1.0),
            "wavelength": _parameter("m", 0.000000001, 1000000000.0, 1.0),
        },
        "variants": {},
        "derived": {
            "period": {
                "unit": "s", "truth": "exact", "source": RELATION_SOURCE,
                "expr": {"op": {"name": "div", "args": [1, {"param": "frequency"}]}},
            },
            "phase_speed": {
                "unit": "m/s", "truth": "exact",
                "source": "AXM periodic-wave relation; medium behavior not inferred",
                "expr": {"op": {"name": "mul", "args": [{"param": "frequency"}, {"param": "wavelength"}]}},
            },
        },
        "constraints": [],
    },
    "rotation.wheel": {
        "schema": SCHEMA,
        "id": "rotation.wheel",
        "parameters": {
            "radius": _parameter("m", 0.000001, 1000000.0, 0.35),
            "angular_speed": _parameter("rad/s", -1000000.0, 1000000.0, 1.0),
        },
        "variants": {},
        "derived": {
            "rim_speed": {
                "unit": "m/s", "truth": "exact",
                "source": "AXM rigid no-slip kinematic relation; actual grip/slip not inferred",
                "expr": {"op": {"name": "div", "args": [
                    {"op": {"name": "mul", "args": [{"param": "radius"}, {"param": "angular_speed"}]}},
                    {"quantity": {"value": 1.0, "unit": "rad"}}
                ]}},
            },
            "circumference": {
                "unit": "m", "truth": "exact", "source": RELATION_SOURCE,
                "expr": {"op": {"name": "mul", "args": [{"const": "tau"}, {"param": "radius"}]}},
            },
            "rotation_frequency": {
                "unit": "Hz", "truth": "exact", "source": RELATION_SOURCE,
                "expr": {"op": {"name": "div", "args": [
                    {"param": "angular_speed"},
                    {"quantity": {"value": 1.0, "unit": "rev"}}
                ]}},
            },
        },
        "constraints": [],
    },
    "mechanism.gear_pair": {
        "schema": SCHEMA,
        "id": "mechanism.gear_pair",
        "parameters": {
            "input_teeth": _parameter("count", 1.0, 1000000.0, 20.0),
            "output_teeth": _parameter("count", 1.0, 1000000.0, 40.0),
            "input_speed": _parameter("rpm", -1000000.0, 1000000.0, 120.0),
        },
        "variants": {"two_to_one_reduction": {"input_teeth": 20.0, "output_teeth": 40.0}},
        "derived": {
            "ratio": {
                "unit": "ratio", "truth": "exact",
                "source": "AXM ideal external gear tooth-count ratio; losses/backlash not inferred",
                "expr": {"op": {"name": "div", "args": [{"param": "output_teeth"}, {"param": "input_teeth"}]}},
            },
            "output_speed": {
                "unit": "rpm", "truth": "exact",
                "source": "AXM ideal gear-speed relation; losses/backlash not inferred",
                "expr": {"op": {"name": "div", "args": [{"param": "input_speed"}, {"param": "ratio"}]}},
            },
        },
        "constraints": [],
    },
    "layout.aspect": {
        "schema": SCHEMA,
        "id": "layout.aspect",
        "parameters": {
            "width": _parameter("px", 1.0, 1000000.0, 1920.0),
            "height": _parameter("px", 1.0, 1000000.0, 1080.0),
        },
        "variants": {
            "hd_16_9": {"width": 1920.0, "height": 1080.0},
            "square": {"width": 1080.0, "height": 1080.0},
        },
        "derived": {
            "aspect_ratio": {
                "unit": "ratio", "truth": "exact",
                "source": RELATION_SOURCE,
                "expr": {"op": {"name": "div", "args": [{"param": "width"}, {"param": "height"}]}},
            }
        },
        "constraints": [],
    },
}


def domain_catalog() -> list[dict[str, Any]]:
    return [
        {
            "id": family_id,
            "parameters": sorted(family["parameters"]),
            "variants": sorted(family["variants"]),
            "derived": sorted(family["derived"]),
        }
        for family_id, family in sorted(FAMILIES.items())
    ]


def domain_family(family_id: str) -> dict[str, Any]:
    if family_id not in FAMILIES:
        raise ValueError("unknown mathematical domain family")
    return validate_family(copy.deepcopy(FAMILIES[family_id]))
