#!/usr/bin/env python3
"""Smoke test for real DXF + Sparrow end-to-end pipeline."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    fixture = ROOT / "samples" / "dxf_import" / "part_contract_ok.json"
    if not fixture.is_file():
        raise AssertionError(f"missing fixture: {fixture}")

    with tempfile.TemporaryDirectory(prefix="vrs_real_dxf_smoke_") as tmp:
        tmp_dir = Path(tmp)
        run_root = tmp_dir / "runs"
        project_path = tmp_dir / "project_dxf_v1.json"

        project = {
            "version": "dxf_v1",
            "name": "real_dxf_smoke",
            "seed": 0,
            "time_limit_s": 20,
            "units": "mm",
            "spacing_mm": 0.0,
            "margin_mm": 0.0,
            "stocks_dxf": [{"id": "stock_1", "path": str(fixture), "quantity": 1, "allowed_rotations_deg": [0]}],
            "parts_dxf": [{"id": "part_1", "path": str(fixture), "quantity": 1, "allowed_rotations_deg": [0]}],
        }
        _write_json(project_path, project)

        cmd = [
            sys.executable,
            str(ROOT / "scripts" / "run_real_dxf_sparrow_pipeline.py"),
            "--project",
            str(project_path),
            "--run-root",
            str(run_root),
        ]
        proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=False)
        if proc.returncode != 0:
            raise AssertionError(f"pipeline failed rc={proc.returncode}, stderr={proc.stderr}")

        run_dir_str = proc.stdout.strip().splitlines()[-1].strip()
        run_dir = Path(run_dir_str)
        if not run_dir.is_dir():
            raise AssertionError(f"invalid run_dir from stdout: {run_dir_str}")

        required = [
            run_dir / "sparrow_instance.json",
            run_dir / "solver_output.json",
            run_dir / "out" / "sheet_001.dxf",
        ]
        for path in required:
            if not path.is_file():
                raise AssertionError(f"missing expected artifact: {path}")

    print("[OK] real DXF + Sparrow pipeline smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
