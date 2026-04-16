#!/usr/bin/env python3
"""Smoke tests for multi-sheet wrapper edge-cases and deterministic output."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from vrs_nesting.sparrow.multi_sheet_wrapper import run_multi_sheet_wrapper


def _resolve_sparrow_bin() -> str:
    explicit = os.environ.get("SPARROW_BIN", "").strip()
    if explicit and Path(explicit).is_file():
        return explicit

    candidate = ROOT / ".cache" / "sparrow" / "target" / "release" / "sparrow"
    if candidate.is_file():
        return str(candidate)

    found = subprocess.run(["which", "sparrow"], capture_output=True, text=True, check=False)
    if found.returncode == 0 and found.stdout.strip():
        return found.stdout.strip()

    raise AssertionError("Sparrow binary not found. Set SPARROW_BIN or run ./scripts/check.sh first.")


def _build_payloads() -> tuple[dict, dict]:
    solver_input = {
        "contract_version": "v1",
        "project_name": "multisheet_edge_smoke",
        "seed": 0,
        "time_limit_s": 4,
        "stocks": [
            {"id": "sheet_1", "width": 100.0, "height": 100.0, "quantity": 2},
        ],
        "parts": [
            {"id": "fit_part", "source_dxf_path": "/tmp/fake_fit.dxf", "source_layers": {"outer": "CUT_OUTER", "inner": "CUT_INNER"}},
            {"id": "huge_part", "source_dxf_path": "/tmp/fake_huge.dxf", "source_layers": {"outer": "CUT_OUTER", "inner": "CUT_INNER"}},
            {"id": "bad_part", "source_dxf_path": "/tmp/fake_bad.dxf", "source_layers": {"outer": "CUT_OUTER", "inner": "CUT_INNER"}},
        ],
    }

    sparrow_instance = {
        "name": "multisheet_edge_smoke",
        "strip_height": 101.0,
        "items": [
            {
                "id": 0,
                "demand": 1,
                "dxf": "fit_part.dxf",
                "instance_id": "fit_part__0001",
                "part_id": "fit_part",
                "allowed_orientations": [0.0],
                "shape": {"type": "simple_polygon", "data": [[0.0, 0.0], [20.0, 0.0], [20.0, 20.0], [0.0, 20.0], [0.0, 0.0]]},
            },
            {
                "id": 1,
                "demand": 1,
                "dxf": "huge_part.dxf",
                "instance_id": "huge_part__0001",
                "part_id": "huge_part",
                "allowed_orientations": [0.0, 90.0],
                "shape": {"type": "simple_polygon", "data": [[0.0, 0.0], [200.0, 0.0], [200.0, 200.0], [0.0, 200.0], [0.0, 0.0]]},
            },
            {
                "id": 2,
                "demand": 1,
                "dxf": "bad_part.dxf",
                "instance_id": "bad_part__0001",
                "part_id": "bad_part",
                "allowed_orientations": [0.0],
                "shape": {"type": "simple_polygon", "data": [[0.0, 0.0], [1.0, 1.0]]},
            },
        ],
    }
    return sparrow_instance, solver_input


def _run_once(run_dir: Path, *, sparrow_bin: str) -> tuple[dict, list[dict]]:
    sparrow_instance, solver_input = _build_payloads()
    run_dir.mkdir(parents=True, exist_ok=True)

    output = run_multi_sheet_wrapper(
        run_dir=run_dir,
        sparrow_instance=sparrow_instance,
        solver_input=solver_input,
        seed=0,
        time_limit_s=4,
        sparrow_bin=sparrow_bin,
    )

    raw_outputs = json.loads((run_dir / "sparrow_output.json").read_text(encoding="utf-8"))
    if not isinstance(raw_outputs, list):
        raise AssertionError("sparrow_output.json must contain list")
    return output, raw_outputs


def _determinism_signature(output: dict) -> dict:
    placements_raw = output.get("placements", [])
    unplaced_raw = output.get("unplaced", [])
    if not isinstance(placements_raw, list) or not isinstance(unplaced_raw, list):
        raise AssertionError("output placements/unplaced must be lists")

    placements = sorted(
        (
            str(item.get("instance_id", "")),
            str(item.get("part_id", "")),
            int(item.get("sheet_index", -1)),
            int(round(float(item.get("rotation_deg", 0.0)))) % 360,
        )
        for item in placements_raw
        if isinstance(item, dict)
    )
    unplaced = sorted(
        (
            str(item.get("instance_id", "")),
            str(item.get("part_id", "")),
            str(item.get("reason", "")),
        )
        for item in unplaced_raw
        if isinstance(item, dict)
    )
    return {
        "status": str(output.get("status", "")),
        "placements": placements,
        "unplaced": unplaced,
    }


def main() -> int:
    sparrow_bin = _resolve_sparrow_bin()

    with tempfile.TemporaryDirectory(prefix="vrs_wrapper_edge_smoke_") as tmp:
        tmp_root = Path(tmp)
        output_a, raw_a = _run_once(tmp_root / "run_a", sparrow_bin=sparrow_bin)
        output_b, raw_b = _run_once(tmp_root / "run_b", sparrow_bin=sparrow_bin)

        if output_a.get("status") != "partial":
            raise AssertionError(f"expected partial status, got: {output_a.get('status')!r}")

        reasons = {str(item.get("reason", "")) for item in output_a.get("unplaced", []) if isinstance(item, dict)}
        if "invalid_geometry" not in reasons:
            raise AssertionError(f"missing invalid_geometry reason in unplaced: {sorted(reasons)}")
        if "too_large" not in reasons:
            raise AssertionError(f"missing too_large reason in unplaced: {sorted(reasons)}")

        global_limit = 4
        for idx, entry in enumerate(raw_a):
            if not isinstance(entry, dict):
                raise AssertionError(f"raw output entry must be object at index {idx}")
            runner_meta = entry.get("runner_meta")
            if not isinstance(runner_meta, dict):
                raise AssertionError(f"runner_meta missing at index {idx}")
            budget = runner_meta.get("time_limit_s")
            if not isinstance(budget, int):
                raise AssertionError(f"runner_meta.time_limit_s must be int at index {idx}, got {budget!r}")
            if budget <= 0:
                raise AssertionError(f"runner_meta.time_limit_s must be >0 at index {idx}, got {budget!r}")
            if budget > global_limit:
                raise AssertionError(f"runner_meta.time_limit_s exceeds global limit at index {idx}: {budget} > {global_limit}")

        sig_a = _determinism_signature(output_a)
        sig_b = _determinism_signature(output_b)
        if sig_a != sig_b:
            raise AssertionError(
                f"determinism failure: semantic output differs between runs with same seed: {sig_a!r} vs {sig_b!r}"
            )

        # raw run metadata can differ (timestamps/paths), but budget vectors must be deterministic
        budgets_a = [int(entry.get("runner_meta", {}).get("time_limit_s", -1)) for entry in raw_a if isinstance(entry, dict)]
        budgets_b = [int(entry.get("runner_meta", {}).get("time_limit_s", -1)) for entry in raw_b if isinstance(entry, dict)]
        if budgets_a != budgets_b:
            raise AssertionError(f"determinism failure: budget vectors differ: {budgets_a} vs {budgets_b}")

    print("[OK] multisheet wrapper edge-cases smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
