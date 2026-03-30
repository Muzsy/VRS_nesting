#!/usr/bin/env python3
"""Headless smoke for trial_run_tool_gui helper logic."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.trial_run_tool_core import TrialRunToolError
from scripts.trial_run_tool_gui import GuiFormValues, build_config_from_form, collect_dxf_files


def _expect_error(fn, *, expected_substring: str) -> None:
    try:
        fn()
    except TrialRunToolError as exc:
        if expected_substring not in str(exc):
            raise RuntimeError(f"unexpected error text: {exc}") from exc
        return
    raise RuntimeError(f"expected TrialRunToolError containing: {expected_substring}")


def main() -> int:
    old_supabase_url = os.environ.get("SUPABASE_URL")
    old_supabase_anon_key = os.environ.get("SUPABASE_ANON_KEY")
    os.environ.pop("SUPABASE_URL", None)
    os.environ.pop("SUPABASE_ANON_KEY", None)

    try:
        with TemporaryDirectory(prefix="smoke_tk_gui_") as tmp:
            root = Path(tmp)
            dxf_dir = root / "dxf"
            out_dir = root / "runs"
            dxf_dir.mkdir(parents=True, exist_ok=True)
            out_dir.mkdir(parents=True, exist_ok=True)

            (dxf_dir / "part_a.dxf").write_text("0\nEOF\n", encoding="utf-8")
            (dxf_dir / "part_b.DXF").write_text("0\nEOF\n", encoding="utf-8")
            (dxf_dir / "notes.txt").write_text("ignore", encoding="utf-8")

            detected = collect_dxf_files(dxf_dir)
            detected_names = [path.name for path in detected]
            if detected_names != ["part_a.dxf", "part_b.DXF"]:
                raise RuntimeError(f"unexpected dxf detection order/content: {detected_names}")

            form_existing = GuiFormValues(
                dxf_dir=str(dxf_dir),
                api_base_url="http://localhost:8000/v1",
                sheet_width="2000",
                sheet_height="1000",
                output_base_dir=str(out_dir),
                mode="existing",
                project_id="project_42",
                project_name="ignored in existing mode",
                project_description="ignored in existing mode",
                default_qty="2",
                auto_start_platform=False,
                technology_display_name="Setup ignored existing mode",
                technology_machine_code="MACH-X",
                technology_material_code="MAT-X",
                technology_thickness_mm="3.0",
                technology_kerf_mm="0.2",
                technology_spacing_mm="0.0",
                technology_margin_mm="0.0",
                technology_rotation_step_deg="90",
                technology_allow_free_rotation=False,
                engine_backend="auto",
            )
            qty_inputs = {
                "part_a.dxf": "3",
                "part_b.DXF": "2",
            }

            config, files = build_config_from_form(form_existing, qty_inputs)
            if [path.name for path in files] != detected_names:
                raise RuntimeError("build_config_from_form returned unexpected file list")

            if config.bearer_token:
                raise RuntimeError("bearer_token should stay empty in GUI env-auth mode")
            if config.existing_project_id != "project_42":
                raise RuntimeError("existing_project_id mismatch")
            if config.project_name is not None:
                raise RuntimeError("project_name should be None in existing mode")
            if config.default_qty != 2:
                raise RuntimeError("default_qty mismatch")
            if config.per_file_qty != {"part_a.dxf": 3}:
                raise RuntimeError(f"unexpected per_file_qty: {config.per_file_qty}")
            if str(config.output_base_dir) != str(out_dir):
                raise RuntimeError("output_base_dir mismatch")
            if config.technology_display_name != "Setup ignored existing mode":
                raise RuntimeError("technology_display_name should pass through")
            if config.technology_machine_code != "MACH-X":
                raise RuntimeError("technology_machine_code should pass through")
            if config.technology_material_code != "MAT-X":
                raise RuntimeError("technology_material_code should pass through")

            with patch(
                "scripts.trial_run_tool_gui._resolve_env",
                side_effect=lambda key: (
                    "https://example.supabase.co"
                    if key == "SUPABASE_URL"
                    else ("anon-key" if key == "SUPABASE_ANON_KEY" else "")
                ),
            ):
                new_config, _ = build_config_from_form(
                    GuiFormValues(
                        dxf_dir=str(dxf_dir),
                        api_base_url="http://localhost:8000/v1",
                        sheet_width="2000",
                        sheet_height="1000",
                        output_base_dir=str(out_dir),
                        mode="new",
                        project_id="",
                        project_name="my project",
                        project_description="desc",
                        default_qty="1",
                        auto_start_platform=False,
                        technology_display_name="Trial Setup",
                        technology_machine_code="MACHINE",
                        technology_material_code="MATERIAL",
                        technology_thickness_mm="3.0",
                        technology_kerf_mm="0.2",
                        technology_spacing_mm="0.0",
                        technology_margin_mm="0.0",
                        technology_rotation_step_deg="90",
                        technology_allow_free_rotation=False,
                        engine_backend="auto",
                    ),
                    {},
                )
            if new_config.project_name != "my project":
                raise RuntimeError("project_name should pass through in new mode")

            _expect_error(
                lambda: build_config_from_form(
                    GuiFormValues(
                        dxf_dir=str(dxf_dir),
                        api_base_url="http://localhost:8000/v1",
                        sheet_width="2000",
                        sheet_height="1000",
                        output_base_dir=str(out_dir),
                        mode="existing",
                        project_id="",
                        project_name="",
                        project_description="",
                        default_qty="1",
                        auto_start_platform=False,
                        technology_display_name="Trial Setup",
                        technology_machine_code="MACHINE",
                        technology_material_code="MATERIAL",
                        technology_thickness_mm="3.0",
                        technology_kerf_mm="0.2",
                        technology_spacing_mm="0.0",
                        technology_margin_mm="0.0",
                        technology_rotation_step_deg="90",
                        technology_allow_free_rotation=False,
                        engine_backend="auto",
                    ),
                    {},
                ),
                expected_substring="project_id is required",
            )

            _expect_error(
                lambda: build_config_from_form(
                    GuiFormValues(
                        dxf_dir=str(dxf_dir),
                        api_base_url="http://localhost:8000/v1",
                        sheet_width="2000",
                        sheet_height="1000",
                        output_base_dir=str(out_dir),
                        mode="new",
                        project_id="",
                        project_name="my project",
                        project_description="desc",
                        default_qty="0",
                        auto_start_platform=False,
                        technology_display_name="Trial Setup",
                        technology_machine_code="MACHINE",
                        technology_material_code="MATERIAL",
                        technology_thickness_mm="3.0",
                        technology_kerf_mm="0.2",
                        technology_spacing_mm="0.0",
                        technology_margin_mm="0.0",
                        technology_rotation_step_deg="90",
                        technology_allow_free_rotation=False,
                        engine_backend="auto",
                    ),
                    {},
                ),
                expected_substring="default_qty must be > 0",
            )

            _expect_error(
                lambda: build_config_from_form(
                    GuiFormValues(
                        dxf_dir=str(dxf_dir),
                        api_base_url="http://localhost:8000/v1",
                        sheet_width="2000",
                        sheet_height="1000",
                        output_base_dir=str(out_dir),
                        mode="new",
                        project_id="",
                        project_name="my project",
                        project_description="desc",
                        default_qty="1",
                        auto_start_platform=False,
                        technology_display_name="Trial Setup",
                        technology_machine_code="MACHINE",
                        technology_material_code="MATERIAL",
                        technology_thickness_mm="3.0",
                        technology_kerf_mm="0.2",
                        technology_spacing_mm="0.0",
                        technology_margin_mm="0.0",
                        technology_rotation_step_deg="90",
                        technology_allow_free_rotation=False,
                        engine_backend="auto",
                    ),
                    {"part_a.dxf": "x"},
                ),
                expected_substring="qty for part_a.dxf must be an integer",
            )

            with patch("scripts.trial_run_tool_gui._resolve_env", return_value=""):
                _expect_error(
                    lambda: build_config_from_form(
                        GuiFormValues(
                            dxf_dir=str(dxf_dir),
                            api_base_url="http://localhost:8000/v1",
                            sheet_width="2000",
                            sheet_height="1000",
                            output_base_dir=str(out_dir),
                            mode="new",
                            project_id="",
                            project_name="my project",
                            project_description="desc",
                            default_qty="1",
                            auto_start_platform=False,
                            technology_display_name="Trial Setup",
                            technology_machine_code="MACHINE",
                            technology_material_code="MATERIAL",
                            technology_thickness_mm="3.0",
                            technology_kerf_mm="0.2",
                            technology_spacing_mm="0.0",
                            technology_margin_mm="0.0",
                            technology_rotation_step_deg="90",
                            technology_allow_free_rotation=False,
                            engine_backend="auto",
                        ),
                        {},
                    ),
                    expected_substring="requires SUPABASE_URL and SUPABASE_ANON_KEY",
                )

            print("PASS smoke_trial_run_tool_tkinter_gui")
        return 0
    finally:
        if old_supabase_url is None:
            os.environ.pop("SUPABASE_URL", None)
        else:
            os.environ["SUPABASE_URL"] = old_supabase_url

        if old_supabase_anon_key is None:
            os.environ.pop("SUPABASE_ANON_KEY", None)
        else:
            os.environ["SUPABASE_ANON_KEY"] = old_supabase_anon_key


if __name__ == "__main__":
    raise SystemExit(main())
