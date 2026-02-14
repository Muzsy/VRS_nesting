#!/usr/bin/env python3
"""Smoke test for real DXF + Sparrow end-to-end pipeline."""

from __future__ import annotations

import json
import importlib.util
import os
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _require_ezdxf() -> None:
    if importlib.util.find_spec("ezdxf") is None:
        raise AssertionError(
            "ezdxf dependency missing for real DXF smoke. "
            "Install with: python3 -m pip install --break-system-packages ezdxf"
        )


def main() -> int:
    _require_ezdxf()

    stock_fixture = ROOT / "samples" / "dxf_demo" / "stock_rect_1000x2000.dxf"
    part_fixture = ROOT / "samples" / "dxf_demo" / "part_arc_spline_chaining_ok.dxf"
    if not stock_fixture.is_file():
        raise AssertionError(f"missing fixture: {stock_fixture}")
    if not part_fixture.is_file():
        raise AssertionError(f"missing fixture: {part_fixture}")

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
            "stocks_dxf": [{"id": "stock_1", "path": str(stock_fixture), "quantity": 1, "allowed_rotations_deg": [0]}],
            "parts_dxf": [{"id": "part_1", "path": str(part_fixture), "quantity": 1, "allowed_rotations_deg": [0]}],
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
        sparrow_bin = os.environ.get("SPARROW_BIN", "").strip()
        if not sparrow_bin:
            candidate = ROOT / ".cache" / "sparrow" / "target" / "release" / "sparrow"
            if candidate.is_file():
                sparrow_bin = str(candidate)
        if sparrow_bin:
            cmd.extend(["--sparrow-bin", sparrow_bin])
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
