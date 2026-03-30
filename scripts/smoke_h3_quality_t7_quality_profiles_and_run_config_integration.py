#!/usr/bin/env python3
"""Smoke for T7: quality profiles + snapshot/runtime integration.

Validates:
- canonical quality profile registry presets
- worker profile resolution and nesting_engine CLI arg mapping
- snapshot builder default/explicit quality profile truth
- local tool CLI/GUI profile normalization + worker env overrides
- benchmark runner case x profile matrix in --plan-only mode

Runs without real Supabase, real worker process, or real solver binary.
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

from api.services.run_snapshot_builder import build_run_snapshot_payload  # noqa: E402
from scripts.run_h3_quality_benchmark import _load_json  # noqa: E402
from scripts.run_trial_run_tool import _build_parser as _build_trial_cli_parser  # noqa: E402
from scripts.smoke_h1_e4_t1_run_snapshot_builder_h1_minimum import (  # noqa: E402
    FakeSupabaseClient,
    _seed_happy_path,
)
from scripts.trial_run_tool_core import (  # noqa: E402
    TrialRunConfig,
    VALID_QUALITY_PROFILES,
    _worker_env_overrides,
)
from scripts.trial_run_tool_gui import GuiFormValues, build_config_from_form  # noqa: E402
from vrs_nesting.config.nesting_quality_profiles import (  # noqa: E402
    DEFAULT_QUALITY_PROFILE,
    VALID_QUALITY_PROFILE_NAMES,
    build_nesting_engine_cli_args_for_quality_profile,
    compact_runtime_policy,
    get_quality_profile_registry,
    runtime_policy_for_quality_profile,
)
import worker.main as worker_main  # noqa: E402


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _assert_registry_presets() -> None:
    registry = get_quality_profile_registry()
    _assert(tuple(sorted(registry.keys())) == tuple(sorted(VALID_QUALITY_PROFILE_NAMES)), "registry key mismatch")

    fast = registry["fast_preview"]
    _assert(fast.get("placer") == "blf", "fast_preview placer mismatch")
    _assert(fast.get("search") == "none", "fast_preview search mismatch")
    _assert(fast.get("part_in_part") == "off", "fast_preview part_in_part mismatch")

    qd = registry["quality_default"]
    _assert(qd.get("placer") == "nfp", "quality_default placer mismatch")
    _assert(qd.get("search") == "sa", "quality_default search mismatch")
    _assert(qd.get("part_in_part") == "auto", "quality_default part_in_part mismatch")

    qa = registry["quality_aggressive"]
    _assert(qa.get("placer") == "nfp", "quality_aggressive placer mismatch")
    _assert(qa.get("search") == "sa", "quality_aggressive search mismatch")
    _assert(qa.get("part_in_part") == "auto", "quality_aggressive part_in_part mismatch")
    _assert(int(qa.get("sa_iters") or 0) > 0, "quality_aggressive sa_iters missing")

    print("  PASS registry_presets")


def _settings(temp_root: Path, *, backend: str, profile_override: str | None = None) -> worker_main.WorkerSettings:
    return worker_main.WorkerSettings(
        supabase_url="https://example.supabase.co",
        supabase_project_ref="proj",
        supabase_access_token="token",
        supabase_service_role_key="service",
        storage_bucket="vrs-nesting",
        worker_id="worker-smoke",
        poll_interval_s=0.1,
        retry_delay_s=1,
        alert_backlog_seconds=60,
        run_timeout_extra_s=0,
        run_log_sync_interval_s=1.0,
        queue_heartbeat_s=1.0,
        queue_lease_ttl_s=10,
        stale_temp_cleanup_max_age_s=60.0,
        run_root=temp_root / "runs-root",
        temp_root=temp_root,
        run_artifacts_bucket="run-artifacts",
        sparrow_bin="",
        once=True,
        engine_backend=backend,
        quality_profile_override=profile_override,
    )


def _assert_worker_profile_cli_mapping() -> None:
    with TemporaryDirectory(prefix="smoke_t7_worker_") as tmp:
        root = Path(tmp)
        run_root = root / "runs"
        input_path = root / "solver_input.json"
        input_path.write_text("{}\n", encoding="utf-8")
        solver_input_payload = {"seed": 7, "time_limit_sec": 5}

        for profile in VALID_QUALITY_PROFILE_NAMES:
            snapshot_policy = compact_runtime_policy(runtime_policy_for_quality_profile(profile))
            snapshot_row = {
                "solver_config_jsonb": {
                    "quality_profile": profile,
                    "nesting_engine_runtime_policy": snapshot_policy,
                }
            }
            settings = _settings(root, backend=worker_main.ENGINE_BACKEND_NESTING_V2)
            resolution = worker_main._resolve_engine_profile_resolution(
                snapshot_row=snapshot_row,
                settings=settings,
                engine_backend=worker_main.ENGINE_BACKEND_NESTING_V2,
            )
            expected_cli = build_nesting_engine_cli_args_for_quality_profile(profile)
            _assert(
                resolution.nesting_engine_cli_args == expected_cli,
                f"worker cli args mismatch for profile={profile}: {resolution.nesting_engine_cli_args} != {expected_cli}",
            )
            invocation = worker_main._build_solver_runner_invocation(
                settings=settings,
                engine_backend=worker_main.ENGINE_BACKEND_NESTING_V2,
                run_id=f"run-{profile}",
                run_root=run_root,
                solver_input_path=input_path,
                solver_input_payload=solver_input_payload,
                nesting_engine_cli_args=resolution.nesting_engine_cli_args,
            )
            cmd = invocation.cmd
            _assert(
                "vrs_nesting.runner.nesting_engine_runner" in " ".join(cmd),
                f"unexpected runner module for profile={profile}: {cmd}",
            )
            for token in expected_cli:
                _assert(token in cmd, f"missing cli token={token} for profile={profile}: {cmd}")

        # Explicit noop truth for sparrow_v1 path.
        snapshot_row_noop = {
            "solver_config_jsonb": {
                "quality_profile": "quality_aggressive",
                "nesting_engine_runtime_policy": compact_runtime_policy(runtime_policy_for_quality_profile("quality_aggressive")),
            }
        }
        sparrow_settings = _settings(root, backend=worker_main.ENGINE_BACKEND_SPARROW_V1)
        noop_resolution = worker_main._resolve_engine_profile_resolution(
            snapshot_row=snapshot_row_noop,
            settings=sparrow_settings,
            engine_backend=worker_main.ENGINE_BACKEND_SPARROW_V1,
        )
        _assert(noop_resolution.nesting_engine_cli_args == [], "sparrow noop path should not emit nesting cli args")
        _assert(noop_resolution.effective_engine_profile == "sparrow_v1_noop", "sparrow noop effective profile mismatch")
        _assert(noop_resolution.engine_profile_match is False, "sparrow noop profile_match should be False")

    print("  PASS worker_profile_cli_mapping")


def _assert_snapshot_quality_truth() -> None:
    fake = FakeSupabaseClient()
    seeded = _seed_happy_path(fake)

    default_payload = build_run_snapshot_payload(
        supabase=fake,
        access_token="token-u1",
        owner_user_id=seeded["owner_id"],
        project_id=seeded["project_id"],
    )
    default_solver_cfg = default_payload.get("solver_config_jsonb")
    _assert(isinstance(default_solver_cfg, dict), "default solver_config_jsonb missing")
    _assert(default_solver_cfg.get("quality_profile") == DEFAULT_QUALITY_PROFILE, "default quality_profile mismatch")
    _assert(default_solver_cfg.get("engine_backend_hint") == "nesting_engine_v2", "engine_backend_hint mismatch")
    default_policy = default_solver_cfg.get("nesting_engine_runtime_policy")
    _assert(isinstance(default_policy, dict), "default nesting_engine_runtime_policy missing")

    explicit_payload = build_run_snapshot_payload(
        supabase=fake,
        access_token="token-u1",
        owner_user_id=seeded["owner_id"],
        project_id=seeded["project_id"],
        quality_profile="fast_preview",
    )
    explicit_solver_cfg = explicit_payload.get("solver_config_jsonb")
    _assert(isinstance(explicit_solver_cfg, dict), "explicit solver_config_jsonb missing")
    _assert(explicit_solver_cfg.get("quality_profile") == "fast_preview", "explicit quality_profile mismatch")
    explicit_policy = explicit_solver_cfg.get("nesting_engine_runtime_policy")
    _assert(isinstance(explicit_policy, dict), "explicit runtime policy missing")
    _assert(explicit_policy.get("placer") == "blf", "explicit runtime policy placer mismatch")
    _assert(explicit_policy.get("search") == "none", "explicit runtime policy search mismatch")
    _assert(explicit_policy.get("part_in_part") == "off", "explicit runtime policy part_in_part mismatch")

    print("  PASS snapshot_quality_truth")


def _assert_local_tool_profile_selector() -> None:
    # CLI parser surface
    parser = _build_trial_cli_parser()
    args_default = parser.parse_args(["--dxf-dir", "/tmp", "--sheet-width", "1000", "--sheet-height", "500", "--non-interactive"])
    _assert(args_default.quality_profile == DEFAULT_QUALITY_PROFILE, "CLI default quality_profile mismatch")

    args_explicit = parser.parse_args(
        [
            "--dxf-dir",
            "/tmp",
            "--sheet-width",
            "1000",
            "--sheet-height",
            "500",
            "--quality-profile",
            "quality_aggressive",
            "--non-interactive",
        ]
    )
    _assert(args_explicit.quality_profile == "quality_aggressive", "CLI explicit quality_profile mismatch")

    # GUI form normalization surface
    with TemporaryDirectory(prefix="smoke_t7_gui_") as tmp:
        dxf_dir = Path(tmp) / "dxf"
        dxf_dir.mkdir(parents=True)
        (dxf_dir / "part.dxf").write_text("0\nEOF\n", encoding="utf-8")

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
            engine_backend="nesting_engine_v2",
            quality_profile="quality_aggressive",
        )
        config, _files = build_config_from_form(form, {})
        _assert(config.quality_profile == "quality_aggressive", "GUI quality_profile normalization mismatch")
        overrides = _worker_env_overrides(config)
        _assert(overrides.get("WORKER_QUALITY_PROFILE") == "quality_aggressive", "worker env override missing quality profile")
        _assert(overrides.get("WORKER_ENGINE_BACKEND") == "nesting_engine_v2", "worker env override missing backend")

    print("  PASS local_tool_profile_selector")


def _assert_benchmark_profile_matrix_plan_only() -> None:
    with TemporaryDirectory(prefix="smoke_t7_bench_") as tmp:
        tmp_root = Path(tmp)
        output_json = tmp_root / "benchmark_plan_profiles.json"
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
            "--engine-backend",
            "nesting_engine_v2",
            "--quality-profile",
            "fast_preview",
            "--quality-profile",
            "quality_default",
            "--quality-profile",
            "quality_aggressive",
        ]
        proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=False)
        if proc.returncode != 0:
            raise RuntimeError(
                "benchmark runner --plan-only profile matrix failed\n"
                f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
            )

        payload = _load_json(output_json)
        _assert(isinstance(payload, dict), "benchmark output payload must be object")
        _assert(payload.get("plan_only") is True, "benchmark output should be plan_only")
        _assert(payload.get("backends") == ["nesting_engine_v2"], f"unexpected backends: {payload.get('backends')}")
        _assert(
            payload.get("quality_profiles") == ["fast_preview", "quality_default", "quality_aggressive"],
            f"unexpected quality_profiles: {payload.get('quality_profiles')}",
        )

        entries = payload.get("entries")
        _assert(isinstance(entries, list), "entries must be list")
        from scripts.gen_h3_quality_benchmark_fixtures import CASE_SPECS

        expected_count = len(CASE_SPECS) * 3
        _assert(len(entries) == expected_count, f"expected {expected_count} entries, got {len(entries)}")

        for entry in entries:
            _assert(entry.get("engine_backend") == "nesting_engine_v2", f"unexpected entry backend: {entry}")
            _assert(entry.get("quality_profile") in VALID_QUALITY_PROFILES, f"unexpected entry profile: {entry}")

    print("  PASS benchmark_profile_matrix_plan_only")


def main() -> int:
    _assert_registry_presets()
    _assert_worker_profile_cli_mapping()
    _assert_snapshot_quality_truth()
    _assert_local_tool_profile_selector()
    _assert_benchmark_profile_matrix_plan_only()
    print("[smoke_h3_quality_t7] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
