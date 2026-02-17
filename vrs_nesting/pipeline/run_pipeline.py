#!/usr/bin/env python3
"""Table-solver pipeline execution for CLI `run` command."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from vrs_nesting.dxf.exporter import export_per_sheet
from vrs_nesting.project.model import ProjectValidationError, load_project_json
from vrs_nesting.run_artifacts.run_dir import append_run_log, create_run_dir, write_project_snapshot
from vrs_nesting.runner.vrs_solver_runner import VrsSolverRunnerError, run_solver_in_dir
from vrs_nesting.validate.solution_validator import validate_nesting_solution


def _eprint(msg: str) -> None:
    print(msg, file=sys.stderr)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _build_solver_input(project_payload: dict[str, Any]) -> dict[str, Any]:
    stocks_raw = project_payload.get("stocks", [])
    parts_raw = project_payload.get("parts", [])

    stocks: list[dict[str, Any]] = []
    for stock in stocks_raw:
        stocks.append(
            {
                "id": stock["id"],
                "quantity": stock["quantity"],
                "width": stock["width"],
                "height": stock["height"],
            }
        )

    parts: list[dict[str, Any]] = []
    for part in parts_raw:
        parts.append(
            {
                "id": part["id"],
                "width": part["width"],
                "height": part["height"],
                "quantity": part["quantity"],
                "allowed_rotations_deg": part["allowed_rotations_deg"],
            }
        )

    return {
        "contract_version": "v1",
        "project_name": project_payload["name"],
        "seed": project_payload["seed"],
        "time_limit_s": project_payload["time_limit_s"],
        "stocks": stocks,
        "parts": parts,
    }


def run_table_pipeline(project_path: str, run_root: str) -> int:
    try:
        project = load_project_json(project_path)
    except ProjectValidationError as exc:
        _eprint(f"ERROR: {exc.code}: {exc.message}")
        return 2

    ctx = None
    try:
        ctx = create_run_dir(run_root=run_root)
        append_run_log(ctx.run_log_path, "RUN_START", f"project={Path(project_path).resolve()}")

        normalized = project.to_dict()
        snapshot_path = write_project_snapshot(ctx.run_dir, normalized)
        append_run_log(ctx.run_log_path, "PROJECT_VALIDATED", f"snapshot={snapshot_path}")
        append_run_log(ctx.run_log_path, "RUN_READY", f"seed={project.seed} time_limit_s={project.time_limit_s}")

        solver_input = _build_solver_input(normalized)
        solver_input_path = ctx.run_dir / "solver_input.json"
        _write_json(solver_input_path, solver_input)
        append_run_log(ctx.run_log_path, "SOLVER_INPUT_WRITTEN", f"path={solver_input_path}")

        run_dir, runner_meta = run_solver_in_dir(
            str(solver_input_path),
            run_dir=ctx.run_dir,
            seed=project.seed,
            time_limit_s=project.time_limit_s,
        )
        append_run_log(
            ctx.run_log_path,
            "SOLVER_FINISHED",
            f"return_code={runner_meta.get('return_code')} duration_sec={runner_meta.get('duration_sec')}",
        )

        solver_output_path = run_dir / "solver_output.json"
        validate_nesting_solution(solver_input_path, solver_output_path)
        append_run_log(ctx.run_log_path, "VALIDATOR_PASS", f"output={solver_output_path}")

        out_dir = run_dir / "out"
        export_summary = export_per_sheet(solver_input, json.loads(solver_output_path.read_text(encoding="utf-8")), out_dir)
        append_run_log(ctx.run_log_path, "EXPORT_DONE", f"exported_count={export_summary.get('exported_count', 0)}")

        report_payload = {
            "contract_version": "v1",
            "project_name": normalized["name"],
            "seed": normalized["seed"],
            "time_limit_s": normalized["time_limit_s"],
            "run_dir": str(run_dir),
            "status": "ok",
            "paths": {
                "project_json": str((run_dir / "project.json").resolve()),
                "solver_input_json": str(solver_input_path.resolve()),
                "solver_output_json": str(solver_output_path.resolve()),
                "runner_meta_json": str((run_dir / "runner_meta.json").resolve()),
                "out_dir": str(out_dir.resolve()),
            },
            "metrics": {
                "placements_count": runner_meta.get("placements_count"),
                "unplaced_count": runner_meta.get("unplaced_count"),
                "sheet_count_used": runner_meta.get("sheet_count_used"),
            },
            "export_summary": export_summary,
            "validator": {"status": "pass"},
        }
        report_path = run_dir / "report.json"
        _write_json(report_path, report_payload)
        append_run_log(ctx.run_log_path, "REPORT_WRITTEN", f"path={report_path}")
    except Exception as exc:  # noqa: BLE001
        if ctx is not None:
            append_run_log(ctx.run_log_path, "RUN_FAIL", str(exc))
        if isinstance(exc, VrsSolverRunnerError):
            _eprint(f"ERROR: E_RUN_SOLVER: {exc}")
            return 2
        _eprint(f"ERROR: E_RUN_PIPELINE: {exc}")
        return 2

    print(str(ctx.run_dir))
    return 0

