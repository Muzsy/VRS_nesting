#!/usr/bin/env python3
"""Smoke-check documented command entrypoints."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "how_to_run.md"


def _run_help(cmd: list[str]) -> None:
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise AssertionError(f"help command failed rc={proc.returncode}: {' '.join(cmd)}\nstderr={proc.stderr}")
    if not proc.stdout.strip() and not proc.stderr.strip():
        raise AssertionError(f"help command produced no output: {' '.join(cmd)}")


def main() -> int:
    if not DOC.is_file():
        raise AssertionError(f"missing documentation file: {DOC}")

    text = DOC.read_text(encoding="utf-8")
    required_snippets = [
        "python3 -m vrs_nesting.cli run",
        "python3 -m vrs_nesting.cli dxf-run",
        "python3 scripts/run_real_dxf_sparrow_pipeline.py",
        "./scripts/check.sh",
    ]
    for snippet in required_snippets:
        if snippet not in text:
            raise AssertionError(f"missing command snippet in docs/how_to_run.md: {snippet}")

    _run_help([sys.executable, "-m", "vrs_nesting.cli", "--help"])
    _run_help([sys.executable, "-m", "vrs_nesting.cli", "run", "--help"])
    _run_help([sys.executable, "-m", "vrs_nesting.cli", "dxf-run", "--help"])
    _run_help([sys.executable, str(ROOT / "scripts" / "run_real_dxf_sparrow_pipeline.py"), "--help"])

    print("[OK] docs command smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

