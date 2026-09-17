#!/usr/bin/env python3
"""Build retained neutral evidence for indexed-surface eligibility."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from axm_uc.indexed_surface_eligibility import (
    CROSS_SOURCE_TUPLE_POLICY,
    INPUT_SCHEMA,
    observe_indexed_surface_eligibility,
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _base():
    return {
        "schema": INPUT_SCHEMA,
        "source_identity": "neutral-indexed-quad-source-v1",
        "surface_identity": "neutral-indexed-quad",
        "source": {"vertex_count": 4, "indices": [0, 1, 2, 0, 2, 3]},
        "render": {
            "vertex_count": 4,
            "indices": [0, 1, 2, 0, 2, 3],
            "channels": {
                "POSITION": [[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0]],
                "NORMAL": [[0, 0, 1]] * 4,
            },
        },
    }


def _cases():
    preserve = _base()

    topology_mismatch = _base()
    topology_mismatch["surface_identity"] = "neutral-topology-lineage-mismatch"
    topology_mismatch["render"]["indices"] = [0, 2, 1, 0, 2, 3]

    dedup = _base()
    dedup["surface_identity"] = "neutral-expanded-corners"
    dedup["render"] = {
        "vertex_count": 6,
        "source_vertex_indices": [0, 1, 2, 0, 2, 3],
        "protected_split_ids": [None] * 6,
        "indices": list(range(6)),
        "channels": {
            "POSITION": [[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 0, 0], [1, 1, 0], [0, 1, 0]],
            "NORMAL": [[0, 0, 1]] * 6,
        },
    }

    uv_split = _base()
    uv_split["surface_identity"] = "neutral-uv-seam"
    uv_split["render"] = {
        "vertex_count": 5,
        "source_vertex_indices": [0, 1, 2, 3, 0],
        "protected_split_ids": [None] * 5,
        "indices": [0, 1, 2, 4, 2, 3],
        "channels": {
            "POSITION": [[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0], [0, 0, 0]],
            "NORMAL": [[0, 0, 1]] * 5,
            "TEXCOORD_0": [[0, 0], [1, 0], [1, 1], [0, 1], [1, 0]],
        },
    }

    protected = _base()
    protected["surface_identity"] = "neutral-protected-topology-split"
    protected["render"] = {
        "vertex_count": 5,
        "source_vertex_indices": [0, 1, 2, 3, 0],
        "protected_split_ids": ["sheet-a", None, None, None, "sheet-b"],
        "indices": [0, 1, 2, 4, 2, 3],
        "channels": {
            "POSITION": [[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0], [0, 0, 0]],
            "NORMAL": [[0, 0, 1]] * 5,
        },
    }

    cross_source = {
        "schema": INPUT_SCHEMA,
        "source_identity": "neutral-triangle-corner-source-v1",
        "surface_identity": "neutral-cross-source-tuple-candidate",
        "candidate_identity_policy": CROSS_SOURCE_TUPLE_POLICY,
        "source": {"vertex_count": 6, "indices": list(range(6))},
        "render": {
            "vertex_count": 6,
            "indices": list(range(6)),
            "protected_split_ids": [None] * 6,
            "channels": {
                "POSITION": [[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 0, 0], [1, 1, 0], [0, 1, 0]],
                "NORMAL": [[0, 0, 1]] * 6,
            },
        },
    }

    cross_source_missing_split = json.loads(json.dumps(cross_source))
    cross_source_missing_split["surface_identity"] = "neutral-cross-source-missing-split-declaration"
    del cross_source_missing_split["render"]["protected_split_ids"]

    ambiguous = json.loads(json.dumps(dedup))
    ambiguous["surface_identity"] = "neutral-ambiguous-expansion"
    del ambiguous["render"]["protected_split_ids"]

    unsupported = _base()
    unsupported["surface_identity"] = "neutral-unsupported-channel"
    unsupported["render"]["channels"]["CUSTOM_UNKNOWN"] = [[0]] * 4

    return {
        "preserve": preserve,
        "topology_mismatch": topology_mismatch,
        "dedup": dedup,
        "uv_split": uv_split,
        "protected_split": protected,
        "cross_source": cross_source,
        "cross_source_missing_split": cross_source_missing_split,
        "ambiguous": ambiguous,
        "unsupported": unsupported,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="indexed-surface-eligibility-evidence")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)

    expected = {
        "preserve": ("PRESERVE_SOURCE_INDEXING", "SAME_AS_SOURCE", 4),
        "topology_mismatch": ("HOLD_TOPOLOGY_LINEAGE_MISMATCH", "NOT_EVALUATED", None),
        "dedup": ("POST_ATTRIBUTE_TUPLE_DEDUP_CANDIDATE", "RENDER_DOMAIN_DERIVED", 4),
        "uv_split": ("PRESERVE_RENDER_DOMAIN_INDEXING", "RENDER_DOMAIN_SPLIT_REQUIRED", 5),
        "protected_split": ("PRESERVE_RENDER_DOMAIN_INDEXING", "RENDER_DOMAIN_SPLIT_REQUIRED", 5),
        "cross_source": ("POST_ATTRIBUTE_TUPLE_DEDUP_CANDIDATE", "RENDER_DOMAIN_CROSS_SOURCE_DEDUP_CANDIDATE", 4),
        "cross_source_missing_split": ("HOLD_CROSS_SOURCE_SPLIT_DECLARATION_REQUIRED", "NOT_EVALUATED", None),
        "ambiguous": ("HOLD_ATTRIBUTE_SEAM_AMBIGUITY", "NOT_EVALUATED", None),
        "unsupported": ("NOT_EVALUATED_UNSUPPORTED_CHANNEL", "NOT_EVALUATED", None),
    }

    summaries = {}
    for name, spec in _cases().items():
        report = observe_indexed_surface_eligibility(spec)
        state, domain, vertices = expected[name]
        if report["eligibility_state"] != state or report["render_domain_state"] != domain:
            raise SystemExit(f"{name}: unexpected state {report['eligibility_state']} / {report['render_domain_state']}")
        if vertices is None:
            if report["candidate"] is not None:
                raise SystemExit(f"{name}: held case unexpectedly produced candidate")
        elif report["candidate"]["vertex_count"] != vertices:
            raise SystemExit(f"{name}: candidate vertex count drift")
        _write(out / f"{name}.input.json", spec)
        _write(out / f"{name}.report.json", report)
        summaries[name] = {
            "eligibility_state": report["eligibility_state"],
            "render_domain_state": report["render_domain_state"],
            "candidate_identity_policy": report["candidate_identity_policy"],
            "candidate_vertex_count": None if report["candidate"] is None else report["candidate"]["vertex_count"],
            "input_digest": report["input_digest"],
            "topology_lineage_matches": report["topology_lineage"]["matches_source_index_stream"],
        }

    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    module = root / "src/axm_uc/indexed_surface_eligibility.py"
    receipt = {
        "schema": "axm.indexed-surface-eligibility-evidence/v0.2",
        "uc_head": head,
        "observer_path": str(module.relative_to(root)),
        "observer_sha256": _sha(module),
        "cases": summaries,
        "truth_boundary": {
            "observer_only": True,
            "surface_mutation": False,
            "visual_equality_proven": False,
            "runtime_savings_proven": False,
            "adoption_authorized": False,
            "cross_source_tuple_mode_requires_explicit_split_declaration": True,
        },
    }
    _write(out / "receipt.json", receipt)
    manifest = {path.name: _sha(path) for path in sorted(out.iterdir()) if path.is_file()}
    _write(out / "sha256-manifest.json", manifest)
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
