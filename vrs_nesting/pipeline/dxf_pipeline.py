#!/usr/bin/env python3
"""DXF + Sparrow pipeline execution for CLI `dxf-run` command."""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from vrs_nesting.dxf.exporter import export_per_sheet, export_per_sheet_svg
from vrs_nesting.project.model import ProjectValidationError, load_dxf_project_json
from vrs_nesting.run_artifacts.run_dir import append_run_log, create_run_dir, write_project_snapshot
from vrs_nesting.runner.vrs_solver_runner import VrsSolverRunnerError
from vrs_nesting.sparrow.input_generator import (
    SparrowInputGeneratorError,
    build_sparrow_inputs,
    write_sparrow_input_artifacts,
)
from vrs_nesting.sparrow.multi_sheet_wrapper import MultiSheetWrapperError, run_multi_sheet_wrapper


def _eprint(msg: str) -> None:
    print(msg, file=sys.stderr)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def run_dxf_pipeline(project_path: str, run_root: str, sparrow_bin: str | None) -> int:
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
        svg_export_summary = export_per_sheet_svg(ctx.out_dir)
        append_run_log(ctx.run_log_path, "DXF_SVG_EXPORT_DONE", f"exported_count={svg_export_summary.get('exported_count', 0)}")

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
                "out_svg_dir": str(ctx.out_dir.resolve()),
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
            "svg_export_summary": svg_export_summary,
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
