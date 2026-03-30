#!/usr/bin/env python3
"""CLI entrypoint for trial-run tool core."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.trial_run_tool_core import TrialRunConfig, TrialRunToolError, VALID_ENGINE_BACKENDS, parse_qty_overrides, run_trial


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run local trial-run orchestration against web_platform API.",
    )
    parser.add_argument("--dxf-dir", help="Directory containing source .dxf files")
    parser.add_argument("--token", help="Bearer token for API + RLS calls")
    parser.add_argument("--api-base-url", default="http://127.0.0.1:8000/v1", help="API base URL")
    parser.add_argument("--sheet-width", type=float, help="Sheet width in mm")
    parser.add_argument("--sheet-height", type=float, help="Sheet height in mm")
    parser.add_argument("--project-id", help="Use existing project instead of creating one")
    parser.add_argument("--project-name", help="Project name when creating a new project")
    parser.add_argument("--project-description", default="", help="Optional project description")
    parser.add_argument("--default-qty", type=int, default=1, help="Default quantity for each DXF")
    parser.add_argument(
        "--qty-override",
        action="append",
        default=[],
        metavar="NAME=QTY",
        help="Per-file quantity override (key can be file name or stem)",
    )
    parser.add_argument("--output-base-dir", default="tmp/runs", help="Base directory for run evidence")
    parser.add_argument("--poll-interval-s", type=float, default=1.0, help="Polling interval seconds")
    parser.add_argument("--run-poll-timeout-s", type=float, default=300.0, help="Run polling timeout seconds")
    parser.add_argument("--geometry-poll-timeout-s", type=float, default=60.0, help="Geometry polling timeout seconds")
    parser.add_argument("--request-timeout-s", type=float, default=30.0, help="HTTP timeout seconds")
    parser.add_argument("--health-timeout-s", type=float, default=30.0, help="Health-retry timeout after auto-start")
    parser.add_argument("--supabase-url", help="Supabase URL for geometry polling (fallback from SUPABASE_URL)")
    parser.add_argument(
        "--supabase-anon-key",
        help="Supabase anon key for geometry polling (fallback from SUPABASE_ANON_KEY)",
    )
    parser.add_argument(
        "--technology-display-name",
        default="Trial Default Setup",
        help="Project technology setup display_name for new project mode",
    )
    parser.add_argument(
        "--technology-machine-code",
        default="TRIAL-MACHINE",
        help="Project technology setup machine_code for new project mode",
    )
    parser.add_argument(
        "--technology-material-code",
        default="TRIAL-MATERIAL",
        help="Project technology setup material_code for new project mode",
    )
    parser.add_argument(
        "--technology-thickness-mm",
        type=float,
        default=3.0,
        help="Project technology setup thickness_mm for new project mode",
    )
    parser.add_argument(
        "--technology-kerf-mm",
        type=float,
        default=0.2,
        help="Project technology setup kerf_mm for new project mode",
    )
    parser.add_argument(
        "--technology-spacing-mm",
        type=float,
        default=0.0,
        help="Project technology setup spacing_mm for new project mode",
    )
    parser.add_argument(
        "--technology-margin-mm",
        type=float,
        default=0.0,
        help="Project technology setup margin_mm for new project mode",
    )
    parser.add_argument(
        "--technology-rotation-step-deg",
        type=int,
        default=90,
        help="Project technology setup rotation_step_deg for new project mode",
    )
    parser.add_argument(
        "--technology-allow-free-rotation",
        action="store_true",
        help="Project technology setup allow_free_rotation for new project mode",
    )
    parser.add_argument(
        "--auto-start-platform",
        dest="auto_start_platform",
        action="store_true",
        default=True,
        help="Auto-heal platform (start/restart when components are not running)",
    )
    parser.add_argument(
        "--no-auto-start-platform",
        dest="auto_start_platform",
        action="store_false",
        help="Disable automatic platform start/restart",
    )
    parser.add_argument(
        "--engine-backend",
        choices=list(VALID_ENGINE_BACKENDS),
        default="auto",
        help="Engine backend for nesting worker (auto | sparrow_v1 | nesting_engine_v2)",
    )
    parser.add_argument("--non-interactive", action="store_true", help="Do not prompt for missing required inputs")
    return parser


def _prompt_if_missing(value: str | None, *, label: str, non_interactive: bool) -> str:
    if value and value.strip():
        return value.strip()
    if non_interactive:
        raise TrialRunToolError(f"missing required argument: {label}")
    prompted = input(f"{label}: ").strip()
    if not prompted:
        raise TrialRunToolError(f"missing required input: {label}")
    return prompted


def _prompt_float_if_missing(value: float | None, *, label: str, non_interactive: bool) -> float:
    if value is not None:
        return float(value)
    if non_interactive:
        raise TrialRunToolError(f"missing required argument: {label}")
    raw = input(f"{label}: ").strip()
    try:
        parsed = float(raw)
    except ValueError as exc:
        raise TrialRunToolError(f"invalid number for {label}: {raw}") from exc
    return parsed


def _resolve_token(args: argparse.Namespace) -> tuple[str, str]:
    """Resolve bearer token: --token > env > empty (core auto-logins from .env.local)."""
    if args.token and str(args.token).strip():
        return str(args.token).strip(), "argv"

    for env_key in ("TRIAL_RUN_TOOL_TOKEN", "API_BEARER_TOKEN"):
        value = os.getenv(env_key, "").strip()
        if value:
            return value, "env"

    return "", "auto"


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        dxf_dir = Path(_prompt_if_missing(args.dxf_dir, label="dxf-dir", non_interactive=args.non_interactive))
        sheet_width = _prompt_float_if_missing(args.sheet_width, label="sheet-width", non_interactive=args.non_interactive)
        sheet_height = _prompt_float_if_missing(args.sheet_height, label="sheet-height", non_interactive=args.non_interactive)
        token, token_source = _resolve_token(args)

        config = TrialRunConfig(
            dxf_dir=dxf_dir,
            bearer_token=token,
            token_source=token_source,
            api_base_url=str(args.api_base_url).strip(),
            sheet_width=sheet_width,
            sheet_height=sheet_height,
            existing_project_id=(str(args.project_id).strip() if args.project_id else None),
            project_name=(str(args.project_name).strip() if args.project_name else None),
            project_description=(str(args.project_description).strip() if args.project_description else ""),
            default_qty=int(args.default_qty),
            per_file_qty=parse_qty_overrides([str(item) for item in args.qty_override]),
            output_base_dir=Path(str(args.output_base_dir)),
            auto_start_platform=bool(args.auto_start_platform),
            health_timeout_s=float(args.health_timeout_s),
            poll_interval_s=float(args.poll_interval_s),
            run_poll_timeout_s=float(args.run_poll_timeout_s),
            geometry_poll_timeout_s=float(args.geometry_poll_timeout_s),
            request_timeout_s=float(args.request_timeout_s),
            supabase_url=(str(args.supabase_url).strip() or None) if args.supabase_url else None,
            supabase_anon_key=(str(args.supabase_anon_key).strip() or None) if args.supabase_anon_key else None,
            technology_display_name=str(args.technology_display_name),
            technology_machine_code=str(args.technology_machine_code),
            technology_material_code=str(args.technology_material_code),
            technology_thickness_mm=float(args.technology_thickness_mm),
            technology_kerf_mm=float(args.technology_kerf_mm),
            technology_spacing_mm=float(args.technology_spacing_mm),
            technology_margin_mm=float(args.technology_margin_mm),
            technology_rotation_step_deg=int(args.technology_rotation_step_deg),
            technology_allow_free_rotation=bool(args.technology_allow_free_rotation),
            engine_backend=str(args.engine_backend),
        )

        result = run_trial(config)

        print(f"success={result.success}")
        print(f"run_dir={result.run_dir}")
        print(f"summary={result.summary_path}")
        if result.project_id:
            print(f"project_id={result.project_id}")
        if result.run_id:
            print(f"run_id={result.run_id}")
        if result.final_run_status:
            print(f"final_status={result.final_run_status}")
        if result.error_message:
            print(f"error={result.error_message}")

        return 0 if result.success else 1
    except TrialRunToolError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
