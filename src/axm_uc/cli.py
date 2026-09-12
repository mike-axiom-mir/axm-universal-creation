from __future__ import annotations

import argparse
import json
from pathlib import Path

from .asset_atoms import ATOM_KINDS
from .machine import UniversalCreationMachine
from .paths import find_machine_root
from .snapshot import create_daily_snapshot, restore_snapshot, verify_snapshot


def _print(value) -> None:
    print(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="axm-uc", description="AXM Universal Creation standalone runtime")
    parser.add_argument("--root", help="machine root; normally auto-detected")
    sub = parser.add_subparsers(dest="command", required=True)

    for name, help_text in [('grammar-capsule','compose a standalone Grammar 102 language capability capsule'),
                            ('state-ripple','compare sparse and full evaluation of an explicit state graph'),
                            ('construction-program','compose and evaluate declared state operations'),
                            ('render-budget','select a bounded visual projection without changing source state')]:
        gp = sub.add_parser(name, help=help_text)
        gp.add_argument('request', help='JSON request file; at most 1 MiB')

    pipelines = sub.add_parser('pipelines', help='map installed capability connections without executing them')
    pipelines.add_argument('--goal', help='exact output token or namespace prefix')
    pipelines.add_argument('--max-hops', type=int, default=4)
    pipelines.add_argument('--limit', type=int, default=30)
    pipelines.add_argument('--search-budget', type=int, default=10000)
    workshop = sub.add_parser('survivor-workshop', help='build both detail levels of the authored custom-surface workshop with an offline viewer')
    workshop.add_argument('path')
    rts = sub.add_parser('rts-reference-pack', help='build the 83-design survivor RTS reference collection')
    rts.add_argument('path')
    rts.add_argument('--asset', action='append', default=None, help='select a catalog asset ID; repeat to build a subset')

    polish = sub.add_parser('rts-workshop-polish', help='build and render the reference-led PBR workshop using a supplied offline Blender Python environment')
    polish.add_argument('path')
    polish.add_argument('--python', required=True, help='Python executable with bpy 4.3, numpy <2 and Pillow installed')
    polish.add_argument('--font', required=True, help='local font file for authored workshop signage')
    polish.add_argument('--resolution', type=int, default=1100)
    polish.add_argument('--samples', type=int, default=64)

    timeline = sub.add_parser('sample-track', help='sample a local integer animation track at a frame')
    timeline.add_argument('track_file')
    timeline.add_argument('--frame',type=int,required=True)
    timeline.add_argument('--start',type=int,default=0)
    timeline.add_argument('--end',type=int,default=60)

    metal = sub.add_parser('metal', help='generate painted-metal material maps offline')
    metal.add_argument('path')
    metal.add_argument('--size', type=int, default=128)
    metal.add_argument('--seed', type=int, default=1)
    metal.add_argument('--wear', type=float, default=0.32)
    metal.add_argument('--scratches', type=int, default=18)
    metal.add_argument('--spec', help='JSON PaintedMetalSpec; overrides wear and scratches flags')

    label = sub.add_parser('bitmap-label', help='create a transparent native 5x7 interface label')
    label.add_argument('path')
    label.add_argument('--text', required=True)
    label.add_argument('--scale', type=int, default=4)

    wav = sub.add_parser('normalize-wav', help='convert integer PCM WAV to mono/stereo 16-bit PCM')
    wav.add_argument('source')
    wav.add_argument('path')
    wav.add_argument('--rate', type=int, default=48000)
    wav.add_argument('--channels', type=int, default=1)

    fabric = sub.add_parser('fabric', help='generate standalone woven fabric material maps')
    fabric.add_argument('path')
    fabric.add_argument('--size',type=int,default=256)
    fabric.add_argument('--seed',type=int,default=1)

    formats = sub.add_parser('formats', help='list size/layout presets or create an editable layout project')
    formats.add_argument('--format', dest='format_name')
    formats.add_argument('--layout')
    formats.add_argument('--path')
    formats.add_argument('--title', default='Untitled creation')
    formats.add_argument('--dpi', type=float, default=300)
    formats.add_argument('--bleed', type=float, default=0, help='extra mm on each print edge')
    formats.add_argument('--safe', type=float, default=0, help='inset in format units')
    formats.add_argument('--landscape', action='store_true')

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

    assets_p = sub.add_parser("assets", help="list or inspect installed deterministic Asset Atom packages")
    assets_p.add_argument("--ref", help="inspect one exact installed id@version package")
    assets_p.add_argument("--asset-class", help="filter by one exact asset class")
    assets_p.add_argument("--atom-kind", choices=sorted(ATOM_KINDS), help="require one supported atom kind")

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
    from .organ_materialization import IMPLEMENTATION_COVERAGE_STATES
    organ_census_p.add_argument("--coverage", choices=sorted(IMPLEMENTATION_COVERAGE_STATES),
                                help="filter combined package and live implementation declarations")
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

    snapshot_p = sub.add_parser("snapshot", help="daily snapshot create/verify/restore")
    snapshot_sub = snapshot_p.add_subparsers(dest="snapshot_command", required=True)
    sc = snapshot_sub.add_parser("create")
    sc.add_argument("--output-dir")
    sc.add_argument("--replace", action="store_true")
    sv = snapshot_sub.add_parser("verify")
    sv.add_argument("snapshot")
    sr = snapshot_sub.add_parser("restore")
    sr.add_argument("snapshot")
    sr.add_argument("--confirm", action="store_true", help="required for destructive current-body restore")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = find_machine_root(args.root) if args.root else find_machine_root()
    machine = UniversalCreationMachine(root)
    if args.command == 'rts-workshop-polish':
        from .rts_polish import polish_workshop
        try:
            result = polish_workshop(root, args.path, args.python, args.font, args.resolution, args.samples)
        except (ValueError, OSError, RuntimeError) as error:
            _print({'type': 'RTS_WORKSHOP_POLISH_FAILED', 'reason': str(error)})
            return 1
        _print(result)
        return 0

    if args.command == 'rts-reference-pack':
        from .rts_foundry import reference_pack_request
        result = machine.create(reference_pack_request(args.path, args.asset))
        _print(result)
        return 0 if result.get('type') == 'CREATION_RESULT' else 1

    if args.command == 'survivor-workshop':
        from .workshop_project import workshop_request
        result = machine.create(workshop_request(args.path))
        _print(result)
        return 0 if result.get('type') == 'CREATION_RESULT' else 1

    if args.command in ('grammar-capsule', 'state-ripple', 'render-budget', 'construction-program'):
        from .grammar_workbench import run_grammar_tool
        try:
            with Path(args.request).open('rb') as source:
                data = source.read(1048577)
            if len(data) > 1048576: raise ValueError('request exceeds 1 MiB')
            _print(run_grammar_tool(root, args.command, json.loads(data)))
        except (ValueError, OSError) as exc:
            raise SystemExit(str(exc)) from exc
        return 0

    if args.command == 'pipelines':
        from .pipeline_map import map_capabilities
        try:
            result = map_capabilities(root, args.goal, args.max_hops, args.limit, args.search_budget)
        except (ValueError, OSError) as exc:
            raise SystemExit(str(exc)) from exc
        _print(result)
        return 0

    if args.command in ('metal', 'bitmap-label', 'normalize-wav'):
        from .media_workbench import PaintedMetalSpec, metal_request, label_request, wav_request
        try:
            if args.command == 'metal':
                spec = PaintedMetalSpec(**json.loads(Path(args.spec).read_text())) if args.spec else PaintedMetalSpec(wear=args.wear, scratches=args.scratches)
                request = metal_request(args.path, args.size, args.seed, spec)
            elif args.command == 'bitmap-label':
                request = label_request(args.path, args.text, args.scale)
            else:
                with Path(args.source).open('rb') as source:
                    data = source.read(16*1024*1024+1)
                request = wav_request(args.path, data, args.rate, args.channels)
        except (ValueError, TypeError, OSError) as exc:
            raise SystemExit(str(exc)) from exc
        result = machine.create(request); _print(result)
        return 0 if result.get('type') == 'CREATION_RESULT' else 1

    if args.command == 'sample-track':
        from .timeline_tracks import sample_track
        try:
            track=json.loads(Path(args.track_file).read_text())
            value=sample_track(track,args.frame,args.start,args.end)
        except (ValueError,OSError) as exc:
            raise SystemExit(str(exc)) from exc
        _print({'frame':args.frame,'value':value,'evidence':'integer track sampled; animation rendering not observed'})
        return 0

    if args.command == 'fabric':
        from .fabric_material import fabric_request
        try:
            request=fabric_request(args.path,args.size,args.seed)
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc
        result=machine.create(request); _print(result)
        return 0 if result.get('type')=='CREATION_RESULT' else 1

    if args.command == 'formats':
        from .format_templates import catalog, layout_project
        if not any((args.format_name,args.layout,args.path)):
            _print(catalog()); return 0
        if not all((args.format_name,args.layout,args.path)):
            raise SystemExit('--format, --layout and --path are required together')
        try:
            template=layout_project(args.format_name,args.layout,args.title,dpi=args.dpi,
                                    bleed=args.bleed,safe=args.safe,landscape=args.landscape)
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc
        result=machine.create({'kind':'templated-static-web-project',
            'direction':'create an editable size-aware layout scaffold',
            'inputs':{'path':args.path,'template':template,'variables':{}}})
        _print(result)
        return 0 if result.get('type')=='CREATION_RESULT' else 1

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
    if args.command == "assets":
        _print(machine.asset_packages(
            ref=args.ref,
            asset_class=args.asset_class,
            atom_kind=args.atom_kind,
        ))
        return 0
    if args.command == "organ-census":
        _print(machine.organ_census(
            anatomy_id=args.anatomy_id,
            domain_code=args.domain_code,
            state=args.state,
            coverage=args.coverage,
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
        if args.snapshot_command == "verify":
            _print(verify_snapshot(Path(args.snapshot)))
            return 0
        _print(restore_snapshot(root, Path(args.snapshot), confirm=args.confirm))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
