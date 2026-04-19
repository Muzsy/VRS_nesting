#!/usr/bin/env python3
"""End-to-end smoke gate for nesting_engine SA CLI path."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_VERSION = "nesting_engine_v2"
QUALITY_MAX_SHEETS_USED = 1


def _run_once(bin_path: Path, fixture_payload: bytes, run_index: int) -> dict[str, Any]:
    cmd = [str(bin_path), "nest", "--search", "sa"]
    proc = subprocess.run(
        cmd,
        cwd=ROOT,
        input=fixture_payload,
        capture_output=True,
        check=False,
    )

    if proc.returncode != 0:
        stderr_text = proc.stderr.decode("utf-8", errors="replace").strip()
        raise AssertionError(
            f"SA CLI run {run_index} failed (rc={proc.returncode}). "
            f"Fix command/input: {' '.join(cmd)}\n"
            f"stderr:\n{stderr_text}"
        )

    stdout_text = proc.stdout.decode("utf-8", errors="replace")
    try:
        payload = json.loads(stdout_text)
    except json.JSONDecodeError as exc:
        snippet = stdout_text.strip()[:240]
        raise AssertionError(
            f"SA CLI run {run_index} produced non-JSON stdout. "
            f"Check command output and fixture compatibility.\n"
            f"stdout snippet: {snippet!r}"
        ) from exc

    if not isinstance(payload, dict):
        raise AssertionError(
            f"SA CLI run {run_index} returned JSON but not an object. "
            "Expected top-level object output contract."
        )

    version = str(payload.get("version", "")).strip()
    if version != EXPECTED_VERSION:
        raise AssertionError(
            f"SA CLI run {run_index} returned version={version!r}, "
            f"expected {EXPECTED_VERSION!r}."
        )

    meta = payload.get("meta")
    if not isinstance(meta, dict):
        raise AssertionError(
            f"SA CLI run {run_index} missing object meta field. "
            "Expected meta.determinism_hash."
        )

    determinism_hash = str(meta.get("determinism_hash", "")).strip()
    if not determinism_hash:
        raise AssertionError(
            f"SA CLI run {run_index} missing non-empty meta.determinism_hash. "
            "Check hashing path in output builder."
        )

    sheets_used = payload.get("sheets_used")
    if isinstance(sheets_used, bool) or not isinstance(sheets_used, int):
        raise AssertionError(
            f"SA CLI run {run_index} has invalid sheets_used={sheets_used!r}. "
            "Expected integer sheets_used field."
        )

    if sheets_used > QUALITY_MAX_SHEETS_USED:
        raise AssertionError(
            f"SA CLI run {run_index} quality threshold failed: "
            f"sheets_used={sheets_used} > {QUALITY_MAX_SHEETS_USED}."
        )

    return {
        "determinism_hash": determinism_hash,
        "sheets_used": sheets_used,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Smoke gate for `nesting_engine nest --search sa`."
    )
    parser.add_argument("--bin", required=True, help="Path to nesting_engine binary")
    parser.add_argument("--input", required=True, help="Path to SA quality fixture JSON")
    parser.add_argument(
        "--runs",
        type=int,
        default=3,
        help="Repeated run count for determinism check (minimum: 2)",
    )
    args = parser.parse_args(argv)

    if args.runs < 2:
        raise AssertionError("--runs must be >= 2 for determinism smoke.")

    bin_path = Path(args.bin)
    input_path = Path(args.input)

    if not bin_path.is_file() or not os.access(bin_path, os.X_OK):
        raise AssertionError(
            f"nesting_engine binary is missing or not executable: {bin_path}"
        )
    if not input_path.is_file():
        raise AssertionError(f"fixture JSON file is missing: {input_path}")

    fixture_payload = input_path.read_bytes()
    runs: list[dict[str, Any]] = []
    for idx in range(1, args.runs + 1):
        runs.append(_run_once(bin_path, fixture_payload, idx))

    hashes = [str(item["determinism_hash"]) for item in runs]
    if len(set(hashes)) != 1:
        raise AssertionError(
            "SA CLI determinism mismatch across repeated runs. "
            f"Expected one stable hash, got: {hashes}"
        )

    sheets_used_values = [int(item["sheets_used"]) for item in runs]
    print(
        "[OK] SA CLI smoke passed: "
        f"runs={args.runs}, determinism_hash={hashes[0]}, "
        f"sheets_used={sheets_used_values[0]}"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
