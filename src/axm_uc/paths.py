from __future__ import annotations

from pathlib import Path


def find_machine_root(start: str | Path | None = None) -> Path:
    current = Path(start or Path.cwd()).resolve()
    if current.is_file():
        current = current.parent
    for candidate in (current, *current.parents):
        if (candidate / "machine.contract.json").is_file():
            return candidate
    raise FileNotFoundError("Could not find machine.contract.json in this path or its parents")
