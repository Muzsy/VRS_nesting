#!/usr/bin/env python3
"""Entry script for real DXF + Sparrow pipeline."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from vrs_nesting.cli import main as cli_main


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run real DXF + Sparrow pipeline")
    parser.add_argument("--project", required=True, help="Path to dxf_v1 project JSON")
    parser.add_argument("--run-root", default="runs", help="Run artifacts root directory (default: runs)")
    parser.add_argument("--sparrow-bin", default=None, help="Optional explicit Sparrow binary path")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    cmd = ["dxf-run", args.project, "--run-root", args.run_root]
    if args.sparrow_bin:
        cmd.extend(["--sparrow-bin", args.sparrow_bin])
    return cli_main(cmd)


if __name__ == "__main__":
    sys.exit(main())
