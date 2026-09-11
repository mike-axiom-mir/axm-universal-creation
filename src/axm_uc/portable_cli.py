from __future__ import annotations

import argparse
import json
from pathlib import Path

from .paths import find_machine_root
from .portable import PortableRuntimeError, build_portable_runtime, verify_portable_runtime


def _print(value: object) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="axm-uc-portable",
        description="Build or verify a sealed portable AXM Universal Creation runtime.",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build", help="build and independently verify a runtime ZIP")
    build.add_argument("--root", help="machine root; normally auto-detected")
    build.add_argument("--output", required=True, help="destination ZIP path")
    build.add_argument("--source-revision", help="explicit source revision for exported lineage")
    verify = sub.add_parser("verify", help="verify inventory, hashes, paths, lineage, and entrypoint")
    verify.add_argument("archive", help="portable runtime ZIP")
    verify.add_argument("--expected-sha256", help="optional caller-pinned archive SHA-256")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "build":
            root = find_machine_root(args.root) if args.root else find_machine_root()
            result = build_portable_runtime(
                root,
                Path(args.output),
                source_revision=args.source_revision,
            )
        else:
            result = verify_portable_runtime(
                Path(args.archive), expected_sha256=args.expected_sha256
            )
    except (OSError, PortableRuntimeError) as exc:
        _print(
            {
                "schema": "axm.universal-creation.portable-runtime-receipt/v0.1",
                "status": "HOLD",
                "error": str(exc),
            }
        )
        return 2
    _print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
