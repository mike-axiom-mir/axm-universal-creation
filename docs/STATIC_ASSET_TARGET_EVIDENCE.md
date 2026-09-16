# Static Asset Target Evidence Gate v0.1

`axm_uc.static_asset_target_evidence.verify_static_asset_target_evidence()` binds target-context evidence to the exact bytes of one static GLB and refuses to turn weak or missing evidence into a stronger claim.

## Why this exists

Universal Creation can inspect static GLB structure and measure resource budgets, but those checks do not prove that an asset actually works in a particular engine, collision scene, navigation context, camera distance, or device budget.

This gate provides a reusable bridge between those external target tests and UC's truth boundary:

- the packet names the exact target engine/context;
- the packet names which lanes are required for this use;
- every packet is bound to the artifact SHA-256;
- a declared PASS needs an evidence kind appropriate to that lane;
- missing or `NOT_TESTED` required lanes remain `HOLD`;
- any supplied target failure remains `FAIL`, even when that lane was not originally required;
- structural/source inspection alone cannot silently become collision, navigation, LOD-visual, or performance proof.

The gate does **not** launch an engine or reproduce the referenced evidence itself. A gate PASS means the declared required evidence packet is complete, appropriately typed, and bound to the exact artifact—not that UC independently certified production readiness.

## Evidence lanes

The v0.1 closed lane set is:

| Lane | PASS needs at least one of |
| --- | --- |
| `target_engine_import` | `TESTED` |
| `scale_pivot` | `TESTED`, `MEASURED` |
| `material_shader` | `TESTED`, `VISUALLY_INSPECTED` |
| `collision` | `TESTED`, `MEASURED` |
| `navigation` | `TESTED`, `MEASURED` |
| `resource_budget` | `TESTED`, `MEASURED` |
| `material_sidedness` | `TESTED`, `VISUALLY_INSPECTED` |
| `lod_perceptual_equivalence` | `VISUALLY_INSPECTED` |
| `target_runtime_integration` | `TESTED`, `MEASURED` |
| `target_device_performance` | `MEASURED` |

`SOURCE_INSPECTED` and `INFERRED` can be retained as evidence records, but they do not by themselves promote any lane to PASS.

## Example

```python
import hashlib
from pathlib import Path

from axm_uc.static_asset_target_evidence import (
    PACKET_SCHEMA,
    verify_static_asset_target_evidence,
)

asset = Path("workshop.glb")
sha256 = hashlib.sha256(asset.read_bytes()).hexdigest()

packet = {
    "schema": PACKET_SCHEMA,
    "artifact_sha256": sha256,
    "target": {
        "engine": "Example Engine",
        "version": "1.2",
        "context": "RTS building",
    },
    "required_lanes": [
        "target_engine_import",
        "scale_pivot",
        "collision",
        "navigation",
        "resource_budget",
    ],
    "lanes": {
        "target_engine_import": {
            "status": "PASS",
            "evidence": [{
                "kind": "TESTED",
                "source": "engine-import-test",
                "summary": "Imported without loader errors.",
            }],
        },
        "scale_pivot": {
            "status": "PASS",
            "evidence": [{
                "kind": "MEASURED",
                "source": "engine-transform-report",
                "summary": "Scale and pivot matched the declared target transform.",
            }],
        },
        "collision": {
            "status": "NOT_TESTED",
            "notes": ["No target collision scene yet."],
        },
        "navigation": {
            "status": "NOT_TESTED",
            "notes": ["No target navigation bake/test yet."],
        },
        "resource_budget": {
            "status": "PASS",
            "evidence": [{
                "kind": "MEASURED",
                "source": "axm.static-asset-budget-evidence/v0.1 report",
                "summary": "The caller-declared target resource budget passed.",
            }],
        },
    },
}

report = verify_static_asset_target_evidence(asset, packet)
assert report["status"] == "HOLD"  # collision/navigation are still untested
```

## Truth boundary

This module verifies:

- a supported GLB container exists at the supplied path;
- packet and artifact SHA-256 identity agree;
- the target/required-lane contract is structurally valid;
- required lanes are present;
- PASS lanes include at least one qualifying evidence kind;
- supplied failures remain visible and block the overall gate.

It does **not** prove:

- that an evidence locator is independently trustworthy;
- target-engine compatibility outside the named target;
- collision correctness beyond the referenced target tests;
- navigation correctness beyond the referenced target tests;
- LOD perceptual equivalence unless a visual inspection receipt exists;
- target-device performance unless measured evidence exists;
- game readiness, final Art Director acceptance, gameplay readability, or production readiness.

This directly complements `axm.static-asset-budget/v0.1`: budget evidence can be one lane inside a broader target-context evidence packet without allowing the budget result to impersonate engine/runtime evidence.
