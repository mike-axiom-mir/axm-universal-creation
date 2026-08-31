from __future__ import annotations

import argparse
import json
from pathlib import Path

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

    topology_p = sub.add_parser("topology", help="inspect the master-to-kernel crosswalk and declared kernel dependencies")
    topology_p.add_argument("--master-id", help="master atom/component/organ id to map into the kernel")
    topology_p.add_argument("--core-id", help="core-kernel id to traverse directly")
    topology_p.add_argument("--depth", type=int, default=6, help="maximum dependency traversal depth")

    executable_p = sub.add_parser("executable", help="inspect which anatomy is explicitly backed by live capabilities")
    executable_p.add_argument("--master-id", help="master anatomy id to inspect for live implementation bindings")
    executable_p.add_argument("--core-id", help="core-kernel id to inspect through exact master crosswalks")

    directions_p = sub.add_parser("directions", help="inspect or deterministically suggest software direction profiles")
    directions_p.add_argument("--id", dest="direction_id", help="inspect one explicit software direction profile")
    directions_p.add_argument("--suggest", help="rank direction candidates for caller-supplied text; never auto-selects")

    organs_p = sub.add_parser("organs", help="list or inspect installed executable software-organ packages")
    organ_action = organs_p.add_mutually_exclusive_group()
    organ_action.add_argument("--ref", help="inspect one exact installed id@version package including source")
    organ_action.add_argument("--test-ref", help="run one installed package's declared deterministic fixtures")
    organs_p.add_argument("--project-type", choices=["generic", "static-web", "python"], help="filter installed packages")
    organs_p.add_argument("--provides", help="filter by one exact provided interface")

    organ_census_p = sub.add_parser(
        "organ-census",
        help="inspect all descriptive organs against installed executable packages and exact interface coverage",
    )
    organ_census_p.add_argument("--id", dest="anatomy_id", help="inspect one exact descriptive organ ID")
    organ_census_p.add_argument("--domain", dest="domain_code", help="filter by one exact domain code")
    organ_census_p.add_argument(
        "--state",
        choices=[
            "CONNECTED_EXECUTABLE_PACKAGE",
            "EXECUTABLE_PACKAGE_WITH_MISSING_INTERFACES",
            "IMPLEMENTATION_REQUIRED",
        ],
        help="filter by observed materialization state",
    )
    organ_census_p.add_argument("--offset", type=int, default=0)
    organ_census_p.add_argument("--limit", type=int, default=415)

    sub.add_parser("forge", help="inspect the detached creation-unit spawning surface and truth boundary")
    sub.add_parser("gap-forge", help="inspect the bounded gap-to-proposal synthesis surface and truth boundary")

    plan_p = sub.add_parser("plan", help="decompose a creation request against direction, anatomy, topology, and live coverage")
    plan_p.add_argument("request", help="JSON request file")
    plan_p.add_argument("--per-level", type=int, default=6, help="maximum matches returned per anatomy level")

    create_p = sub.add_parser("create", help="route one creation request")
    create_p.add_argument("request", help="JSON request file")

    trial_p = sub.add_parser("trial", help="plan, create, and independently verify a project creation")
    trial_p.add_argument("request", help="JSON project creation request file")
    trial_p.add_argument("--per-level", type=int, default=6, help="maximum matches returned per anatomy level")

    candidate_p = sub.add_parser("candidate", help="test or adopt a candidate capability")
    candidate_sub = candidate_p.add_subparsers(dest="candidate_command", required=True)
    for name in ("test", "adopt"):
        cp = candidate_sub.add_parser(name)
        cp.add_argument("manifest")

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
        _print(machine.inspect(args.query, args.level, args.limit))
        return 0
    if args.command == "topology":
        _print(machine.topology(master_id=args.master_id, core_id=args.core_id, depth=args.depth))
        return 0
    if args.command == "executable":
        _print(machine.executable(master_id=args.master_id, core_id=args.core_id))
        return 0
    if args.command == "directions":
        _print(machine.software_directions(direction_id=args.direction_id, suggest=args.suggest))
        return 0
    if args.command == "organs":
        _print(machine.executable_organs(
            ref=args.ref,
            test_ref=args.test_ref,
            project_type=args.project_type,
            provides=args.provides,
        ))
        return 0
    if args.command == "organ-census":
        _print(machine.organ_census(
            anatomy_id=args.anatomy_id,
            domain_code=args.domain_code,
            state=args.state,
            offset=args.offset,
            limit=args.limit,
        ))
        return 0
    if args.command == "forge":
        _print(machine.creation_forge())
        return 0
    if args.command == "gap-forge":
        _print(machine.gap_forge())
        return 0
    if args.command == "plan":
        request = json.loads(Path(args.request).read_text(encoding="utf-8"))
        _print(machine.plan(request, per_level=args.per_level))
        return 0
    if args.command == "create":
        request = json.loads(Path(args.request).read_text(encoding="utf-8"))
        _print(machine.create(request))
        return 0
    if args.command == "trial":
        request = json.loads(Path(args.request).read_text(encoding="utf-8"))
        result = machine.trial(request, per_level=args.per_level)
        _print(result)
        return 0 if result.get("passed") is True else 2
    if args.command == "candidate":
        manifest = Path(args.manifest)
        result = machine.test_candidate(manifest) if args.candidate_command == "test" else machine.adopt_candidate(manifest)
        _print(result)
        return 0 if result.get("passed", result.get("adopted", False)) else 2
    if args.command == "snapshot":
        if args.snapshot_command == "create":
            _print(create_daily_snapshot(root, Path(args.output_dir) if args.output_dir else None, args.replace))
            return 0
        _print(restore_snapshot(root, Path(args.snapshot), confirm=args.confirm))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
