from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def clean() -> None:
    shutil.rmtree(ROOT / ".axm-build", ignore_errors=True)
    shutil.rmtree(ROOT / ".pytest_cache", ignore_errors=True)
    for path in sorted(ROOT.rglob("__pycache__"), reverse=True):
        shutil.rmtree(path, ignore_errors=True)
    for path in ROOT.rglob("*.pyc"):
        path.unlink(missing_ok=True)


if __name__ == "__main__":
    clean()
