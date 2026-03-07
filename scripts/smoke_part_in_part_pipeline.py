#!/usr/bin/env python3
"""Smoke gate for BLF part-in-part off|auto behavior."""

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


def _run_once(bin_path: Path, fixture_payload: bytes, mode: str, run_index: int) -> dict[str, Any]:
    cmd = [str(bin_path), "nest", "--placer", "blf", "--part-in-part", mode]
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
            f"part-in-part smoke run failed (mode={mode}, run={run_index}, rc={proc.returncode})\n"
            f"cmd={' '.join(cmd)}\n"
            f"stderr:\n{stderr_text}"
        )

    stdout_text = proc.stdout.decode("utf-8", errors="replace")
    try:
        payload = json.loads(stdout_text)
    except json.JSONDecodeError as exc:
        snippet = stdout_text.strip()[:300]
        raise AssertionError(
            f"part-in-part smoke produced non-JSON stdout (mode={mode}, run={run_index}): {snippet!r}"
        ) from exc

    if not isinstance(payload, dict):
        raise AssertionError(f"unexpected non-object JSON output (mode={mode}, run={run_index})")

    version = str(payload.get("version", "")).strip()
    if version != EXPECTED_VERSION:
        raise AssertionError(
            f"unexpected output version (mode={mode}, run={run_index}): {version!r}"
        )

    meta = payload.get("meta")
    if not isinstance(meta, dict):
        raise AssertionError(f"missing object meta field (mode={mode}, run={run_index})")

    determinism_hash = str(meta.get("determinism_hash", "")).strip()
    if not determinism_hash:
        raise AssertionError(
            f"missing meta.determinism_hash (mode={mode}, run={run_index})"
        )

    sheets_used = payload.get("sheets_used")
    if isinstance(sheets_used, bool) or not isinstance(sheets_used, int):
        raise AssertionError(
            f"invalid sheets_used value (mode={mode}, run={run_index}): {sheets_used!r}"
        )

    return {
        "sheets_used": sheets_used,
        "determinism_hash": determinism_hash,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Smoke gate for part-in-part cavity-aware BLF pipeline"
    )
    parser.add_argument("--bin", required=True, help="Path to nesting_engine binary")
    parser.add_argument("--input", required=True, help="Path to F3-2 fixture JSON")
    parser.add_argument(
        "--auto-runs",
        type=int,
        default=3,
        help="Repeated run count for auto-mode determinism check (minimum: 2)",
    )
    args = parser.parse_args(argv)

    if args.auto_runs < 2:
        raise AssertionError("--auto-runs must be >= 2")

    bin_path = Path(args.bin)
    input_path = Path(args.input)

    if not bin_path.is_file() or not os.access(bin_path, os.X_OK):
        raise AssertionError(f"nesting_engine binary is missing or not executable: {bin_path}")
    if not input_path.is_file():
        raise AssertionError(f"fixture JSON file is missing: {input_path}")

    fixture_payload = input_path.read_bytes()

    baseline = _run_once(bin_path, fixture_payload, "off", 1)
    if baseline["sheets_used"] != 2:
        raise AssertionError(
            "baseline expectation failed: "
            f"expected sheets_used=2, got {baseline['sheets_used']}"
        )

    auto_runs: list[dict[str, Any]] = []
    for idx in range(1, args.auto_runs + 1):
        auto_runs.append(_run_once(bin_path, fixture_payload, "auto", idx))

    if auto_runs[0]["sheets_used"] != 1:
        raise AssertionError(
            "auto expectation failed: "
            f"expected sheets_used=1, got {auto_runs[0]['sheets_used']}"
        )

    auto_hashes = [str(item["determinism_hash"]) for item in auto_runs]
    if len(set(auto_hashes)) != 1:
        raise AssertionError(
            f"auto-mode determinism_hash mismatch across runs: {auto_hashes}"
        )

    print(
        "[OK] part-in-part smoke passed: "
        f"baseline_sheets={baseline['sheets_used']}, "
        f"auto_sheets={auto_runs[0]['sheets_used']}, "
        f"auto_hash={auto_hashes[0]}"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
