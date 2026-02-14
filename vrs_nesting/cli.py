#!/usr/bin/env python3
"""VRS CLI run commands for table-solver and DXF+Sparrow pipelines."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from vrs_nesting.dxf.exporter import export_per_sheet
from vrs_nesting.project.model import (
    ProjectValidationError,
    load_dxf_project_json,
    load_project_json,
)
from vrs_nesting.runner.vrs_solver_runner import VrsSolverRunnerError, run_solver_in_dir
from vrs_nesting.run_artifacts.run_dir import append_run_log, create_run_dir, write_project_snapshot
from vrs_nesting.sparrow.input_generator import (
    SparrowInputGeneratorError,
    build_sparrow_inputs,
    write_sparrow_input_artifacts,
)
from vrs_nesting.sparrow.multi_sheet_wrapper import MultiSheetWrapperError, run_multi_sheet_wrapper
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


def _cmd_run(project_path: str, run_root: str) -> int:
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


def _cmd_dxf_run(project_path: str, run_root: str, sparrow_bin: str | None) -> int:
    try:
        project = load_dxf_project_json(project_path)
    except ProjectValidationError as exc:
        _eprint(f"ERROR: {exc.code}: {exc.message}")
        return 2

    ctx = None
    try:
        project_abs = Path(project_path).resolve()
        project_dir = project_abs.parent

        ctx = create_run_dir(run_root=run_root)
        append_run_log(ctx.run_log_path, "DXF_RUN_START", f"project={project_abs}")

        snapshot_path = write_project_snapshot(ctx.run_dir, project.to_dict())
        append_run_log(ctx.run_log_path, "DXF_PROJECT_VALIDATED", f"snapshot={snapshot_path}")

        sparrow_instance, solver_input, input_meta = build_sparrow_inputs(project, project_dir=project_dir)
        instance_path, solver_input_path, meta_path = write_sparrow_input_artifacts(
            ctx.run_dir,
            sparrow_instance=sparrow_instance,
            solver_input=solver_input,
            meta=input_meta,
        )
        append_run_log(ctx.run_log_path, "DXF_INPUT_READY", f"instance={instance_path} solver_input={solver_input_path} meta={meta_path}")

        solver_output = run_multi_sheet_wrapper(
            run_dir=ctx.run_dir,
            sparrow_instance=sparrow_instance,
            solver_input=solver_input,
            seed=project.seed,
            time_limit_s=project.time_limit_s,
            sparrow_bin=sparrow_bin,
        )
        append_run_log(ctx.run_log_path, "DXF_SPARROW_DONE", f"placements={len(solver_output.get('placements', []))}")

        export_summary = export_per_sheet(solver_input, solver_output, ctx.out_dir)
        append_run_log(ctx.run_log_path, "DXF_EXPORT_DONE", f"exported_count={export_summary.get('exported_count', 0)}")

        report_payload = {
            "contract_version": "dxf_v1",
            "project_name": project.name,
            "seed": project.seed,
            "time_limit_s": project.time_limit_s,
            "run_dir": str(ctx.run_dir),
            "status": str(solver_output.get("status", "ok")),
            "paths": {
                "project_json": str(snapshot_path.resolve()),
                "sparrow_instance_json": str(instance_path.resolve()),
                "solver_input_json": str(solver_input_path.resolve()),
                "sparrow_input_meta_json": str(meta_path.resolve()),
                "sparrow_output_json": str((ctx.run_dir / "sparrow_output.json").resolve()),
                "solver_output_json": str((ctx.run_dir / "solver_output.json").resolve()),
                "out_dir": str(ctx.out_dir.resolve()),
            },
            "metrics": {
                "placements_count": len(solver_output.get("placements", [])),
                "unplaced_count": len(solver_output.get("unplaced", [])),
                "unplaced_reasons": {
                    str(reason): int(count)
                    for reason, count in Counter(
                        str(item.get("reason", "unknown"))
                        for item in solver_output.get("unplaced", [])
                        if isinstance(item, dict)
                    ).items()
                },
            },
            "export_summary": export_summary,
        }
        report_path = ctx.run_dir / "report.json"
        _write_json(report_path, report_payload)
        append_run_log(ctx.run_log_path, "DXF_REPORT_WRITTEN", f"path={report_path}")
    except Exception as exc:  # noqa: BLE001
        if ctx is not None:
            append_run_log(ctx.run_log_path, "DXF_RUN_FAIL", str(exc))
        if isinstance(exc, (ProjectValidationError, SparrowInputGeneratorError, MultiSheetWrapperError, VrsSolverRunnerError)):
            _eprint(f"ERROR: E_DXF_RUN: {exc}")
            return 2
        _eprint(f"ERROR: E_DXF_PIPELINE: {exc}")
        return 2

    print(str(ctx.run_dir))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="VRS nesting CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run full table-solver pipeline into one run directory")
    run_parser.add_argument("project_json", help="Path to project JSON file")
    run_parser.add_argument("--run-root", default="runs", help="Run artifacts root directory (default: runs)")

    dxf_run_parser = subparsers.add_parser("dxf-run", help="Run real DXF + Sparrow pipeline into one run directory")
    dxf_run_parser.add_argument("project_json", help="Path to dxf_v1 project JSON file")
    dxf_run_parser.add_argument("--run-root", default="runs", help="Run artifacts root directory (default: runs)")
    dxf_run_parser.add_argument("--sparrow-bin", default=None, help="Optional explicit Sparrow binary path")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "run":
        return _cmd_run(args.project_json, args.run_root)
    if args.command == "dxf-run":
        return _cmd_dxf_run(args.project_json, args.run_root, args.sparrow_bin)

    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
