from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def cleanup() -> None:
    subprocess.run([sys.executable, str(ROOT / "tools/clean.py")], cwd=ROOT, check=False)


def main() -> int:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    try:
        run = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
            cwd=ROOT,
            env=env,
        )
        if run.returncode != 0:
            return run.returncode
        cleanup()
        if (ROOT / ".axm-build").exists():
            print("BUILD_INCOMPLETE: build debris remains", file=sys.stderr)
            return 4
        print("BUILD_OK")
        return 0
    finally:
        cleanup()


if __name__ == "__main__":
    raise SystemExit(main())
