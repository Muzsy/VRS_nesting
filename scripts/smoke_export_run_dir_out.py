#!/usr/bin/env python3
"""Smoke test for exporter --run-dir integration and run_dir/out artifacts."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from vrs_nesting.run_artifacts.run_dir import create_run_dir


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="vrs_export_run_dir_") as tmp:
        run_root = Path(tmp) / "runs"
        ctx = create_run_dir(run_root=str(run_root))

        if not ctx.out_dir.is_dir():
            raise AssertionError(f"missing out_dir from run context: {ctx.out_dir}")

        solver_input = {
            "contract_version": "v1",
            "project_name": "export_run_dir_smoke",
            "seed": 0,
            "time_limit_s": 60,
            "stocks": [{"id": "sheet_1", "width": 1000, "height": 2000, "quantity": 1}],
            "parts": [{"id": "part_a", "width": 100, "height": 200, "quantity": 1, "allowed_rotations_deg": [0]}],
        }
        solver_output = {
            "contract_version": "v1",
            "placements": [{"instance_id": "part_a__0001", "part_id": "part_a", "sheet_index": 0, "x": 10, "y": 20, "rotation_deg": 0}],
            "unplaced": [],
        }

        _write_json(ctx.run_dir / "solver_input.json", solver_input)
        _write_json(ctx.run_dir / "solver_output.json", solver_output)

        cmd = [sys.executable, str(ROOT / "vrs_nesting" / "dxf" / "exporter.py"), "--run-dir", str(ctx.run_dir)]
        proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=False)
        if proc.returncode != 0:
            raise AssertionError(f"exporter failed rc={proc.returncode}, stderr={proc.stderr}")

        dxf_path = ctx.out_dir / "sheet_001.dxf"
        if not dxf_path.is_file():
            raise AssertionError(f"missing exported dxf: {dxf_path}")
        if dxf_path.stat().st_size <= 0:
            raise AssertionError(f"empty exported dxf: {dxf_path}")

    print("[OK] exporter --run-dir smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
