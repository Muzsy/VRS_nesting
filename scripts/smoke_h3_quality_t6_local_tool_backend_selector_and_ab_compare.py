#!/usr/bin/env python3
"""Smoke for T6: backend selector + A/B compare matrix in local tooling.

Validates:
- CLI/GUI config normalization for engine_backend
- subprocess env override for WORKER_ENGINE_BACKEND
- benchmark runner --plan-only --compare-backends matrix
- compare delta block from fake run results

Runs without real Supabase, real solver or real worker process.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.trial_run_tool_core import (  # noqa: E402
    VALID_ENGINE_BACKENDS,
    TrialRunConfig,
    TrialRunToolError,
    _engine_backend_env_overrides,
)
from scripts.trial_run_tool_gui import GuiFormValues, build_config_from_form  # noqa: E402
from scripts.run_h3_quality_benchmark import _build_compare_delta  # noqa: E402
from scripts.smoke_trial_run_tool_cli_core import _FakeTransport  # noqa: E402
from scripts.trial_run_tool_core import run_trial  # noqa: E402


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# 1) CLI backend selector -> TrialRunConfig
# ---------------------------------------------------------------------------
def _assert_cli_backend_selector() -> None:
    """Verify CLI --engine-backend flows into TrialRunConfig correctly."""
    from scripts.run_trial_run_tool import _build_parser

    parser = _build_parser()
    # default = auto
    args_default = parser.parse_args(["--dxf-dir", "/tmp", "--sheet-width", "1000", "--sheet-height", "500", "--non-interactive"])
    assert args_default.engine_backend == "auto", f"expected default auto, got {args_default.engine_backend}"

    for backend in ("sparrow_v1", "nesting_engine_v2"):
        args_explicit = parser.parse_args([
            "--dxf-dir", "/tmp",
            "--sheet-width", "1000",
            "--sheet-height", "500",
            "--engine-backend", backend,
            "--non-interactive",
        ])
        assert args_explicit.engine_backend == backend, f"expected {backend}, got {args_explicit.engine_backend}"

    print("  PASS cli_backend_selector")


# ---------------------------------------------------------------------------
# 2) GUI backend selector -> GuiFormValues -> TrialRunConfig
# ---------------------------------------------------------------------------
def _assert_gui_backend_selector() -> None:
    """Verify GUI form engine_backend normalizes into TrialRunConfig."""
    with TemporaryDirectory(prefix="smoke_t6_gui_") as tmp:
        dxf_dir = Path(tmp) / "dxf"
        dxf_dir.mkdir()
        (dxf_dir / "part.dxf").write_text("0\nEOF\n", encoding="utf-8")

        for backend in VALID_ENGINE_BACKENDS:
            form = GuiFormValues(
                dxf_dir=str(dxf_dir),
                api_base_url="http://127.0.0.1:8000/v1",
                sheet_width="2000",
                sheet_height="1000",
                output_base_dir=str(Path(tmp) / "out"),
                mode="existing",
                project_id="proj_1",
                project_name="",
                project_description="",
                default_qty="1",
                auto_start_platform=False,
                technology_display_name="Test",
                technology_machine_code="M",
                technology_material_code="MAT",
                technology_thickness_mm="3",
                technology_kerf_mm="0.2",
                technology_spacing_mm="0",
                technology_margin_mm="0",
                technology_rotation_step_deg="90",
                technology_allow_free_rotation=False,
                engine_backend=backend,
            )
            config, _ = build_config_from_form(form, {})
            assert config.engine_backend == backend, f"GUI: expected {backend}, got {config.engine_backend}"

        # Invalid backend should raise
        try:
            bad_form = GuiFormValues(
                dxf_dir=str(dxf_dir),
                api_base_url="http://127.0.0.1:8000/v1",
                sheet_width="2000",
                sheet_height="1000",
                output_base_dir=str(Path(tmp) / "out"),
                mode="existing",
                project_id="proj_1",
                project_name="",
                project_description="",
                default_qty="1",
                auto_start_platform=False,
                technology_display_name="Test",
                technology_machine_code="M",
                technology_material_code="MAT",
                technology_thickness_mm="3",
                technology_kerf_mm="0.2",
                technology_spacing_mm="0",
                technology_margin_mm="0",
                technology_rotation_step_deg="90",
                technology_allow_free_rotation=False,
                engine_backend="invalid_backend",
            )
            build_config_from_form(bad_form, {})
            raise RuntimeError("should have raised TrialRunToolError for invalid backend")
        except TrialRunToolError:
            pass

    print("  PASS gui_backend_selector")


# ---------------------------------------------------------------------------
# 3) Platform command env override
# ---------------------------------------------------------------------------
def _assert_platform_env_override() -> None:
    """Verify _engine_backend_env_overrides returns correct env for each mode."""
    cfg_auto = TrialRunConfig(dxf_dir=Path("/tmp"), engine_backend="auto")
    assert _engine_backend_env_overrides(cfg_auto) is None, "auto should not produce env overrides"

    cfg_v1 = TrialRunConfig(dxf_dir=Path("/tmp"), engine_backend="sparrow_v1")
    overrides_v1 = _engine_backend_env_overrides(cfg_v1)
    assert overrides_v1 == {"WORKER_ENGINE_BACKEND": "sparrow_v1"}, f"unexpected: {overrides_v1}"

    cfg_v2 = TrialRunConfig(dxf_dir=Path("/tmp"), engine_backend="nesting_engine_v2")
    overrides_v2 = _engine_backend_env_overrides(cfg_v2)
    assert overrides_v2 == {"WORKER_ENGINE_BACKEND": "nesting_engine_v2"}, f"unexpected: {overrides_v2}"

    print("  PASS platform_env_override")


# ---------------------------------------------------------------------------
# 4) quality_summary requested/effective/match fields
# ---------------------------------------------------------------------------
def _assert_quality_summary_backend_fields() -> None:
    """Verify quality_summary.json contains requested/effective/match backend fields."""
    with TemporaryDirectory(prefix="smoke_t6_qs_") as tmp:
        root = Path(tmp)
        dxf_dir = root / "dxf"
        out_dir = root / "runs"
        dxf_dir.mkdir(parents=True)
        (dxf_dir / "part_a.dxf").write_text("0\nEOF\n", encoding="utf-8")

        for backend in ("auto", "sparrow_v1"):
            cfg = TrialRunConfig(
                dxf_dir=dxf_dir,
                bearer_token="trial-token-12345",
                token_source="argv",
                api_base_url="http://localhost:8000/v1",
                sheet_width=2000.0,
                sheet_height=1000.0,
                default_qty=1,
                output_base_dir=out_dir,
                auto_start_platform=False,
                supabase_url="https://example.supabase.co",
                supabase_anon_key="anon-key",
                poll_interval_s=0.01,
                run_poll_timeout_s=2.0,
                geometry_poll_timeout_s=2.0,
                engine_backend=backend,
            )
            result = run_trial(cfg, transport=_FakeTransport())
            if not result.success:
                raise RuntimeError(f"run_trial failed for backend={backend}: {result.error_message}")

            qs = _load_json(result.run_dir / "quality_summary.json")
            assert "requested_engine_backend" in qs, f"missing requested_engine_backend for backend={backend}"
            assert "effective_engine_backend" in qs, f"missing effective_engine_backend for backend={backend}"
            assert "engine_backend_match" in qs, f"missing engine_backend_match for backend={backend}"
            assert qs["requested_engine_backend"] == backend, (
                f"requested mismatch: {qs['requested_engine_backend']} != {backend}"
            )
            # effective should be from engine_meta evidence (sparrow_v1 in fake transport)
            assert qs["effective_engine_backend"] == "sparrow_v1", (
                f"effective mismatch: {qs['effective_engine_backend']}"
            )

            if backend == "sparrow_v1":
                assert qs["engine_backend_match"] is True, "match should be True for sparrow_v1"
            elif backend == "auto":
                assert qs["engine_backend_match"] is None, "match should be None for auto"

    print("  PASS quality_summary_backend_fields")


# ---------------------------------------------------------------------------
# 5) Benchmark runner --plan-only --compare-backends matrix
# ---------------------------------------------------------------------------
def _assert_benchmark_plan_compare() -> None:
    """Verify benchmark runner produces case x backend matrix in plan-only mode."""
    with TemporaryDirectory(prefix="smoke_t6_bench_") as tmp:
        tmp_root = Path(tmp)
        output_json = tmp_root / "benchmark_plan.json"
        fixtures_root = tmp_root / "fixtures"

        cmd = [
            sys.executable,
            str(ROOT / "scripts" / "run_h3_quality_benchmark.py"),
            "--manifest",
            str(ROOT / "samples" / "trial_run_quality" / "benchmark_manifest_v1.json"),
            "--fixtures-root",
            str(fixtures_root),
            "--output",
            str(output_json),
            "--plan-only",
            "--compare-backends",
        ]
        proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=False)
        if proc.returncode != 0:
            raise RuntimeError(
                "benchmark runner --plan-only --compare-backends failed\n"
                f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
            )

        payload = _load_json(output_json)
        assert isinstance(payload, dict), "output must be dict"
        assert payload.get("plan_only") is True, "should be plan_only"
        assert payload.get("backends") == ["sparrow_v1", "nesting_engine_v2"], (
            f"unexpected backends: {payload.get('backends')}"
        )

        entries = payload.get("entries", [])
        assert isinstance(entries, list), "entries must be list"

        # Each case should appear twice (one per backend)
        from scripts.gen_h3_quality_benchmark_fixtures import CASE_SPECS
        expected_count = len(CASE_SPECS) * 2
        assert len(entries) == expected_count, (
            f"expected {expected_count} entries (cases x 2 backends), got {len(entries)}"
        )

        # Verify engine_backend is set on each entry
        for entry in entries:
            assert "engine_backend" in entry, "entry missing engine_backend"
            assert entry["engine_backend"] in ("sparrow_v1", "nesting_engine_v2"), (
                f"unexpected backend in entry: {entry['engine_backend']}"
            )

        # Check that each case has both backends
        from collections import Counter
        case_backend_pairs = [(e["case_id"], e["engine_backend"]) for e in entries]
        assert len(case_backend_pairs) == len(set(case_backend_pairs)), "duplicate case+backend pairs"

    print("  PASS benchmark_plan_compare")


# ---------------------------------------------------------------------------
# 6) Compare delta block from fake results
# ---------------------------------------------------------------------------
def _assert_compare_delta_block() -> None:
    """Verify _build_compare_delta produces correct deltas from fake entries."""
    entry_v1: dict[str, Any] = {
        "case_id": "test_case",
        "engine_backend": "sparrow_v1",
        "runtime_sec": 2.5,
        "quality_summary": {
            "status": "ok",
            "effective_engine_backend": "sparrow_v1",
            "sheets_used": 3,
            "solver_utilization_pct": 72.5,
            "nonzero_rotation_count": 2,
        },
    }
    entry_v2: dict[str, Any] = {
        "case_id": "test_case",
        "engine_backend": "nesting_engine_v2",
        "runtime_sec": 1.8,
        "quality_summary": {
            "status": "ok",
            "effective_engine_backend": "nesting_engine_v2",
            "sheets_used": 2,
            "solver_utilization_pct": 85.0,
            "nonzero_rotation_count": 4,
        },
    }

    delta = _build_compare_delta("test_case", [entry_v1, entry_v2])
    assert delta is not None, "delta should not be None"
    assert delta["case_id"] == "test_case"
    assert delta["requested_backends"] == ["sparrow_v1", "nesting_engine_v2"]
    assert delta["effective_backends"] == ["sparrow_v1", "nesting_engine_v2"]
    assert delta["sheet_count_delta"] == -1.0, f"sheet delta: {delta['sheet_count_delta']}"
    assert abs(delta["utilization_pct_delta"] - 12.5) < 0.001, f"util delta: {delta['utilization_pct_delta']}"
    assert abs(delta["runtime_sec_delta"] - (-0.7)) < 0.001, f"runtime delta: {delta['runtime_sec_delta']}"
    assert delta["nonzero_rotation_delta"] == 2, f"rotation delta: {delta['nonzero_rotation_delta']}"
    assert delta["winner_by_sheet_count"] == "nesting_engine_v2", f"winner sheets: {delta['winner_by_sheet_count']}"
    assert delta["winner_by_utilization"] == "nesting_engine_v2", f"winner util: {delta['winner_by_utilization']}"
    assert delta["incomplete_reason"] is None

    # Incomplete case: one side has error
    entry_err: dict[str, Any] = {
        "case_id": "test_case",
        "engine_backend": "nesting_engine_v2",
        "runtime_sec": None,
        "quality_summary": {"status": "error"},
    }
    delta_incomplete = _build_compare_delta("test_case", [entry_v1, entry_err])
    assert delta_incomplete is not None
    assert delta_incomplete["incomplete_reason"] is not None
    assert "not enough" in delta_incomplete["incomplete_reason"]

    print("  PASS compare_delta_block")


# ---------------------------------------------------------------------------
# 7) Single-backend benchmark plan-only (backward compat)
# ---------------------------------------------------------------------------
def _assert_benchmark_plan_single_backend() -> None:
    """Verify plan-only without --compare-backends uses single auto backend."""
    with TemporaryDirectory(prefix="smoke_t6_single_") as tmp:
        tmp_root = Path(tmp)
        output_json = tmp_root / "benchmark_plan.json"
        fixtures_root = tmp_root / "fixtures"

        cmd = [
            sys.executable,
            str(ROOT / "scripts" / "run_h3_quality_benchmark.py"),
            "--manifest",
            str(ROOT / "samples" / "trial_run_quality" / "benchmark_manifest_v1.json"),
            "--fixtures-root",
            str(fixtures_root),
            "--output",
            str(output_json),
            "--plan-only",
        ]
        proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=False)
        if proc.returncode != 0:
            raise RuntimeError(
                "benchmark runner --plan-only (single backend) failed\n"
                f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
            )
        payload = _load_json(output_json)
        assert payload.get("backends") == ["auto"], f"default should be ['auto'], got {payload.get('backends')}"
        # Each case should appear once
        from scripts.gen_h3_quality_benchmark_fixtures import CASE_SPECS
        assert len(payload.get("entries", [])) == len(CASE_SPECS), "single backend: one entry per case"

    print("  PASS benchmark_plan_single_backend")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main() -> int:
    print("smoke_h3_quality_t6_local_tool_backend_selector_and_ab_compare")
    _assert_cli_backend_selector()
    _assert_gui_backend_selector()
    _assert_platform_env_override()
    _assert_quality_summary_backend_fields()
    _assert_benchmark_plan_compare()
    _assert_compare_delta_block()
    _assert_benchmark_plan_single_backend()
    print("PASS smoke_h3_quality_t6_local_tool_backend_selector_and_ab_compare")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except TrialRunToolError as exc:
        print(f"FAIL smoke_h3_quality_t6: {exc}", file=sys.stderr)
        raise
