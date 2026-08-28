from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from axm_uc.integrity import refresh, verify


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
        manifest = refresh(ROOT)
        check = verify(ROOT)
        if check["status"] != "clean":
            print("BUILD_INCOMPLETE: integrity baseline does not match current body", file=sys.stderr)
            return 3
        if (ROOT / ".axm-build").exists():
            print("BUILD_INCOMPLETE: build debris remains", file=sys.stderr)
            return 4
        print(f"BUILD_OK body_sha256={manifest['body_sha256']}")
        return 0
    finally:
        cleanup()


if __name__ == "__main__":
    raise SystemExit(main())
