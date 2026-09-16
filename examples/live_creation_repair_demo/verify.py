from pathlib import Path

status = Path("status.txt").read_text(encoding="utf-8").strip()
raise SystemExit(0 if status == "ready" else 3)
