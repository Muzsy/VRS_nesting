#!/usr/bin/env python3
"""VRS CLI command dispatch for table-solver and DXF pipelines."""

from __future__ import annotations

import argparse
import sys

from vrs_nesting.pipeline.dxf_pipeline import run_dxf_pipeline
from vrs_nesting.pipeline.run_pipeline import run_table_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="VRS nesting CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run full table-solver pipeline into one run directory")
    run_parser.add_argument("project_json", help="Path to project JSON file")
    run_parser.add_argument("--run-root", default="runs", help="Run artifacts root directory (default: runs)")

    dxf_run_parser = subparsers.add_parser("dxf-run", help="Run real DXF + Sparrow pipeline into one run directory")
    dxf_run_parser.add_argument("project_json", help="Path to dxf_v1 project JSON file")
    dxf_run_parser.add_argument("--run-root", default="runs", help="Run artifacts root directory (default: runs)")
    dxf_run_parser.add_argument("--sparrow-bin", default=None, help="Optional explicit Sparrow binary path")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "run":
        return run_table_pipeline(args.project_json, args.run_root)
    if args.command == "dxf-run":
        return run_dxf_pipeline(args.project_json, args.run_root, args.sparrow_bin)

    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
