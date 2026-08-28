from __future__ import annotations

import argparse
import json
from pathlib import Path

from .integrity import refresh, verify
from .machine import UniversalCreationMachine
from .paths import find_machine_root
from .snapshot import create_daily_snapshot, restore_snapshot


def _print(value) -> None:
    print(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="axm-uc", description="AXM Universal Creation standalone runtime")
    parser.add_argument("--root", help="machine root; normally auto-detected")
    sub = parser.add_subparsers(dest="command", required=True)

    inspect_p = sub.add_parser("inspect", help="inspect the current machine and registry")
    inspect_p.add_argument("--query", default="")
    inspect_p.add_argument("--level", choices=["atom", "component", "organ"])
    inspect_p.add_argument("--limit", type=int, default=20)
    inspect_p.add_argument("--integrity", action="store_true")

    create_p = sub.add_parser("create", help="route one creation request")
    create_p.add_argument("request", help="JSON request file")

    candidate_p = sub.add_parser("candidate", help="test or adopt a candidate capability")
    candidate_sub = candidate_p.add_subparsers(dest="candidate_command", required=True)
    for name in ("test", "adopt"):
        cp = candidate_sub.add_parser(name)
        cp.add_argument("manifest")

    integrity_p = sub.add_parser("integrity", help="internal body integrity")
    integrity_p.add_argument("action", choices=["verify", "refresh"])

    snapshot_p = sub.add_parser("snapshot", help="daily snapshot export/restore")
    snapshot_sub = snapshot_p.add_subparsers(dest="snapshot_command", required=True)
    sc = snapshot_sub.add_parser("create")
    sc.add_argument("--output-dir")
    sc.add_argument("--replace", action="store_true")
    sr = snapshot_sub.add_parser("restore")
    sr.add_argument("snapshot")
    sr.add_argument("--confirm", action="store_true", help="required for destructive current-body restore")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = find_machine_root(args.root) if args.root else find_machine_root()
    machine = UniversalCreationMachine(root)

    if args.command == "inspect":
        result = machine.inspect(args.query, args.level, args.limit)
        if args.integrity:
            result["integrity"] = verify(root)
        _print(result)
        return 0
    if args.command == "create":
        request = json.loads(Path(args.request).read_text(encoding="utf-8"))
        _print(machine.create(request))
        return 0
    if args.command == "candidate":
        manifest = Path(args.manifest)
        result = machine.test_candidate(manifest) if args.candidate_command == "test" else machine.adopt_candidate(manifest)
        _print(result)
        return 0 if result.get("passed", result.get("adopted", False)) else 2
    if args.command == "integrity":
        _print(refresh(root) if args.action == "refresh" else verify(root))
        return 0
    if args.command == "snapshot":
        if args.snapshot_command == "create":
            _print(create_daily_snapshot(root, Path(args.output_dir) if args.output_dir else None, args.replace))
            return 0
        _print(restore_snapshot(root, Path(args.snapshot), confirm=args.confirm))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
