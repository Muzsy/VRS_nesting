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


def _assert_under_root(path: Path, root: Path, *, label: str) -> None:
    resolved_path = path.resolve()
    resolved_root = root.resolve()
    if resolved_path == resolved_root:
        return
    if resolved_root not in resolved_path.parents:
        raise AssertionError(f"{label} is outside expected root: path={resolved_path} root={resolved_root}")


def _require_keys(payload: dict, required: list[str], *, where: str) -> None:
    for key in required:
        if key not in payload:
            raise AssertionError(f"missing key {where}.{key}")


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

        stdout_lines = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
        if len(stdout_lines) != 1:
            raise AssertionError(f"stdout contract violation: expected 1 non-empty line, got {len(stdout_lines)} lines: {stdout_lines!r}")

        run_dir_str = stdout_lines[0]
        run_dir = Path(run_dir_str).resolve()
        if not run_dir.is_dir():
            raise AssertionError(f"invalid run_dir from stdout: {run_dir_str}")
        _assert_under_root(run_dir, run_root, label="run_dir")

        required = [
            run_dir / "project.json",
            run_dir / "run.log",
            run_dir / "report.json",
            run_dir / "sparrow_instance.json",
            run_dir / "solver_input.json",
            run_dir / "sparrow_input_meta.json",
            run_dir / "sparrow_output.json",
            run_dir / "solver_output.json",
            run_dir / "source_geometry_map.json",
            run_dir / "sparrow_stdout.log",
            run_dir / "sparrow_stderr.log",
            run_dir / "out" / "sheet_001.dxf",
        ]
        for path in required:
            if not path.is_file():
                raise AssertionError(f"missing expected artifact: {path}")
        if (run_dir / "out" / "sheet_001.dxf").stat().st_size <= 0:
            raise AssertionError(f"empty expected artifact: {run_dir / 'out' / 'sheet_001.dxf'}")

        report_path = run_dir / "report.json"
        try:
            report_payload = json.loads(report_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise AssertionError(f"invalid report.json: line={exc.lineno} col={exc.colno}") from exc
        if not isinstance(report_payload, dict):
            raise AssertionError("report.json top-level must be object")

        _require_keys(
            report_payload,
            [
                "contract_version",
                "project_name",
                "seed",
                "time_limit_s",
                "run_dir",
                "status",
                "paths",
                "metrics",
                "export_summary",
            ],
            where="report",
        )
        if str(report_payload.get("contract_version")) != "dxf_v1":
            raise AssertionError(f"unexpected report.contract_version: {report_payload.get('contract_version')!r}")

        paths_payload = report_payload.get("paths")
        if not isinstance(paths_payload, dict):
            raise AssertionError("report.paths must be object")
        _require_keys(
            paths_payload,
            [
                "project_json",
                "sparrow_instance_json",
                "solver_input_json",
                "sparrow_input_meta_json",
                "sparrow_output_json",
                "solver_output_json",
                "out_dir",
            ],
            where="report.paths",
        )

        metrics_payload = report_payload.get("metrics")
        if not isinstance(metrics_payload, dict):
            raise AssertionError("report.metrics must be object")
        _require_keys(metrics_payload, ["placements_count", "unplaced_count"], where="report.metrics")

        file_path_keys = [
            "project_json",
            "sparrow_instance_json",
            "solver_input_json",
            "sparrow_input_meta_json",
            "sparrow_output_json",
            "solver_output_json",
        ]
        for key in file_path_keys:
            candidate = Path(str(paths_payload[key])).resolve()
            if not candidate.is_file():
                raise AssertionError(f"report.paths.{key} does not point to existing file: {candidate}")

        out_dir_from_report = Path(str(paths_payload["out_dir"])).resolve()
        if not out_dir_from_report.is_dir():
            raise AssertionError(f"report.paths.out_dir does not point to existing dir: {out_dir_from_report}")
        if out_dir_from_report != (run_dir / "out").resolve():
            raise AssertionError(
                f"report.paths.out_dir mismatch: expected {(run_dir / 'out').resolve()} got {out_dir_from_report}"
            )
        out_sheet_001 = out_dir_from_report / "sheet_001.dxf"
        if not out_sheet_001.is_file():
            raise AssertionError(f"report out_dir missing sheet_001.dxf: {out_sheet_001}")
        if out_sheet_001.stat().st_size <= 0:
            raise AssertionError(f"report out_dir sheet_001.dxf empty: {out_sheet_001}")

    print("[OK] real DXF + Sparrow pipeline smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
