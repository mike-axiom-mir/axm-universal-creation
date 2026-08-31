from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any


# Minimal local grammar awareness for creation/repair. The shape is influenced by
# the explicit grammar-profile approach in axm-102-grammer, but this module does
# not import that repository's learning ledgers or claim its full 102 grammars.
# Each entry says only what this runtime can currently identify or validate.
GRAMMAR_BY_SUFFIX: dict[str, dict[str, Any]] = {
    ".py": {
        "grammar_id": "python",
        "identification": "file-extension",
        "validation": "parser-backed",
        "validator": "python-compile",
    },
    ".json": {
        "grammar_id": "json",
        "identification": "file-extension",
        "validation": "parser-backed-automatic",
        "validator": "json-valid",
    },
    ".html": {
        "grammar_id": "html",
        "identification": "file-extension",
        "validation": "structural-link-check-only",
        "validator": "html-local-links",
    },
    ".htm": {
        "grammar_id": "html",
        "identification": "file-extension",
        "validation": "structural-link-check-only",
        "validator": "html-local-links",
    },
    ".js": {
        "grammar_id": "javascript",
        "identification": "file-extension",
        "validation": "lexical-module-reference-check-available",
        "validator": "javascript-local-imports",
    },
    ".mjs": {
        "grammar_id": "javascript",
        "identification": "file-extension",
        "validation": "lexical-module-reference-check-available",
        "validator": "javascript-local-imports",
    },
    ".css": {
        "grammar_id": "css",
        "identification": "file-extension",
        "validation": "lexical-local-reference-check-available",
        "validator": "css-local-links",
    },
    ".md": {
        "grammar_id": "markdown",
        "identification": "file-extension",
        "validation": "identified-not-parser-validated",
        "validator": None,
    },
    ".txt": {
        "grammar_id": "plain-text",
        "identification": "file-extension",
        "validation": "text-only",
        "validator": None,
    },
}


def describe_path(path: Path) -> dict[str, Any]:
    suffix = path.suffix.casefold()
    profile = GRAMMAR_BY_SUFFIX.get(suffix)
    if profile is None:
        return {
            "grammar_id": "unknown",
            "identification": "no-local-profile",
            "validation": "unclassified",
            "validator": None,
        }
    return dict(profile)


def grammar_inventory(root: Path) -> dict[str, Any]:
    root = Path(root).resolve()
    files: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        profile = describe_path(path)
        grammar_id = str(profile["grammar_id"])
        counts[grammar_id] += 1
        files.append({
            "path": path.relative_to(root).as_posix(),
            **profile,
        })
    return {
        "truth_status": "OBSERVED_EXTENSION_GRAMMAR_INVENTORY",
        "method": "explicit local extension profiles; validation strength is reported per grammar",
        "counts": dict(sorted(counts.items())),
        "files": files,
        "limitations": [
            "extension identification is not semantic proof of file contents",
            "only validators explicitly named above are currently available",
            "this is not the full axm-102-grammer profile corpus",
        ],
    }
