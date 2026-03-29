#!/usr/bin/env python3
"""Headless smoke for trial_run_tool_gui helper logic."""

from __future__ import annotations

import sys
from pathlib import Path
from tempfile import TemporaryDirectory

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
            bearer_token="gui-secret-token",
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
            supabase_url="https://example.supabase.co",
            supabase_anon_key="anon-key",
        )
        qty_inputs = {
            "part_a.dxf": "3",
            "part_b.DXF": "2",
        }

        config, files = build_config_from_form(form_existing, qty_inputs)
        if [path.name for path in files] != detected_names:
            raise RuntimeError("build_config_from_form returned unexpected file list")

        if config.token_source != "gui":
            raise RuntimeError("token_source should be gui")
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

        _expect_error(
            lambda: build_config_from_form(
                GuiFormValues(
                    dxf_dir=str(dxf_dir),
                    bearer_token="token",
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
                    supabase_url="",
                    supabase_anon_key="",
                ),
                {},
            ),
            expected_substring="project_id is required",
        )

        _expect_error(
            lambda: build_config_from_form(
                GuiFormValues(
                    dxf_dir=str(dxf_dir),
                    bearer_token="token",
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
                    supabase_url="",
                    supabase_anon_key="",
                ),
                {},
            ),
            expected_substring="default_qty must be > 0",
        )

        _expect_error(
            lambda: build_config_from_form(
                GuiFormValues(
                    dxf_dir=str(dxf_dir),
                    bearer_token="token",
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
                    supabase_url="",
                    supabase_anon_key="",
                ),
                {"part_a.dxf": "x"},
            ),
            expected_substring="qty for part_a.dxf must be an integer",
        )

    print("PASS smoke_trial_run_tool_tkinter_gui")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
