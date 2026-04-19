#!/usr/bin/env python3
"""Smoke test for per-sheet SVG export artifacts in dxf-run pipeline."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _assert_under_root(path: Path, root: Path, *, label: str) -> None:
    resolved_path = path.resolve()
    resolved_root = root.resolve()
    if resolved_path == resolved_root:
        return
    if resolved_root not in resolved_path.parents:
        raise AssertionError(f"{label} is outside expected root: path={resolved_path} root={resolved_root}")


def main() -> int:
    stock_fixture = ROOT / "samples" / "dxf_demo" / "stock_rect_1000x2000.dxf"
    part_fixture = ROOT / "samples" / "dxf_demo" / "part_arc_spline_chaining_ok.dxf"
    if not stock_fixture.is_file():
        raise AssertionError(f"missing fixture: {stock_fixture}")
    if not part_fixture.is_file():
        raise AssertionError(f"missing fixture: {part_fixture}")

    with tempfile.TemporaryDirectory(prefix="vrs_svg_export_smoke_") as tmp:
        tmp_dir = Path(tmp)
        run_root = tmp_dir / "runs"
        project_path = tmp_dir / "project_dxf_v1.json"

        project = {
            "version": "dxf_v1",
            "name": "svg_export_smoke",
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
            "-m",
            "vrs_nesting.cli",
            "dxf-run",
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
            raise AssertionError(f"dxf-run failed rc={proc.returncode}, stderr={proc.stderr}")

        stdout_lines = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
        if len(stdout_lines) != 1:
            raise AssertionError(f"stdout contract violation: expected 1 line, got {len(stdout_lines)}: {stdout_lines!r}")

        run_dir = Path(stdout_lines[0]).resolve()
        if not run_dir.is_dir():
            raise AssertionError(f"invalid run_dir from stdout: {run_dir}")
        _assert_under_root(run_dir, run_root, label="run_dir")

        svg_path = run_dir / "out" / "sheet_001.svg"
        if not svg_path.is_file():
            raise AssertionError(f"missing svg artifact: {svg_path}")
        if svg_path.stat().st_size <= 0:
            raise AssertionError(f"empty svg artifact: {svg_path}")

        report_path = run_dir / "report.json"
        try:
            report = json.loads(report_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise AssertionError(f"invalid report.json: line={exc.lineno} col={exc.colno}") from exc
        if not isinstance(report, dict):
            raise AssertionError("report.json top-level must be object")

        paths_payload = report.get("paths")
        if not isinstance(paths_payload, dict):
            raise AssertionError("report.paths must be object")
        out_svg_dir = paths_payload.get("out_svg_dir")
        if not isinstance(out_svg_dir, str) or not out_svg_dir.strip():
            raise AssertionError("missing report.paths.out_svg_dir")

        out_svg_dir_path = Path(out_svg_dir).resolve()
        if out_svg_dir_path != (run_dir / "out").resolve():
            raise AssertionError(
                f"report.paths.out_svg_dir mismatch: expected {(run_dir / 'out').resolve()} got {out_svg_dir_path}"
            )
        if not out_svg_dir_path.is_dir():
            raise AssertionError(f"report.paths.out_svg_dir does not point to existing dir: {out_svg_dir_path}")

    print("[OK] svg export smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
