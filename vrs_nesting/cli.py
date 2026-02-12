#!/usr/bin/env python3
"""Minimal VRS CLI bootstrap with strict project validation and run snapshot."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from vrs_nesting.project.model import ProjectValidationError, load_project_json
from vrs_nesting.run_artifacts.run_dir import append_run_log, create_run_dir, write_project_snapshot


def _eprint(msg: str) -> None:
    print(msg, file=sys.stderr)


def _cmd_run(project_path: str, run_root: str) -> int:
    try:
        project = load_project_json(project_path)
    except ProjectValidationError as exc:
        _eprint(f"ERROR: {exc.code}: {exc.message}")
        return 2

    try:
        ctx = create_run_dir(run_root=run_root)
        append_run_log(ctx.run_log_path, "RUN_START", f"project={Path(project_path).resolve()}")

        normalized = project.to_dict()
        snapshot_path = write_project_snapshot(ctx.run_dir, normalized)
        append_run_log(ctx.run_log_path, "PROJECT_VALIDATED", f"snapshot={snapshot_path}")
        append_run_log(ctx.run_log_path, "RUN_READY", f"seed={project.seed} time_limit_s={project.time_limit_s}")
    except Exception as exc:  # noqa: BLE001
        _eprint(f"ERROR: E_RUN_IO: {exc}")
        return 2

    print(str(ctx.run_dir))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="VRS nesting CLI bootstrap")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Validate project and create run artifact snapshot")
    run_parser.add_argument("project_json", help="Path to project JSON file")
    run_parser.add_argument("--run-root", default="runs", help="Run artifacts root directory (default: runs)")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "run":
        return _cmd_run(args.project_json, args.run_root)

    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
